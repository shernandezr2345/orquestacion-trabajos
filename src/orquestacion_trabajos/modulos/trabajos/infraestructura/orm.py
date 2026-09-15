from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from orquestacion_trabajos.seedwork.infraestructura.orm import Base


class TrabajoORM(Base):
    __tablename__ = "trabajos"
    __table_args__ = (UniqueConstraint("id_solicitud", name="uq_trabajos_id_solicitud"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    id_partner: Mapped[str] = mapped_column(String(64), nullable=False)
    categoria: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo_solicitud: Mapped[str] = mapped_column(String(64), nullable=False)
    tipo_red: Mapped[str] = mapped_column(String(64), nullable=False)
    referencia_externa: Mapped[str] = mapped_column(String(255), nullable=False)
    id_politica: Mapped[str] = mapped_column(String(64), nullable=False)
    version_politica: Mapped[int] = mapped_column(nullable=False)
    estado: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    creado_en: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    resultado_estado: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resultado_id_peticion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_id_cotizacion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_id_proveedor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_categoria: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_tipo_red: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_importe_menor: Mapped[int | None] = mapped_column(nullable=True)
    resultado_moneda: Mapped[str | None] = mapped_column(String(16), nullable=True)
    resultado_motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
