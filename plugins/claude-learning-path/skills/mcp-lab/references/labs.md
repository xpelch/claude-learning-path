# Labs: Introduction to Model Context Protocol

All labs happen in the lab folder with `server_starter.py` and `client_starter.py`.
`CHECK` = `uv run python "${CLAUDE_PLUGIN_ROOT}/skills/mcp-lab/scripts/check_server.py" server_starter.py`.

---

## server-tools: Build a document server with tools and test it in the inspector

Lessons: L1–L4.

**Steps for the user**
1. Implement `read_doc_contents(doc_id)` and `edit_document(doc_id, old_str, new_str)` with `@mcp.tool(name=..., description=...)`, type hints, and `Field(description=...)` for every argument. Unknown ids raise `ValueError` with a clear message.
2. Start the inspector: `uv run mcp dev server_starter.py`, **Connect**, **List Tools**, run `read_doc_contents` on `roadmap.md`, run `edit_document`, then read again to see the change persist.
3. Ask: "How is this different from writing tool schemas for the Claude API yourself?" (The SDK generates the schema; the server executes the tools.)

**Check**

```
CHECK --expect-tools read_doc_contents,edit_document \
  --call read_doc_contents '{"doc_id":"roadmap.md"}' \
  --call edit_document '{"doc_id":"roadmap.md","old_str":"Q2","new_str":"Q2 (moved)"}'
```

Also confirm an unknown id fails: `--call read_doc_contents '{"doc_id":"nope"}'` should report FAIL for that call (an error result is the expected behaviour here).

**Pass when:** the first check PASSes with no missing-description warnings, the unknown-id call errors, and the user did step 2.

---

## client: Implement list_tools and call_tool in a client

Lesson: L5.

**Steps**
1. In `client_starter.py`, implement `list_tools()` (return `result.tools`) and `call_tool()` (forward name and input to the session).
2. Run `uv run python client_starter.py server_starter.py`. It should print the tool names and the roadmap document.
3. Ask: "Where do the tool name and input come from in a real app?" (Claude's `tool_use` block.) "Why wrap ClientSession in a class?" (Connection cleanup.)

**Pass when:** step 2 prints both tools and the document content, and the answers are right.

---

## resources: Add direct and templated resources, then read them from the client

Lessons: L6–L7.

**Steps**
1. Server: `docs://documents` (direct, `application/json`, returns the list of ids) and `docs://documents/{doc_id}` (templated, `text/plain`).
2. Client: `read_resource(uri)` using `AnyUrl(uri)`, taking `contents[0]`, and `json.loads` when the MIME type is `application/json`.
3. Inspector: find both under *Resources* and *Resource Templates*.
4. Ask: "Why inject a mentioned document via a resource rather than letting Claude call a tool?"

**Check**

```
CHECK --expect-resources docs://documents --expect-templates "docs://documents/{doc_id}" \
  --read docs://documents --read docs://documents/incident-42.txt
```

Then uncomment the `read_resource` line in the client's `main()` and run it: it must print a Python list, not a JSON string.

**Pass when:** the check PASSes, the client prints a list, and step 4 is answered (app-controlled context, no extra tool round trip).

---

## prompts: Add a server prompt and fetch it from the client

Lessons: L8–L9.

**Steps**
1. Server: `@mcp.prompt(name="format", description=...)` taking `doc_id` (with `Field`) and returning `[base.UserMessage(...)]` that tells Claude to rewrite the document in Markdown **using the `edit_document` tool**, with the id inside XML tags.
2. Client: `list_prompts()` and `get_prompt(name, args)` returning `result.messages`.
3. Inspector: render the prompt with a doc id and read the interpolated text.

**Check**

```
CHECK --expect-prompts format --get-prompt format '{"doc_id":"onboarding.md"}'
```

**Pass when:** the check PASSes, the rendered text contains the doc id, and the prompt references the edit tool.

---

## primitive-choice: Pick tool, resource or prompt for six features

Lesson: L10.

Ask the user to choose the primitive and say **who controls it** (model, app or user) for each feature. Keep the answers hidden until they reply.

1. Claude should be able to create a Jira ticket when it decides one is needed. → **tool** (model)
2. The app shows a dropdown of the user's recent files. → **resource** (app)
3. A "Summarize this PR" button with a carefully tuned instruction. → **prompt** (user)
4. Attach the current database schema to every question in a SQL assistant. → **resource** (app)
5. Claude can run a SQL query to answer a question. → **tool** (model)
6. A `/standup` command producing a report in the team's format. → **prompt** (user)

**Pass when:** at least 5/6 are right, including the controller for each.

---

## connect-claude-code: Connect your server to Claude Code

Lessons: L1 (and API course L60).

**Steps**
1. With the tools lab done, register the server: `claude mcp add docs-lab -- uv run --directory <lab folder> python server_starter.py` (adapt to the user's setup; the course's form is `claude mcp add <name> <command...>`).
2. Start a new Claude Code session, check the server is connected (`/mcp`), and ask: "What does incident-42.txt say?". Claude should call `read_doc_contents`.
3. Afterwards, offer to remove it: `claude mcp remove docs-lab`.

**Pass when:** the user confirms Claude answered through the tool (the tool call is visible in the transcript).
