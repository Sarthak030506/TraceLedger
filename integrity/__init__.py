"""Integrity package: Merkle trees, inclusion proofs, Ed25519 signatures, and batch verifier."""
from .merkle import build_merkle_tree, hash_pair
from .models import BatchCommitment, MerkleProofStep, MerkleTreeResult, VerificationResult
from .proofs import generate_proof, verify_inclusion
from .signer import generate_keypair, sign_batch, verify_signature
from .verifier import verify_batch

__all__ = [
    "build_merkle_tree",
    "hash_pair",
    "generate_proof",
    "verify_inclusion",
    "generate_keypair",
    "sign_batch",
    "verify_signature",
    "verify_batch",
    "MerkleProofStep",
    "MerkleTreeResult",
    "VerificationResult",
    "BatchCommitment",
]
