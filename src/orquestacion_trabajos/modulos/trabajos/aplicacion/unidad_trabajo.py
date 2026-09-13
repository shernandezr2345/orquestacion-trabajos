from __future__ import annotations

from abc import ABC, abstractmethod


class UnidadTrabajo(ABC):
    @abstractmethod
    def confirmar(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def revertir(self) -> None:
        raise NotImplementedError


class InMemoryUnidadTrabajo(UnidadTrabajo):
    def confirmar(self) -> None:
        return None

    def revertir(self) -> None:
        return None
