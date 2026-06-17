"""Storage readiness checks."""

from __future__ import annotations

from collections.abc import Callable


def safe_error_message(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {str(exc)[:240]}"


class StorageStatusProvider:
    def __init__(
        self,
        *,
        backend_getter: Callable[[], str],
        client_getter: Callable[[], object | None],
        required_migration: str,
        required_columns: dict[str, tuple[str, ...]],
    ) -> None:
        self._backend_getter = backend_getter
        self._client_getter = client_getter
        self._required_migration = required_migration
        self._required_columns = required_columns
        self._cache: dict | None = None

    def check_schema(self) -> dict:
        backend = self._backend_getter()
        if backend != "supabase":
            return {
                "backend": backend,
                "ready": True,
                "schema_checked": False,
                "required_migration": None,
                "required_columns": {},
                "missing_or_unverified_columns": {},
                "warning": None,
                "errors": [],
            }

        client = self._client_getter()
        if client is None:
            return {
                "backend": backend,
                "ready": False,
                "schema_checked": False,
                "required_migration": self._required_migration,
                "required_columns": {
                    table: list(columns)
                    for table, columns in self._required_columns.items()
                },
                "missing_or_unverified_columns": {
                    table: list(columns)
                    for table, columns in self._required_columns.items()
                },
                "warning": (
                    "Supabase schema could not be checked because the client is not initialized. "
                    f"Apply {self._required_migration} before using Supabase mode for hosted beta."
                ),
                "errors": ["Supabase client is not initialized."],
            }

        missing_or_unverified: dict[str, list[str]] = {}
        errors: list[str] = []
        for table, columns in self._required_columns.items():
            try:
                (
                    client
                    .table(table)
                    .select(",".join(columns))
                    .limit(0)
                    .execute()
                )
            except Exception as exc:
                missing_or_unverified[table] = list(columns)
                errors.append(f"{table}: {safe_error_message(exc)}")

        ready = not missing_or_unverified
        return {
            "backend": backend,
            "ready": ready,
            "schema_checked": True,
            "required_migration": self._required_migration,
            "required_columns": {
                table: list(columns)
                for table, columns in self._required_columns.items()
            },
            "missing_or_unverified_columns": missing_or_unverified,
            "warning": None if ready else (
                "Supabase schema is missing or cannot verify current recommendation/action "
                f"columns. Apply {self._required_migration} before using Supabase mode "
                "for hosted beta."
            ),
            "errors": errors,
        }

    def status(self, *, force_check: bool = False) -> dict:
        if self._backend_getter() != "supabase":
            return self.check_schema()
        if force_check or self._cache is None:
            self._cache = self.check_schema()
        return self._cache

    def clear_cache(self) -> None:
        self._cache = None
