"""MCP server for the payments support assistant demo.

Exposes three tools over stdio transport:
  - search_policy: semantic search over the policy corpus
  - lookup_order:  read order + refund state from SQLite
  - issue_refund:  write a refund row, guarded by business rules
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from rag import search as rag_search

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "db", "payments.db")
REFUND_WINDOW_DAYS = 30

# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("payments-support")


@mcp.tool(
    name="search_policy",
    description=(
        "Semantic search over internal policy documents. "
        "Returns the top matching policy excerpts for a natural-language query. "
        "Use this to find refund rules, escalation procedures, dispute handling, "
        "and other operational policies before taking action."
    ),
)
def search_policy(query: str) -> list[dict]:
    """Search policy documents by semantic similarity.

    Args:
        query: Natural-language question or topic to search for.
    """
    results = rag_search(query)
    if not results:
        return [{"error": "No policy documents found. The corpus may not be loaded."}]
    return results


@mcp.tool(
    name="lookup_order",
    description=(
        "Look up an order by its ID. Returns the order details (amount, status, "
        "customer, created date) and any existing refunds against that order."
    ),
)
def lookup_order(order_id: str) -> dict:
    """Retrieve order and refund state from the database.

    Args:
        order_id: The order identifier (e.g. 'ORD-001').
    """
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": f"Order {order_id} not found."}

        order = dict(row)
        refunds = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM refunds WHERE order_id = ?", (order_id,)
            ).fetchall()
        ]
        order["refunds"] = refunds
        return order
    finally:
        conn.close()


@mcp.tool(
    name="issue_refund",
    description=(
        "Issue a refund for an order. Enforces business rules: the order must exist, "
        "must be in a refundable status, must be within the refund window, must not "
        "already have a refund, and the refund amount must not exceed the order amount."
    ),
)
def issue_refund(order_id: str, amount: float) -> dict:
    """Issue a refund against an order, subject to guard rules.

    Args:
        order_id: The order identifier to refund.
        amount: The refund amount (must be > 0 and <= order amount).
    """
    conn = _get_db()
    try:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": f"Order {order_id} not found."}

        order = dict(row)

        # Guard 1: status must allow refunds
        if order["status"] not in ("COMPLETED", "CANCELLED"):
            return {
                "error": f"Order {order_id} is in {order['status']} status and is not eligible for a refund."
            }

        # Guard 2: refund window
        created = datetime.fromisoformat(order["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created).days
        if age_days > REFUND_WINDOW_DAYS:
            return {
                "error": (
                    f"Order {order_id} was placed {age_days} days ago, "
                    f"outside the {REFUND_WINDOW_DAYS}-day refund window."
                )
            }

        # Guard 3: no existing refund
        existing = conn.execute(
            "SELECT refund_id, amount FROM refunds WHERE order_id = ?", (order_id,)
        ).fetchone()
        if existing:
            return {
                "error": (
                    f"Order {order_id} already has a refund "
                    f"(ref: {existing['refund_id']}, amount: {existing['amount']}). "
                    f"No second refund allowed."
                )
            }

        # Guard 4: amount validation
        if amount <= 0:
            return {"error": "Refund amount must be greater than zero."}
        if amount > order["amount"]:
            return {
                "error": (
                    f"Refund amount {amount} exceeds order amount {order['amount']}. "
                    f"Refunds cannot exceed the original order amount."
                )
            }

        # All guards passed — issue the refund
        refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO refunds (refund_id, order_id, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (refund_id, order_id, amount, "COMPLETED", now),
        )
        conn.commit()

        return {
            "success": True,
            "refund_id": refund_id,
            "order_id": order_id,
            "amount": amount,
            "status": "COMPLETED",
            "created_at": now,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
