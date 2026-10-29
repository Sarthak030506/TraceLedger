"""Ed25519 digital signature generation and verification for batch commitments."""
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def generate_keypair() -> tuple[str, str]:
    """Generates a new Ed25519 keypair.

    Returns:
        (private_key_hex, public_key_hex): Pair of 64-character lowercase hex strings (32 bytes each).
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv_bytes.hex(), pub_bytes.hex()


def canonical_batch_bytes(batch_metadata: dict[str, Any]) -> bytes:
    """Deterministically serializes batch metadata for signing.

    Excludes any existing 'signature' key, sorts keys alphabetically at every level,
    uses (',', ':') separators without spaces, and encodes to UTF-8.
    """
    signing_data = {k: v for k, v in batch_metadata.items() if k != "signature"}
    canonical_str = json.dumps(
        signing_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return canonical_str.encode("utf-8")


def _resolve_private_key(private_key: str | bytes | ed25519.Ed25519PrivateKey) -> ed25519.Ed25519PrivateKey:
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        return private_key
    if isinstance(private_key, str):
        key_bytes = bytes.fromhex(private_key.strip())
    elif isinstance(private_key, bytes):
        key_bytes = private_key
    else:
        raise TypeError(f"Unsupported private key type: {type(private_key).__name__}")
    return ed25519.Ed25519PrivateKey.from_private_bytes(key_bytes)


def _resolve_public_key(public_key: str | bytes | ed25519.Ed25519PublicKey) -> ed25519.Ed25519PublicKey:
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return public_key
    if isinstance(public_key, str):
        key_bytes = bytes.fromhex(public_key.strip())
    elif isinstance(public_key, bytes):
        key_bytes = public_key
    else:
        raise TypeError(f"Unsupported public key type: {type(public_key).__name__}")
    return ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)


def sign_batch(batch_metadata: dict[str, Any], private_key: str | bytes | ed25519.Ed25519PrivateKey) -> str:
    """Signs batch metadata using Ed25519.

    Args:
        batch_metadata: Dict containing batch fields (e.g. batch_id, merkle_root, sequence bounds).
        private_key: 32-byte private key as hex string, raw bytes, or Ed25519PrivateKey.

    Returns:
        128-character lowercase hex string signature.
    """
    priv = _resolve_private_key(private_key)
    message_bytes = canonical_batch_bytes(batch_metadata)
    sig_bytes = priv.sign(message_bytes)
    return sig_bytes.hex()


def verify_signature(
    batch_metadata: dict[str, Any],
    signature: str | bytes,
    public_key: str | bytes | ed25519.Ed25519PublicKey,
) -> bool:
    """Verifies an Ed25519 batch signature.

    Args:
        batch_metadata: Dict containing batch fields.
        signature: 64-byte signature as 128-char hex string or raw bytes.
        public_key: 32-byte public key as hex string, raw bytes, or Ed25519PublicKey.

    Returns:
        bool: True if signature is cryptographically valid, False otherwise.
    """
    try:
        pub = _resolve_public_key(public_key)
        if isinstance(signature, str):
            sig_bytes = bytes.fromhex(signature.strip())
        elif isinstance(signature, bytes):
            sig_bytes = signature
        else:
            return False

        message_bytes = canonical_batch_bytes(batch_metadata)
        pub.verify(sig_bytes, message_bytes)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
