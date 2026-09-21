from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.sagas.infraestructura.repositorios import (
    SqlAlchemyRepositorioSagaLog,
    SqlAlchemyRepositorioSagas,
)
from orquestacion_trabajos.seedwork.infraestructura.unidad_trabajo_sqlalchemy import (
    UnidadTrabajoSQL,
)


class UnidadTrabajoSagasSQL(UnidadTrabajoSQL):
    restricciones_reintentables = frozenset(
        {
            "uq_saga_instance_id_solicitud",
            "uq_saga_log_idempotencia",
        }
    )

    def __init__(self, crear_sesion: Callable[[], Session]) -> None:
        super().__init__(crear_sesion)

    def _crear_repositorios(self) -> None:
        self._sagas = SqlAlchemyRepositorioSagas(self.sesion)
        self._saga_logs = SqlAlchemyRepositorioSagaLog(self.sesion)

    @property
    def sagas(self) -> SqlAlchemyRepositorioSagas:
        if not self._activa:
            raise RuntimeError("Unidad de trabajo inactiva")
        return self._sagas

    @property
    def saga_logs(self) -> SqlAlchemyRepositorioSagaLog:
        if not self._activa:
            raise RuntimeError("Unidad de trabajo inactiva")
        return self._saga_logs
