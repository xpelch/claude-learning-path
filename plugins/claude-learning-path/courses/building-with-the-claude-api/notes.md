# Building with the Claude API — study notes

Original study notes written for this plugin; they summarize the course and are not a copy of it.
Take the actual course (free) at https://academy.claude.com/courses/building-with-the-claude-api.

Each lesson section starts with `## L<n> <lesson-slug>`, where `<n>` is the lesson's position in the course.
Lessons L47, L48 and L50–L56 (the MCP module) are identical to the *Introduction to Model Context Protocol* course; their notes are in `courses/introduction-to-model-context-protocol/notes.md`.

> Model names, tool version strings and limits change over time. The course uses names such as `claude-sonnet-4-5`, `text_editor_20250124` and `web_search_20250305`; check the current API docs before copying them.

---

# Module 1 — Accessing Claude with the API (api-basics)

## L1 accessing-the-api — Accessing the API

- A request passes through five stages: client → **your server** → Anthropic API → model → back to your server → client.
- **Never call the API from browser or mobile code**: the API key is a secret, and anything shipped to a client can be extracted. The client talks to your server, which holds the key.
- You can use an official SDK (Python, TypeScript/JavaScript, Go, Ruby…) or plain HTTP.
- Every request needs: the **API key**, a **model** name, a list of **messages**, and **max_tokens**.
- Inside the model, conceptually: **tokenization** (text → tokens) → **embedding** (each token → a vector of numbers encoding its possible meanings) → **contextualization** (vectors adjusted using neighbouring tokens to pick the meaning in context) → **generation** (probabilities for the next token, then sampling with some randomness; repeat token by token).
- Generation stops when: `max_tokens` is reached, the model emits its natural end-of-sequence, or a **stop sequence** appears.
- The response carries the generated **content**, **usage** (input/output token counts) and a **stop_reason**.

## L2 getting-an-api-key — Getting an API key

- Keys are created in the Claude Console (platform.claude.com): *Get API keys* → *Create key*, choose a workspace and a recognizable name.
- The key is shown **only once**. If lost, delete it and create a new one.
- Treat it like a password: never commit it or paste it into shared places.

## L3 making-a-request — Making a request

- Setup in Python: install `anthropic` (and `python-dotenv`), put `ANTHROPIC_API_KEY=...` in a `.env` file, and **add `.env` to `.gitignore`**. `Anthropic()` reads the key from the environment.
- `client.messages.create(model=..., max_tokens=..., messages=[...])` is the core call.
- `max_tokens` is a **ceiling, not a target**: Claude writes what it needs and is cut off only if it reaches the limit.
- Messages alternate roles: `user` (human input) and `assistant` (model output), each `{"role": ..., "content": ...}`.
- The generated text is at `response.content[0].text`.

## L4 multi-turn-conversations — Multi-turn conversations

- **The API is stateless**: Claude keeps no memory between requests.
- To continue a conversation, **you** keep the message list and resend the **whole history** each time: append the assistant reply, append the next user message, send everything.
- Handy helpers: `add_user_message(messages, text)`, `add_assistant_message(messages, text)`, `chat(messages)`.

## L5 system-prompts — System prompts

- The `system` parameter tells Claude **how** to respond: role, tone, style, rules. Claude answers the way someone in that role would, and stays on task.
- Example: a math tutor prompt ("give hints, guide step by step, don't hand out the answer") turns a full solution into guiding questions.
- In a reusable `chat()` helper, only add `system` when one is given (the course notes that passing `system=None` is rejected).

## L6 temperature — Temperature

- Generation = predict probabilities for the next token, then **sample** one.
- **Temperature (0 to 1)** reshapes those probabilities: near 0 the most likely token nearly always wins (deterministic); near 1 the choice spreads across options (more varied).
- Rough guide: **0–0.3** facts, code, extraction, moderation; **0.4–0.7** summaries, teaching, problem solving; **0.8–1.0** brainstorming, creative writing, marketing, jokes.
- A higher temperature makes different outputs *more likely*; it does not guarantee them.

## L7 response-streaming — Response streaming

- Responses can take many seconds. **Streaming** sends the text in chunks as it is generated, so the UI can show progress.
- With `stream=True` you receive events: `MessageStart`, `ContentBlockStart`, `ContentBlockDelta` (the text chunks), `ContentBlockStop`, `MessageDelta`, `MessageStop`, all within **one** request.
- The SDK helper `client.messages.stream(...)` exposes `stream.text_stream` (text only) and `stream.get_final_message()` (the assembled message, e.g. to store it).

## L8 structured-data — Structured data

- Asking for JSON often returns JSON wrapped in a Markdown fence plus commentary, which is awkward when an app needs the raw data.
- Technique from the course: **prefill** the assistant turn with the opening fence (e.g. an assistant message containing ```` ```json ````) and set a **stop sequence** of ```` ``` ````. Claude continues with just the content and stops before closing the fence. Then `json.loads(text.strip())`.
- Works for any fenced or delimited output (code, CSV, lists): prefill what Claude would open with and stop on what it would close with.
- Note: prefilling is incompatible with extended thinking (see L39), and newer API versions also offer dedicated structured-output features. Check the current docs.

# Module 2 — Prompt evaluation (evals)

## L9 prompt-evaluation — Prompt evaluation

- **Prompt engineering** = techniques to write better prompts. **Prompt evaluation** = measuring how well a prompt works, automatically, against test inputs.
- After drafting a prompt you can (1) test it once, (2) test it a few times and patch edge cases, or (3) run it through an **eval pipeline** and iterate on scores. Options 1 and 2 are the common traps: real users produce inputs you didn't imagine.
- Evals cost more effort up front but catch problems before production and let you compare prompt versions objectively.

## L10 a-typical-eval-workflow — A typical eval workflow

1. **Draft** a prompt template.
2. Build an **eval dataset** of realistic inputs (by hand or generated by Claude).
3. **Run** each input through the prompt and Claude.
4. **Grade** each output (e.g. 1–10).
5. **Change the prompt and repeat**, comparing average scores (e.g. 7.66 → 8.7 after adding guidance).
- Start small; many tools exist, but the core loop is simple.

## L11 generating-test-datasets — Generating test datasets

- The course example: a prompt that must return **only** Python, JSON or a regex for AWS tasks, with no extra prose.
- A dataset is a list of objects such as `{"task": "..."}`.
- Claude can generate it; a **fast, cheap model (Haiku)** is fine for this. Use prefill + stop sequence to get parseable JSON, then save it to `dataset.json`.

## L12 running-the-eval — Running the eval

- Three functions: `run_prompt(test_case)` (fill the template, call Claude), `run_test_case(test_case)` (run and grade, returning output, test case and score), `run_eval(dataset)` (loop and collect results).
- Start with a placeholder score to get the pipeline working, then add real graders.
- Expect it to be slow at first (sequential calls); concurrency comes later.

## L13 model-based-grading — Model based grading

- Three kinds of graders:
  - **Code**: length, required or forbidden words, syntax validity, readability.
  - **Model**: quality, instruction following, completeness, helpfulness, safety.
  - **Human**: most flexible but slow and tedious.
- Define **criteria first** (course example: format, valid syntax, task following).
- A model grader prompt asks for JSON with **strengths, weaknesses, reasoning and a score**. Asking for reasoning keeps scores from clustering around a bland middle (≈6).
- Report the **average score** across the dataset as the metric to track.

## L14 code-based-grading — Code based grading

- Code graders check **format and syntax**; the model grader checks **task following**.
- Validators try to parse the output (`json.loads`, `ast.parse`, `re.compile`): parse OK → 10, error → 0.
- Each test case records its expected **format** so the right validator runs.
- Tighten the prompt ("respond only with Python, JSON or a plain regex; no commentary") and prefill a code fence.
- Combine scores, e.g. the average of model and syntax scores (weights are your choice).

# Module 3 — Prompt engineering techniques (prompt-engineering)

## L15 prompt-engineering — Prompt engineering

- Loop: set a goal → write a first prompt → evaluate → apply one technique → re-evaluate. **Change one thing at a time.**
- Course running example: a one-day meal plan for an athlete (height, weight, goal, dietary restrictions), graded with extra criteria (calorie total, macros, meals with portions and timing).
- Keep the dataset small (2–3 cases) and concurrency low (≈3) while iterating to avoid rate limits; a low first score (≈2/10) is normal.

## L16 being-clear-and-direct — Being clear and direct

- The **first line** matters most: state the task plainly.
- **Clear**: simple words, say exactly what you want. **Direct**: instructions, not questions, starting with an action verb (*Write, Create, Generate, Identify*).
- "What should this person eat?" → "Generate a one-day meal plan for an athlete that meets their dietary restrictions." (course score ≈2.3 → ≈3.9).

## L17 being-specific — Being specific

- Two kinds of specificity:
  - **Output guidelines**: qualities the result must have (length, structure, required elements, tone). Use them in almost every prompt.
  - **Process steps**: an ordered method to follow. Use them for complex problems: troubleshooting, decisions, critical thinking, anything needing several angles.
- They combine well. Adding guidelines to the meal-plan prompt roughly doubled its score (≈3.9 → ≈7.9).

## L18 structure-with-xml-tags — Structure with XML tags

- When a prompt interpolates lots of content, wrap each piece in **descriptive tags** (`<sales_records>`, `<my_code>`, `<docs>`, `<athlete_information>`) so instructions and data don't blur together.
- Tag names are yours to invent; specific names beat generic ones like `<data>`.
- Most useful with large or mixed content; harmless and clarifying even for short prompts.

## L19 providing-examples — Providing examples

- **One-shot / multi-shot** prompting: include sample input → ideal output pairs.
- Great for corner cases (e.g. sarcasm in sentiment analysis), complex output formats, tone, and ambiguous inputs.
- Wrap examples in tags (`<sample_input>`, `<ideal_output>`), say what they are, and **explain why** the example output is good.
- Mine your eval results: reuse the highest-scoring outputs as examples, and target your most common failures.

# Module 4 — Tool use with Claude (tool-use)

## L20 introducing-tool-use — Introducing tool use

- Tools let Claude reach **fresh or external data** (weather, databases, APIs) beyond its training.
- Flow: you send the question plus tool descriptions → Claude replies with a **tool request** → **your code** runs it → you send the result back → Claude writes the final answer.

## L21 project-overview — Project overview

- Course project: "remind me about my doctor's appointment a week from Thursday".
- Gaps to fill with tools: Claude may not know the exact current time, date arithmetic over many days is error-prone, and it has no way to set a reminder.
- Tools: `get_current_datetime`, `add_duration_to_datetime`, `set_reminder`. Principle: **extend the model with tools** instead of working around its limits in the prompt.

## L22 tool-functions — Tool functions

- A tool function is an ordinary function your code runs when Claude asks.
- Best practices: **descriptive function and parameter names**, **validate inputs**, and **raise clear error messages**. Claude sees the error and can retry with corrected arguments.

## L23 tool-schemas — Tool schemas

- Each tool is described by `name`, `description` and `input_schema` (a **JSON Schema** of the arguments). JSON Schema is a general standard, not something specific to AI.
- Good descriptions run **3–4 sentences**: what it does, when to use it, what it returns, plus a description for every argument.
- Shortcut: have Claude write the schema from your function and the tool-use docs.
- Convention: `my_tool` + `my_tool_schema`; wrap with `ToolParam` for type checking.

## L24 handling-message-blocks — Handling message blocks

- Pass `tools=[...]` to `messages.create`.
- A tool-using reply is a **multi-block** assistant message: usually a **text** block plus a **tool_use** block (`id`, `name`, `input`, type `tool_use`).
- Append the **entire** `response.content` to the history, not just the text, or later requests lose the tool call.

## L25 sending-tool-results — Sending tool results

- Run the function with the requested input (`fn(**block.input)`).
- Reply with a **user** message containing a `tool_result` block: `tool_use_id` (must match the request's id), `content` (the output as a string), `is_error`.
- Several tool calls can arrive in one reply; answer each, matched by id.
- The follow-up request must still include the **tools list**, because the history references them.

## L26 multi-turn-conversations-with-tools — Multi-turn conversations with tools

- One question can need several tool calls in sequence ("what day is 103 days from today?" → get the date, then add days).
- So wrap calls in a **loop** that continues while Claude keeps asking for tools.
- Refactor helpers: messages accept strings, block lists or whole `Message` objects; `chat()` accepts `tools` and returns the full message; `text_from_message()` joins the text blocks.

## L27 implementing-multiple-turns — Implementing multiple turns

- Loop condition: continue while `response.stop_reason == "tool_use"`; otherwise it is the final answer.
- `run_tools(message)` handles **every** `tool_use` block and returns one `tool_result` per block (matched ids).
- Wrap each execution in try/except: on failure still return a result, with `is_error: True` and the error text.
- A `run_tool(name, input)` router maps names to functions, so adding tools doesn't touch the loop.

## L28 using-multiple-tools — Using multiple tools

- Adding a tool = write the function, write the schema, add it to the tools list, add a case in `run_tool`.
- Claude chains tools on its own (compute a date, then set the reminder) and mixes text with tool calls in one message.

## L29 fine-grained-tool-calling — Fine grained tool calling

- Streaming tool calls yields `input_json` events with `partial_json` (new chunk) and `snapshot` (accumulated JSON so far).
- By default the API **buffers and validates** each complete **top-level key/value** before sending it, so output arrives in bursts.
- **Fine-grained tool calling** turns that validation off: chunks arrive immediately, but the JSON **may be invalid** (e.g. `undefined`), so your code must handle parse errors.
- Use it only when the buffering delay hurts UX or you must act on partial arguments early.

## L30 the-text-edit-tool — The text edit tool

- A tool whose **schema is built into Claude** (view files or directories, view line ranges, replace text, create files, insert lines, undo edits). You send only a small typed stub whose version string depends on the model.
- **You still implement** the file operations: Claude only emits the requests.
- Useful for building your own editing or coding-agent features where no AI editor is available.

## L31 the-web-search-tool — The web search tool

- A **server tool**: Anthropic runs the search; you only include a schema (`type: web_search_<version>`, `name: web_search`, `max_uses`). An org admin must enable it in the Console first.
- `max_uses` caps how many searches Claude may run; `allowed_domains` restricts sources (e.g. `nih.gov`).
- The response mixes text blocks, the search query used (server tool use), result blocks (titles, URLs) and **citations** with the supporting text. Render sources and inline citations in your UI.

# Module 5 — Retrieval augmented generation (rag)

## L32 introducing-retrieval-augmented-generation — Introducing RAG

- Putting a whole large document into the prompt hits length limits, lowers quality on very long prompts, and costs more time and money.
- **RAG**: pre-split documents into **chunks**; at question time retrieve only the **relevant chunks** and put those in the prompt.
- Pros: focus, scales to huge or many documents, cheaper and faster. Cons: needs preprocessing, a search mechanism, chunks may miss context, many chunking choices to evaluate.

## L33 text-chunking-strategies — Text chunking strategies

- Bad chunking injects the wrong context (the course example: a medical "bug" matched to a software question).
- **Size-based**: fixed length with **overlap**. Simple, works on anything including code, but cuts words and sections.
- **Structure-based**: split on headings or sections. Cleanest, but only when the format is guaranteed (e.g. your own Markdown reports).
- **Semantic**: group related sentences using NLP. Best relevance, most compute and complexity.
- **Sentence-based**: groups of N sentences with overlap. A practical middle ground.
- No universal best. Size-based with overlap is a common, robust production default.

## L34 text-embeddings — Text embeddings

- **Semantic search** compares meaning, not exact words, using **embeddings**: vectors of numbers (roughly −1..1) produced by an embedding model.
- Individual dimensions aren't human-interpretable; they are learned features.
- Anthropic doesn't provide an embedding model; the course uses **VoyageAI** (`voyage-3-large`, separate key in `VOYAGE_API_KEY`).

## L35 the-full-rag-flow — The full RAG flow

1. Chunk the source. 2. Embed each chunk (vectors are **normalized** to length 1). 3. Store them in a **vector database**. *(Preprocessing ends here.)* 4. Embed the user's query with the **same model**. 5. Find the nearest stored vectors. 6. Put the question and the best chunks in the prompt.
- **Cosine similarity** is the cosine of the angle between vectors, from −1 to 1 (1 = very similar, 0 = unrelated). **Cosine distance** = 1 − similarity (0 = very similar).

## L36 implementing-the-rag-flow — Implementing the RAG flow

- Code shape: `chunk_by_section` → batch `generate_embedding(chunks)` → `VectorIndex.add_vector(embedding, {"content": chunk})` → embed the query → `store.search(query_embedding, k)`.
- Store the **original text** (or a reference) with each vector. Numbers alone are useless as prompt context.
- Results come back with distances; lower means closer.

## L37 bm25-lexical-search — BM25 lexical search

- Semantic search can miss **exact identifiers** (an incident ID like `INC-2023-Q4-011`) and return merely related sections.
- **Lexical search with BM25**: tokenize the query, see how often each term appears across documents, weight **rare terms higher** and common words lower, and rank documents by the weighted matches.
- Strong for IDs, technical terms and exact phrases. Run it **alongside** semantic search (hybrid search).

## L38 a-multi-index-rag-pipeline — A multi-index RAG pipeline

- Give every index the same interface (`add_document`, `search`) and wrap them in a **Retriever** that queries all of them and merges the results.
- **Reciprocal Rank Fusion**: `score(d) = Σ 1 / (k + rank_i(d))` over the indexes (k is often 60; the course uses 1 for readability). Documents ranked well by several indexes rise to the top.
- Worked example with k=1: ranks (1,2) → 0.833; (3,1) → 0.75; (2,3) → 0.583.
- New search methods plug in by implementing the same interface.

# Module 6 — Features of Claude (features)

## L39 extended-thinking — Extended thinking

- Claude reasons in a **thinking block** before the final text block. It can be more accurate on hard tasks and makes the reasoning visible.
- Costs: thinking tokens are billed, latency goes up, and response handling is more complex.
- **When**: only after prompt optimization plus evals still fall short.
- Thinking blocks carry a **signature** (a tamper check); a **redacted thinking** block holds encrypted reasoning flagged by safety systems. Pass it back unchanged, and make sure your app handles it.
- Enable with `thinking={"type": "enabled", "budget_tokens": N}`: minimum budget **1024**, and **`max_tokens` must exceed the budget**.
- Not compatible with some features (notably **prefill**) and restricts temperature. Check the docs' compatibility list.

## L40 image-support — Image support

- Send **image blocks** (base64 or URL) alongside text blocks in a user message.
- Limits from the course: up to 100 images per request, 5 MB each, max 8000 px per side for a single image (2000 px when sending several). Cost ≈ `width × height / 750` tokens.
- Prompt engineering still applies: give a **step-by-step method**, **examples** (one-shot with a known answer), and decomposed checks. The course's satellite fire-risk prompt shows a structured rubric (residence, overhang %, fuel ladders, rating 1–4).

## L41 pdf-support — PDF support

- Same pattern as images, but a **`document`** block with media type `application/pdf`.
- Claude reads the text, images, charts, tables and layout of the PDF.

## L42 citations — Citations

- On a document block, add a `title` and `citations: {"enabled": true}`.
- Responses then carry citations with `cited_text`, `document_index`, `document_title` and, for PDFs, `start_page_number`/`end_page_number` (**character positions** for plain-text sources).
- Build UIs where users can hover or verify sources. Use citations when trust, verification or authoritative sources matter.

## L43 prompt-caching — Prompt caching

- Normally the work done on your input is discarded after each response. **Prompt caching** keeps it so identical content in later requests is processed **faster and cheaper**.
- The first request **writes** the cache; later identical prefixes **read** it.
- Default lifetime **5 minutes**, refreshed free on each use; an optional **1-hour** lifetime costs more to write.
- Only pays off when the same content is sent often (e.g. many questions about one big document).

## L44 rules-of-prompt-caching — Rules of prompt caching

- Not automatic: add a **cache breakpoint** (`"cache_control": {"type": "ephemeral"}`) to a block (use the long block form, not the string shorthand).
- Everything **up to and including** the breakpoint is cached; reuse requires that prefix to be **identical** (a single changed word invalidates it).
- Breakpoints can go on system prompts, tool definitions, images, tool use and tool result blocks, and can cover multiple messages.
- Processing order is **tools → system → messages**; up to **4 breakpoints** per request.
- Minimum cacheable length: **1024 tokens** (the total content being cached).

## L45 prompt-caching-in-action — Prompt caching in action

- Cache **tools** by adding `cache_control` to the **last** tool (on a copy, not the original list), and cache the **system prompt** by sending it as a text block with `cache_control`.
- Watch `usage`: `cache_creation_input_tokens` on the first call, `cache_read_input_tokens` after.
- Change the system prompt but not the tools → tools are read from cache and the system prompt is written anew.

## L46 code-execution-and-the-files-api — Code execution and the Files API

- **Files API**: upload a file once and reference it by **file id** instead of re-sending base64.
- **Code execution**: a server tool; Claude runs Python in an **isolated container without network access**, possibly several times per answer.
- Together: upload data → add a `container_upload` block with the file id → Claude analyses it with code → generated files (e.g. plots) come back as ids you download via the Files API.
- Response blocks: text, server tool use (the code), code execution results.

# Module 7 — Model Context Protocol (mcp)

L47 `introducing-mcp`, L48 `mcp-clients` and L50–L56 (tools, inspector, client, resources, prompts) are covered in the MCP course notes.

## L49 project-setup — Project setup

- Course project: a **CLI chatbot** over in-memory documents, with **both** an MCP client (user interaction) and an MCP server (document read and edit tools). Real projects usually build only one side.
- Setup: key in `.env`, install dependencies (uv recommended), run `uv run main.py` (or `python main.py`).
- **Verify the baseline**: ask something with a known answer (e.g. 1+1) and check it's *correct*, not just that a reply appeared. Before the tools exist, questions about the documents are answered by the model alone.
- Habit: every time you add a layer (tool, data source, server), ask one question whose answer you already know before building the next.

# Module 8 — Agents and workflows (agents)

## L57 anthropic-apps — Anthropic apps

- Two Anthropic products serve as agent case studies: **Claude Code** (terminal coding agent) and **Computer Use** (tools to operate a desktop through screenshots, clicks and typing).
- What makes them work: tool use, multi-step execution, interaction with an environment, autonomous problem solving.

## L58 claude-code-setup — Claude Code setup

- Claude Code: file search/read/edit, terminal commands, web access, and **MCP servers** for more tools.
- Runs on macOS, Linux and Windows (the course shows installing Node.js, then `npm install -g @anthropic-ai/claude-code`, then running `claude` and logging in; the docs list current install methods).

## L59 claude-code-in-action — Claude Code in action

- `/init` scans the codebase and writes **CLAUDE.md** (build commands, conventions, architecture), which is loaded into future sessions. Scopes: **project** (shared), **local** (personal, git-ignored), **user** (all projects).
- `#` quickly adds a note to a CLAUDE.md; `/clear` resets the conversation.
- Effective workflow: **feed context** (point at relevant files) → **ask for a plan, no code yet** → **implement**.
- TDD variant: context → brainstorm test cases → write the tests → write code until they pass.

## L60 enhancements-with-mcp-servers — Enhancements with MCP servers

- Claude Code has a built-in MCP client: `claude mcp add <name> <command...>` (e.g. `claude mcp add documents uv run main.py`); it connects at startup.
- Servers can bring tools, prompts and resources. Examples: Sentry (errors), Playwright (browser), Figma, Atlassian (Jira/Confluence), Firecrawl (scraping), Slack.
- Combine servers to fit your workflow (ticket → code → error data → team notification).

## L61 agents-and-workflows — Agents and workflows

- Both handle tasks too big for one request.
- **Workflow**: a predetermined series of Claude calls, used when you can picture the steps (or the UX limits the tasks). **Agent**: a goal plus tools, and Claude decides the steps, used when tasks are open-ended.
- **Evaluator–optimizer** pattern: a producer creates output, a grader checks it, feedback loops back until accepted (course example: image → description → CadQuery model → render → compare with the image).

## L62 parallelization-workflows — Parallelization workflows

- Split one complex decision into **independent sub-tasks run in parallel**, each with its own specialized prompt (e.g. one call per candidate material), then **aggregate** in a final call.
- Benefits: focused attention, each prompt optimized separately, easy to add options, more reliable than one giant prompt.

## L63 chaining-workflows — Chaining workflows

- Break a big task into **sequential** focused steps, optionally with non-LLM processing in between (find trends → pick topic → research → script → render video → post).
- Fix for long prompts whose constraints get ignored: generate first, then run a **second, targeted revision call** ("remove AI self-references, remove emojis, replace clichés").

## L64 routing-workflows — Routing workflows

- First call **classifies** the request into a fixed set of categories; the input then goes to **one** specialized pipeline (prompt, tools, flow) for that category.
- Good for diverse request types (support bots, content tools) when categorization is reliable.

## L65 agents-and-tools — Agents and tools

- An agent's strength comes from **combining tools** in ways not planned in advance (datetime tools → "what weekday in 11 days?", "remind me next Wednesday"). Agents can also ask the user for missing information.
- Prefer **abstract, composable tools** (Claude Code's bash, read, write, edit, glob, grep) over hyper-specific ones ("refactor code").

## L66 environment-inspection — Environment inspection

- Agents act blindly unless they can **observe the results** of their actions: screenshots after each computer-use action, **read before write** for files, checking API responses.
- Tell the agent in the system prompt how to verify (e.g. extract frames with FFmpeg, transcribe audio to check timing).
- Always ask: "How will Claude know this action worked?"

## L67 workflows-vs-agents — Workflows vs agents

- Workflows: higher accuracy (one focused subtask at a time), easier to test and evaluate, predictable, but less flexible and need upfront design.
- Agents: flexible, handle novel tasks and can ask for input, but have lower task success rates and are harder to test and instrument.
- Recommendation: **prefer workflows** whenever possible; use agents only when truly needed. Users want reliability, not cleverness.
