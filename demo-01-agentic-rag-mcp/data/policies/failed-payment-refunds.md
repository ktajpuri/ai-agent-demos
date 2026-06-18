# Failed-Payment Refunds

This policy covers the edge case where a payment attempt **failed** but an amount was nonetheless **authorized or held** on the customer's account. This is different from a standard refund because no successful charge was ever captured.

## Why This Is Different

In a standard refund, money was successfully captured and we return it. In a failed-payment case, the charge did not complete — but the customer's bank may have placed a temporary authorization hold that reserves the funds without transferring them to us. Because we never received the funds, we cannot "refund" them in the usual sense; the hold must instead be released or allowed to expire.

## The Process

1. Confirm the payment status is FAILED (see order status definitions).
2. Determine whether an authorization hold exists on the customer's account.
3. If a hold exists, request its release through the payment processor rather than issuing a refund.
4. If the processor confirms no funds were captured, no refund transaction is created — document that the charge failed and the hold will release.
5. If, exceptionally, funds were actually captured despite the failure, handle that captured amount under the standard refund policy.

## Timeline Differences

Authorization holds are released by the customer's bank, not by us. Release timelines are typically faster than a posted refund but are entirely controlled by the bank — commonly a few business days, sometimes up to a week or more depending on the issuer.

## What to Tell the Customer

Explain that the charge did not go through, that any amount they see is a temporary hold rather than a completed payment, and that the hold will be released by their bank. Provide a reference for the failed transaction. Do not promise a refund for funds that were never captured.
