from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend import main


REPO_ROOT = Path(__file__).parent.parent


class _FakeSupabaseQuery:
    def __init__(self, available_columns: dict[str, set[str]], table_name: str):
        self.available_columns = available_columns
        self.table_name = table_name
        self.selected_columns: list[str] = []

    def select(self, columns: str):
        self.selected_columns = [column.strip() for column in columns.split(",")]
        return self

    def limit(self, _count: int):
        return self

    def execute(self):
        available = self.available_columns.get(self.table_name, set())
        missing = [column for column in self.selected_columns if column not in available]
        if missing:
            raise RuntimeError(f"missing columns: {', '.join(missing)}")
        return SimpleNamespace(data=[])


class _FakeSupabaseClient:
    def __init__(self, available_columns: dict[str, set[str]]):
        self.available_columns = available_columns

    def table(self, table_name: str):
        return _FakeSupabaseQuery(self.available_columns, table_name)


def test_supabase_migration_adds_current_recommendation_and_action_columns() -> None:
    migration = (REPO_ROOT / "db/migrations/002_recommendation_action_plans.sql").read_text()

    assert "ADD COLUMN IF NOT EXISTS action_plan JSONB" in migration
    assert "ADD COLUMN IF NOT EXISTS overlap JSONB" in migration
    assert "ADD COLUMN IF NOT EXISTS overlap_dossier JSONB" in migration
    assert "ADD COLUMN IF NOT EXISTS context JSONB" in migration
    assert "ALTER TABLE actions" in migration


def test_storage_status_reports_ready_when_supabase_columns_exist(monkeypatch) -> None:
    monkeypatch.setattr(main, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(
        main,
        "_supabase_client",
        _FakeSupabaseClient(
            {
                "recommendations": {"action_plan", "overlap", "overlap_dossier", "context"},
                "actions": {"action_plan"},
            }
        ),
    )
    monkeypatch.setattr(main, "_supabase_schema_status_cache", None)

    status = main._storage_status(force_check=True)

    assert status["ready"] is True
    assert status["schema_checked"] is True
    assert status["missing_or_unverified_columns"] == {}
    assert status["warning"] is None


def test_storage_status_warns_when_supabase_columns_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(main, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(
        main,
        "_supabase_client",
        _FakeSupabaseClient(
            {
                "recommendations": {"id", "title"},
                "actions": {"id"},
            }
        ),
    )
    monkeypatch.setattr(main, "_supabase_schema_status_cache", None)

    status = main._storage_status(force_check=True)

    assert status["ready"] is False
    assert status["schema_checked"] is True
    assert status["required_migration"] == main.SUPABASE_SCHEMA_MIGRATION
    assert status["missing_or_unverified_columns"] == {
        "recommendations": ["action_plan", "overlap", "overlap_dossier", "context"],
        "actions": ["action_plan"],
    }
    assert "hosted beta" in status["warning"]
