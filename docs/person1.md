# Person 1 — Event Collection, Secure Storage & Record Hashing

**Branch:** `feature/event-collection-hashing`  
**Focus:** Build the foundation that receives events and produces deterministic record hashes.

## Goal

Implement the first part of TraceLedger's pipeline: collect structured security events, sanitize them, assign sequence numbers, store records off-chain, and hash each record reliably.

## Tasks

1. Define a shared security-event schema with fields such as:
   - `event_id`
   - `sequence_number`
   - `timestamp`
   - `event_type`
   - `source`
   - `details` (sanitized; avoid secrets and unnecessary personal data)
2. Implement event collection for the MVP using sample events or a simple local input source.
3. Sanitize/minimize fields before storing or hashing.
4. Ensure records are serialized deterministically before hashing.
5. Use SHA-256 to create a hash for each record.
6. Store raw/sample records off-chain in local files or SQLite, as agreed with the team.
7. Write tests for valid events, missing fields, sanitization and repeatable hashes.
8. Document how Person 2 can consume the output.

## Suggested files

```text
sidecar/
├── models.py
├── collector.py
├── sanitizer.py
├── hasher.py
└── storage.py

tests/
└── test_collection_hashing.py
```

## Interface to provide

Coordinate exact names with Person 2. Proposed output:

```json
{
  "event_id": "evt-001",
  "sequence_number": 1,
  "timestamp": "ISO-8601 timestamp",
  "event_type": "authentication",
  "record_hash": "sha256-hex-digest"
}
```

The hash must be calculated from a documented canonical representation. Do not hash arbitrary dictionary string output that may change field order or formatting.

## Acceptance checklist

- [ ] Events follow the agreed schema.
- [ ] Sensitive fields are removed or masked before processing.
- [ ] Sequence numbers are assigned consistently.
- [ ] Identical canonical records produce identical SHA-256 hashes.
- [ ] A changed record produces a different hash.
- [ ] Stored records remain off-chain.
- [ ] Tests pass and the interface is documented.

## Five-day plan

| Day | Deliverable |
|---|---|
| 1 | Event schema and sample collector |
| 2 | Sanitization, sequence numbers and deterministic serialization |
| 3 | SHA-256 hashing and off-chain storage |
| 4 | Unit tests and integration with Person 2 |
| 5 | Bug fixes and support for end-to-end testing |

## Git workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/event-collection-hashing

git add sidecar tests
git commit -m "Implement event collection and record hashing"
git push -u origin feature/event-collection-hashing
```

## Boundaries

Do **not** implement Merkle trees, smart contracts, FastAPI endpoints, or the dashboard in this branch. Those are assigned to other team members.
