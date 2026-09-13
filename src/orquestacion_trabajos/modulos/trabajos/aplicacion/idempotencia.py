from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


class InMemoryIdempotencia:
    def __init__(self) -> None:
        self._registros: dict[str, Any] = {}

    def registrar(self, clave: str, contenido: Any) -> bool:
        if clave not in self._registros:
            self._registros[clave] = contenido
            return True

        previo = self._registros[clave]
        if self._son_iguales(previo, contenido):
            return False

        raise ValueError(f"conflicto de idempotencia para {clave}")

    def obtener(self, clave: str) -> Any | None:
        return self._registros.get(clave)

    @staticmethod
    def _son_iguales(izquierda: Any, derecha: Any) -> bool:
        if (
            is_dataclass(izquierda)
            and not isinstance(izquierda, type)
            and is_dataclass(derecha)
            and not isinstance(derecha, type)
        ):
            return asdict(izquierda) == asdict(derecha)
        if isinstance(izquierda, dict) and isinstance(derecha, dict):
            return izquierda == derecha
        return izquierda == derecha
