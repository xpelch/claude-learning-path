---
name: claude-api-lab
description: Hands-on coding labs for the Building with the Claude API course. The user writes Python against the Anthropic SDK — first request and multi-turn chat, clean JSON output, an eval pipeline with graders, a multi-tool conversation loop, hybrid BM25 + rank-fusion retrieval, prompt caching measurement, and a workflow pattern. Use when the user wants a Claude API lab, exercise or coding practice from that course, or wants to practise tool use, evals, RAG or prompt caching hands-on.
allowed-tools:
  - Read
  - Glob
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
---

# Claude API lab

The user writes the code; you coach. Starters are in `assets/`:

- `chat_helpers.py`: `add_user_message`, `add_assistant_message`, `chat` (returns the full Message; supports `system`, `temperature`, `stop_sequences`, `tools`), `text_from_message`.
- `retrieval_exercise.py`: offline exercise (no key needed) with built-in self-checks.

## Setup (first lab only)

1. Ask where to create the lab folder; copy the starters there.
2. The user creates an environment (`uv init && uv add anthropic python-dotenv`, or a venv with pip).
3. **API key**: the user creates it in the Claude Console and writes `ANTHROPIC_API_KEY=...` into `.env` **themselves**, and adds `.env` to `.gitignore`. Never ask for the key in chat, never print it, never commit it. API calls are billed to their account, so mention it and keep lab runs small.
4. Model: `chat_helpers.py` reads `ANTHROPIC_MODEL` (default `claude-haiku-4-5`, cheap and fast for labs). Model ids and tool versions change; if one is rejected, check the current API docs.

## Running a lab

Labs are listed in `${CLAUDE_PLUGIN_ROOT}/courses/path.json` (course `building-with-the-claude-api`). Steps and pass criteria are in [references/labs.md](references/labs.md); read only the chosen lab's section. With no choice given, suggest the first lab not passed (`lp.py status --course building-with-the-claude-api`).

1. State the goal and pass criteria.
2. **The user writes the code.** Hint and review; point to the lesson notes in `${CLAUDE_PLUGIN_ROOT}/courses/building-with-the-claude-api/notes.md` (sections `## L<n> <lesson-slug>`). A full solution given on request means the lab doesn't count.
3. Have the user run their code and check the output against the criteria. You may run it with their permission.
4. Record the outcome:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" record-lab --course building-with-the-claude-api --lab <id> [--failed]
```

Use `python` instead of `python3` if needed (Windows). The MCP module's hands-on work is the `mcp-lab` skill.
