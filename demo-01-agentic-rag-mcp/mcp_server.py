"""MCP server for the payments support assistant demo.

Exposes three tools over stdio transport:
  - search_policy: semantic search over the policy corpus
  - lookup_order:  read order state from SQLite or the Razorpay payments lab
  - issue_refund:  issue a full refund via the Razorpay payments lab
"""

import os
import sqlite3

import httpx
from mcp.server.fastmcp import FastMCP

from rag import search as rag_search

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "db", "payments.db")
RAZORPAY_LAB_URL = os.environ.get("RAZORPAY_LAB_URL", "http://localhost:3000")
USE_RAZORPAY_LAB = os.environ.get("USE_RAZORPAY_LAB", "false").lower() == "true"

# ---------------------------------------------------------------------------
# SQLite helpers (used when USE_RAZORPAY_LAB is false)
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
        "created date) and any existing refunds against that order."
    ),
)
def lookup_order(order_id: str) -> dict:
    """Retrieve order and refund state.

    Args:
        order_id: The order identifier (e.g. 'ORD-001' or 'order_xxx').
    """
    if USE_RAZORPAY_LAB:
        resp = httpx.get(f"{RAZORPAY_LAB_URL}/orders/{order_id}")
        data = resp.json()
        if resp.status_code != 200:
            return {"error": data.get("error", resp.text)}
        return {
            "order_id": data["id"],
            "amount": data["amount"],
            "status": data["status"],
            "created_at": data["created_at"],
            "refunds": [],
        }

    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
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
        "Issue a full refund for an order. Partial amounts are not supported. "
        "The order must be in PAID status with an associated payment. "
        "Refund confirmation arrives asynchronously via webhook."
    ),
)
def issue_refund(order_id: str) -> dict:
    """Issue a full refund via the payments lab.

    Args:
        order_id: The Razorpay order identifier to refund.
    """
    resp = httpx.post(f"{RAZORPAY_LAB_URL}/refund/{order_id}")
    data = resp.json()
    if resp.status_code != 200:
        return {"error": data.get("error", resp.text)}
    return data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
