"""Routes for submitting, listing, and retrieving batch commitments."""
from datetime import datetime, timezone
import threading

from fastapi import APIRouter, Depends, HTTPException, Query, status

from integrity.merkle import build_merkle_tree
from integrity.signer import commitment_signing_payload, verify_signature
from ..schemas import BatchCommitmentRequest, BatchListResponse, BatchResponse
from ..security import require_write_key, signer_public_key
from ..services.blockchain import AnchorError, default_blockchain_service
from ..services.storage import get_batch, get_latest_batch, list_batches, save_batch

router = APIRouter(prefix="/batches", tags=["batches"])

# Serializes the read-latest -> anchor -> insert sequence so two concurrent submissions
# cannot both pass the chain checks and both send an on-chain transaction.
# Per-process only: run a single worker (the default for all deploy configs here).
_submit_lock = threading.Lock()


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


def _check_record_hashes(req: BatchCommitmentRequest) -> None:
    """Supplied leaf hashes must match the declared count and rebuild the declared root."""
    if req.record_hashes is None:
        return
    if len(req.record_hashes) != req.record_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"record_hashes has {len(req.record_hashes)} entries but record_count is {req.record_count}",
        )
    computed = build_merkle_tree(req.record_hashes)["merkle_root"]
    if computed != req.merkle_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"record_hashes do not rebuild merkle_root: computed {computed}",
        )


def _check_signature(batch_dict: dict, timestamp_supplied: bool) -> None:
    """Enforce Ed25519 signatures when BATCH_SIGNER_PUBLIC_KEY is configured."""
    pub = signer_public_key()
    if pub is None:
        return
    if not batch_dict.get("signature"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="signature is required (BATCH_SIGNER_PUBLIC_KEY is configured)",
        )
    if not timestamp_supplied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="timestamp is required for signed batches (it is part of the signed payload)",
        )
    if not verify_signature(commitment_signing_payload(batch_dict), batch_dict["signature"], pub):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid batch signature",
        )


@router.post(
    "",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_key)],
)
def submit_batch(req: BatchCommitmentRequest):
    """Submit and anchor a new batch commitment."""
    _check_record_hashes(req)

    batch_dict = req.model_dump()
    timestamp_supplied = batch_dict.get("timestamp") is not None
    if not timestamp_supplied:
        batch_dict["timestamp"] = int(datetime.now(timezone.utc).timestamp())
    _check_signature(batch_dict, timestamp_supplied)

    with _submit_lock:
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

        if latest is not None and req.first_sequence != latest["last_sequence"] + 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Sequence gap: expected first_sequence {latest['last_sequence'] + 1}, "
                    f"got {req.first_sequence}"
                ),
            )

        # Anchor to blockchain (live MST, or explicit simulation when unconfigured)
        try:
            anchor_info = default_blockchain_service.anchor_batch(batch_dict)
        except AnchorError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        batch_dict.update(anchor_info)
        saved = save_batch(batch_dict)
    return BatchResponse(**saved)
