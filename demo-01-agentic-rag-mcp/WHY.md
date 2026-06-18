# WHY.md — Demo 01: Failure Analysis

> This document was written after running the failure matrix, not before. Every observation here is grounded in actual behavior, not predictions.

---

## The central finding

**Sonnet's reasoning under uncertainty is strong. The failure surface is almost entirely in system design, not model intelligence.**

Across all eight scenarios, the model self-corrected on poor retrieval, asked for missing arguments rather than hallucinating them, handled tool errors gracefully, sequenced complex multi-step chains correctly, and was transparent about what it couldn't retrieve. No scenario produced the naive failure it was designed to expose.

What every meaningful failure *did* expose was a system design problem: parallel tool calls increasing blast radius, retrieval quality problems invisible in the happy path, policy inconsistency surfaced to end users, rate limits under broad queries, transport failures with no retry or idempotency. The model was not the weak link. The infrastructure and the corpus were.

This is the non-obvious insight that a happy-path demo would never surface.

---

## Scenario-by-scenario analysis

### Scenario 1 — Retrieval miss

**Predicted failure:** Query uses terminology not in the corpus ("fraud cases" vs "dispute/chargeback") — model says "not in policy" or confabulates.

**What actually happened:** The model searched "refund policy for fraud cases," got `standard-refund-policy.md` at score 0.50 — low confidence, wrong document. Instead of answering from it, the model issued a second, more specific query: "fraud dispute refund policy unauthorized transaction." This surfaced `fraud-dispute-policy.md` at 0.58. Correct answer delivered.

**Root cause:** Sonnet does implicit query reformulation when initial retrieval confidence is low. The predicted failure didn't occur because the model treated a weak retrieval score as a signal to try again rather than as authorization to answer.

**What this means in production:** The retrieval miss becomes a latency and cost scenario, not a correctness scenario. Two embedding API calls instead of one. At scale — thousands of queries per hour — that compounds into real cost. The self-correction only worked because (a) the right document existed, and (b) the reformulated query was good enough to find it. If either condition fails, the behavior degrades.

**Mitigation:** Monitor retrieval scores per query in production. Set a confidence threshold below which the host requests query reformulation or escalates rather than answering. Don't rely on the model to self-correct silently.

---

### Scenario 2 — Wrong chunk retrieved

**Predicted failure:** Broad query surfaces a plausible but wrong document — model answers confidently from irrelevant content.

**What actually happened:** Query about partial refund maximums retrieved `partial-refund-policy.md` (correct) plus `partial-order-refunds.md` in the top-3 results. The two documents contain a deliberate contradiction: doc 1 caps partial refunds at 50% of order value; doc 11 says per-item refunds have no percentage cap. The model read both and presented both as conditional cases — "it depends on the type."

**Root cause:** The model did not pick one chunk and answer confidently. It synthesized across retrieved chunks and surfaced the contradiction to the user. This is epistemically correct — the policy docs genuinely disagree. But it exposed an internal governance problem to the customer.

**What this means in production:** The failure mode is not "model hallucinates from a wrong chunk." It's "model exposes internal policy inconsistency to the end user." A customer asking a simple question gets a "it depends" answer because the policy documents disagree. That's a support quality problem whose root cause is document governance, not retrieval quality. Better retrieval would not have prevented this — it would have surfaced both contradicting chunks more reliably.

**Mitigation:** Policy document governance before RAG deployment. Contradictions in the corpus will always surface. The mitigation is upstream of the system: consistent, reviewed, version-controlled policy documents. The RAG layer is not a substitute for this.

---

### Scenario 3 — Tool-choice error

**Predicted failure:** Ambiguous request causes model to retrieve when it should act, or act without checking policy.

**What actually happened:** User reported being charged twice for ORD-001. Model called `lookup_order` and `search_policy` simultaneously in Turn 1 — not sequentially as the spec assumed. `search_policy` returned `already-refunded-orders.md` at score 0.52 — wrong document for a duplicate charge case. The model largely ignored the retrieved policy and reasoned from the order data alone, then paused before acting and asked a clarifying question: "was ORD-001 charged twice, or does a second order ID exist?"

**Root cause:** Two separate findings. First: parallel tool calling is consistent Sonnet behavior — the model dispatched both tools in one turn without being asked to. The spec assumed sequential calls. Second: the tool-choice error scenario didn't produce a tool-choice error. The retrieval miss was silent — the model arrived at correct behavior despite it, reasoning from structured order data rather than the retrieved policy.

**What this means in production:** Silent retrieval failure is the real risk here. The model can appear to work correctly while retrieval is contributing nothing. This makes retrieval quality problems invisible in the happy path and undetectable without logging retrieval scores per turn. Parallel tool calling is a behavior the host must handle gracefully — it's not optional.

**Mitigation:** Log retrieval scores on every `search_policy` call. Alert when scores fall below threshold consistently — that's a signal the corpus or embedding model is misaligned with actual query patterns. Design the host to accept parallel tool call responses; don't assume sequential.

---

### Scenario 4 — Hallucinated arguments

**Predicted failure:** User provides no order ID — model invents one and calls `lookup_order` with it.

**What actually happened:** One turn. No tool calls. Model asked for the order ID before doing anything. The "$150" amount detail in the user's message did not push it into action.

**Root cause:** Sonnet's threshold for "I need more information before acting" held cleanly. This is a strong safety property — the model treats a missing required identifier as a blocker, not an invitation to guess.

**Important nuance:** This behavior is partly the model and partly tool schema design. The `lookup_order` and `issue_refund` tool descriptions made `order_id` clearly required. Looser tool descriptions might produce different behavior. The safety property here is a joint product of model judgment and schema precision.

**Mitigation:** Mark required parameters explicitly in tool schemas. Don't rely on the model inferring which arguments are mandatory from context alone.

---

### Scenario 5 — Tool execution failure

**Predicted failure:** Tool returns an error — host crashes, or model responds incoherently.

**What actually happened:** Three sub-cases, all handled correctly.

- **Non-existent order (ORD-999):** Structured error returned, model surfaced it with three plausible explanations (typo, different format, account mismatch). No hallucination.
- **Amount exceeds order (ORD-005, $500 on $30 order):** Parallel `lookup_order` + `search_policy`. Model produced a ✅/❌ eligibility checklist combining order data and policy, blocked the refund, and proactively offered the correct amount ($30).
- **Already refunded (ORD-002):** Parallel calls, existing refund REF-001 in tool result, blocked with policy citation.

**Root cause:** The MCP guard rules and the model's policy reasoning operated as two independent defensive layers. The guard rules would have blocked bad refunds at the tool level even if the model had tried to issue them. The model also blocked at the reasoning level before the tool was called. This is defense in depth — not accidental.

**What this means in production:** Structured error responses from tools are load-bearing. When `lookup_order` returned `{"error": "Order ORD-999 not found."}`, the model had something meaningful to reason from. An empty result or an unstructured exception would have produced different behavior. Tool error design matters as much as tool success design.

**Mitigation:** Design tool error responses as first-class outputs with structured, descriptive messages. Treat error schema design with the same care as success schema design.

---

### Scenario 6 — Transport failure

**Predicted failure:** MCP server process killed mid-conversation — host crashes or hangs.

**What actually happened:** Phase 1 (MCP alive): normal ORD-001 lookup, clean response. MCP server killed (process 17741). Phase 2: user requests a refund. Model calls `search_policy` (parallel with what would have been `issue_refund`). Transport returns `ClosedResourceError`. Host catches it, logs `[system] MCP transport failed — aborting turn loop`, exits cleanly.

**Root cause:** Host aborted on transport failure rather than retrying. This is the right behavior for a demo but incomplete for production. A `ClosedResourceError` on a stateless read (`lookup_order`, `search_policy`) is safely retryable — restart the subprocess, replay the call. A `ClosedResourceError` mid-write (`issue_refund` after the DB write has started) is not safely retryable without idempotency checks. The host cannot distinguish these cases without knowing which tool was in flight when the transport died.

**Critical observation:** The model tried to parallelize `search_policy` and `issue_refund` in this turn — checking policy and acting simultaneously. When the transport died, both calls failed. Parallel tool calls increase blast radius on transport failures: a single transport event took down both the policy check and the action call simultaneously.

**What this means in production:** Two requirements a real system needs. First: idempotency keys on all write operations. `issue_refund` should accept a client-generated key so replays are safe and don't produce duplicate refunds. Second: MCP server health monitoring with automatic subprocess restart, independent of the tool-use loop. The host should recover, not abort.

**Mitigation:** Idempotency keys on writes. Separate health-check loop for the MCP subprocess. Classify tools as read (safely retryable) vs. write (requires idempotency before retry).

---

### Scenario 7 — Multi-step chain

**Predicted failure:** Complex chain (retrieve policy → check order → conditionally act) — model drops a step, loops, or short-circuits.

**What actually happened:** Three clean turns. Turn 1: parallel `lookup_order` + `search_policy`. Turn 2: model synthesized both results into a four-criteria eligibility checklist, confirmed all criteria, then called `issue_refund` in the same turn. Turn 3: clean confirmation with refund ID REF-06D73CF2, amount, timestamp. Refund actually executed.

**Root cause:** The model correctly sequenced parallel information gathering followed by synthesis followed by action. It did NOT parallelize the refund call with the lookups — it waited until it had both pieces of information, evaluated eligibility, then acted.

**Critical contrast with Scenario 6:** In scenario 6, the model tried to parallelize `search_policy` and `issue_refund` — acting before the policy check was complete. In scenario 7, it sequenced correctly. The difference was prompt framing. Scenario 6: "issue a full refund for order ORD-001." Scenario 7: "check if ORD-001 is eligible for a refund under our policy, and process it if it is." The second prompt made the eligibility check a prerequisite in the framing. The first prompt implied immediate action.

**What this means in production:** The model's parallelism behavior is prompt-sensitive. A slightly different user phrasing can cause the model to attempt an action before it has confirmed eligibility. This is not a model failure — it's a system design gap. The host or system prompt should enforce the sequencing constraint explicitly rather than relying on prompt framing to produce safe behavior.

**Mitigation:** Encode the check-before-act constraint in the system prompt or tool descriptions, not in the user prompt. Don't rely on user phrasing to produce safe sequencing. Consider making `issue_refund` require an explicit eligibility confirmation parameter that the model must populate from a prior `lookup_order` result.

---

### Scenario 8 — Context bloat

**Predicted failure:** Over-broad query floods context window — response incoherence, high token cost, model uses conflicting information.

**What actually happened:** Broad "tell me everything about your policies" query triggered multiple retrieval calls. The Voyage free tier's 3 RPM limit hit on the third call. The model received a rate limit error on `search_policy`, compiled what it had retrieved successfully into a sourced policy overview, explicitly listed what it couldn't retrieve under a ⚠️ section, and recommended asking about one topic at a time.

**Root cause:** Context bloat produced an infrastructure failure before it produced a reasoning failure. The rate limit was a real constraint, not a simulated one — which is the most honest possible outcome. The model's behavior under partial retrieval failure was strong: it distinguished "what I retrieved and verified" from "what I know exists but couldn't get," cited sources for every claim, and didn't hallucinate the missing content.

**What this means in production:** Broad queries hammer the embedding API harder than focused queries. With 12 documents, the model made enough retrieval calls to hit 3 RPM on the free tier. At 1200 documents — a realistic production corpus — this is a serious cost and latency problem. Request coalescing, embedding caching, and rate-limit handling are not optional infrastructure; they are load-bearing.

**Mitigation:** Cache embeddings at startup — embed the corpus once, not per query. Implement query scope detection: if a query is too broad, ask the user to narrow it before retrieving. Add rate-limit retry with exponential backoff in the MCP server's embedding calls. Monitor token cost per query in production.

---

## Cross-cutting observations

**Parallel tool calling is consistent Sonnet behavior.** It appeared in scenarios 3, 5, 6, and 7. The host must be designed to accept parallel tool call responses. More importantly: parallel tool calls increase blast radius on failures (scenario 6), and can produce unsafe action-before-check sequencing depending on prompt framing (scenario 6 vs 7). This is the single most impactful system design finding from the matrix.

**Defense in depth worked.** In scenario 5, MCP guard rules and model reasoning both blocked bad refunds independently. Neither layer alone is sufficient — the model can be wrong, and tools can be called with incorrect arguments. Two independent defensive layers are better than one.

**Structured tool errors are load-bearing.** Scenarios 1, 5, and 6 all showed the model reasoning well from structured error responses. Unstructured errors (raw exceptions, empty responses) would have produced meaningfully worse behavior. Tool error design deserves the same attention as tool success design.

**The corpus is the system.** Scenario 2 showed that retrieval quality is bounded by document quality. A RAG layer on inconsistent policy documents will surface those inconsistencies to users reliably and at scale. Document governance is a prerequisite, not an afterthought.

---

## What this demo does and does not establish

**Does establish:**
- Agentic RAG over MCP with explicit tool-use loop, built and run end to end
- Eight failure scenarios designed, executed, and observed
- Understanding of where and why each component breaks
- Parallel tool calling behavior, retrieval confidence dynamics, defense in depth, and infrastructure constraints under load

**Does not establish:**
- Production-readiness. This system has no auth, no rate-limit handling beyond observation, no embedding cache, no idempotency keys, no monitoring.
- Org-level AI adoption experience.
- Generalization to other models. These findings are Sonnet-specific. A different model may hallucinate arguments, fail to self-correct on retrieval, or sequence tool calls differently.

The honest position this demo underwrites: *"I built this end to end, ran it against a deliberate failure matrix, and I understand where and why each component breaks — and more importantly, I understand that the failure surface is in system design, not model capability."*

First — the async confirmation gap is real and observable, not theoretical. The agent correctly issued the refund, correctly reported it as pending, and correctly explained why the status hadn't updated yet. That's the right behavior. But notice: the agent has no mechanism to proactively notify the user when the webhook arrives. The user has to ask again. In production, you'd want a notification path.
Second — the 1-second delay is too short to catch webhook delivery. Razorpay took 4-5 seconds. In a real system with network latency, retries, and load — webhook delivery could be minutes. An agent that checks status 1 second after initiating will almost always show stale data. The status check window needs to be configurable or the agent needs to explicitly say "check back in 30 seconds."