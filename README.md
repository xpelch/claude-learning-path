# claude-learning-path

A Claude Code plugin that turns Claude into a study companion for the whole
[Claude Partner Network learning path](https://anthropic.skilljar.com/page/claude-partner-network-learning-path)
on Anthropic Academy. It tracks your progress, quizzes you, and runs hands-on labs for all four courses.

> Unofficial community project, not affiliated with or endorsed by Anthropic.
> The study notes, questions and labs are original material written for this plugin; take the real (free) courses on
> [Anthropic Academy](https://academy.claude.com/courses).

## Install

In your shell:

```bash
claude plugin marketplace add xpelch/claude-learning-path
claude plugin install claude-learning-path@xpelch
```

Or inside a Claude Code session: `/plugin marketplace add xpelch/claude-learning-path`, then `/plugin install claude-learning-path@xpelch`.

The scripts need Python 3.8+ (standard library only). Some labs install their own dependencies in a lab folder.

## Coverage

| # | Course | Lessons | Questions | Labs |
| --- | --- | --- | --- | --- |
| 1 | [Introduction to agent skills](https://academy.claude.com/courses/introduction-to-agent-skills) | 6 | 30 | 6 |
| 2 | [Building with the Claude API](https://academy.claude.com/courses/building-with-the-claude-api) (8 modules) | 67 | 174 + 36 shared | 7 |
| 3 | [Introduction to Model Context Protocol](https://academy.claude.com/courses/introduction-to-model-context-protocol) | 10 | 40 | 6 |
| 4 | [Claude Code in Action](https://academy.claude.com/courses/claude-code-in-action) | 9 | 36 | 8 |

The 9 MCP lessons that appear in both the API course and the MCP course are covered once and **share progress**: master them in one course and they count in the other.

## Skills

Skills trigger automatically from natural requests; you can also call them directly, e.g. `/claude-learning-path:course-quiz`.

| Skill | What it does | Try saying |
| --- | --- | --- |
| `learning-path-coach` | Progress, next step, recaps and cheat sheets per lesson, module or course | "Where am I in the Claude learning path?", "What next?", "Recap the RAG module" |
| `course-quiz` | One-question-at-a-time quizzes, review of missed questions, mock exams (one question per lesson) | "Quiz me on hooks", "Mock exam on the MCP course", "Review what I got wrong" |
| `skill-authoring-lab` | Agent skills labs + `SKILL.md` linter | "Give me a skills lab", "Lint my skills folder" |
| `claude-api-lab` | Coding labs: first request, clean JSON, evals, tool loop, hybrid retrieval, prompt caching, workflows | "Give me a Claude API lab" |
| `mcp-lab` | Build the course's document server and client step by step, with an automatic checker | "Start the MCP lab", "Check my MCP server" |
| `claude-code-lab` | Session steering, CLAUDE.md audit, verification skill, hooks, headless JSON, GitHub Actions, plugin packaging | "Audit my CLAUDE.md", "Test my PreToolUse hook" |

Progress is recorded automatically after each recap, quiz and lab, in the plugin's persistent data directory
(`$CLAUDE_PLUGIN_DATA/progress.json`, falling back to `~/.claude/claude-learning-path/`). A lesson is **mastered**
when at least 80% of its questions were answered correctly on their latest attempt; a course is complete when every
lesson is mastered and every lab is passed.

### Version notes

- **MCP labs pin `mcp<2`.** The course uses the Python SDK v1 (`FastMCP`); SDK v2 renamed it `MCPServer` and changed other APIs.
- **API labs need your own API key.** Write it in a `.env` file yourself (the plugin never asks for it). API calls are billed to your account.
- **Names change over time.** Model names, tool version strings and Claude Code flags change; the notes flag version-sensitive details.

## Repository layout

```
.claude-plugin/marketplace.json          marketplace "xpelch" (this repo)
plugins/claude-learning-path/
  .claude-plugin/plugin.json
  courses/path.json                      courses, modules, lessons (with shared "same_as" lessons), labs
  courses/<course>/notes.md              study notes, one "## L<n> <lesson>" section per lesson
  courses/<course>/questions.json        question bank (mcq + open), ids unique across courses
  scripts/lp.py                          progress tracker: status, next, lessons, quiz (--module, --review, --exam), record-*
  scripts/lint_skill.py                  SKILL.md linter
  scripts/lint_claude_md.py              CLAUDE.md audit
  scripts/hook_test.py                   dry-run a Claude Code hook and explain the outcome
  skills/learning-path-coach/  skills/course-quiz/
  skills/skill-authoring-lab/  skills/claude-api-lab/  skills/mcp-lab/  skills/claude-code-lab/
tests/test_plugin.py                     content integrity, scripts, lab assets
```

The design follows what the agent-skills course teaches. Skills are organized by **action** (coach, quiz, a lab per course)
so descriptions stay distinct. Course material loads through **progressive disclosure**: only the needed lesson
sections are read. Deterministic work (progress, question selection, linting, hook checks) is done by **scripts that
Claude runs without reading**.

## Development

```bash
python -m unittest discover -s tests
python plugins/claude-learning-path/scripts/lint_skill.py plugins/claude-learning-path/skills
claude plugin validate .
claude --plugin-dir ./plugins/claude-learning-path
```

The MCP tests run only when the `mcp` package (`<2`) is importable; otherwise they are skipped.

## License

MIT
