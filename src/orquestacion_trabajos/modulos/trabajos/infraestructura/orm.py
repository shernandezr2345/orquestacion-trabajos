from __future__ import annotations

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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

    resultado_estado: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resultado_id_peticion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_id_cotizacion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_id_proveedor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_categoria: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_tipo_red: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_importe_menor: Mapped[int | None] = mapped_column(nullable=True)
    resultado_moneda: Mapped[str | None] = mapped_column(String(16), nullable=True)
    resultado_motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)


class InboxORM(Base):
    __tablename__ = "inbox"
    __table_args__ = (
        UniqueConstraint("consumidor", "id_mensaje", name="uq_inbox_consumidor_mensaje"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    consumidor: Mapped[str] = mapped_column(String(128), nullable=False)
    id_mensaje: Mapped[str] = mapped_column(String(128), nullable=False)
    contenido: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDIENTE")
    creado_en: Mapped[str] = mapped_column(String(64), nullable=False)
    procesado_en: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OutboxORM(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(128), nullable=False)
    destino: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDIENTE")
    creado_en: Mapped[str] = mapped_column(String(64), nullable=False)
    procesado_en: Mapped[str | None] = mapped_column(String(64), nullable=True)
