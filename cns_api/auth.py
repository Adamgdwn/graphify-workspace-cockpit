"""Shared API key guard for CNS API routes."""
from typing import Optional
from fastapi import HTTPException
from cns_api.config import get_api_key


def require_api_key(x_api_key: Optional[str]) -> None:
    """Enforce API key auth when CNS_API_KEY is configured. No-op if key not set."""
    configured_key = get_api_key()
    if not configured_key:
        return
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Api-Key header")
