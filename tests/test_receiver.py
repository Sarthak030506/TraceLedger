"""Tests for the authenticated event receiver."""
import concurrent.futures
import json
import threading
import urllib.error
import urllib.request
from typing import Any

import pytest

from sidecar.receiver import make_server
from sidecar.storage import RecordStore


def request_json(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: Any = None,
) -> tuple[int, Any]:
    """Helper to perform HTTP requests using standard library urllib."""
    req_headers = dict(headers or {})
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/json"
        elif isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        elif isinstance(body, str):
            data = body.encode("utf-8")
        req_headers["Content-Length"] = str(len(data))

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except Exception:
            parsed = raw
        return exc.code, parsed


@pytest.fixture
def receiver(tmp_path, monkeypatch):
    """Start receiver on a random port (port 0) with a fresh SQLite DB in tmp_path."""
    test_key = "test-secret-key-123"
    monkeypatch.setenv("SIDECAR_API_KEY", test_key)
    db_file = tmp_path / "receiver_test.db"

    server = make_server(host="127.0.0.1", port=0, db_path=str(db_file), api_key=test_key)
    assigned_port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{assigned_port}"

    yield {
        "base_url": base_url,
        "api_key": test_key,
        "db_path": str(db_file),
    }

    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_refuse_to_start_if_api_key_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("SIDECAR_API_KEY", raising=False)
    db_file = tmp_path / "refuse.db"
    with pytest.raises(RuntimeError, match="SIDECAR_API_KEY environment variable is not set"):
        make_server(host="127.0.0.1", port=0, db_path=str(db_file), api_key=None)


def test_health_endpoint(receiver):
    url = f"{receiver['base_url']}/health"
    status, data = request_json(url, method="GET")
    assert status == 200
    assert data == {"status": "ok", "record_count": 0}


def test_valid_event(receiver):
    url = f"{receiver['base_url']}/events"
    event = {
        "event_id": "evt-rec-001",
        "timestamp": "2026-10-29T12:00:00Z",
        "event_type": "expense_created",
        "source": "expense-tracker",
        "details": {"amount_cents": 4500, "category": "travel", "currency": "USD"},
    }

    status, data = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=event,
    )
    assert status == 200
    assert data["event_id"] == "evt-rec-001"
    assert data["sequence_number"] == 1
    assert data["timestamp"] == "2026-10-29T12:00:00Z"
    assert data["event_type"] == "expense_created"
    assert len(data["record_hash"]) == 64
    assert not data["record_hash"].startswith("0x")

    # Verify health endpoint increments count
    status_h, data_h = request_json(f"{receiver['base_url']}/health", method="GET")
    assert status_h == 200
    assert data_h["record_count"] == 1


def test_event_list(receiver):
    url = f"{receiver['base_url']}/events"
    events = [
        {
            "event_id": "evt-list-001",
            "timestamp": "2026-10-29T12:01:00Z",
            "event_type": "expense_created",
            "source": "expense-tracker",
            "details": {"amount_cents": 1200, "note": "coffee"},
        },
        {
            "event_id": "evt-list-002",
            "timestamp": "2026-10-29T12:02:00Z",
            "event_type": "expense_approved",
            "source": "expense-tracker",
            "details": {"amount_cents": 1200, "approver": "manager"},
        },
    ]

    status, data = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=events,
    )
    assert status == 200
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["sequence_number"] == 1
    assert data[1]["sequence_number"] == 2
    assert len(data[0]["record_hash"]) == 64
    assert len(data[1]["record_hash"]) == 64


def test_bad_api_key(receiver):
    url = f"{receiver['base_url']}/events"
    event = {
        "event_id": "evt-auth-001",
        "timestamp": "2026-10-29T12:00:00Z",
        "event_type": "auth",
        "source": "src",
        "details": {"foo": "bar"},
    }

    status, data = request_json(
        url,
        method="POST",
        headers={"X-API-Key": "wrong-key-value"},
        body=event,
    )
    assert status == 401
    assert "error" in data


def test_missing_api_key(receiver):
    url = f"{receiver['base_url']}/events"
    event = {
        "event_id": "evt-auth-002",
        "timestamp": "2026-10-29T12:00:00Z",
        "event_type": "auth",
        "source": "src",
        "details": {"foo": "bar"},
    }

    status, data = request_json(url, method="POST", body=event)
    assert status == 401
    assert "error" in data


def test_invalid_event(receiver):
    url = f"{receiver['base_url']}/events"
    # Missing required 'timestamp' field
    bad_event = {
        "event_id": "evt-bad-001",
        "event_type": "auth",
        "source": "src",
        "details": {"foo": "bar"},
    }

    status, data = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=bad_event,
    )
    assert status == 400
    assert "missing required fields" in data["error"]


def test_duplicate_event_id(receiver):
    url = f"{receiver['base_url']}/events"
    event = {
        "event_id": "evt-dup-unique",
        "timestamp": "2026-10-29T12:00:00Z",
        "event_type": "auth",
        "source": "src",
        "details": {"step": 1},
    }

    # First ingestion succeeds
    status1, _ = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=event,
    )
    assert status1 == 200

    # Second ingestion with same event_id returns 409 Conflict
    status2, data2 = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=event,
    )
    assert status2 == 409
    assert "duplicate event_id" in data2["error"]


def test_oversized_body(receiver):
    url = f"{receiver['base_url']}/events"
    # Create body larger than 64 KB (65536 bytes)
    big_details = {"padding": "A" * (65 * 1024)}
    big_event = {
        "event_id": "evt-huge",
        "timestamp": "2026-10-29T12:00:00Z",
        "event_type": "auth",
        "source": "src",
        "details": big_details,
    }

    status, data = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=big_event,
    )
    assert status == 413
    assert "Payload too large" in data["error"]


def test_consecutive_sequence_numbers_under_20_parallel_requests(receiver):
    url = f"{receiver['base_url']}/events"
    n_requests = 20

    def post_single(idx: int) -> tuple[int, Any]:
        evt = {
            "event_id": f"evt-par-{idx:04d}",
            "timestamp": f"2026-10-29T12:{idx // 60:02d}:{idx % 60:02d}Z",
            "event_type": "parallel_event",
            "source": "parallel-runner",
            "details": {"seq_index": idx, "amount": idx * 100},
        }
        return request_json(
            url,
            method="POST",
            headers={"X-API-Key": receiver["api_key"]},
            body=evt,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(post_single, range(n_requests)))

    for status, data in results:
        assert status == 200
        assert "record_hash" in data

    # Verify directly from database
    store = RecordStore(receiver["db_path"])
    records = store.get_records()
    store.close()

    assert len(records) == n_requests
    sequences = [r["sequence_number"] for r in records]
    assert sequences == list(range(1, n_requests + 1))


def test_secrets_never_appear_in_stored_data(receiver):
    url = f"{receiver['base_url']}/events"
    secret_pw = "SuperSecretPassword123"
    secret_key = "sk-live-abcdef123456"
    secret_token = "token987654321"

    event = {
        "event_id": "evt-secret-audit",
        "timestamp": "2026-10-29T12:00:00Z",
        "event_type": "login_audit",
        "source": "auth-portal",
        "details": {
            "user": "alice",
            "email": "alice@corp.com",
            "ip": "192.168.1.55",
            "password": secret_pw,
            "api_key": secret_key,
            "session_token": secret_token,
            "audit_log": f"authenticated with token={secret_token}",
        },
    }

    status, _ = request_json(
        url,
        method="POST",
        headers={"X-API-Key": receiver["api_key"]},
        body=event,
    )
    assert status == 200

    # Inspect stored records
    store = RecordStore(receiver["db_path"])
    rows = store.conn.execute("SELECT * FROM records WHERE event_id = 'evt-secret-audit'").fetchall()
    store.close()

    assert len(rows) == 1
    row = dict(rows[0])
    raw_stored_details = row["details_json"]
    raw_canonical = row["canonical_json"]

    # Assert secrets never appear anywhere in stored records
    assert secret_pw not in raw_stored_details
    assert secret_pw not in raw_canonical
    assert secret_key not in raw_stored_details
    assert secret_key not in raw_canonical
    assert secret_token not in raw_stored_details
    assert secret_token not in raw_canonical

    # Assert PII masking was applied
    details = json.loads(raw_stored_details)
    assert details["email"] == "a***@corp.com"
    assert details["ip"] == "192.168.1.xxx"


def test_other_paths_and_methods(receiver):
    # GET /events -> 405
    status, _ = request_json(f"{receiver['base_url']}/events", method="GET")
    assert status == 405

    # POST /health -> 405
    status, _ = request_json(f"{receiver['base_url']}/health", method="POST", body={})
    assert status == 405

    # GET /unknown -> 404
    status, _ = request_json(f"{receiver['base_url']}/unknown", method="GET")
    assert status == 404

    # POST /unknown -> 404
    status, _ = request_json(f"{receiver['base_url']}/unknown", method="POST", body={})
    assert status == 404
