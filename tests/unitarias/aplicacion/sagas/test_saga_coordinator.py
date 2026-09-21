from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from orquestacion_trabajos.modulos.sagas.aplicacion.coordinador import SagaCoordinator
from orquestacion_trabajos.modulos.sagas.aplicacion.eventos import SagaMessageEnvelope
from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaLogResultado,
    SagaLogTipoRegistro,
    SagaStatus,
    SagaStepName,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.repositorios import (
    SqlAlchemyRepositorioSagaLog,
    SqlAlchemyRepositorioSagas,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.orm import SagaInstanceORM, SagaLogORM
from orquestacion_trabajos.modulos.sagas.infraestructura.unidad_trabajo import (
    UnidadTrabajoSagaTrabajosSQL,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base
from orquestacion_trabajos.seedwork.infraestructura.orm import OutboxORM

DESTINOS = {
    "TrabajoCreado.v1": "persistent://public/default/trabajo-creado-v1",
    "SolicitarCotizacion.v1": "persistent://public/default/solicitar-cotizacion-v1",
}


class CrearTrabajoFallaDespues(CrearTrabajoHandler):
    def ejecutar(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        trabajo = super().ejecutar(*args, **kwargs)
        raise RuntimeError("fallo intencional posterior")
        return trabajo


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _crear_coordinator(
    sessions: sessionmaker[Session],
    *,
    crear_handler: CrearTrabajoHandler | None = None,
) -> SagaCoordinator:
    crear_uow = lambda: UnidadTrabajoSagaTrabajosSQL(sessions, DESTINOS)
    crear = crear_handler or CrearTrabajoHandler(crear_uow)
    aplicar = AplicarCotizacionHandler(crear_uow)
    return SagaCoordinator(crear_uow, crear, aplicar)


def _envelope_solicitud(
    *, event_id: str = "evt-1", id_solicitud: str = "sol-1", id_partner: str = "par-1"
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "SolicitudDePartnerListaParaAtencion.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:00:00Z",
        "correlacion": id_solicitud,
        "id_solicitud": id_solicitud,
        "version_solicitud": 1,
        "id_partner": id_partner,
        "referencia_externa": "ref-1",
        "categoria": "SINIESTRO",
        "tipo_solicitud": "SINIESTRO",
        "aprobacion_previa": None,
        "tipo_red": "GENERAL_HDA",
        "id_politica": "pol-1",
        "version_politica": 1,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="SolicitudDePartnerListaParaAtencion.v1",
        message_id=event_id,
        payload=payload,
        id_solicitud=id_solicitud,
        correlacion=id_solicitud,
    )


def _envelope_cotizacion_registrada(
    *,
    event_id: str,
    id_trabajo: str,
    id_solicitud: str,
    id_partner: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "CotizacionRegistrada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:01:00Z",
        "correlacion": id_solicitud,
        "causacion": "cmd-1",
        "id_peticion": id_trabajo,
        "id_trabajo": id_trabajo,
        "id_solicitud": id_solicitud,
        "id_partner": id_partner,
        "version_catalogo": 1,
        "version_cotizacion": 1,
        "id_cotizacion": "cot-1",
        "id_proveedor": "prov-1",
        "importe_menor": 100,
        "moneda": "COP",
        "categoria": "SINIESTRO",
        "tipo_red": "GENERAL_HDA",
    }
    return SagaMessageEnvelope(
        tipo_mensaje="CotizacionRegistrada.v1",
        message_id=event_id,
        payload=payload,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion="cmd-1",
    )


def _envelope_cotizacion_rechazada(
    *,
    event_id: str,
    id_trabajo: str,
    id_solicitud: str,
    id_partner: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "CotizacionRechazada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:02:00Z",
        "correlacion": id_solicitud,
        "causacion": "cmd-1",
        "id_peticion": id_trabajo,
        "id_trabajo": id_trabajo,
        "id_solicitud": id_solicitud,
        "id_partner": id_partner,
        "version_catalogo": 1,
        "version_cotizacion": 1,
        "motivo": "SIN_OFERTA_PARA_CATEGORIA",
        "categoria": "SINIESTRO",
        "tipo_red": "GENERAL_HDA",
    }
    return SagaMessageEnvelope(
        tipo_mensaje="CotizacionRechazada.v1",
        message_id=event_id,
        payload=payload,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion="cmd-1",
    )


def _ultimo_log(session: Session, id_saga: str):
    return SqlAlchemyRepositorioSagaLog(session).obtener_ultimo_por_saga(id_saga)


def _envelope_atencion_habilitada(
    *, event_id: str, id_saga: str, id_solicitud: str
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "AtencionHabilitadaRegistrada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:03:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="AtencionHabilitadaRegistrada.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        correlacion=id_solicitud,
    )


def _envelope_atencion_cancelada(
    *, event_id: str, id_saga: str, id_solicitud: str
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "AtencionCanceladaRegistrada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:04:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="AtencionCanceladaRegistrada.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        correlacion=id_solicitud,
    )


def test_happy_path_inicial_crea_saga_trabajo_y_comando() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.RUNNING
        assert saga.id_trabajo is not None
        assert saga.paso_actual == SagaStepName.SOLICITAR_COTIZACION
        salida = (
            session.query(OutboxORM)
            .filter(OutboxORM.tipo == "SolicitarCotizacion.v1")
            .order_by(OutboxORM.id.desc())
            .first()
        )
        assert salida is not None


def test_idempotencia_no_repite_efectos_ni_emision() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    env = _envelope_solicitud(event_id="evt-dup")
    coordinator.procesar(env, consumidor="orquestacion-solicitudes-v1")
    coordinator.procesar(env, consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        outbox = session.query(OutboxORM).filter(OutboxORM.tipo == "SolicitarCotizacion.v1").all()
        assert len(outbox) == 1
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.DUPLICATE
            and log.resultado == SagaLogResultado.NO_OP_DUPLICATE
            for log in logs
        )


def test_late_completed_registra_no_op_late() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        repo.actualizar_estado(saga, SagaStatus.COMPLETED)
        session.commit()

    coordinator.procesar(
        _envelope_cotizacion_registrada(
            event_id="evt-late-completed",
            id_trabajo="trab-x",
            id_solicitud="sol-1",
            id_partner="par-1",
        ),
        consumidor="orquestacion-cotizacion-registrada-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.LATE
        assert ultimo.resultado == SagaLogResultado.NO_OP_LATE


def test_late_compensated_registra_no_op_late() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        repo.actualizar_estado(saga, SagaStatus.COMPENSATED)
        session.commit()

    coordinator.procesar(
        _envelope_cotizacion_rechazada(
            event_id="evt-late-compensated",
            id_trabajo="trab-x",
            id_solicitud="sol-1",
            id_partner="par-1",
        ),
        consumidor="orquestacion-cotizacion-rechazada-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.LATE
        assert ultimo.resultado == SagaLogResultado.NO_OP_LATE


def test_out_of_order_evento_futuro() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        envelope = SagaMessageEnvelope(
            tipo_mensaje="AtencionHabilitadaRegistrada.v1",
            message_id="evt-futuro",
            payload={"id_solicitud": "sol-1", "id_saga": saga.id_saga, "event_id": "evt-futuro"},
            id_saga=saga.id_saga,
            id_solicitud="sol-1",
        )

    coordinator.procesar(envelope, consumidor="orquestacion-atencion-habilitada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.OUT_OF_ORDER
        assert ultimo.resultado == SagaLogResultado.NO_OP_OUT_OF_ORDER


def test_conflict_ids_inconsistentes() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        envelope = SagaMessageEnvelope(
            tipo_mensaje="CotizacionRegistrada.v1",
            message_id="evt-conflict-ids",
            payload={
                "event_id": "evt-conflict-ids",
                "id_saga": saga.id_saga,
                "id_solicitud": "sol-distinta",
            },
            id_saga=saga.id_saga,
            id_solicitud="sol-distinta",
            id_trabajo=saga.id_trabajo,
            correlacion="sol-distinta",
        )

    coordinator.procesar(envelope, consumidor="orquestacion-cotizacion-registrada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.resultado == SagaLogResultado.REJECTED_CONFLICT


def test_conflict_contenido_incompatible() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        envelope = _envelope_cotizacion_registrada(
            event_id="evt-conflict-content",
            id_trabajo="trab-no-corresponde",
            id_solicitud="sol-1",
            id_partner="par-1",
        )

    coordinator.procesar(envelope, consumidor="orquestacion-cotizacion-registrada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.resultado == SagaLogResultado.REJECTED_CONFLICT


def test_rollback_si_falla_operacion_posterior() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    crear_uow = lambda: UnidadTrabajoSagaTrabajosSQL(sessions, DESTINOS)
    coordinator = SagaCoordinator(
        crear_uow,
        CrearTrabajoFallaDespues(crear_uow),
        AplicarCotizacionHandler(crear_uow),
    )

    with pytest.raises(RuntimeError, match="fallo intencional"):
        coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is None
        assert session.query(OutboxORM).count() == 0


def test_cotizacion_registrada_avanza_solo_en_paso_habilitado() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        env = _envelope_cotizacion_registrada(
            event_id="evt-cot-ok",
            id_trabajo=saga.id_trabajo,
            id_solicitud="sol-1",
            id_partner="par-1",
        )

    coordinator.procesar(env, consumidor="orquestacion-cotizacion-registrada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.paso_actual == SagaStepName.ABRIR_SEGUIMIENTO


def test_cotizacion_rechazada_mantiene_ruta_pendiente_sin_compensaciones() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        env = _envelope_cotizacion_rechazada(
            event_id="evt-cot-rej",
            id_trabajo=saga.id_trabajo,
            id_solicitud="sol-1",
            id_partner="par-1",
        )

    coordinator.procesar(env, consumidor="orquestacion-cotizacion-rechazada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.RUNNING
        assert saga.paso_actual == SagaStepName.CANCELAR_TRABAJO_POR_RECHAZO
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.IGNORED
            and "decision pendiente" in (log.detalle or "")
            for log in logs
        )
        assert not any(out.tipo == "AnularCotizacion.v1" for out in session.query(OutboxORM).all())


def test_resolucion_por_id_saga_sin_id_solicitud_procesa_sin_conflicto() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        envelope = SagaMessageEnvelope(
            tipo_mensaje="CotizacionRegistrada.v1",
            message_id="evt-id-saga-only",
            payload={
                "event_id": "evt-id-saga-only",
                "tipo": "CotizacionRegistrada.v1",
                "version_contrato": 1,
                "instante": "2026-09-21T00:05:00Z",
                "id_peticion": saga.id_trabajo,
                "id_trabajo": saga.id_trabajo,
                "id_solicitud": "sol-1",
                "id_partner": "par-1",
                "version_catalogo": 1,
                "version_cotizacion": 1,
                "id_cotizacion": "cot-id-saga-only",
                "id_proveedor": "prov-1",
                "importe_menor": 150,
                "moneda": "COP",
                "categoria": "SINIESTRO",
                "tipo_red": "GENERAL_HDA",
            },
            id_saga=saga.id_saga,
            id_trabajo=saga.id_trabajo,
        )

    coordinator.procesar(envelope, consumidor="orquestacion-cotizacion-registrada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.paso_actual == SagaStepName.ABRIR_SEGUIMIENTO
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert not any(log.resultado == SagaLogResultado.REJECTED_CONFLICT for log in logs)


def test_mensaje_sin_identificadores_no_ejecuta_efectos_ni_registra_log() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    envelope = SagaMessageEnvelope(
        tipo_mensaje="AtencionHabilitadaRegistrada.v1",
        message_id="evt-sin-ids",
        payload={"event_id": "evt-sin-ids", "tipo": "AtencionHabilitadaRegistrada.v1"},
    )

    coordinator.procesar(envelope, consumidor="orquestacion-atencion-habilitada-v1")

    with sessions() as session:
        assert session.query(SagaInstanceORM).count() == 0
        assert session.query(SagaLogORM).count() == 0
        assert session.query(OutboxORM).count() == 0


def test_conflicto_cruzado_id_saga_e_id_solicitud_de_distintas_sagas() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(
        _envelope_solicitud(event_id="evt-a", id_solicitud="sol-a", id_partner="par-a"),
        consumidor="orquestacion-solicitudes-v1",
    )
    coordinator.procesar(
        _envelope_solicitud(event_id="evt-b", id_solicitud="sol-b", id_partner="par-b"),
        consumidor="orquestacion-solicitudes-v1",
    )

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga_a = repo.obtener_por_id_solicitud("sol-a")
        saga_b = repo.obtener_por_id_solicitud("sol-b")
        assert saga_a is not None
        assert saga_b is not None
        assert saga_a.id_trabajo is not None
        paso_antes = saga_a.paso_actual
        envelope = SagaMessageEnvelope(
            tipo_mensaje="CotizacionRegistrada.v1",
            message_id="evt-conflicto-cruzado",
            payload={
                "event_id": "evt-conflicto-cruzado",
                "id_saga": saga_a.id_saga,
                "id_solicitud": "sol-b",
                "id_trabajo": saga_a.id_trabajo,
            },
            id_saga=saga_a.id_saga,
            id_solicitud="sol-b",
            id_trabajo=saga_a.id_trabajo,
            correlacion="sol-b",
        )

    coordinator.procesar(envelope, consumidor="orquestacion-cotizacion-registrada-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga_a = repo.obtener_por_id_solicitud("sol-a")
        assert saga_a is not None
        assert saga_a.paso_actual == paso_antes
        ultimo = _ultimo_log(session, saga_a.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.EVENT_RECEIVED
        assert ultimo.resultado == SagaLogResultado.REJECTED_CONFLICT


def test_happy_path_atencion_habilitada_y_idempotencia() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        repo.actualizar_paso(saga, SagaStepName.COMPLETAR_SAGA)
        session.commit()

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        env = _envelope_atencion_habilitada(
            event_id="evt-attn-hab",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
        )
        outbox_antes = session.query(OutboxORM).count()

    coordinator.procesar(env, consumidor="orquestacion-atencion-habilitada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPLETED
        assert saga.paso_actual == SagaStepName.COMPLETAR_SAGA
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.STATE_CHANGED
        assert ultimo.resultado == SagaLogResultado.APPLIED
        assert session.query(OutboxORM).count() == outbox_antes

    coordinator.procesar(env, consumidor="orquestacion-atencion-habilitada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPLETED
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.DUPLICATE
            and log.resultado == SagaLogResultado.NO_OP_DUPLICATE
            for log in logs
        )
        assert session.query(OutboxORM).count() == outbox_antes


def test_happy_path_atencion_cancelada_y_idempotencia() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        repo.actualizar_estado(saga, SagaStatus.COMPENSATING)
        repo.actualizar_paso(saga, SagaStepName.FINALIZAR_COMPENSACION)
        session.commit()

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        env = _envelope_atencion_cancelada(
            event_id="evt-attn-can",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
        )
        outbox_antes = session.query(OutboxORM).count()

    coordinator.procesar(env, consumidor="orquestacion-atencion-cancelada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATED
        assert saga.paso_actual == SagaStepName.FINALIZAR_COMPENSACION
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.STATE_CHANGED
        assert ultimo.resultado == SagaLogResultado.APPLIED
        assert session.query(OutboxORM).count() == outbox_antes

    coordinator.procesar(env, consumidor="orquestacion-atencion-cancelada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATED
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.DUPLICATE
            and log.resultado == SagaLogResultado.NO_OP_DUPLICATE
            for log in logs
        )
        assert session.query(OutboxORM).count() == outbox_antes
