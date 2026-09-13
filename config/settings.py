from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    env: str = field(default_factory=lambda: _env("ORQUESTACION_ENV", "local"))
    http_host: str = field(default_factory=lambda: _env("ORQUESTACION_HTTP_HOST", "0.0.0.0"))
    http_port: int = field(default_factory=lambda: int(_env("ORQUESTACION_HTTP_PORT", "8001")))
    database_url: str = field(
        default_factory=lambda: _env(
            "ORQUESTACION_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/orquestacion_trabajos",
        )
    )
    pulsar_url: str = field(
        default_factory=lambda: _env("ORQUESTACION_PULSAR_URL", "pulsar://localhost:6650")
    )
    pulsar_tenant: str = field(default_factory=lambda: _env("ORQUESTACION_PULSAR_TENANT", "public"))
    pulsar_namespace: str = field(
        default_factory=lambda: _env("ORQUESTACION_PULSAR_NAMESPACE", "default")
    )
    enable_lifespan_consumers: bool = field(
        default_factory=lambda: (
            _env("ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS", "false").lower()
            in {"1", "true", "yes", "on"}
        )
    )


settings = Settings()
