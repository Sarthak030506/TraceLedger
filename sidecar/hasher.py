"""Canonical serialization and SHA-256 record hashing.

CANONICAL FORM (documented contract, do not change without telling everyone):
  * JSON object with keys: event_id, sequence_number, timestamp, event_type,
    source, details   (record_hash is NOT part of the hashed data)
  * keys sorted alphabetically at every nesting level
  * separators (",", ":") -> no spaces
  * UTF-8, ensure_ascii=False
  * NaN/Infinity rejected
  * hash = SHA-256(canonical_json.encode("utf-8")), lowercase hex, 64 chars,
    NO "0x" prefix
"""
import hashlib
import json

from .models import RECORD_FIELDS


def canonical_json(record: dict) -> str:
    data = {k: record[k] for k in RECORD_FIELDS}
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def hash_record(record: dict) -> str:
    return hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


def hash_canonical(canonical: str) -> str:
    """Hash an already-canonical string (used to re-verify stored records)."""
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
