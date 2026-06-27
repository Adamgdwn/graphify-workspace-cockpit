"""
CNS API configuration — all values from environment variables.

No default paths assume a local filesystem layout. Callers must supply
CNS_STORE_PATH. All other settings have safe, cloud-compatible defaults.
"""
import os


def get_store_path() -> str:
    """Path to the CNS SQLite store. Must be set — no default."""
    path = os.environ.get("CNS_STORE_PATH", "")
    if not path:
        raise RuntimeError(
            "CNS_STORE_PATH is required. Set it to the CNS SQLite database path."
        )
    return path


def get_api_port() -> int:
    return int(os.environ.get("CNS_API_PORT", "8001"))


def get_api_key() -> str:
    """Optional API key. Empty string means auth is disabled."""
    return os.environ.get("CNS_API_KEY", "")


def get_api_host() -> str:
    return os.environ.get("CNS_API_HOST", "0.0.0.0")
