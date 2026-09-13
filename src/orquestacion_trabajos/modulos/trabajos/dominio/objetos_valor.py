from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from orquestacion_trabajos.seedwork.dominio.objetos_valor import ObjetoValor

if TYPE_CHECKING:
    from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo


@dataclass(frozen=True)
class OrigenSolicitud(ObjetoValor):
    id_solicitud: str
    id_partner: str
    categoria: str
    tipo_solicitud: str
    tipo_red: str
    referencia_externa: str
    id_politica: str
    version_politica: int


@dataclass(frozen=True)
class CondicionesAtencion(ObjetoValor):
    categoria: str
    tipo_solicitud: str
    tipo_red: str


@dataclass(frozen=True)
class ResultadoCotizacion(ObjetoValor):
    id_trabajo: str
    id_solicitud: str
    id_partner: str
    id_peticion: str
    id_cotizacion: str
    id_proveedor: str
    estado: str
    categoria: str
    tipo_red: str
    importe_menor: int | None = None
    moneda: str | None = None
    motivo: str | None = None

    def es_aceptada(self) -> bool:
        return self.estado == "ACEPTADA"

    def es_rechazada(self) -> bool:
        return self.estado == "RECHAZADA"

    def es_compatible_con(self, trabajo: Trabajo) -> bool:
        return (
            self.id_trabajo == str(trabajo.id)
            and self.id_solicitud == str(trabajo.id_solicitud)
            and self.id_partner == str(trabajo.id_partner)
            and self.categoria == trabajo.categoria
            and self.tipo_red == trabajo.tipo_red
        )
