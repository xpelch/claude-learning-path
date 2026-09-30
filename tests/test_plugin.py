"""Run with: python -m unittest discover -s tests"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugins" / "claude-learning-path"
LP = PLUGIN / "scripts" / "lp.py"
LINT = PLUGIN / "scripts" / "lint_skill.py"
BROKEN = PLUGIN / "skills" / "skill-authoring-lab" / "assets" / "broken"
COURSE = "introduction-to-agent-skills"


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True, encoding="utf-8")


def lint_codes(path):
    r = run(LINT, path, "--json")
    return r.returncode, {i["code"] for rep in json.loads(r.stdout) for i in rep["items"]}


class ContentTests(unittest.TestCase):
    def test_path_and_questions_are_consistent(self):
        path = json.loads((PLUGIN / "courses" / "path.json").read_text(encoding="utf-8"))
        for course in path["courses"]:
            if course["status"] != "available":
                continue
            lessons = {l["slug"] for l in course["lessons"]}
            qs = json.loads((PLUGIN / "courses" / course["slug"] / "questions.json").read_text(encoding="utf-8"))["questions"]
            ids = [q["id"] for q in qs]
            self.assertEqual(len(ids), len(set(ids)), "duplicate question ids")
            for q in qs:
                self.assertIn(q["lesson"], lessons, q["id"])
                self.assertIn(q["type"], ("mcq", "open"), q["id"])
                if q["type"] == "mcq":
                    self.assertIn(q["answer"], q["choices"], q["id"])
            for lesson in lessons:
                self.assertGreaterEqual(sum(q["lesson"] == lesson for q in qs), 3, lesson)
            notes = (PLUGIN / "courses" / course["slug"] / "notes.md").read_text(encoding="utf-8")
            for n, l in enumerate(course["lessons"], 1):
                self.assertIn(f"## L{n} {l['slug']}", notes)

    def test_plugin_skills_lint_clean(self):
        code, codes = lint_codes(PLUGIN / "skills")
        self.assertEqual(code, 0, codes)
        self.assertFalse(codes & {"description-when", "description-short", "bare-bash", "broken-link"}, codes)


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
        f = self.place("case-1", "skills/SKILL.md")
        code, codes = lint_codes(f)
        self.assertEqual(code, 1)
        self.assertIn("skills-root", codes)

    def test_case2_bad_name(self):
        f = self.place("case-2", "skills/pdf-tools/SKILL.md")
        code, codes = lint_codes(f)
        self.assertEqual(code, 1)
        self.assertTrue({"name-format", "name-dir", "bare-bash"} <= codes, codes)

    def test_case3_vague_description(self):
        f = self.place("case-3", "skills/docs-helper/SKILL.md")
        code, codes = lint_codes(f)
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

    def test_full_flow(self):
        nxt = json.loads(self.lp("next"))
        self.assertEqual((nxt["action"], nxt["lesson"]), ("study", "what-are-skills"))

        self.lp("mark-studied", "--course", COURSE, "--lesson", "what-are-skills")
        self.assertEqual(json.loads(self.lp("next"))["action"], "quiz")

        qs = json.loads(self.lp("quiz", "--course", COURSE, "--lesson", "what-are-skills", "--n", "10"))["questions"]
        self.assertEqual(len(qs), 5)
        results = ",".join(f"{q['id']}={0 if i == 0 else 1}" for i, q in enumerate(qs))
        out = json.loads(self.lp("record-quiz", "--course", COURSE, "--results", results))
        self.assertTrue(out["lessons"][0]["mastered"])  # 4/5 = 80%

        review = json.loads(self.lp("quiz", "--course", COURSE, "--review"))["questions"]
        self.assertEqual([q["id"] for q in review], [qs[0]["id"]])

        self.assertEqual(json.loads(self.lp("next"))["lesson"], "creating-your-first-skill")

    def test_labs_and_completion(self):
        qs = json.loads(self.lp("quiz", "--course", COURSE, "--n", "100"))["questions"]
        self.lp("record-quiz", "--course", COURSE, "--results", ",".join(f"{q['id']}=1" for q in qs))
        nxt = json.loads(self.lp("next"))
        self.assertEqual((nxt["action"], nxt["lab"]), ("lab", "first-skill"))
        for lab in ("first-skill", "description-tuning", "allowed-tools", "progressive-disclosure",
                    "subagent-skills", "broken-skills"):
            self.lp("record-lab", "--course", COURSE, "--lab", lab)
        nxt = json.loads(self.lp("next"))
        self.assertEqual((nxt["action"], nxt["course"]), ("take-course-externally", "claude-with-the-anthropic-api"))
        self.assertIn("100%", self.lp("status"))

    def test_rejects_bad_input(self):
        r = run(LP, "--data-dir", self.data, "record-quiz", "--course", COURSE, "--results", "nope=1")
        self.assertNotEqual(r.returncode, 0)
        r = run(LP, "--data-dir", self.data, "quiz", "--course", "claude-code-in-action")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
