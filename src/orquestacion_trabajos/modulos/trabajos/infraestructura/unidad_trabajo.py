from collections.abc import Callable

from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.infraestructura.mapeadores_eventos import (
    MapeadorTrabajoAvro,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyRepositorioTrabajos,
)
from orquestacion_trabajos.seedwork.infraestructura.inbox import SqlAlchemyInbox
from orquestacion_trabajos.seedwork.infraestructura.outbox import SqlAlchemyOutbox
from orquestacion_trabajos.seedwork.infraestructura.unidad_trabajo_sqlalchemy import (
    UnidadTrabajoSQL,
)


class UnidadTrabajoTrabajosSQL(UnidadTrabajoSQL):
    restricciones_reintentables = frozenset(
        {"uq_trabajos_id_solicitud", "uq_inbox_consumidor_mensaje"}
    )

    def __init__(self, crear_sesion: Callable[[], Session], destinos: dict[str, str]) -> None:
        super().__init__(crear_sesion)
        self.destinos = destinos

    def _crear_repositorios(self) -> None:
        self._trabajos = SqlAlchemyRepositorioTrabajos(self.sesion)

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
