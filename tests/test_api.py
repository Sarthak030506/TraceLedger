"""Unit tests for FastAPI backend endpoints (Person 3)."""
import copy
import hashlib
import os
import pytest
from fastapi.testclient import TestClient

from backend.database import init_db
from backend.main import app
from integrity.merkle import build_merkle_tree
from sidecar.collector import ingest_many, sample_events
from sidecar.storage import RecordStore


@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path, monkeypatch):
    """Ensure each test runs with an isolated temporary SQLite database."""
    test_db = str(tmp_path / "test_backend.db")
    monkeypatch.setenv("BACKEND_DB_PATH", test_db)
    init_db(test_db)
    return test_db


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    """Health check returns status ok and metrics."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "blockchain_connected" in data
    assert data["latest_batch_id"] == 0
    assert data["total_batches"] == 0


def test_submit_batch_lifecycle(client):
    """Submit genesis batch and subsequent chained batch."""
    root1 = "a" * 64
    batch1_payload = {
        "batch_id": 1,
        "merkle_root": root1,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 5,
        "record_count": 5,
        "timestamp": 1729000000,
        "signature": "c" * 128,
    }

    resp1 = client.post("/api/batches", json=batch1_payload)
    assert resp1.status_code == 201
    b1 = resp1.json()
    assert b1["batch_id"] == 1
    assert b1["merkle_root"] == root1
    # No blockchain configured in tests: the anchor must be labelled as simulated
    assert b1["status"] == "simulated"
    assert b1["transaction_hash"].startswith("0x")

    # Submit second chained batch
    root2 = "b" * 64
    batch2_payload = {
        "batch_id": 2,
        "merkle_root": root2,
        "previous_root": root1,
        "first_sequence": 6,
        "last_sequence": 10,
        "record_count": 5,
        "timestamp": 1729000100,
    }
    resp2 = client.post("/api/batches", json=batch2_payload)
    assert resp2.status_code == 201
    b2 = resp2.json()
    assert b2["batch_id"] == 2
    assert b2["previous_root"] == root1

    # Verify listing
    list_resp = client.get("/api/batches")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 2
    assert len(list_data["batches"]) == 2

    # Get single batch
    single_resp = client.get("/api/batches/1")
    assert single_resp.status_code == 200
    assert single_resp.json()["batch_id"] == 1


def test_submit_batch_validation_errors(client):
    """Enforces monotonic batch IDs and sequence count integrity."""
    # 1. Skipped batchId (cannot start at 2)
    resp = client.post("/api/batches", json={
        "batch_id": 2,
        "merkle_root": "a" * 64,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 5,
        "record_count": 5,
    })
    assert resp.status_code == 400
    assert "non-monotonic" in resp.json()["detail"].lower()

    # 2. Inconsistent count vs sequence numbers
    resp = client.post("/api/batches", json={
        "batch_id": 1,
        "merkle_root": "a" * 64,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 5,
        "record_count": 10,  # Expected 5
    })
    assert resp.status_code == 422  # Pydantic validation error


def test_submit_batch_broken_chain_error(client):
    """Rejects batch if previous_root does not match the preceding batch root."""
    root1 = "a" * 64
    client.post("/api/batches", json={
        "batch_id": 1,
        "merkle_root": root1,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 5,
        "record_count": 5,
    })

    # Batch 2 with wrong previous_root
    resp = client.post("/api/batches", json={
        "batch_id": 2,
        "merkle_root": "b" * 64,
        "previous_root": "9" * 64,  # Incorrect
        "first_sequence": 6,
        "last_sequence": 10,
        "record_count": 5,
    })
    assert resp.status_code == 400
    assert "broken batch chain" in resp.json()["detail"].lower()


def test_batch_verification_endpoint(client):
    """End-to-end verification via backend API with unaltered and tampered records."""
    store = RecordStore(":memory:")
    ingest_many(sample_events(), store)
    full_records = store.get_records()
    hashes = [r["record_hash"] for r in store.get_hash_records()]
    tree = build_merkle_tree(hashes)
    root = tree["merkle_root"]

    # Commit batch
    client.post("/api/batches", json={
        "batch_id": 1,
        "merkle_root": root,
        "previous_root": "0" * 64,
        "first_sequence": 1,
        "last_sequence": 5,
        "record_count": 5,
    })

    # Verify unaltered records
    verify_resp = client.post("/api/batches/1/verify", json={"records": full_records})
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["verified"] is True
    assert verify_data["expected_root"] == root
    assert verify_data["computed_root"] == root
    assert verify_data["errors"] == []

    # Verify tampered records
    tampered_records = copy.deepcopy(full_records)
    tampered_records[0]["details"]["tampered"] = True

    tampered_resp = client.post("/api/batches/1/verify", json={"records": tampered_records})
    assert tampered_resp.status_code == 200
    tampered_data = tampered_resp.json()
    assert tampered_data["verified"] is False
    assert len(tampered_data["errors"]) > 0


def test_batch_not_found(client):
    """Returns 404 when querying or verifying a non-existent batch."""
    assert client.get("/api/batches/999").status_code == 404
    assert client.post("/api/batches/999/verify", json={"records": []}).status_code == 404
