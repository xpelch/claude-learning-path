# Labs: Building with the Claude API

All labs use `chat_helpers.py` in the user's lab folder unless stated. Keep datasets and loops small: calls are billed.

---

## first-request: First request, multi-turn chat and a system prompt

Module 1 (L1–L6).

**Steps for the user**
1. Send one request and print `response.content[0].text` plus `response.usage` and `response.stop_reason`.
2. Show statelessness: ask "Define recursion in one sentence", then in a **new** request only "Give another example". Then redo it by appending the assistant reply and the follow-up to the **same** message list.
3. Add a system prompt making Claude a tutor who gives hints, not answers; compare with and without it on "How do I solve 3x + 5 = 20?".
4. Run the same creative prompt at temperature 0 and 1, three times each, and describe the difference.
5. Bonus: stream a reply with `client.messages.stream(...)` and `text_stream`, then call `get_final_message()`.

**Pass when:** step 2 shows the difference between the two approaches, step 3 changes the behaviour, and the user explains why temperature 1 doesn't *guarantee* different outputs.

---

## structured-output: Get clean JSON back with prefill and stop sequences

Module 1 (L8).

**Steps**
1. Ask for "a short JSON object describing a fictional book (title, author, year)" and show the default output (usually fenced, with commentary).
2. Apply the course technique: append an assistant message with ```` ```json ```` and pass `stop_sequences=["```"]`; `json.loads(text.strip())` must succeed.
3. Write `generate_json(prompt) -> dict` that retries once if parsing fails.
4. If the API rejects assistant prefill for the chosen model, look up the current structured-output option in the docs and use it instead. Explain the difference.

**Pass when:** `generate_json` returns a dict for three different prompts with no Markdown or prose around it.

---

## eval-pipeline: Build a small eval pipeline with code and model graders

Module 2 (L9–L14).

**Goal:** measure a prompt that must return **only** Python, JSON or a regex.

**Steps**
1. Generate a dataset of **4** tasks with a fast model (each `{"task": ..., "format": "python"|"json"|"regex"}`) and save `dataset.json`.
2. `run_prompt(case)`, `run_test_case(case)`, `run_eval(dataset)` as in the course.
3. Code grader: parse with `ast.parse` / `json.loads` / `re.compile` → 10 or 0.
4. Model grader returning JSON with `strengths`, `weaknesses`, `reasoning`, `score`.
5. Final score = the average of both; print the average across the dataset.
6. Improve the prompt **once** (e.g. "respond only with …, no commentary" plus a prefilled fence) and re-run.

**Pass when:** both runs print an average, the second is higher (or the user explains why not), and they can say why the grader asks for reasoning.

---

## tool-loop: Implement a multi-tool conversation loop

Module 4 (L20–L28).

**Steps**
1. Write `get_current_datetime(date_format)` and `add_duration_to_datetime(datetime_str, duration, unit)` with input validation and clear errors, plus JSON schemas (name, 3–4 sentence descriptions, `input_schema`).
2. `run_tools(message)`: one `tool_result` per `tool_use` block (matching `tool_use_id`), `json.dumps` of the output, `is_error: True` with the message on exceptions.
3. `run_conversation(messages)`: loop while `stop_reason == "tool_use"`, appending the **full** assistant content and the tool results, always passing the tools.
4. Test: "What day of the week is it 103 days from today?" and "What time is it in HH:MM format?".
5. Error test: temporarily make one tool raise, and show that Claude receives `is_error` and reacts.

**Pass when:** both questions are answered correctly through the tools (print each tool call), and step 5 doesn't crash the loop.

---

## hybrid-retrieval: Hybrid retrieval with BM25 and reciprocal rank fusion

Module 5 (L32–L38). No API key needed.

**Steps**
1. In `retrieval_exercise.py`, implement `chunk_by_section`, `rrf_scores` and `fuse`.
2. Run `python retrieval_exercise.py`: all four lines must print `ok`.
3. Explain: why does the incident id favour lexical search? Why fuse by rank instead of adding raw scores? What does k change?
4. Bonus (needs a VoyageAI key the user sets up themselves): add a vector index and fuse both rankings.

**Pass when:** four `ok` lines and correct answers to step 3.

---

## prompt-caching: Measure prompt caching on tools and system prompt

Module 6 (L43–L45).

**Steps**
1. Build a system prompt above the minimum cacheable size (the course states 1024 tokens; the minimum can differ by model, so check the docs), e.g. a long style guide.
2. Send it as a text block with `cache_control: {"type": "ephemeral"}`; add `cache_control` to a **copy** of the last tool definition too.
3. Call twice and print `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens`.
4. Change one word in the system prompt and call again: which part is read from cache and which is written?

**Pass when:** the second call shows cache reads, step 4 shows tools read and system prompt written, and the user explains the tools → system → messages order.

---

## workflow-patterns: Choose and build a workflow pattern

Module 8 (L61–L67).

**Steps**
1. The user picks a small real task from their work and decides between **chaining**, **routing**, **parallelization** and **evaluator–optimizer**, or an **agent**, justifying the choice with the course's criteria (can you picture the steps?).
2. Implement it with 2–4 Claude calls (e.g. routing: classify into 3 categories, then a specialized prompt per category; chaining: generate, then a targeted revision pass).
3. Run it on 3 inputs and show intermediate outputs.

**Pass when:** the pattern fits the task (with an explicit reason), the code runs on 3 inputs, and the user can name one benefit and one downside of choosing a workflow over an agent here.
