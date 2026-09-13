from __future__ import annotations

from collections.abc import Generator

from config.database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.trabajos.aplicacion.consultas import (
    FiltroTrabajos,
    TrabajoConsulta,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.consultar_trabajos import (
    ConsultarTrabajosHandler,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyRepositorioTrabajos,
)

router = APIRouter(prefix="/trabajos", tags=["trabajos"])


class ResultadoCotizacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estado: str
    id_peticion: str | None
    id_cotizacion: str | None
    id_proveedor: str | None
    importe_menor: int | None
    moneda: str | None
    motivo: str | None


class TrabajoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    resultado: ResultadoCotizacionResponse | None


def _session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


session_dependency = Depends(_session)


def _respuesta(consulta: TrabajoConsulta) -> TrabajoResponse:
    return TrabajoResponse.model_validate(consulta)


@router.get("/{trabajo_id}", response_model=TrabajoResponse)
def obtener_trabajo(trabajo_id: str, session: Session = session_dependency) -> TrabajoResponse:
    trabajo = ConsultarTrabajosHandler(SqlAlchemyRepositorioTrabajos(session)).por_id(trabajo_id)
    if trabajo is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return _respuesta(trabajo)


@router.get("", response_model=list[TrabajoResponse])
def listar_trabajos(
    id_solicitud: str | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = session_dependency,
) -> list[TrabajoResponse]:
    filtro = FiltroTrabajos(id_solicitud=id_solicitud, limite=limite, offset=offset)
    trabajos = ConsultarTrabajosHandler(SqlAlchemyRepositorioTrabajos(session)).listar(filtro)
    return [_respuesta(trabajo) for trabajo in trabajos]
