# Refund Amount Limits

This policy sets the hard limits on refund amounts and explains how currency is handled.

## Core Limit: Never Exceed the Original Amount

A refund — whether full, partial, combined, or pro-rata — may **never exceed the original amount the customer paid for the order**. The sum of all refunds issued against a single order must remain at or below the original captured amount. This rule overrides any other calculation. If a calculation produces a figure higher than the original amount, cap it at the original amount.

## Currency Handling

Refunds are issued in the **same currency** as the original charge. Agents must not convert a refund into a different currency or issue it to a payment method in a different currency than the original.

## Multi-Currency Edge Cases

Exchange-rate movement between the charge date and the refund date can cause the customer's bank to credit a slightly different amount in their local currency, even though we refund the exact original transaction-currency amount. Handle these cases as follows:

- Always refund the exact original amount in the original transaction currency.
- Do not add or subtract to compensate for exchange-rate differences; we control the transaction-currency amount, not the customer's bank conversion.
- If a customer was charged in one currency but their account now operates in another, escalate to the specialist team rather than attempting a manual conversion.

Any rounding must round down to ensure the refund never exceeds the original amount. Document the original currency and amount on every refund record.
