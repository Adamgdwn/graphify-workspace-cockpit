"""
Connection management and schema initialization for the CNS SQLite store.

Path is read from the CNS_STORE_PATH environment variable. No default path
assumptions — callers must supply a path explicitly or set the env var.
"""
import os
import sqlite3
from cns_store.schema import ALL_TABLES_DDL, INDEXES_DDL


def get_store_path() -> str:
    """Return CNS_STORE_PATH from environment, raising if not set."""
    path = os.environ.get("CNS_STORE_PATH")
    if not path:
        raise RuntimeError(
            "CNS_STORE_PATH environment variable is not set. "
            "Set it to the path of the CNS SQLite database file."
        )
    return path


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Open a SQLite connection with recommended settings for the CNS store.

    Callers are responsible for closing the connection.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(db_path: str) -> None:
    """
    Initialize the CNS store schema at db_path.

    Creates all tables and indexes if they do not already exist.
    Safe to call multiple times (idempotent).
    """
    conn = get_connection(db_path)
    try:
        with conn:
            for ddl in ALL_TABLES_DDL:
                conn.execute(ddl)
            for idx in INDEXES_DDL:
                conn.execute(idx)
    finally:
        conn.close()
