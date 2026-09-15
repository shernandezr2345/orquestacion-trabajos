import os
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from orquestacion_trabajos.config.bootstrap import componer_despacho
from orquestacion_trabajos.config.database import Database
from orquestacion_trabajos.config.persistencia import verificar_destinos
from orquestacion_trabajos.config.settings import Settings
from orquestacion_trabajos.modulos.trabajos.infraestructura.despacho import publicacion
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.orquestacion import (
    TrabajoCreadoV1,
)
from orquestacion_trabajos.seedwork.infraestructura.despacho_outbox import DespachadorOutbox
from orquestacion_trabajos.seedwork.infraestructura.orm import Base, OutboxORM
from orquestacion_trabajos.seedwork.infraestructura.publicador_pulsar import PublicadorPulsar


@pytest.fixture
def base():
    engine = create_engine(os.environ["ORQUESTACION_DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    database = Database(engine, sessionmaker(bind=engine))
    yield database
    database.close()


def add_output(base, destino="test", tipo="TrabajoCreado.v1"):
    with base.session_factory() as session:
        session.add(
            OutboxORM(
                tipo=tipo,
                destino=destino,
                payload={"event_id": "event", "id_trabajo": "work"},
                creado_en="now",
            )
        )
        session.commit()


@pytest.mark.parametrize("failure", ["send", "commit", None])
def test_send_and_mark_are_atomic_and_retry_uses_same_payload(base, failure):
    add_output(base)
    publish = Mock()

    class FailingSession(Session):
        pass

    sessions = sessionmaker(bind=base.engine, class_=FailingSession)

    def fail_commit(session):
        raise RuntimeError("commit failed")

    if failure == "send":
        publish.side_effect = RuntimeError("send failed")
    if failure == "commit":
        event.listen(FailingSession, "before_commit", fail_commit)
    dispatcher = DespachadorOutbox(sessions, "test", publish)
    if failure:
        with pytest.raises(RuntimeError):
            dispatcher.despachar_siguiente()
        with base.session_factory() as session:
            assert session.execute(select(OutboxORM.estado)).scalar_one() == "PENDIENTE"
        publish.side_effect = None
        if failure == "commit":
            event.remove(FailingSession, "before_commit", fail_commit)
    assert dispatcher.despachar_siguiente()
    with base.session_factory() as session:
        assert session.execute(select(OutboxORM.estado)).scalar_one() == "PROCESADA"
    assert not dispatcher.despachar_siguiente()
    assert all(call.args[1]["event_id"] == "event" for call in publish.call_args_list)


def test_destinations_are_independent_and_unknown_pending_destination_is_visible(base):
    add_output(base, "bad")
    add_output(base, "good")
    assert DespachadorOutbox(base.session_factory, "good", Mock()).despachar_siguiente()
    with base.session_factory() as session:
        assert (
            session.execute(select(OutboxORM.estado).where(OutboxORM.destino == "bad")).scalar_one()
            == "PENDIENTE"
        )
    with pytest.raises(ValueError, match="Unknown"):
        verificar_destinos(base, Settings())


@pytest.mark.parametrize(
    "tipo,identifier", [("TrabajoCreado.v1", "event_id"), ("SolicitarCotizacion.v1", "command_id")]
)
def test_both_outputs_use_work_key_and_stable_identity(tipo, identifier):
    publisher = Mock()
    payload = {identifier: "stable", "id_trabajo": "work"}
    publicacion(publisher)(tipo, payload)
    publisher.publicar.assert_called_once_with(
        payload, "work", {"tipo": tipo, identifier: "stable"}
    )


def test_publisher_opens_once_and_closes_client(monkeypatch):
    client = Mock()
    factory = Mock(return_value=client)
    monkeypatch.setattr("pulsar.Client", factory)
    publisher = PublicadorPulsar(
        "pulsar://localhost:6650",
        "persistent://public/default/test",
        Mock(),
        lambda payload: payload,
    )
    publisher.publicar({}, "key", {})
    publisher.publicar({}, "key", {})
    factory.assert_called_once()
    client.create_producer.assert_called_once()
    publisher.cerrar()
    client.close.assert_called_once()


def test_bootstrap_selects_avro_and_configured_destination(base, monkeypatch):
    client = Mock()
    monkeypatch.setattr("pulsar.Client", Mock(return_value=client))
    component = componer_despacho(
        base, Settings(pulsar_namespace="isolated"), "TrabajoCreado.v1", TrabajoCreadoV1
    )
    assert not component.paso()
    assert (
        client.create_producer.call_args.args[0] == "persistent://public/isolated/trabajo-creado-v1"
    )
    component.cerrar()
