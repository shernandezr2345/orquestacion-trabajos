from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaInstance,
    SagaLog,
    SagaStatus,
    SagaStepName,
)
from orquestacion_trabajos.modulos.sagas.dominio.repositorios import (
    RepositorioSagaLog,
    RepositorioSagas,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.mapeadores import (
    SagaInstanceMapper,
    SagaLogMapper,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.orm import SagaInstanceORM, SagaLogORM


class SagaConcurrencyConflictError(RuntimeError):
    pass


class SqlAlchemyRepositorioSagas(RepositorioSagas):
    def __init__(self, session: Session, *, lock_reads: bool = False) -> None:
        self._session = session
        self._lock_reads = lock_reads
        self._loaded_versions: dict[str, int] = {}

    def _sesion(self) -> Session:
        return self._session

    def crear(self, saga: SagaInstance) -> None:
        try:
            self._sesion().add(SagaInstanceMapper.a_orm(saga))
            self._loaded_versions[saga.id_saga] = saga.version
        except IntegrityError as exc:
            raise ValueError("Conflicto de unicidad al crear saga") from exc

    def obtener_por_id_saga(self, id_saga: str) -> SagaInstance | None:
        row = self._sesion().get(SagaInstanceORM, id_saga, with_for_update=self._lock_reads)
        if row is None:
            return None
        self._loaded_versions[id_saga] = row.version
        return SagaInstanceMapper.desde_orm(row)

    def obtener_por_id_solicitud(self, id_solicitud: str) -> SagaInstance | None:
        statement = select(SagaInstanceORM).where(SagaInstanceORM.id_solicitud == id_solicitud)
        if self._lock_reads:
            statement = statement.with_for_update()
        row = self._sesion().execute(statement).scalar_one_or_none()
        if row is None:
            return None
        self._loaded_versions[row.id_saga] = row.version
        return SagaInstanceMapper.desde_orm(row)

    def actualizar_estado(self, saga: SagaInstance, estado: SagaStatus) -> None:
        saga.actualizar_estado(estado)
        self._guardar_cambios(saga)

    def actualizar_paso(self, saga: SagaInstance, paso: SagaStepName) -> None:
        saga.actualizar_paso(paso)
        self._guardar_cambios(saga)

    def asignar_id_trabajo(self, saga: SagaInstance, id_trabajo: str) -> None:
        saga.asignar_id_trabajo(id_trabajo)
        self._guardar_cambios(saga)

    def marcar_seguimiento_apertura_solicitada(self, saga: SagaInstance) -> None:
        saga.marcar_seguimiento_apertura_solicitada()
        self._guardar_cambios(saga)

    def marcar_seguimiento_abierto_confirmado(self, saga: SagaInstance) -> None:
        saga.marcar_seguimiento_abierto_confirmado()
        self._guardar_cambios(saga)

    def _guardar_cambios(self, saga: SagaInstance) -> None:
        expected_version = self._loaded_versions.get(saga.id_saga)
        if expected_version is None:
            raise ValueError("Debe cargar la saga antes de actualizarla")

        saved_id = self._sesion().scalar(
            update(SagaInstanceORM)
            .where(
                SagaInstanceORM.id_saga == saga.id_saga,
                SagaInstanceORM.version == expected_version,
            )
            .values(
                id_trabajo=saga.id_trabajo,
                estado=saga.estado.value,
                paso_actual=saga.paso_actual.value,
                seguimiento_apertura_solicitada=saga.seguimiento_apertura_solicitada,
                seguimiento_abierto_confirmado=saga.seguimiento_abierto_confirmado,
                version=saga.version,
                updated_at=saga.updated_at,
            )
            .returning(SagaInstanceORM.id_saga)
        )

        if saved_id is None:
            raise SagaConcurrencyConflictError("Conflicto de concurrencia al guardar saga")

        self._loaded_versions[saga.id_saga] = saga.version


class SqlAlchemyRepositorioSagaLog(RepositorioSagaLog):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _sesion(self) -> Session:
        return self._session

    def registrar(self, registro: SagaLog) -> None:
        try:
            self._sesion().add(SagaLogMapper.a_orm(registro))
        except IntegrityError as exc:
            raise ValueError("Conflicto de unicidad al registrar SagaLog") from exc

    def listar_por_saga(self, id_saga: str) -> list[SagaLog]:
        rows = (
            self._sesion()
            .execute(
                select(SagaLogORM)
                .where(SagaLogORM.id_saga == id_saga)
                .order_by(SagaLogORM.created_at.asc(), SagaLogORM.log_id.asc())
            )
            .scalars()
            .all()
        )
        return [SagaLogMapper.desde_orm(row) for row in rows]

    def obtener_ultimo_por_saga(self, id_saga: str) -> SagaLog | None:
        row = (
            self._sesion()
            .execute(
                select(SagaLogORM)
                .where(SagaLogORM.id_saga == id_saga)
                .order_by(SagaLogORM.created_at.desc(), SagaLogORM.log_id.desc())
                .limit(1)
            )
            .scalar_one_or_none()
        )
        return SagaLogMapper.desde_orm(row) if row is not None else None

    def buscar_por_message_id(
        self,
        *,
        id_saga: str,
        tipo_mensaje: str,
        message_id: str,
    ) -> SagaLog | None:
        row = (
            self._sesion()
            .execute(
                select(SagaLogORM).where(
                    SagaLogORM.id_saga == id_saga,
                    SagaLogORM.tipo_mensaje == tipo_mensaje,
                    or_(SagaLogORM.event_id == message_id, SagaLogORM.command_id == message_id),
                )
            )
            .scalar_one_or_none()
        )
        return SagaLogMapper.desde_orm(row) if row is not None else None


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
