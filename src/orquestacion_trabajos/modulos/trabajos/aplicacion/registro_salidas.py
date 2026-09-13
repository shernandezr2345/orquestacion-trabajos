from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SalidaRegistrada:
    tipo: str
    payload: Mapping[str, object]


class InMemoryRegistroSalidas:
    def __init__(self) -> None:
        self.salidas: list[SalidaRegistrada] = []

    def registrar(self, tipo: str, payload: Mapping[str, object]) -> None:
        self.salidas.append(SalidaRegistrada(tipo=tipo, payload=payload))
