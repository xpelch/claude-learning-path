# claude-learning-path

A Claude Code plugin that turns Claude into a study companion for the
[Claude Partner Network learning path](https://anthropic.skilljar.com/page/claude-partner-network-learning-path)
on Anthropic Academy. It tracks your progress, quizzes you, and runs hands-on labs.

> Unofficial community project, not affiliated with or endorsed by Anthropic.
> The study notes and questions are original summaries; take the real (free) courses on
> [Anthropic Academy](https://academy.claude.com/courses).

## Install

In your shell:

```bash
claude plugin marketplace add xpelch/claude-learning-path
claude plugin install claude-learning-path@xpelch
```

Or inside a Claude Code session: `/plugin marketplace add xpelch/claude-learning-path`, then `/plugin install claude-learning-path@xpelch`.

The scripts need Python 3.8+ (standard library only).

## What's inside

Three skills that trigger automatically from natural requests. You can also call them directly, e.g. `/claude-learning-path:course-quiz`.

| Skill | What it does | Try saying |
| --- | --- | --- |
| `learning-path-coach` | Progress, next step, lesson and course recaps | "Where am I in the Claude learning path?", "What should I study next?", "Recap the lesson on sharing skills" |
| `course-quiz` | One-question-at-a-time quiz, graded and explained, with a review mode for missed questions | "Quiz me on agent skills", "Test me on troubleshooting skills", "Review what I got wrong" |
| `skill-authoring-lab` | Six hands-on labs, plus a linter for any `SKILL.md` | "Give me a skills lab", "Lint my skills folder", "Why doesn't my skill trigger?" |

Progress is recorded automatically after each recap, quiz and lab, in the plugin's persistent data directory
(`$CLAUDE_PLUGIN_DATA/progress.json`, falling back to `~/.claude/claude-learning-path/`). A lesson is **mastered**
when at least 80% of its questions were answered correctly on their latest attempt.

## Course coverage

| # | Course | Status |
| --- | --- | --- |
| 1 | Introduction to agent skills | ✅ notes, 30 questions, 6 labs |
| 2 | Building with the Claude API | planned |
| 3 | Introduction to Model Context Protocol | planned |
| 4 | Claude Code in Action | planned |

Planned courses already appear in the coach's progress view, with a link to the course.

## Repository layout

```
.claude-plugin/marketplace.json          marketplace "xpelch" (this repo)
plugins/claude-learning-path/
  .claude-plugin/plugin.json
  courses/path.json                      courses, lessons, labs, mastery threshold
  courses/<course>/notes.md              study notes, one "## L<n> <lesson>" section per lesson
  courses/<course>/questions.json        question bank (mcq + open)
  scripts/lp.py                          progress tracker: status, next, quiz, record-*
  scripts/lint_skill.py                  SKILL.md linter
  skills/learning-path-coach/
  skills/course-quiz/
  skills/skill-authoring-lab/            + references/labs.md, assets/broken/ fixtures
tests/test_plugin.py
```

The design follows what the course teaches: skills are organized by **action** (coach, quiz, lab) rather than one per
course, so descriptions stay distinct. Course material loads through **progressive disclosure**, only the
lesson needed. Deterministic work (progress, question selection, linting) is done by **scripts that Claude runs
without reading**.

## Adding a course

1. Set its `status` to `available` in `courses/path.json` and list its `lessons` (and `labs`).
2. Add `courses/<slug>/notes.md` with a `## L<n> <lesson-slug>` section per lesson.
3. Add `courses/<slug>/questions.json` (at least 3 questions per lesson).
4. Optionally add a `<topic>-lab` skill for hands-on practice.
5. Run the checks below.

## Development

```bash
python -m unittest discover -s tests
python plugins/claude-learning-path/scripts/lint_skill.py plugins/claude-learning-path/skills
claude plugin validate .
claude --plugin-dir ./plugins/claude-learning-path
```

## License

MIT
