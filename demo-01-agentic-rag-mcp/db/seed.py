"""Seed the payments demo database with test data for the failure matrix."""

import sqlite3
import os
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "payments.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    now = datetime.now(timezone.utc)

    # --- Orders ---

    # 1. Normal completed order — within 30-day window, no refund issued.
    #    Straightforward happy-path refund candidate.
    cur.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        ("ORD-001", 150.00, "COMPLETED", "CUST-100", (now - timedelta(days=5)).isoformat()),
    )

    # 2. Already-refunded order — a completed order that already has a refund.
    #    Tests the "no second refund" guard.
    cur.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        ("ORD-002", 200.00, "COMPLETED", "CUST-101", (now - timedelta(days=10)).isoformat()),
    )

    # 3. Order in PROCESSING status — not eligible for refund per policy doc 9.
    cur.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        ("ORD-003", 75.00, "PROCESSING", "CUST-102", (now - timedelta(days=2)).isoformat()),
    )

    # 4. Expired refund window — completed order placed 45 days ago (outside 30-day window).
    cur.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        ("ORD-004", 320.00, "COMPLETED", "CUST-103", (now - timedelta(days=45)).isoformat()),
    )

    # 5. Small order — used to test "refund exceeds order amount" guard.
    #    Order is $30; a refund request for more than $30 should be rejected.
    cur.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        ("ORD-005", 30.00, "COMPLETED", "CUST-104", (now - timedelta(days=3)).isoformat()),
    )

    # --- Refunds ---

    # Existing refund against ORD-002 (the already-refunded order).
    cur.execute(
        "INSERT INTO refunds VALUES (?, ?, ?, ?, ?)",
        ("REF-001", "ORD-002", 200.00, "COMPLETED", (now - timedelta(days=8)).isoformat()),
    )

    conn.commit()
    conn.close()
    print(f"Database seeded at {DB_PATH}")


if __name__ == "__main__":
    seed()
