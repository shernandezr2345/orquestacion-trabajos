from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    ResultadoCotizacionEntrada,
    SolicitudListaParaAtencion,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo


def _entero_mensaje(valor: object, predeterminado: int = 0) -> int:
    if isinstance(valor, int):
        return valor
    if isinstance(valor, str):
        return int(valor)
    return predeterminado


class MapeadorEventoEntrada:
    """Traducir mensajes Avro de Entrada a tipos de Orquestación."""

    @staticmethod
    def mensaje_a_solicitud(mensaje: dict[str, object]) -> SolicitudListaParaAtencion:
        """Traducir SolicitudDePartnerListaParaAtencion.v1 a tipo local."""
        return SolicitudListaParaAtencion(
            event_id=str(mensaje.get("event_id", "")),
            id_solicitud=str(mensaje.get("id_solicitud", "")),
            id_partner=str(mensaje.get("id_partner", "")),
            categoria=str(mensaje.get("categoria", "")),
            tipo_solicitud=str(mensaje.get("tipo_solicitud", "")),
            tipo_red=str(mensaje.get("tipo_red", "")),
            referencia_externa=str(mensaje.get("referencia_externa", "")),
            id_politica=str(mensaje.get("id_politica", "")),
            version_politica=_entero_mensaje(mensaje.get("version_politica", 1), 1),
        )


class MapeadorTrabajoAvro:
    """Traducir Trabajo a mensajes Avro para publicación."""

    @staticmethod
    def trabajo_a_solicitar_cotizacion(
        trabajo: Trabajo, evento_origen_id: str
    ) -> dict[str, object]:
        """Traducir Trabajo a comando SolicitarCotizacion.v1."""
        ahora = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "command_id": str(uuid4()),
            "tipo": "SolicitarCotizacion.v1",
            "version_contrato": 1,
            "instante": ahora,
            "correlacion": trabajo.id_solicitud,
            "causacion": evento_origen_id,
            "id_peticion": str(trabajo.id),
            "id_trabajo": str(trabajo.id),
            "id_solicitud": trabajo.id_solicitud,
            "id_partner": trabajo.id_partner,
            "categoria": trabajo.categoria,
            "tipo_solicitud": trabajo.tipo_solicitud,
            "tipo_red": trabajo.tipo_red,
            "id_politica": trabajo.id_politica,
            "version_politica": trabajo.version_politica,
        }

    @staticmethod
    def trabajo_a_trabajo_creado(trabajo: Trabajo, evento_origen_id: str) -> dict[str, object]:
        """Traducir Trabajo a evento TrabajoCreado.v1."""
        ahora = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "event_id": str(uuid4()),
            "tipo": "TrabajoCreado.v1",
            "version_contrato": 1,
            "instante": ahora,
            "correlacion": trabajo.id_solicitud,
            "causacion": evento_origen_id,
            "id_trabajo": str(trabajo.id),
            "id_solicitud": trabajo.id_solicitud,
            "id_partner": trabajo.id_partner,
            "id_peticion": str(trabajo.id),
            "referencia_externa": trabajo.referencia_externa,
            "categoria": trabajo.categoria,
            "tipo_solicitud": trabajo.tipo_solicitud,
            "tipo_red": trabajo.tipo_red,
            "id_politica": trabajo.id_politica,
            "version_politica": trabajo.version_politica,
            "creado_en": ahora,
            "estado": trabajo.estado.value,
            "version_trabajo": trabajo.version,
        }


class MapeadorResultadoCotizacion:
    """Traducir eventos de Cotizaciones a tipos locales."""

    @staticmethod
    def cotizacion_registrada_a_resultado(
        mensaje: dict[str, object],
    ) -> ResultadoCotizacionEntrada:
        """Traducir CotizacionRegistrada.v1 a ResultadoCotizacionEntrada."""
        return ResultadoCotizacionEntrada(
            event_id=str(mensaje.get("event_id", "")),
            id_trabajo=str(mensaje.get("id_trabajo", "")),
            id_solicitud=str(mensaje.get("id_solicitud", "")),
            id_partner=str(mensaje.get("id_partner", "")),
            id_peticion=str(mensaje.get("id_peticion", "")),
            id_cotizacion=str(mensaje.get("id_cotizacion", "")),
            id_proveedor=str(mensaje.get("id_proveedor", "")),
            estado="ACEPTADA",
            categoria=str(mensaje.get("categoria", "")),
            tipo_red=str(mensaje.get("tipo_red", "")),
            importe_menor=_entero_mensaje(mensaje.get("importe_menor", 0)) or None,
            moneda=str(mensaje.get("moneda", "")) or None,
        )

    @staticmethod
    def cotizacion_rechazada_a_resultado(
        mensaje: dict[str, object],
    ) -> ResultadoCotizacionEntrada:
        """Traducir CotizacionRechazada.v1 a ResultadoCotizacionEntrada."""
        return ResultadoCotizacionEntrada(
            event_id=str(mensaje.get("event_id", "")),
            id_trabajo=str(mensaje.get("id_trabajo", "")),
            id_solicitud=str(mensaje.get("id_solicitud", "")),
            id_partner=str(mensaje.get("id_partner", "")),
            id_peticion=str(mensaje.get("id_peticion", "")),
            id_cotizacion="",
            id_proveedor="",
            estado="RECHAZADA",
            categoria=str(mensaje.get("categoria", "")),
            tipo_red=str(mensaje.get("tipo_red", "")),
            motivo=str(mensaje.get("motivo", "")),
        )
