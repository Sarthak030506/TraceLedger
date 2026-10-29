"""Event collection for the MVP: sample events or a local JSON/JSONL file,
plus the ingest pipeline: validate -> sanitize -> sequence -> hash -> store.
"""
import json
from typing import Iterable, Iterator

from .models import ValidationError, validate_raw_event
from .sanitizer import sanitize_event
from .storage import RecordStore


def sample_events() -> list[dict]:
    """Deterministic sample events (includes secrets/PII to exercise the sanitizer)."""
    return [
        {"event_id": "evt-001", "timestamp": "2026-10-29T10:00:00Z", "event_type": "authentication",
         "source": "auth-service",
         "details": {"user": "alice", "email": "alice@example.com", "ip": "192.168.1.45",
                     "result": "success", "password": "hunter2"}},
        {"event_id": "evt-002", "timestamp": "2026-10-29T10:01:10Z", "event_type": "authentication",
         "source": "auth-service",
         "details": {"user": "bob", "ip": "10.0.0.7", "result": "failure", "reason": "bad_password"}},
        {"event_id": "evt-003", "timestamp": "2026-10-29T10:02:30Z", "event_type": "permission_change",
         "source": "iam",
         "details": {"actor": "admin", "target": "bob", "new_role": "editor",
                     "api_key": "sk-live-123456"}},
        {"event_id": "evt-004", "timestamp": "2026-10-29T10:03:45Z", "event_type": "config_change",
         "source": "config-manager",
         "details": {"setting": "session_timeout", "old": 30, "new": 15, "actor": "admin"}},
        {"event_id": "evt-005", "timestamp": "2026-10-29T10:05:00Z", "event_type": "authentication",
         "source": "auth-service",
         "details": {"user": "carol", "email": "carol@corp.in", "ip": "172.16.4.200",
                     "result": "success", "note": "token=abc123 used"}},
    ]


def read_json_file(path: str) -> Iterator[dict]:
    """Read a .json (list) or .jsonl (one event per line) file."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read().strip()
    if not text:
        return
    if text.startswith("["):
        yield from json.loads(text)
    else:
        for line in text.splitlines():
            if line.strip():
                yield json.loads(line)


def ingest_event(raw: dict, store: RecordStore) -> dict:
    """Run one raw event through the whole pipeline. Returns the hash record."""
    clean = sanitize_event(validate_raw_event(raw))
    return store.append(clean)


def ingest_many(events: Iterable[dict], store: RecordStore) -> dict:
    """Ingest events, continuing past invalid ones.
    Returns {"stored": [hash records], "rejected": [(index, error message)]}."""
    stored, rejected = [], []
    for i, raw in enumerate(events):
        try:
            stored.append(ingest_event(raw, store))
        except ValidationError as exc:
            rejected.append((i, str(exc)))
    return {"stored": stored, "rejected": rejected}


if __name__ == "__main__":
    store = RecordStore(":memory:")
    result = ingest_many(sample_events(), store)
    print(json.dumps(result["stored"], indent=2))
    print("rejected:", result["rejected"])
