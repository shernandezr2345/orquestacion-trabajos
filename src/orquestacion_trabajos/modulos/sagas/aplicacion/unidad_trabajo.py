from typing import Protocol

from orquestacion_trabajos.modulos.sagas.dominio.repositorios import (
    RepositorioSagaLog,
    RepositorioSagas,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import UnidadTrabajoTrabajos


class UnidadTrabajoSaga(UnidadTrabajoTrabajos, Protocol):
    @property
    def sagas(self) -> RepositorioSagas: ...
    @property
    def saga_logs(self) -> RepositorioSagaLog: ...
    def sincronizar(self) -> None: ...
    def registrar_mensaje(self, tipo: str, payload: dict[str, object]) -> None: ...
    def outbox_por_tipo(self, *, tipo: str) -> list[dict[str, object]]: ...
