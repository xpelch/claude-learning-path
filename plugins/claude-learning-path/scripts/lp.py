#!/usr/bin/env python3
"""Learning-path progress tracker for the claude-learning-path plugin.

Standard library only. Course content is read from ../courses; progress is
stored in <data-dir>/progress.json where <data-dir> is, in order:
--data-dir, $CLAUDE_PLUGIN_DATA, ~/.claude/claude-learning-path.

Commands:
  status                      progress per course and lesson
  next                        recommended next step
  quiz  --course C [--lesson L] [--n 5] [--review]
                              pick questions (JSON, answers included for grading)
  record-quiz --course C --results id=1,id=0,...
  record-lab  --course C --lab ID [--failed]
  mark-studied --course C --lesson L
  reset --yes
"""
import argparse
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSES_DIR = ROOT / "courses"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def data_dir(args):
    d = args.data_dir or os.environ.get("CLAUDE_PLUGIN_DATA") or str(Path.home() / ".claude" / "claude-learning-path")
    return Path(d)


def load_path():
    return load_json(COURSES_DIR / "path.json")


def find_course(path, slug):
    for c in path["courses"]:
        if c["slug"] == slug:
            return c
    sys.exit(f"error: unknown course '{slug}'. Known: {', '.join(c['slug'] for c in path['courses'])}")


def load_questions(slug):
    q = load_json(COURSES_DIR / slug / "questions.json", {"questions": []})
    return q["questions"]


def load_progress(args):
    p = load_json(data_dir(args) / "progress.json")
    return p or {"version": 1, "created": now(), "courses": {}}


def save_progress(args, prog):
    d = data_dir(args)
    d.mkdir(parents=True, exist_ok=True)
    prog["updated"] = now()
    tmp = d / "progress.json.tmp"
    tmp.write_text(json.dumps(prog, indent=2), encoding="utf-8")
    tmp.replace(d / "progress.json")


def course_prog(prog, slug):
    return prog["courses"].setdefault(slug, {"questions": {}, "lessons": {}, "labs": {}})


def lesson_mastery(cp, questions, lesson):
    """Share of the lesson's questions whose latest answer was correct."""
    qs = [q for q in questions if q["lesson"] == lesson]
    if not qs:
        return 0.0, 0, 0
    ok = sum(1 for q in qs if cp["questions"].get(q["id"], {}).get("last") == 1)
    return ok / len(qs), ok, len(qs)


def course_summary(path, prog, course):
    cp = prog["courses"].get(course["slug"], {"questions": {}, "lessons": {}, "labs": {}})
    questions = load_questions(course["slug"])
    th = path["mastery_threshold"]
    lessons = []
    for l in course["lessons"]:
        m, ok, total = lesson_mastery(cp, questions, l["slug"])
        lessons.append({
            "slug": l["slug"], "title": l["title"],
            "studied": bool(cp["lessons"].get(l["slug"], {}).get("studied")),
            "mastery": round(m, 2), "correct": ok, "total": total, "mastered": total > 0 and m >= th,
        })
    labs = [{"id": x["id"], "title": x["title"], "passed": bool(cp["labs"].get(x["id"], {}).get("passed"))}
            for x in course.get("labs", [])]
    n_items = len(lessons) + len(labs)
    done = sum(l["mastered"] for l in lessons) + sum(x["passed"] for x in labs)
    return {
        "slug": course["slug"], "title": course["title"], "status": course["status"], "url": course["url"],
        "lessons": lessons, "labs": labs,
        "percent": round(100 * done / n_items) if n_items else 0,
        "complete": n_items > 0 and done == n_items,
    }


def cmd_status(args):
    path = load_path()
    prog = load_progress(args)
    out = {"path": path["title"], "courses": [course_summary(path, prog, c) for c in path["courses"]],
           "updated": prog.get("updated")}
    if args.json:
        print(json.dumps(out, indent=2))
        return
    print(f"{out['path']}  (mastery threshold {int(path['mastery_threshold'] * 100)}%)")
    for c in out["courses"]:
        if c["status"] != "available":
            print(f"\n[ ] {c['title']} — content not in this plugin yet ({c['url']})")
            continue
        print(f"\n[{'x' if c['complete'] else ' '}] {c['title']} — {c['percent']}%")
        for l in c["lessons"]:
            mark = "x" if l["mastered"] else ("~" if l["correct"] or l["studied"] else " ")
            print(f"    [{mark}] {l['title']}: quiz {l['correct']}/{l['total']}{' (studied)' if l['studied'] else ''}")
        for x in c["labs"]:
            print(f"    [{'x' if x['passed'] else ' '}] lab {x['id']}: {x['title']}")
    print(f"\nprogress file: {data_dir(args) / 'progress.json'}")


def cmd_next(args):
    path = load_path()
    prog = load_progress(args)
    for course in path["courses"]:
        s = course_summary(path, prog, course)
        if s["complete"]:
            continue
        if s["status"] != "available":
            rec = {"action": "take-course-externally", "course": s["slug"], "title": s["title"], "url": s["url"],
                   "why": "Next course in the path; this plugin has no study material for it yet."}
            break
        lesson = next((l for l in s["lessons"] if not l["mastered"]), None)
        if lesson:
            action = "quiz" if lesson["studied"] or lesson["correct"] else "study"
            rec = {"action": action, "course": s["slug"], "lesson": lesson["slug"], "title": lesson["title"],
                   "mastery": lesson["mastery"],
                   "why": ("Review the notes for this lesson, then take its quiz." if action == "study"
                           else f"Quiz mastery is {int(lesson['mastery'] * 100)}%; reach "
                                f"{int(path['mastery_threshold'] * 100)}% to master it.")}
            break
        lab = next((x for x in s["labs"] if not x["passed"]), None)
        rec = {"action": "lab", "course": s["slug"], "lab": lab["id"], "title": lab["title"],
               "why": "All lessons mastered; practice with the hands-on labs."}
        break
    else:
        rec = {"action": "done", "why": "Every course in the path is complete."}
    print(json.dumps(rec, indent=2))


def cmd_quiz(args):
    path = load_path()
    course = find_course(path, args.course)
    if course["status"] != "available":
        sys.exit(f"error: no questions for '{args.course}' yet")
    questions = load_questions(args.course)
    if args.lesson:
        if args.lesson not in {l["slug"] for l in course["lessons"]}:
            sys.exit(f"error: unknown lesson '{args.lesson}'")
        questions = [q for q in questions if q["lesson"] == args.lesson]
    cp = load_progress(args)["courses"].get(args.course, {"questions": {}})
    seen = cp["questions"]
    if args.review:
        questions = [q for q in questions if seen.get(q["id"], {}).get("last") == 0]
        if not questions:
            print(json.dumps({"questions": [], "note": "Nothing to review: no missed questions."}))
            return
    rnd = random.Random(args.seed)
    rnd.shuffle(questions)
    # Missed first, then never asked, then already correct.
    rank = {0: 0, None: 1, 1: 2}
    questions.sort(key=lambda q: rank[seen.get(q["id"], {}).get("last")])
    print(json.dumps({"course": args.course, "questions": questions[: args.n]}, indent=2))


def cmd_record_quiz(args):
    path = load_path()
    find_course(path, args.course)
    known = {q["id"]: q for q in load_questions(args.course)}
    prog = load_progress(args)
    cp = course_prog(prog, args.course)
    recorded = []
    for item in filter(None, args.results.split(",")):
        qid, _, val = item.strip().partition("=")
        if qid not in known or val not in ("0", "1"):
            sys.exit(f"error: bad result '{item}' (expected <question-id>=0|1)")
        q = cp["questions"].setdefault(qid, {"attempts": 0, "correct": 0})
        q["attempts"] += 1
        q["correct"] += int(val)
        q["last"] = int(val)
        q["at"] = now()
        recorded.append(qid)
    save_progress(args, prog)
    lessons = sorted({known[q]["lesson"] for q in recorded})
    course = find_course(path, args.course)
    summary = course_summary(path, prog, course)
    print(json.dumps({"recorded": len(recorded),
                      "lessons": [l for l in summary["lessons"] if l["slug"] in lessons],
                      "course_percent": summary["percent"]}, indent=2))


def cmd_record_lab(args):
    course = find_course(load_path(), args.course)
    if args.lab not in {x["id"] for x in course.get("labs", [])}:
        sys.exit(f"error: unknown lab '{args.lab}'")
    prog = load_progress(args)
    lab = course_prog(prog, args.course)["labs"].setdefault(args.lab, {"attempts": 0})
    lab["attempts"] += 1
    lab["passed"] = lab.get("passed", False) or not args.failed
    lab["at"] = now()
    save_progress(args, prog)
    print(json.dumps({"lab": args.lab, **lab}))


def cmd_mark_studied(args):
    course = find_course(load_path(), args.course)
    if args.lesson not in {l["slug"] for l in course["lessons"]}:
        sys.exit(f"error: unknown lesson '{args.lesson}'")
    prog = load_progress(args)
    course_prog(prog, args.course)["lessons"].setdefault(args.lesson, {}).update(studied=True, at=now())
    save_progress(args, prog)
    print(json.dumps({"lesson": args.lesson, "studied": True}))


def cmd_reset(args):
    if not args.yes:
        sys.exit("error: pass --yes to erase all progress")
    f = data_dir(args) / "progress.json"
    if f.exists():
        f.unlink()
    print(json.dumps({"reset": True}))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_status)
    sub.add_parser("next").set_defaults(fn=cmd_next)
    p = sub.add_parser("quiz")
    p.add_argument("--course", required=True); p.add_argument("--lesson"); p.add_argument("--n", type=int, default=5)
    p.add_argument("--review", action="store_true"); p.add_argument("--seed", type=int)
    p.set_defaults(fn=cmd_quiz)
    p = sub.add_parser("record-quiz"); p.add_argument("--course", required=True); p.add_argument("--results", required=True)
    p.set_defaults(fn=cmd_record_quiz)
    p = sub.add_parser("record-lab"); p.add_argument("--course", required=True); p.add_argument("--lab", required=True)
    p.add_argument("--failed", action="store_true"); p.set_defaults(fn=cmd_record_lab)
    p = sub.add_parser("mark-studied"); p.add_argument("--course", required=True); p.add_argument("--lesson", required=True)
    p.set_defaults(fn=cmd_mark_studied)
    p = sub.add_parser("reset"); p.add_argument("--yes", action="store_true"); p.set_defaults(fn=cmd_reset)

    # Allow --data-dir after the subcommand too.
    args, rest = ap.parse_known_args(argv)
    if rest:
        extra = argparse.ArgumentParser(); extra.add_argument("--data-dir")
        e, unknown = extra.parse_known_args(rest)
        if unknown:
            ap.error(f"unrecognized arguments: {' '.join(unknown)}")
        args.data_dir = e.data_dir or args.data_dir
    args.fn(args)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
