from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.sagas.infraestructura.repositorios import (
    SqlAlchemyRepositorioSagaLog,
    SqlAlchemyRepositorioSagas,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.infraestructura.mapeadores_eventos import (
    MapeadorTrabajoAvro,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyRepositorioTrabajos,
)
from orquestacion_trabajos.seedwork.infraestructura.inbox import SqlAlchemyInbox
from orquestacion_trabajos.seedwork.infraestructura.orm import OutboxORM
from orquestacion_trabajos.seedwork.infraestructura.outbox import SqlAlchemyOutbox
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


class UnidadTrabajoSagaTrabajosSQL(UnidadTrabajoSQL):
    restricciones_reintentables = frozenset(
        {
            "uq_saga_instance_id_solicitud",
            "uq_saga_log_idempotencia",
            "uq_trabajos_id_solicitud",
            "uq_inbox_consumidor_mensaje",
        }
    )

    def __init__(self, crear_sesion: Callable[[], Session], destinos: dict[str, str]) -> None:
        super().__init__(crear_sesion)
        self.destinos = destinos

    def _crear_repositorios(self) -> None:
        self._sagas = SqlAlchemyRepositorioSagas(self.sesion, lock_reads=True)
        self._saga_logs = SqlAlchemyRepositorioSagaLog(self.sesion)
        self._trabajos = SqlAlchemyRepositorioTrabajos(self.sesion)

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

    @property
    def trabajos(self) -> SqlAlchemyRepositorioTrabajos:
        if not self._activa:
            raise RuntimeError("Unidad de trabajo inactiva")
        return self._trabajos

    def preparar_entrada(self, consumidor: str, event_id: str, contenido: str) -> bool:
        inbox = SqlAlchemyInbox(self.sesion)
        procesado = inbox.ya_procesado(consumidor=consumidor, id_mensaje=event_id)
        inbox.registrar(consumidor=consumidor, id_mensaje=event_id, contenido=contenido)
        return not procesado

    def registrar_creacion(self, trabajo: Trabajo, event_id: str) -> None:
        outbox = SqlAlchemyOutbox(self.sesion)
        for tipo, mapper in (
            ("TrabajoCreado.v1", MapeadorTrabajoAvro.trabajo_a_trabajo_creado),
            ("SolicitarCotizacion.v1", MapeadorTrabajoAvro.trabajo_a_solicitar_cotizacion),
        ):
            outbox.registrar(
                tipo=tipo, payload=mapper(trabajo, event_id), destino=self.destinos[tipo]
            )

    def sincronizar(self) -> None:
        self.sesion.flush()

    def registrar_mensaje(self, tipo: str, payload: dict[str, object]) -> None:
        SqlAlchemyOutbox(self.sesion).registrar(
            tipo=tipo,
            payload=payload,
            destino=self.destinos[tipo],
        )

    def outbox_por_tipo(self, *, tipo: str) -> list[dict[str, object]]:
        rows = (
            self.sesion.execute(
                select(OutboxORM).where(OutboxORM.tipo == tipo).order_by(OutboxORM.id.asc())
            )
            .scalars()
            .all()
        )
        return [dict(row.payload) for row in rows]
