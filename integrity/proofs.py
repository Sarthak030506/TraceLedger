"""Merkle inclusion proof generation and verification."""
from typing import Any

from .merkle import build_merkle_tree, hash_pair, validate_hash_hex


def verify_inclusion(record_hash: str, proof: list[dict[str, str]], expected_root: str) -> bool:
    """Verifies that a specific record hash is included in a Merkle tree root.

    Args:
        record_hash: 64-character lowercase hex SHA-256 string (no '0x').
        proof: List of sibling hashes and positions (e.g., [{"position": "left"|"right", "hash": "..."}]).
        expected_root: 64-character lowercase hex root to compare against.

    Returns:
        bool: True if proof recomputes to expected_root, False otherwise.
    """
    try:
        current = validate_hash_hex(record_hash, "record_hash")
        target_root = validate_hash_hex(expected_root, "expected_root")
    except (TypeError, ValueError):
        return False

    if not isinstance(proof, list):
        return False

    current_hash = current

    try:
        for step in proof:
            if not isinstance(step, dict):
                return False
            pos = step.get("position")
            sibling_raw = step.get("hash")
            if not isinstance(sibling_raw, str):
                return False
            sibling = validate_hash_hex(sibling_raw, "sibling_hash")

            if pos == "right":
                current_hash = hash_pair(current_hash, sibling)
            elif pos == "left":
                current_hash = hash_pair(sibling, current_hash)
            else:
                return False

        return current_hash == target_root
    except Exception:
        return False


def generate_proof(record_hashes: list[str], leaf_index: int) -> list[dict[str, str]]:
    """Generate Merkle inclusion proof for a specific leaf index."""
    tree = build_merkle_tree(record_hashes)
    if not (0 <= leaf_index < len(tree["proofs"])):
        raise IndexError(f"Leaf index {leaf_index} out of bounds (0-{len(tree['proofs']) - 1})")
    return tree["proofs"][leaf_index]
