"""Scenario 5: Tool execution failure.

Three sub-cases exercising different guard rules:
  1. lookup_order for a non-existent order (ORD-999)
  2. issue_refund where amount ($500) exceeds the order total ($30)
  3. issue_refund on an already-refunded order (ORD-002 / REF-001)

Observe: does the host surface each error cleanly, and does the model
respond sensibly without retrying the same call?
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import run_scenario

if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="5 · Tool execution failure",
            user_messages=[
                "Look up order ORD-999",
                "Issue a refund of $500 for order ORD-005",
                "Issue a full refund for order ORD-002",
            ],
        )
    )
