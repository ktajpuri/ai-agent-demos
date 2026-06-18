# Demo 01 — Agentic RAG over MCP with Tool Calling

## What this is

A minimal demo that wires three real patterns from modern AI engineering into one working system:

- **MCP (Model Context Protocol)** — a standard, open protocol for exposing tools and resources to an AI agent. The model doesn't call functions directly; it speaks MCP, and the server on the other end decides how to fulfill the request.
- **RAG (Retrieval-Augmented Generation)** — the model retrieves from a document corpus at runtime, grounding its responses in policy rather than relying on parametric memory (what the model "remembers" from training).
- **Tool Calling** — the model decides at runtime which tool to invoke, in what order, and with what arguments. Retrieval is one of those tools — not a fixed preprocessing step.

These three compose into a pattern called **agentic RAG**: the model retrieves *when it judges it should*, not as a mandatory step before every response. That distinction is load-bearing — it's where most of the interesting failure modes live, because the model's judgment about *when to retrieve* is itself a thing that can be wrong.

---

## Use case

A support operations assistant for a payments company. Given a natural-language request, the model can:

- Search policy documents to answer questions about refund windows, partial refunds, fraud escalation, and similar topics
- Look up the current state of an order
- Issue a refund, subject to business rules

This domain was chosen deliberately. It reuses the payments mental model and SQLite schema from a prior [Razorpay integration lab](https://github.com/kamlesh/razorpay-payments-lab) — so the learning budget here stays on the new surface (MCP + retrieval), not on rebuilding domain logic from scratch. The scenario also has a natural tension that makes tool-choice interesting: some requests require retrieval only, some require action only, and some require the model to retrieve policy *before* deciding whether to act.

---

## Architecture

```
User (CLI prompt)
       │
       ▼
Python Host
(Anthropic API — explicit tool-use loop)
       │
       │  stdio
       ▼
MCP Server (Python)
  ├── search_policy ──► embedding search → in-memory vector store → policy corpus
  ├── lookup_order  ──► SQLite read (orders table)
  └── issue_refund  ──► SQLite write (refunds table, with guard rules)
```

The host runs the tool-use loop **explicitly** — not through an agent framework. The model returns a tool call, the host routes it to the MCP server over stdio, the result comes back, the host feeds it into the next model turn. This is intentional: a framework would abstract away exactly the loop we're here to understand.

---

## Components

### MCP Server
- Three tools: `search_policy`, `lookup_order`, `issue_refund`
- **stdio transport** — no HTTP server, no port management. Simplest MCP transport; the host spawns the server as a subprocess and communicates over stdin/stdout.
- Written in Python using the MCP Python SDK

**Why MCP instead of plain function calling?**
You could expose the same three functions directly via the Anthropic tool-use API without any MCP. The reason to use MCP here is that it's the direction the industry is standardizing on: tools exposed over MCP can be consumed by any MCP-compatible host or agent framework, not just this one script. Understanding the protocol — what it adds, where it adds friction — is part of what this demo is for.

### RAG Layer
- ~12 hand-written policy documents covering: refund windows, partial refund rules, already-refunded orders, fraud escalation, dispute handling, expired windows
- **In-memory vector store** (cosine similarity over numpy arrays) — at this corpus size, a dedicated vector DB (Pinecone, Weaviate, etc.) adds infrastructure complexity without adding learning. The retrieval mechanics are identical; the scale is not.
- **Real embeddings** — using a real embedding API (OpenAI `text-embedding-3-small` or equivalent). Fake/random embeddings would make retrieval meaningless and eliminate the failure scenarios we're here to study.

### Python Host
- Thin: calls Anthropic API, parses `tool_use` blocks, routes to MCP server, feeds `tool_result` blocks back into the next turn
- No agent framework — the loop is written explicitly so every turn is visible and attributable
- Logs each turn to stdout: model response, tool calls made, tool results received

### SQLite
- `orders` table: `order_id`, `amount`, `status`, `customer_id`, `created_at`
- `refunds` table: `refund_id`, `order_id`, `amount`, `status`, `created_at`
- Seeded with test data that covers the failure scenarios below (missing orders, already-refunded orders, orders with amounts at boundary conditions)

---

## Failure matrix

This is the centerpiece of the demo. The happy path is not interesting. These eight scenarios are.

| # | Scenario | Setup | What we observe |
|---|----------|-------|-----------------|
| 1 | **Retrieval miss** | Query uses terminology not in the corpus (e.g. "chargeback" when docs say "dispute") | Does the model say "I couldn't find a policy on this" or does it confabulate an answer from training data? |
| 2 | **Wrong chunk retrieved** | Query is broad enough to surface a plausible but wrong document (e.g. "refund" returns the fraud policy) | Does the model confidently answer from the irrelevant chunk, or does it signal uncertainty? |
| 3 | **Tool-choice error** | Request is ambiguous — could be answered by policy lookup or by direct action | Does the model retrieve when it should act, or act without checking policy first? |
| 4 | **Hallucinated arguments** | User asks to refund an order but doesn't provide an order ID | Does the model ask for the ID, or does it fabricate one and call `lookup_order` with it? |
| 5 | **Tool execution failure** | `lookup_order` for a non-existent ID; `issue_refund` for an amount exceeding the order; `issue_refund` on an already-refunded order | Does the host surface the error to the model cleanly, and does the model respond sensibly? |
| 6 | **Transport failure** | MCP server process is killed mid-conversation | Does the host crash, hang, or degrade gracefully with a meaningful error? |
| 7 | **Multi-step chain** | Request requires: retrieve policy → check order status → conditionally issue refund | Does the model complete the chain, loop unnecessarily, or short-circuit a step? |
| 8 | **Context bloat** | Query is intentionally over-broad, retrieving maximum chunks | Effect on response coherence, latency, and token cost — and whether the model notices it has conflicting information |

Each scenario is documented in `WHY.md` after the build: root cause, what the failure tells us about the component, and what a production system would do differently.

---

## What this demo does not do

- **No UI.** CLI only. The interaction surface is not the point.
- **No production hardening.** No auth, no rate limiting, no retry logic beyond the basics, no monitoring.
- **No real vector DB.** In-memory is sufficient at this scale; adding a DB would be incidental complexity.
- **No fine-tuning.** Out-of-scope for this learning objective.
- **No claim of org-level AI adoption.** This is a learning artifact. The honest position it underwrites: *"I built this end to end, ran it against a deliberate failure matrix, and I understand where and why each component breaks."*

---

## Done → stop condition

The demo is complete when:

1. All eight failure scenarios can be triggered from the CLI and produce observable, repeatable behavior
2. `WHY.md` is written — root cause and mitigation documented for each scenario
3. The host, MCP server, and SQLite seed script are clean enough that someone else could clone the repo and run them

At that point: stop. Do not add a UI. Do not add a fourth tool. Do not add a vector DB "to see what changes." The learning objective is met.

---

## Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.11+ | MCP SDK, Anthropic SDK, numpy — all native |
| LLM API | Anthropic (claude-sonnet-4-6) | Tool-use loop is explicit and well-documented |
| MCP transport | stdio | Simplest; no HTTP server complexity |
| MCP SDK | `mcp` (Python) | Official SDK — version pinned at build time |
| Vector store | numpy (in-memory cosine) | Right-sized for 12 documents |
| Embeddings | OpenAI `text-embedding-3-small` | Small, cheap, real |
| Database | SQLite (stdlib) | No infrastructure; same schema as Razorpay lab |

---

## Relationship to Demo 02

Demo 01 establishes the baseline: MCP tools and retrieval doing the work. Demo 02 asks what changes when the model is also given an explicit *procedural Skill* — and whether that changes the failure modes. The contrast between them is the point. Do not build demo 02 before this one is done and stopped.
