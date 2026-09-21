from __future__ import annotations

from uuid import uuid4

from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaInstance,
    SagaLog,
    SagaLogResultado,
    SagaLogTipoRegistro,
    SagaStatus,
    SagaStepName,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.orm import SagaInstanceORM, SagaLogORM


class SagaInstanceMapper:
    @staticmethod
    def a_orm(saga: SagaInstance) -> SagaInstanceORM:
        return SagaInstanceORM(
            id_saga=saga.id_saga,
            id_solicitud=saga.id_solicitud,
            id_trabajo=saga.id_trabajo,
            estado=saga.estado.value,
            paso_actual=saga.paso_actual.value,
            seguimiento_apertura_solicitada=saga.seguimiento_apertura_solicitada,
            seguimiento_abierto_confirmado=saga.seguimiento_abierto_confirmado,
            version=saga.version,
            created_at=saga.created_at,
            updated_at=saga.updated_at,
        )

    @staticmethod
    def desde_orm(row: SagaInstanceORM) -> SagaInstance:
        saga = SagaInstance(
            id_saga=row.id_saga,
            id_solicitud=row.id_solicitud,
            id_trabajo=row.id_trabajo,
            estado=SagaStatus(row.estado),
            paso_actual=SagaStepName(row.paso_actual),
            seguimiento_apertura_solicitada=row.seguimiento_apertura_solicitada,
            seguimiento_abierto_confirmado=row.seguimiento_abierto_confirmado,
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        saga.limpiar_eventos()
        return saga


class SagaLogMapper:
    @staticmethod
    def a_orm(registro: SagaLog) -> SagaLogORM:
        return SagaLogORM(
            log_id=registro.log_id or str(uuid4()),
            id_saga=registro.id_saga,
            id_solicitud=registro.id_solicitud,
            id_trabajo=registro.id_trabajo,
            paso=registro.paso,
            tipo_registro=registro.tipo_registro.value,
            tipo_mensaje=registro.tipo_mensaje,
            event_id=registro.event_id,
            command_id=registro.command_id,
            causacion=registro.causacion,
            estado_anterior=registro.estado_anterior.value if registro.estado_anterior else None,
            estado_nuevo=registro.estado_nuevo.value if registro.estado_nuevo else None,
            resultado=registro.resultado.value,
            detalle=registro.detalle,
            created_at=registro.created_at,
        )

    @staticmethod
    def desde_orm(row: SagaLogORM) -> SagaLog:
        return SagaLog(
            log_id=row.log_id,
            id_saga=row.id_saga,
            id_solicitud=row.id_solicitud,
            id_trabajo=row.id_trabajo,
            paso=row.paso,
            tipo_registro=SagaLogTipoRegistro(row.tipo_registro),
            tipo_mensaje=row.tipo_mensaje,
            event_id=row.event_id,
            command_id=row.command_id,
            causacion=row.causacion,
            estado_anterior=SagaStatus(row.estado_anterior) if row.estado_anterior else None,
            estado_nuevo=SagaStatus(row.estado_nuevo) if row.estado_nuevo else None,
            resultado=SagaLogResultado(row.resultado),
            detalle=row.detalle,
            created_at=row.created_at,
        )
