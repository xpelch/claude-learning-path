# Introduction to agent skills — study notes

Original study notes written for this plugin; they summarize the course and are not a copy of it.
Take the actual course (free) at https://academy.claude.com/courses/introduction-to-agent-skills.

Each lesson section starts with `## L<n>` so a single lesson can be located with a search for its heading.

---

## L1 what-are-skills — What are skills?

**Core idea:** a skill is written guidance you give Claude once, which Claude then applies on its own whenever a task matches. It replaces re-explaining the same standards (review checklists, commit formats, style rules) in every prompt.

- A skill is a **folder** whose entry point is a file named `SKILL.md`.
- `SKILL.md` starts with YAML **frontmatter** holding at least a `name` and a `description`; the instructions follow below the closing `---`.
- The **description is the trigger**: Claude compares each request with the descriptions of the available skills and activates the ones whose meaning matches.
- Where skills live:
  - **Personal**: `~/.claude/skills/` (on Windows `C:/Users/<you>/.claude/skills/`) and available in every project.
  - **Project**: `.claude/skills/` at the repository root, committed so everyone who clones the repo gets them.
- How skills differ from neighbouring features:
  - `CLAUDE.md` is loaded into **every** conversation, so it suits always-true rules.
  - Slash commands run only when **you type them**.
  - Skills load **on demand**, **automatically**, when the request matches. Until then only their name and description occupy context.
- Rule of thumb: if you keep explaining the same thing to Claude, it should become a skill.

Minimal example:

```yaml
---
name: sql-style
description: Applies the team's SQL conventions (naming, formatting, CTEs over subqueries). Use when writing, reviewing or refactoring SQL queries or migrations.
---
Conventions and examples go here.
```

## L2 creating-your-first-skill — Creating your first skill

**Steps**
1. Create a directory named after the skill inside a skills folder, e.g. `~/.claude/skills/pr-description/`.
2. Add `SKILL.md` with `name`, `description`, then the instructions.
3. Start a new Claude Code session (the course says skills are loaded at startup), then ask Claude which skills are available to confirm it is listed.
4. Test with a natural request ("write a PR description for my changes") and check that Claude says it is using the skill.

**What happens under the hood**
- At startup Claude Code scans four sources: **enterprise** (managed settings), **personal**, **project**, and **installed plugins**.
- Only each skill's **name and description** are loaded at this point, not the body.
- When a request semantically overlaps a description, Claude proposes the skill and **asks you to confirm** loading it, so you stay aware of what enters the context.
- After confirmation the full `SKILL.md` is read and followed.

**Priority when two skills share a name** (highest first):
1. Enterprise
2. Personal
3. Project
4. Plugins

So an enterprise `code-review` skill overrides your personal `code-review`. Avoid collisions with specific names (`frontend-review`, `security-review`) instead of generic ones (`review`).

**Maintenance:** edit `SKILL.md` to update a skill; delete its directory to remove it; start a new session for changes to apply.

## L3 configuration-and-multi-file-skills — Configuration and multi-file skills

**Frontmatter fields**

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | Lowercase letters, digits and hyphens; max 64 characters; should equal the directory name. |
| `description` | yes | Max 1,024 characters. The most important field because it drives matching. |
| `allowed-tools` | no | Tools Claude may use **without a permission prompt** while the skill is active. |
| `model` | no | Which Claude model runs the skill (a Claude Code addition to the open standard). |

The core fields come from the open Agent Skills standard (agentskills.io); Claude Code adds some of its own.

**Writing descriptions:** answer two questions: *what does the skill do?* and *when should Claude use it?* "Helps with docs" is too vague to match reliably. If a skill fails to trigger, add the words people actually use when they ask for that task.

**`allowed-tools` pre-approves; it does not restrict.**
- Listed tools run without asking, for the rest of the turn that invoked the skill; the grant ends with your next message.
- Tools not listed are still available through the normal permission flow.
- Bare `Bash` pre-approves any shell command, so prefer a pattern such as `Bash(git status *)`.
- To actually remove tools while a skill is active, Claude Code has a separate `disallowed-tools` field.
- (The course video describes `allowed-tools` as a restriction; the written lesson corrects this.)

**Progressive disclosure**
- A skill's content shares the context window with the conversation, so do not put everything in one huge file.
- Keep the essentials in `SKILL.md` (**under ~500 lines**) and move detail into supporting files that Claude opens only when needed.
- Suggested layout from the open standard: `scripts/` (executable code), `references/` (extra docs), `assets/` (templates, images, data).
- In `SKILL.md`, link each supporting file and say **when** to read it (e.g. "read `references/architecture.md` only for system-design questions"). It works like a table of contents.

**Scripts**
- A script can be **run** without its source entering the context; only its output costs tokens.
- Tell Claude explicitly to *run* the script, not to read it.
- Good fits: environment checks, transformations that must be identical every time, anything more reliable as tested code than as freshly generated code.

## L4 skills-vs-other-claude-code-features — Skills vs. other Claude Code features

| Feature | Loads / fires | Best for |
| --- | --- | --- |
| `CLAUDE.md` | Every conversation, always | Project-wide rules, hard constraints ("never modify the DB schema"), framework and style preferences |
| Skills | On demand, when a request matches | Task-specific expertise and detailed procedures that would clutter every conversation |
| Subagents | Separate, isolated context; returns a result | Delegating work, different tool access, keeping the main context clean |
| Hooks | On **events** (file save, before/after a tool call) | Linters, validation, automatic side effects |
| MCP servers | Provide external tools and integrations | Connecting Claude to outside systems and data |

Key contrasts:
- Skills are **request-driven**; hooks are **event-driven**.
- A skill **adds knowledge to the current conversation**; a subagent **works in its own context**.
- These features combine; a typical setup uses several at once. Do not force everything into skills.

## L5 sharing-skills — Sharing skills

**Three distribution routes**
1. **Commit to the repository** (`.claude/skills/`): simplest; everyone who clones or pulls gets the skills. Best for team standards and project-specific workflows. The `.claude/` folder can also hold agents, hooks and settings.
2. **Plugins**: a plugin has a `skills/` directory with one folder per skill, each containing `SKILL.md`. Publish it through a **marketplace** so others can install it. Best for skills useful beyond a single project.
3. **Enterprise managed settings**: administrators deploy skills organization-wide. These have the **highest priority**. Managed settings can also limit plugin sources, e.g. with `strictKnownMarketplaces`. Best for things that *must* be consistent (security, compliance).

**Skills and subagents**
- A subagent starts with a **fresh context** and does **not** inherit your skills.
- **Built-in** agents (e.g. Explore, Plan) cannot use skills at all.
- **Custom** subagents (markdown files in `.claude/agents/`, which you can create with `/agents`) can use skills listed in their frontmatter `skills:` field.
- Listed skills load **when the subagent starts**, not on demand, so list only skills that are always relevant to that agent's job.

```yaml
---
name: frontend-reviewer
description: Use this agent to review frontend code for accessibility and performance.
tools: Read, Grep, Glob, Skill
skills: accessibility-audit, performance-check
---
```

## L6 troubleshooting-skills — Troubleshooting skills

Problems fall into a few buckets:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Structural doubts | Invalid layout or frontmatter | Run the **skills validator** first (the course suggests installing it with `uv`). |
| Doesn't trigger | Description does not overlap how you phrase requests | Add real trigger phrases; test several phrasings ("why is this slow?", "profile this", "make this faster"). |
| Doesn't load / not listed | `SKILL.md` at the skills root instead of inside a named folder; wrong file name (must be exactly `SKILL.md`); YAML errors | Fix the path, name and YAML; run `claude --debug` and look for your skill's name. |
| Wrong skill used | Descriptions too similar | Make descriptions distinct and specific. |
| Personal skill ignored | Shadowed by a higher-priority skill with the same name | Rename yours (easiest) or talk to the admin. |
| Plugin skills missing | Stale cache or bad plugin structure | Clear the cache, restart, reinstall; validate the structure. |
| Fails at runtime | Missing dependencies, non-executable scripts, backslash paths | Install and document dependencies; `chmod +x` scripts; use forward slashes everywhere, even on Windows. |

Checklist: *not triggering → description; not loading → path, file name, YAML; wrong skill → distinct descriptions; shadowed → priority, rename; plugin missing → cache, reinstall; runtime → dependencies, permissions, paths.*
