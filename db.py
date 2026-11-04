"""SQLite helpers for paper-trading-portfolio."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "portfolio.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'crypto')),
                quantity REAL NOT NULL CHECK (quantity > 0),
                cost_basis REAL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol);
            """
        )


def list_holdings() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM holdings ORDER BY asset_type, symbol"
        ).fetchall()
    return [dict(r) for r in rows]


def add_holding(
    symbol: str,
    asset_type: str,
    quantity: float,
    cost_basis: float | None = None,
    notes: str = "",
) -> dict:
    symbol = symbol.strip().upper()
    asset_type = asset_type.strip().lower()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO holdings (symbol, asset_type, quantity, cost_basis, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (symbol, asset_type, quantity, cost_basis, notes.strip()),
        )
        holding_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM holdings WHERE id = ?", (holding_id,)
        ).fetchone()
    return dict(row)


def delete_holding(holding_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
        return cur.rowcount > 0


def get_holding(holding_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM holdings WHERE id = ?", (holding_id,)
        ).fetchone()
    return dict(row) if row else None
