from __future__ import annotations

from unittest.mock import Mock

from config.rutas import rutas
from pulsar.schema import AvroSchema

from orquestacion_trabajos.infraestructura.consumidores import (
    ConsumidorCotizacionRechazada,
    ConsumidorCotizacionRegistrada,
)
from orquestacion_trabajos.infraestructura.esquemas_python.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)


def _registrada() -> CotizacionRegistradaV1:
    return CotizacionRegistradaV1(
        event_id="evt-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        causacion="cmd-1",
        id_peticion="pet-1",
        id_trabajo="trab-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        id_cotizacion="cot-1",
        id_proveedor="prov-1",
        categoria="SINIESTRO",
        tipo_red="GENERAL_HDA",
        importe_menor=15000000,
        moneda="COP",
        version_catalogo=1,
    )


def _rechazada() -> CotizacionRechazadaV1:
    return CotizacionRechazadaV1(
        event_id="evt-2",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        causacion="cmd-1",
        id_peticion="pet-1",
        id_trabajo="trab-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        id_proveedor="prov-1",
        categoria="SINIESTRO",
        tipo_red="GENERAL_HDA",
        motivo="SIN_OFERTA_PARA_CATEGORIA",
        version_catalogo=1,
    )


def test_registrada_configura_topic_subscription_shared_y_schema(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr("pulsar.Client", Mock(return_value=client))
    consumidor = ConsumidorCotizacionRegistrada(Mock())

    consumidor.conectar()

    assert client.subscribe.call_args.args[0] == rutas.topico_cotizacion_registrada
    assert client.subscribe.call_args.kwargs["subscription_name"] == (
        rutas.suscripcion_cotizacion_registrada
    )
    assert client.subscribe.call_args.kwargs["consumer_type"].name == "Shared"
    assert isinstance(client.subscribe.call_args.kwargs["schema"], AvroSchema)


def test_rechazada_configura_topic_subscription_shared_y_schema(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr("pulsar.Client", Mock(return_value=client))
    consumidor = ConsumidorCotizacionRechazada(Mock())

    consumidor.conectar()

    assert client.subscribe.call_args.args[0] == rutas.topico_cotizacion_rechazada
    assert client.subscribe.call_args.kwargs["subscription_name"] == (
        rutas.suscripcion_cotizacion_rechazada
    )
    assert client.subscribe.call_args.kwargs["consumer_type"].name == "Shared"
    assert isinstance(client.subscribe.call_args.kwargs["schema"], AvroSchema)


def test_registrada_usa_value_mapper_y_handler_con_estado_aceptada() -> None:
    handler = Mock()
    consumidor = ConsumidorCotizacionRegistrada(lambda: handler)
    mensaje = Mock()
    mensaje.value.return_value = _registrada()

    consumidor._procesar_mensaje(Mock(), mensaje)

    mensaje.value.assert_called_once_with()
    comando = handler.ejecutar.call_args.args[0]
    assert comando.resultado.estado == "ACEPTADA"
    assert comando.resultado.id_trabajo == "trab-1"


def test_rechazada_usa_value_mapper_y_handler_con_estado_rechazada() -> None:
    handler = Mock()
    consumidor = ConsumidorCotizacionRechazada(lambda: handler)
    mensaje = Mock()
    mensaje.value.return_value = _rechazada()

    consumidor._procesar_mensaje(Mock(), mensaje)

    mensaje.value.assert_called_once_with()
    comando = handler.ejecutar.call_args.args[0]
    assert comando.resultado.estado == "RECHAZADA"
    assert comando.resultado.motivo == "SIN_OFERTA_PARA_CATEGORIA"


def test_consumers_de_resultados_no_hacen_ack_en_esta_etapa() -> None:
    for consumidor, record in (
        (ConsumidorCotizacionRegistrada(lambda: Mock()), _registrada()),
        (ConsumidorCotizacionRechazada(lambda: Mock()), _rechazada()),
    ):
        mensaje = Mock()
        mensaje.value.return_value = record

        consumidor._procesar_mensaje(Mock(), mensaje)

        mensaje.acknowledge.assert_not_called()