# Labs: Introduction to agent skills

Each lab lists its goal, where to work, the steps for the user, and the success criteria used before recording a pass.
"Lab folder" means a throwaway directory the user agrees to, e.g. `~/skills-lab/`, unless the lab says otherwise.

---

## first-skill: Build and verify your first skill

Lessons: L1, L2.

**Goal:** create a working skill from scratch and see Claude pick it up.

**Where:** a project the user chooses (`<project>/.claude/skills/`) or their personal folder (`~/.claude/skills/`). Ask which; project is safer to clean up.

**Steps for the user**
1. Pick a real, repeated task (commit messages, PR descriptions, explaining code…).
2. Create `<skills>/<skill-name>/SKILL.md` with `name`, `description` and a short set of instructions.
3. Run the linter on it and fix any errors.
4. Start a new Claude Code session in that project, ask "what skills are available?" and confirm the skill is listed.
5. Make a natural request that should trigger it and confirm Claude uses it.

**Pass when:** the linter reports no errors, the name matches the directory, and the user confirms steps 4 and 5 worked.

---

## description-tuning: Tune a description until it triggers reliably

Lessons: L3, L6.

**Goal:** turn a vague description into one that answers *what* and *when* and matches real phrasings.

**Steps**
1. Start from the user's skill from `first-skill`, or from this deliberately weak one: `description: Helps with docs.`
2. The user writes **five** different ways a colleague might ask for the task (casual, terse, indirect, with jargon, as a question).
3. For each phrasing, the user predicts whether the current description would match, and why.
4. The user rewrites the description: what it does, then "Use when…" with the trigger words found in step 2. Stay under 1,024 characters.
5. Optional live check: new session, try the phrasings, note which ones trigger.

**Pass when:** the final description states what and when, covers the vocabulary of at least four of the five phrasings, and the linter shows no `description-*` warnings.

---

## allowed-tools: Pre-approve tools with allowed-tools

Lesson: L3.

**Goal:** understand that `allowed-tools` **pre-approves** tools and does not restrict them.

**Steps**
1. The user adds `allowed-tools` to a read-oriented skill (e.g. codebase onboarding) listing only what it needs: `Read, Grep, Glob`.
2. Ask: "If the skill's instructions lead Claude to edit a file, what happens?" Expected answer: the edit goes through the normal permission prompt, because unlisted tools are not blocked.
3. Ask how they would actually forbid edits during the skill. Expected answer: the separate `disallowed-tools` field.
4. If they want shell access, make them narrow it, e.g. `Bash(git log *)` instead of bare `Bash`, and explain why.
5. Run the linter.

**Pass when:** the frontmatter is valid, there is no bare `Bash`, and the user answered steps 2 and 3 correctly in their own words.

---

## progressive-disclosure: Split a large skill with progressive disclosure

Lesson: L3.

**Goal:** restructure a bloated skill into `SKILL.md` + `references/` + `scripts/` (+ `assets/`).

**Setup:** in the lab folder, create `big-skill/SKILL.md` with valid frontmatter (`name: big-skill`) and a body mixing: a 10-line core workflow, a long API/reference section (generate ~150 lines of plausible reference tables), a template, and inline shell steps that check the environment.

**Steps for the user**
1. Decide what must stay in `SKILL.md` (the core workflow) and what is occasional.
2. Move the reference material to `references/`, the template to `assets/`, and the environment check to an executable script in `scripts/` (with a shebang).
3. In `SKILL.md`, link each file and say **when** to read it; for the script, say to **run** it, not read it.
4. Run the linter.

**Pass when:** no linter errors (links resolve), `SKILL.md` is only the core plus conditional pointers, and the script is invoked with a "run this" instruction.

---

## subagent-skills: Give a custom subagent its skills

Lesson: L5.

**Goal:** make a custom subagent that preloads specific skills.

**Where:** a project the user chooses.

**Steps**
1. Ask first: "Will the built-in Explore agent see your project skills?" Expected: no. Built-in agents can't use skills.
2. The user makes sure one or two relevant skills exist in `.claude/skills/`.
3. The user creates `.claude/agents/<agent-name>.md` (by hand or with `/agents`) with frontmatter `name`, `description`, `tools` and `skills: <skill-a>, <skill-b>`.
4. Ask: "When are those skills loaded for the subagent?" Expected: when the subagent starts, not on demand. So only list skills that are always relevant to it.
5. Optional: delegate a task to the agent and check that it applies the skill.

**Pass when:** the agent file has valid frontmatter with a `skills` field naming skills that exist, and the user answered steps 1 and 4 correctly.

---

## broken-skills: Diagnose four broken skills

Lesson: L6.

**Goal:** practise the troubleshooting checklist on real failures.

**Setup** (you, not the user, copy the fixtures into the lab folder, keeping these exact target paths):

| Fixture | Copy to |
| --- | --- |
| `assets/broken/case-1.md` | `<lab>/case-1/skills/SKILL.md` |
| `assets/broken/case-2.md` | `<lab>/case-2/skills/pdf-tools/SKILL.md` |
| `assets/broken/case-3.md` | `<lab>/case-3/skills/docs-helper/SKILL.md` |
| `assets/broken/case-4.md` | `<lab>/case-4/skills/release-notes/skill.md` |

**Steps for the user**, for each case:
1. Look at the folder and file, then state the symptom it would cause (not listed / not loading / never triggers / fails at runtime) and the root cause.
2. Propose the fix, then run the linter to confirm.

**Expected diagnoses** (keep hidden until the user answers):
- **case-1**: `SKILL.md` sits at the skills root, so it doesn't load. Move it into `skills/<name>/SKILL.md`.
- **case-2**: `name: PDF_Tools` breaks the naming rules and doesn't match the directory. Also `allowed-tools` has bare `Bash`. Fix: `name: pdf-tools` and a narrowed Bash pattern.
- **case-3**: valid structure but the description is "Helps with docs." The skill never triggers; it needs what + when + trigger phrases.
- **case-4**: file named `skill.md` instead of `SKILL.md`; the body links a missing `references/format.md` and uses a backslash path `scripts\build.sh`. Fix: rename, fix or remove the link, use forward slashes, and make scripts executable.

**Pass when:** the user identified at least three of the four root causes before seeing the answers, and all four cases lint clean after their fixes (case-3 without the `description-when` warning).
