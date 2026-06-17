"""OneNote connector — reads notebooks, sections, and pages via Microsoft Graph API.

Access is read-only (Notes.Read.All scope).
No write, delete, share, or admin operations.
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import ConnectorBase, connector_node
from .microsoft_auth import get_token, is_authenticated

GRAPH = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 20


def _get(url: str, token: str) -> dict | None:
    try:
        import requests  # type: ignore
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


class OneNoteConnector(ConnectorBase):
    connector_id = "onenote"
    display_name = "OneNote"

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir

    def is_authenticated(self) -> bool:
        return is_authenticated(self.state_dir)

    def list_items(self) -> list[dict]:
        token = get_token(self.state_dir)
        if not token:
            raise RuntimeError("Not authenticated with Microsoft")
        items: list[dict] = []
        notebooks = (_get(f"{GRAPH}/me/onenote/notebooks", token) or {}).get("value", [])
        for nb in notebooks:
            nb_id = nb["id"]
            nb_name = nb.get("displayName", nb_id)
            sections = (
                _get(f"{GRAPH}/me/onenote/notebooks/{nb_id}/sections", token) or {}
            ).get("value", [])
            for sec in sections:
                sec_id = sec["id"]
                sec_name = sec.get("displayName", sec_id)
                pages = (
                    _get(f"{GRAPH}/me/onenote/sections/{sec_id}/pages?$top=100", token) or {}
                ).get("value", [])
                for pg in pages:
                    items.append({
                        "id": pg["id"],
                        "title": pg.get("title") or "(untitled)",
                        "notebook": nb_name,
                        "section": sec_name,
                        "created_at": pg.get("createdDateTime", ""),
                        "modified_at": pg.get("lastModifiedDateTime", ""),
                        "web_url": pg.get("links", {}).get("oneNoteWebUrl", {}).get("href", ""),
                    })
        return items

    def fetch_content(self, item_id: str) -> str:
        token = get_token(self.state_dir)
        if not token:
            return ""
        try:
            import requests  # type: ignore
            r = requests.get(
                f"{GRAPH}/me/onenote/pages/{item_id}/content",
                headers={"Authorization": f"Bearer {token}"},
                timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                return ""
            text = re.sub(r"<[^>]+>", " ", r.text)
            return re.sub(r"\s+", " ", text).strip()[:10000]
        except Exception:
            return ""

    def to_graph_nodes(self, items: list[dict]) -> list[dict]:
        return [
            connector_node(
                connector_id=self.connector_id,
                item_id=item["id"],
                label=item["title"],
                node_type="note",
                file_type="document",
                source_path_parts=(
                    item.get("notebook", ""),
                    item.get("section", ""),
                    item.get("title", item["id"]),
                ),
                metadata={
                    "page_id": item["id"],
                    "web_url": item.get("web_url", ""),
                    "notebook": item.get("notebook", ""),
                    "section": item.get("section", ""),
                    "created_at": item.get("created_at", ""),
                    "modified_at": item.get("modified_at", ""),
                },
                extra={
                    "notebook": item.get("notebook", ""),
                    "section": item.get("section", ""),
                    "source_location": item.get("web_url", ""),
                    "modified_at": item.get("modified_at", ""),
                },
            )
            for item in items
        ]
