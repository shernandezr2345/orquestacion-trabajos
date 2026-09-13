from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos
from orquestacion_trabajos.modulos.trabajos.infraestructura.mapeadores import TrabajoMapper
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import (
    InboxORM,
    OutboxORM,
    TrabajoORM,
)


class InboxConflictError(ValueError):
    """Se intenta registrar un mismo mensaje de Inbox con contenido distinto."""


class SqlAlchemyInbox:
    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session = session

    def _sesion(self) -> Session:
        session = self._session
        if callable(session):
            return cast(Session, session())
        return session

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
                    estado="PENDIENTE",
                    creado_en="now",
                    procesado_en=None,
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


class SqlAlchemyOutbox:
    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session = session

    def _sesion(self) -> Session:
        session = self._session
        if callable(session):
            return cast(Session, session())
        return session

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
                creado_en="now",
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


class SqlAlchemyRepositorioTrabajos(RepositorioTrabajos):
    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session = session

    def _sesion(self) -> Session:
        session = self._session
        if callable(session):
            return cast(Session, session())
        return session

    def guardar(self, trabajo: Trabajo) -> None:
        session = self._sesion()
        try:
            row = session.get(TrabajoORM, str(trabajo.id))
            mapped = TrabajoMapper.a_orm(trabajo)
            if row is None:
                session.add(mapped)
            else:
                row.id_solicitud = mapped.id_solicitud
                row.id_partner = mapped.id_partner
                row.categoria = mapped.categoria
                row.tipo_solicitud = mapped.tipo_solicitud
                row.tipo_red = mapped.tipo_red
                row.referencia_externa = mapped.referencia_externa
                row.id_politica = mapped.id_politica
                row.version_politica = mapped.version_politica
                row.estado = mapped.estado
                row.version = mapped.version
                row.resultado_estado = mapped.resultado_estado
                row.resultado_id_peticion = mapped.resultado_id_peticion
                row.resultado_id_cotizacion = mapped.resultado_id_cotizacion
                row.resultado_id_proveedor = mapped.resultado_id_proveedor
                row.resultado_categoria = mapped.resultado_categoria
                row.resultado_tipo_red = mapped.resultado_tipo_red
                row.resultado_importe_menor = mapped.resultado_importe_menor
                row.resultado_moneda = mapped.resultado_moneda
                row.resultado_motivo = mapped.resultado_motivo
        except IntegrityError as exc:
            raise ValueError("Conflicto de unicidad al guardar trabajo") from exc

    def obtener_por_id(self, trabajo_id: str) -> Trabajo | None:
        session = self._sesion()
        row = session.get(TrabajoORM, trabajo_id)
        if row is None:
            return None
        return TrabajoMapper.desde_orm(row)

    def obtener_por_solicitud(self, id_solicitud: str) -> Trabajo | None:
        session = self._sesion()
        row = session.execute(
            select(TrabajoORM).where(TrabajoORM.id_solicitud == id_solicitud)
        ).scalar_one_or_none()
        if row is None:
            return None
        return TrabajoMapper.desde_orm(row)
