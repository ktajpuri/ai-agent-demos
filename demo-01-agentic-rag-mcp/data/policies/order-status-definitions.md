# Order Status Definitions

This document defines each order status and states whether an order in that status is eligible for a refund. Always check an order's status before processing a refund.

## PENDING

The order has been created but payment has not yet been captured. Because no money has been captured, there is nothing to refund. **Not eligible for a refund** — if the customer no longer wants the order, cancel it instead.

## PROCESSING

The order's payment has been captured and the order is being prepared or actively worked on. Orders in **PROCESSING** status are **not eligible for a refund**. The order must first move out of PROCESSING (to COMPLETED or CANCELLED) before any refund can be considered. If a customer requests a refund while the order is PROCESSING, explain that the order must finish processing first, and follow up once its status changes.

## COMPLETED

The order's payment was captured and the order was fulfilled. **Eligible for a refund** under the standard refund policy, subject to the 30-day window and other eligibility rules.

## CANCELLED

The order was cancelled before fulfillment. If payment was captured before cancellation, the captured amount is **eligible for a refund**. If no payment was captured, there is nothing to refund.

## FAILED

The payment attempt failed. Normally there is nothing to refund. However, if an amount was authorized or held despite the failure, this is handled as an edge case under the failed-payment refunds policy rather than a standard refund.

## Summary

| Status | Refund Eligible |
| --- | --- |
| PENDING | No |
| PROCESSING | No |
| COMPLETED | Yes |
| CANCELLED | Yes, if payment captured |
| FAILED | Only via failed-payment edge case |
