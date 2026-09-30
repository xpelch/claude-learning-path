# Labs: Claude Code in Action

Each lab lists goal, setup, steps for the user, and pass criteria. "Practice repo" = a throwaway git repo or a branch the user agrees to.
`$S` below stands for `${CLAUDE_PLUGIN_ROOT}/scripts`.

---

## session-steering: Plan, compact, rewind and goal on a real task

Lesson: L1.

**Goal:** use the four steering tools deliberately on one multi-step task.

**Steps** (the user, in their own Claude Code session on a practice repo):
1. Pick a task touching several files. Enter **plan mode** (Shift+Tab), get a plan, and make at least one correction to it before approving.
2. Midway, run `/compact` **with instructions** saying what to keep. Write down the instruction used.
3. Deliberately take a wrong turn, then use **rewind** (Esc Esc on an empty prompt) and pick the right restore option (code, conversation, or both). Say why that option.
4. Finish with `/goal <condition>` where the condition is **visible in output** (e.g. a test command's result). Explain why "the code is clean" would be a bad goal.

**Pass when:** the user reports all four steps, the compact instruction is specific, the rewind option choice is justified, and the goal condition is checkable from the transcript.

---

## claude-md-audit: Audit and tighten a CLAUDE.md

Lesson: L2.

**Setup:** use the user's own CLAUDE.md (copy it first) or the fixture `assets/bloated-CLAUDE.md` copied into a practice folder.

**Steps**
1. Run `python3 $S/lint_claude_md.py <file>` and go through the findings together.
2. The user rewrites the file:
   - vague rules become specific and checkable,
   - every ban names its replacement,
   - hard rules move to a hook (write down which hook event and what it blocks; the hook itself is the `hook-guard` lab),
   - at most 2–3 emphasized rules,
   - personal or temporary notes move to `CLAUDE.local.md`.
3. Re-run the linter.

**Pass when:** no `vague`, `hard-rule` or `emphasis` warnings remain, the file is shorter than before, and the user can say which location (managed, user, project, local) each remaining rule belongs in.

---

## verification-skill: Build a verification skill

Lessons: L3 (and the agent-skills course).

**Goal:** a project skill that runs the gates after a change and reports evidence.

**Steps**
1. In a practice repo with tests, the user creates `.claude/skills/verify-changes/SKILL.md` whose description makes it fire when a change is finished (e.g. "Use after implementing or refactoring code, before saying the work is done").
2. Procedure: run the test suite, read `git diff`, **check that no test was weakened or deleted to pass**, report PASS/FAIL with the evidence (commands and results).
3. Put the gate commands in `scripts/check.sh` (or `check.py`) and tell Claude to **run** it, not read it.
4. Lint it: `python3 $S/lint_skill.py .claude/skills/verify-changes`.
5. Live test: ask Claude for a small refactor and see whether the skill fires on its own.

**Pass when:** the linter passes, the skill includes the "tests not weakened" check, gates live in a script, and the live test triggered the skill (or the user tuned the description until it did).

---

## hook-guard: Write a PreToolUse guard that blocks or redacts

Lesson: L5.

**Goal:** a Bash guard that (a) **denies** `git push` to `main`/`master` and (b) **redacts** strings like `sk_live_...` with `updatedInput`, letting the command run.

**Steps**
1. The user writes the hook script (any language): read the event JSON from stdin, inspect `tool_input.command`.
2. Deny case: print `hookSpecificOutput` with `permissionDecision: "deny"` and a reason (exit 0), **or** exit 2 with a reason on stderr. Ask which they chose and why.
3. Redact case: return `updatedInput` with the **full** input (the command with the secret replaced, plus any other fields such as `description`).
4. Test without touching real config:
   - `python3 $S/hook_test.py --event PreToolUse --tool Bash --input '{"command":"git push origin main"}' -- <their command>` → must be **BLOCKED**
   - `--input '{"command":"curl -H \"Authorization: sk_live_abc123\" https://example.com","description":"call api"}'` → must be **REWRITTEN** with no dropped-field warning
   - `--input '{"command":"git status"}'` → must **PROCEED**
5. Ask: "What would exit 1 have done?" (Nothing: non-blocking.)
6. Optional: register it under `hooks.PreToolUse` with matcher `Bash` in a practice repo's `.claude/settings.json` and re-test with `--settings`.

**Pass when:** the three dry runs give BLOCKED / REWRITTEN (no dropped fields) / PROCEEDS, and the user answered step 5 correctly.

---

## stop-hook-gate: Gate the end of a turn on passing tests

Lessons: L4, L5, L8.

**Goal:** Claude can't finish while tests fail.

**Steps**
1. The user writes a Stop hook command that runs the test suite; on failure it prints the failing output to **stderr** and exits **2**; on success it exits 0.
2. It must avoid infinite loops: if the event has `stop_hook_active: true`, consider letting it stop (explain why).
3. Dry-run in a practice repo: make a test fail → `python3 $S/hook_test.py --event Stop -- <command>` must say **BLOCKED** with the failure in stderr. Fix the test → **PROCEEDS**.
4. Ask: "Why pair this with auto mode?" (The classifier checks intent, not correctness.)

**Pass when:** both dry runs behave as expected and the user explains the auto-mode pairing.

---

## headless-json: Headless run with structured JSON output

Lesson: L6.

**Goal:** get machine-readable data out of `claude -p`.

**Steps**
1. The user runs, in a repo of their choice, a command like:
   `claude -p "List the exported function names in <file>" --output-format json --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}'`
2. Extract the result from `.structured_output` (with `jq` or Python) and check the exit code.
3. Capture `session_id` and continue with `claude --resume <id> -p "..."`.
4. Explain what `-p` does not load by default (hooks, skills, plugins, MCP servers, CLAUDE.md) and when they'd use `--bare`, a routine, or the Agent SDK instead.

**Pass when:** the user shows the extracted array, a successful resume, and answers step 4.

---

## github-action: Write an @claude GitHub Actions workflow

Lesson: L7.

**Goal:** a correct workflow file (running it is optional).

**Steps**
1. The user writes `.github/workflows/claude.yaml` in a practice repo: triggers on issue comments and PR review comments; job permissions include `id-token: write` (plus contents/pull-requests/issues as needed); step `anthropics/claude-code-action@v1` with `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}` (or OAuth token / cloud provider), `trigger_phrase: "@claude"`, and `claude_args` with `--max-turns`.
2. Second workflow: a scheduled report (cron + `workflow_dispatch`) with a `prompt` input and read-only tools.
3. Questions: When would you use managed Code Review instead? Can it approve a PR? How do you apply its findings? (`/code-review --fix` locally.)
4. Never put a real key in the file; secrets only.

**Pass when:** both YAML files are syntactically valid, use secrets, cap turns, and the answers to step 3 are right.

---

## package-plugin: Package a .claude setup as a plugin

Lesson: L9 (and the agent-skills course, lesson 5).

**Goal:** turn a working `.claude` setup (a skill plus a hook) into an installable plugin.

**Steps**
1. Create `my-plugin/` with `.claude-plugin/plugin.json` (`name` at minimum, plus `version`), `skills/<skill>/SKILL.md`, and `hooks/hooks.json`.
2. Validate: `claude plugin validate ./my-plugin`, and lint the skills: `python3 $S/lint_skill.py my-plugin/skills`.
3. Try it without installing: `claude --plugin-dir ./my-plugin`, then call the skill as `/<plugin-name>:<skill>`.
4. Questions: What happens if the plugin's PreToolUse hook and yours both match? (Both fire.) What should you check before installing someone else's plugin?

**Pass when:** validation passes, the namespaced skill runs, and step 4 is answered correctly.
