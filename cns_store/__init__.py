"""CNS store — SQLite-backed entity/relationship graph for Graphify Phase 2."""
from cns_store.db import init_db, get_connection

__all__ = ["init_db", "get_connection"]
