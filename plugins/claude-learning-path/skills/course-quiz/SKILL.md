---
name: course-quiz
description: Interactive quiz on the Claude Partner Network learning path courses (currently Introduction to agent skills). Asks one question at a time, grades the answer, explains it, and records the score automatically. Use when the user says quiz me, test me, check my understanding, practice questions, review what I got wrong, or wants to test their knowledge of agent skills, SKILL.md, or a lesson of an Anthropic Academy course.
allowed-tools:
  - Read
  - Grep
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
---

# Course quiz

Run a short, friendly quiz and record the results. Run the script; do not read `lp.py` or the question bank file directly. Use `python3`, or `python` if `python3` fails (Windows).

## 1. Pick the questions

Work out the course and, if the user named one, the lesson. Course and lesson slugs are in `${CLAUDE_PLUGIN_ROOT}/courses/path.json`. With no lesson given, quiz the whole course. If the user asks to review mistakes, add `--review`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" quiz --course introduction-to-agent-skills [--lesson <slug>] [--n 5] [--review]
```

The JSON includes answers and explanations **for your grading only**. Never show an answer before the user replies.

## 2. Ask one question at a time

- `mcq`: show the prompt and lettered choices, then wait. Accept a letter or the choice text.
- `open`: show the prompt and wait. Grade against the key points in `answer`. Count it correct (1) when the essential ideas are there even if worded differently; count it wrong (0) when a key idea is missing or wrong. Say which point was missing.
- After each answer: say correct or not, give the explanation in one or two sentences, then move on. If the user seems confused, you may read the matching lesson section of `${CLAUDE_PLUGIN_ROOT}/courses/<course>/notes.md` (headings `## L<n> <lesson-slug>`) to explain further.
- If the user stops early, record only the questions they actually answered.

## 3. Record the results (automatic, always)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" record-quiz --course introduction-to-agent-skills --results l1-q1=1,l1-q2=0
```

Use `1` for correct and `0` for wrong, with the question ids from step 1.

## 4. Wrap up

Show the score (e.g. 4/5), the lessons whose mastery changed (from the script output), and one next step: review the missed topic, quiz another lesson, or run a hands-on lab. Suggest `--review` when there were misses.
