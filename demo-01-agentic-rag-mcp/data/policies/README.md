# Payments Support Policy Corpus

This directory contains the policy documents used as the RAG corpus for the payments support assistant demo. Each document is focused and self-contained (roughly 150–300 words) so it can be retrieved and reasoned over independently.

## Documents

1. **standard-refund-policy.md** — The 30-day standard refund window, eligibility criteria, process, and what the customer receives.
2. **partial-refund-policy.md** — When partial refunds apply, the 50%-of-order-value cap, calculation, and approval.
3. **already-refunded-orders.md** — Handling orders that already have a refund; no second refunds; provide the existing refund reference.
4. **expired-refund-window.md** — What happens after 30 days, limited exceptions, escalation, and customer communication.
5. **fraud-dispute-policy.md** — Unauthorized-charge handling as disputes and chargebacks; filing, timelines, and resolution.
6. **subscription-refund-policy.md** — The 7-day subscription refund window, pro-rata calculation, and cancellation vs. refund.
7. **escalation-paths.md** — When to escalate, who handles each tier, response times, and required information.
8. **refund-amount-limits.md** — Refunds never exceed the original amount; currency handling and multi-currency edge cases.
9. **order-status-definitions.md** — PENDING, PROCESSING, COMPLETED, CANCELLED, FAILED and refund eligibility per status.
10. **refund-processing-times.md** — How long each refund type takes, communicating timelines, and handling delays.
11. **partial-order-refunds.md** — Refunding individual items in a multi-item order, calculated per item with no percentage cap.
12. **failed-payment-refunds.md** — Edge case where a payment failed but an amount was held; release vs. refund and timelines.

## ⚠️ Deliberate Inconsistencies and Gaps

The following issues are **intentional**. They exist so the demo's failure matrix can exercise contradiction handling and retrieval-miss scenarios. **They are not mistakes — do not "fix" them.**

### 1. Contradiction: partial refund cap (doc 1/2 vs. doc 11)

- **partial-refund-policy.md** says partial refunds are **capped at 50% of order value**.
- **partial-order-refunds.md** says item refunds are **calculated per item with no percentage cap**.

These give slightly different guidance for overlapping "partial refund" situations. This contradiction tests whether the assistant detects and reconciles conflicting policies.

### 2. Contradiction: refund window (doc 1 vs. doc 6)

- **standard-refund-policy.md** states a **30-day** refund window.
- **subscription-refund-policy.md** states a **7-day** window for subscriptions and explicitly says it contradicts the 30-day standard.

This tests whether the assistant applies the correct, more-specific policy rather than the general one.

### 3. Terminology gap: fraud disputes (doc 5)

**fraud-dispute-policy.md** deliberately uses only **"dispute"** and **"chargeback"** and **never** the word **"refund."** A user asking to "refund a fraudulent charge" may fail to retrieve this document — this is the intended retrieval-miss scenario.

### 4. Status trap: PROCESSING (doc 9)

**order-status-definitions.md** defines a **PROCESSING** status and states such orders are **not eligible for a refund.** This is used in failure-scenario testing where an order in PROCESSING should block a refund the assistant might otherwise approve.
