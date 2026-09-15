from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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
