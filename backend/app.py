"""FastAPI application construction."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address


def create_app(
    *,
    title: str,
    version: str,
    cors_origins: list[str],
    api_key_middleware_cls: type,
    api_key_getter: Callable[[], str],
    resolve_user: Callable[[str], str],
    rate_limit_handler: Callable[[Request, RateLimitExceeded], JSONResponse],
    lifespan: Callable[[FastAPI], Any] | None = None,
) -> tuple[FastAPI, Limiter]:
    app = FastAPI(title=title, version=version, lifespan=lifespan)

    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        api_key_middleware_cls,
        api_key_getter=api_key_getter,
        resolve_user=resolve_user,
    )
    return app, limiter
