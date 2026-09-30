---
name: mcp-lab
description: Hands-on labs for the Introduction to Model Context Protocol course (and the MCP module of Building with the Claude API). The user builds a Python MCP document server and client step by step — tools, the inspector, resources, prompts — then connects it to Claude Code, with an automatic checker. Use when the user wants an MCP lab or exercise, wants to practise building an MCP server or client, or asks to check what their MCP server exposes.
allowed-tools:
  - Read
  - Glob
  - Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
  - Bash(python "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" *)
---

# MCP lab

The user builds the course's document server and client themselves. Starters are in `assets/`; a checker is in `scripts/`. Run the checker, don't read it.

## Setup (first lab only)

1. Ask where to create the lab folder (e.g. `~/mcp-lab`). Copy `assets/server_starter.py` and `assets/client_starter.py` there.
2. The user creates the environment: `uv init` then `uv add "mcp[cli]<2" pydantic` (or a venv with `pip install "mcp[cli]<2" pydantic`). Don't install packages globally.
3. Most labs need **no API key**. Only running the full chatbot with Claude does; if so, the user puts the key in `.env` themselves. Never ask them to paste a key into the chat.

## Checker

Run it with the lab environment's Python (it needs the `mcp` package):

```bash
uv run python "${CLAUDE_PLUGIN_ROOT}/skills/mcp-lab/scripts/check_server.py" server_starter.py \
  --expect-tools read_doc_contents,edit_document \
  --call read_doc_contents '{"doc_id":"roadmap.md"}'
```

Other options: `--expect-resources`, `--expect-templates`, `--expect-prompts`, `--read <uri>`, `--get-prompt <name> '<json>'`. It exits 0 on PASS and warns about tools or arguments without descriptions.

## Running a lab

Labs are listed in `${CLAUDE_PLUGIN_ROOT}/courses/path.json` (course `introduction-to-model-context-protocol`). Full steps and pass criteria are in [references/labs.md](references/labs.md); read only the chosen lab's section. With no choice given, suggest the first lab not passed yet.

1. State the goal and pass criteria.
2. **The user writes the code.** Hint, review, and point to the notes (`${CLAUDE_PLUGIN_ROOT}/courses/introduction-to-model-context-protocol/notes.md`). A solution shown on request means the lab doesn't count.
3. Verify with the checker command given in the lab.
4. Record the outcome. Labs belong to the MCP course even when the user comes from the API course:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lp.py" --data-dir "${CLAUDE_PLUGIN_DATA}" record-lab --course introduction-to-model-context-protocol --lab <id> [--failed]
```

Use `python` instead of `python3` if needed (Windows).
