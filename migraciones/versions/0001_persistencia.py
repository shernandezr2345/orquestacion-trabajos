import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trabajos",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("id_solicitud", sa.String(64), nullable=False),
        sa.Column("id_partner", sa.String(64), nullable=False),
        sa.Column("categoria", sa.String(64), nullable=False),
        sa.Column("tipo_solicitud", sa.String(64), nullable=False),
        sa.Column("tipo_red", sa.String(64), nullable=False),
        sa.Column("referencia_externa", sa.String(255), nullable=False),
        sa.Column("id_politica", sa.String(64), nullable=False),
        sa.Column("version_politica", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.String(64), nullable=False),
        sa.Column("resultado_estado", sa.String(32), nullable=True),
        sa.Column("resultado_id_peticion", sa.String(64), nullable=True),
        sa.Column("resultado_id_cotizacion", sa.String(64), nullable=True),
        sa.Column("resultado_id_proveedor", sa.String(64), nullable=True),
        sa.Column("resultado_categoria", sa.String(64), nullable=True),
        sa.Column("resultado_tipo_red", sa.String(64), nullable=True),
        sa.Column("resultado_importe_menor", sa.Integer(), nullable=True),
        sa.Column("resultado_moneda", sa.String(16), nullable=True),
        sa.Column("resultado_motivo", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id_solicitud", name="uq_trabajos_id_solicitud"),
    )
    op.create_index("ix_trabajos_id_solicitud", "trabajos", ["id_solicitud"])
    op.create_table(
        "inbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("consumidor", sa.String(128), nullable=False),
        sa.Column("id_mensaje", sa.String(128), nullable=False),
        sa.Column("contenido", sa.String(), nullable=False),
        sa.Column("estado", sa.String(32), nullable=False),
        sa.Column("creado_en", sa.String(64), nullable=False),
        sa.Column("procesado_en", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumidor", "id_mensaje", name="uq_inbox_consumidor_mensaje"),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(128), nullable=False),
        sa.Column("destino", sa.String(128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("estado", sa.String(32), nullable=False),
        sa.Column("creado_en", sa.String(64), nullable=False),
        sa.Column("procesado_en", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("outbox")
    op.drop_table("inbox")
    op.drop_index("ix_trabajos_id_solicitud", table_name="trabajos")
    op.drop_table("trabajos")
