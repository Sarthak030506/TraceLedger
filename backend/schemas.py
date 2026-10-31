"""Pydantic schemas for TraceLedger backend API requests and responses."""
from typing import Any
from pydantic import BaseModel, Field, field_validator


class BatchCommitmentRequest(BaseModel):
    batch_id: int = Field(gt=0, description="Monotonic batch identifier (starts at 1)")
    merkle_root: str = Field(description="64-character lowercase SHA-256 Merkle root (no 0x)")
    previous_root: str = Field(
        default="0" * 64,
        description="64-character lowercase Merkle root of the immediately preceding batch",
    )
    first_sequence: int = Field(gt=0, description="Sequence number of the first event")
    last_sequence: int = Field(gt=0, description="Sequence number of the last event")
    record_count: int = Field(gt=0, description="Total number of records in batch")
    timestamp: int | None = Field(default=None, description="Unix timestamp of commitment creation")
    signature: str | None = Field(default=None, description="Ed25519 signature of batch metadata")
    record_hashes: list[str] | None = Field(
        default=None,
        description="Optional ordered list of 64-char leaf hashes used to build the Merkle root.",
    )

    @field_validator("merkle_root", "previous_root")
    @classmethod
    def validate_hex_roots(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned.startswith("0x"):
            cleaned = cleaned[2:]
        if len(cleaned) != 64 or not all(c in "0123456789abcdef" for c in cleaned):
            raise ValueError("Root must be a 64-character hex string (SHA-256)")
        return cleaned

    @field_validator("signature")
    @classmethod
    def validate_signature_hex(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        cleaned = v.strip().lower().removeprefix("0x")
        if len(cleaned) != 128 or not all(c in "0123456789abcdef" for c in cleaned):
            raise ValueError("signature must be a 128-character hex Ed25519 signature")
        return cleaned

    @field_validator("record_hashes")
    @classmethod
    def validate_record_hashes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [h.strip().lower() for h in v]
        for i, h in enumerate(cleaned):
            if len(h) != 64 or not all(c in "0123456789abcdef" for c in h):
                raise ValueError(f"record_hashes[{i}] must be a 64-character hex string (no 0x)")
        return cleaned

    @field_validator("record_count")
    @classmethod
    def validate_count_range(cls, v: int, info) -> int:
        first = info.data.get("first_sequence")
        last = info.data.get("last_sequence")
        if first is not None and last is not None:
            expected = last - first + 1
            if v != expected:
                raise ValueError(
                    f"record_count ({v}) must match last_sequence - first_sequence + 1 ({expected})"
                )
        return v


class BatchResponse(BaseModel):
    batch_id: int
    merkle_root: str
    previous_root: str
    first_sequence: int
    last_sequence: int
    record_count: int
    timestamp: int
    signature: str | None = None
    transaction_hash: str | None = None
    block_number: int | None = None
    status: str
    created_at: str
    record_hashes_json: str | None = None


class BatchListResponse(BaseModel):
    batches: list[BatchResponse]
    total: int


class BatchVerifyRequest(BaseModel):
    records: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional list of full records. If omitted, fetched from sidecar store.",
    )


class BatchVerifyResponse(BaseModel):
    batch_id: int
    verified: bool
    expected_root: str
    computed_root: str
    record_count: int
    errors: list[str]
    message: str
    transaction_hash: str | None = None
    verification_source: str = Field(
        description=(
            "What was re-hashed: 'provided_records' or 'sidecar_store' (raw records, strongest), "
            "'leaf_hashes' (stored leaf hashes only; raw logs NOT checked), or 'none'."
        )
    )
    onchain_checked: bool = Field(
        description="True if the commitment was compared against the live contract."
    )
    signature_valid: bool | None = Field(
        default=None,
        description="Ed25519 check result; None when no signer public key is configured.",
    )


class HealthResponse(BaseModel):
    status: str
    anchor_mode: str
    blockchain_connected: bool
    contract_address: str | None = None
    chain_id: int | None = None
    latest_batch_id: int
    total_batches: int
