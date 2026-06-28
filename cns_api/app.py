"""CNS API FastAPI application factory."""
from fastapi import FastAPI
from cns_api.routes.health import router as health_router
from cns_api.routes.gail_os import router as gail_os_router
from cns_api.routes.freedom import router as freedom_router
from cns_api.routes.admin import router as admin_router
from cns_api.routes.evidence import router as evidence_router
from cns_api.routes.operating_knowledge import router as okp_router
from cns_api.routes.charters import router as charters_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Graphify CNS API",
        description="Relationship intelligence query service for GAIL OS and Freedom.",
        version="2.0.0",
    )
    app.include_router(health_router)
    app.include_router(gail_os_router)
    app.include_router(freedom_router)
    app.include_router(admin_router)
    app.include_router(evidence_router)
    app.include_router(okp_router)
    app.include_router(charters_router)
    return app
