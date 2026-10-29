"""Database setup and connection management for TraceLedger backend."""
import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id INTEGER PRIMARY KEY,
    merkle_root TEXT NOT NULL,
    previous_root TEXT NOT NULL,
    first_sequence INTEGER NOT NULL,
    last_sequence INTEGER NOT NULL,
    record_count INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    signature TEXT,
    transaction_hash TEXT,
    block_number INTEGER,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TEXT NOT NULL,
    record_hashes_json TEXT
);

CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    verified INTEGER NOT NULL,
    expected_root TEXT NOT NULL,
    computed_root TEXT NOT NULL,
    errors_json TEXT,
    verified_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES batches(batch_id)
);
"""


def get_db_path(explicit_path: str | None = None) -> str:
    """Return explicit path or read from BACKEND_DB_PATH environment variable."""
    if os.environ.get("VERCEL"):
        return explicit_path or os.environ.get("BACKEND_DB_PATH", "/tmp/backend.db")
    return explicit_path or os.environ.get("BACKEND_DB_PATH", "data/backend.db")


def init_db(db_path: str | None = None) -> None:
    """Initialize SQLite tables for backend metadata storage."""
    target_path = get_db_path(db_path)
    if target_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    conn = sqlite3.connect(target_path)
    try:
        conn.executescript(SCHEMA_SQL)
        # Add column to existing DBs that pre-date this schema version
        try:
            conn.execute("ALTER TABLE batches ADD COLUMN record_hashes_json TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
    finally:
        conn.close()


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Create a new SQLite connection with Row factory enabled."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn
