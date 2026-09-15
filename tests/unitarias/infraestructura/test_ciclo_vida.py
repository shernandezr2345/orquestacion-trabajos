import asyncio
from threading import Event
from unittest.mock import Mock

import pytest

from orquestacion_trabajos.config.bootstrap import Componente
from orquestacion_trabajos.config.procesamiento import procesar_eventos
from orquestacion_trabajos.config.settings import Settings


def test_processing_starts_five_independent_cycles_and_closes_them(monkeypatch):
    executed = [Event() for _ in range(5)]
    closed = [Event() for _ in range(5)]

    def component(index):
        def step():
            executed[index].set()
            return False

        return Componente(str(index), step, closed[index].set)

    monkeypatch.setattr(
        "orquestacion_trabajos.config.procesamiento.componer_componentes",
        lambda *args: [component(index) for index in range(5)],
    )
    monkeypatch.setattr(
        "orquestacion_trabajos.config.persistencia.verificar_destinos", lambda *args: None
    )

    async def run():
        settings = Settings(
            database_url="postgresql+psycopg://localhost/test", enable_lifespan_consumers=True
        )
        async with procesar_eventos(Mock(), settings) as processing:
            assert all(event.wait(1) for event in executed)
            assert len(processing.ciclos) == 5
            assert all(not ciclo.hilo.daemon for ciclo in processing.ciclos)
        assert all(event.is_set() for event in closed)
        assert all(not ciclo.hilo.is_alive() for ciclo in processing.ciclos)

    asyncio.run(run())


def test_processing_disabled_does_not_compose(monkeypatch):
    compose = Mock(side_effect=AssertionError("unexpected composition"))
    monkeypatch.setattr("orquestacion_trabajos.config.procesamiento.componer_componentes", compose)

    async def run():
        async with procesar_eventos(Mock(), Settings()) as processing:
            assert processing is None

    asyncio.run(run())


def test_startup_failure_closes_previously_started_cycle(monkeypatch):
    from orquestacion_trabajos.seedwork.infraestructura.ciclos import Ciclo

    closed = Event()
    monkeypatch.setattr(
        "orquestacion_trabajos.config.persistencia.verificar_destinos", lambda *args: None
    )
    monkeypatch.setattr(
        "orquestacion_trabajos.config.procesamiento.componer_componentes",
        lambda *args: [
            Componente("first", lambda: False, closed.set),
            Componente("second", lambda: False, lambda: None),
        ],
    )
    original = Ciclo.iniciar

    def start(self):
        if self.nombre == "second":
            raise RuntimeError("cannot start")
        original(self)

    monkeypatch.setattr(Ciclo, "iniciar", start)

    async def run():
        with pytest.raises(RuntimeError, match="cannot start"):
            async with procesar_eventos(
                Mock(),
                Settings(
                    database_url="postgresql+psycopg://localhost/test",
                    enable_lifespan_consumers=True,
                ),
            ):
                pass

    asyncio.run(run())
    assert closed.is_set()
