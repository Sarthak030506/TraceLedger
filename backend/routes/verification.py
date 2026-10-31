"""Routes for verifying records against anchored batch commitments."""
import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status

from integrity.merkle import build_merkle_tree
from integrity.signer import commitment_signing_payload, verify_signature
from integrity.verifier import verify_batch
from sidecar.storage import RecordStore
from ..schemas import BatchVerifyRequest, BatchVerifyResponse
from ..security import signer_public_key
from ..services.blockchain import AnchorError, default_blockchain_service
from ..services.storage import get_batch, log_verification

router = APIRouter(prefix="/batches", tags=["verification"])

# Fields that must agree between the off-chain metadata row and the on-chain commitment.
_ONCHAIN_FIELDS = ("merkle_root", "previous_root", "first_sequence", "last_sequence", "record_count")


def _resolve_anchor(batch: dict[str, Any]) -> tuple[dict[str, Any], bool, list[str], list[str]]:
    """Return (commitment, onchain_checked, errors, notes).

    The commitment to verify against is the on-chain one whenever the chain can be read,
    so a tampered off-chain metadata row cannot redefine what "correct" means.
    """
    if batch.get("status") == "simulated" or default_blockchain_service.mode == "simulated":
        return batch, False, [], ["simulated anchor: on-chain commitment not checked"]
    try:
        onchain = default_blockchain_service.get_onchain_batch(batch["batch_id"])
    except AnchorError as exc:
        return batch, False, [], [f"on-chain commitment not checked: {exc}"]
    if onchain is None:
        return batch, True, [f"Batch {batch['batch_id']} is not committed on-chain"], []

    errors = [
        f"Off-chain metadata disagrees with chain on {field}: "
        f"stored {batch[field]!r}, on-chain {onchain[field]!r}"
        for field in _ONCHAIN_FIELDS
        if str(batch[field]).lower() != str(onchain[field]).lower()
    ]
    return onchain, True, errors, []


def _verify_leaf_hashes(stored_hashes_json: str, commitment: dict[str, Any]) -> dict[str, Any]:
    """Weakest strategy: only proves the stored leaf hashes rebuild the anchored root."""
    expected_root = commitment["merkle_root"]
    try:
        leaf_hashes: list[str] = json.loads(stored_hashes_json)
        computed_root = build_merkle_tree(leaf_hashes)["merkle_root"]
    except Exception as exc:
        return {
            "verified": False,
            "expected_root": expected_root,
            "computed_root": "",
            "record_count": 0,
            "errors": [f"Failed to recompute root from stored hashes: {exc}"],
            "message": "Verification error",
        }
    errors = []
    if len(leaf_hashes) != commitment["record_count"]:
        errors.append(
            f"Record count mismatch: commitment covers {commitment['record_count']}, "
            f"stored leaf hashes {len(leaf_hashes)}"
        )
    if computed_root != expected_root:
        errors.append(f"Merkle root mismatch: expected {expected_root}, computed {computed_root}")
    verified = not errors
    return {
        "verified": verified,
        "expected_root": expected_root,
        "computed_root": computed_root,
        "record_count": len(leaf_hashes),
        "errors": errors,
        "message": (
            "Leaf hashes match the anchored root (raw log records were not available to re-hash)"
            if verified
            else f"Integrity verification failed with {len(errors)} error(s)"
        ),
    }


def _check_signature(batch: dict[str, Any]) -> tuple[bool | None, list[str]]:
    pub = signer_public_key()
    if pub is None:
        return None, []
    if not batch.get("signature"):
        return False, ["Batch has no signature but BATCH_SIGNER_PUBLIC_KEY is configured"]
    if not verify_signature(commitment_signing_payload(batch), batch["signature"], pub):
        return False, ["Batch signature is invalid for the configured signer key"]
    return True, []


@router.post("/{batch_id}/verify", response_model=BatchVerifyResponse)
def verify_batch_records(batch_id: int, req: BatchVerifyRequest):
    """Verify stored or provided records against the anchored Merkle root of a batch."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )

    commitment, onchain_checked, anchor_errors, notes = _resolve_anchor(batch)
    first_seq, last_seq = commitment["first_sequence"], commitment["last_sequence"]

    records = req.records
    source = "none"

    # ── Strategy 1: caller supplied full records ──────────────────────────────
    if records is not None:
        source = "provided_records"
        res = verify_batch(records, commitment["merkle_root"], first_seq, last_seq)

    # ── Strategy 2: load from sidecar DB ─────────────────────────────────────
    else:
        sidecar_records: list | None = None
        db_path = os.environ.get("SIDECAR_DB_PATH", "data/records.db")
        if os.path.exists(db_path):
            store = RecordStore(db_path)
            try:
                sidecar_records = store.get_records(start=first_seq, end=last_seq)
            finally:
                store.close()

        if sidecar_records:
            source = "sidecar_store"
            res = verify_batch(sidecar_records, commitment["merkle_root"], first_seq, last_seq)

        # ── Strategy 3: stored leaf hashes only (weaker; raw logs not checked) ─
        elif batch.get("record_hashes_json"):
            source = "leaf_hashes"
            res = _verify_leaf_hashes(batch["record_hashes_json"], commitment)

        else:
            res = verify_batch([], commitment["merkle_root"], first_seq, last_seq)
            res["message"] = "No records available to verify against the anchored root"

    signature_valid, signature_errors = _check_signature(batch)
    errors = anchor_errors + signature_errors + res["errors"]
    verified = res["verified"] and not errors
    message = res["message"] if verified or not (anchor_errors or signature_errors) else (
        f"Integrity verification failed with {len(errors)} error(s)"
    )
    if notes:
        message += " (" + "; ".join(notes) + ")"

    log_verification(
        batch_id=batch_id,
        verified=verified,
        expected_root=res["expected_root"],
        computed_root=res["computed_root"],
        errors=errors,
    )

    return BatchVerifyResponse(
        batch_id=batch_id,
        verified=verified,
        expected_root=res["expected_root"],
        computed_root=res["computed_root"],
        record_count=res["record_count"],
        errors=errors,
        message=message,
        transaction_hash=batch.get("transaction_hash"),
        verification_source=source,
        onchain_checked=onchain_checked,
        signature_valid=signature_valid,
    )
