from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SalidaRegistrada:
    tipo: str
    payload: Mapping[str, object]
    destino: str | None = None


class RegistroSalidas(Protocol):
    def registrar(
        self,
        *,
        tipo: str,
        payload: Mapping[str, object],
        destino: str | None = None,
    ) -> None: ...


class InMemoryRegistroSalidas:
    def __init__(self) -> None:
        self.salidas: list[SalidaRegistrada] = []

    def registrar(
        self,
        tipo: str,
        payload: Mapping[str, object],
        destino: str | None = None,
    ) -> None:
        self.salidas.append(SalidaRegistrada(tipo=tipo, payload=payload, destino=destino))
