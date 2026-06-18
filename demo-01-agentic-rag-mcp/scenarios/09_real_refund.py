"""Scenario 9: Real refund via the Razorpay payments lab.

Requires a running payments lab (localhost:3000) with a completed checkout.
The human provides a Razorpay order ID that has reached PAID status.

This scenario documents the async confirmation gap: issuing a refund
returns immediately with initiation status, but the order transitions
to REFUNDED only when the refund.processed webhook arrives.

Before running:
  1. Start the payments lab: cd razorpay-payments-lab && npm start
  2. Complete a checkout at http://localhost:3000
  3. Copy the Razorpay order ID (e.g. order_xxx)
  4. Run: python scenarios/09_real_refund.py order_xxx
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import log_header, log_text, run_scenario


async def _wait_for_webhook(msg_index: int):
    if msg_index == 0:
        log_text("system", "Waiting 10 second for webhook delivery…")
        await asyncio.sleep(10)


def main():
    if len(sys.argv) < 2:
        print(
            "Before running: complete a checkout at localhost:3000, "
            "get the order ID from the lab, pass it as argument:\n\n"
            "  python scenarios/09_real_refund.py order_xxx\n"
        )
        sys.exit(1)

    order_id = sys.argv[1]

    os.environ["USE_RAZORPAY_LAB"] = "true"

    asyncio.run(
        run_scenario(
            title="9 · Real refund (async confirmation gap)",
            user_messages=[
                f"Issue a full refund for order {order_id}",
                "What is the current status of that refund?",
            ],
            between_messages=_wait_for_webhook,
        )
    )

    print()
    log_header("Observation")
    print(
        "  Note: Razorpay refund confirmation arrives asynchronously via webhook.\n"
        "  This response reflects initiation only, not confirmation.\n"
        "  Compare the order status above — if still PAID, the refund.processed\n"
        "  webhook has not yet arrived. If REFUNDED, it has."
    )


if __name__ == "__main__":
    main()
