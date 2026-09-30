# Claude Code in Action — study notes

Original study notes written for this plugin; they summarize the course and are not a copy of it.
Take the actual course (free) at https://academy.claude.com/courses/claude-code-in-action.

Each lesson section starts with `## L<n> <lesson-slug>`. The course's theme: running **long, hands-off Claude Code sessions you can trust**. That means steering, configuring, automating, then verifying.

> Commands, flags and limits evolve quickly (several features are research previews). Check the Claude Code docs for current behaviour.

---

## L1 steering-long-sessions — Steering long sessions

Two habits: **scope before Claude starts**, **steer while it runs**.

- **Plan mode**: Claude researches read-only and proposes a plan. *Read the plan properly* and iterate on it; fixing a plan is cheaper than cleaning up a bad run.
- **`/compact <instructions>`** summarizes the conversation and replaces it with the summary, freeing context. Always say what to keep, e.g. `/compact Focus on the --version flag implementation`, or important details may be dropped.
- **Rewind** (double Esc on an empty prompt): every prompt is a checkpoint. Options: restore code and conversation, conversation only, code only, **summarize from here** (compress a side-quest after the checkpoint), **summarize up to here** (compress a long setup before it).
- **`/goal <condition>`**: Claude keeps working across turns until a fast evaluator confirms the condition. The evaluator **only reads the transcript**, so the condition must be visible in output (e.g. test results). `/goal clear` cancels.
- **`/loop`**: runs a prompt on an interval (fixed or self-paced) to watch something external (CI, a deploy); Esc stops it.
- **Worktrees** for parallel sessions: each session gets its own file tree, so they don't clobber each other. Clean worktrees are removed on exit. A **`.worktreeinclude`** file lists git-ignored files (like `.env`) to copy into each worktree.

## L2 a-claude-md-that-follows — A CLAUDE.md that follows

- CLAUDE.md is **guidance, not enforced configuration**. Every line competes for attention, so **the leaner the file, the more of it is followed**.
- **Hard rules belong in hooks** (e.g. "never push to main" → a PreToolUse hook that blocks it). CLAUDE.md keeps the softer conventions.
- **Four locations**, all loaded together at launch: **managed policy** (org, can't be excluded), **user** (you, every project), **project** (shared in the repo), **local** (you, this repo only, git-ignored; good for personal notes during a refactor).
- **Imports** (`@path/to/file.md`) organize a long file, but imported files are **expanded inline at launch**. They **don't reduce** context.
- Phrasing rules:
  - **Specific and checkable** ("put new API routes in `src/api/handlers`, one per file", not "follow best practices").
  - **Name the replacement** ("use named exports, not default exports", not just "don't use default exports").
  - **Emphasis is a budget**: IMPORTANT/MUST only work relative to quieter lines, so spend them on the 2–3 rules that hurt most.
- Keep it under revision: when Claude gets something wrong, treat it as a bug report against CLAUDE.md ("add that to CLAUDE.md"). If you can't justify a line, delete it.

## L3 verification-skills — Verification skills

- The first skill worth building is one that **verifies Claude's own work**, so checking doesn't depend on you remembering to ask.
- Shape: its description matches finished changes, so it fires on its own → **runs the tests** → **reads the diff** → **checks that no test was weakened** to pass → **reports pass/fail with evidence**. "Done" means gates run and observed, not "the code looks right".
- Same shape fits any repeated procedure (release checklist, migration recipe, pre-PR check). If you've typed the same multi-step instruction twice, make it a skill.
- The skill folder can hold a `reference.md` (read only when needed) and **scripts** (e.g. `check.sh`) that are **executed, not loaded** into context. Keep `SKILL.md` lean.
- Where rules live: always-on conventions → **CLAUDE.md**; task procedures → **skills**; must-not-skip rules → **hooks** (code that runs, not instructions).
- Commit it to `.claude/skills` so the whole team gets the same checks.

## L4 permission-modes — Permission modes

Six modes, each drawing a different line between "runs freely" and "asks first":

| Mode | Behaviour |
| --- | --- |
| **Manual** | Reads run without asking; everything else asks. |
| **Accept edits** | Reads, file edits and common filesystem commands run; for iterating when you review afterwards. |
| **Plan** | Researches and proposes, edits nothing (with auto available, its classifier can approve exploration commands). |
| **Auto** | Everything runs, but a **separate classifier model reviews each action** first. |
| **Don't ask** | Only **pre-approved** tools run; everything else is **auto-denied**, with no prompt. |
| **Bypass permissions** | No checks at all (like `--dangerously-skip-permissions`). **Only in an isolated container or VM.** |

- **Shift+Tab** cycles the everyday modes; the status bar shows the current one.
- The auto classifier guards **intent**: it blocks things like production deploys/migrations, force pushes, piping downloads into a shell, sending sensitive data out, and irreversibly deleting pre-existing files. It allows local edits, lockfile installs, reads, and pushing your own branch.
- It does **not** check correctness (broken code isn't dangerous). Pair auto with a **Stop hook that runs the tests**: intent is checked before each action, correctness after.
- **Don't ask** fits unattended runs (CI, cron, overnight batches): nothing hangs waiting for approval.

## L5 hooks — Hooks

- A hook is **deterministic code at a fixed point in the loop**. It turns "Claude usually does X" into "Claude can't skip X".
- Key events (out of ~30): **PreToolUse** (before a tool call; the enforcement point), **PostToolUse** (after a successful call; formatting, lint), **Stop** / **SubagentStop** (when Claude wants to end; can refuse), **PreCompact** / **PostCompact**, **InstructionsLoaded** (audit which CLAUDE.md/rules loaded), **SessionStart** (prime the environment; `startup` source for fresh starts only).
- To **re-inject context after compaction**, use **SessionStart with the `compact` matcher** (not PostCompact): its output goes back into the conversation.
- **PreToolUse JSON** (print it and exit 0): `hookSpecificOutput.permissionDecision` = `allow` | `deny` | `ask` (plus `defer` for non-interactive `-p` runs), with `permissionDecisionReason`. **`updatedInput`** rewrites the call instead of blocking (e.g. redact a secret), but it **replaces the whole input**, so echo back the fields you don't change.
- **Exit codes** (for hooks that don't return JSON):
  - **0** = success (stdout JSON is parsed; plain text is added to context only on SessionStart, UserPromptSubmit and UserPromptExpansion).
  - **2** = **blocking error**; stderr is fed back to Claude.
  - **Anything else, including 1** = non-blocking; logged, and Claude carries on. **Use 2 to block, not 1.**
- Exit 2 on **Stop** keeps Claude working. On **PostToolUse** the tool already ran (too late to stop it, but the feedback reaches Claude). Some events (Notification, SessionStart) ignore blocking.
- Matchers pick the tool (e.g. `Bash`); an optional `if` narrows to specific commands.
- Pattern: a Bash guard that spots `sk_live_...` and **redacts** it via `updatedInput` so the command still runs without leaking the secret.

## L6 routines-and-headless — Routines and headless

A spectrum from "build nothing" to "full control":

- **Routines**: a saved **prompt + repository + connectors** that runs on **Anthropic's cloud**, triggered by **cron**, an **HTTP POST** to its endpoint, or a **GitHub event**. Create at `claude.ai/code/routines` or with `/schedule <plain-language request>`.
  - Limits: research preview; recurring schedules at most **hourly**; each run starts from a **fresh clone of the default branch**, pushes freely to `claude/` branches, and other pushes are checked (refused for protected branches, others' open PRs, or others' commits). Keep `main` protected.
- **Headless `claude -p "..."`**: one-shot, reads stdin and writes stdout, pipes like any CLI tool. It **skips auto-discovery** of hooks, skills, plugins, MCP servers and CLAUDE.md (you get only what you allow explicitly), and starts faster.
  - **Structured output**: `--output-format json --json-schema '<schema>'`; the matching object is in **`structured_output`** (e.g. `jq '.structured_output.functions'`).
  - **Multi-step**: capture `session_id` from the JSON and continue with `claude --resume <id>`.
  - **`--bare`**: deterministic mode for CI when you need repeatable results.
- **Agent SDK** (TypeScript/Python): embed Claude Code in your app through a `query` function with options (`allowedTools`, system prompt, permission mode), and iterate over streamed messages.
- Decision: routines by default → `-p` when the job needs your pipeline → `--bare` for repeatable CI → Agent SDK when it belongs in your product.

## L7 github-actions-and-code-review — GitHub Actions and Code Review

- **Code Review (managed)**: an Anthropic-hosted service through the Claude GitHub app. An org admin enables it in Claude Code admin settings and picks repos and timing (on PR open, on every push, or on an `@claude review` comment). Review agents analyze the diff **against the whole codebase** and post **inline, severity-tagged findings**, deduplicated and ranked, with a summary in the check run.
  - It **never approves or blocks** a PR and has **no managed autofix**. Apply fixes locally with `/code-review --fix`. Research preview, Team and Enterprise plans.
- **GitHub Action (DIY)**, for anything beyond review (implement from a comment, scheduled reports, any event): set up with `/install-github-app` (needs repo admin; installs the app and the API key secret). Action `anthropics/claude-code-action@v1`.
  - Inputs: `anthropic_api_key` (or `claude_code_oauth_token`, or workload identity federation), `github_token` (optional override), `trigger_phrase` (default `@claude`), `use_bedrock` / `use_vertex` / `use_foundry`, `prompt` (set it to run automatically on the event instead of waiting for a mention), `claude_args` (CLI flags).
  - Workflow in `.github/workflows/claude.yaml` listening to PR and issue comments; grant `id-token: write`. A cron schedule (plus `workflow_dispatch` for manual runs) serves daily reports.
  - Tune with `claude_args`: `--max-turns` caps the loop, a non-prompting permission mode for unattended runs, and minimal allowed tools (read-only for reports).
- Rule: managed Code Review for reviews; the Action when Claude must *do* something in CI.

## L8 trust-it-verifying-unsupervised-runs — Trust it: verifying unsupervised runs

- **Verify in proportion to how little you watched.**
- Keep unattended work runs in **auto mode rather than bypass**: the classifier still screens dangerous actions (but never judges correctness).
- **Start from the diff, not the summary**: run `/code-review`, then read `git diff` yourself. Check the planned files first, then anything **outside** the plan. A tidy summary proves nothing.
- Make tests a **gate, not a promise**: a **Stop hook** that runs tests and blocks on failure, and a **PostToolUse hook** that lints and type-checks after edits. **Exit 2** feeds failures back so Claude fixes them without being asked.
- Verify headless runs by their **JSON result and exit code**.
- Get a **cold second opinion**: a fresh session or subagent with no memory of how the code was built reviews it and catches what the author rationalized.

## L9 plugins — Plugins

- A **plugin** is one installable, versioned unit bundling skills, subagents, hooks, MCP server configs, and more (LSP servers, monitors, themes, a narrow `settings.json`).
- Install in-session: `/plugin install <name>@<marketplace>` (e.g. `github@claude-plugins-official`); Claude Code reloads plugins for you (`/reload-plugins --force` if it warns about re-reading the conversation).
- Teams add a (private) **marketplace** once: `/plugin marketplace add your-org/claude-plugins`, for central discovery, versions and updates. Browse in the Discover tab.
- **Read before you install**: a plugin runs code **with your privileges**, and its hooks fire on every matching call, whether or not you wanted them. Check its details (components, context cost). Community marketplace entries pass automated review; the official marketplace is curated separately, but **reviewed ≠ trusted**.
- Components run **alongside** yours: **hooks stack** (both fire); skills, agents and commands are **namespaced** (`/plugin-name:skill`). A plugin `settings.json` honours only the `agent` and subagent status-line keys, and `agent` can promote a plugin subagent to the main thread (changing default behaviour).
- **Packaging**: reuse the `.claude` layout (one folder per skill, `agents/*.md`, `hooks/hooks.json`, `.mcp.json` at the root). Components are discovered by convention.
- Optional manifest `.claude-plugin/plugin.json` (name, version, description, author); **name is the only required field** and namespaces the skills. Version it like a dependency.
