from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from config.settings import settings
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db_ready = True
    app.state.pulsar_ready = False
    app.state.consumers_started = False
    if settings.enable_lifespan_consumers:
        app.state.consumers_started = True
    yield
    app.state.db_ready = False
    app.state.pulsar_ready = False
    app.state.consumers_started = False


def create_app() -> FastAPI:
    app = FastAPI(title="Orquestacion Trabajos", version="0.1.0", lifespan=lifespan)

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, object]:
        return {
            "status": "ready",
            "database": "not_checked",
            "pulsar": "not_checked",
            "consumers": app.state.consumers_started,
        }

    return app


app = create_app()
