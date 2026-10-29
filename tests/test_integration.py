"""Integration tests across Sidecar, Integrity, Backend, and Blockchain modules."""
import json
import pytest

from sidecar.collector import ingest_many, sample_events
from sidecar.storage import RecordStore
from integrity.merkle import build_merkle_tree
from integrity.verifier import verify_batch


def test_sidecar_ingest_and_hash_records():
    """Ingest sample events into an in-memory store and verify hash records and integrity."""
    store = RecordStore(":memory:")
    result = ingest_many(sample_events(), store)
    assert len(result["stored"]) == 5
    assert result["rejected"] == []

    hash_records = store.get_hash_records()
    assert len(hash_records) == 5

    # Assert 5 items in sequence order with 64-char lowercase hex hashes
    for idx, rec in enumerate(hash_records, start=1):
        assert rec["sequence_number"] == idx
        h = rec["record_hash"]
        assert isinstance(h, str)
        assert len(h) == 64
        assert h == h.lower()
        assert not h.startswith("0x")
        assert all(c in "0123456789abcdef" for c in h)

    # Assert no mismatches between canonical JSON and stored hashes
    assert store.recompute_mismatches() == []
    store.close()


def test_merkle_verification_and_tamper_detection():
    """Merkle tree construction, batch verification, and tamper detection."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)

    # 1. Retrieve hashes for leaves
    hash_records = store.get_hash_records()
    record_hashes = [r["record_hash"] for r in hash_records]
    assert len(record_hashes) == 5

    # 2. Build Merkle tree
    tree = build_merkle_tree(record_hashes)
    expected_root = tree["merkle_root"]
    assert len(expected_root) == 64

    # 3. Batch verification succeeds on unaltered records
    full_records = store.get_records()
    verification = verify_batch(full_records, expected_root)
    assert verification["verified"] is True
    assert verification["computed_root"] == expected_root
    assert verification["errors"] == []

    # 4. Tamper with one stored record
    store.conn.execute(
        "UPDATE records SET details_json = ? WHERE sequence_number = 1",
        (json.dumps({"tampered": True}),)
    )
    tampered_records = store.get_records()
    tampered_res = verify_batch(tampered_records, expected_root)
    assert tampered_res["verified"] is False
    assert len(tampered_res["errors"]) > 0

    store.close()
