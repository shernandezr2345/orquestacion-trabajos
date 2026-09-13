from __future__ import annotations

from typing import Any


class Entidad:
    def __init__(self, *, id: Any = None, version: int = 1) -> None:
        self.id = id
        self.version = version
        self.eventos_dominio: list[Any] = []

    def agregar_evento(self, evento: Any) -> None:
        self.eventos_dominio.append(evento)

    def limpiar_eventos(self) -> None:
        self.eventos_dominio.clear()
