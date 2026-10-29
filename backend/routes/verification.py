"""Routes for verifying records against anchored batch commitments."""
import os
from fastapi import APIRouter, HTTPException, status

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
    if records is None:
        # Load from sidecar database
        db_path = os.environ.get("SIDECAR_DB_PATH", "data/records.db")
        if os.path.exists(db_path):
            store = RecordStore(db_path)
            try:
                records = store.get_records(
                    start=batch["first_sequence"],
                    end=batch["last_sequence"],
                )
            finally:
                store.close()
        else:
            records = []

    res = verify_batch(records, batch["merkle_root"])

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
