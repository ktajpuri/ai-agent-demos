"""Scenario 7: Multi-step chain.

A single request that requires three steps:
  1. Retrieve the refund policy (search_policy)
  2. Check the order's current state (lookup_order)
  3. Conditionally issue the refund (issue_refund)

Observe: does the model complete all three steps, loop unnecessarily,
or short-circuit by skipping the policy check?
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import run_scenario

if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="7 · Multi-step chain",
            user_messages=[
                (
                    "Check if order ORD-001 is eligible for a full refund "
                    "under our refund policy, and process it if it is"
                ),
            ],
        )
    )
