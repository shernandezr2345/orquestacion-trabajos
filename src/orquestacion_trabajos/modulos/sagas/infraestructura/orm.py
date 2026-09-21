from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orquestacion_trabajos.seedwork.infraestructura.orm import Base


class SagaInstanceORM(Base):
    __tablename__ = "saga_instance"
    __table_args__ = (
        UniqueConstraint("id_solicitud", name="uq_saga_instance_id_solicitud"),
        CheckConstraint(
            "estado IN ('RUNNING', 'COMPENSATING', 'COMPLETED', 'COMPENSATED')",
            name="ck_saga_instance_estado",
        ),
        CheckConstraint(
            "(NOT seguimiento_abierto_confirmado) OR seguimiento_apertura_solicitada",
            name="ck_saga_instance_seguimiento_consistente",
        ),
    )

    id_saga: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_solicitud: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    id_trabajo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", index=True)
    paso_actual: Mapped[str] = mapped_column(String(128), nullable=False)
    seguimiento_apertura_solicitada: Mapped[bool] = mapped_column(nullable=False, default=False)
    seguimiento_abierto_confirmado: Mapped[bool] = mapped_column(nullable=False, default=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    updated_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    logs: Mapped[list[SagaLogORM]] = relationship(
        "SagaLogORM", back_populates="saga", passive_deletes=True
    )


class SagaLogORM(Base):
    __tablename__ = "saga_log"
    __table_args__ = (
        CheckConstraint(
            "tipo_registro IN ('EVENT_RECEIVED', 'COMMAND_EMITTED', 'EVENT_EMITTED', 'LOCAL_OPERATION', 'STATE_CHANGED', 'DUPLICATE', 'LATE', 'OUT_OF_ORDER', 'IGNORED')",
            name="ck_saga_log_tipo_registro",
        ),
        CheckConstraint(
            "resultado IN ('APPLIED', 'NO_OP_DUPLICATE', 'NO_OP_LATE', 'NO_OP_OUT_OF_ORDER', 'REJECTED_CONFLICT')",
            name="ck_saga_log_resultado",
        ),
        Index("ix_saga_log_saga_created", "id_saga", "created_at"),
        Index("ix_saga_log_solicitud_created", "id_solicitud", "created_at"),
        Index(
            "uq_saga_log_idempotencia",
            "id_saga",
            "tipo_mensaje",
            text("coalesce(event_id, command_id)"),
            unique=True,
            postgresql_where=text("(event_id IS NOT NULL) OR (command_id IS NOT NULL)"),
        ),
    )

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_saga: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("saga_instance.id_saga", ondelete="RESTRICT"),
        nullable=False,
    )
    id_solicitud: Mapped[str] = mapped_column(String(64), nullable=False)
    id_trabajo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paso: Mapped[str] = mapped_column(String(128), nullable=False)
    tipo_registro: Mapped[str] = mapped_column(String(32), nullable=False)
    tipo_mensaje: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    command_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    causacion: Mapped[str | None] = mapped_column(String(128), nullable=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(32), nullable=True)
    estado_nuevo: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resultado: Mapped[str] = mapped_column(String(32), nullable=False)
    detalle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    saga: Mapped[SagaInstanceORM] = relationship("SagaInstanceORM", back_populates="logs")
