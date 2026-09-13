from __future__ import annotations

from collections.abc import Callable
from typing import Self, cast

from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import UnidadTrabajo


class SQLAlchemyUnidadTrabajo(UnidadTrabajo):
    def __init__(self, session: Session | Callable[[], Session]) -> None:
        self._session = session

    def _obtener_sesion(self) -> Session:
        session = self._session
        if callable(session):
            return cast(Session, session())
        return session

    def confirmar(self) -> None:
        self._obtener_sesion().commit()

    def revertir(self) -> None:
        self._obtener_sesion().rollback()

    def cerrar(self) -> None:
        self._obtener_sesion().close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.cerrar()
