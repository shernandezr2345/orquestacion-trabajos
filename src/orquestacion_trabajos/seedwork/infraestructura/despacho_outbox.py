from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from orquestacion_trabajos.seedwork.infraestructura.orm import OutboxORM


class DespachadorOutbox:
    def __init__(
        self,
        crear_sesion: Callable[[], Session],
        destino: str,
        publicar: Callable[[str, dict[str, object]], None],
    ) -> None:
        self.crear_sesion = crear_sesion
        self.destino = destino
        self.publicar = publicar

    def despachar_siguiente(self) -> bool:
        with self.crear_sesion() as sesion, sesion.begin():
            salida = sesion.execute(
                select(OutboxORM)
                .where(OutboxORM.estado == "PENDIENTE", OutboxORM.destino == self.destino)
                .order_by(OutboxORM.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
            if salida is None:
                return False
            self.publicar(salida.tipo, salida.payload)
            salida.estado = "PROCESADA"
            salida.procesado_en = datetime.now(UTC).isoformat()
        return True
