from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolicitudListaParaAtencion:
    event_id: str
    id_solicitud: str
    id_partner: str
    categoria: str
    tipo_solicitud: str
    tipo_red: str
    referencia_externa: str
    id_politica: str
    version_politica: int


@dataclass(frozen=True)
class ResultadoCotizacionEntrada:
    event_id: str
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


@dataclass(frozen=True)
class CrearTrabajoCommand:
    solicitud: SolicitudListaParaAtencion


@dataclass(frozen=True)
class AplicarCotizacionCommand:
    resultado: ResultadoCotizacionEntrada
    version_esperada: int | None = None
