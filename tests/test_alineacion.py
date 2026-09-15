from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from orquestacion_trabajos.api.app import create_app
from orquestacion_trabajos.config.settings import Settings


def test_apps_have_independent_resources_and_close_after_processing():
    events = []
    databases = []

    def database_factory(url):
        database = Mock()
        database.close.side_effect = lambda: events.append(("database", url))
        databases.append(database)
        return database

    @asynccontextmanager
    async def processing_factory(database, settings):
        try:
            yield None
        finally:
            events.append(("processing", settings.database_url))

    first = create_app(
        Settings(database_url="postgresql+psycopg://localhost/first"),
        database_factory,
        processing_factory,
    )
    second = create_app(
        Settings(database_url="postgresql+psycopg://localhost/second"),
        database_factory,
        processing_factory,
    )
    with TestClient(first), TestClient(second):
        assert first.state.database is not second.state.database
    assert events == [
        ("processing", "postgresql+psycopg://localhost/second"),
        ("database", "postgresql+psycopg://localhost/second"),
        ("processing", "postgresql+psycopg://localhost/first"),
        ("database", "postgresql+psycopg://localhost/first"),
    ]


def test_without_database_liveness_works_and_queries_return_503():
    with TestClient(create_app(Settings(database_url=None))) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        assert client.get("/trabajos").status_code == 503


def test_startup_failure_is_visible_and_closes_database():
    database = Mock()

    @asynccontextmanager
    async def fail(database, settings):
        raise RuntimeError("startup failed")
        yield

    application = create_app(
        Settings(database_url="postgresql+psycopg://localhost/test"), lambda url: database, fail
    )
    with pytest.raises(RuntimeError, match="startup failed"), TestClient(application):
        pass
    database.close.assert_called_once()


def test_shutdown_does_not_close_database_while_cycle_is_alive():
    database = Mock()
    processing = Mock()
    cycle = Mock()
    cycle.hilo.is_alive.return_value = True
    processing.ciclos = [cycle]

    @asynccontextmanager
    async def factory(database, settings):
        yield processing
        raise TimeoutError("cycle still alive")

    application = create_app(
        Settings(database_url="postgresql+psycopg://localhost/test"), lambda url: database, factory
    )
    with pytest.raises(TimeoutError), TestClient(application):
        pass
    database.close.assert_not_called()


def test_database_error_in_query_returns_503():
    from sqlalchemy.exc import OperationalError

    database = Mock()
    database.session_factory.return_value.execute.side_effect = OperationalError(
        "select", {}, RuntimeError("offline")
    )

    @asynccontextmanager
    async def processing(database, settings):
        yield None

    application = create_app(
        Settings(database_url="postgresql+psycopg://localhost/test"),
        lambda url: database,
        processing,
    )
    with TestClient(application) as client:
        assert client.get("/trabajos").status_code == 503


def test_processing_requires_an_explicit_database():
    with pytest.raises(ValueError, match="requires"):
        Settings(database_url=None, enable_lifespan_consumers=True)
