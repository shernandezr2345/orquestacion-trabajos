import os

from alembic import context
from sqlalchemy import Connection, create_engine
from sqlalchemy.pool import NullPool

from orquestacion_trabajos.modulos.sagas.infraestructura.orm import (  # noqa: F401
    SagaInstanceORM,
    SagaLogORM,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if context.is_offline_mode():
    context.configure(
        url=os.environ["ORQUESTACION_DATABASE_URL"],
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    run_migrations(connection)
else:
    engine = create_engine(
        os.environ["ORQUESTACION_DATABASE_URL"],
        poolclass=NullPool,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=60000"},
    )
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()
