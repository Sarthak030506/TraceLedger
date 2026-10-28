# TraceLedger Inter-Module Interface Contracts

This document formalizes the agreed contracts, data schemas, and API interfaces between the modules developed by Person 1 (Sidecar), Person 2 (Integrity), and Person 3 (Backend & Blockchain).

---

## 1. Person 1 (Sidecar) Output Contract

The sidecar agent captures security events, sanitizes sensitive data, assigns sequential numbers, deterministically serializes records, and computes a SHA-256 hash.

### Record Schema

Each processed event output by Person 1 must adhere to this JSON structure:

```json
{
  "event_id": "evt-001a2b3c",
  "sequence_number": 1,
  "timestamp": "2026-10-29T12:00:00.000000Z",
  "event_type": "authentication_success",
  "source": "auth-service",
  "details": {
    "user": "alice",
    "ip_address": "192.168.1.10"
  },
  "record_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
}
```

### Hash Specification
- **Algorithm:** SHA-256
- **Format:** Lowercase hexadecimal string (64 characters)
- **Prefix:** **NO `0x` prefix**
- **Canonical Serialization:** Deterministic JSON serialization (sorted keys, no extraneous whitespace, UTF-8 encoded) before hashing.
- **Minimal Required Fields for downstream verification:**
  ```json
  {
    "event_id": "string",
    "sequence_number": 1,
    "timestamp": "ISO-8601 string",
    "event_type": "string",
    "record_hash": "64-char lowercase hex SHA-256"
  }
  ```

---

## 2. Person 2 (Integrity & Cryptography) Module Contract

The integrity layer groups record hashes into a Merkle tree, generates inclusion proofs, handles cryptographic signatures (Ed25519), and performs verification.

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
    
    Args:
        records: Ordered list of record dictionaries.
        expected_root: 64-character lowercase hex string.
        
    Returns:
        {
            "verified": bool,
            "expected_root": str,
            "calculated_root": str,
            "record_count": int,
            "errors": list[str]      # List of tampering or mismatch details if verified is False
        }
    """
```

### Merkle Tree Specification Rules
- **Leaf hashing:** `hash(record_bytes)` produces the initial leaf hash (64-char hex).
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
  "record_count": 100,
  "timestamp": 1729000000,
  "signature": "ed25519_hex_or_base64_signature"
}
```

### Blockchain / Solidity Formatting Rules
- **Hex Prefix Handling:**
  - In internal Python logic, off-chain storage, and REST API payloads: **No `0x` prefix** (lowercase 64-char hex strings).
  - At the **blockchain boundary** only: Prepend `0x` to format as EVM `bytes32` (e.g., `0x` + 64 hex characters = 66 characters total) when passing to web3.py / smart contract calls.
- **Smart Contract Interface:**
  ```solidity
  function commitBatch(
      uint256 batchId,
      bytes32 merkleRoot,
      uint256 recordCount,
      uint256 timestamp,
      bytes calldata signature
  ) external;
  ```

---

## Summary of Cross-Module Conventions

| Layer / Context | Hash / Root Format | `0x` Prefix? | Case |
|---|---|---|---|
| Sidecar (Person 1) | SHA-256 Hex | No | lowercase |
| Integrity Engine (Person 2) | SHA-256 Hex | No | lowercase |
| Backend & REST API (Person 3) | SHA-256 Hex | No | lowercase |
| Web3 / Smart Contract (Person 3) | `bytes32` Hex | **Yes (`0x...`)** | lowercase |
