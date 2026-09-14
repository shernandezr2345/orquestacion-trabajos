from __future__ import annotations

from pulsar.schema import Boolean, Integer, Record, String


class _NullableBoolean(Boolean):
    def default(self) -> bool | None:
        return None


class SolicitudDePartnerListaParaAtencionV1(Record):
    _avro_namespace = "entrada.eventos"

    event_id = String(required=True)
    tipo = String(
        default="SolicitudDePartnerListaParaAtencion.v1",
        required=True,
        required_default=True,
    )
    version_contrato = Integer(default=1, required=True, required_default=True)
    instante = String(required=True)
    correlacion = String(required=True)
    id_solicitud = String(required=True)
    id_partner = String(required=True)
    referencia_externa = String(required=True)
    categoria = String(required=True)
    tipo_solicitud = String(required=True)
    aprobacion_previa = _NullableBoolean(default=None, required_default=True)
    tipo_red = String(required=True)
    id_politica = String(required=True)
    version_politica = Integer(required=True)
    version_solicitud = Integer(required=True)
