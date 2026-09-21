import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saga_instance",
        sa.Column("id_saga", sa.String(64), nullable=False),
        sa.Column("id_solicitud", sa.String(64), nullable=False),
        sa.Column("id_trabajo", sa.String(64), nullable=True),
        sa.Column("estado", sa.String(32), nullable=False, server_default="RUNNING"),
        sa.Column("paso_actual", sa.String(128), nullable=False, server_default="CREAR_TRABAJO"),
        sa.Column(
            "seguimiento_apertura_solicitada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "seguimiento_abierto_confirmado",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id_saga"),
        sa.UniqueConstraint("id_solicitud", name="uq_saga_instance_id_solicitud"),
        sa.CheckConstraint(
            "estado IN ('RUNNING', 'COMPENSATING', 'COMPLETED', 'COMPENSATED')",
            name="ck_saga_instance_estado",
        ),
        sa.CheckConstraint(
            "(NOT seguimiento_abierto_confirmado) OR seguimiento_apertura_solicitada",
            name="ck_saga_instance_seguimiento_consistente",
        ),
    )
    op.create_index("ix_saga_instance_id_solicitud", "saga_instance", ["id_solicitud"])
    op.create_index("ix_saga_instance_estado", "saga_instance", ["estado"])

    op.create_table(
        "saga_log",
        sa.Column("log_id", sa.String(64), nullable=False),
        sa.Column("id_saga", sa.String(64), nullable=False),
        sa.Column("id_solicitud", sa.String(64), nullable=False),
        sa.Column("id_trabajo", sa.String(64), nullable=True),
        sa.Column("paso", sa.String(128), nullable=False),
        sa.Column("tipo_registro", sa.String(32), nullable=False),
        sa.Column("tipo_mensaje", sa.String(128), nullable=True),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("command_id", sa.String(128), nullable=True),
        sa.Column("causacion", sa.String(128), nullable=True),
        sa.Column("estado_anterior", sa.String(32), nullable=True),
        sa.Column("estado_nuevo", sa.String(32), nullable=True),
        sa.Column("resultado", sa.String(32), nullable=False),
        sa.Column("detalle", sa.String(255), nullable=True),
        sa.Column("created_at", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("log_id"),
        sa.ForeignKeyConstraint(["id_saga"], ["saga_instance.id_saga"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "tipo_registro IN ('EVENT_RECEIVED', 'COMMAND_EMITTED', 'EVENT_EMITTED', 'LOCAL_OPERATION', 'STATE_CHANGED', 'DUPLICATE', 'LATE', 'OUT_OF_ORDER', 'IGNORED')",
            name="ck_saga_log_tipo_registro",
        ),
        sa.CheckConstraint(
            "resultado IN ('APPLIED', 'NO_OP_DUPLICATE', 'NO_OP_LATE', 'NO_OP_OUT_OF_ORDER', 'REJECTED_CONFLICT')",
            name="ck_saga_log_resultado",
        ),
    )
    op.create_index("ix_saga_log_saga_created", "saga_log", ["id_saga", "created_at"])
    op.create_index("ix_saga_log_solicitud_created", "saga_log", ["id_solicitud", "created_at"])
    op.create_index(
        "uq_saga_log_idempotencia",
        "saga_log",
        ["id_saga", "tipo_mensaje", sa.text("coalesce(event_id, command_id)")],
        unique=True,
        postgresql_where=sa.text("(event_id IS NOT NULL) OR (command_id IS NOT NULL)"),
    )


def downgrade() -> None:
    op.drop_index("uq_saga_log_idempotencia", table_name="saga_log")
    op.drop_index("ix_saga_log_solicitud_created", table_name="saga_log")
    op.drop_index("ix_saga_log_saga_created", table_name="saga_log")
    op.drop_table("saga_log")

    op.drop_index("ix_saga_instance_estado", table_name="saga_instance")
    op.drop_index("ix_saga_instance_id_solicitud", table_name="saga_instance")
    op.drop_table("saga_instance")
