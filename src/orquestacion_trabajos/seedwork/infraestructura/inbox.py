from __future__ import annotations

from abc import ABC, abstractmethod


class Inbox(ABC):
    @abstractmethod
    def registrar(self, *, consumidor: str, id_mensaje: str, contenido: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def ya_procesado(self, *, consumidor: str, id_mensaje: str) -> bool:
        raise NotImplementedError
