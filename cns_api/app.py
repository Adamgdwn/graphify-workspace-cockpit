"""CNS API FastAPI application factory."""
from fastapi import FastAPI
from cns_api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Graphify CNS API",
        description="Relationship intelligence query service for GAIL OS and Freedom.",
        version="2.0.0",
    )
    app.include_router(health_router)
    return app
