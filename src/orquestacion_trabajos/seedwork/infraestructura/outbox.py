from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from orquestacion_trabajos.seedwork.infraestructura.orm import OutboxORM


class SqlAlchemyOutbox:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _sesion(self) -> Session:
        return self._session

    def registrar(
        self,
        *,
        tipo: str,
        payload: Mapping[str, object],
        destino: str | None = None,
    ) -> None:
        session = self._sesion()
        session.add(
            OutboxORM(
                tipo=tipo,
                destino=destino,
                payload=payload,
                estado="PENDIENTE",
                creado_en=datetime.now(UTC).isoformat(),
                procesado_en=None,
            )
        )

    def pendientes(self) -> list[dict[str, object]]:
        session = self._sesion()
        rows = (
            session.execute(select(OutboxORM).where(OutboxORM.estado == "PENDIENTE"))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "tipo": row.tipo,
                "destino": row.destino,
                "payload": row.payload,
            }
            for row in rows
        ]
