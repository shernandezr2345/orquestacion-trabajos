import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, insert, inspect, text
from sqlalchemy.engine import make_url

from orquestacion_trabajos.modulos.sagas.infraestructura.orm import (  # noqa: F401
    SagaInstanceORM,
    SagaLogORM,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base
from orquestacion_trabajos.seedwork.infraestructura.orm import InboxORM

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration_engine() -> Iterator[Engine]:
    url = make_url(os.environ["ORQUESTACION_DATABASE_URL"])
    database_name = "orquestacion_migrations_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 3})
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    engine = create_engine(url.set(database=database_name), connect_args={"connect_timeout": 3})
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
        admin.dispose()


def migrate(engine: Engine, target: str, *, downgrade: bool = False) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        operation = command.downgrade if downgrade else command.upgrade
        operation(config, target)


def test_initial_migration_matches_orm_and_upgrade_preserves_data(migration_engine: Engine) -> None:
    migrate(migration_engine, "head")
    assert set(inspect(migration_engine).get_table_names()) == {
        "alembic_version",
        "trabajos",
        "inbox",
        "outbox",
        "saga_instance",
        "saga_log",
    }
    with migration_engine.begin() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002"
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        connection.execute(
            insert(InboxORM).values(
                consumidor="migration-test",
                id_mensaje="message",
                contenido="{}",
                estado="PROCESADA",
                creado_en="2026-09-14T00:00:00Z",
            )
        )
    migrate(migration_engine, "head")
    with migration_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM inbox")) == 1


def test_migration_downgrade_and_upgrade_roundtrip(migration_engine: Engine) -> None:
    migrate(migration_engine, "head")
    migrate(migration_engine, "base", downgrade=True)
    assert set(inspect(migration_engine).get_table_names()) == {"alembic_version"}
    migrate(migration_engine, "head")
    with migration_engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_existing_unversioned_schema_is_not_adopted(migration_engine: Engine) -> None:
    from sqlalchemy.exc import ProgrammingError

    Base.metadata.create_all(migration_engine)
    with migration_engine.begin() as connection:
        connection.execute(
            insert(InboxORM).values(
                consumidor="legacy",
                id_mensaje="keep",
                contenido="{}",
                estado="PROCESADA",
                creado_en="2026-09-14T00:00:00Z",
            )
        )
    with pytest.raises(ProgrammingError):
        migrate(migration_engine, "head")
    assert "alembic_version" not in inspect(migration_engine).get_table_names()
    with migration_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM inbox")) == 1
