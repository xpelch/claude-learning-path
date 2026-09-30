# Introduction to Model Context Protocol — study notes

Original study notes written for this plugin; they summarize the course and are not a copy of it.
Take the actual course (free) at https://academy.claude.com/courses/introduction-to-model-context-protocol.
The same lessons (except L10) also form the MCP module of *Building with the Claude API*.

Each lesson section starts with `## L<n> <lesson-slug>`.

> **SDK version**: the course code uses the Python SDK **v1** (`from mcp.server.fastmcp import FastMCP`). In SDK **v2**, `FastMCP` was renamed `MCPServer` and other APIs changed, so pin `mcp<2` to follow the course as written.

The course builds a small **document chatbot** in Python: a CLI app (`main.py`) with an MCP **client** (`mcp_client.py`) and a custom MCP **server** (`mcp_server.py`) holding documents in an in-memory dict.

---

## L1 introducing-mcp — Introducing MCP

- **MCP (Model Context Protocol)** is a communication layer that gives Claude **tools, resources and prompts** without you writing all the integration code.
- Architecture: your app contains an **MCP client**, which connects to one or more **MCP servers**; each server wraps an outside service (GitHub, AWS, a database…).
- Problem solved: exposing a big service like GitHub as tools would mean writing, testing and maintaining many schemas and functions yourself. With MCP, a server that already exposes them is plugged in instead.
- **Anyone** can write a server; service providers often publish official ones.
- **MCP vs calling an API directly**: with MCP the tool schemas and functions are already defined for you.
- **MCP vs tool use**: they are complementary. Tool use is *how Claude calls tools*; MCP is *who provides and executes them*: a server someone else built.

## L2 mcp-clients — MCP clients

- The **client** is your app's bridge to a server: it handles the protocol and message exchange.
- MCP is **transport-agnostic**: most commonly client and server run on the same machine over **stdio**, but HTTP, WebSockets and other transports work too.
- Core message pairs: `ListToolsRequest` → `ListToolsResult` (what tools exist?) and `CallToolRequest` → `CallToolResult` (run this tool with these arguments).
- End-to-end flow for "what repositories do I have?": user → your server → client lists tools (server answers) → your server sends the question plus tools to Claude → Claude asks for a tool → client sends `CallToolRequest` → MCP server calls GitHub → result flows back → sent to Claude → final answer → user. Many steps, each with a clear job.

## L3 defining-tools-with-mcp — Defining tools with MCP

- The official **Python SDK** builds a server in one line: `mcp = FastMCP("DocumentMCP", log_level="ERROR")`.
- Tools are plain functions with the **`@mcp.tool(name=..., description=...)`** decorator. Arguments use **type hints** plus Pydantic **`Field(description=...)`**, and the SDK **generates the JSON schema** for you.
- Course tools: `read_doc_contents(doc_id)` and `edit_document(doc_id, old_str, new_str)` (find and replace).
- Raise exceptions for bad input (e.g. unknown `doc_id` → `ValueError`); errors surface to the client.
- Benefits: no hand-written schemas, validation from types, clear parameter docs, automatic registration.

## L4 the-server-inspector — The server inspector

- The SDK ships a browser-based **MCP Inspector**: `mcp dev mcp_server.py` (inside your environment, e.g. `uv run mcp dev mcp_server.py`), then open the local URL it prints.
- Click **Connect**, open **Tools**, **List Tools**, pick one, fill the inputs, **Run Tool**, and check the success status and output.
- Server state persists between calls, so you can edit then read to verify a workflow.
- Use it to iterate quickly, test edge cases and errors, and debug without the full app.

## L5 implementing-a-client — Implementing a client

- Usually a project implements **either** a client **or** a server; the course builds both to see them interact.
- Two layers: the SDK's **`ClientSession`** (the actual connection, which needs careful cleanup) wrapped in your own **`MCPClient`** class that manages resources.
- Core methods:
  - `list_tools()` → `(await self.session().list_tools()).tools`
  - `call_tool(name, input)` → `await self.session().call_tool(name, input)`
- The app uses them to (1) send the tool list to Claude and (2) run the tools Claude asks for.
- Test with `uv run mcp_client.py` (prints the tools), then `uv run main.py` and ask about a document.

## L6 defining-resources — Defining resources

- **Resources** expose **data** for reading, like GET handlers. Course use case: `@document` mentions (list documents for autocomplete; fetch a document's text to inject into the prompt, so Claude doesn't need a tool call).
- Protocol: `ReadResourceRequest` (with a **URI**) → `ReadResourceResult`.
- **Direct** resources have a fixed URI: `@mcp.resource("docs://documents", mime_type="application/json")`.
- **Templated** resources have parameters in the URI: `@mcp.resource("docs://documents/{doc_id}", mime_type="text/plain")`. The SDK passes `doc_id` as a keyword argument.
- `mime_type` hints how to parse the result (`application/json`, `text/plain`, `application/pdf`…). The SDK serializes return values for you.
- Inspector: *Resources* lists direct resources, *Resource Templates* lists templated ones.

## L7 accessing-resources — Accessing resources

- Client side: `read_resource(uri)` calls `session.read_resource(AnyUrl(uri))` and takes `result.contents[0]`.
- If the content is text with MIME `application/json`, `json.loads` it; otherwise return the raw text.
- In the CLI, typing `@` shows documents (from the list resource); the chosen document's content goes **directly into the prompt**. That is faster and smoother than making Claude call a tool.

## L8 defining-prompts — Defining prompts

- **Prompts** are pre-built, **tested** instructions the server author provides so users get better results than their own ad-hoc wording.
- `@mcp.prompt(name="format", description=...)` on a function whose arguments (with `Field` descriptions) are interpolated into the text. It returns a **list of messages** (`base.UserMessage(...)`, optionally assistant messages too).
- Course example: `/format <doc_id>` rewrites a document in Markdown using the `edit_document` tool.
- Check the rendered messages in the Inspector.
- Benefits: consistency, encoded expertise, reuse across clients, one place to improve.

## L9 prompts-in-the-client — Prompts in the client

- `list_prompts()` → `(await session.list_prompts()).prompts`.
- `get_prompt(name, args)` → `(await session.get_prompt(name, args)).messages`. The args dict (e.g. `{"doc_id": "plan.md"}`) becomes the prompt function's keyword arguments.
- In the CLI, typing `/` lists prompts as commands; the resulting messages go to Claude, which then uses tools as needed.

## L10 mcp-review — MCP review

Each primitive is controlled by a different part of the stack:

| Primitive | Controlled by | Use it to | Example in Claude's apps |
| --- | --- | --- | --- |
| **Tools** | the **model** | give Claude new capabilities it decides to use | running code, calculations |
| **Resources** | the **application** | get data into your app for UI or context | "Add from Google Drive" |
| **Prompts** | the **user** | offer predefined workflows triggered on demand | workflow buttons, slash commands |

Rule of thumb: tools serve the model, resources serve your app, prompts serve your users.
