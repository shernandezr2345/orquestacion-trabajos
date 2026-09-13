from __future__ import annotations

from abc import ABC, abstractmethod

from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo


class RepositorioTrabajos(ABC):
    @abstractmethod
    def guardar(self, trabajo: Trabajo) -> None:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, trabajo_id: str) -> Trabajo | None:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_solicitud(self, id_solicitud: str) -> Trabajo | None:
        raise NotImplementedError

    def obtener_por_id_solicitud(self, id_solicitud: str) -> Trabajo | None:
        return self.obtener_por_solicitud(id_solicitud)
