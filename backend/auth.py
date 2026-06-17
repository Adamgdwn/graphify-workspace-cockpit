"""Authentication middleware for the backend API."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Require the configured API key when one is set.

    The middleware accepts callables so tests and runtime config can patch
    `backend.main` globals without rebuilding the FastAPI app.
    """

    def __init__(
        self,
        app,
        *,
        api_key_getter: Callable[[], str],
        resolve_user: Callable[[str], str],
    ) -> None:
        super().__init__(app)
        self._api_key_getter = api_key_getter
        self._resolve_user = resolve_user

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        api_key = self._api_key_getter()
        provided = ""
        if (
            api_key
            and request.method != "OPTIONS"
            and request.url.path not in ("/health",)
        ):
            provided = (
                request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                or request.headers.get("x-api-key", "")
            )
            if provided != api_key:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        request.state.user_id = self._resolve_user(provided or api_key)
        return await call_next(request)
