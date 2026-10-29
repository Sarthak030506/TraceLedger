import copy
import hashlib
import json

import pytest

from sidecar.collector import ingest_event, ingest_many, read_json_file, sample_events
from sidecar.hasher import canonical_json, hash_record
from sidecar.models import ValidationError, build_record, validate_raw_event
from sidecar.sanitizer import mask_email, mask_ip, sanitize_details
from sidecar.storage import DuplicateEventError, RecordStore


@pytest.fixture
def store():
    s = RecordStore(":memory:")
    yield s
    s.close()


def good_event(**over):
    e = {"event_id": "evt-x", "timestamp": "2026-10-29T10:00:00Z",
         "event_type": "authentication", "source": "auth", "details": {"result": "ok"}}
    e.update(over)
    return e


# ---------- schema / validation ----------
def test_valid_event_passes():
    out = validate_raw_event(good_event())
    assert out["event_id"] == "evt-x" and out["timestamp"] == "2026-10-29T10:00:00Z"


@pytest.mark.parametrize("field", ["event_id", "timestamp", "event_type", "source", "details"])
def test_missing_field_rejected(field):
    e = good_event()
    del e[field]
    with pytest.raises(ValidationError):
        validate_raw_event(e)


def test_bad_timestamp_rejected():
    for bad in ("yesterday", "2026-10-29T10:00:00", 12345):
        with pytest.raises(ValidationError):
            validate_raw_event(good_event(timestamp=bad))


def test_timestamp_normalized_to_utc():
    out = validate_raw_event(good_event(timestamp="2026-10-29T15:30:00+05:30"))
    assert out["timestamp"] == "2026-10-29T10:00:00Z"


def test_floats_rejected():
    with pytest.raises(ValidationError):
        validate_raw_event(good_event(details={"score": 0.5}))


def test_unknown_fields_dropped():
    out = validate_raw_event(good_event(extra="junk"))
    assert "extra" not in out


# ---------- sanitization ----------
def test_sensitive_keys_removed():
    d = sanitize_details({"user": "a", "password": "x", "API_KEY": "y", "auth_token": "z"})
    assert d == {"user": "a"}


def test_nested_sensitive_keys_removed():
    d = sanitize_details({"ctx": {"secret": "s", "ok": 1}, "items": [{"token": "t", "n": 2}]})
    assert d == {"ctx": {"ok": 1}, "items": [{"n": 2}]}


def test_email_and_ip_masked():
    assert mask_email("alice@example.com") == "a***@example.com"
    assert mask_ip("192.168.1.45") == "192.168.1.xxx"


def test_inline_secret_redacted():
    d = sanitize_details({"note": "token=abc123 used"})
    assert "abc123" not in d["note"]


def test_sanitize_does_not_mutate_input():
    d = {"password": "p", "ip": "1.2.3.4"}
    before = copy.deepcopy(d)
    sanitize_details(d)
    assert d == before


def test_pipeline_never_stores_secrets(store):
    for e in sample_events():
        ingest_event(e, store)
    dump = json.dumps(store.get_records()) + "".join(
        r["canonical_json"] for r in store.conn.execute("SELECT canonical_json FROM records"))
    for secret in ("hunter2", "sk-live-123456", "abc123", "alice@example.com", "192.168.1.45"):
        assert secret not in dump


# ---------- hashing ----------
def rec(seq=1, **over):
    r = build_record(validate_raw_event(good_event(**over)), seq)
    return r


def test_hash_is_sha256_hex():
    h = hash_record(rec())
    assert len(h) == 64 and h == h.lower() and not h.startswith("0x")
    int(h, 16)


def test_identical_records_same_hash():
    assert hash_record(rec()) == hash_record(rec())


def test_key_order_does_not_matter():
    a = rec(details={"a": 1, "b": 2})
    b = rec(details={"b": 2, "a": 1})
    assert hash_record(a) == hash_record(b)


def test_changed_record_changes_hash():
    base = hash_record(rec())
    assert hash_record(rec(source="other")) != base
    assert hash_record(rec(details={"result": "fail"})) != base
    assert hash_record(rec(seq=2)) != base  # sequence number is hashed -> reordering detectable


def test_canonical_form_is_documented_format():
    r = rec(details={"b": 1, "a": "é"})
    expected = ('{"details":{"a":"é","b":1},"event_id":"evt-x","event_type":"authentication",'
                '"sequence_number":1,"source":"auth","timestamp":"2026-10-29T10:00:00Z"}')
    assert canonical_json(r) == expected
    assert hash_record(r) == hashlib.sha256(expected.encode("utf-8")).hexdigest()


# ---------- storage / sequence numbers ----------
def test_sequence_numbers_consecutive(store):
    out = ingest_many(sample_events(), store)["stored"]
    assert [r["sequence_number"] for r in out] == [1, 2, 3, 4, 5]


def test_hash_record_interface_shape(store):
    ingest_event(sample_events()[0], store)
    r = store.get_hash_records()[0]
    assert set(r) == {"event_id", "sequence_number", "timestamp", "event_type", "record_hash"}


def test_repeatable_hashes_across_runs():
    h = []
    for _ in range(2):
        s = RecordStore(":memory:")
        ingest_many(sample_events(), s)
        h.append([r["record_hash"] for r in s.get_hash_records()])
        s.close()
    assert h[0] == h[1]


def test_duplicate_event_id_rejected(store):
    ingest_event(good_event(), store)
    with pytest.raises(DuplicateEventError):
        ingest_event(good_event(), store)
    assert store.count() == 1  # no sequence gap created
    assert ingest_event(good_event(event_id="evt-y"), store)["sequence_number"] == 2


def test_ingest_many_skips_invalid(store):
    events = sample_events()
    events.insert(1, {"event_id": "bad"})
    res = ingest_many(events, store)
    assert len(res["stored"]) == 5 and len(res["rejected"]) == 1
    assert [r["sequence_number"] for r in res["stored"]] == [1, 2, 3, 4, 5]


def test_range_query_for_batches(store):
    ingest_many(sample_events(), store)
    batch = store.get_hash_records(2, 4)
    assert [r["sequence_number"] for r in batch] == [2, 3, 4]


def test_local_tamper_detected_by_recompute(store):
    ingest_many(sample_events(), store)
    assert store.recompute_mismatches() == []
    store.conn.execute("UPDATE records SET canonical_json = replace(canonical_json,'admin','evil') WHERE sequence_number=3")
    assert store.recompute_mismatches() == [3]


def test_persisted_to_file_and_reloaded(tmp_path):
    p = str(tmp_path / "r.db")
    s = RecordStore(p)
    ingest_many(sample_events(), s)
    hashes = s.get_hash_records()
    s.close()
    s2 = RecordStore(p)
    assert s2.get_hash_records() == hashes
    assert ingest_event(good_event(event_id="evt-new"), s2)["sequence_number"] == 6
    s2.close()


def test_read_json_and_jsonl(tmp_path):
    evs = sample_events()
    (tmp_path / "a.json").write_text(json.dumps(evs))
    (tmp_path / "b.jsonl").write_text("\n".join(json.dumps(e) for e in evs))
    assert list(read_json_file(str(tmp_path / "a.json"))) == evs
    assert list(read_json_file(str(tmp_path / "b.jsonl"))) == evs
