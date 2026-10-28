# Sidecar: Event Collection & Record Hashing (Person 1)

Pipeline: `raw event -> validate -> sanitize -> sequence number -> canonical JSON -> SHA-256 -> SQLite (off-chain)`

## Quick start
```bash
pip install pytest
python -m pytest -q                 # run tests
python -m sidecar.collector         # demo: ingest 5 sample events, print hash records
```
```python
from sidecar.collector import sample_events, ingest_many
from sidecar.storage import RecordStore

store = RecordStore("records.db")
ingest_many(sample_events(), store)
hashes = store.get_hash_records()        # <- what Person 2 consumes
```

## Output for Person 2
`store.get_hash_records(start=1, end=None)` returns a list ordered by `sequence_number`:
```json
{
  "event_id": "evt-001",
  "sequence_number": 1,
  "timestamp": "2026-10-29T10:00:00Z",
  "event_type": "authentication",
  "record_hash": "64-char lowercase hex, no 0x prefix"
}
```
* Build the Merkle tree from `record_hash` values **in sequence_number order**.
* A batch = a contiguous range, e.g. `get_hash_records(1, 5)`.
* The contract uses `bytes32`: add `0x` only at the blockchain layer.
* `store.get_records(start, end)` returns the full sanitized records (with `details`) for re-hashing during verification.

## Canonical representation (what is hashed)
JSON object with exactly these keys: `event_id, sequence_number, timestamp, event_type, source, details`
* keys sorted at every level, separators `(",", ":")`, UTF-8, `ensure_ascii=False`, NaN rejected
* `record_hash` itself is NOT hashed
* `hash = SHA-256(canonical_json.encode("utf-8"))`, lowercase hex
* To re-verify a stored record, call `hash_record(record)` from `sidecar/hasher.py`

## Rules enforced
* Required: `event_id, timestamp, event_type, source, details`; extra fields are dropped
* Timestamp must carry a timezone and is normalized to UTC `YYYY-MM-DDTHH:MM:SSZ`
* No floats in `details` (unstable text form); use int or str
* Sensitive keys (password, token, secret, api_key, cookie, ...) are dropped; emails masked (`a***@x.com`); IPv4 masked (`1.2.3.xxx`); inline `token=...` redacted
* Sequence numbers: consecutive from 1, assigned atomically in one DB transaction; duplicate `event_id` is rejected without creating a gap

## Open decisions to confirm with the team
1. Hex without `0x` (current choice)
2. `sequence_number` is part of the hash (makes reordering detectable)
3. SQLite for storage (current choice)
