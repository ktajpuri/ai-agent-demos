"""Scenario 2: Wrong chunk retrieved.

Two policy documents cover partial refunds with contradictory rules:
  - partial-refund-policy.md says capped at 50 % of order value
  - partial-order-refunds.md says there is NO percentage cap

A query about the partial-refund cap is broad enough that the retriever
may surface the wrong document (or both), and the model may confidently
answer from whichever chunk it sees first.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import run_scenario

if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="2 · Wrong chunk retrieved",
            user_messages=[
                "What is the maximum percentage I can get back as a partial refund?",
            ],
        )
    )
