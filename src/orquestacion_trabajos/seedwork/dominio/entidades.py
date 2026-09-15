from __future__ import annotations

from orquestacion_trabajos.seedwork.dominio.eventos import EventoDominio


class Entidad:
    def __init__(self, *, id: str, version: int = 1) -> None:
        self.id = id
        self.version = version
        self.eventos_dominio: list[EventoDominio] = []

    def agregar_evento(self, evento: EventoDominio) -> None:
        self.eventos_dominio.append(evento)

    def limpiar_eventos(self) -> None:
        self.eventos_dominio.clear()
