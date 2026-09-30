#!/usr/bin/env python3
"""Learning-path progress tracker for the claude-learning-path plugin.

Standard library only. Course content is read from ../courses; progress is
stored in <data-dir>/progress.json where <data-dir> is, in order:
--data-dir, $CLAUDE_PLUGIN_DATA, ~/.claude/claude-learning-path.

Commands:
  status [--course C] [--json]
                              progress overview, or lesson detail for one course
  next                        recommended next step (JSON)
  lessons --course C          lesson slugs, titles and modules (JSON)
  quiz  --course C [--lesson L | --module M] [--n 5] [--review] [--exam]
                              pick questions (JSON, answers included for grading)
  record-quiz --course C --results id=1,id=0,...
  record-lab  --course C --lab ID [--failed]
  mark-studied --course C --lesson L
  reset --yes

A lesson may declare "same_as": "<course>/<lesson>" in path.json. It then shares
that lesson's questions, notes and progress.
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
SCHEMA_VERSION = 2


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


# ---------------------------------------------------------------- content

def load_path():
    return load_json(COURSES_DIR / "path.json")


def find_course(path, slug):
    for c in path["courses"]:
        if c["slug"] == slug:
            return c
    sys.exit(f"error: unknown course '{slug}'. Known: {', '.join(c['slug'] for c in path['courses'])}")


def find_lesson(course, slug):
    for l in course["lessons"]:
        if l["slug"] == slug:
            return l
    sys.exit(f"error: unknown lesson '{slug}' in {course['slug']}")


def canonical(course_slug, lesson):
    """(course, lesson) that owns the content and progress of a lesson."""
    if lesson.get("same_as"):
        c, _, l = lesson["same_as"].partition("/")
        return c, l
    return course_slug, lesson["slug"]


_bank_cache = {}


def bank(course_slug):
    if course_slug not in _bank_cache:
        _bank_cache[course_slug] = load_json(COURSES_DIR / course_slug / "questions.json", {"questions": []})["questions"]
    return _bank_cache[course_slug]


def lesson_questions(course_slug, lesson):
    c, l = canonical(course_slug, lesson)
    return [dict(q, lesson=lesson["slug"]) for q in bank(c) if q["lesson"] == l]


def course_questions(course):
    return [q for l in course["lessons"] for q in lesson_questions(course["slug"], l)]


# ---------------------------------------------------------------- progress

def empty_progress():
    return {"version": SCHEMA_VERSION, "created": now(), "questions": {}, "studied": {}, "labs": {}}


def migrate(prog):
    if prog.get("version", 1) >= SCHEMA_VERSION:
        return prog
    new = empty_progress()
    new["created"] = prog.get("created", new["created"])
    for c, cp in prog.get("courses", {}).items():
        new["questions"].update(cp.get("questions", {}))
        for l, v in cp.get("lessons", {}).items():
            if v.get("studied"):
                new["studied"][f"{c}/{l}"] = v.get("at", now())
        for lab, v in cp.get("labs", {}).items():
            new["labs"][f"{c}/{lab}"] = v
    return new


def load_progress(args):
    p = load_json(data_dir(args) / "progress.json")
    return migrate(p) if p else empty_progress()


def save_progress(args, prog):
    d = data_dir(args)
    d.mkdir(parents=True, exist_ok=True)
    prog["updated"] = now()
    tmp = d / "progress.json.tmp"
    tmp.write_text(json.dumps(prog, indent=2), encoding="utf-8")
    tmp.replace(d / "progress.json")


def is_studied(prog, course_slug, lesson):
    c, l = canonical(course_slug, lesson)
    return f"{c}/{l}" in prog["studied"]


# ---------------------------------------------------------------- summaries

def lesson_summary(path, prog, course_slug, lesson):
    qs = lesson_questions(course_slug, lesson)
    ok = sum(1 for q in qs if prog["questions"].get(q["id"], {}).get("last") == 1)
    m = ok / len(qs) if qs else 0.0
    return {
        "slug": lesson["slug"], "title": lesson["title"], "module": lesson.get("module"),
        "same_as": lesson.get("same_as"), "studied": is_studied(prog, course_slug, lesson),
        "mastery": round(m, 2), "correct": ok, "total": len(qs),
        "mastered": bool(qs) and m >= path["mastery_threshold"],
    }


def course_summary(path, prog, course):
    lessons = [lesson_summary(path, prog, course["slug"], l) for l in course["lessons"]]
    labs = [{"id": x["id"], "title": x["title"],
             "passed": bool(prog["labs"].get(f"{course['slug']}/{x['id']}", {}).get("passed"))}
            for x in course.get("labs", [])]
    n_items = len(lessons) + len(labs)
    done = sum(l["mastered"] for l in lessons) + sum(x["passed"] for x in labs)
    return {
        "slug": course["slug"], "title": course["title"], "status": course["status"], "url": course["url"],
        "lessons": lessons, "labs": labs,
        "percent": round(100 * done / n_items) if n_items else 0,
        "complete": n_items > 0 and done == n_items,
    }


def mark(l):
    return "x" if l["mastered"] else ("~" if l["correct"] or l["studied"] else " ")


def cmd_status(args):
    path = load_path()
    prog = load_progress(args)
    courses = [c for c in path["courses"] if not args.course or c["slug"] == args.course]
    if args.course and not courses:
        find_course(path, args.course)
    out = {"path": path["title"], "courses": [course_summary(path, prog, c) for c in courses],
           "updated": prog.get("updated")}
    if args.json:
        print(json.dumps(out, indent=2))
        return
    print(f"{out['path']}  (mastery threshold {int(path['mastery_threshold'] * 100)}%)")
    for c in out["courses"]:
        if c["status"] != "available":
            print(f"\n[ ] {c['title']} — not covered by this plugin yet ({c['url']})")
            continue
        n_m = sum(l["mastered"] for l in c["lessons"])
        n_l = sum(x["passed"] for x in c["labs"])
        print(f"\n[{'x' if c['complete'] else ' '}] {c['title']} — {c['percent']}% "
              f"({n_m}/{len(c['lessons'])} lessons mastered, {n_l}/{len(c['labs'])} labs)")
        modules = []
        for l in c["lessons"]:
            if l["module"] not in modules:
                modules.append(l["module"])
        detailed = bool(args.course) or len(c["lessons"]) <= 12
        for mod in modules:
            ls = [l for l in c["lessons"] if l["module"] == mod]
            if mod:
                done = sum(l["mastered"] for l in ls)
                print(f"    {mod}: {done}/{len(ls)} mastered")
            if detailed:
                pad = "      " if mod else "    "
                for l in ls:
                    shared = f" (shared with {l['same_as'].split('/')[0]})" if l["same_as"] else ""
                    print(f"{pad}[{mark(l)}] {l['title']}: quiz {l['correct']}/{l['total']}"
                          f"{' (studied)' if l['studied'] else ''}{shared}")
        for x in c["labs"]:
            print(f"    [{'x' if x['passed'] else ' '}] lab {x['id']}: {x['title']}")
    print(f"\nprogress file: {data_dir(args) / 'progress.json'}")


def cmd_next(args):
    path = load_path()
    prog = load_progress(args)
    rec = {"action": "done", "why": "Every course in the path is complete."}
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
                   "module": lesson["module"], "mastery": lesson["mastery"],
                   "why": ("Review the notes for this lesson, then take its quiz." if action == "study"
                           else f"Quiz mastery is {int(lesson['mastery'] * 100)}%; reach "
                                f"{int(path['mastery_threshold'] * 100)}% to master it.")}
            break
        lab = next(x for x in s["labs"] if not x["passed"])
        rec = {"action": "lab", "course": s["slug"], "lab": lab["id"], "title": lab["title"],
               "why": "All lessons mastered; practice with the hands-on labs."}
        break
    print(json.dumps(rec, indent=2))


def cmd_lessons(args):
    course = find_course(load_path(), args.course)
    print(json.dumps([{k: l[k] for k in ("slug", "title", "module", "same_as") if l.get(k)}
                      for l in course["lessons"]], indent=2))


def cmd_quiz(args):
    path = load_path()
    course = find_course(path, args.course)
    if course["status"] != "available":
        sys.exit(f"error: no questions for '{args.course}' yet")
    lessons = course["lessons"]
    if args.lesson:
        lessons = [find_lesson(course, args.lesson)]
    elif args.module:
        lessons = [l for l in lessons if (l.get("module") or "").lower() == args.module.lower()]
        if not lessons:
            mods = sorted({l.get("module") for l in course["lessons"] if l.get("module")})
            sys.exit(f"error: unknown module '{args.module}'. Known: {', '.join(mods) or 'none'}")
    seen = load_progress(args)["questions"]
    rank = {0: 0, None: 1, 1: 2}  # missed first, then never asked, then already correct
    rnd = random.Random(args.seed)

    def ordered(qs):
        qs = list(qs)
        rnd.shuffle(qs)
        qs.sort(key=lambda q: rank[seen.get(q["id"], {}).get("last")])
        return qs

    if args.exam:
        picked = [ordered(lesson_questions(course["slug"], l))[:1] for l in lessons]
        questions = [q for p in picked for q in p]
        rnd.shuffle(questions)
        n = args.n or 20
    else:
        questions = [q for l in lessons for q in lesson_questions(course["slug"], l)]
        if args.review:
            questions = [q for q in questions if seen.get(q["id"], {}).get("last") == 0]
            if not questions:
                print(json.dumps({"questions": [], "note": "Nothing to review: no missed questions."}))
                return
        questions = ordered(questions)
        n = args.n or 5
    print(json.dumps({"course": args.course, "questions": questions[:n]}, indent=2))


def cmd_record_quiz(args):
    path = load_path()
    course = find_course(path, args.course)
    known = {q["id"]: q for q in course_questions(course)}
    prog = load_progress(args)
    recorded = []
    for item in filter(None, args.results.split(",")):
        qid, _, val = item.strip().partition("=")
        if qid not in known or val not in ("0", "1"):
            sys.exit(f"error: bad result '{item}' (expected <question-id>=0|1 for course {args.course})")
        q = prog["questions"].setdefault(qid, {"attempts": 0, "correct": 0})
        q["attempts"] += 1
        q["correct"] += int(val)
        q["last"] = int(val)
        q["at"] = now()
        recorded.append(qid)
    save_progress(args, prog)
    touched = {known[q]["lesson"] for q in recorded}
    summary = course_summary(path, prog, course)
    print(json.dumps({"recorded": len(recorded),
                      "lessons": [l for l in summary["lessons"] if l["slug"] in touched],
                      "course_percent": summary["percent"]}, indent=2))


def cmd_record_lab(args):
    course = find_course(load_path(), args.course)
    if args.lab not in {x["id"] for x in course.get("labs", [])}:
        sys.exit(f"error: unknown lab '{args.lab}'")
    prog = load_progress(args)
    lab = prog["labs"].setdefault(f"{args.course}/{args.lab}", {"attempts": 0})
    lab["attempts"] += 1
    lab["passed"] = lab.get("passed", False) or not args.failed
    lab["at"] = now()
    save_progress(args, prog)
    print(json.dumps({"lab": args.lab, **lab}))


def cmd_mark_studied(args):
    course = find_course(load_path(), args.course)
    c, l = canonical(course["slug"], find_lesson(course, args.lesson))
    prog = load_progress(args)
    prog["studied"][f"{c}/{l}"] = now()
    save_progress(args, prog)
    print(json.dumps({"lesson": args.lesson, "studied": True, **({"shared_with": c} if c != args.course else {})}))


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

    p = sub.add_parser("status"); p.add_argument("--course"); p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)
    sub.add_parser("next").set_defaults(fn=cmd_next)
    p = sub.add_parser("lessons"); p.add_argument("--course", required=True); p.set_defaults(fn=cmd_lessons)
    p = sub.add_parser("quiz")
    p.add_argument("--course", required=True); p.add_argument("--lesson"); p.add_argument("--module")
    p.add_argument("--n", type=int); p.add_argument("--review", action="store_true")
    p.add_argument("--exam", action="store_true"); p.add_argument("--seed", type=int)
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
