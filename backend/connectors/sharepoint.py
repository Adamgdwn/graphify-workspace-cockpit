"""SharePoint connector — reads file listings via Microsoft Graph API.

Access is read-only (Files.Read.All scope).
No write, delete, share, or admin operations.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from .base import ConnectorBase
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


class SharePointConnector(ConnectorBase):
    connector_id = "sharepoint"
    display_name = "SharePoint"

    def __init__(self, state_dir: Path, site_urls: list[str]) -> None:
        self.state_dir = state_dir
        self.site_urls = site_urls

    def is_authenticated(self) -> bool:
        return is_authenticated(self.state_dir)

    def _site_id(self, site_url: str, token: str) -> str | None:
        parsed = urlparse(site_url)
        host = parsed.netloc
        path = parsed.path.strip("/")
        data = _get(f"{GRAPH}/sites/{host}:/{path}", token)
        return data["id"] if data else None

    def list_items(self) -> list[dict]:
        token = get_token(self.state_dir)
        if not token:
            raise RuntimeError("Not authenticated with Microsoft")
        items: list[dict] = []
        for site_url in self.site_urls:
            site_id = self._site_id(site_url, token)
            if not site_id:
                continue
            drives_data = _get(f"{GRAPH}/sites/{site_id}/drives", token)
            for drive in (drives_data or {}).get("value", []):
                drive_id = drive["id"]
                files_data = _get(
                    f"{GRAPH}/drives/{drive_id}/root/children?$top=200", token
                )
                for f in (files_data or {}).get("value", []):
                    if not f.get("file"):
                        continue  # skip folders
                    items.append({
                        "id": f["id"],
                        "name": f["name"],
                        "site_url": site_url,
                        "drive_id": drive_id,
                        "web_url": f.get("webUrl", ""),
                        "modified_at": f.get("lastModifiedDateTime", ""),
                        "size": f.get("size", 0),
                        "mime_type": f.get("file", {}).get("mimeType", ""),
                    })
        return items

    def fetch_content(self, item_id: str, drive_id: str = "") -> str:  # type: ignore[override]
        token = get_token(self.state_dir)
        if not token or not drive_id:
            return ""
        try:
            import requests  # type: ignore
            r = requests.get(
                f"{GRAPH}/drives/{drive_id}/items/{item_id}/content",
                headers={"Authorization": f"Bearer {token}"},
                timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                return ""
            return r.content.decode("utf-8", errors="ignore")[:10000]
        except Exception:
            return ""

    def to_graph_nodes(self, items: list[dict]) -> list[dict]:
        return [
            {
                "id": f"sharepoint:{item['id']}",
                "label": item["name"],
                "type": "document",
                "source": "sharepoint",
                "site_url": item["site_url"],
                "file_path": item.get("web_url", ""),
                "modified_at": item.get("modified_at", ""),
                "metadata": {
                    "drive_id": item.get("drive_id", ""),
                    "item_id": item["id"],
                    "mime_type": item.get("mime_type", ""),
                    "size": item.get("size", 0),
                },
            }
            for item in items
        ]
