from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping


class Outbox(ABC):
    @abstractmethod
    def registrar(
        self,
        *,
        tipo: str,
        payload: Mapping[str, object],
        destino: str | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def pendientes(self) -> list[dict[str, object]]:
        raise NotImplementedError
