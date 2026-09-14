from __future__ import annotations

from uuid import uuid4

import pytest

from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo, TrabajoEstado
from orquestacion_trabajos.modulos.trabajos.dominio.eventos import CotizacionAplicada
from orquestacion_trabajos.modulos.trabajos.dominio.excepciones import (
    CotizacionAjenaError,
    ResultadoIncompatibleError,
    VersionEsperadaIncompatibleError,
)
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
    ResultadoCotizacion,
)


def _solicitud() -> OrigenSolicitud:
    return OrigenSolicitud(
        id_solicitud=str(uuid4()),
        id_partner=str(uuid4()),
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        referencia_externa="ref-001",
        id_politica=str(uuid4()),
        version_politica=1,
    )


def _condiciones() -> CondicionesAtencion:
    return CondicionesAtencion(
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
    )


def _resultado_aceptado(trabajo: Trabajo) -> ResultadoCotizacion:
    return ResultadoCotizacion(
        id_trabajo=str(trabajo.id),
        id_solicitud=str(trabajo.id_solicitud),
        id_partner=str(trabajo.id_partner),
        id_peticion=str(uuid4()),
        id_cotizacion=str(uuid4()),
        id_proveedor=str(uuid4()),
        estado="ACEPTADA",
        importe_menor=150_000_000,
        moneda="COP",
        categoria=trabajo.categoria,
        tipo_red=trabajo.tipo_red,
    )


def _resultado_rechazado(trabajo: Trabajo) -> ResultadoCotizacion:
    return ResultadoCotizacion(
        id_trabajo=str(trabajo.id),
        id_solicitud=str(trabajo.id_solicitud),
        id_partner=str(trabajo.id_partner),
        id_peticion=str(uuid4()),
        id_cotizacion=str(uuid4()),
        id_proveedor=str(uuid4()),
        estado="RECHAZADA",
        motivo="SIN_OFERTA_PARA_CATEGORIA",
        categoria=trabajo.categoria,
        tipo_red=trabajo.tipo_red,
    )


def test_creacion_de_trabajo_produce_estado_pendiente() -> None:
    trabajo = Trabajo.crear(_solicitud(), _condiciones())

    assert trabajo.estado == TrabajoEstado.PENDIENTE_COTIZACION
    assert trabajo.version == 1
    assert trabajo.id is not None
    assert trabajo.id_solicitud == trabajo.origen.id_solicitud
    assert len(trabajo.eventos_dominio) == 1


def test_cotizacion_perteneciente_a_otro_trabajo_o_solicitud_falla() -> None:
    trabajo = Trabajo.crear(_solicitud(), _condiciones())
    resultado = _resultado_aceptado(trabajo)
    resultado = ResultadoCotizacion(
        id_trabajo=str(uuid4()),
        id_solicitud=str(uuid4()),
        id_partner=str(trabajo.id_partner),
        id_peticion=str(uuid4()),
        id_cotizacion=str(uuid4()),
        id_proveedor=str(uuid4()),
        estado="ACEPTADA",
        importe_menor=200_000_000,
        moneda="COP",
        categoria=trabajo.categoria,
        tipo_red=trabajo.tipo_red,
    )

    with pytest.raises(CotizacionAjenaError):
        trabajo.aplicar_resultado(resultado)


def test_mismo_resultado_es_idempotente_y_no_generan_segundo_evento() -> None:
    trabajo = Trabajo.crear(_solicitud(), _condiciones())
    resultado = _resultado_aceptado(trabajo)

    trabajo.aplicar_resultado(resultado)
    primer_numero_eventos = len(trabajo.eventos_dominio)

    trabajo.aplicar_resultado(resultado)

    assert trabajo.estado == TrabajoEstado.COTIZADO
    assert len(trabajo.eventos_dominio) == primer_numero_eventos
    assert isinstance(trabajo.eventos_dominio[-1], CotizacionAplicada)


def test_resultado_contrario_o_incompatible_falla() -> None:
    trabajo = Trabajo.crear(_solicitud(), _condiciones())
    aceptada = _resultado_aceptado(trabajo)
    rechazada = _resultado_rechazado(trabajo)

    trabajo.aplicar_resultado(aceptada)

    with pytest.raises(ResultadoIncompatibleError):
        trabajo.aplicar_resultado(rechazada)


def test_version_esperada_antigua_falla() -> None:
    trabajo = Trabajo.crear(_solicitud(), _condiciones())
    resultado = _resultado_aceptado(trabajo)

    with pytest.raises(VersionEsperadaIncompatibleError):
        trabajo.aplicar_resultado(resultado, version_esperada=999)


def test_reconstruir_trabajo_en_estado_cotizado_conserva_su_version() -> None:
    trabajo_original = Trabajo.crear(_solicitud(), _condiciones())
    resultado = _resultado_aceptado(trabajo_original)
    trabajo_original.aplicar_resultado(resultado)

    trabajo_recuperado = Trabajo.reconstruir(
        id_trabajo=trabajo_original.id,
        id_solicitud=trabajo_original.id_solicitud,
        id_partner=trabajo_original.id_partner,
        categoria=trabajo_original.categoria,
        tipo_solicitud=trabajo_original.tipo_solicitud,
        tipo_red=trabajo_original.tipo_red,
        referencia_externa=trabajo_original.referencia_externa,
        id_politica=trabajo_original.id_politica,
        version_politica=trabajo_original.version_politica,
        estado=trabajo_original.estado,
        version=trabajo_original.version,
        resultado=trabajo_original.resultado,
    )

    assert trabajo_recuperado.version == trabajo_original.version
    assert trabajo_recuperado.estado == TrabajoEstado.COTIZADO
    assert trabajo_recuperado.eventos_dominio == []


def test_reconstruccion_no_generan_nuevos_eventos() -> None:
    trabajo = Trabajo.crear(_solicitud(), _condiciones())
    trabajo_reconstruido = Trabajo.reconstruir(
        id_trabajo=trabajo.id,
        id_solicitud=trabajo.id_solicitud,
        id_partner=trabajo.id_partner,
        categoria=trabajo.categoria,
        tipo_solicitud=trabajo.tipo_solicitud,
        tipo_red=trabajo.tipo_red,
        referencia_externa=trabajo.referencia_externa,
        id_politica=trabajo.id_politica,
        version_politica=trabajo.version_politica,
        estado=trabajo.estado,
        version=trabajo.version,
        resultado=trabajo.resultado,
    )

    assert trabajo_reconstruido.eventos_dominio == []


def test_los_datos_propios_de_creacion_se_conservan() -> None:
    solicitud = _solicitud()
    trabajo = Trabajo.crear(solicitud, _condiciones())

    assert trabajo.id_solicitud == solicitud.id_solicitud
    assert trabajo.id_partner == solicitud.id_partner
    assert trabajo.categoria == solicitud.categoria
    assert trabajo.tipo_solicitud == solicitud.tipo_solicitud
    assert trabajo.tipo_red == solicitud.tipo_red
    assert trabajo.referencia_externa == solicitud.referencia_externa
    assert trabajo.id_politica == solicitud.id_politica
    assert trabajo.version_politica == solicitud.version_politica


def test_rejection_does_not_require_fields_absent_from_its_contract() -> None:
    from dataclasses import replace

    trabajo = Trabajo.crear(_solicitud(), _condiciones())
    rejected = replace(_resultado_rechazado(trabajo), categoria="", tipo_red="")
    trabajo.aplicar_resultado(rejected)
    assert trabajo.estado == TrabajoEstado.COTIZACION_RECHAZADA
