import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from orquestacion_trabajos.seedwork.infraestructura.orm import InboxORM


class InboxConflictError(ValueError):
    """Se intenta registrar un mismo mensaje de Inbox con contenido distinto."""


class SqlAlchemyInbox:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _sesion(self) -> Session:
        return self._session

    @staticmethod
    def _normalizar_contenido(contenido: str) -> str:
        try:
            return json.dumps(json.loads(contenido), sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            return contenido.strip()

    @classmethod
    def _contenido_igual(cls, izquierdo: str, derecho: str) -> bool:
        return cls._normalizar_contenido(izquierdo) == cls._normalizar_contenido(derecho)

    def registrar(self, *, consumidor: str, id_mensaje: str, contenido: str) -> None:
        session = self._sesion()
        fila = session.execute(
            select(InboxORM).where(
                (InboxORM.consumidor == consumidor) & (InboxORM.id_mensaje == id_mensaje)
            )
        ).scalar_one_or_none()

        if fila is None:
            session.add(
                InboxORM(
                    consumidor=consumidor,
                    id_mensaje=id_mensaje,
                    contenido=contenido,
                    estado="PROCESADA",
                    creado_en=datetime.now(UTC).isoformat(),
                    procesado_en=datetime.now(UTC).isoformat(),
                )
            )
            return

        if self._contenido_igual(fila.contenido, contenido):
            return

        raise InboxConflictError(
            f"Conflito de inbox para consumidor={consumidor} y id_mensaje={id_mensaje}"
        )

    def ya_procesado(self, *, consumidor: str, id_mensaje: str) -> bool:
        session = self._sesion()
        row = session.execute(
            select(InboxORM).where(
                (InboxORM.consumidor == consumidor) & (InboxORM.id_mensaje == id_mensaje)
            )
        ).scalar_one_or_none()
        return row is not None
