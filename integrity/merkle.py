"""Merkle tree construction, root computation, and proof path generation.

Follows the INTERFACES.md specification:
- Leaves: Lowercase 64-char SHA-256 hex string hashes from sidecar (no 0x). Leaves are NOT re-hashed.
- Pairs: Concatenate raw 32-byte digests: SHA256(left_node_bytes + right_node_bytes).
- Odd leaf handling: If a tree level has an odd number of nodes, duplicate the last node to form the final pair.
- Output: merkle_root (64 hex lowercase), leaves (original list), proofs (proof path per leaf).
"""
import hashlib
from typing import Any

from .models import MerkleTreeResult


def validate_hash_hex(h: str, name: str = "hash") -> str:
    """Validate and normalize a 64-character lowercase SHA-256 hex string."""
    if not isinstance(h, str):
        raise TypeError(f"{name} must be a string, got {type(h).__name__}")
    normalized = h.strip().lower()
    if normalized.startswith("0x"):
        raise ValueError(f"{name} must not include '0x' prefix: {h!r}")
    if len(normalized) != 64 or not all(c in "0123456789abcdef" for c in normalized):
        raise ValueError(f"{name} must be a 64-character hex string: {h!r}")
    return normalized


def hash_pair(left_hex: str, right_hex: str) -> str:
    """Hash two 32-byte SHA-256 digests together in binary format.

    Internal node hashing rule: SHA256(left_node_bytes + right_node_bytes).
    """
    left_bytes = bytes.fromhex(validate_hash_hex(left_hex, "left_hex"))
    right_bytes = bytes.fromhex(validate_hash_hex(right_hex, "right_hex"))
    return hashlib.sha256(left_bytes + right_bytes).hexdigest()


def build_merkle_tree(record_hashes: list[str]) -> dict[str, Any]:
    """Constructs a deterministic Merkle tree from an ordered list of record hashes.

    Args:
        record_hashes: Ordered list of 64-character lowercase SHA-256 hex strings (no '0x').

    Returns:
        {
            "merkle_root": str,      # 64-character lowercase hex string
            "leaves": list[str],     # Original record hashes
            "proofs": list[list]     # Proof paths for each leaf index
        }
    """
    if not isinstance(record_hashes, list):
        raise TypeError("record_hashes must be a list of hex strings")

    validated_leaves = [validate_hash_hex(h, f"record_hashes[{i}]") for i, h in enumerate(record_hashes)]

    if not validated_leaves:
        empty_root = "0" * 64
        return MerkleTreeResult(
            merkle_root=empty_root,
            leaves=[],
            proofs=[],
        ).to_dict()

    if len(validated_leaves) == 1:
        single_leaf = validated_leaves[0]
        return MerkleTreeResult(
            merkle_root=single_leaf,
            leaves=[single_leaf],
            proofs=[[]],
        ).to_dict()

    # Build levels from bottom up, duplicating last element on odd length levels
    levels: list[list[str]] = []
    current_level = list(validated_leaves)

    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
        levels.append(list(current_level))
        next_level = [
            hash_pair(current_level[j], current_level[j + 1])
            for j in range(0, len(current_level), 2)
        ]
        current_level = next_level

    merkle_root = current_level[0]

    # Generate inclusion proofs for each original leaf
    proofs: list[list[dict[str, str]]] = []
    for i in range(len(validated_leaves)):
        idx = i
        proof_path: list[dict[str, str]] = []
        for level in levels:
            sibling_idx = idx ^ 1
            position = "right" if (idx % 2 == 0) else "left"
            sibling_hash = level[sibling_idx]
            proof_path.append({"position": position, "hash": sibling_hash})
            idx = idx // 2
        proofs.append(proof_path)

    return MerkleTreeResult(
        merkle_root=merkle_root,
        leaves=validated_leaves,
        proofs=proofs,
    ).to_dict()
