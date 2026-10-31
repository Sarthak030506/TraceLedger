"""Request authentication and signer configuration for the backend API."""
import hmac
import os

from fastapi import Header, HTTPException, status

from .services.blockchain import default_blockchain_service


def require_write_key(x_api_key: str | None = Header(default=None)) -> None:
    """Guard state-changing endpoints with the BACKEND_API_KEY shared secret.

    If BACKEND_API_KEY is unset, writes are only allowed in simulated mode (local
    development). With live anchoring configured, an unset key refuses all writes so a
    public deployment can never spend the anchoring wallet's gas for anonymous callers.
    """
    expected = os.environ.get("BACKEND_API_KEY", "").strip()
    if not expected:
        if default_blockchain_service.mode != "simulated":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Batch submission disabled: BACKEND_API_KEY must be set when live anchoring is enabled",
            )
        return
    if not x_api_key or not hmac.compare_digest(x_api_key.strip(), expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header",
        )


def signer_public_key() -> str | None:
    """Hex Ed25519 public key that batch signatures must verify against, if configured."""
    key = os.environ.get("BATCH_SIGNER_PUBLIC_KEY", "").strip()
    return key or None
