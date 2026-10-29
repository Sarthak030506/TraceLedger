"""Off-chain storage in SQLite. Raw records never leave this database.

Sequence numbers are assigned inside a single write transaction so they are
consecutive (1, 2, 3, ...) with no gaps or duplicates.
"""
import json
import sqlite3

from .hasher import canonical_json, hash_canonical, hash_record
from .models import ValidationError, build_record

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    sequence_number INTEGER PRIMARY KEY,
    event_id        TEXT NOT NULL UNIQUE,
    timestamp       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    source          TEXT NOT NULL,
    details_json    TEXT NOT NULL,
    canonical_json  TEXT NOT NULL,
    record_hash     TEXT NOT NULL
);
"""


class DuplicateEventError(ValidationError):
    """event_id already stored."""


class RecordStore:
    def __init__(self, path: str = "traceledger_records.db"):
        self.conn = sqlite3.connect(path, isolation_level=None)  # manual transactions
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)

    def close(self):
        self.conn.close()

    def append(self, clean_event: dict) -> dict:
        """Assign the next sequence number, hash, and store a sanitized event.

        Returns the hash record: event_id, sequence_number, timestamp,
        event_type, record_hash.
        """
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT COALESCE(MAX(sequence_number), 0) FROM records").fetchone()
            record = build_record(clean_event, row[0] + 1)
            canon = canonical_json(record)
            rhash = hash_record(record)
            self.conn.execute(
                "INSERT INTO records VALUES (?,?,?,?,?,?,?,?)",
                (record["sequence_number"], record["event_id"], record["timestamp"],
                 record["event_type"], record["source"],
                 json.dumps(record["details"], sort_keys=True), canon, rhash),
            )
            self.conn.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            self.conn.execute("ROLLBACK")
            raise DuplicateEventError(f"duplicate event_id: {clean_event['event_id']}") from exc
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        return self._to_hash_record(record, rhash)

    @staticmethod
    def _to_hash_record(record: dict, rhash: str) -> dict:
        return {
            "event_id": record["event_id"],
            "sequence_number": record["sequence_number"],
            "timestamp": record["timestamp"],
            "event_type": record["event_type"],
            "record_hash": rhash,
        }

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]

    def get_records(self, start: int = 1, end: int | None = None) -> list[dict]:
        """Full stored records (with details), ordered by sequence number."""
        end = end if end is not None else 2**62
        rows = self.conn.execute(
            "SELECT * FROM records WHERE sequence_number BETWEEN ? AND ? ORDER BY sequence_number",
            (start, end),
        ).fetchall()
        return [
            {
                "event_id": r["event_id"], "sequence_number": r["sequence_number"],
                "timestamp": r["timestamp"], "event_type": r["event_type"],
                "source": r["source"], "details": json.loads(r["details_json"]),
            }
            for r in rows
        ]

    def get_hash_records(self, start: int = 1, end: int | None = None) -> list[dict]:
        """The interface output for Person 2, ordered by sequence number."""
        end = end if end is not None else 2**62
        rows = self.conn.execute(
            "SELECT event_id, sequence_number, timestamp, event_type, record_hash "
            "FROM records WHERE sequence_number BETWEEN ? AND ? ORDER BY sequence_number",
            (start, end),
        ).fetchall()
        return [dict(r) for r in rows]

    def recompute_mismatches(self) -> list[int]:
        """Sequence numbers whose stored canonical text no longer matches its
        stored hash. (Basic local check; full batch verification is Person 2's job.)"""
        bad = []
        for r in self.conn.execute("SELECT sequence_number, canonical_json, record_hash FROM records"):
            if hash_canonical(r["canonical_json"]) != r["record_hash"]:
                bad.append(r["sequence_number"])
        return bad
