"""Run with: python -m unittest discover -s tests"""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "claude-learning-path"
SCRIPTS = PLUGIN / "scripts"
LP, LINT, HOOK, LINT_MD = (SCRIPTS / n for n in ("lp.py", "lint_skill.py", "hook_test.py", "lint_claude_md.py"))
FIXTURES = REPO / "tests" / "fixtures"
BROKEN = PLUGIN / "skills" / "skill-authoring-lab" / "assets" / "broken"
PATH = json.loads((PLUGIN / "courses" / "path.json").read_text(encoding="utf-8"))
COURSES = {c["slug"]: c for c in PATH["courses"]}
SKILLS_COURSE = "introduction-to-agent-skills"
API = "building-with-the-claude-api"
MCP = "introduction-to-model-context-protocol"
CCA = "claude-code-in-action"


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True, encoding="utf-8")


def lint_codes(path):
    r = run(LINT, path, "--json")
    return r.returncode, {i["code"] for rep in json.loads(r.stdout) for i in rep["items"]}


def bank(slug):
    return json.loads((PLUGIN / "courses" / slug / "questions.json").read_text(encoding="utf-8"))["questions"]


class ContentTests(unittest.TestCase):
    def test_every_course_is_covered(self):
        self.assertEqual(set(COURSES), {SKILLS_COURSE, API, MCP, CCA})
        self.assertTrue(all(c["status"] == "available" for c in COURSES.values()))
        self.assertEqual(sum(len(c["lessons"]) for c in COURSES.values()), 92)

    def test_question_banks(self):
        all_ids = []
        for slug, course in COURSES.items():
            qs = bank(slug)
            all_ids += [q["id"] for q in qs]
            own = {l["slug"] for l in course["lessons"] if not l.get("same_as")}
            for q in qs:
                self.assertIn(q["lesson"], own, q["id"])
                self.assertIn(q["type"], ("mcq", "open"), q["id"])
                self.assertTrue(q["prompt"] and q["answer"] and q["explanation"], q["id"])
                if q["type"] == "mcq":
                    self.assertIn(q["answer"], q["choices"], q["id"])
            for lesson in own:
                self.assertGreaterEqual(sum(q["lesson"] == lesson for q in qs), 3, f"{slug}/{lesson}")
        self.assertEqual(len(all_ids), len(set(all_ids)), "question ids must be unique across courses")

    def test_notes_have_every_lesson(self):
        for slug, course in COURSES.items():
            notes = (PLUGIN / "courses" / slug / "notes.md").read_text(encoding="utf-8")
            for n, l in enumerate(course["lessons"], 1):
                if l.get("same_as"):
                    target_course, target_lesson = l["same_as"].split("/")
                    self.assertIn(target_lesson, [x["slug"] for x in COURSES[target_course]["lessons"]])
                    continue
                self.assertIn(f"## L{n} {l['slug']}", notes, f"{slug}/{l['slug']}")

    def test_modules_are_declared(self):
        api = COURSES[API]
        declared = {m["id"] for m in api["modules"]}
        self.assertEqual({l["module"] for l in api["lessons"]}, declared)

    def test_plugin_skills_lint_clean(self):
        code, codes = lint_codes(PLUGIN / "skills")
        self.assertEqual(code, 0, codes)
        self.assertFalse(codes & {"description-when", "description-short", "bare-bash", "broken-link"}, codes)

    def test_labs_have_instructions(self):
        lab_files = {SKILLS_COURSE: "skill-authoring-lab", API: "claude-api-lab", MCP: "mcp-lab", CCA: "claude-code-lab"}
        for slug, skill in lab_files.items():
            text = (PLUGIN / "skills" / skill / "references" / "labs.md").read_text(encoding="utf-8")
            for lab in COURSES[slug]["labs"]:
                self.assertIn(f"## {lab['id']}:", text, f"{skill}: {lab['id']}")


class LintFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def place(self, case, rel):
        dest = self.tmp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(BROKEN / f"{case}.md", dest)
        return dest

    def test_case1_skills_root(self):
        code, codes = lint_codes(self.place("case-1", "skills/SKILL.md"))
        self.assertEqual(code, 1)
        self.assertIn("skills-root", codes)

    def test_case2_bad_name(self):
        code, codes = lint_codes(self.place("case-2", "skills/pdf-tools/SKILL.md"))
        self.assertEqual(code, 1)
        self.assertTrue({"name-format", "name-dir", "bare-bash"} <= codes, codes)

    def test_case3_vague_description(self):
        code, codes = lint_codes(self.place("case-3", "skills/docs-helper/SKILL.md"))
        self.assertEqual(code, 0)
        self.assertTrue({"description-when", "description-short"} <= codes, codes)

    def test_case4_wrong_filename_link_backslash(self):
        self.place("case-4", "skills/release-notes/skill.md")
        code, codes = lint_codes(self.tmp / "skills" / "release-notes")
        self.assertEqual(code, 1)
        self.assertTrue({"file-name", "broken-link", "backslash-path"} <= codes, codes)

    def test_missing_frontmatter(self):
        d = self.tmp / "skills" / "x"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
        code, codes = lint_codes(d)
        self.assertEqual(code, 1)
        self.assertIn("no-frontmatter", codes)


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.data)

    def lp(self, *args):
        r = run(LP, "--data-dir", self.data, *args)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def all_correct(self, course):
        qs = json.loads(self.lp("quiz", "--course", course, "--n", "1000"))["questions"]
        self.lp("record-quiz", "--course", course, "--results", ",".join(f"{q['id']}=1" for q in qs))

    def test_study_quiz_review_flow(self):
        nxt = json.loads(self.lp("next"))
        self.assertEqual((nxt["action"], nxt["lesson"]), ("study", "what-are-skills"))
        self.lp("mark-studied", "--course", SKILLS_COURSE, "--lesson", "what-are-skills")
        self.assertEqual(json.loads(self.lp("next"))["action"], "quiz")

        qs = json.loads(self.lp("quiz", "--course", SKILLS_COURSE, "--lesson", "what-are-skills", "--n", "10"))["questions"]
        self.assertEqual(len(qs), 5)
        results = ",".join(f"{q['id']}={0 if i == 0 else 1}" for i, q in enumerate(qs))
        out = json.loads(self.lp("record-quiz", "--course", SKILLS_COURSE, "--results", results))
        self.assertTrue(out["lessons"][0]["mastered"])  # 4/5 = 80%

        review = json.loads(self.lp("quiz", "--course", SKILLS_COURSE, "--review"))["questions"]
        self.assertEqual([q["id"] for q in review], [qs[0]["id"]])
        self.assertEqual(json.loads(self.lp("next"))["lesson"], "creating-your-first-skill")

    def test_course_completion_moves_to_next_course(self):
        self.all_correct(SKILLS_COURSE)
        nxt = json.loads(self.lp("next"))
        self.assertEqual((nxt["action"], nxt["lab"]), ("lab", "first-skill"))
        for lab in COURSES[SKILLS_COURSE]["labs"]:
            self.lp("record-lab", "--course", SKILLS_COURSE, "--lab", lab["id"])
        nxt = json.loads(self.lp("next"))
        self.assertEqual((nxt["action"], nxt["course"], nxt["lesson"], nxt["module"]),
                         ("study", API, "accessing-the-api", "api-basics"))

    def test_shared_lessons_share_progress(self):
        self.all_correct(MCP)
        status = json.loads(self.lp("status", "--course", API, "--json"))["courses"][0]
        mcp_lessons = [l for l in status["lessons"] if l["module"] == "mcp"]
        shared = [l for l in mcp_lessons if l["same_as"]]
        self.assertEqual(len(shared), 9)
        self.assertTrue(all(l["mastered"] for l in shared))
        self.assertFalse(next(l for l in mcp_lessons if l["slug"] == "project-setup")["mastered"])
        # Studying a shared lesson from the API course marks the MCP one too.
        self.lp("mark-studied", "--course", API, "--lesson", "mcp-clients")
        mcp = json.loads(self.lp("status", "--course", MCP, "--json"))["courses"][0]
        self.assertTrue(next(l for l in mcp["lessons"] if l["slug"] == "mcp-clients")["studied"])
        # API-course quizzes can record shared questions.
        q = json.loads(self.lp("quiz", "--course", API, "--lesson", "introducing-mcp", "--n", "1"))["questions"][0]
        self.assertTrue(q["id"].startswith("mcp-"))
        self.lp("record-quiz", "--course", API, "--results", f"{q['id']}=0")

    def test_exam_and_module_modes(self):
        exam = json.loads(self.lp("quiz", "--course", CCA, "--exam"))["questions"]
        self.assertEqual(len(exam), len(COURSES[CCA]["lessons"]))
        self.assertEqual(len({q["lesson"] for q in exam}), len(exam))
        big = json.loads(self.lp("quiz", "--course", API, "--exam"))["questions"]
        self.assertEqual(len(big), 20)
        rag = json.loads(self.lp("quiz", "--course", API, "--module", "rag", "--n", "100"))["questions"]
        self.assertEqual(len(rag), 21)
        self.assertTrue(all(q["id"].startswith("api-") for q in rag))

    def test_migrates_v1_progress(self):
        v1 = {"version": 1, "created": "2026-09-30T00:00:00+00:00", "courses": {SKILLS_COURSE: {
            "questions": {"l1-q1": {"attempts": 1, "correct": 1, "last": 1}},
            "lessons": {"what-are-skills": {"studied": True, "at": "2026-09-30T00:00:00+00:00"}},
            "labs": {"first-skill": {"attempts": 1, "passed": True}}}}}
        Path(self.data, "progress.json").write_text(json.dumps(v1), encoding="utf-8")
        c = json.loads(self.lp("status", "--course", SKILLS_COURSE, "--json"))["courses"][0]
        self.assertTrue(c["lessons"][0]["studied"])
        self.assertEqual(c["lessons"][0]["correct"], 1)
        self.assertTrue(c["labs"][0]["passed"])

    def test_rejects_bad_input(self):
        self.assertNotEqual(run(LP, "--data-dir", self.data, "record-quiz", "--course", SKILLS_COURSE,
                                "--results", "nope=1").returncode, 0)
        self.assertNotEqual(run(LP, "--data-dir", self.data, "record-quiz", "--course", SKILLS_COURSE,
                                "--results", "api-l1-q1=1").returncode, 0)
        self.assertNotEqual(run(LP, "--data-dir", self.data, "quiz", "--course", API, "--module", "nope").returncode, 0)


class HookTestTests(unittest.TestCase):
    def hook(self, event, tool_input, *cmd):
        r = run(HOOK, "--event", event, "--tool", "Bash", "--input", json.dumps(tool_input), "--", *cmd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    guard = (sys.executable, str(FIXTURES / "guard.py"))

    def test_block_rewrite_proceed(self):
        self.assertIn("result: BLOCKED", self.hook("PreToolUse", {"command": "git push origin main"}, *self.guard))
        out = self.hook("PreToolUse", {"command": "curl -H sk_live_abc x", "description": "d"}, *self.guard)
        self.assertIn("result: REWRITTEN", out)
        self.assertIn("fields dropped: description", out)
        self.assertIn("result: PROCEEDS", self.hook("PreToolUse", {"command": "git status"}, *self.guard))

    def test_exit_1_does_not_block(self):
        out = self.hook("PreToolUse", {"command": "x"}, sys.executable, "-c", "import sys; sys.exit(1)")
        self.assertIn("exit code: 1", out)
        self.assertNotIn("SyntaxError", out)
        self.assertIn("NON-BLOCKING", out)
        self.assertIn("result: PROCEEDS", out)

    def test_stop_hook_exit_2_blocks(self):
        out = self.hook("Stop", {}, sys.executable, "-c", "import sys; print('2 tests failed', file=sys.stderr); sys.exit(2)")
        self.assertIn("result: BLOCKED", out)
        self.assertIn("2 tests failed", out)


class ClaudeMdLintTests(unittest.TestCase):
    def test_bloated_fixture(self):
        r = run(LINT_MD, PLUGIN / "skills" / "claude-code-lab" / "assets" / "bloated-CLAUDE.md", "--json")
        codes = {i["code"] for i in json.loads(r.stdout)["items"]}
        self.assertTrue({"vague", "hard-rule", "emphasis", "no-replace"} <= codes, codes)

    def test_tight_file_is_clean(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "CLAUDE.md").write_text(
                "# Conventions\n- Put new API routes in `src/api/handlers`, one per file.\n"
                "- Use named exports, not default exports.\n- Run `npm test` before saying a change is done.\n",
                encoding="utf-8")
            r = run(LINT_MD, tmp / "CLAUDE.md", "--json")
            self.assertEqual(json.loads(r.stdout)["items"], [])
        finally:
            shutil.rmtree(tmp)


class LabAssetTests(unittest.TestCase):
    def test_retrieval_exercise_is_solvable(self):
        spec = importlib.util.spec_from_file_location(
            "retrieval", PLUGIN / "skills" / "claude-api-lab" / "assets" / "retrieval_exercise.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def rrf_scores(rankings, k=60):
            s = {}
            for ranking in rankings:
                for rank, d in enumerate(ranking, 1):
                    s[d] = s.get(d, 0) + 1 / (k + rank)
            return s

        mod.chunk_by_section = lambda text: re.split(r"\n## ", text)
        mod.rrf_scores = rrf_scores
        mod.fuse = lambda rankings, k=60: sorted(rrf_scores(rankings, k), key=lambda d: -rrf_scores(rankings, k)[d])
        chunks = mod.chunk_by_section(mod.REPORT)
        self.assertEqual(len(chunks), 5)
        self.assertEqual(mod.fuse([["s2", "s7", "s6"], ["s6", "s2", "s7"]], k=1), ["s2", "s6", "s7"])
        index = mod.BM25Index()
        for i, c in enumerate(chunks):
            index.add_document({"id": f"s{i + 1}", "content": c})
        top = {d["id"] for d, _ in index.search("What happened with INC-2023-Q4-011?", k=2)}
        self.assertEqual(top, {"s2", "s4"})

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "mcp SDK not installed")
    def test_mcp_checker_on_reference_server(self):
        r = run(PLUGIN / "skills" / "mcp-lab" / "scripts" / "check_server.py", FIXTURES / "mcp_solution_server.py",
                "--expect-tools", "read_doc_contents,edit_document",
                "--expect-resources", "docs://documents", "--expect-templates", "docs://documents/{doc_id}",
                "--expect-prompts", "format",
                "--call", "read_doc_contents", '{"doc_id":"roadmap.md"}',
                "--read", "docs://documents", "--get-prompt", "format", '{"doc_id":"plan.md"}')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)
        bad = run(PLUGIN / "skills" / "mcp-lab" / "scripts" / "check_server.py", FIXTURES / "mcp_solution_server.py",
                  "--call", "read_doc_contents", '{"doc_id":"nope"}')
        self.assertEqual(bad.returncode, 1)

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "mcp SDK not installed")
    def test_mcp_starters_import(self):
        for name in ("server_starter.py", "client_starter.py"):
            r = subprocess.run([sys.executable, "-c", f"import runpy; runpy.run_path(r'{PLUGIN / 'skills' / 'mcp-lab' / 'assets' / name}', run_name='x')"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
