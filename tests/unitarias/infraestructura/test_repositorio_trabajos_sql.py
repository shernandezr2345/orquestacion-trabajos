from __future__ import annotations

import uuid

import pytest
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import sessionmaker

from orquestacion_trabajos.config.settings import Settings

settings = Settings.from_environment()
from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    CrearTrabajoCommand,
    SolicitudListaParaAtencion,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base, TrabajoORM
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyRepositorioTrabajos,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.unidad_trabajo import (
    UnidadTrabajoTrabajosSQL,
)
from orquestacion_trabajos.seedwork.infraestructura.inbox import InboxConflictError, SqlAlchemyInbox
from orquestacion_trabajos.seedwork.infraestructura.orm import InboxORM, OutboxORM
from orquestacion_trabajos.seedwork.infraestructura.outbox import SqlAlchemyOutbox


def _engine_postgresql() -> Engine:
    assert settings.database_url is not None
    engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine


def _trabajo_para_prueba(id_solicitud: str) -> Trabajo:
    return Trabajo.crear(
        origen=OrigenSolicitud(
            id_solicitud=id_solicitud,
            id_partner="partner-1",
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
            referencia_externa="ref-001",
            id_politica="politica-1",
            version_politica=1,
        ),
        condiciones=CondicionesAtencion(
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
        ),
    )


def _solicitud() -> SolicitudListaParaAtencion:
    return SolicitudListaParaAtencion(
        event_id="evt-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        referencia_externa="ref-001",
        id_politica="politica-1",
        version_politica=1,
    )


def test_repositorio_trabajos_guarda_y_reconstruye() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    solicitud = _solicitud()
    trabajo = Trabajo.crear(
        origen=OrigenSolicitud(
            id_solicitud=solicitud.id_solicitud,
            id_partner=solicitud.id_partner,
            categoria=solicitud.categoria,
            tipo_solicitud=solicitud.tipo_solicitud,
            tipo_red=solicitud.tipo_red,
            referencia_externa=solicitud.referencia_externa,
            id_politica=solicitud.id_politica,
            version_politica=solicitud.version_politica,
        ),
        condiciones=CondicionesAtencion(
            categoria=solicitud.categoria,
            tipo_solicitud=solicitud.tipo_solicitud,
            tipo_red=solicitud.tipo_red,
        ),
    )

    with Session() as session:
        repo = SqlAlchemyRepositorioTrabajos(session)
        repo.guardar(trabajo)
        resultado = repo.obtener_por_id(str(trabajo.id))

    assert resultado is not None
    assert resultado.id_solicitud == solicitud.id_solicitud
    assert resultado.version == 1
    assert resultado.estado.value == "PENDIENTE_COTIZACION"


def test_uow_commit_atomico_persiste_trabajo_inbox_y_outbox() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    message_id = f"msg-{uuid.uuid4()}"
    consumer = f"consumer-{uuid.uuid4()}"
    id_solicitud = f"sol-{uuid.uuid4()}"

    with UnidadTrabajoTrabajosSQL(Session, {}) as uow:
        session = uow.sesion
        repo = uow.trabajos
        inbox = SqlAlchemyInbox(session)
        outbox = SqlAlchemyOutbox(session)

        trabajo = _trabajo_para_prueba(id_solicitud)
        repo.guardar(trabajo)
        inbox.registrar(
            consumidor=consumer,
            id_mensaje=message_id,
            contenido='{"evento":"TrabajoCreado.v1"}',
        )
        outbox.registrar(
            tipo="TrabajoCreado.v1",
            payload={"id_trabajo": str(trabajo.id), "id_solicitud": id_solicitud},
            destino="trabajos",
        )
        uow.confirmar()

    with Session() as session:
        trabajo_row = session.get(TrabajoORM, str(trabajo.id))
        inbox_row = session.execute(
            select(InboxORM).where(
                (InboxORM.consumidor == consumer) & (InboxORM.id_mensaje == message_id)
            )
        ).scalar_one_or_none()
        outbox_rows = (
            session.execute(select(OutboxORM).where(OutboxORM.tipo == "TrabajoCreado.v1"))
            .scalars()
            .all()
        )

    assert trabajo_row is not None
    assert inbox_row is not None
    assert any(
        row.payload.get("id_trabajo") == str(trabajo.id) and row.estado == "PENDIENTE"
        for row in outbox_rows
    )


def test_uow_rollback_atomico_deshace_trabajo_inbox_y_outbox() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    message_id = f"msg-{uuid.uuid4()}"
    consumer = f"consumer-{uuid.uuid4()}"
    id_solicitud = f"sol-{uuid.uuid4()}"

    with UnidadTrabajoTrabajosSQL(Session, {}) as uow:
        session = uow.sesion
        repo = uow.trabajos
        inbox = SqlAlchemyInbox(session)
        outbox = SqlAlchemyOutbox(session)

        trabajo = _trabajo_para_prueba(id_solicitud)
        repo.guardar(trabajo)
        inbox.registrar(
            consumidor=consumer,
            id_mensaje=message_id,
            contenido='{"evento":"rollback"}',
        )
        outbox.registrar(
            tipo="TrabajoCreado.v1",
            payload={"id_trabajo": str(trabajo.id), "id_solicitud": id_solicitud},
            destino="trabajos",
        )
        uow.revertir()

    with Session() as session:
        trabajo_row = session.get(TrabajoORM, str(trabajo.id))
        inbox_row = session.execute(
            select(InboxORM).where(
                (InboxORM.consumidor == consumer) & (InboxORM.id_mensaje == message_id)
            )
        ).scalar_one_or_none()
        outbox_rows = session.execute(select(OutboxORM)).scalars().all()

    assert trabajo_row is None
    assert inbox_row is None
    assert outbox_rows == []


def test_inbox_real_mismo_id_y_contenido_no_crea_dos_registros() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    consumer = f"consumer-{uuid.uuid4()}"
    message_id = f"msg-{uuid.uuid4()}"
    contenido = '{"evento":"duplicado"}'

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        inbox.registrar(consumidor=consumer, id_mensaje=message_id, contenido=contenido)
        session.commit()

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        inbox.registrar(consumidor=consumer, id_mensaje=message_id, contenido=contenido)

    with Session() as session:
        rows = (
            session.execute(
                select(InboxORM).where(
                    (InboxORM.consumidor == consumer) & (InboxORM.id_mensaje == message_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].contenido == contenido


def test_inbox_real_mismo_id_y_contenido_distinto_genera_conflicto() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    consumer = f"consumer-{uuid.uuid4()}"
    message_id = f"msg-{uuid.uuid4()}"
    contenido_original = '{"a":1}'
    contenido_distinto = '{"a":2}'

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        inbox.registrar(consumidor=consumer, id_mensaje=message_id, contenido=contenido_original)
        session.commit()

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        with pytest.raises(InboxConflictError, match="Conflito de inbox"):
            inbox.registrar(
                consumidor=consumer, id_mensaje=message_id, contenido=contenido_distinto
            )

    with Session() as session:
        row = session.execute(
            select(InboxORM).where(
                (InboxORM.consumidor == consumer) & (InboxORM.id_mensaje == message_id)
            )
        ).scalar_one()
        assert row.contenido == contenido_original


def test_inbox_real_distinto_consumidor_mismo_mensaje_puede_registrarse() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    message_id = f"msg-{uuid.uuid4()}"
    contenido = '{"evento":"duplicado"}'

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        inbox.registrar(consumidor="consumer-a", id_mensaje=message_id, contenido=contenido)
        session.commit()

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        inbox.registrar(consumidor="consumer-b", id_mensaje=message_id, contenido=contenido)
        session.commit()

    with Session() as session:
        rows = (
            session.execute(select(InboxORM).where(InboxORM.id_mensaje == message_id))
            .scalars()
            .all()
        )
        assert len(rows) == 2
        assert {row.consumidor for row in rows} == {"consumer-a", "consumer-b"}


def test_inbox_registrar_no_hace_commit_ni_rollback_por_si_mismo() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    consumer = "consumer-x"
    message_id = "msg-x"
    contenido = '{"evento":"pending"}'

    with Session() as session:
        inbox = SqlAlchemyInbox(session)
        inbox.registrar(consumidor=consumer, id_mensaje=message_id, contenido=contenido)
        assert (
            session.execute(
                select(InboxORM).where(
                    (InboxORM.consumidor == consumer) & (InboxORM.id_mensaje == message_id)
                )
            ).scalar_one_or_none()
            is not None
        )

        session.rollback()
        assert (
            session.execute(
                select(InboxORM).where(
                    (InboxORM.consumidor == consumer) & (InboxORM.id_mensaje == message_id)
                )
            ).scalar_one_or_none()
            is None
        )


def test_outbox_real_persiste_salida_pendiente() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    payload = {"id_trabajo": "t-123", "estado": "PENDIENTE"}

    with Session() as session:
        outbox = SqlAlchemyOutbox(session)
        outbox.registrar(tipo="TrabajoCreado.v1", payload=payload, destino="trabajos")
        session.commit()

    with Session() as session:
        row = session.execute(
            select(OutboxORM).where(OutboxORM.tipo == "TrabajoCreado.v1")
        ).scalar_one()

    assert row is not None
    assert row.destino == "trabajos"
    assert row.payload == payload
    assert row.estado == "PENDIENTE"


def test_handler_confirms_work_inbox_and_both_outputs():
    engine = _engine_postgresql()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    destinos = {"TrabajoCreado.v1": "creado", "SolicitarCotizacion.v1": "peticion"}
    handler = CrearTrabajoHandler(lambda: UnidadTrabajoTrabajosSQL(sessions, destinos))
    comando = CrearTrabajoCommand(_solicitud())
    trabajo = handler.ejecutar(comando)
    handler.ejecutar(comando)
    with sessions() as session:
        assert session.get(TrabajoORM, str(trabajo.id)) is not None
        assert len(session.execute(select(InboxORM)).scalars().all()) == 1
        assert {row.tipo for row in session.execute(select(OutboxORM)).scalars()} == set(destinos)


def test_unidad_trabajo_confirma_y_revertir() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with UnidadTrabajoTrabajosSQL(Session, {}) as uow:
        uow.confirmar()
        uow.revertir()

    assert True


def test_uow_commit_persiste_en_sesion_nueva() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    id_solicitud = f"sol-{uuid.uuid4()}"

    with UnidadTrabajoTrabajosSQL(Session, {}) as uow:
        repo = uow.trabajos
        trabajo = _trabajo_para_prueba(id_solicitud)
        repo.guardar(trabajo)
        uow.confirmar()

    with Session() as session:
        row = session.get(TrabajoORM, str(trabajo.id))
        assert row is not None
        assert row.id_solicitud == id_solicitud
        assert row.estado == "PENDIENTE_COTIZACION"


def test_uow_rollback_deshace_cambios() -> None:
    engine = _engine_postgresql()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    id_solicitud = f"sol-{uuid.uuid4()}"

    with UnidadTrabajoTrabajosSQL(Session, {}) as uow:
        repo = uow.trabajos
        trabajo = _trabajo_para_prueba(id_solicitud)
        repo.guardar(trabajo)
        try:
            raise RuntimeError("error de negocio intencional")
        except RuntimeError:
            uow.revertir()

    with Session() as session:
        row = session.get(TrabajoORM, str(trabajo.id))
        assert row is None


def test_concurrent_result_updates_preserve_first_commit() -> None:
    from dataclasses import replace

    from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import ResultadoCotizacion

    engine = _engine_postgresql()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    work = _trabajo_para_prueba("concurrent-request")
    with sessions() as session:
        SqlAlchemyRepositorioTrabajos(session).guardar(work)
        session.commit()
    with sessions() as first, sessions() as second:
        first_repo = SqlAlchemyRepositorioTrabajos(first)
        second_repo = SqlAlchemyRepositorioTrabajos(second)
        first_work = first_repo.obtener_por_id(str(work.id))
        second_work = second_repo.obtener_por_id(str(work.id))
        assert first_work is not None and second_work is not None
        original = ResultadoCotizacion(
            id_trabajo=str(work.id),
            id_solicitud=work.id_solicitud,
            id_partner=work.id_partner,
            id_peticion=str(work.id),
            id_cotizacion="quote",
            id_proveedor="provider",
            estado="ACEPTADA",
            categoria=work.categoria,
            tipo_red=work.tipo_red,
            importe_menor=100,
            moneda="COP",
        )
        first_work.aplicar_resultado(original)
        second_work.aplicar_resultado(replace(original, importe_menor=200))
        first_repo.guardar(first_work)
        first.commit()
        with pytest.raises(RuntimeError, match="[Cc]oncurr"):
            second_repo.guardar(second_work)
            second.commit()
        second.rollback()
    with sessions() as session:
        saved = SqlAlchemyRepositorioTrabajos(session).obtener_por_id(str(work.id))
        assert saved is not None and saved.resultado == original
    engine.dispose()


@pytest.mark.parametrize("accepted", [True, False])
def test_result_transaction_is_durable_and_replay_preserves_version(accepted):
    from dataclasses import replace

    from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
        AplicarCotizacionCommand,
        ResultadoCotizacionEntrada,
    )
    from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
        AplicarCotizacionHandler,
    )

    engine = _engine_postgresql()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    destinations = {"TrabajoCreado.v1": "creado", "SolicitarCotizacion.v1": "peticion"}
    factory = lambda: UnidadTrabajoTrabajosSQL(sessions, destinations)
    work = CrearTrabajoHandler(factory).ejecutar(CrearTrabajoCommand(_solicitud()))
    result = ResultadoCotizacionEntrada(
        event_id="result",
        id_trabajo=str(work.id),
        id_solicitud=work.id_solicitud,
        id_partner=work.id_partner,
        id_peticion=str(work.id),
        id_cotizacion="quote" if accepted else "",
        id_proveedor="provider" if accepted else "",
        estado="ACEPTADA" if accepted else "RECHAZADA",
        categoria=work.categoria,
        tipo_red=work.tipo_red,
        importe_menor=100 if accepted else None,
        moneda="COP" if accepted else None,
        motivo=None if accepted else "SIN_OFERTA_PARA_CATEGORIA",
    )
    handler = AplicarCotizacionHandler(factory)
    handler.ejecutar(AplicarCotizacionCommand(result))
    handler.ejecutar(AplicarCotizacionCommand(result))
    with pytest.raises(InboxConflictError):
        handler.ejecutar(AplicarCotizacionCommand(result, contenido="changed envelope"))
    incompatible = replace(result, event_id="foreign", id_peticion="foreign")
    from orquestacion_trabajos.modulos.trabajos.dominio.excepciones import CotizacionAjenaError

    with pytest.raises(CotizacionAjenaError):
        handler.ejecutar(AplicarCotizacionCommand(incompatible))
    with sessions() as session:
        assert session.get(TrabajoORM, str(work.id)).version == 2
        assert len(session.execute(select(InboxORM)).scalars().all()) == 2
        assert len(session.execute(select(OutboxORM)).scalars().all()) == 2


def test_failed_output_registration_rolls_back_sql_work_and_inbox():
    engine = _engine_postgresql()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    handler = CrearTrabajoHandler(
        lambda: UnidadTrabajoTrabajosSQL(sessions, {"TrabajoCreado.v1": "creado"})
    )
    with pytest.raises(KeyError):
        handler.ejecutar(CrearTrabajoCommand(_solicitud()))
    with sessions() as session:
        for model in (TrabajoORM, InboxORM, OutboxORM):
            assert session.execute(select(model)).scalars().all() == []
