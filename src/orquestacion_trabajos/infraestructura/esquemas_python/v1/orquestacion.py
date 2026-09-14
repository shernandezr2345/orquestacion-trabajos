from __future__ import annotations

from pulsar.schema import Integer, Record, String


class TrabajoCreadoV1(Record):
    _avro_namespace = "orquestacion.eventos"

    event_id = String(required=True)
    tipo = String(default="TrabajoCreado.v1", required=True, required_default=True)
    version_contrato = Integer(default=1, required=True, required_default=True)
    instante = String(required=True)
    correlacion = String(required=True)
    causacion = String(required=True)
    id_trabajo = String(required=True)
    id_solicitud = String(required=True)
    id_partner = String(required=True)
    id_peticion = String(required=True)
    referencia_externa = String(required=True)
    categoria = String(required=True)
    tipo_solicitud = String(required=True)
    tipo_red = String(required=True)
    id_politica = String(required=True)
    version_politica = Integer(required=True)
    creado_en = String(required=True)
    estado = String(default="PENDIENTE_COTIZACION", required=True, required_default=True)
    version_trabajo = Integer(default=1, required=True, required_default=True)


class SolicitarCotizacionV1(Record):
    _avro_namespace = "orquestacion.eventos"

    command_id = String(required=True)
    tipo = String(default="SolicitarCotizacion.v1", required=True, required_default=True)
    version_contrato = Integer(default=1, required=True, required_default=True)
    instante = String(required=True)
    correlacion = String(required=True)
    causacion = String(required=True)
    id_peticion = String(required=True)
    id_trabajo = String(required=True)
    id_solicitud = String(required=True)
    id_partner = String(required=True)
    categoria = String(required=True)
    tipo_solicitud = String(required=True)
    tipo_red = String(required=True)
    id_politica = String(required=True)
    version_politica = Integer(required=True)
