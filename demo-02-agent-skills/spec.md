# Demo 02 — Agent Skills as Encoded Procedure

> **Prerequisite:** This demo is only meaningful in contrast to Demo 01. Complete demo 01 first — including the failure matrix and WHY.md — before building this one.

---

## What this is

A focused demo that isolates one question: **what does a Skill do that an MCP tool or a system prompt doesn't — and where does encoded procedure fail?**

In Demo 01, the model decides how to handle a refund request using tool results and its own judgment. In this demo, the same task is handled two ways side by side:

- **Mode A (baseline):** Model has the MCP tools from Demo 01. No procedural guidance beyond the tool descriptions. It improvises from tool outputs.
- **Mode B (Skill):** Model has the same tools *and* a Skill that encodes the refund-adjudication procedure explicitly — the steps, the conditions, the edge cases — as structured instructions the model can load and follow.

The interesting part is not which mode "wins." It's where they diverge, why they diverge, and what each failure tells you about the mechanism.

---

## What a Skill is

A Skill is a structured, reusable block of procedural knowledge given to the model. In the Claude/MCP ecosystem, a Skill is typically a folder containing:

- A `SKILL.md` — instructions describing a procedure the model should follow when the Skill is active
- Optional supporting files (schemas, examples, reference data)

The model loads the Skill when it determines the Skill is relevant to the current task (or when the host explicitly activates it). The key distinction from a system prompt: a Skill is modular and composable — it can be loaded selectively, combined with other Skills, and versioned independently of the host configuration.

**The distinction from an MCP tool:** An MCP tool is a *capability* — something the model can invoke to get data or trigger an effect. A Skill is *procedure* — instructions about how the model should reason and act, independent of any specific tool call. A Skill can govern *how* and *when* the model uses its tools.

---

## Use case

The same payments support domain from Demo 01. The Skill encodes the refund adjudication procedure:

```
To process a refund request:
1. Verify the order exists and retrieve its current status
2. Check whether a refund has already been issued for this order
3. Look up the applicable refund policy for this order type and age
4. If the order is within the refund window and no prior refund exists:
   - Confirm the refund amount does not exceed the order amount
   - Issue the refund
   - Confirm the outcome to the user
5. If outside the refund window:
   - Retrieve the escalation policy
   - Inform the user of the limitation and the escalation path
6. If a refund already exists:
   - Do not issue a second refund
   - Inform the user and provide the existing refund reference
```

The procedure has enough conditional branches and edge cases that the difference between "model improvising" and "model following procedure" is observable and testable.

---

## Architecture

```
User (CLI prompt)
       │
       ▼
Python Host
(Anthropic API — tool-use loop, same as Demo 01)
       │
       ├── Mode A: tools only (no Skill)
       │
       └── Mode B: tools + Skill loaded into context
               │
               ▼
         SKILL.md (refund adjudication procedure)
               +
         MCP Server (same as Demo 01)
           ├── search_policy
           ├── lookup_order
           └── issue_refund
```

The host can run in either mode from the CLI. Same prompt, same tools, same model — only the presence of the Skill changes. This isolation is deliberate: it's what makes the comparison clean.

---

## Failure matrix

Demo 01's failure matrix was about retrieval and tool-use mechanics. This demo's failure matrix is about procedural adherence and the limits of Skill-encoded guidance.

| # | Scenario | Setup | What we observe |
|---|----------|-------|-----------------|
| 1 | **Skill doesn't trigger** | Request is phrased in a way the model doesn't recognize as a refund-adjudication task | Model skips the Skill and improvises — does it reach the right answer anyway, or does it skip a required step? |
| 2 | **Over-rigid adherence** | Request has an edge case the Skill procedure doesn't cover (e.g. partial refund on a subscription order) | Does the model follow the procedure to a wrong conclusion, or does it reason outside the procedure sensibly? |
| 3 | **Procedure-tool conflict** | Tool result contradicts a Skill assumption (e.g. Skill says "check refund window first" but `lookup_order` returns a status that makes that irrelevant) | Does the model reconcile, freeze, or default to the procedure blindly? |
| 4 | **Step skipping** | Procedure has 6 steps; request seems to make steps 2–3 obviously unnecessary | Does the model skip steps it deems redundant, and does skipping cause a downstream error? |
| 5 | **Mode A vs Mode B, same failure** | Run a scenario that failed in Demo 01 (e.g. hallucinated arguments) in both modes | Does the Skill mitigate the failure, make it worse, or have no effect? |
| 6 | **Mode A vs Mode B, different outcome** | Multi-step chain (retrieve → check → act) run in both modes | Does the Skill produce a more reliable chain, and at what cost (more tokens, more turns, more rigidity)? |
| 7 | **Procedure contradiction** | Two steps in the Skill give guidance that conflicts in a specific edge case | Which instruction does the model follow, and why? |
| 8 | **Skill loaded unnecessarily** | Simple lookup request (no refund) — Skill is active but shouldn't govern this request | Does the model apply the procedure where it doesn't apply, producing over-engineered responses? |

---

## What this demo does not do

- Does not re-implement the RAG or MCP infrastructure from scratch — it imports from Demo 01.
- Does not benchmark Skills against fine-tuning, agent frameworks, or other approaches — out of scope.
- Does not claim Skills are better or worse than system prompts in general — the question is narrower: what's the observable difference in this specific task, with this specific procedure.
- Does not produce a production-ready Skill. The Skill written here is a learning artifact.

---

## Done → stop condition

The demo is complete when:

1. Both Mode A and Mode B are runnable from the CLI with the same test prompts
2. All eight failure scenarios are observable and documented
3. `WHY.md` answers the central question for each scenario: *did the Skill help, hurt, or make no difference — and why?*
4. A short concluding section in `WHY.md` answers the meta-question: *when would you reach for a Skill vs. a better tool description vs. a system prompt?*

At that point: stop.

---

## Stack

Same as Demo 01, with one addition:

| Component | Choice | Reason |
|-----------|--------|--------|
| Skill format | Markdown (`SKILL.md`) | Matches the Claude/MCP Skill convention |
| Everything else | Same as Demo 01 | No new infrastructure; the Skill is the variable |

---

## The central question this demo answers

After running both demos, you should be able to answer this with specificity:

> *Given a multi-step task with conditional branches and edge cases — when does the model need an encoded procedural Skill, when is a well-described tool enough, and when does a Skill make things worse?*

That's the question. The failure matrix is designed to surface evidence for the answer, not to confirm a predetermined conclusion.
