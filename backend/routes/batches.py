"""Routes for submitting, listing, and retrieving batch commitments."""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status

from ..schemas import BatchCommitmentRequest, BatchListResponse, BatchResponse
from ..services.blockchain import default_blockchain_service
from ..services.storage import get_batch, get_latest_batch, list_batches, save_batch

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("", response_model=BatchListResponse)
def get_all_batches(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List batches ordered by batch_id descending."""
    batches, total = list_batches(limit=limit, offset=offset)
    return BatchListResponse(batches=[BatchResponse(**b) for b in batches], total=total)


@router.get("/{batch_id}", response_model=BatchResponse)
def get_single_batch(batch_id: int):
    """Retrieve details for a specific batch by ID."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )
    return BatchResponse(**batch)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def submit_batch(req: BatchCommitmentRequest):
    """Submit and anchor a new batch commitment."""
    latest = get_latest_batch()
    expected_id = 1 if latest is None else latest["batch_id"] + 1

    if req.batch_id != expected_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Non-monotonic batch_id: expected {expected_id}, got {req.batch_id}",
        )

    expected_prev = "0" * 64 if latest is None else latest["merkle_root"]
    if req.previous_root.lower() != expected_prev.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Broken batch chain: expected previous_root {expected_prev}, "
                f"got {req.previous_root}"
            ),
        )

    batch_dict = req.model_dump()
    if batch_dict.get("timestamp") is None:
        batch_dict["timestamp"] = int(datetime.now(timezone.utc).timestamp())

    # Anchor to blockchain (MST or deterministic offline simulation)
    anchor_info = default_blockchain_service.anchor_batch(batch_dict)

    batch_dict.update(anchor_info)
    saved = save_batch(batch_dict)
    return BatchResponse(**saved)
