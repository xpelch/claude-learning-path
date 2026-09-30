---
name: claude-code-lab
description: Hands-on labs for the Claude Code in Action course, plus two checkers. Guides the user through steering long sessions, tightening a CLAUDE.md, building a verification skill, writing PreToolUse and Stop hooks, headless runs with JSON output, a GitHub Actions workflow and packaging a plugin. Use when the user wants a Claude Code lab or exercise, asks to audit or tighten their CLAUDE.md, or wants to test or debug a Claude Code hook (exit codes, permissionDecision, updatedInput).
allowed-tools:
  - Read
  - Glob
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_claude_md.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lint_claude_md.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hook_test.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/hook_test.py" *)
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
---

# Claude Code lab

Practise the *Claude Code in Action* course on the user's real setup. Run the scripts; don't read their source. Use `python3`, or `python` if `python3` fails (Windows).

## Checkers (usable on their own)

**Audit a CLAUDE.md**: flags size (imports included), vague rules, bans with no replacement, hard rules that belong in hooks, emphasis overuse, broken imports:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint_claude_md.py" <path/to/CLAUDE.md>
```

**Dry-run a hook** against a synthetic event and explain what Claude Code would do (exit 0/2/other, `permissionDecision`, `updatedInput` dropping fields):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hook_test.py" --event PreToolUse --tool Bash --input '{"command":"git push origin main"}' -- <hook command>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hook_test.py" --event PreToolUse --tool Bash --input '{...}' --settings .claude/settings.json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hook_test.py" --event Stop --settings .claude/settings.json
```

It approximates Claude Code's rules for learning; confirm in a real session when it matters.

## Labs

The lab list is in `${CLAUDE_PLUGIN_ROOT}/courses/path.json` (course `claude-code-in-action`). Instructions are in [references/labs.md](references/labs.md); read only the chosen lab's section. With no choice given, suggest the first lab not yet passed (`lp.py status --course claude-code-in-action`).

1. State the goal and pass criteria.
2. **The user does the work**; you hint and review. Showing the solution on request means the lab doesn't count.
3. **Ask before changing the user's real configuration** (`.claude/settings.json`, hooks, CLAUDE.md, workflows). Prefer a throwaway repo or a branch, never overwrite without a backup, and never enable bypass permissions outside a container or VM.
4. Verify against the criteria, using the checkers where the lab says.
5. Record the outcome:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" record-lab --course claude-code-in-action --lab <id> [--failed]
```

6. Offer to undo lab-only changes.

Background for explanations: `${CLAUDE_PLUGIN_ROOT}/courses/claude-code-in-action/notes.md` (sections `## L<n> <lesson-slug>`).
