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

    @field_validator("merkle_root", "previous_root")
    @classmethod
    def validate_hex_roots(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned.startswith("0x"):
            cleaned = cleaned[2:]
        if len(cleaned) != 64 or not all(c in "0123456789abcdef" for c in cleaned):
            raise ValueError("Root must be a 64-character hex string (SHA-256)")
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


class HealthResponse(BaseModel):
    status: str
    blockchain_connected: bool
    contract_address: str | None = None
    chain_id: int | None = None
    latest_batch_id: int
    total_batches: int
