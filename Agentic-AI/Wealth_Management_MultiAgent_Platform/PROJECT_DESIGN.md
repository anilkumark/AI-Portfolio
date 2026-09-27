# Wealth Management Multi-Agent Platform
### Full production design — combining both source projects into one system

**Project location:** developed locally here (`Wealth_Management_MultiAgent_Platform/`, alongside `Customer_Refund_MultiAgents/`), to be pushed to its own location in the GitHub portfolio repo — `AI-Portfolio/Agentic-AI/Wealth_Management_MultiAgent_Platform/` — later, the same pattern used for the refund project.

This file exists so the design survives independently of any one conversation — readable by any future session (or any other engineer) opening this folder cold.

---

## 1. Problem statement

Two source projects, same underlying gap: advisors and clients have no single place to ask a plain-English question and get a trustworthy answer.

- **"Financial Reporting Agent"** covers the *data + retrieval* half — Fabric-based structured data, text-to-SQL, RAG over policy/market documents, reporting.
- **"Wealth Management Chatbot"** covers the *analysis + reasoning* half — a conversational agent with specialized tools (stock position analysis, risk calculation & mitigation) and memory.

Combined, these aren't two products — they're one advisor assistant. Building them separately duplicates the ingestion pipeline, the chatbot interface, and the memory layer for no reason. Combined, and hardened to real production standards, this becomes a genuine platform: reusable tools, governed data access, guarded outputs, and a compliance gate on anything that looks like advice.

---

## 2. The honest tension: "autonomous" vs. "compliance-gated" — resolved explicitly

The goal was for this to be autonomous where possible. It can't be uniformly autonomous — and pretending otherwise would be a real liability. The resolution:

- **Fact-only agents run fully autonomously** — no output they produce is advice, so there's nothing to gate. (Data Query, Insights, Stock Position Analysis reporting-only mode.)
- **Advice-generating agents are always gated** — Risk Calculation & Mitigation, by definition, proposes an action. It never reaches a client without human sign-off, no matter how confident the system is. This isn't a limitation of the platform — it's the platform correctly modeling where autonomy is appropriate and where it isn't.

Worth stating this distinction explicitly to a client — it's a sign of a well-designed system, not an unfinished one.

---

## 3. Full agent roster

| Agent | Job | Autonomous? |
|---|---|---|
| **Supervisor** | Routes requests, merges results, enforces the compliance gate | — (orchestrator) |
| **Data Query Agent** | Text-to-SQL against Fabric, real numbers only | Yes |
| **Insights Agent** | RAG over market commentary / risk disclosures via Azure AI Search | Yes |
| **Stock Position Analysis Agent** | Portfolio composition, concentration, sector exposure | Yes (factual analysis) |
| **Risk Calculation & Mitigation Agent** | Risk metrics (volatility, VaR) + mitigation proposals | **No — always compliance-gated** |
| **Reporting Agent** | Formats and delivers the final, approved answer | Gated by upstream approval |

---

## 4. Every requested concern, decided

**Azure deployment** — Azure Container Apps (API + UI), Microsoft Fabric (data), Azure AI Search (vectors), Azure Database for PostgreSQL (state), Azure Key Vault (secrets), Microsoft Entra ID (auth).

**LangGraph** — orchestration backbone: `langgraph-supervisor` for handoffs, `create_react_agent` per scoped specialist.

**LangSmith** — tracing (env-var only). **Added:** use LangSmith's **Prompt Hub** to version and A/B test prompts in production, instead of just files in git — this project has enough prompts (6 agents) and enough compliance sensitivity that prompt changes deserve their own review/rollback trail, not just a commit.

**Docker** — `Dockerfile` + `docker-compose.yml` locally, same images deployed to Container Apps.

**Guardrails — new layer, added.** Two directions:
- *Input guardrails:* prompt-injection detection, PII detection before anything reaches the LLM
- *Output guardrails:* block hallucinated-looking figures (cross-check numbers in the response actually appear in retrieved context or query results), enforce the "not financial advice" disclaimer on every AI-originated message, block disallowed language
- **Decision:** build this as our own lightweight module (regex + LLM-classifier hybrid — the same pattern already used for the compliance-gate trigger), not a third-party framework like Guardrails AI/NeMo. Keeps the logic ownable and consistent with the rest of the system, and avoids a heavy new dependency for something we can implement precisely for this domain.

**Governance — new layer, added.**
- *Data governance:* **Microsoft Purview**, integrated with Fabric natively — data lineage and classification on the structured data, not something to build ourselves.
- *AI governance:* the audit trail already covered by LangSmith + the approval table; prompt versioning via the LangSmith Prompt Hub (above); a cost/usage governance dashboard tracking token spend per agent, since multiple active LLM agents on `gpt-4o` can get expensive fast without visibility.

**API** — FastAPI.

**Graph (database)** — **not included in v1.** A graph database (e.g., Neo4j) would help with relationship-heavy queries ("which clients are overexposed to sectors correlated with fund X's decline"), but nothing in the current scope needs it yet. Noted as a future extension, not built now — adding it without a concrete use case is scope creep.

**MCP (Model Context Protocol) — added, and this is the real "platform" move.** Instead of each tool being a Python function wired directly into one agent, expose the Fabric query capability, the risk-calculation logic, and the stock-analysis logic as **MCP servers**. Agents connect to them as MCP clients. This is what actually makes it a *platform* rather than one app: the same risk-calculation server could be reused by a different internal tool, an analyst's Claude Desktop session, or a future client-facing product — without duplicating the logic.

**Memory — two distinct kinds, both included.**
- *Short-term (per-conversation):* the LangGraph Postgres checkpointer.
- *Long-term (cross-session, new):* a separate client-profile memory store recording preferences and history across sessions ("this client always asks about ESG exposure," "last quarter's risk tolerance conversation") — genuinely different from conversation state, and something neither source project had.

**Observability — two layers, both included.**
- **LangSmith** for AI-specific tracing.
- **Azure Application Insights**, added — infra-level monitoring LangSmith doesn't cover: API latency, error rates, container health, request throughput. A production platform needs both; LangSmith alone leaves you blind to "the API is slow" or "a container is crash-looping."

**Evaluation — three checks, one new.**
- RAGAS (Insights Agent).
- SQL-correctness eval (Data Query Agent).
- **New: risk-calculation correctness eval** — the Risk Agent does real math (volatility, VaR); this needs its own test suite comparing computed values against known-correct results, the same rigor as RAGAS but for arithmetic, not language.
- **New: guardrail effectiveness testing** — periodic adversarial/red-team-style prompts run against the system to confirm prompt-injection and PII guardrails actually catch what they're supposed to.

**Retrieval** — Azure AI Search.

**Validations** — Pydantic schemas at every API boundary, SQL validation before execution, **added:** business-rule validation on risk calculations (outputs bounded to sane ranges — a VaR calculation returning a nonsensical number should fail loudly, not reach a client).

**Exceptions** — a custom exception hierarchy (`core/exceptions.py`, same pattern as the refund project): `ClientNotFoundError`, `InvalidSQLError`, `RiskCalculationError`, `ComplianceGateError`, `GuardrailViolationError` — each mapped to a clean FastAPI error response, never a raw traceback.

**UI** — Streamlit. Genuinely production-capable for an internal advisor tool; a custom React frontend is a real option later if this becomes client-facing rather than advisor-facing, but it's a separate, bigger investment — not needed for v1.

**Schemas** — typed Pydantic models throughout.

**Prompts** — one file per agent, paired with the LangSmith Prompt Hub for versioning (see Governance above).

**Fine-tuning** — not needed for v1. RAG solves knowledge grounding better than fine-tuning (documents update instantly, a fine-tuned model's knowledge goes stale). SQL generation and risk math are handled by strong prompting + deterministic tools, not something fine-tuning improves. The one place it could help later: a small fine-tuned classifier for the guardrail/compliance-trigger check, once there's real production data on what should and shouldn't get flagged — a narrow, data-driven optimization for after launch, not a v1 requirement.

---

## 5. Folder structure

```
Wealth_Management_MultiAgent_Platform/
├── src/wealth_agent/
│   ├── core/            (config, logging, exceptions)
│   ├── schemas/          (typed request/response + domain models)
│   ├── prompts/           (one .md per agent)
│   ├── guardrails/         (input/output checks)
│   ├── governance/          (usage/cost tracking, Purview integration hooks)
│   ├── mcp_servers/          (Fabric query, risk calc, stock analysis as MCP servers)
│   ├── ingestion/              (Fabric/document pipeline)
│   ├── retrieval/                (Azure AI Search)
│   ├── agents/                    (6 scoped agents + supervisor)
│   ├── memory/                     (short-term checkpointer + long-term client-profile store)
│   ├── observability/               (LangSmith + Application Insights wiring)
│   ├── api/                          (FastAPI)
│   └── ui/                            (Streamlit)
├── evaluation/    (RAGAS, SQL-correctness, risk-correctness, guardrail red-team tests)
├── tests/
├── docker/
└── .github/workflows/
```

---

## 6. Architecture

```
Advisor / Client ──(Entra ID)──► Streamlit ──► FastAPI ──► Guardrails (input) ──► Supervisor
                                                                                        │
                    ┌───────────────┬───────────────┬───────────────┬────────────────┤
                    ▼               ▼               ▼               ▼                ▼
              Data Query      Insights (RAG)   Stock Position   Risk & Mitigation   Reporting
              Agent            Agent             Analysis Agent  Agent (GATED)       Agent
                    │               │               │               │                │
                    ▼               ▼               ▼               ▼                │
          Fabric Warehouse   Azure AI Search   (via MCP server)  (via MCP server)     │
          (via MCP server)                                            │              │
                                                                        ▼              │
                                                              Compliance Gate           │
                                                            (interrupt · Postgres ·      │
                                                             email approval)             │
                                                                        │                │
                                                                        └────────────────┘
                                                                                 │
                                                                                 ▼
                                                                  Guardrails (output) ──► Client
```

Everything traced (LangSmith + App Insights), everything evaluated on a schedule, everything governed (Purview + prompt hub + cost tracking), nothing advice-shaped reaching a client ungated.

---

## Status

Design phase complete. Next step: scaffold this folder structure (empty files first, same approach used for the refund project), then build incrementally, agent by agent, testing each piece before moving to the next.
