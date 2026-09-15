from typing import Protocol

from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos
from orquestacion_trabajos.seedwork.aplicacion.unidad_trabajo import UnidadTrabajo


class UnidadTrabajoTrabajos(UnidadTrabajo, Protocol):
    @property
    def trabajos(self) -> RepositorioTrabajos: ...
    def preparar_entrada(self, consumidor: str, event_id: str, contenido: str) -> bool: ...
    def registrar_creacion(self, trabajo: Trabajo, event_id: str) -> None: ...
