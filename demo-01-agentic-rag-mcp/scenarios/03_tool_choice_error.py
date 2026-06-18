"""Scenario 3: Tool-choice error.

The request is ambiguous: a duplicate charge could be a billing dispute
(policy lookup) or a straightforward refund (direct action).  The model
must decide whether to retrieve policy first or jump straight to
issuing a refund — and either choice can be wrong.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import run_scenario

if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="3 · Tool-choice error",
            user_messages=[
                "I was charged twice for order ORD-001 and I want my money back",
            ],
        )
    )
