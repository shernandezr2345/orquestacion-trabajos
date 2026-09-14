from __future__ import annotations

from unittest.mock import Mock

from config.rutas import rutas
from pulsar.schema import AvroSchema

from orquestacion_trabajos.infraestructura.despacho import DespachoOutbox
from orquestacion_trabajos.infraestructura.esquemas_python.v1.orquestacion import (
    SolicitarCotizacionV1,
    TrabajoCreadoV1,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import OutboxORM


def _trabajo_creado_payload() -> dict[str, object]:
    return {
        "event_id": "evt-1",
        "tipo": "TrabajoCreado.v1",
        "version_contrato": 1,
        "instante": "2026-09-13T00:00:00Z",
        "correlacion": "sol-1",
        "causacion": "evt-entrada",
        "id_trabajo": "trab-1",
        "id_solicitud": "sol-1",
        "id_partner": "partner-1",
        "id_peticion": "trab-1",
        "referencia_externa": "ref-1",
        "categoria": "SINIESTRO",
        "tipo_solicitud": "SINIESTRO",
        "tipo_red": "GENERAL_HDA",
        "id_politica": "pol-1",
        "version_politica": 1,
        "creado_en": "2026-09-13T00:00:00Z",
        "estado": "PENDIENTE_COTIZACION",
        "version_trabajo": 1,
    }


def _solicitar_cotizacion_payload() -> dict[str, object]:
    return {
        "command_id": "cmd-1",
        "tipo": "SolicitarCotizacion.v1",
        "version_contrato": 1,
        "instante": "2026-09-13T00:00:00Z",
        "correlacion": "sol-1",
        "causacion": "evt-entrada",
        "id_peticion": "trab-1",
        "id_trabajo": "trab-1",
        "id_solicitud": "sol-1",
        "id_partner": "partner-1",
        "categoria": "SINIESTRO",
        "tipo_solicitud": "SINIESTRO",
        "tipo_red": "GENERAL_HDA",
        "id_politica": "pol-1",
        "version_politica": 1,
    }


def _salida(tipo: str, payload: dict[str, object]) -> OutboxORM:
    return OutboxORM(
        id=1,
        tipo=tipo,
        destino="persistent://public/default/test",
        payload=payload,
        estado="PENDIENTE",
        creado_en="2026-09-13T00:00:00Z",
        procesado_en=None,
    )


def test_trabajo_creado_se_convierte_a_record_avro() -> None:
    salida = _salida("TrabajoCreado.v1", _trabajo_creado_payload())

    record = DespachoOutbox._record_para_salida(salida)

    assert isinstance(record, TrabajoCreadoV1)
    assert record.id_trabajo == "trab-1"
    assert record.estado == "PENDIENTE_COTIZACION"


def test_solicitar_cotizacion_se_convierte_a_record_avro() -> None:
    salida = _salida("SolicitarCotizacion.v1", _solicitar_cotizacion_payload())

    record = DespachoOutbox._record_para_salida(salida)

    assert isinstance(record, SolicitarCotizacionV1)
    assert record.id_trabajo == "trab-1"
    assert record.command_id == "cmd-1"


def test_producers_se_crean_una_vez_con_schema_y_destino_correctos(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr("pulsar.Client", Mock(return_value=client))
    dispatcher = DespachoOutbox(Mock())

    dispatcher.conectar()
    dispatcher.conectar()

    assert client.create_producer.call_count == 2
    calls = client.create_producer.call_args_list
    assert calls[0].args[0] == rutas.topico_solicitar_cotizacion
    assert isinstance(calls[0].kwargs["schema"], AvroSchema)
    assert calls[1].args[0] == rutas.topico_trabajo_creado
    assert isinstance(calls[1].kwargs["schema"], AvroSchema)


def test_publicar_salida_envia_record_y_marca_procesada_despues() -> None:
    producer = Mock()
    producer.send.return_value = "message-id"
    session = Mock()
    dispatcher = DespachoOutbox(Mock())
    dispatcher.producers["TrabajoCreado.v1"] = producer
    salida = _salida("TrabajoCreado.v1", _trabajo_creado_payload())

    dispatcher._publicar_salida(session, salida)

    enviado = producer.send.call_args.args[0]
    assert isinstance(enviado, TrabajoCreadoV1)
    assert producer.send.call_args.kwargs["partition_key"] == "trab-1"
    assert salida.estado == "PROCESADA"
    assert salida.procesado_en is not None
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_solicitar_cotizacion_envia_el_record_sin_alterar_y_con_partition_key() -> None:
    producer = Mock()
    producer.send.return_value = "message-id"
    session = Mock()
    dispatcher = DespachoOutbox(Mock())
    dispatcher.producers["SolicitarCotizacion.v1"] = producer
    payload = _solicitar_cotizacion_payload()
    salida = _salida("SolicitarCotizacion.v1", payload)

    dispatcher._publicar_salida(session, salida)

    enviado = producer.send.call_args.args[0]
    assert isinstance(enviado, SolicitarCotizacionV1)
    assert enviado.id_trabajo == payload["id_trabajo"]
    assert producer.send.call_args.kwargs["partition_key"] == payload["id_trabajo"]


def test_fallo_de_publicacion_hace_rollback_y_deja_pendiente() -> None:
    producer = Mock()
    producer.send.side_effect = RuntimeError("broker no disponible")
    session = Mock()
    dispatcher = DespachoOutbox(Mock())
    dispatcher.producers["TrabajoCreado.v1"] = producer
    salida = _salida("TrabajoCreado.v1", _trabajo_creado_payload())

    try:
        dispatcher._publicar_salida(session, salida)
    except RuntimeError:
        pass

    assert salida.estado == "PENDIENTE"
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def test_tipo_desconocido_no_se_marca_procesado() -> None:
    session = Mock()
    dispatcher = DespachoOutbox(Mock())
    salida = _salida("TipoDesconocido.v1", {"dato": "valor"})

    dispatcher._publicar_salida(session, salida)

    assert salida.estado == "PENDIENTE"
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_fallo_despues_de_send_hace_rollback_y_conserva_la_fila_pendiente() -> None:
    producer = Mock()
    producer.send.return_value = "message-id"
    session = Mock()
    session.commit.side_effect = RuntimeError("fallo al confirmar PROCESADA")
    dispatcher = DespachoOutbox(Mock())
    dispatcher.producers["TrabajoCreado.v1"] = producer
    salida = _salida("TrabajoCreado.v1", _trabajo_creado_payload())

    try:
        dispatcher._publicar_salida(session, salida)
    except RuntimeError:
        pass

    producer.send.assert_called_once()
    session.rollback.assert_called_once()


def test_salidas_se_procesan_independientemente() -> None:
    trabajo_producer = Mock()
    trabajo_producer.send.side_effect = RuntimeError("fallo TrabajoCreado")
    cotizacion_producer = Mock()
    cotizacion_producer.send.return_value = "message-id"
    dispatcher = DespachoOutbox(Mock())
    dispatcher.producers = {
        "TrabajoCreado.v1": trabajo_producer,
        "SolicitarCotizacion.v1": cotizacion_producer,
    }
    first = _salida("TrabajoCreado.v1", _trabajo_creado_payload())
    second = _salida("SolicitarCotizacion.v1", _solicitar_cotizacion_payload())
    session = Mock()

    for salida in (first, second):
        try:
            dispatcher._publicar_salida(session, salida)
        except RuntimeError:
            pass

    assert first.estado == "PENDIENTE"
    assert second.estado == "PROCESADA"
    cotizacion_producer.send.assert_called_once()
