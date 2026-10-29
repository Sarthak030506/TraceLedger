# TraceLedger Inter-Module Interface Contracts

This document formalizes the agreed contracts, data schemas, and API interfaces between the modules developed by Person 1 (Sidecar), Person 2 (Integrity), and Person 3 (Backend & Blockchain).

---

## 1. Person 1 (Sidecar) Output Contract

The sidecar agent captures security events, sanitizes sensitive data, assigns sequential numbers, deterministically serializes records, and computes a SHA-256 hash.

### Timestamps
All timestamps across the entire pipeline must be whole-second UTC ISO-8601 strings in the exact format:
`YYYY-MM-DDTHH:MM:SSZ` (e.g., `2026-10-29T12:00:00Z`). The sidecar normalizes all ingested timestamps to this format; microseconds and local timezone offsets are not permitted.

### Record Shapes

The off-chain storage layer (`RecordStore`) exposes two distinct record shapes:

#### a) Full Stored Record (`RecordStore.get_records`)
Returned by `RecordStore.get_records(start, end)`. This contains the complete, sanitized event payload used during batch verification and audit inspections. Notice that `record_hash` is **NOT** included in the hashed data:

```json
{
  "event_id": "evt-001a2b3c",
  "sequence_number": 1,
  "timestamp": "2026-10-29T12:00:00Z",
  "event_type": "authentication",
  "source": "auth-service",
  "details": {
    "ip": "192.168.1.xxx",
    "result": "success",
    "user": "alice"
  }
}
```

- **Canonical JSON Hashing Form:** Deterministic JSON serialization of exactly these 6 keys (`event_id`, `sequence_number`, `timestamp`, `event_type`, `source`, `details`), sorted alphabetically at every level, separators `(",", ":")`, UTF-8 encoded without spaces. `record_hash` is NOT part of the hashed data.

#### b) Hash Record (`RecordStore.get_hash_records`)
Returned by `RecordStore.get_hash_records(start, end)`. This is the lightweight record consumed by Person 2 to construct Merkle trees:

```json
{
  "event_id": "evt-001a2b3c",
  "sequence_number": 1,
  "timestamp": "2026-10-29T12:00:00Z",
  "event_type": "authentication",
  "record_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
}
```

### Hash Specification
- **Algorithm:** SHA-256
- **Format:** Lowercase hexadecimal string (64 characters)
- **Prefix:** **NO `0x` prefix**

---

## 2. Person 2 (Integrity & Cryptography) Module Contract

The integrity layer groups record hashes into a Merkle tree, generates inclusion proofs, handles cryptographic signatures (Ed25519), and performs verification.

Merkle leaves are the record_hash values from the sidecar, in sequence_number order. Do not hash them again to make leaves.

verify_batch receives full records (get_records), recomputes each hash with sidecar.hasher.hash_record, then rebuilds the root.

### Core Function Signatures

#### A. `build_merkle_tree`
```python
def build_merkle_tree(record_hashes: list[str]) -> dict:
    """
    Constructs a Merkle tree from an ordered list of record hashes.
    
    Args:
        record_hashes: List of 64-character lowercase SHA-256 hex strings (no '0x').
        
    Returns:
        {
            "merkle_root": str,      # 64-character lowercase hex string
            "leaves": list[str],     # Original record hashes
            "proofs": list[dict]     # Proof paths for each leaf index
        }
    """
```

#### B. `verify_inclusion`
```python
def verify_inclusion(record_hash: str, proof: list[dict], expected_root: str) -> bool:
    """
    Verifies that a specific record hash is included in a Merkle tree root.
    
    Args:
        record_hash: 64-character lowercase hex SHA-256 string (no '0x').
        proof: List of sibling hashes and positions (e.g., [{"position": "left"|"right", "hash": "..."}]).
        expected_root: 64-character lowercase hex root to compare against.
        
    Returns:
        bool: True if proof recomputes to expected_root, False otherwise.
    """
```

#### C. `verify_batch`
```python
def verify_batch(records: list[dict], expected_root: str) -> dict:
    """
    Recomputes hashes and Merkle root from retained records and verifies against expected root.
    verify_batch receives full records (get_records), recomputes each hash with sidecar.hasher.hash_record, then rebuilds the root.
    
    Args:
        records: Ordered list of full record dictionaries (from RecordStore.get_records).
        expected_root: 64-character lowercase hex string.
        
    Returns:
        {
            "verified": bool,
            "expected_root": str,
            "computed_root": str,
            "record_count": int,
            "errors": list[str],
            "message": str
        }
    """
```

### Merkle Tree Specification Rules
- **Leaf hashing:** Merkle leaves are the record_hash values from the sidecar, in sequence_number order. Do not hash them again to make leaves.
- **Internal node hashing:** Pairs of nodes are concatenated and hashed: `SHA256(left_node_bytes + right_node_bytes)`.
- **Odd leaf handling:** If a tree level has an odd number of leaves, **duplicate the last leaf** to form the final pair before hashing up to the parent level.

---

## 3. Person 3 (Backend & Blockchain) Contract

Person 3 manages off-chain persistence, exposes FastAPI endpoints, and anchors batch commitments to the Solidity smart contract.

### Batch Commitment Schema

```json
{
  "batch_id": 1,
  "merkle_root": "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
  "previous_root": "0000000000000000000000000000000000000000000000000000000000000000",
  "first_sequence": 1,
  "last_sequence": 100,
  "record_count": 100,
  "timestamp": 1729000000,
  "signature": "ed25519_hex_or_base64_signature"
}
```

- **`first_sequence`**: Sequence number of the first event in the batch.
- **`last_sequence`**: Sequence number of the last event in the batch (`last_sequence - first_sequence + 1 == record_count`).
- **`previous_root`**: Merkle root of the immediately preceding batch (chained cryptographic history; all zeros for batch 1).

### Signature Handling & On-Chain Protection
Signature: stored on-chain for reference only. The contract does NOT verify Ed25519; the real on-chain protection is the owner-only access control. Signature verification happens off-chain in integrity/signer.py.

### Blockchain / Solidity Formatting Rules
- **Hex Prefix Handling:**
  - In internal Python logic, off-chain storage, and REST API payloads: **No `0x` prefix** (lowercase 64-char hex strings).
  - At the **blockchain boundary** only: Prepend `0x` to format as EVM `bytes32` (e.g., `0x` + 64 hex characters = 66 characters total) when passing to web3.py / smart contract calls.
- **Smart Contract Interface:**
  ```solidity
  function commitBatch(
      uint256 batchId,
      bytes32 merkleRoot,
      bytes32 previousRoot,
      uint256 firstSequence,
      uint256 lastSequence,
      uint256 recordCount,
      uint256 timestamp,
      bytes calldata signature
  ) external;
  ```

---

## Summary of Cross-Module Conventions

| Layer / Context | Hash / Root Format | `0x` Prefix? | Case | Timestamps |
|---|---|---|---|---|
| Sidecar (Person 1) | SHA-256 Hex | No | lowercase | UTC `YYYY-MM-DDTHH:MM:SSZ` |
| Integrity Engine (Person 2) | SHA-256 Hex | No | lowercase | UTC `YYYY-MM-DDTHH:MM:SSZ` |
| Backend & REST API (Person 3) | SHA-256 Hex | No | lowercase | UTC `YYYY-MM-DDTHH:MM:SSZ` / Unix epoch |
| Web3 / Smart Contract (Person 3) | `bytes32` Hex | **Yes (`0x...`)** | lowercase | Unix epoch integer |
