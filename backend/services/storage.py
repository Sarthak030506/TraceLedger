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


class DatabaseAheadOfChain(Exception):
    """The local database holds batches the configured contract does not have."""

    def __init__(self, db_latest: int, chain_latest: int):
        super().__init__(
            f"Local database is at batch #{db_latest} but the configured contract is at "
            f"#{chain_latest}. The database belongs to a different contract; "
            f"point BACKEND_DB_PATH at a fresh file or restore the matching contract."
        )
        self.db_latest = db_latest
        self.chain_latest = chain_latest


def sync_from_chain(service: Any, db_path: str | None = None) -> int:
    """Import batches that exist on-chain but not in the local database.

    The contract is the source of truth for the batch chain. A wiped or ephemeral
    database (e.g. a free-tier host restart) must not make us try to re-submit
    batch #1 to a contract that is already at #N. Imported rows have no leaf hashes (not
    stored on-chain); the transaction hash is recovered from the event log when possible.

    Returns the number of batches imported. No-op in simulated mode (the database
    is the only record there). Raises AnchorError if the chain cannot be read and
    DatabaseAheadOfChain if the database contains batches the contract lacks.
    """
    if service.mode not in ("live", "read_only"):
        return 0

    chain_latest = service.latest_onchain_batch_id()
    db_latest_row = get_latest_batch(db_path)
    db_latest = db_latest_row["batch_id"] if db_latest_row else 0
    if db_latest > chain_latest:
        raise DatabaseAheadOfChain(db_latest, chain_latest)

    imported = 0
    for batch_id in range(1, chain_latest + 1):
        if get_batch(batch_id, db_path):
            continue
        onchain = service.get_onchain_batch(batch_id)
        if onchain is None:
            break
        save_batch(
            {
                "batch_id": onchain["batch_id"],
                "merkle_root": onchain["merkle_root"],
                "previous_root": onchain["previous_root"],
                "first_sequence": onchain["first_sequence"],
                "last_sequence": onchain["last_sequence"],
                "record_count": onchain["record_count"],
                "timestamp": onchain["timestamp"],
                "signature": onchain.get("signature") or None,
                "transaction_hash": service.get_onchain_tx_hash(batch_id, onchain.get("block_number")),
                "block_number": onchain.get("block_number"),
                "status": "confirmed",
            },
            db_path,
        )
        imported += 1
    return imported


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
