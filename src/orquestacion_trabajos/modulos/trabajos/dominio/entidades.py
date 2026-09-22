from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from orquestacion_trabajos.modulos.trabajos.dominio.eventos import CotizacionAplicada, TrabajoCreado
from orquestacion_trabajos.modulos.trabajos.dominio.excepciones import (
    CotizacionAjenaError,
    EstadoTrabajoInvalidoError,
    ResultadoIncompatibleError,
    VersionEsperadaIncompatibleError,
)
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
    ResultadoCotizacion,
)
from orquestacion_trabajos.seedwork.dominio.entidades import Entidad


class TrabajoEstado(str, Enum):
    PENDIENTE_COTIZACION = "PENDIENTE_COTIZACION"
    COTIZADO = "COTIZADO"
    COTIZACION_RECHAZADA = "COTIZACION_RECHAZADA"
    CANCELADO = "CANCELADO"


class Trabajo(Entidad):
    def __init__(
        self,
        *,
        origen: OrigenSolicitud,
        condiciones: CondicionesAtencion,
        estado: TrabajoEstado = TrabajoEstado.PENDIENTE_COTIZACION,
        resultado: ResultadoCotizacion | None = None,
        id: str | None = None,
        version: int = 1,
    ) -> None:
        super().__init__(id=id or str(uuid4()), version=version)
        self.origen = origen
        self.condiciones = condiciones
        self.estado = estado
        self.resultado = resultado
        self.id_solicitud = self.origen.id_solicitud
        self.id_partner = self.origen.id_partner
        self.categoria = self.origen.categoria
        self.tipo_solicitud = self.origen.tipo_solicitud
        self.tipo_red = self.origen.tipo_red
        self.referencia_externa = self.origen.referencia_externa
        self.id_politica = self.origen.id_politica
        self.version_politica = self.origen.version_politica
        if self.estado == TrabajoEstado.PENDIENTE_COTIZACION and self.resultado is None:
            self._validar_estado_inicial()

    def _validar_estado_inicial(self) -> None:
        if self.estado not in {TrabajoEstado.PENDIENTE_COTIZACION}:
            raise EstadoTrabajoInvalidoError(
                "El trabajo recién creado debe iniciar en PENDIENTE_COTIZACION"
            )

    @classmethod
    def crear(cls, origen: OrigenSolicitud, condiciones: CondicionesAtencion) -> Trabajo:
        trabajo = cls(
            origen=origen, condiciones=condiciones, estado=TrabajoEstado.PENDIENTE_COTIZACION
        )
        evento = TrabajoCreado(
            id_trabajo=str(trabajo.id),
            id_solicitud=trabajo.id_solicitud,
            id_partner=trabajo.id_partner,
            categoria=trabajo.categoria,
            tipo_solicitud=trabajo.tipo_solicitud,
            tipo_red=trabajo.tipo_red,
            referencia_externa=trabajo.referencia_externa,
            id_politica=trabajo.id_politica,
            version_politica=trabajo.version_politica,
            instante=datetime.now(UTC),
        )
        trabajo.agregar_evento(evento)
        return trabajo

    def cancelar(self) -> None:
        if self.estado != TrabajoEstado.CANCELADO:
            self.estado = TrabajoEstado.CANCELADO
            self.version += 1

    def aplicar_resultado(
        self,
        resultado: ResultadoCotizacion,
        *,
        version_esperada: int | None = None,
    ) -> None:
        if version_esperada is not None and version_esperada != self.version:
            raise VersionEsperadaIncompatibleError(
                f"Versión esperada incompatibe: {version_esperada} != {self.version}"
            )

        if not resultado.es_compatible_con(self):
            raise CotizacionAjenaError("La cotización no pertenece a este trabajo o solicitud")

        if self.resultado is not None:
            if self.resultado == resultado:
                return
            raise ResultadoIncompatibleError(
                "Un resultado terminal no puede ser reemplazado por otro resultado"
            )

        if self.estado == TrabajoEstado.CANCELADO:
            raise EstadoTrabajoInvalidoError("Un trabajo cancelado no puede reactivarse")

        if resultado.es_aceptada():
            self.estado = TrabajoEstado.COTIZADO
        elif resultado.es_rechazada():
            self.estado = TrabajoEstado.COTIZACION_RECHAZADA
        else:
            raise EstadoTrabajoInvalidoError("Resultado de cotización no soportado")

        self.resultado = resultado
        self.version += 1

        evento = CotizacionAplicada(
            id_trabajo=str(self.id),
            id_solicitud=self.id_solicitud,
            id_partner=self.id_partner,
            id_peticion=resultado.id_peticion,
            id_cotizacion=resultado.id_cotizacion,
            estado=resultado.estado,
            instante=datetime.now(UTC),
        )
        self.agregar_evento(evento)

    @classmethod
    def reconstruir(
        cls,
        *,
        id_trabajo: str,
        id_solicitud: str,
        id_partner: str,
        categoria: str,
        tipo_solicitud: str,
        tipo_red: str,
        referencia_externa: str,
        id_politica: str,
        version_politica: int,
        estado: TrabajoEstado,
        version: int,
        resultado: ResultadoCotizacion | None,
    ) -> Trabajo:
        trabajo = cls(
            origen=OrigenSolicitud(
                id_solicitud=id_solicitud,
                id_partner=id_partner,
                categoria=categoria,
                tipo_solicitud=tipo_solicitud,
                tipo_red=tipo_red,
                referencia_externa=referencia_externa,
                id_politica=id_politica,
                version_politica=version_politica,
            ),
            condiciones=CondicionesAtencion(
                categoria=categoria,
                tipo_solicitud=tipo_solicitud,
                tipo_red=tipo_red,
            ),
            estado=estado,
            resultado=resultado,
            id=id_trabajo,
            version=version,
        )
        trabajo.limpiar_eventos()
        return trabajo
