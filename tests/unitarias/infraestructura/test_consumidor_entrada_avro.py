from __future__ import annotations

from unittest.mock import Mock

from config.rutas import rutas
from pulsar.schema import AvroSchema

from orquestacion_trabajos.infraestructura.consumidores import ConsumidorEntrada
from orquestacion_trabajos.infraestructura.esquemas_python.v1.entrada import (
    SolicitudDePartnerListaParaAtencionV1,
)


def _record() -> SolicitudDePartnerListaParaAtencionV1:
    return SolicitudDePartnerListaParaAtencionV1(
        event_id="evt-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        referencia_externa="ref-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        id_politica="pol-1",
        version_politica=1,
        version_solicitud=2,
    )


def test_conectar_configura_topic_subscription_shared_y_avro_schema(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr("pulsar.Client", Mock(return_value=client))
    consumidor = ConsumidorEntrada(Mock(), Mock(), Mock())

    consumidor.conectar()

    kwargs = client.subscribe.call_args.kwargs
    assert client.subscribe.call_args.args[0] == rutas.topico_solicitud_entrada
    assert kwargs["subscription_name"] == rutas.suscripcion_solicitud_entrada
    assert kwargs["consumer_type"].name == "Shared"
    assert isinstance(kwargs["schema"], AvroSchema)
    assert kwargs["message_listener"] == consumidor._procesar_mensaje


def test_record_avro_se_adapta_a_dict_para_el_mapper() -> None:
    record = _record()
    datos = {nombre: getattr(record, nombre) for nombre in record._fields}

    assert datos["event_id"] == "evt-1"
    assert datos["id_solicitud"] == "sol-1"
    assert datos["id_partner"] == "partner-1"
    assert datos["version_politica"] == 1