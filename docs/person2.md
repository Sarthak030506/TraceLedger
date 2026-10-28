# Person 2 — Merkle Proofs, Digital Signatures & Verification

**Branch:** `feature-merkle-verification`  
**Focus:** Turn hashed records into verifiable batches and detect local tampering.

## Goal

Build the cryptographic batch layer: construct Merkle trees from Person 1's record hashes, produce inclusion proofs, sign batch metadata, and verify records against a previously created commitment.

## Tasks

1. Agree on the record-hash input/output format with Person 1 before coding.
2. Implement a Merkle tree builder that accepts an ordered list of SHA-256 record hashes.
3. Generate a deterministic Merkle root for each batch.
4. Implement inclusion-proof generation and verification for a record in a batch.
5. Use Ed25519 to sign batch metadata and verify signatures.
6. Implement a local verification function that recomputes hashes/root from retained records and compares them with the expected root.
7. Detect altered, missing, duplicated or reordered records within the retained batch.
8. Add unit tests for valid batches, invalid proofs, changed records, missing records and invalid signatures.
9. Document the batch format and provide a small command-line or Python demo.

## Suggested files

```text
integrity/
├── merkle.py
├── proofs.py
├── signer.py
├── verifier.py
└── models.py

tests/
└── test_merkle_verification.py
```

## Interface to provide

Coordinate final names with Person 1 and Person 3. Proposed functions:

```python
build_merkle_tree(record_hashes) -> {
    "merkle_root": str,
    "proofs": list
}

verify_inclusion(record_hash, proof, expected_root) -> bool

verify_batch(records, expected_root) -> {
    "verified": bool,
    "expected_root": str,
    "computed_root": str,
    "message": str
}
```

Document how an odd number of leaves is handled and ensure tree construction is deterministic. Never trust a root supplied by the same untrusted local records during verification; compare against the previously retained commitment.

## Acceptance checklist

- [ ] Same ordered hash list produces the same Merkle root.
- [ ] Valid inclusion proofs verify successfully.
- [ ] Invalid proofs fail.
- [ ] Modifying, deleting or reordering a record causes batch verification to fail.
- [ ] Ed25519 signatures can be created and verified.
- [ ] Invalid signatures are rejected.
- [ ] Tests and a repeatable local demo pass.

## Five-day plan

| Day | Deliverable |
|---|---|
| 1 | Merkle tree design and agreed interfaces |
| 2 | Root calculation and inclusion proofs |
| 3 | Ed25519 signing and signature verification |
| 4 | Batch verifier and tampering tests |
| 5 | Integrate with Person 1's hashes and support end-to-end demo |

## Git workflow

```bash
git checkout main
git pull origin main
git checkout -b feature-merkle-verification

git add integrity tests
git commit -m "Implement Merkle proofs and integrity verification"
git push -u origin feature-merkle-verification
```

## Boundaries

Do **not** implement event collection/storage, blockchain contracts, FastAPI endpoints, or the dashboard. Keep this module independent and expose clear Python functions.
