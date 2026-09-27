# Cross-Organization Insurance Claim Verification — A2A Project

## Problem Statement

An insurance company processes a car accident claim that includes a claimed injury and claimed vehicle damage. Verifying these claims genuinely requires two outside organizations — a hospital (to confirm the injury) and a repair shop (to assess vehicle damage) — that will never share a database or codebase with the insurance company, for real legal and business reasons (patient privacy law, competitive separation, independent infrastructure).

Today, this verification is largely manual: prescriptions, medical bills, and repair estimates are emailed or faxed between organizations, and a human reviews them by hand — slow, and not scalable across many partner hospitals/repair shops.

**What this project builds:** an Agent2Agent (A2A) system where the Insurance company's own agent can ask a specific verification question directly to an independent Hospital agent (and, later, a Repair Shop agent), each hosted on separate cloud infrastructure, built with separate agent frameworks, each keeping full control of its own private data — getting back only a narrow answer (does this diagnosis match this claim?) in real time, instead of a manual, multi-day document exchange.

## Tech Stack

**Insurance side (AWS):**
- Agent logic: CrewAI
- Data: Amazon RDS (Postgres) — claims table
- Hosting: AWS Lambda behind API Gateway
- Logging: CloudWatch

**Hospital side (GCP):**
- Agent logic: LangGraph (chosen for its fixed, auditable step-by-step flow — appropriate for a verification decision that must be explainable the same way every time)
- Data: synthetic medical records, embedded for RAG-based search
- Hosting: Cloud Run
- LLM: Vertex AI (Gemini)
- Logging: Cloud Logging

**Cross-cutting:**
- A2A layer: official `a2a-sdk` (Python) on both sides — Agent Card + task/message handling
- Auth: credential (API key) issued when the partnership is set up, checked on every incoming request

## Step 1 — Hospital's synthetic medical records data

**What we did:** created a small, realistic dataset of synthetic patient records belonging entirely to the Hospital side — this is the data the Hospital Agent will later search against (via RAG) when the Insurance Agent asks it to verify a claimed injury. This dataset never leaves the Hospital's own environment.

**Columns:**
- `patient_name`
- `diagnosis`
- `treatment_date`
- `doctor_notes`

**Why this had to come before any agent code:** the Hospital Agent's whole purpose is to check a claim against real records — there's nothing to check against until this data exists.

## Step 2 — Turn the medical records into searchable embeddings (RAG groundwork)

**What we did:** converted each medical record's diagnosis + doctor's notes into an embedding (a numeric representation of its meaning), so a future claim description can be compared against all records by meaning, not exact wording.

**File created:** `hospital-agent/build_embeddings.py`

**Methods used:**
- `TextEmbeddingModel.from_pretrained("text-embedding-004")` (Vertex AI) — generates one embedding per record's combined diagnosis + doctor's notes text.
- `chromadb.PersistentClient` — stores each embedding, along with the patient name/diagnosis/treatment date as metadata, in a local vector store.

**Where saved:** `hospital-agent/chroma_store/` — a local Chroma vector database folder.

**Why this comes before the agent logic:** the Hospital Agent's reasoning flow (Step 3) needs a search tool to call — this step is what creates that tool's underlying data.

**Code walkthrough (high level):**
1. Connect to Vertex AI using the project ID and region.
2. Load the `text-embedding-004` embedding model.
3. Read `medical_records.csv` into a table.
4. For each patient row, combine `diagnosis` + `doctor_notes` into one text block, send it to the embedding model, and get back a list of numbers representing its meaning.
5. Save that record (the embedding plus patient name/diagnosis/treatment date as metadata) into the local Chroma vector store.

**Result:** confirmed by actually running the script — "Stored 10 records in Chroma vector store at .../hospital-agent/chroma_store". All 10 synthetic patient records embedded and stored, ready for similarity search in Step 3.

## Step 3 — Build the search function (semantic, not keyword or hybrid)

**What we did:** built `search_claim()`, which takes a claimed injury description, embeds it the same way as Step 2's records, and finds the closest matching record in `chroma_store` by meaning.

**File created:** `hospital-agent/search_records.py`

**Code walkthrough (high level):**
1. Connect to Vertex AI, load the same `text-embedding-004` model used in Step 2 (must match, or comparisons aren't meaningful).
2. Open the existing Chroma vector store from Step 2 (`chroma_store/`).
3. `search_claim()` takes the claimed injury description as text.
4. Embed that text using the same model — turning the claim description into a number-list, same format as the stored records.
5. `collection.query()` compares that embedding against all 10 stored embeddings using cosine similarity, returns the closest match(es) plus their distance scores.

**Search type used:** pure semantic (vector) search — not keyword matching, not hybrid. A query like "neck pain after being rear-ended" can match a record even if it shares no exact words with it, because the comparison is done on embeddings (meaning), not text.

**Methods used:**
- `TextEmbeddingModel.get_embeddings()` — embeds the incoming claim description the same way records were embedded in Step 2.
- `collection.query()` (Chroma) — compares the query's embedding against all stored embeddings using cosine similarity, returns the closest match(es).

**Result:** tested with the query "patient reported neck pain after being rear-ended" — correctly returned a whiplash-diagnosed record (Sarah Wilson, distance 0.409) as the closest match out of all 10 records (which include fractures, concussions, back strain, and knee injury) — confirming the semantic search correctly distinguishes between diagnosis types, not just returning arbitrary results.

**Noted for later, not yet built:** for genuine production scale (millions of records), this local Chroma approach would need to move to Vertex AI Vector Search (a managed, scalable vector database) with a batch embedding pipeline and incremental updates — deferred for now to keep the initial end-to-end build simple, since Vertex AI Vector Search has real ongoing hosting cost.

**Key parameters/concepts in this step:**
- **`top_k`** — how many closest matches to return (set to 1 here; configurable to return more candidates).
- **`PersistentClient`** — tells Chroma to save the vector store to disk (`chroma_store/`), so it survives after the script ends, unlike an in-memory client which would lose everything on exit.
- **Why cosine similarity, not another distance metric:** cosine similarity compares the *angle* between two embeddings, ignoring magnitude — text embeddings' magnitude can vary for reasons unrelated to meaning (like text length), so comparing angle is the standard, more reliable choice for text search, which is why it's Chroma's (and most vector databases') default.

## Step 4 — Hospital Agent's decision flow (LangGraph)

**Why this step is needed:** `search_claim()` only returns "here's the closest record and a distance score" — nothing yet decides whether that counts as a real match, or turns it into a usable answer. This step is what makes the actual verification decision.

**File created:** `hospital-agent/verification_flow.py`

**High-level flow (fixed checklist, same steps/order every run):**
1. Receive claim details — patient name, claimed injury, accident date.
2. Call `search_claim()` (Step 3) to find the closest medical record.
3. Check: is the found record's distance below a fixed threshold (`0.5`)? → `diagnosis_match`.
4. Check: is the gap between accident date and treatment date within a fixed limit (`2 days`)? → `date_match`.
5. Combine both checks into a final `confidence` score and one of 3 decisions: `match`, `needs_review`, or `no_match`.

**Methods used:**
- `langgraph.graph.StateGraph` — defines the fixed node sequence (`search` → `check_diagnosis` → `check_date` → `compute_confidence`), each node reading/writing to one shared `ClaimState`.
- Fixed rules, not free-text LLM judgment, for both checks — this is what makes the same claim always produce the same decision (the auditability requirement discussed earlier).

**Decision rules:**
- Diagnosis doesn't match → `confidence = 0.0`, decision = `no_match`
- Diagnosis matches but date doesn't → reduced confidence, decision = `needs_review` (flagged for a human)
- Both match → `confidence = 1 - distance`, decision = `match`

**What "confidence" actually means:** a number from 0 to 1 representing how sure the system is that the claim genuinely matches a real record — higher means more certain. It's calculated as `1 - distance`, since distance measures how *different* two things are (0 = identical meaning), so flipping it turns "difference" into "similarity." When the date doesn't match, an extra 0.3 penalty is subtracted, reflecting reduced certainty even when the diagnosis text looks similar.

**Code walkthrough (high level, post-fix), with the exact methods used at each step:**
1. `ClaimState` (a `TypedDict`) defines the shared data structure every node reads from and writes to — patient name, claimed injury, accident date, plus fields filled in as the flow runs (found diagnosis, distance, match flags, confidence, decision).
2. `search_node(state)` — calls `search_claim(claimed_injury, patient_name, top_k=1)`, now passing `patient_name` too, so Chroma's `where={"patient_name": patient_name}` filter restricts the search to only that one patient's records before comparing anything. If no record exists for this patient at all, it stores `None`s instead of crashing.
3. `diagnosis_check_node(state)` — reads `state["distance"]` and sets `diagnosis_match = distance <= 0.5`. Guards against `distance is None` (no record found) by setting `diagnosis_match = False` safely.
4. `date_check_node(state)` — uses `datetime.strptime()` to parse both the claimed accident date and the found record's treatment date, subtracts them to get a day-gap, sets `date_match = gap_days <= 2`. Same `None`-safety guard as above.
5. `confidence_node(state)` — reads both match flags and decides the final `confidence` (number) and `decision` (label): `no_record_found`, `no_match`, `needs_review`, or `match`.
6. `StateGraph` wires these 4 functions into a fixed sequence (`search → check_diagnosis → check_date → compute_confidence → END`) via `graph.add_edge(...)` calls — every call to `verification_app.invoke(...)` runs through this exact same sequence, in this exact same order, every time.

**First test result — and a real bug it exposed:** ran the flow for John Doe's claim ("neck pain after being rear-ended", accident date 2026-01-15). It returned `found_diagnosis: whiplash`, `date_match: False`, `decision: needs_review` — but the record it actually found belonged to **Sarah Wilson**, a completely different patient, matched purely because her doctor's notes sounded similar. The date check happened to catch that something was off (30-day gap), but that was luck, not design — `search_node` never compared `patient_name` at all.

**Fix applied:**
- `search_records.py`: `search_claim()` now takes a `patient_name` argument and passes `where={"patient_name": patient_name}` into Chroma's query — restricting the search to only that patient's own records before any diagnosis comparison happens.
- `verification_flow.py`: `search_node` now passes `state["patient_name"]` into the search, and all 3 downstream nodes (`diagnosis_check_node`, `date_check_node`, `confidence_node`) were updated to handle the case where a patient has **no records at all** (a new `no_record_found` decision), instead of crashing on a missing value.

**How this would be validated at real scale (not just this one example):**
- Build a small "golden set" of test claims with known-correct answers — a genuine match, a patient with zero records, a correct patient with a mismatched date — and run the flow against all of them automatically, checking the output matches every time.
- At production scale, periodically sample-check a random subset of live results, and track aggregate metrics over time (e.g., what % of claims come back `no_match`) — a sudden shift signals something broke, without needing to check every record by hand.
- Specifically test the `patient_name` filter's reliability once real scale introduces the possibility of two different patients sharing the exact same name.

**Result after the fix — confirmed correct:** re-ran John Doe's claim. The search now correctly found **John Doe's own** whiplash record (treatment date 2026-01-16, 1 day after the claimed accident date) instead of a different patient's. Both checks passed (`diagnosis_match: True`, `date_match: True`), giving `confidence: 0.55` and `decision: match` — proving the `patient_name` filter fix resolved the cross-patient mismatch bug.

## Step 5 — Expose the Hospital Agent as an actual A2A endpoint

**Files created:** `hospital-agent/agent_card.py`, `hospital-agent/a2a_server.py`

**What we did, high level:** `agent_card.py` is the Hospital Agent's public "business card" — a description of who it is and what it can do, published at a known address so other agents can discover it before ever talking to it. `a2a_server.py` is the actual running program that answers when someone calls.

**`agent_card.py` — what each piece does:**
- `AgentCard` (from `a2a.types`) — the manifest object itself: `name`, `description`, `url` (where to reach it), `capabilities` (streaming turned off, since our flow returns one final answer, not a live stream).
- `AgentSkill` — describes one specific thing the agent can do; we defined one, `verify_claim`, with its own `id`, `name`, `description`, and `tags` so another agent scanning the card knows exactly what to ask for.
- `AgentCapabilities` — a small settings object (just `streaming: False` here) telling callers how responses will be delivered.

**`a2a_server.py` — what each piece does:**
- `AgentExecutor` (base class from the SDK) — we extend it as `HospitalVerificationExecutor`; this is the required shape the SDK expects any agent's logic to fit into.
- `execute(context, event_queue)` — the one method we implement: reads the incoming text via `context.get_user_input()`, splits it into `patient_name`/`claimed_injury`/`accident_date`, and this is where our *actual* work happens.
- `verification_app.invoke({...})` — calls Step 4's real LangGraph flow (search → check diagnosis → check date → compute confidence) with those 3 values.
- `event_queue.enqueue_event(new_agent_text_message(...))` — packages the result and sends it back to whoever asked.
- `DefaultRequestHandler` — the SDK's built-in traffic router; connects incoming A2A requests to our executor.
- `InMemoryTaskStore` — keeps track of in-progress/completed tasks, stored in memory (fine for now; a real production system would use a persistent store instead).
- `A2AStarletteApplication(agent_card=AGENT_CARD, http_handler=request_handler)` — combines the Agent Card and the request handler into one actual web application.
- `uvicorn.run(app.build(), host="0.0.0.0", port=8080)` — starts the real HTTP server, listening on port 8080 — this is what made the agent reachable when we tested it.

**Real bug hit and fixed — a repeat of the Part 2 SageMaker SDK lesson:** `pip install a2a-sdk` grabbed the latest version (1.1.2), which is a completely restructured, gRPC/protobuf-based rewrite — `a2a.server.apps.A2AStarletteApplication` doesn't exist in that version at all. **Fixed by pinning to `a2a-sdk==0.2.16`**, the version matching the widely-documented tutorial API this code was written against.

**Result — confirmed working:** started the server successfully (`Uvicorn running on http://0.0.0.0:8080`), then fetched `http://localhost:8080/.well-known/agent.json` from a separate terminal and got back `200 OK` with the correct Agent Card JSON — proving the Hospital Agent is genuinely discoverable over HTTP, not just running locally in theory.

**Next:** send an actual verification task to this running agent (not just fetch its card) — full end-to-end test of the A2A flow.

## Step 6 — Full end-to-end A2A test: a real client talking to the running agent

**File created:** `hospital-agent/test_client.py` — simulates what the Insurance Agent will eventually do.

**Real bug hit while building this:** guessed the client's class name and method signatures from memory, same risk as the server earlier. Instead of guessing, read the installed `a2a-sdk==0.2.16` package's actual source (`a2a/client/client.py` and `a2a/types.py`) to confirm the exact real classes and fields needed — `A2AClient`, `Message`, `MessageSendParams`, `Part`, `TextPart`, `Role`, `SendMessageRequest` — before writing any code.

**What the client does:**
1. `A2AClient.get_client_from_agent_card_url()` — fetches the Agent Card from `http://localhost:8080` and builds a client pointed at it.
2. Constructs a `Message` containing one `TextPart`: `"John Doe|patient reported neck pain after being rear-ended|2026-01-15"`.
3. Sends it via `client.send_message()` — a real JSON-RPC `message/send` request over HTTP.

**Result — confirmed working, genuine end-to-end success:** the running server received the request, ran it through the full LangGraph verification flow internally, and returned:
```
decision=match, confidence=0.55, found_diagnosis=whiplash, found_treatment_date=2026-01-16
```
— the exact same correct result validated locally in Step 4, now delivered over the real A2A protocol between two separate processes, not a local function call. This is the first genuine proof that the Hospital Agent works as an actual A2A service.

## Step 7 — Insurance side: claims table

**Cost decision:** rather than a new AWS RDS instance (continuous hourly cost), reused the local Docker Postgres already running from the truck delay project — a `claims` table added there, at zero extra cost.

**What we did:** created a `claims` table (`claim_id`, `patient_name`, `claimed_injury`, `accident_date`, `claim_amount`, `status`), and inserted one sample claim for John Doe — the same patient/injury/date already validated against the Hospital Agent, so the two sides can be tested together end-to-end.

**Result:** confirmed via `SELECT * FROM claims;` — 1 row present, `status = 'submitted'`.

**Next:** build the Insurance Agent itself (CrewAI) — reads this claim, calls the Hospital Agent via A2A (reusing the `test_client.py` pattern), and updates the claim's status based on the response.

## Step 8 — Insurance Agent (CrewAI)

**Verified before writing code:** checked the actually-installed `crewai==1.15.21` package's real class fields (`Agent.model_fields`, `Task.model_fields`, `Crew.model_fields`) rather than assuming an API from memory — same discipline that caught the a2a-sdk version mismatch earlier.

**Files created:**
- `insurance-agent/hospital_tool.py` — a bridge. Wraps the already-working A2A client call to the Hospital Agent (from Step 6's `test_client.py`) as a "tool" the Insurance Agent's AI can call whenever it decides it needs to verify something.
- `insurance-agent/claims_agent.py` — the actual Insurance Agent. Pulls a claim's details from Postgres, hands the job to an AI agent (Claude, via AWS Bedrock) with instructions to verify it using the hospital tool, then updates the claim's status based on what comes back.

**`hospital_tool.py` — what each piece does:**
1. `_call_hospital_agent()` — the same A2A client logic from `test_client.py`, turned into a reusable async function taking parameters instead of hardcoded values.
2. `@tool("Verify claim with hospital")` (from `crewai.tools`) — turns a plain Python function into something the Agent can call as a tool; the docstring becomes the description the LLM reads to decide *when* to use it.
3. `asyncio.run(...)` — bridges the gap between A2A's async client and CrewAI's synchronous tool-calling.

**`claims_agent.py` — what each piece does:**
1. `engine = create_engine(...)` — connects to the local Postgres `claims` table (same pattern as the truck project).
2. `Agent(role=..., goal=..., backstory=..., tools=[...], llm="bedrock/anthropic.claude-3-sonnet-...")` — defines the AI agent itself: its purpose, and that it has access to the one hospital-verification tool.
3. `get_claim()` / `update_claim_status()` — plain SQL to read a claim's details and write the final decision back.
4. `Task(description=..., expected_output=..., agent=claims_agent)` — the plain-English instructions given to the agent for this specific claim.
5. `Crew(agents=[...], tasks=[...], process=Process.sequential).kickoff()` — actually runs the agent against the task.
6. Result text is checked for `decision=match`/`needs_review`/other, and the claim's status is updated accordingly.

**CrewAI concepts, high level:**
- **Agent** — the "who": the AI worker itself, with a role, a goal, and access to tools.
- **Task** — the "what": the specific job assigned to that agent for one run.
- **Crew** — the "team": bundles agent(s) + task(s) together and actually runs them.
- **Process** — the "order of operations": `sequential` runs tasks one after another; `hierarchical` (not used here) would have a manager agent delegating — only relevant with multiple agents/tasks.

**Bedrock path attempted, then abandoned — real account-level blocker:** added `AmazonBedrockFullAccess` to the IAM user and submitted Anthropic's required "use case details" form, but every model tried (`claude-3-sonnet`, `claude-3-5-sonnet-v2`, then the current `claude-sonnet-5`) failed. Diagnosed step by step, confirming each theory with a direct `boto3` call before changing code:
- First two model IDs: "this model version has reached end of life" — those specific dated snapshots were retired.
- `claude-sonnet-5` bare model ID: `PermissionError: not available for this account` — confirmed via `list_foundation_models(byProvider='Anthropic')` that the model itself existed and was `ACTIVE`, so the block wasn't the model name.
- Queried `list_inference_profiles()` directly and found newer Claude models are only invocable through a **cross-region inference profile ID** (prefixed `eu.` or `global.`), not the bare model ID — switching to `eu.anthropic.claude-sonnet-5` got past that specific error.
- Region mismatch next: CrewAI's Bedrock provider defaults its `boto3` client to `us-east-1` unless `region_name` is passed explicitly, but the model string was an `eu.` profile — fixed by wrapping the model in CrewAI's own `LLM(model=..., region_name="eu-north-1")` object instead of a bare string.
- Final blocker was AWS-account-level, not code: `INVALID_PAYMENT_INSTRUMENT` — AWS Marketplace (which Bedrock model subscriptions bill through) rejected the account's card because it's registered under India's RBI **e-mandate** recurring-payment rule, which Marketplace's one-time variable-amount charges can't authorize. A direct `bedrock-runtime.converse()` call confirmed this independent of any CrewAI code. Retrying later returned an even broader `Error 002: Access to Bedrock models is not allowed for this account` — an account-level restriction needing AWS Support to lift, not something fixable from the console or code.

**Decision:** switched the Insurance Agent's LLM from AWS Bedrock to the **Anthropic API directly** (a separate provider, no AWS billing involved) to keep moving without waiting on AWS Support. This only changes one line (`llm="claude-sonnet-5"` instead of a Bedrock-wrapped `LLM(...)` object) — everything else (CrewAI `Agent`/`Task`/`Crew`, the hospital tool, A2A calls) is identical either way, since the LLM provider is swappable by design.

**Further real bugs hit and fixed getting the direct API path working:**
- CrewAI's native Anthropic provider raised `ImportError: Anthropic native provider not available` — traced to the installed `anthropic` Python package (0.64.0) missing a function (`transform_schema`) that CrewAI's wrapper imports; fixed by upgrading the `anthropic` package.
- Next, every call failed with a generic `Connection error` (not an auth error) — isolated by testing the Anthropic SDK directly outside CrewAI, then getting the *real* underlying exception via `exception.__cause__`, which revealed `TypeError('process() takes no keyword arguments')` coming from inside `httpx2`'s response decompression path (`httpx2` is the Anthropic SDK's actual, newer HTTP client dependency — not the more commonly known `httpx` package). Root cause: the API's response was Brotli-compressed, and the installed `brotli` Python package's decompressor doesn't support the keyword argument `httpx2` calls it with — only the `brotlicffi` variant does. Fixed by uninstalling `brotli` and installing `brotlicffi` instead.
- Wrong model ID string for the direct API (`claude-sonnet-5-20250929` doesn't exist on the direct API, only on Bedrock's inference profiles) — found the correct bare ID (`claude-sonnet-5`) by calling `client.models.list()` against the account directly instead of guessing.

**Result — first genuine successful end-to-end run:** `claims_agent.py` executed the full chain for Claim 1 — CrewAI Agent called `verify_claim_with_hospital`, which reached the real Hospital Agent over A2A and got back `decision=match, confidence=0.55, found_diagnosis=whiplash, found_treatment_date=2026-01-16` — the LLM then wrote a narrative summary recommending manual review given the moderate confidence.

**A second real bug found from that first run — status logic mismatch:** the claim was written to the database as `status = "rejected"` despite the hospital returning `decision=match`. Root cause: the status-decision code checked `"decision=match" in result_text`, but `result_text` was the LLM's paraphrased final answer ("Hospital Decision: MATCH" in prose), which never contains the literal substring `"decision=match"` — only the raw tool output does.

**Fix applied:**
- `hospital_tool.py` now sets a module-level `last_raw_response` variable to the exact raw string returned by the Hospital Agent every time the tool is called (or a descriptive `error=...` string if the A2A call itself fails, e.g. the server isn't running) — giving `claims_agent.py` a way to read the real machine-readable result, separate from the LLM's human-readable narration of it.
- `claims_agent.py`'s status logic now reads `hospital_tool.last_raw_response` instead of the LLM's output text for its `decision=match` / `decision=needs_review` checks.

**Result after the fix — confirmed correct:** re-ran Claim 1 — raw hospital response unchanged (`decision=match, confidence=0.55, ...`), but the claim was now correctly written to the database as `status = "approved"`.

## Step 9 — Debug/demo UI (Streamlit)

**Why built:** to see the whole cross-organization flow happen visually, one step at a time, instead of only reading terminal logs — and to easily test both correct and deliberately wrong claim data without touching the database.

**File created:** `insurance-agent/app.py`

**Two tabs, two different purposes:**
1. **"Direct A2A test (no LLM, fastest)"** — calls `verify_claim_with_hospital.func(...)` directly, bypassing CrewAI and the LLM entirely. Lets you type any `patient_name`/`claimed_injury`/`accident_date` combination — including a nonexistent patient, a mismatched injury, or a far-off date — and see the Hospital Agent's real raw response immediately, at zero LLM cost. Also surfaces the connection-error path cleanly (e.g. what happens if `a2a_server.py` isn't running).
2. **"Full Insurance Agent flow (CrewAI + DB)"** — picks a real claim from the Postgres `claims` table, runs the entire CrewAI → A2A → LangGraph chain, and shows each stage as its own labeled step (claim fetched, LLM's narrative answer, raw hospital response used for the actual decision, final DB status written) inside a live `st.status(...)` block, plus a full captured console log in an expander.

**Real bug hit while building this — CrewAI tool objects aren't plain functions:** calling `verify_claim_with_hospital(...)` directly (outside of an `Agent`/`Task`) failed, because `@tool(...)` wraps the function into a CrewAI `Tool` object, not the original callable. Fixed by calling `.func(...)` on it, after checking the actual attributes available on that `Tool` object (`dir(sample_tool)`) rather than guessing.

## Appendix — A2A Protocol, Agent Card, CrewAI, and LangGraph (interview reference)

### What problem A2A actually solves

Two organizations (Insurance, Hospital) each run their own AI agent, on separate cloud accounts, in separate codebases, that can never share a database — for real legal reasons (patient privacy law) and business reasons (competitive separation). A2A is a protocol that lets one organization's agent ask another organization's agent a question and get a structured answer back, without either side needing to see the other's internal code, data, or infrastructure. This is different from Model Context Protocol (MCP), which connects one agent to its own tools/data sources — A2A specifically connects one agent to a *different, independently-operated* agent.

### The Agent Card and the discovery handshake

Before the Insurance Agent can ask the Hospital Agent anything, it needs to know: where to send requests, what the Hospital Agent is even capable of answering, and how responses will be delivered. This is what the **Agent Card** solves — a small JSON document published at a fixed, well-known path (`/.well-known/agent.json`) on the Hospital Agent's server.

In this project, `agent_card.py` builds this card from three pieces:
- `AgentCard` — the top-level manifest: `name`, `description`, `url` (where to actually send requests), and `capabilities`.
- `AgentSkill` — one specific capability the agent offers; here, a single skill called `verify_claim`, with its own `id`, `name`, `description`, and `tags`, so a caller scanning the card knows exactly what question this agent can answer.
- `AgentCapabilities` — delivery settings; `streaming: False` here, meaning the agent always returns one final answer rather than a live stream of partial results.

The **handshake** itself, done automatically inside `A2AClient.get_client_from_agent_card_url(httpx_client, "http://localhost:8080")`, is: the client sends a plain HTTP `GET` to `http://localhost:8080/.well-known/agent.json`, parses the returned Agent Card JSON, and uses its `url` field to know where to send the actual verification request next. This is a discovery step, not authentication — it answers "what can you do and where do I send my request," not "am I allowed to talk to you." (In this project, no additional credential check runs on top of it yet — the Tech Stack section above notes an API key credential as the intended production auth layer, not yet implemented.)

### The actual request/response — JSON-RPC over HTTP

Once the client has the Hospital Agent's URL, sending an actual message means:
1. Building a `Message` object containing one or more `Part`s — here, a single `TextPart` with plain text like `"John Doe|patient reported neck pain after being rear-ended|2026-01-15"`.
2. Wrapping that in a `SendMessageRequest` with a unique `id`.
3. Calling `client.send_message(request)` — this sends a JSON-RPC 2.0 `message/send` request over a plain HTTP POST to the Agent Card's URL.

On the receiving side, `a2a_server.py` wires this up with three SDK pieces:
- `AgentExecutor` — the abstract base class the SDK requires; the Hospital side implements it as `HospitalVerificationExecutor`, with one required method, `execute(context, event_queue)`, containing the actual business logic (here: parse the incoming text, run it through the LangGraph flow, package the result).
- `DefaultRequestHandler` — the SDK's built-in router that receives the raw JSON-RPC request, extracts the message, and calls the executor's `execute()`.
- `InMemoryTaskStore` — tracks the lifecycle of each request/task in memory (a production system would use a persistent store so task history survives a server restart).

`A2AStarletteApplication(agent_card=AGENT_CARD, http_handler=request_handler)` combines the Agent Card (for the discovery `GET`) and the request handler (for the actual `POST`) into one Starlette web app, which `uvicorn.run(...)` serves as a real HTTP server. The response travels back wrapped as a `SendMessageResponse`, whose actual payload sits under `.root.result.parts[0].root.text` — a real structural detail discovered by inspecting the SDK's own `model_fields` rather than assuming a flatter shape, after hitting `'SendMessageResponse' object has no attribute 'result'` in testing.

### CrewAI concepts, as used on the Insurance side

- **Agent** — the "who": an AI worker with a `role`, `goal`, `backstory` (context shaping its behavior/tone), a list of `tools` it's allowed to call, and an `llm` (which model actually powers its reasoning — swappable independently of everything else, as proven when this project moved from Bedrock to the direct Anthropic API without touching any other logic).

**`Agent(...)` — what each real argument in `claims_agent.py` does, and why:**
- `role` — a short label describing the job; injected into the LLM's system prompt to shape how it "thinks of itself" when responding.
- `goal` — the agent's overall objective, also injected into its prompt — defines what success looks like for every task it's given.
- `backstory` — extra context/personality that further shapes judgment; here, explicitly stating "you never approve a claim without checking with the hospital first" nudges the LLM to always use the tool rather than guess.
- `tools` — a list of Python functions wrapped with `@tool(...)`; the LLM sees each tool's name and docstring and decides during reasoning whether/when to call it.
- `llm` — which model backs this agent's reasoning; a plain string like `"claude-sonnet-5"` resolves to the direct Anthropic API by default, while wrapping it in CrewAI's own `LLM(model=..., region_name=...)` object routes through AWS Bedrock instead — same `Agent`, swappable backend.
- `verbose` — controls how much CrewAI prints to the console (the `🤖 Agent Started` / `✅ Agent Final Answer` boxes).
- **Important:** creating this object defines the agent but runs nothing yet — it only does work once attached to a `Task` and executed inside `Crew.kickoff()`.

- **Task** — the "what": one specific job description, in plain English, handed to an agent for a single run — here, "verify this claim using the hospital tool," with the claim's actual details interpolated in.
- **Tool** — a plain Python function wrapped with `@tool("description")`, which turns it into something the agent's LLM can choose to call mid-reasoning. The function's docstring is what the LLM actually reads to decide *when* this tool is relevant — in this project, `verify_claim_with_hospital`'s docstring explicitly tells the LLM it returns decision/confidence/diagnosis/date fields.
- **Crew** — bundles agent(s) and task(s) together and is what actually runs them via `.kickoff()`.
- **Process** — `sequential` (used here) runs tasks one after another in order; `hierarchical` (not used, only relevant with multiple agents) would add a manager agent that delegates tasks to others.

**`crew.kickoff()` — what actually happens step by step when this one line runs:**
1. Takes the first (only) task and assigns it to `claims_agent`.
2. Sends the task's `description` text to the LLM as a prompt, along with the list of tools the agent is allowed to call.
3. The LLM reads the prompt, decides it needs to call `verify_claim_with_hospital` with the patient/injury/date values, and CrewAI actually executes that Python function on its behalf — this is the real A2A network call happening, triggered by the LLM's own decision, not hardcoded control flow.
4. The tool's return string is fed back to the LLM as an "observation."
5. The LLM writes a final natural-language answer summarizing the result — this becomes the task's output.
6. `.kickoff()` returns a `CrewOutput` object; `str(result)` gives the LLM's final written text — which, as the Step 8 status-logic bug above showed, is a *paraphrase*, not the tool's raw machine-readable output.
- **A subtlety learned by hitting a real bug:** an LLM agent's final "Final Answer" is its own paraphrase of whatever a tool returned — it is not the same string as the tool's actual return value. Anything downstream that needs to make a hard decision (like updating a database status) should read the tool's raw output directly, never the LLM's prose summary of it.

### LangGraph concepts, as used on the Hospital side

- **Why LangGraph here, not CrewAI:** the verification decision needs to be explainable and reproducible the exact same way every time the same input is given — a fixed, auditable sequence of steps, not an LLM improvising a different reasoning path each run. LangGraph is built for exactly this: a graph of plain Python functions with no LLM call inside the decision logic itself.
- **`StateGraph`** — defines the graph: a set of named nodes and fixed edges between them.
- **State (`ClaimState`, a `TypedDict`)** — one shared dictionary-like object that flows through every node; each node reads some fields and writes others into it.
- **Nodes** — plain functions (`search_node`, `diagnosis_check_node`, `date_check_node`, `confidence_node`) that each do one focused piece of work and return the (possibly updated) state.
- **Edges** — `graph.add_edge("search", "check_diagnosis")` etc. — define the fixed order nodes run in; `graph.set_entry_point(...)` defines where a run starts, `END` marks where it stops.
- **`graph.compile()`** — turns the node/edge definitions into a runnable object (`verification_app`); **`.invoke({...})`** actually runs one claim through the full sequence and returns the final state.
- **No LLM inside this graph at all** — every decision (`diagnosis_match`, `date_match`, final `confidence`/`decision`) is plain Python arithmetic and comparisons against fixed thresholds. The only place any model is involved is earlier, converting text into embeddings for the semantic search step — the actual match/no-match/needs-review judgment itself is deterministic.
