CREATE TABLE IF NOT EXISTS orders (
    order_id    TEXT PRIMARY KEY,
    amount      REAL NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED', 'FAILED')),
    customer_id TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id   TEXT PRIMARY KEY,
    order_id    TEXT NOT NULL REFERENCES orders(order_id),
    amount      REAL NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
