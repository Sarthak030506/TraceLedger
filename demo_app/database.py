"""SQLite storage layer for the Demo Expense App.

All amounts are stored as integers representing paise (minor units).
Floating-point numbers are strictly forbidden.
"""
from datetime import datetime, timezone
import os
import sqlite3
import uuid
from typing import Any

from .auditor import assert_no_floats

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id TEXT PRIMARY KEY,
    user TEXT NOT NULL,
    category TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_DB_PATH = "data/demo_expenses.db"
DEFAULT_BUDGET_PAISE = 5000000  # ₹50,000 in paise


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection and ensure the database directory and tables exist."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize SQLite schema and default settings."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'monthly_budget_minor'").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('monthly_budget_minor', ?)",
                (str(DEFAULT_BUDGET_PAISE),),
            )
            conn.commit()
    finally:
        conn.close()


def add_expense(
    user: str,
    category: str,
    amount_minor: int,
    description: str,
    db_path: str = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Add a new expense. amount_minor must be an integer."""
    assert_no_floats(amount_minor, "amount_minor")
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ValueError("amount_minor must be an integer (in paise)")
    if amount_minor <= 0:
        raise ValueError("amount_minor must be positive")

    expense_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO expenses (id, user, category, amount_minor, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (expense_id, user, category, amount_minor, description, now_utc),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": expense_id,
        "user": user,
        "category": category,
        "amount_minor": amount_minor,
        "description": description,
        "created_at": now_utc,
    }


def get_expenses(user: str | None = None, db_path: str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Retrieve all expenses, optionally filtered by user, ordered newest first."""
    conn = get_connection(db_path)
    try:
        if user:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE user = ? ORDER BY created_at DESC", (user,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM expenses ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_expense_by_id(expense_id: str, db_path: str = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Retrieve an expense by its ID."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_expense_amount(
    expense_id: str,
    new_amount_minor: int,
    db_path: str = DEFAULT_DB_PATH,
) -> tuple[dict[str, Any] | None, int | None]:
    """Update the amount of an existing expense.

    Returns (updated_record, old_amount_minor) or (None, None) if not found.
    """
    assert_no_floats(new_amount_minor, "new_amount_minor")
    if not isinstance(new_amount_minor, int) or isinstance(new_amount_minor, bool):
        raise ValueError("new_amount_minor must be an integer (in paise)")
    if new_amount_minor <= 0:
        raise ValueError("new_amount_minor must be positive")

    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if not row:
            return None, None
        old_amount_minor = row["amount_minor"]

        conn.execute(
            "UPDATE expenses SET amount_minor = ? WHERE id = ?",
            (new_amount_minor, expense_id),
        )
        conn.commit()

        updated_row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return dict(updated_row), old_amount_minor
    finally:
        conn.close()


def delete_expense(expense_id: str, db_path: str = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Delete an expense by ID. Returns the deleted record or None if not found."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if not row:
            return None
        deleted_record = dict(row)
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        return deleted_record
    finally:
        conn.close()


def get_budget(db_path: str = DEFAULT_DB_PATH) -> int:
    """Get the current monthly budget in paise."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'monthly_budget_minor'").fetchone()
        return int(row["value"]) if row else DEFAULT_BUDGET_PAISE
    finally:
        conn.close()


def set_budget(new_budget_minor: int, db_path: str = DEFAULT_DB_PATH) -> tuple[int, int]:
    """Set the monthly budget in paise. Returns (new_budget, old_budget)."""
    assert_no_floats(new_budget_minor, "new_budget_minor")
    if not isinstance(new_budget_minor, int) or isinstance(new_budget_minor, bool):
        raise ValueError("new_budget_minor must be an integer (in paise)")
    if new_budget_minor < 0:
        raise ValueError("budget cannot be negative")

    conn = get_connection(db_path)
    try:
        old_budget = get_budget(db_path)
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('monthly_budget_minor', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(new_budget_minor),),
        )
        conn.commit()
        return new_budget_minor, old_budget
    finally:
        conn.close()
