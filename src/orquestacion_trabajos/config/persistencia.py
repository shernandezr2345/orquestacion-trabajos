from collections.abc import Callable

from sqlalchemy import select

from orquestacion_trabajos.config.database import Database
from orquestacion_trabajos.config.rutas import destinos
from orquestacion_trabajos.config.settings import Settings
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import UnidadTrabajoTrabajos
from orquestacion_trabajos.modulos.trabajos.infraestructura.unidad_trabajo import (
    UnidadTrabajoTrabajosSQL,
)
from orquestacion_trabajos.seedwork.infraestructura.orm import OutboxORM


def crear_uow(base: Database, settings: Settings) -> Callable[[], UnidadTrabajoTrabajos]:
    return lambda: UnidadTrabajoTrabajosSQL(base.session_factory, destinos(settings))


def verificar_destinos(base: Database, settings: Settings) -> None:
    permitidos = destinos(settings)
    with base.session_factory() as sesion:
        pendientes = sesion.execute(
            select(OutboxORM.tipo, OutboxORM.destino)
            .where(OutboxORM.estado == "PENDIENTE")
            .distinct()
        )
        for tipo, destino in pendientes:
            if tipo not in permitidos or destino != permitidos[tipo]:
                raise ValueError(f"Unknown outbox destination: {tipo} / {destino}")
