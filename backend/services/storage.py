"""Storage service for persisting batch commitments and verification results in SQLite."""
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from ..database import get_connection


def save_batch(batch_data: dict[str, Any], db_path: str | None = None) -> dict[str, Any]:
    """Insert a new batch commitment record into SQLite."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ts = batch_data.get("timestamp")
    if ts is None:
        ts = int(datetime.now(timezone.utc).timestamp())

    # Serialize optional record_hashes list for storage
    record_hashes = batch_data.get("record_hashes")
    record_hashes_json = json.dumps(record_hashes) if record_hashes is not None else None

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO batches (
                batch_id, merkle_root, previous_root, first_sequence,
                last_sequence, record_count, timestamp, signature,
                transaction_hash, block_number, status, created_at,
                record_hashes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_data["batch_id"],
                batch_data["merkle_root"].lower(),
                batch_data.get("previous_root", "0" * 64).lower(),
                batch_data["first_sequence"],
                batch_data["last_sequence"],
                batch_data["record_count"],
                ts,
                batch_data.get("signature"),
                batch_data.get("transaction_hash"),
                batch_data.get("block_number"),
                batch_data.get("status", "confirmed"),
                now_utc,
                record_hashes_json,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_data["batch_id"],)).fetchone()
        return dict(row)
    finally:
        conn.close()


def get_batch(batch_id: int, db_path: str | None = None) -> dict[str, Any] | None:
    """Retrieve a single batch by ID."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_batches(
    limit: int = 50,
    offset: int = 0,
    db_path: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """List batches ordered by batch_id descending, along with total count."""
    conn = get_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY batch_id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows], total
    finally:
        conn.close()


def get_latest_batch(db_path: str | None = None) -> dict[str, Any] | None:
    """Retrieve the most recent batch committed."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM batches ORDER BY batch_id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def log_verification(
    batch_id: int,
    verified: bool,
    expected_root: str,
    computed_root: str,
    errors: list[str],
    db_path: str | None = None,
) -> None:
    """Log an audit verification attempt."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO verification_logs (
                batch_id, verified, expected_root, computed_root, errors_json, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                1 if verified else 0,
                expected_root,
                computed_root,
                json.dumps(errors),
                now_utc,
            ),
        )
        conn.commit()
    finally:
        conn.close()
