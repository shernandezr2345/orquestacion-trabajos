from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SagaMessageEnvelope:
    tipo_mensaje: str
    message_id: str
    payload: dict[str, Any]
    id_saga: str | None = None
    id_solicitud: str | None = None
    id_trabajo: str | None = None
    correlacion: str | None = None
    causacion: str | None = None
