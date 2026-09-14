from __future__ import annotations

from pulsar.schema import Integer, Long, Record, String


class CotizacionRegistradaV1(Record):
    _avro_namespace = "cotizaciones.eventos"

    event_id = String(required=True)
    tipo = String(default="CotizacionRegistrada.v1", required=True, required_default=True)
    version_contrato = Integer(default=1, required=True, required_default=True)
    instante = String(required=True)
    correlacion = String(required=True)
    causacion = String(required=True)
    id_peticion = String(required=True)
    id_trabajo = String(required=True)
    id_solicitud = String(required=True)
    id_partner = String(required=True)
    id_cotizacion = String(required=True)
    id_proveedor = String(required=True)
    categoria = String(required=True)
    tipo_red = String(required=True)
    importe_menor = Long(required=True)
    moneda = String(required=True)
    version_catalogo = Integer(required=True)
    version_cotizacion = Integer(default=1, required=True, required_default=True)


class CotizacionRechazadaV1(Record):
    _avro_namespace = "cotizaciones.eventos"

    event_id = String(required=True)
    tipo = String(default="CotizacionRechazada.v1", required=True, required_default=True)
    version_contrato = Integer(default=1, required=True, required_default=True)
    instante = String(required=True)
    correlacion = String(required=True)
    causacion = String(required=True)
    id_peticion = String(required=True)
    id_trabajo = String(required=True)
    id_solicitud = String(required=True)
    id_partner = String(required=True)
    id_proveedor = String(required=True)
    categoria = String(required=True)
    tipo_red = String(required=True)
    motivo = String(required=True)
    version_catalogo = Integer(required=True)
    version_cotizacion = Integer(default=1, required=True, required_default=True)
