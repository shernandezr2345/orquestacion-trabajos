from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResultadoCotizacionConsulta:
    estado: str
    id_peticion: str | None
    id_cotizacion: str | None
    id_proveedor: str | None
    importe_menor: int | None
    moneda: str | None
    motivo: str | None


@dataclass(frozen=True)
class TrabajoConsulta:
    id: str
    estado: str
    version: int
    creado_en: str
    id_solicitud: str
    id_partner: str
    categoria: str
    tipo_solicitud: str
    tipo_red: str
    referencia_externa: str
    id_politica: str
    version_politica: int
    resultado: ResultadoCotizacionConsulta | None


@dataclass(frozen=True)
class FiltroTrabajos:
    id_solicitud: str | None = None
    limite: int = 50
    offset: int = 0


class PuertoConsultaTrabajos(Protocol):
    def consultar_por_id(self, trabajo_id: str) -> TrabajoConsulta | None: ...

    def consultar(self, filtro: FiltroTrabajos) -> list[TrabajoConsulta]: ...
