from __future__ import annotations

from unittest.mock import Mock

import pytest
from config.database import engine
from config.rutas import rutas
from pulsar.schema import AvroSchema
from sqlalchemy.orm import sessionmaker

from orquestacion_trabajos.infraestructura.consumidores import (
    ConsumidorCotizacionRechazada,
    ConsumidorCotizacionRegistrada,
)
from orquestacion_trabajos.infraestructura.esquemas_python.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.idempotencia import InMemoryIdempotencia
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import (
    Base,
    InboxORM,
    OutboxORM,
    TrabajoORM,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    InboxConflictError,
    SqlAlchemyOutbox,
    SqlAlchemyRepositorioTrabajos,
)


def _registrada(
    id_trabajo: str = "trab-1",
    event_id: str = "evt-1",
    importe_menor: int = 15000000,
    id_solicitud: str = "sol-1",
) -> CotizacionRegistradaV1:
    return CotizacionRegistradaV1(
        event_id=event_id,
        instante="2026-09-13T00:00:00Z",
        correlacion=id_solicitud,
        causacion="cmd-1",
        id_peticion="pet-1",
        id_trabajo=id_trabajo,
        id_solicitud=id_solicitud,
        id_partner="partner-1",
        id_cotizacion="cot-1",
        id_proveedor="prov-1",
        categoria="SINIESTRO",
        tipo_red="GENERAL_HDA",
        importe_menor=importe_menor,
        moneda="COP",
        version_catalogo=1,
    )


def _rechazada(
    id_trabajo: str = "trab-1", event_id: str = "evt-2", id_solicitud: str = "sol-1"
) -> CotizacionRechazadaV1:
    return CotizacionRechazadaV1(
        event_id=event_id,
        instante="2026-09-13T00:00:00Z",
        correlacion=id_solicitud,
        causacion="cmd-1",
        id_peticion="pet-1",
        id_trabajo=id_trabajo,
        id_solicitud=id_solicitud,
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
    consumidor = ConsumidorCotizacionRegistrada(Mock(), Mock())

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
    consumidor = ConsumidorCotizacionRechazada(Mock(), Mock())

    consumidor.conectar()

    assert client.subscribe.call_args.args[0] == rutas.topico_cotizacion_rechazada
    assert client.subscribe.call_args.kwargs["subscription_name"] == (
        rutas.suscripcion_cotizacion_rechazada
    )
    assert client.subscribe.call_args.kwargs["consumer_type"].name == "Shared"
    assert isinstance(client.subscribe.call_args.kwargs["schema"], AvroSchema)


class _ResultDouble:
    def scalar_one_or_none(self):
        return None


class _SessionDouble:
    def __init__(
        self, orden: list[str] | None = None, commit_error: Exception | None = None
    ) -> None:
        self.orden = orden if orden is not None else []
        self.commit_error = commit_error
        self.rollbacks = 0

    def execute(self, _statement):
        return _ResultDouble()

    def add(self, _entity) -> None:
        return None

    def commit(self) -> None:
        self.orden.append("commit")
        if self.commit_error is not None:
            raise self.commit_error

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        return None


def _session_factory():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _guardar_trabajo(session_factory, id_solicitud: str = "sol-1") -> Trabajo:
    trabajo = Trabajo.crear(
        OrigenSolicitud(
            id_solicitud=id_solicitud,
            id_partner="partner-1",
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
            referencia_externa=f"ref-{id_solicitud}",
            id_politica="pol-1",
            version_politica=1,
        ),
        CondicionesAtencion(
            categoria="SINIESTRO", tipo_solicitud="SINIESTRO", tipo_red="GENERAL_HDA"
        ),
    )
    with session_factory() as session:
        SqlAlchemyRepositorioTrabajos(session).guardar(trabajo)
        session.commit()
    return trabajo


def _handler_factory(session):
    return AplicarCotizacionHandler(
        SqlAlchemyRepositorioTrabajos(session), SqlAlchemyOutbox(session), InMemoryIdempotencia()
    )


def test_registrada_usa_value_mapper_y_handler_con_estado_aceptada() -> None:
    handler = Mock()
    session = _SessionDouble()
    consumidor = ConsumidorCotizacionRegistrada(lambda: session, lambda _: handler)
    mensaje = Mock()
    mensaje.value.return_value = _registrada()

    consumidor._procesar_mensaje(Mock(), mensaje)

    mensaje.value.assert_called_once_with()
    comando = handler.ejecutar.call_args.args[0]
    assert comando.resultado.estado == "ACEPTADA"
    assert comando.resultado.id_trabajo == "trab-1"


def test_rechazada_usa_value_mapper_y_handler_con_estado_rechazada() -> None:
    handler = Mock()
    session = _SessionDouble()
    consumidor = ConsumidorCotizacionRechazada(lambda: session, lambda _: handler)
    mensaje = Mock()
    mensaje.value.return_value = _rechazada()

    consumidor._procesar_mensaje(Mock(), mensaje)

    mensaje.value.assert_called_once_with()
    comando = handler.ejecutar.call_args.args[0]
    assert comando.resultado.estado == "RECHAZADA"
    assert comando.resultado.motivo == "SIN_OFERTA_PARA_CATEGORIA"


def test_registrada_persiste_inbox_trabajo_outbox_y_hace_ack() -> None:
    session_factory = _session_factory()
    trabajo = _guardar_trabajo(session_factory)
    consumer = Mock()
    mensaje = Mock()
    record = _registrada(str(trabajo.id))
    mensaje.value.return_value = record

    ConsumidorCotizacionRegistrada(session_factory, _handler_factory)._procesar_mensaje(
        consumer, mensaje
    )

    with session_factory() as session:
        assert session.get(TrabajoORM, str(trabajo.id)).estado == "COTIZADO"
        assert session.query(InboxORM).one().id_mensaje == record.event_id
        assert session.query(OutboxORM).one().tipo == "CotizacionAplicada"
    consumer.acknowledge.assert_called_once_with(mensaje)


def test_rechazada_persiste_inbox_trabajo_outbox_y_hace_ack() -> None:
    session_factory = _session_factory()
    trabajo = _guardar_trabajo(session_factory)
    consumer = Mock()
    mensaje = Mock()
    record = _rechazada(str(trabajo.id))
    mensaje.value.return_value = record

    ConsumidorCotizacionRechazada(session_factory, _handler_factory)._procesar_mensaje(
        consumer, mensaje
    )

    with session_factory() as session:
        assert session.get(TrabajoORM, str(trabajo.id)).estado == "COTIZACION_RECHAZADA"
        assert session.query(InboxORM).one().id_mensaje == record.event_id
        assert session.query(OutboxORM).one().tipo == "CotizacionAplicada"
    consumer.acknowledge.assert_called_once_with(mensaje)


def test_inbox_y_handler_reciben_la_misma_session_y_commit_precede_ack(monkeypatch) -> None:
    orden: list[str] = []
    session = _SessionDouble(orden)
    handler = Mock()
    handler.ejecutar.side_effect = lambda _: orden.append("handler")
    sesiones_inbox: list[object] = []

    class InboxDouble:
        def __init__(self, inbox_session) -> None:
            sesiones_inbox.append(inbox_session)

        def ya_procesado(self, **_kwargs) -> bool:
            return False

        def registrar(self, **_kwargs) -> None:
            return None

    monkeypatch.setattr(
        "orquestacion_trabajos.infraestructura.consumidores.SqlAlchemyInbox", InboxDouble
    )
    consumer = Mock()
    consumer.acknowledge.side_effect = lambda _: orden.append("ack")
    mensaje = Mock()
    mensaje.value.return_value = _registrada()

    ConsumidorCotizacionRegistrada(lambda: session, lambda received: handler)._procesar_mensaje(
        consumer, mensaje
    )

    assert sesiones_inbox == [session]
    assert handler is not None
    assert orden == ["handler", "commit", "ack"]


def test_error_del_handler_hace_rollback_sin_efectos_parciales_ni_ack() -> None:
    session_factory = _session_factory()
    trabajo = _guardar_trabajo(session_factory)
    handler = Mock()
    handler.ejecutar.side_effect = RuntimeError("fallo de negocio")
    consumer = Mock()
    mensaje = Mock()
    mensaje.value.return_value = _registrada(str(trabajo.id))
    consumidor = ConsumidorCotizacionRegistrada(session_factory, lambda _: handler)

    with pytest.raises(RuntimeError, match="fallo de negocio"):
        consumidor._procesar_mensaje(consumer, mensaje)

    with session_factory() as session:
        assert session.get(TrabajoORM, str(trabajo.id)).estado == "PENDIENTE_COTIZACION"
        assert session.query(InboxORM).count() == 0
        assert session.query(OutboxORM).count() == 0
    consumer.acknowledge.assert_not_called()


def test_error_de_commit_hace_rollback_y_no_ack() -> None:
    session = _SessionDouble(commit_error=RuntimeError("commit fallido"))
    handler = Mock()
    consumer = Mock()
    mensaje = Mock()
    mensaje.value.return_value = _registrada()

    with pytest.raises(RuntimeError, match="commit fallido"):
        ConsumidorCotizacionRegistrada(lambda: session, lambda _: handler)._procesar_mensaje(
            consumer, mensaje
        )

    assert session.rollbacks == 1
    consumer.acknowledge.assert_not_called()


def test_redelivery_no_repite_efecto_y_hace_ack() -> None:
    session_factory = _session_factory()
    trabajo = _guardar_trabajo(session_factory)
    record = _registrada(str(trabajo.id))
    consumidor = ConsumidorCotizacionRegistrada(session_factory, _handler_factory)

    for _ in range(2):
        consumer = Mock()
        mensaje = Mock()
        mensaje.value.return_value = record
        consumidor._procesar_mensaje(consumer, mensaje)
        consumer.acknowledge.assert_called_once_with(mensaje)

    with session_factory() as session:
        assert session.get(TrabajoORM, str(trabajo.id)).version == 2
        assert session.query(InboxORM).count() == 1
        assert session.query(OutboxORM).count() == 1


def test_conflicto_inbox_no_ejecuta_negocio_ni_hace_ack() -> None:
    session_factory = _session_factory()
    trabajo = _guardar_trabajo(session_factory)
    consumidor = ConsumidorCotizacionRegistrada(session_factory, _handler_factory)
    primero = Mock()
    primero.value.return_value = _registrada(str(trabajo.id), event_id="evt-conflicto")
    consumidor._procesar_mensaje(Mock(), primero)
    segundo_consumer = Mock()
    segundo = Mock()
    segundo.value.return_value = _registrada(
        str(trabajo.id), event_id="evt-conflicto", importe_menor=16000000
    )

    with pytest.raises(InboxConflictError):
        consumidor._procesar_mensaje(segundo_consumer, segundo)

    with session_factory() as session:
        assert session.get(TrabajoORM, str(trabajo.id)).version == 2
        assert session.query(InboxORM).count() == 1
        assert session.query(OutboxORM).count() == 1
    segundo_consumer.acknowledge.assert_not_called()


def test_consumidores_independientes_aceptan_mismo_event_id() -> None:
    session_factory = _session_factory()
    trabajo_registrado = _guardar_trabajo(session_factory, "sol-registrada")
    trabajo_rechazado = _guardar_trabajo(session_factory, "sol-rechazada")
    event_id = "evt-compartido"
    registrado = Mock()
    registrado.value.return_value = _registrada(
        str(trabajo_registrado.id), event_id, id_solicitud="sol-registrada"
    )
    rechazado = Mock()
    rechazado.value.return_value = _rechazada(
        str(trabajo_rechazado.id), event_id, id_solicitud="sol-rechazada"
    )

    ConsumidorCotizacionRegistrada(session_factory, _handler_factory)._procesar_mensaje(
        Mock(), registrado
    )
    ConsumidorCotizacionRechazada(session_factory, _handler_factory)._procesar_mensaje(
        Mock(), rechazado
    )

    with session_factory() as session:
        filas = session.query(InboxORM).filter_by(id_mensaje=event_id).all()
        assert {fila.consumidor for fila in filas} == {
            rutas.suscripcion_cotizacion_registrada,
            rutas.suscripcion_cotizacion_rechazada,
        }
