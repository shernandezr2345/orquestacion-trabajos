from __future__ import annotations

from abc import ABC, abstractmethod

from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaInstance,
    SagaLog,
    SagaStatus,
    SagaStepName,
)


class RepositorioSagas(ABC):
    @abstractmethod
    def crear(self, saga: SagaInstance) -> None:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id_saga(self, id_saga: str) -> SagaInstance | None:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id_solicitud(self, id_solicitud: str) -> SagaInstance | None:
        raise NotImplementedError

    @abstractmethod
    def actualizar_estado(self, saga: SagaInstance, estado: SagaStatus) -> None:
        raise NotImplementedError

    @abstractmethod
    def actualizar_paso(self, saga: SagaInstance, paso: SagaStepName) -> None:
        raise NotImplementedError

    @abstractmethod
    def asignar_id_trabajo(self, saga: SagaInstance, id_trabajo: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def marcar_seguimiento_apertura_solicitada(self, saga: SagaInstance) -> None:
        raise NotImplementedError

    @abstractmethod
    def marcar_seguimiento_abierto_confirmado(self, saga: SagaInstance) -> None:
        raise NotImplementedError


class RepositorioSagaLog(ABC):
    @abstractmethod
    def registrar(self, registro: SagaLog) -> None:
        raise NotImplementedError

    @abstractmethod
    def listar_por_saga(self, id_saga: str) -> list[SagaLog]:
        raise NotImplementedError

    @abstractmethod
    def obtener_ultimo_por_saga(self, id_saga: str) -> SagaLog | None:
        raise NotImplementedError

    @abstractmethod
    def buscar_por_message_id(
        self,
        *,
        id_saga: str,
        tipo_mensaje: str,
        message_id: str,
    ) -> SagaLog | None:
        raise NotImplementedError
