from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from orquestacion_trabajos.seedwork.dominio.entidades import Entidad


class SagaStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPENSATING = "COMPENSATING"
    COMPLETED = "COMPLETED"
    COMPENSATED = "COMPENSATED"


class SagaStepName(str, Enum):
    CREAR_TRABAJO = "CREAR_TRABAJO"
    SOLICITAR_COTIZACION = "SOLICITAR_COTIZACION"
    ABRIR_SEGUIMIENTO = "ABRIR_SEGUIMIENTO"
    REGISTRAR_ATENCION_HABILITADA = "REGISTRAR_ATENCION_HABILITADA"
    COMPLETAR_SAGA = "COMPLETAR_SAGA"
    CANCELAR_TRABAJO_POR_RECHAZO = "CANCELAR_TRABAJO_POR_RECHAZO"
    REGISTRAR_ATENCION_CANCELADA = "REGISTRAR_ATENCION_CANCELADA"
    INICIAR_COMPENSACION_APERTURA = "INICIAR_COMPENSACION_APERTURA"
    CANCELAR_TRABAJO_COMPENSACION = "CANCELAR_TRABAJO_COMPENSACION"
    REGISTRAR_ATENCION_CANCELADA_COMPENSACION = "REGISTRAR_ATENCION_CANCELADA_COMPENSACION"
    CANCELAR_SEGUIMIENTO_SI_APLICA = "CANCELAR_SEGUIMIENTO_SI_APLICA"
    FINALIZAR_COMPENSACION = "FINALIZAR_COMPENSACION"


class SagaLogTipoRegistro(str, Enum):
    EVENT_RECEIVED = "EVENT_RECEIVED"
    COMMAND_EMITTED = "COMMAND_EMITTED"
    EVENT_EMITTED = "EVENT_EMITTED"
    LOCAL_OPERATION = "LOCAL_OPERATION"
    STATE_CHANGED = "STATE_CHANGED"
    DUPLICATE = "DUPLICATE"
    LATE = "LATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    IGNORED = "IGNORED"


class SagaLogResultado(str, Enum):
    APPLIED = "APPLIED"
    NO_OP_DUPLICATE = "NO_OP_DUPLICATE"
    NO_OP_LATE = "NO_OP_LATE"
    NO_OP_OUT_OF_ORDER = "NO_OP_OUT_OF_ORDER"
    REJECTED_CONFLICT = "REJECTED_CONFLICT"


class EstadoSagaInvalidoError(ValueError):
    pass


class PasoSagaInvalidoError(ValueError):
    pass


class ReglaSagaInvalidaError(ValueError):
    pass


class SagaInstance(Entidad):
    def __init__(
        self,
        *,
        id_solicitud: str,
        estado: SagaStatus,
        paso_actual: SagaStepName,
        id_saga: str | None = None,
        id_trabajo: str | None = None,
        seguimiento_apertura_solicitada: bool = False,
        seguimiento_abierto_confirmado: bool = False,
        version: int = 1,
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> None:
        super().__init__(id=id_saga or str(uuid4()), version=version)
        self.id_solicitud = id_solicitud
        self.id_trabajo = id_trabajo
        self.estado = estado
        self.paso_actual = paso_actual
        self.seguimiento_apertura_solicitada = seguimiento_apertura_solicitada
        self.seguimiento_abierto_confirmado = seguimiento_abierto_confirmado
        self.created_at = created_at or self._now_iso()
        self.updated_at = updated_at or self.created_at
        self._validar_banderas()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @property
    def id_saga(self) -> str:
        return str(self.id)

    @classmethod
    def crear(cls, *, id_solicitud: str) -> SagaInstance:
        return cls(
            id_solicitud=id_solicitud,
            id_trabajo=None,
            estado=SagaStatus.RUNNING,
            paso_actual=SagaStepName.CREAR_TRABAJO,
            seguimiento_apertura_solicitada=False,
            seguimiento_abierto_confirmado=False,
            version=1,
        )

    def _marcar_mutacion(self) -> None:
        self.version += 1
        self.updated_at = self._now_iso()

    def _validar_banderas(self) -> None:
        if self.seguimiento_abierto_confirmado and not self.seguimiento_apertura_solicitada:
            raise ReglaSagaInvalidaError(
                "seguimiento_abierto_confirmado=true requiere seguimiento_apertura_solicitada=true"
            )

    def actualizar_estado(self, estado: SagaStatus) -> None:
        if not isinstance(estado, SagaStatus):
            raise EstadoSagaInvalidoError("Estado de saga no soportado")
        if self.estado != estado:
            self.estado = estado
            self._marcar_mutacion()

    def actualizar_paso(self, paso_actual: SagaStepName) -> None:
        if not isinstance(paso_actual, SagaStepName):
            raise PasoSagaInvalidoError("Paso de saga no soportado")
        if self.paso_actual != paso_actual:
            self.paso_actual = paso_actual
            self._marcar_mutacion()

    def asignar_id_trabajo(self, id_trabajo: str) -> None:
        if self.id_trabajo != id_trabajo:
            self.id_trabajo = id_trabajo
            self._marcar_mutacion()

    def marcar_seguimiento_apertura_solicitada(self) -> None:
        if not self.seguimiento_apertura_solicitada:
            self.seguimiento_apertura_solicitada = True
            self._marcar_mutacion()

    def marcar_seguimiento_abierto_confirmado(self) -> None:
        cambio = False
        if not self.seguimiento_apertura_solicitada:
            self.seguimiento_apertura_solicitada = True
            cambio = True
        if not self.seguimiento_abierto_confirmado:
            self.seguimiento_abierto_confirmado = True
            cambio = True
        self._validar_banderas()
        if cambio:
            self._marcar_mutacion()


@dataclass(frozen=True)
class SagaLog:
    id_saga: str
    id_solicitud: str
    paso: str
    tipo_registro: SagaLogTipoRegistro
    resultado: SagaLogResultado
    created_at: str
    log_id: str | None = None
    id_trabajo: str | None = None
    tipo_mensaje: str | None = None
    event_id: str | None = None
    command_id: str | None = None
    causacion: str | None = None
    estado_anterior: SagaStatus | None = None
    estado_nuevo: SagaStatus | None = None
    detalle: str | None = None

    @property
    def message_id(self) -> str | None:
        return self.event_id or self.command_id

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")
