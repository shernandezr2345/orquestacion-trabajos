from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from orquestacion_trabajos.api.app import create_app
from orquestacion_trabajos.config.settings import Settings

settings = Settings.from_environment()
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo, TrabajoEstado
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
    ResultadoCotizacion,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base, TrabajoORM
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyRepositorioTrabajos,
)


def _session_factory():
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _trabajo(
    id_solicitud: str, estado: TrabajoEstado = TrabajoEstado.PENDIENTE_COTIZACION
) -> Trabajo:
    origen = OrigenSolicitud(
        id_solicitud=id_solicitud,
        id_partner="partner-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        referencia_externa="ref-001",
        id_politica="politica-1",
        version_politica=1,
    )
    condiciones = CondicionesAtencion(
        categoria="SINIESTRO", tipo_solicitud="SINIESTRO", tipo_red="GENERAL_HDA"
    )
    resultado = None
    if estado == TrabajoEstado.COTIZADO:
        resultado = ResultadoCotizacion(
            id_trabajo="trabajo-cotizado",
            id_solicitud=id_solicitud,
            id_partner="partner-1",
            id_peticion="peticion-1",
            id_cotizacion="cotizacion-1",
            id_proveedor="proveedor-1",
            estado="ACEPTADA",
            categoria="SINIESTRO",
            tipo_red="GENERAL_HDA",
            importe_menor=15000000,
            moneda="COP",
        )
    elif estado == TrabajoEstado.COTIZACION_RECHAZADA:
        resultado = ResultadoCotizacion(
            id_trabajo="trabajo-rechazado",
            id_solicitud=id_solicitud,
            id_partner="partner-1",
            id_peticion="peticion-2",
            id_cotizacion="",
            id_proveedor="",
            estado="RECHAZADA",
            categoria="SINIESTRO",
            tipo_red="GENERAL_HDA",
            motivo="SIN_OFERTA_PARA_CATEGORIA",
        )
    return Trabajo(
        origen=origen,
        condiciones=condiciones,
        estado=estado,
        resultado=resultado,
        id=str(uuid4()),
        version=2 if resultado else 1,
    )


def _guardar(session_factory, trabajo: Trabajo, creado_en: str) -> None:
    with session_factory() as session:
        SqlAlchemyRepositorioTrabajos(session).guardar(trabajo)
        session.query(TrabajoORM).filter_by(id=str(trabajo.id)).update({"creado_en": creado_en})
        session.commit()


def test_get_trabajo_existente_expone_estado_y_peticion() -> None:
    engine, session_factory = _session_factory()
    trabajo = _trabajo("sol-pendiente")
    _guardar(session_factory, trabajo, "2026-09-13T10:00:00Z")

    with TestClient(create_app()) as client:
        response = client.get(f"/trabajos/{trabajo.id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(trabajo.id),
        "estado": "PENDIENTE_COTIZACION",
        "version": 1,
        "creado_en": "2026-09-13T10:00:00Z",
        "id_solicitud": "sol-pendiente",
        "id_partner": "partner-1",
        "categoria": "SINIESTRO",
        "tipo_solicitud": "SINIESTRO",
        "tipo_red": "GENERAL_HDA",
        "referencia_externa": "ref-001",
        "id_politica": "politica-1",
        "version_politica": 1,
        "resultado": None,
    }
    engine.dispose()


def test_get_trabajo_inexistente_devuelve_404() -> None:
    engine, _ = _session_factory()
    with TestClient(create_app()) as client:
        response = client.get("/trabajos/no-existe")
    assert response.status_code == 404
    engine.dispose()


def test_get_expone_resultado_cotizado_y_rechazado() -> None:
    engine, session_factory = _session_factory()
    cotizado = _trabajo("sol-cotizada", TrabajoEstado.COTIZADO)
    rechazado = _trabajo("sol-rechazada", TrabajoEstado.COTIZACION_RECHAZADA)
    _guardar(session_factory, cotizado, "2026-09-13T10:00:00Z")
    _guardar(session_factory, rechazado, "2026-09-13T10:01:00Z")

    with TestClient(create_app()) as client:
        cotizado_response = client.get(f"/trabajos/{cotizado.id}")
        rechazado_response = client.get(f"/trabajos/{rechazado.id}")

    assert cotizado_response.json()["estado"] == "COTIZADO"
    assert cotizado_response.json()["resultado"]["importe_menor"] == 15000000
    assert rechazado_response.json()["estado"] == "COTIZACION_RECHAZADA"
    assert rechazado_response.json()["resultado"]["motivo"] == "SIN_OFERTA_PARA_CATEGORIA"
    engine.dispose()


def test_listado_filtra_pagina_y_ordena_por_fecha_e_id() -> None:
    engine, session_factory = _session_factory()
    primero = _trabajo("sol-a")
    segundo = _trabajo("sol-b")
    ajeno = _trabajo("sol-ajeno")
    _guardar(session_factory, primero, "2026-09-13T10:00:00Z")
    _guardar(session_factory, segundo, "2026-09-13T10:00:00Z")
    _guardar(session_factory, ajeno, "2026-09-13T10:00:00Z")

    with TestClient(create_app()) as client:
        filtrado = client.get("/trabajos?id_solicitud=sol-a")
        pagina = client.get("/trabajos?limite=1&offset=1")

    assert [item["id_solicitud"] for item in filtrado.json()] == ["sol-a"]
    assert len(pagina.json()) == 1
    assert pagina.json()[0]["id"] == sorted([str(primero.id), str(segundo.id), str(ajeno.id)])[1]
    engine.dispose()


def test_listado_sin_resultados_y_limites_invalidos() -> None:
    engine, _ = _session_factory()
    with TestClient(create_app()) as client:
        vacio = client.get("/trabajos?id_solicitud=ausente")
        limite = client.get("/trabajos?limite=101")
        offset = client.get("/trabajos?offset=-1")
    assert vacio.status_code == 200
    assert vacio.json() == []
    assert limite.status_code == 422
    assert offset.status_code == 422
    engine.dispose()


def test_get_usa_estado_persistido_sin_dependencia_de_cotizaciones() -> None:
    engine, session_factory = _session_factory()
    trabajo = _trabajo("sol-sin-cotizaciones")
    _guardar(session_factory, trabajo, "2026-09-13T10:00:00Z")
    with TestClient(create_app()) as client:
        response = client.get(f"/trabajos/{trabajo.id}")
    assert response.status_code == 200
    assert response.json()["estado"] == "PENDIENTE_COTIZACION"
    engine.dispose()
