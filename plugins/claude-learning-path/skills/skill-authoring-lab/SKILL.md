---
name: skill-authoring-lab
description: Hands-on labs for the Introduction to agent skills course, plus a linter for any SKILL.md. Guides the user through building, tuning, splitting and debugging real Claude Code skills, and checks skill files for structure, naming, description and path problems. Use when the user wants a skills lab or exercise, wants to practice writing agent skills, asks to lint, validate or check a SKILL.md or a skills folder, or asks why a skill doesn't trigger or load.
allowed-tools:
  - Read
  - Glob
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_skill.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lint_skill.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
---

# Skill authoring lab

Two jobs: **lint** skill files on request, and **run labs** that make the user practice what the course teaches. Run the scripts; don't read their source. Use `python3`, or `python` if `python3` fails (Windows).

## Lint a skill

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_skill.py" <SKILL.md | skill dir | skills root> [--json]
```

Report errors first, then warnings, each with the concrete fix. `info` items are optional. Linting passes when there are no errors. The linter is structural; it cannot prove a description triggers. For that, use the description-tuning lab method: realistic phrasings, then check whether the skill activates.

## Run a lab

The lab list is in `${CLAUDE_PLUGIN_ROOT}/courses/path.json` (course `introduction-to-agent-skills`). Full instructions per lab are in [references/labs.md](references/labs.md); read only the section for the chosen lab. If the user doesn't pick one, suggest the first lab not yet passed. Get progress with:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" status
```

How to run a lab:
1. State the goal and the success criteria from `labs.md`.
2. **The user does the work.** Give hints and review, but don't write the solution unless they ask to see it (then the lab doesn't count as passed).
3. Ask before creating files; create lab files where the lab says, and never overwrite an existing skill.
4. Check the result against the criteria, using the linter where the lab says so.
5. Record the outcome automatically:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" record-lab --course introduction-to-agent-skills --lab <id> [--failed]
```

6. Offer to clean up any lab files created outside the user's own projects.

Broken-skill fixtures for the `broken-skills` lab are in `assets/broken/`. Copy them as the lab explains; don't show their content to the user before they have diagnosed them.
