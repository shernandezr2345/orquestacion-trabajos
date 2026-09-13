from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class EventoDominio:
    instante: datetime

    def __post_init__(self) -> None:
        if self.instante.tzinfo is None:
            object.__setattr__(self, "instante", self.instante.replace(tzinfo=UTC))


@dataclass(frozen=True)
class EventoInterno(EventoDominio):
    pass
