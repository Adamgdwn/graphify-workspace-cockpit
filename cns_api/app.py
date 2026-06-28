"""CNS API FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from cns_api.routes.health import router as health_router
from cns_api.routes.gail_os import router as gail_os_router
from cns_api.routes.freedom import router as freedom_router
from cns_api.routes.admin import router as admin_router
from cns_api.routes.evidence import router as evidence_router
from cns_api.routes.operating_knowledge import router as okp_router
from cns_api.routes.charters import router as charters_router
from cns_api.routes.charter_execute import router as charter_execute_router
from cns_api.config import get_store_path
from cns_store.db import init_db


@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        store_path = get_store_path()
        init_db(store_path)
    except RuntimeError:
        pass  # CNS_STORE_PATH not set; health route reports store: "missing"
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Graphify CNS API",
        description="Relationship intelligence query service for GAIL OS and Freedom.",
        version="2.0.0",
        lifespan=_lifespan,
    )
    app.include_router(health_router)
    app.include_router(gail_os_router)
    app.include_router(freedom_router)
    app.include_router(admin_router)
    app.include_router(evidence_router)
    app.include_router(okp_router)
    app.include_router(charters_router)
    app.include_router(charter_execute_router)
    return app
