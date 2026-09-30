---
name: course-quiz
description: Interactive quiz and mock exam for the Claude Partner Network learning path — agent skills, Building with the Claude API, Model Context Protocol, Claude Code in Action (280 questions). Asks one question at a time, grades and explains, and records the score automatically. Use when the user says quiz me, test me, check my understanding, practice questions, mock exam, final assessment, review what I got wrong, or wants to test their knowledge of a lesson, module or course from these Anthropic Academy courses.
allowed-tools:
  - Read
  - Grep
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
---

# Course quiz

Run a short, friendly quiz and record the results. Run the script; don't read `lp.py` or the question banks directly. Use `python3`, or `python` if `python3` fails (Windows).

## 1. Pick the questions

Work out the course and optionally a lesson or module. Slugs come from `lp.py lessons --course <slug>`. Courses: `introduction-to-agent-skills`, `building-with-the-claude-api` (modules `api-basics`, `evals`, `prompt-engineering`, `tool-use`, `rag`, `features`, `mcp`, `agents`), `introduction-to-model-context-protocol`, `claude-code-in-action`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" quiz --course <slug> [--lesson <slug> | --module <id>] [--n 5]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" quiz --course <slug> --review     # missed questions only
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" quiz --course <slug> --exam       # one question per lesson, up to 20
```

Defaults: 5 questions; missed questions come first, then unseen ones. Use `--exam` for "mock exam" or "final assessment" requests. It works on a module too. The JSON includes answers and explanations **for your grading only**. Never show an answer before the user replies.

## 2. Ask one question at a time

- `mcq`: show the prompt and lettered choices, then wait. Accept a letter or the choice text.
- `open`: show the prompt and wait. Grade against the key points in `answer`: correct (1) when the essential ideas are there in any wording, wrong (0) when a key idea is missing or wrong. Say what was missing.
- After each answer: correct or not, the explanation in one or two sentences, next question. In exam mode, hold explanations until the end unless asked.
- If the user is confused, read the matching section of `${CLAUDE_PLUGIN_ROOT}/courses/<course>/notes.md` (heading `## L<n> <lesson-slug>`; for API-course MCP lessons, the MCP course's notes) to explain.
- If the user stops early, record only what they answered.

## 3. Record the results (automatic, always)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" record-quiz --course <slug> --results <id>=1,<id>=0
```

`1` = correct, `0` = wrong, with the question ids from step 1 and the same course slug.

## 4. Wrap up

Show the score (e.g. 4/5 or 16/20), the lessons whose mastery changed (from the script output), and one next step: review a missed topic, `--review`, another lesson or module, or a hands-on lab.
