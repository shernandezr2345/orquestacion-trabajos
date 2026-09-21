from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from orquestacion_trabajos.config.settings import Settings
from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaInstance,
    SagaLog,
    SagaLogResultado,
    SagaLogTipoRegistro,
    SagaStatus,
    SagaStepName,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.orm import SagaInstanceORM, SagaLogORM
from orquestacion_trabajos.modulos.sagas.infraestructura.repositorios import (
    SagaConcurrencyConflictError,
    SqlAlchemyRepositorioSagaLog,
    SqlAlchemyRepositorioSagas,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.unidad_trabajo import (
    UnidadTrabajoSagasSQL,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base

settings = Settings.from_environment()


def _engine_postgresql() -> Engine:
    if settings.database_url:
        engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return engine


def _crear_saga(id_solicitud: str) -> SagaInstance:
    return SagaInstance.crear(id_solicitud=id_solicitud)


def _crear_log(
    *,
    id_saga: str,
    id_solicitud: str,
    paso: str,
    tipo_registro: SagaLogTipoRegistro,
    resultado: SagaLogResultado,
    tipo_mensaje: str | None = None,
    event_id: str | None = None,
    command_id: str | None = None,
    estado_anterior: SagaStatus | None = None,
    estado_nuevo: SagaStatus | None = None,
    created_at: str | None = None,
) -> SagaLog:
    return SagaLog(
        log_id=str(uuid4()),
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=None,
        paso=paso,
        tipo_registro=tipo_registro,
        tipo_mensaje=tipo_mensaje,
        event_id=event_id,
        command_id=command_id,
        causacion=None,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        resultado=resultado,
        detalle=None,
        created_at=created_at or SagaLog.now_iso(),
    )


def test_01_crear_saga_inicial_con_campos_por_defecto() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-001")
        repo.crear(saga)
        session.commit()

    with SessionFactory() as session:
        row = session.get(SagaInstanceORM, saga.id_saga)

    assert row is not None
    assert row.estado == SagaStatus.RUNNING.value
    assert row.id_trabajo is None
    assert row.seguimiento_apertura_solicitada is False
    assert row.seguimiento_abierto_confirmado is False


def test_02_asignar_id_trabajo_posteriormente() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-002")
        repo.crear(saga)
        session.commit()

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga_loaded = repo.obtener_por_id_solicitud("sol-002")
        assert saga_loaded is not None
        repo.asignar_id_trabajo(saga_loaded, "trab-002")
        session.commit()

    with SessionFactory() as session:
        row = session.get(SagaInstanceORM, saga.id_saga)

    assert row is not None
    assert row.id_trabajo == "trab-002"


def test_03_marcar_apertura_solicitada_no_confirma_apertura() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-003")
        repo.crear(saga)
        session.commit()

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga_loaded = repo.obtener_por_id_solicitud("sol-003")
        assert saga_loaded is not None
        repo.marcar_seguimiento_apertura_solicitada(saga_loaded)
        session.commit()

    with SessionFactory() as session:
        row = session.get(SagaInstanceORM, saga.id_saga)

    assert row is not None
    assert row.seguimiento_apertura_solicitada is True
    assert row.seguimiento_abierto_confirmado is False


def test_04_marcar_apertura_confirmada_respeta_regla_consistencia() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-004")
        repo.crear(saga)
        session.commit()

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga_loaded = repo.obtener_por_id_solicitud("sol-004")
        assert saga_loaded is not None
        repo.marcar_seguimiento_abierto_confirmado(saga_loaded)
        session.commit()

    with SessionFactory() as session:
        row = session.get(SagaInstanceORM, saga.id_saga)

    assert row is not None
    assert row.seguimiento_abierto_confirmado is True
    assert row.seguimiento_apertura_solicitada is True


def test_05_registrar_saga_log_event_received() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-005")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SolicitudDePartnerListaParaAtencion.v1",
                event_id="EVT-005",
            )
        )
        session.commit()

    with SessionFactory() as session:
        rows = session.query(SagaLogORM).all()

    assert len(rows) == 1
    assert rows[0].tipo_registro == SagaLogTipoRegistro.EVENT_RECEIVED.value


def test_06_registrar_saga_log_command_emitted() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-006")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=SagaStepName.SOLICITAR_COTIZACION.value,
                tipo_registro=SagaLogTipoRegistro.COMMAND_EMITTED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SolicitarCotizacion.v1",
                command_id="CMD-006",
            )
        )
        session.commit()

    with SessionFactory() as session:
        row = session.query(SagaLogORM).one()

    assert row.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED.value


def test_07_registrar_state_changed_running_a_compensating() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-007")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=SagaStepName.INICIAR_COMPENSACION_APERTURA.value,
                tipo_registro=SagaLogTipoRegistro.STATE_CHANGED,
                resultado=SagaLogResultado.APPLIED,
                estado_anterior=SagaStatus.RUNNING,
                estado_nuevo=SagaStatus.COMPENSATING,
            )
        )
        session.commit()

    with SessionFactory() as session:
        row = session.query(SagaLogORM).one()

    assert row.estado_anterior == SagaStatus.RUNNING.value
    assert row.estado_nuevo == SagaStatus.COMPENSATING.value


def test_08_listar_logs_por_saga_ordenados_cronologicamente() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-008")
        saga_repo.crear(saga)

        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                event_id="EVT-008-A",
                created_at="2026-09-20T10:00:00Z",
            )
        )
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=SagaStepName.SOLICITAR_COTIZACION.value,
                tipo_registro=SagaLogTipoRegistro.COMMAND_EMITTED,
                resultado=SagaLogResultado.APPLIED,
                command_id="CMD-008-B",
                created_at="2026-09-20T10:00:01Z",
            )
        )
        session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        logs = log_repo.listar_por_saga(saga.id_saga)

    assert [log.created_at for log in logs] == [
        "2026-09-20T10:00:00Z",
        "2026-09-20T10:00:01Z",
    ]


def test_09_unique_id_solicitud_no_permite_dos_sagas() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        repo.crear(_crear_saga("sol-009"))
        repo.crear(_crear_saga("sol-009"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_10_saga_log_append_only_en_repositorio() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-010")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                event_id="EVT-010-A",
            )
        )
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.DUPLICATE,
                resultado=SagaLogResultado.NO_OP_DUPLICATE,
                event_id="EVT-010-A",
            )
        )
        session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        logs = log_repo.listar_por_saga(saga.id_saga)

    assert len(logs) == 2
    assert not hasattr(SqlAlchemyRepositorioSagaLog, "actualizar")
    assert not hasattr(SqlAlchemyRepositorioSagaLog, "eliminar")


def test_11_conflicto_concurrencia_por_version() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-011")
        repo.crear(saga)
        session.commit()

    session_a: Session = SessionFactory()
    session_b: Session = SessionFactory()
    try:
        repo_a = SqlAlchemyRepositorioSagas(session_a)
        repo_b = SqlAlchemyRepositorioSagas(session_b)

        saga_a = repo_a.obtener_por_id_solicitud("sol-011")
        saga_b = repo_b.obtener_por_id_solicitud("sol-011")
        assert saga_a is not None
        assert saga_b is not None

        repo_a.actualizar_paso(saga_a, SagaStepName.SOLICITAR_COTIZACION)
        session_a.commit()

        with pytest.raises(SagaConcurrencyConflictError):
            repo_b.actualizar_estado(saga_b, SagaStatus.COMPENSATING)
    finally:
        session_a.close()
        session_b.close()


def test_12_busqueda_saga_por_id_saga_e_id_solicitud() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-012")
        repo.crear(saga)
        session.commit()

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        by_id = repo.obtener_por_id_saga(saga.id_saga)
        by_solicitud = repo.obtener_por_id_solicitud("sol-012")

    assert by_id is not None
    assert by_solicitud is not None
    assert by_id.id_saga == by_solicitud.id_saga


def test_13_buscar_por_message_id_en_saga_log() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-013")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=SagaStepName.SOLICITAR_COTIZACION.value,
                tipo_registro=SagaLogTipoRegistro.COMMAND_EMITTED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SolicitarCotizacion.v1",
                command_id="CMD-013",
            )
        )
        session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        row = log_repo.buscar_por_message_id(
            id_saga=saga.id_saga,
            tipo_mensaje="SolicitarCotizacion.v1",
            message_id="CMD-013",
        )

    assert row is not None
    assert row.command_id == "CMD-013"


def test_14_uow_saga_confirma_y_reversion_atomica() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    saga_id: str | None = None
    with UnidadTrabajoSagasSQL(SessionFactory) as uow:
        saga = _crear_saga("sol-014")
        uow.sagas.crear(saga)
        uow.saga_logs.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                event_id="EVT-014",
            )
        )
        saga_id = saga.id_saga
        uow.confirmar()

    assert saga_id is not None
    with SessionFactory() as session:
        saga_row = session.get(SagaInstanceORM, saga_id)
        log_rows = session.query(SagaLogORM).where(SagaLogORM.id_saga == saga_id).all()

    assert saga_row is not None
    assert len(log_rows) == 1


def test_15_uow_rollback_atomico_revierte_saga_y_log() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = _crear_saga("sol-015")
        repo.crear(saga)
        session.commit()

    with pytest.raises(RuntimeError, match="fallo intencional"), UnidadTrabajoSagasSQL(
        SessionFactory
    ) as uow:
        saga_loaded = uow.sagas.obtener_por_id_solicitud("sol-015")
        assert saga_loaded is not None
        uow.sagas.actualizar_paso(saga_loaded, SagaStepName.SOLICITAR_COTIZACION)
        uow.saga_logs.registrar(
            _crear_log(
                id_saga=saga_loaded.id_saga,
                id_solicitud=saga_loaded.id_solicitud,
                paso=saga_loaded.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.COMMAND_EMITTED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SolicitarCotizacion.v1",
                command_id="CMD-015",
            )
        )
        raise RuntimeError("fallo intencional")

    with SessionFactory() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga_loaded = repo.obtener_por_id_solicitud("sol-015")
        assert saga_loaded is not None
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga_loaded.id_saga)

    assert saga_loaded.paso_actual == SagaStepName.CREAR_TRABAJO
    assert saga_loaded.version == 1
    assert logs == []


def test_16_idempotencia_caso_a_event_id_y_command_id_null() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-016")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SolicitudDePartnerListaParaAtencion.v1",
                event_id="E1",
                command_id=None,
            )
        )
        session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.DUPLICATE,
                resultado=SagaLogResultado.NO_OP_DUPLICATE,
                tipo_mensaje="SolicitudDePartnerListaParaAtencion.v1",
                event_id="E1",
                command_id=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_17_idempotencia_caso_b_command_id_y_event_id_null() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-017")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.COMMAND_EMITTED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SolicitarCotizacion.v1",
                event_id=None,
                command_id="C1",
            )
        )
        session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.DUPLICATE,
                resultado=SagaLogResultado.NO_OP_DUPLICATE,
                tipo_mensaje="SolicitarCotizacion.v1",
                event_id=None,
                command_id="C1",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_18_idempotencia_caso_c_coalesce_prioriza_event_id() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-018")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="Evento.v1",
                event_id="E1",
                command_id="C1",
            )
        )
        session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.DUPLICATE,
                resultado=SagaLogResultado.NO_OP_DUPLICATE,
                tipo_mensaje="Evento.v1",
                event_id="E1",
                command_id="C2",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with SessionFactory() as session:
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="Evento.v1",
                event_id="E2",
                command_id="C1",
            )
        )
        session.commit()

    with SessionFactory() as session:
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)

    assert len(logs) == 2


def test_19_idempotencia_caso_d_ambos_ids_null_no_participa_indice_parcial() -> None:
    engine = _engine_postgresql()
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionFactory() as session:
        saga_repo = SqlAlchemyRepositorioSagas(session)
        log_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = _crear_saga("sol-019")
        saga_repo.crear(saga)
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.IGNORED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SinMessageId.v1",
                event_id=None,
                command_id=None,
            )
        )
        log_repo.registrar(
            _crear_log(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.IGNORED,
                resultado=SagaLogResultado.APPLIED,
                tipo_mensaje="SinMessageId.v1",
                event_id=None,
                command_id=None,
            )
        )
        session.commit()

    with SessionFactory() as session:
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)

    assert len(logs) == 2
