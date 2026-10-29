"""Routes for verifying records against anchored batch commitments."""
import json
import os
from fastapi import APIRouter, HTTPException, status

from integrity.merkle import build_merkle_tree
from integrity.verifier import verify_batch
from sidecar.storage import RecordStore
from ..schemas import BatchVerifyRequest, BatchVerifyResponse
from ..services.storage import get_batch, log_verification

router = APIRouter(prefix="/api/batches", tags=["verification"])


@router.post("/{batch_id}/verify", response_model=BatchVerifyResponse)
def verify_batch_records(batch_id: int, req: BatchVerifyRequest):
    """Verify stored or provided records against the anchored Merkle root of a batch."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )

    records = req.records

    # ── Strategy 1: caller supplied full records ──────────────────────────────
    if records is not None:
        res = verify_batch(records, batch["merkle_root"])

    # ── Strategy 2: load from sidecar DB ─────────────────────────────────────
    else:
        sidecar_records: list | None = None
        db_path = os.environ.get("SIDECAR_DB_PATH", "data/records.db")
        if os.path.exists(db_path):
            store = RecordStore(db_path)
            try:
                sidecar_records = store.get_records(
                    start=batch["first_sequence"],
                    end=batch["last_sequence"],
                )
            finally:
                store.close()

        if sidecar_records:
            res = verify_batch(sidecar_records, batch["merkle_root"])

        # ── Strategy 3: use stored leaf hashes (submitted via API) ────────────
        else:
            stored_hashes_json = batch.get("record_hashes_json")
            if stored_hashes_json:
                try:
                    leaf_hashes: list[str] = json.loads(stored_hashes_json)
                    expected_root = batch["merkle_root"]
                    tree = build_merkle_tree(leaf_hashes)
                    computed_root = tree["merkle_root"]
                    verified = computed_root == expected_root
                    errors = (
                        []
                        if verified
                        else [f"Merkle root mismatch: expected {expected_root}, computed {computed_root}"]
                    )
                    res = {
                        "verified": verified,
                        "expected_root": expected_root,
                        "computed_root": computed_root,
                        "record_count": len(leaf_hashes),
                        "errors": errors,
                        "message": (
                            "Batch integrity verified successfully (from stored leaf hashes)"
                            if verified
                            else f"Integrity verification failed with {len(errors)} error(s)"
                        ),
                    }
                except Exception as exc:
                    res = {
                        "verified": False,
                        "expected_root": batch["merkle_root"],
                        "computed_root": "",
                        "record_count": 0,
                        "errors": [f"Failed to recompute root from stored hashes: {exc}"],
                        "message": "Verification error",
                    }
            else:
                # No records available at all
                res = verify_batch([], batch["merkle_root"])

    log_verification(
        batch_id=batch_id,
        verified=res["verified"],
        expected_root=res["expected_root"],
        computed_root=res["computed_root"],
        errors=res["errors"],
    )

    return BatchVerifyResponse(
        batch_id=batch_id,
        verified=res["verified"],
        expected_root=res["expected_root"],
        computed_root=res["computed_root"],
        record_count=res["record_count"],
        errors=res["errors"],
        message=res["message"],
        transaction_hash=batch.get("transaction_hash"),
    )
