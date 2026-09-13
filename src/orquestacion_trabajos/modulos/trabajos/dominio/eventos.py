from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from orquestacion_trabajos.seedwork.dominio.eventos import EventoInterno


@dataclass(frozen=True)
class TrabajoCreado(EventoInterno):
    id_trabajo: str
    id_solicitud: str
    id_partner: str
    categoria: str
    tipo_solicitud: str
    tipo_red: str
    referencia_externa: str
    id_politica: str
    version_politica: int
    instante: datetime


@dataclass(frozen=True)
class CotizacionAplicada(EventoInterno):
    id_trabajo: str
    id_solicitud: str
    id_partner: str
    id_peticion: str
    id_cotizacion: str
    estado: str
    instante: datetime
