"""Abstract base for cloud knowledge connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ConnectorBase(ABC):
    connector_id: str
    display_name: str

    @abstractmethod
    def is_authenticated(self) -> bool: ...

    @abstractmethod
    def list_items(self) -> list[dict]: ...

    @abstractmethod
    def fetch_content(self, item_id: str) -> str: ...

    def to_graph_nodes(self, items: list[dict]) -> list[dict]:
        return []
