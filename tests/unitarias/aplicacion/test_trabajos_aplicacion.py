from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from uuid import uuid4

import pytest

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    AplicarCotizacionCommand,
    CrearTrabajoCommand,
    ResultadoCotizacionEntrada,
    SolicitudListaParaAtencion,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo, TrabajoEstado
from orquestacion_trabajos.modulos.trabajos.dominio.excepciones import (
    CotizacionAjenaError,
    ResultadoIncompatibleError,
    VersionEsperadaIncompatibleError,
)
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos


class FakeRepositorio(RepositorioTrabajos):
    def __init__(self) -> None:
        self._trabajos: dict[str, Trabajo] = {}
        self._por_solicitud: dict[str, Trabajo] = {}

    def guardar(self, trabajo: Trabajo) -> None:
        self._trabajos[str(trabajo.id)] = trabajo
        self._por_solicitud[trabajo.id_solicitud] = trabajo

    def obtener_por_id(self, trabajo_id: str) -> Trabajo | None:
        return self._trabajos.get(trabajo_id)

    def obtener_por_solicitud(self, id_solicitud: str) -> Trabajo | None:
        return self._por_solicitud.get(id_solicitud)

    def obtener_por_id_solicitud(self, id_solicitud: str) -> Trabajo | None:
        return self.obtener_por_solicitud(id_solicitud)


def _solicitud(event_id: str | None = None) -> SolicitudListaParaAtencion:
    return SolicitudListaParaAtencion(
        event_id=event_id or str(uuid4()),
        id_solicitud=str(uuid4()),
        id_partner=str(uuid4()),
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        referencia_externa="ref-001",
        id_politica=str(uuid4()),
        version_politica=1,
    )


def _resultado_aceptado(trabajo: Trabajo) -> ResultadoCotizacionEntrada:
    return ResultadoCotizacionEntrada(
        event_id=str(uuid4()),
        id_trabajo=str(trabajo.id),
        id_solicitud=str(trabajo.id_solicitud),
        id_partner=str(trabajo.id_partner),
        id_peticion=str(trabajo.id),
        id_cotizacion=str(uuid4()),
        id_proveedor=str(uuid4()),
        estado="ACEPTADA",
        categoria=trabajo.categoria,
        tipo_red=trabajo.tipo_red,
        importe_menor=150_000_000,
        moneda="COP",
    )


def _resultado_rechazado(trabajo: Trabajo) -> ResultadoCotizacionEntrada:
    return ResultadoCotizacionEntrada(
        event_id=str(uuid4()),
        id_trabajo=str(trabajo.id),
        id_solicitud=str(trabajo.id_solicitud),
        id_partner=str(trabajo.id_partner),
        id_peticion=str(trabajo.id),
        id_cotizacion=str(uuid4()),
        id_proveedor=str(uuid4()),
        estado="RECHAZADA",
        categoria=trabajo.categoria,
        tipo_red=trabajo.tipo_red,
        motivo="SIN_OFERTA_PARA_CATEGORIA",
    )


def test_crear_trabajo_registra_salida() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    handler = CrearTrabajoHandler(lambda: unidad)

    comando = CrearTrabajoCommand(solicitud=_solicitud())
    trabajo = handler.ejecutar(comando)

    assert trabajo.estado == TrabajoEstado.PENDIENTE_COTIZACION
    assert repo.obtener_por_id(str(trabajo.id)) is trabajo
    assert unidad.salidas[0].tipo == "TrabajoCreado.v1"
    assert unidad.salidas[1].tipo == "SolicitarCotizacion.v1"


def test_crear_trabajo_es_idempotente_por_event_id() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    handler = CrearTrabajoHandler(lambda: unidad)
    solicitud = _solicitud(event_id="evt-dup")

    primer = handler.ejecutar(CrearTrabajoCommand(solicitud=solicitud))
    segundo = handler.ejecutar(CrearTrabajoCommand(solicitud=solicitud))

    assert segundo is primer
    assert len(repo._trabajos) == 1


def test_crear_trabajo_es_idempotente_por_solicitud_y_nuevo_event_id() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    handler = CrearTrabajoHandler(lambda: unidad)
    solicitud = _solicitud(event_id="evt-1")

    primer = handler.ejecutar(CrearTrabajoCommand(solicitud=solicitud))
    otra = SolicitudListaParaAtencion(
        event_id="evt-2",
        id_solicitud=solicitud.id_solicitud,
        id_partner=solicitud.id_partner,
        categoria=solicitud.categoria,
        tipo_solicitud=solicitud.tipo_solicitud,
        tipo_red=solicitud.tipo_red,
        referencia_externa=solicitud.referencia_externa,
        id_politica=solicitud.id_politica,
        version_politica=solicitud.version_politica,
    )

    segundo = handler.ejecutar(CrearTrabajoCommand(solicitud=otra))

    assert segundo is primer
    assert len(repo._trabajos) == 1


def test_crear_trabajo_conflicto_con_event_id_reutilizado_con_contenido_distinto() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    handler = CrearTrabajoHandler(lambda: unidad)

    primera = _solicitud(event_id="evt-dup")
    handler.ejecutar(CrearTrabajoCommand(solicitud=primera))

    otra = SolicitudListaParaAtencion(
        event_id="evt-dup",
        id_solicitud=str(uuid4()),
        id_partner="otro-partner",
        categoria=primera.categoria,
        tipo_solicitud=primera.tipo_solicitud,
        tipo_red=primera.tipo_red,
        referencia_externa=primera.referencia_externa,
        id_politica=primera.id_politica,
        version_politica=primera.version_politica,
    )
    with pytest.raises(ValueError, match="conflicto"):
        handler.ejecutar(CrearTrabajoCommand(solicitud=otra))


def test_aplicar_cotizacion_valida_actualiza_el_trabajo() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    crear = CrearTrabajoHandler(lambda: unidad)
    trabajo = crear.ejecutar(CrearTrabajoCommand(solicitud=_solicitud()))

    aplicar = AplicarCotizacionHandler(lambda: unidad)
    resultado = _resultado_aceptado(trabajo)

    trabajo_actualizado = aplicar.ejecutar(AplicarCotizacionCommand(resultado=resultado))

    assert trabajo_actualizado.estado == TrabajoEstado.COTIZADO
    assert trabajo_actualizado.resultado is not None
    assert len(unidad.salidas) == 2


def test_aplicar_cotizacion_repetida_no_generan_efectos_duplicados() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    crear = CrearTrabajoHandler(lambda: unidad)
    trabajo = crear.ejecutar(CrearTrabajoCommand(solicitud=_solicitud()))
    aplicar = AplicarCotizacionHandler(lambda: unidad)
    resultado = _resultado_aceptado(trabajo)

    primero = aplicar.ejecutar(AplicarCotizacionCommand(resultado=resultado))
    segundo = aplicar.ejecutar(AplicarCotizacionCommand(resultado=resultado))

    assert primero is segundo
    assert len(repo._trabajos) == 1


def test_aplicar_cotizacion_falla_si_trabajo_no_existe() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    handler = AplicarCotizacionHandler(lambda: unidad)

    comando = AplicarCotizacionCommand(
        resultado=ResultadoCotizacionEntrada(
            event_id=str(uuid4()),
            id_trabajo=str(uuid4()),
            id_solicitud=str(uuid4()),
            id_partner=str(uuid4()),
            id_peticion=str(uuid4()),
            id_cotizacion=str(uuid4()),
            id_proveedor=str(uuid4()),
            estado="ACEPTADA",
            categoria="SINIESTRO",
            tipo_red="GENERAL_HDA",
            importe_menor=100,
            moneda="COP",
        )
    )

    with pytest.raises(ValueError, match="no existe"):
        handler.ejecutar(comando)


def test_aplicar_cotizacion_falla_si_resultado_es_ajeno() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    crear = CrearTrabajoHandler(lambda: unidad)
    trabajo = crear.ejecutar(CrearTrabajoCommand(solicitud=_solicitud()))
    handler = AplicarCotizacionHandler(lambda: unidad)

    resultado = ResultadoCotizacionEntrada(
        event_id=str(uuid4()),
        id_trabajo=str(trabajo.id),
        id_solicitud=str(uuid4()),
        id_partner=trabajo.id_partner,
        id_peticion=str(uuid4()),
        id_cotizacion=str(uuid4()),
        id_proveedor=str(uuid4()),
        estado="ACEPTADA",
        categoria=trabajo.categoria,
        tipo_red=trabajo.tipo_red,
        importe_menor=150_000_000,
        moneda="COP",
    )
    with pytest.raises(CotizacionAjenaError):
        handler.ejecutar(AplicarCotizacionCommand(resultado=resultado))


def test_aplicar_cotizacion_falla_si_resultado_incompatible() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    crear = CrearTrabajoHandler(lambda: unidad)
    trabajo = crear.ejecutar(CrearTrabajoCommand(solicitud=_solicitud()))
    handler = AplicarCotizacionHandler(lambda: unidad)

    aceptada = _resultado_aceptado(trabajo)
    handler.ejecutar(AplicarCotizacionCommand(resultado=aceptada))
    rechazada = _resultado_rechazado(trabajo)

    with pytest.raises(ResultadoIncompatibleError):
        handler.ejecutar(AplicarCotizacionCommand(resultado=rechazada))


def test_aplicar_cotizacion_falla_si_version_esperada_invalida() -> None:
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)
    crear = CrearTrabajoHandler(lambda: unidad)
    trabajo = crear.ejecutar(CrearTrabajoCommand(solicitud=_solicitud()))
    handler = AplicarCotizacionHandler(lambda: unidad)

    with pytest.raises(VersionEsperadaIncompatibleError):
        handler.ejecutar(
            AplicarCotizacionCommand(resultado=_resultado_aceptado(trabajo), version_esperada=999)
        )


@dataclass
class Salida:
    tipo: str


class FakeUnidad:
    def __init__(self, repo):
        self.trabajos = repo
        self.salidas = []
        self.inbox = {}
        self.confirmaciones = 0

    def __enter__(self):
        self.snapshot = deepcopy((self.trabajos.__dict__, self.salidas, self.inbox))
        self.confirmada = False
        return self

    def __exit__(self, *args):
        if not self.confirmada:
            self.revertir()

    def confirmar(self):
        self.confirmada = True
        self.confirmaciones += 1

    def revertir(self):
        datos, self.salidas, self.inbox = self.snapshot
        self.trabajos.__dict__.update(datos)

    def preparar_entrada(self, consumidor, event_id, contenido):
        key = (consumidor, event_id)
        if key in self.inbox:
            if self.inbox[key] != contenido:
                raise ValueError("conflicto de inbox")
            return False
        self.inbox[key] = contenido
        return True

    def registrar_creacion(self, trabajo, event_id):
        self.salidas.extend([Salida("TrabajoCreado.v1"), Salida("SolicitarCotizacion.v1")])


def test_failure_registering_outputs_rolls_back_work_and_inbox():
    repo = FakeRepositorio()
    unidad = FakeUnidad(repo)

    def fail(*args):
        raise RuntimeError("output failure")

    unidad.registrar_creacion = fail
    with pytest.raises(RuntimeError, match="output failure"):
        CrearTrabajoHandler(lambda: unidad).ejecutar(CrearTrabajoCommand(_solicitud()))
    assert not repo._trabajos
    assert not unidad.inbox
    assert unidad.confirmaciones == 0
