from __future__ import annotations

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    ResultadoCotizacionEntrada,
    SolicitudListaParaAtencion,
)


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
