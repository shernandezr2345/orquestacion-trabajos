from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from config.database import engine
from config.settings import settings
from fastapi import FastAPI
from sqlalchemy import text

from orquestacion_trabajos.api.trabajos import router as trabajos_router
from orquestacion_trabajos.infraestructura.ciclo_vida import CicloVidaPulsar

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.db_ready = True
    app.state.pulsar_ready = False
    app.state.consumers_started = False
    app.state.ciclo_vida_pulsar = None

    if settings.enable_lifespan_consumers:
        try:
            logger.info("Iniciando ciclo de vida de Pulsar en lifespan")
            ciclo_vida = CicloVidaPulsar()
            ciclo_vida.iniciar()
            app.state.ciclo_vida_pulsar = ciclo_vida
            app.state.consumers_started = True
            app.state.pulsar_ready = True
            logger.info("Ciclo de vida de Pulsar iniciado correctamente")
        except Exception:
            logger.exception("Error iniciando Pulsar en lifespan")
            app.state.consumers_started = False
            app.state.pulsar_ready = False

    yield

    # Shutdown
    if app.state.ciclo_vida_pulsar is not None:
        try:
            logger.info("Deteniendo ciclo de vida de Pulsar")
            app.state.ciclo_vida_pulsar.detener()
        except Exception:
            logger.exception("Error deteniendo Pulsar")

    app.state.db_ready = False
    app.state.pulsar_ready = False
    app.state.consumers_started = False


def create_app() -> FastAPI:
    app = FastAPI(title="Orquestacion Trabajos", version="0.1.0", lifespan=lifespan)
    app.include_router(trabajos_router)

    @app.get("/health/live")
    async def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, object]:
        database_ready = False
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            database_ready = True
        except Exception:
            logger.exception("PostgreSQL no disponible para readiness")

        if settings.enable_lifespan_consumers:
            ciclo_vida = app.state.ciclo_vida_pulsar
            pulsar_ready = ciclo_vida is not None and ciclo_vida.esta_listo()
        else:
            pulsar_ready = True

        return {
            "status": "ready" if database_ready and pulsar_ready else "not_ready",
            "database": "ready" if database_ready else "not_ready",
            "pulsar": "ready" if pulsar_ready else "not_ready",
            "consumers": app.state.consumers_started,
        }

    return app


app = create_app()
