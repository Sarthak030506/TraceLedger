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

## Receiver

The sidecar includes an authenticated HTTP event receiver built using standard library `http.server`:

### Starting the Receiver
```bash
export SIDECAR_API_KEY="your-secret-api-key"
python -m sidecar.receiver --db data/records.db
```
*(On Windows PowerShell, use `$env:SIDECAR_API_KEY="your-secret-api-key"`)*

### Endpoints
- **`GET /health`** (Public): Returns service status and stored record count.
  ```bash
  curl http://127.0.0.1:8001/health
  # Response: {"status":"ok","record_count":0}
  ```
- **`POST /events`** (Authenticated): Accepts a single JSON event or an array of events up to 64 KB.
  Requires the `X-API-Key` header matching `SIDECAR_API_KEY`.
  Returns `200` with the created hash record(s), `400` on validation errors, `401` on unauthorized/bad key, `409` on duplicate `event_id`, or `413` if payload exceeds 64 KB.

### Curl Example: Ingest Expense Event
```bash
curl -X POST http://127.0.0.1:8001/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{
    "event_id": "exp-001",
    "timestamp": "2026-10-29T12:00:00Z",
    "event_type": "expense_created",
    "source": "expense-tracker",
    "details": {
      "user": "alice",
      "category": "travel",
      "amount_minor": 15050,
      "currency": "USD"
    }
  }'
```

### Expense-Tracker Event Examples
*(Note: Amounts must be represented as **integer minor units** e.g. cents/paise — floating-point numbers are strictly rejected by the validator to prevent representation drift.)*

**1. Expense Created ($150.50):**
```json
{
  "event_id": "exp-101",
  "timestamp": "2026-10-29T14:10:00Z",
  "event_type": "expense_created",
  "source": "expense-tracker",
  "details": {
    "user": "bob",
    "category": "meals",
    "amount_minor": 15050,
    "currency": "USD",
    "merchant": "Bistro Cafe"
  }
}
```

**2. Expense Approved ($42.00):**
```json
{
  "event_id": "exp-102",
  "timestamp": "2026-10-29T14:25:00Z",
  "event_type": "expense_approved",
  "source": "expense-tracker",
  "details": {
    "expense_id": "exp-100",
    "approver": "manager",
    "amount_minor": 4200,
    "currency": "USD"
  }
}
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
