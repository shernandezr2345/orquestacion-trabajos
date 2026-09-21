from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from orquestacion_trabajos.modulos.sagas.aplicacion.coordinador import SagaCoordinator
from orquestacion_trabajos.modulos.sagas.aplicacion.eventos import SagaMessageEnvelope
from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaLog,
    SagaLogResultado,
    SagaLogTipoRegistro,
    SagaStatus,
    SagaStepName,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.orm import SagaInstanceORM, SagaLogORM
from orquestacion_trabajos.modulos.sagas.infraestructura.repositorios import (
    SqlAlchemyRepositorioSagaLog,
    SqlAlchemyRepositorioSagas,
)
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
    causacion: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "CotizacionRegistrada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:01:00Z",
        "correlacion": id_solicitud,
        "causacion": causacion,
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
        causacion=causacion,
    )


def _envelope_cotizacion_rechazada(
    *,
    event_id: str,
    id_trabajo: str,
    id_solicitud: str,
    id_partner: str,
    causacion: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "CotizacionRechazada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:02:00Z",
        "correlacion": id_solicitud,
        "causacion": causacion,
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
        causacion=causacion,
    )


def _ultimo_log(session: Session, id_saga: str):
    return SqlAlchemyRepositorioSagaLog(session).obtener_ultimo_por_saga(id_saga)


def _envelope_atencion_habilitada(
    *, event_id: str, id_saga: str, id_solicitud: str, id_trabajo: str, causacion: str | None = None
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "AtencionHabilitadaRegistrada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:03:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
        "id_trabajo": id_trabajo,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="AtencionHabilitadaRegistrada.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion=causacion,
    )


def _envelope_atencion_cancelada(
    *, event_id: str, id_saga: str, id_solicitud: str, id_trabajo: str, causacion: str | None = None
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "AtencionCanceladaRegistrada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:04:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
        "id_trabajo": id_trabajo,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="AtencionCanceladaRegistrada.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion=causacion,
    )


def _envelope_seguimiento_abierto(
    *,
    event_id: str,
    id_saga: str,
    id_solicitud: str,
    id_trabajo: str,
    causacion: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "SeguimientoTrabajoAbierto.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:06:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
        "id_trabajo": id_trabajo,
        "correlacion": id_solicitud,
        "causacion": causacion,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="SeguimientoTrabajoAbierto.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion=causacion,
    )


def _envelope_apertura_fallida(
    *,
    event_id: str,
    id_saga: str,
    id_solicitud: str,
    id_trabajo: str,
    causacion: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "AperturaSeguimientoFallida.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:07:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
        "id_trabajo": id_trabajo,
        "correlacion": id_solicitud,
        "causacion": causacion,
        "codigo_motivo": "FALLO_CONTROLADO_APERTURA",
        "detalle": "falla controlada",
    }
    return SagaMessageEnvelope(
        tipo_mensaje="AperturaSeguimientoFallida.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion=causacion,
    )


def _envelope_cotizacion_anulada(
    *,
    event_id: str,
    id_saga: str,
    id_solicitud: str,
    id_trabajo: str,
    causacion: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "CotizacionAnulada.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:08:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
        "id_trabajo": id_trabajo,
        "correlacion": id_solicitud,
        "causacion": causacion,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="CotizacionAnulada.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion=causacion,
    )


def _envelope_seguimiento_cancelado(
    *,
    event_id: str,
    id_saga: str,
    id_solicitud: str,
    id_trabajo: str,
    causacion: str,
) -> SagaMessageEnvelope:
    payload = {
        "event_id": event_id,
        "tipo": "SeguimientoTrabajoCancelado.v1",
        "version_contrato": 1,
        "instante": "2026-09-21T00:09:00Z",
        "id_saga": id_saga,
        "id_solicitud": id_solicitud,
        "id_trabajo": id_trabajo,
        "correlacion": id_solicitud,
        "causacion": causacion,
    }
    return SagaMessageEnvelope(
        tipo_mensaje="SeguimientoTrabajoCancelado.v1",
        message_id=event_id,
        payload=payload,
        id_saga=id_saga,
        id_solicitud=id_solicitud,
        id_trabajo=id_trabajo,
        correlacion=id_solicitud,
        causacion=causacion,
    )


def _ultimo_command_id(session: Session, id_saga: str, tipo_mensaje: str) -> str:
    logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(id_saga)
    ids = [
        str(log.command_id)
        for log in logs
        if log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
        and log.tipo_mensaje == tipo_mensaje
        and log.command_id
    ]
    assert ids
    return ids[-1]


def _causacion_solicitar(session: Session, id_saga: str) -> str:
    return _ultimo_command_id(session, id_saga, "SolicitarCotizacion.v1")


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
            causacion="cmd-irrelevante",
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
            causacion="cmd-irrelevante",
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
            causacion="cmd-irrelevante",
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
            causacion=_causacion_solicitar(session, saga.id_saga),
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
            causacion=_causacion_solicitar(session, saga.id_saga),
        )

    coordinator.procesar(env, consumidor="orquestacion-cotizacion-rechazada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        assert saga.paso_actual == SagaStepName.REGISTRAR_ATENCION_CANCELADA
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.LOCAL_OPERATION
            and "cancelado localmente" in (log.detalle or "")
            for log in logs
        )
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
            and log.tipo_mensaje == "RegistrarAtencionCancelada.v1"
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
                "causacion": _causacion_solicitar(session, saga.id_saga),
            },
            id_saga=saga.id_saga,
            id_trabajo=saga.id_trabajo,
            causacion=_causacion_solicitar(session, saga.id_saga),
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
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-happy-attn",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_abrir = _ultimo_command_id(session, saga.id_saga, "AbrirSeguimientoTrabajo.v1")
        coordinator.procesar(
            _envelope_seguimiento_abierto(
                event_id="evt-seg-open-happy-attn",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion=cmd_abrir,
            ),
            consumidor="orquestacion-seguimiento-abierto-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_habilitar = _ultimo_command_id(session, saga.id_saga, "RegistrarAtencionHabilitada.v1")
        env = _envelope_atencion_habilitada(
            event_id="evt-attn-hab",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=cmd_habilitar,
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
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        env_rechazo = _envelope_cotizacion_rechazada(
            event_id="evt-pre-attn-can",
            id_trabajo=str(saga.id_trabajo),
            id_solicitud=saga.id_solicitud,
            id_partner="par-1",
            causacion=_causacion_solicitar(session, saga.id_saga),
        )

    coordinator.procesar(env_rechazo, consumidor="orquestacion-cotizacion-rechazada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        comando_cancelacion = _ultimo_command_id(
            session, saga.id_saga, "RegistrarAtencionCancelada.v1"
        )
        env = _envelope_atencion_cancelada(
            event_id="evt-attn-can",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=comando_cancelacion,
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


def test_cotizacion_registrada_emite_abrir_seguimiento_pendiente_contrato() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        env = _envelope_cotizacion_registrada(
            event_id="evt-cot-abrir",
            id_trabajo=saga.id_trabajo,
            id_solicitud="sol-1",
            id_partner="par-1",
            causacion=_causacion_solicitar(session, saga.id_saga),
        )

    coordinator.procesar(env, consumidor="orquestacion-cotizacion-registrada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.paso_actual == SagaStepName.ABRIR_SEGUIMIENTO
        assert saga.seguimiento_apertura_solicitada is True
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
            and log.tipo_mensaje == "AbrirSeguimientoTrabajo.v1"
            for log in logs
        )


def test_seguimiento_abierto_emite_registrar_atencion_habilitada() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")
    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-seg",
                id_trabajo=saga.id_trabajo,
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        comando_abrir = _ultimo_command_id(session, saga.id_saga, "AbrirSeguimientoTrabajo.v1")
        env = _envelope_seguimiento_abierto(
            event_id="evt-seg-open",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=comando_abrir,
        )

    coordinator.procesar(env, consumidor="orquestacion-seguimiento-abierto-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.paso_actual == SagaStepName.REGISTRAR_ATENCION_HABILITADA
        assert saga.seguimiento_abierto_confirmado is True
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
            and log.tipo_mensaje == "RegistrarAtencionHabilitada.v1"
            for log in logs
        )


def test_cotizacion_rechazada_con_seguimiento_abierto_espera_confirmaciones() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        repo.marcar_seguimiento_abierto_confirmado(saga)
        session.commit()

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        env = _envelope_cotizacion_rechazada(
            event_id="evt-cot-rej-open",
            id_trabajo=str(saga.id_trabajo),
            id_solicitud=saga.id_solicitud,
            id_partner="par-1",
            causacion=_causacion_solicitar(session, saga.id_saga),
        )

    coordinator.procesar(env, consumidor="orquestacion-cotizacion-rechazada-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        assert saga.paso_actual == SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA
        cmd_cancel_atencion = _ultimo_command_id(session, saga.id_saga, "RegistrarAtencionCancelada.v1")
        cmd_cancel_seguimiento = _ultimo_command_id(
            session, saga.id_saga, "CancelarSeguimientoTrabajo.v1"
        )

    coordinator.procesar(
        _envelope_atencion_cancelada(
            event_id="evt-attn-cancel-open",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=cmd_cancel_atencion,
        ),
        consumidor="orquestacion-atencion-cancelada-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING

    coordinator.procesar(
        _envelope_seguimiento_cancelado(
            event_id="evt-seg-cancel-open",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=cmd_cancel_seguimiento,
        ),
        consumidor="orquestacion-seguimiento-cancelado-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATED
        assert saga.paso_actual == SagaStepName.FINALIZAR_COMPENSACION


def test_apertura_fallida_emite_anular_y_cotizacion_anulada_continua_compensacion() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")
    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-apf",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        comando_abrir = _ultimo_command_id(session, saga.id_saga, "AbrirSeguimientoTrabajo.v1")
        env_falla = _envelope_apertura_fallida(
            event_id="evt-apertura-fallida",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=comando_abrir,
        )

    coordinator.procesar(env_falla, consumidor="orquestacion-apertura-fallida-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        assert saga.paso_actual == SagaStepName.INICIAR_COMPENSACION_APERTURA
        comando_anular = _ultimo_command_id(session, saga.id_saga, "AnularCotizacion.v1")

    coordinator.procesar(
        _envelope_cotizacion_anulada(
            event_id="evt-cot-anulada",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=comando_anular,
        ),
        consumidor="orquestacion-cotizacion-anulada-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert any(
            log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
            and log.tipo_mensaje == "RegistrarAtencionCancelada.v1"
            for log in logs
        )


def test_causacion_historica_acepta_command_id_emitido_no_reciente() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        repo.marcar_seguimiento_abierto_confirmado(saga)
        session.commit()

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        coordinator.procesar(
            _envelope_cotizacion_rechazada(
                event_id="evt-rechazo-causal-hist",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-rechazada-v1",
        )

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        logs_repo = SqlAlchemyRepositorioSagaLog(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_atencion = _ultimo_command_id(session, saga.id_saga, "RegistrarAtencionCancelada.v1")
        cmd_cancel_antiguo = _ultimo_command_id(session, saga.id_saga, "CancelarSeguimientoTrabajo.v1")
        logs_repo.registrar(
            SagaLog(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=saga.id_trabajo,
                paso=saga.paso_actual.value,
                tipo_registro=SagaLogTipoRegistro.COMMAND_EMITTED,
                tipo_mensaje="CancelarSeguimientoTrabajo.v1",
                command_id="cmd-cancel-reciente",
                causacion="evt-rechazo-causal-hist",
                resultado=SagaLogResultado.APPLIED,
                detalle="Comando manual para validar causal historica",
                created_at=SagaLog.now_iso(),
            )
        )
        session.commit()

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        coordinator.procesar(
            _envelope_atencion_cancelada(
                event_id="evt-attn-cancel-hist",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion=cmd_atencion,
            ),
            consumidor="orquestacion-atencion-cancelada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        coordinator.procesar(
            _envelope_seguimiento_cancelado(
                event_id="evt-seg-cancel-hist",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion=cmd_cancel_antiguo,
            ),
            consumidor="orquestacion-seguimiento-cancelado-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATED


def test_conflicto_si_causacion_no_corresponde_a_command_emitido() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-causacion-missing",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        env = _envelope_seguimiento_abierto(
            event_id="evt-seg-causacion-missing",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion="cmd-no-existe",
        )

    coordinator.procesar(env, consumidor="orquestacion-seguimiento-abierto-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.resultado == SagaLogResultado.REJECTED_CONFLICT
        assert "sin command_id emitido" in (ultimo.detalle or "")


def test_conflicto_si_causacion_apunta_a_command_de_otro_tipo() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        solicitar = _ultimo_command_id(session, saga.id_saga, "SolicitarCotizacion.v1")
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-causacion-mismatch",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=solicitar,
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )
        env = _envelope_seguimiento_abierto(
            event_id="evt-seg-causacion-mismatch",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=solicitar,
        )

    coordinator.procesar(env, consumidor="orquestacion-seguimiento-abierto-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.resultado == SagaLogResultado.REJECTED_CONFLICT
        assert "corresponde a SolicitarCotizacion.v1" in (ultimo.detalle or "")


def test_compensacion_espera_cancelacion_seguimiento_cuando_apertura_fue_solicitada() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")
    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-apf-wait",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_abrir = _ultimo_command_id(session, saga.id_saga, "AbrirSeguimientoTrabajo.v1")
        coordinator.procesar(
            _envelope_apertura_fallida(
                event_id="evt-apertura-fallida-wait",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion=cmd_abrir,
            ),
            consumidor="orquestacion-apertura-fallida-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_anular = _ultimo_command_id(session, saga.id_saga, "AnularCotizacion.v1")
        coordinator.procesar(
            _envelope_cotizacion_anulada(
                event_id="evt-cot-anulada-wait",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion=cmd_anular,
            ),
            consumidor="orquestacion-cotizacion-anulada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.paso_actual == SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA
        cmd_cancel_atencion = _ultimo_command_id(session, saga.id_saga, "RegistrarAtencionCancelada.v1")

    coordinator.procesar(
        _envelope_atencion_cancelada(
            event_id="evt-attn-cancel-wait",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=cmd_cancel_atencion,
        ),
        consumidor="orquestacion-atencion-cancelada-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        assert saga.paso_actual == SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA


def test_compensacion_no_cierra_con_confirmacion_parcial() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        repo = SqlAlchemyRepositorioSagas(session)
        saga = repo.obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        repo.marcar_seguimiento_abierto_confirmado(saga)
        session.commit()

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        coordinator.procesar(
            _envelope_cotizacion_rechazada(
                event_id="evt-cot-rej-partial",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-rechazada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_cancel_seguimiento = _ultimo_command_id(
            session, saga.id_saga, "CancelarSeguimientoTrabajo.v1"
        )

    coordinator.procesar(
        _envelope_seguimiento_cancelado(
            event_id="evt-seg-cancel-partial",
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=str(saga.id_trabajo),
            causacion=cmd_cancel_seguimiento,
        ),
        consumidor="orquestacion-seguimiento-cancelado-v1",
    )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        assert saga.paso_actual == SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA


def test_apertura_fallida_no_permite_cerrar_sin_cotizacion_anulada() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")
    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_registrada(
                event_id="evt-cot-apf-pre",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-registrada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        cmd_abrir = _ultimo_command_id(session, saga.id_saga, "AbrirSeguimientoTrabajo.v1")
        coordinator.procesar(
            _envelope_apertura_fallida(
                event_id="evt-apertura-fallida-pre",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion=cmd_abrir,
            ),
            consumidor="orquestacion-apertura-fallida-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        coordinator.procesar(
            _envelope_atencion_cancelada(
                event_id="evt-attn-cancel-sin-anular",
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=str(saga.id_trabajo),
                causacion="cmd-no-aplica",
            ),
            consumidor="orquestacion-atencion-cancelada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.estado == SagaStatus.COMPENSATING
        assert saga.paso_actual == SagaStepName.INICIAR_COMPENSACION_APERTURA
        ultimo = _ultimo_log(session, saga.id_saga)
        assert ultimo is not None
        assert ultimo.tipo_registro == SagaLogTipoRegistro.OUT_OF_ORDER
        assert ultimo.resultado == SagaLogResultado.NO_OP_OUT_OF_ORDER


def test_cotizacion_rechazada_no_emite_anular_cotizacion() -> None:
    engine = _engine()
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    coordinator = _crear_coordinator(sessions)

    coordinator.procesar(_envelope_solicitud(), consumidor="orquestacion-solicitudes-v1")

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        assert saga.id_trabajo is not None
        coordinator.procesar(
            _envelope_cotizacion_rechazada(
                event_id="evt-rechazo-sin-anular",
                id_trabajo=str(saga.id_trabajo),
                id_solicitud=saga.id_solicitud,
                id_partner="par-1",
                causacion=_causacion_solicitar(session, saga.id_saga),
            ),
            consumidor="orquestacion-cotizacion-rechazada-v1",
        )

    with sessions() as session:
        saga = SqlAlchemyRepositorioSagas(session).obtener_por_id_solicitud("sol-1")
        assert saga is not None
        logs = SqlAlchemyRepositorioSagaLog(session).listar_por_saga(saga.id_saga)
        assert not any(
            log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
            and log.tipo_mensaje == "AnularCotizacion.v1"
            for log in logs
        )
