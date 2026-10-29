"""Tests for the Demo Expense Tracker App.

Verifies:
1. The correct event is built for each action.
2. No floats appear in any payload.
3. A failed send goes to the outbox without raising an error (mocked HTTP call).
4. FastAPI endpoints execute cleanly.
"""
from datetime import datetime
import json
import os
from unittest.mock import patch
import urllib.error

from fastapi.testclient import TestClient
import pytest

from demo_app.auditor import Auditor, assert_no_floats, build_audit_event
import demo_app.database as db
from demo_app.main import app


@pytest.fixture
def test_auditor(tmp_path):
    """Fixture providing an isolated Auditor pointing to a temporary outbox."""
    outbox_file = tmp_path / "test_outbox.jsonl"
    auditor = Auditor(
        sidecar_url="http://127.0.0.1:8999/events",
        api_key="test-key",
        outbox_path=str(outbox_file),
    )
    return auditor


@pytest.fixture
def test_db(tmp_path):
    """Fixture providing an isolated SQLite database path."""
    db_file = tmp_path / "test_demo_expenses.db"
    db.init_db(str(db_file))
    return str(db_file)


# ---------------------------------------------------------------------------
# 1. Event Building & Structure Tests
# ---------------------------------------------------------------------------


def test_build_event_structure():
    """Verify standard shape: event_id (uuid4), ISO-8601 UTC timestamp, source, details."""
    details = {"user": "alice", "result": "success"}
    event = build_audit_event("authentication", details)

    assert isinstance(event["event_id"], str)
    assert len(event["event_id"]) == 36  # UUID4
    assert event["event_type"] == "authentication"
    assert event["source"] == "expense-demo"
    assert event["details"] == details

    # Verify timestamp format YYYY-MM-DDTHH:MM:SSZ (whole seconds UTC)
    ts = event["timestamp"]
    assert ts.endswith("Z")
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    assert dt is not None


def test_all_action_event_types_built_correctly():
    """Verify each required event type produces the agreed schema."""
    # 1. authentication (success)
    auth_success = build_audit_event("authentication", {"user": "alice", "result": "success"})
    assert auth_success["event_type"] == "authentication"
    assert auth_success["details"] == {"user": "alice", "result": "success"}

    # 2. authentication (failure)
    auth_fail = build_audit_event(
        "authentication",
        {"user": "bob", "result": "failure", "reason": "invalid_credentials"},
    )
    assert auth_fail["event_type"] == "authentication"
    assert auth_fail["details"]["result"] == "failure"
    assert "password" not in auth_fail["details"]

    # 3. expense_created
    exp_created = build_audit_event(
        "expense_created",
        {"expense_id": "exp-1", "amount_minor": 15000, "category": "travel", "user": "alice"},
    )
    assert exp_created["event_type"] == "expense_created"
    assert exp_created["details"]["amount_minor"] == 15000
    assert "description" not in exp_created["details"]

    # 4. expense_updated (must include expense_id, old_amount_minor, new_amount_minor)
    exp_updated = build_audit_event(
        "expense_updated",
        {
            "expense_id": "exp-1",
            "old_amount_minor": 15000,
            "new_amount_minor": 20000,
            "user": "alice",
        },
    )
    assert exp_updated["event_type"] == "expense_updated"
    assert exp_updated["details"]["old_amount_minor"] == 15000
    assert exp_updated["details"]["new_amount_minor"] == 20000
    assert exp_updated["details"]["expense_id"] == "exp-1"

    # 5. expense_deleted
    exp_deleted = build_audit_event(
        "expense_deleted",
        {"expense_id": "exp-1", "amount_minor": 20000, "user": "alice"},
    )
    assert exp_deleted["event_type"] == "expense_deleted"
    assert exp_deleted["details"]["amount_minor"] == 20000

    # 6. budget_changed
    budget_evt = build_audit_event(
        "budget_changed",
        {"old_budget_minor": 5000000, "new_budget_minor": 6000000, "user": "alice"},
    )
    assert budget_evt["event_type"] == "budget_changed"
    assert budget_evt["details"]["old_budget_minor"] == 5000000
    assert budget_evt["details"]["new_budget_minor"] == 6000000

    # 7. data_exported
    export_evt = build_audit_event(
        "data_exported",
        {"record_count": 10, "format": "csv", "user": "alice"},
    )
    assert export_evt["event_type"] == "data_exported"
    assert export_evt["details"] == {"record_count": 10, "format": "csv", "user": "alice"}


# ---------------------------------------------------------------------------
# 2. Strict Float Rejection Tests
# ---------------------------------------------------------------------------


def test_no_floats_allowed_in_audit_payloads():
    """Verify that floats anywhere in payload or details raise ValueError."""
    # Direct float
    with pytest.raises(ValueError, match="Float detected"):
        assert_no_floats(150.50)

    # Float in dict
    with pytest.raises(ValueError, match="Float detected"):
        build_audit_event("expense_created", {"amount_minor": 150.50})

    # Float in nested dict
    with pytest.raises(ValueError, match="Float detected"):
        assert_no_floats({"meta": {"val": 12.34}})

    # Valid integers pass with no error
    assert_no_floats({"amount_minor": 15050, "count": 2, "zero": 0})


def test_database_rejects_floats(test_db):
    """Ensure database layer strictly enforces integers for currency."""
    with pytest.raises(ValueError, match="Float detected|must be an integer"):
        db.add_expense("alice", "meals", 12.50, "Lunch", db_path=test_db)  # type: ignore

    with pytest.raises(ValueError, match="Float detected|must be an integer"):
        db.update_expense_amount("some-id", 45.00, db_path=test_db)  # type: ignore

    with pytest.raises(ValueError, match="Float detected|must be an integer"):
        db.set_budget(5000.50, db_path=test_db)  # type: ignore


# ---------------------------------------------------------------------------
# 3. Reliability & Outbox Fallback Tests
# ---------------------------------------------------------------------------


def test_failed_send_appends_to_outbox_without_raising_error(test_auditor):
    """Mock HTTP call failure; verify event is saved to outbox file and no error is raised."""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        # Synchronous emit to verify immediately
        event = test_auditor.emit(
            "expense_created",
            {"expense_id": "exp-fail-1", "amount_minor": 5000, "category": "travel", "user": "alice"},
            sync=True,
        )

    assert event is not None
    assert test_auditor.sent_count == 0

    # Verify event appended to outbox.jsonl
    assert os.path.exists(test_auditor.outbox_path)
    with open(test_auditor.outbox_path, "r", encoding="utf-8") as fh:
        lines = [json.loads(line) for line in fh if line.strip()]

    assert len(lines) == 1
    assert lines[0]["event_id"] == event["event_id"]
    assert lines[0]["event_type"] == "expense_created"

    status = test_auditor.get_status()
    assert status["events_sent"] == 0
    assert status["queued"] == 1


def test_outbox_drains_when_receiver_recovers(test_auditor):
    """Verify that flush_outbox drains queued events when HTTP begins succeeding."""
    # 1. Queue 2 events while service is down
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Server down")):
        test_auditor.emit("authentication", {"user": "alice", "result": "success"}, sync=True)
        test_auditor.emit("budget_changed", {"old_budget_minor": 100, "new_budget_minor": 200, "user": "alice"}, sync=True)

    status_down = test_auditor.get_status()
    assert status_down["queued"] == 2
    assert status_down["events_sent"] == 0

    # 2. Service recovers: mock urlopen to succeed (HTTP 200)
    class DummyResponse:
        status = 200
        def read(self): return b'{"status":"ok"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    with patch("urllib.request.urlopen", return_value=DummyResponse()):
        flushed = test_auditor.flush_outbox()

    assert flushed == 2
    status_up = test_auditor.get_status()
    assert status_up["queued"] == 0
    assert status_up["events_sent"] == 2


# ---------------------------------------------------------------------------
# 4. FastAPI End-to-End Route Tests
# ---------------------------------------------------------------------------


def test_login_routes():
    """Verify authentication endpoint successes and failure auditing."""
    client = TestClient(app)

    with patch("demo_app.main.default_auditor.emit") as mock_emit:
        # Success
        resp = client.post("/api/login", json={"username": "alice", "password": "password123"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "user": "alice"}
        mock_emit.assert_called_with("authentication", {"user": "alice", "result": "success"})

        # Failure
        resp_bad = client.post("/api/login", json={"username": "alice", "password": "wrongpassword"})
        assert resp_bad.status_code == 401
        mock_emit.assert_called_with(
            "authentication",
            {"user": "alice", "result": "failure", "reason": "invalid_credentials"},
        )


def test_expense_crud_routes():
    """Verify expense creation, editing, deletion, and CSV export."""
    client = TestClient(app)

    with patch("demo_app.main.default_auditor.emit") as mock_emit:
        # 1. Create expense
        resp_create = client.post(
            "/api/expenses",
            json={
                "user": "alice",
                "category": "travel",
                "amount_minor": 12500,
                "description": "Taxi ride",
            },
        )
        assert resp_create.status_code == 200
        created = resp_create.json()
        assert created["amount_minor"] == 12500
        expense_id = created["id"]

        mock_emit.assert_called_with(
            "expense_created",
            {
                "expense_id": expense_id,
                "amount_minor": 12500,
                "category": "travel",
                "user": "alice",
            },
        )

        # 2. Update expense amount
        resp_edit = client.put(
            f"/api/expenses/{expense_id}",
            json={"amount_minor": 15000, "user": "alice"},
        )
        assert resp_edit.status_code == 200
        assert resp_edit.json()["amount_minor"] == 15000

        mock_emit.assert_called_with(
            "expense_updated",
            {
                "expense_id": expense_id,
                "old_amount_minor": 12500,
                "new_amount_minor": 15000,
                "user": "alice",
            },
        )

        # 3. Budget update
        resp_budget = client.post(
            "/api/budget",
            json={"budget_minor": 8000000, "user": "alice"},
        )
        assert resp_budget.status_code == 200
        assert resp_budget.json()["budget_minor"] == 8000000
        assert mock_emit.call_args[0][0] == "budget_changed"

        # 4. Export CSV
        resp_export = client.get("/api/export?user=alice")
        assert resp_export.status_code == 200
        assert "text/csv" in resp_export.headers["content-type"]
        assert "Taxi ride" in resp_export.text
        assert mock_emit.call_args[0][0] == "data_exported"

        # 5. Delete expense
        resp_del = client.delete(f"/api/expenses/{expense_id}?user=alice")
        assert resp_del.status_code == 200
        assert mock_emit.call_args[0][0] == "expense_deleted"
