"""Scenario 1: Retrieval miss.

The fraud-dispute-policy.md never uses the word "refund" — only "dispute"
and "chargeback".  Querying for "refund policy for fraud" may fail to
retrieve it, and the model may confabulate an answer from training data
instead of admitting the corpus has no match.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import run_scenario

if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="1 · Retrieval miss",
            user_messages=[
                "What is your refund policy for fraud cases?",
            ],
        )
    )
