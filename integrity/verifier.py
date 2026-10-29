"""Batch integrity verification and tampering detection (Person 2).

Recomputes record hashes using the canonical JSON form from sidecar.hasher,
rebuilds the Merkle root, and compares against the expected commitment.
Detects altered, missing, reordered, or duplicated records.
"""
from typing import Any

from sidecar.hasher import hash_record
from .merkle import build_merkle_tree, validate_hash_hex
from .models import VerificationResult


def verify_batch(records: list[dict[str, Any]], expected_root: str) -> dict[str, Any]:
    """Recomputes hashes and Merkle root from retained records and verifies against expected root.

    Args:
        records: Ordered list of full record dictionaries (e.g. from RecordStore.get_records).
        expected_root: 64-character lowercase hex string anchored on-chain.

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
    errors: list[str] = []

    try:
        norm_expected_root = validate_hash_hex(expected_root, "expected_root")
    except (TypeError, ValueError) as exc:
        return VerificationResult(
            verified=False,
            expected_root=str(expected_root),
            computed_root="",
            record_count=len(records) if isinstance(records, list) else 0,
            errors=[f"Invalid expected_root: {exc}"],
            message=f"Invalid expected root: {exc}",
        ).to_dict()

    if not isinstance(records, list):
        return VerificationResult(
            verified=False,
            expected_root=norm_expected_root,
            computed_root="",
            record_count=0,
            errors=["Records payload must be a list"],
            message="Records payload must be a list",
        ).to_dict()

    if len(records) == 0:
        empty_root = "0" * 64
        is_empty_match = norm_expected_root == empty_root
        if not is_empty_match:
            errors.append(f"Empty records list but expected non-empty root: {norm_expected_root}")
        return VerificationResult(
            verified=is_empty_match,
            expected_root=norm_expected_root,
            computed_root=empty_root,
            record_count=0,
            errors=errors,
            message="Batch is empty" if is_empty_match else "Empty records list does not match expected root",
        ).to_dict()

    leaf_hashes: list[str] = []
    prev_seq: int | None = None

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"Record at index {idx} is not a dictionary: {rec!r}")
            continue

        seq = rec.get("sequence_number")
        if seq is None or not isinstance(seq, int) or isinstance(seq, bool):
            errors.append(f"Record at index {idx} has invalid sequence_number: {seq!r}")
        else:
            if prev_seq is not None:
                if seq == prev_seq:
                    errors.append(f"Duplicate sequence number detected: {seq}")
                elif seq < prev_seq:
                    errors.append(f"Records reordered: sequence {seq} appeared after sequence {prev_seq}")
                elif seq > prev_seq + 1:
                    errors.append(f"Missing sequence number(s) between {prev_seq} and {seq}")
            prev_seq = seq

        # Recompute record hash from the canonical content
        try:
            recomputed = hash_record(rec)
            leaf_hashes.append(recomputed)

            # Check against recorded record_hash if supplied in dictionary
            stored_hash = rec.get("record_hash")
            if stored_hash is not None:
                if not isinstance(stored_hash, str) or stored_hash.lower() != recomputed:
                    errors.append(
                        f"Record sequence {seq} (event {rec.get('event_id')}) tampered: "
                        f"stored hash {stored_hash!r} != recomputed hash {recomputed}"
                    )
        except Exception as exc:
            errors.append(f"Error hashing record at index {idx} (seq={seq}): {exc}")

    if len(leaf_hashes) != len(records):
        computed_root = ""
        errors.append("Could not compute Merkle root due to un-hashable records")
    else:
        tree = build_merkle_tree(leaf_hashes)
        computed_root = tree["merkle_root"]
        if computed_root != norm_expected_root:
            errors.append(
                f"Merkle root mismatch: expected {norm_expected_root}, computed {computed_root}"
            )

    verified = (len(errors) == 0) and (computed_root == norm_expected_root)
    message = (
        "Batch integrity verified successfully"
        if verified
        else f"Integrity verification failed with {len(errors)} error(s)"
    )

    return VerificationResult(
        verified=verified,
        expected_root=norm_expected_root,
        computed_root=computed_root,
        record_count=len(records),
        errors=errors,
        message=message,
    ).to_dict()
