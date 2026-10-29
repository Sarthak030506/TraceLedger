"""Data models and schemas for the cryptographic integrity layer (Person 2)."""
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class MerkleProofStep:
    """A single step in a Merkle inclusion proof."""
    position: Literal["left", "right"]
    hash: str

    def to_dict(self) -> dict[str, str]:
        return {"position": self.position, "hash": self.hash}


@dataclass
class MerkleTreeResult:
    """Output of Merkle tree construction."""
    merkle_root: str
    leaves: list[str]
    proofs: list[list[dict[str, str]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "merkle_root": self.merkle_root,
            "leaves": self.leaves,
            "proofs": self.proofs,
        }


@dataclass
class VerificationResult:
    """Result of batch integrity verification."""
    verified: bool
    expected_root: str
    computed_root: str
    record_count: int
    errors: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "expected_root": self.expected_root,
            "computed_root": self.computed_root,
            "record_count": self.record_count,
            "errors": self.errors,
            "message": self.message,
        }


@dataclass
class BatchCommitment:
    """Commitment payload for blockchain anchoring."""
    batch_id: int
    merkle_root: str
    previous_root: str
    first_sequence: int
    last_sequence: int
    record_count: int
    timestamp: int
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
