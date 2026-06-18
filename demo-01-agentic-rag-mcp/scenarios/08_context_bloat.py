"""Scenario 8: Context bloat.

An intentionally over-broad query that forces the retriever to return
chunks covering different (and contradictory) policies.  The corpus
contains deliberate conflicts:
  - 30-day vs. 7-day refund windows
  - 50 % partial-refund cap vs. no cap

Observe: effect on coherence, latency, and whether the model notices
the contradictions in the retrieved material.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import run_scenario

if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="8 · Context bloat",
            user_messages=[
                (
                    "Explain all of your policies about refunds, returns, "
                    "cancellations, disputes, chargebacks, and escalation "
                    "procedures in complete detail"
                ),
            ],
        )
    )
