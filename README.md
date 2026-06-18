# AI Agent Demos

Two focused, deliberately scoped demos exploring real patterns in modern AI engineering — built as learning artifacts, not production systems.

Each demo is structured around a **failure matrix**: a set of scenarios designed to expose where and why each component breaks. The failure matrix is the point, not the happy path.

---

## Why this exists

Most AI coding tutorials show you what works. These demos are built to show what breaks, and why — because understanding failure modes is the difference between knowing how to use a tool and knowing how to build with it responsibly.

The two demos are sequenced intentionally. Build and understand demo 1 before demo 2. The second is only meaningful in contrast to the first.

---

## Demo 01 — Agentic RAG over MCP with Tool Calling

**The question:** When you give a model retrieval *and* actions, how does it decide which to use — and where does that decision go wrong?

Three real patterns compose into one architecture:
- **MCP** (Model Context Protocol) — standard protocol for exposing tools to an agent
- **RAG** — retrieval over a policy corpus so the model grounds responses in documents, not parametric memory
- **Tool Calling** — the model decides at runtime whether to retrieve, act, or chain both

→ [Read the full spec](./demo-01-agentic-rag-mcp/spec.md)

---

## Demo 02 — Agent Skills as Encoded Procedure

**The question:** What does a Skill do that an MCP tool or a system prompt doesn't — and where does encoded procedure fail?

A focused comparison: the same refund-adjudication task, done two ways — model improvising from raw tool output, versus model following a Skill that encodes the procedure explicitly. The interesting part is where they diverge.

→ [Read the full spec](./demo-02-agent-skills/spec.md)

---

## Repo structure

```
ai-agent-demos/
├── README.md                        ← you are here
├── demo-01-agentic-rag-mcp/
│   ├── spec.md                      ← architecture, failure matrix, done→stop condition
│   ├── WHY.md                       ← failure analysis and mitigations (written post-build)
│   └── ...                          ← code (added during build)
└── demo-02-agent-skills/
    ├── spec.md
    ├── WHY.md
    └── ...
```

---

## What these demos are not

Neither demo claims production-readiness, org-level AI adoption experience, or framework-level design. They are honest learning artifacts: the kind of thing you build when you want to understand how something actually works, not just that it works.

The honest position they underwrite: *"I've built these patterns end to end, run them against deliberate failure scenarios, and I understand where and why each component breaks."*
