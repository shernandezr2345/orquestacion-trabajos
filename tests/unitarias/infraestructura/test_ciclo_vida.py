from __future__ import annotations

from typing import ClassVar
from unittest.mock import Mock

from sqlalchemy.orm import Session

from orquestacion_trabajos.infraestructura.ciclo_vida import CicloVidaPulsar
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyOutbox,
    SqlAlchemyRepositorioTrabajos,
)


class _ThreadDouble:
    instancias: ClassVar[list[_ThreadDouble]] = []

    def __init__(self, *, target, daemon: bool, name: str) -> None:
        self.target = target
        self.daemon = daemon
        self.name = name
        self.iniciado = False
        self.unido = False
        self.instancias.append(self)

    def start(self) -> None:
        self.iniciado = True
        self.target()

    def is_alive(self) -> bool:
        return self.iniciado

    def join(self, timeout: int) -> None:
        self.unido = True


class _ComponenteDouble:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.inicios = 0
        self.detenciones = 0

    def iniciar(self) -> None:
        self.inicios += 1

    def desconectar(self) -> None:
        self.detenciones += 1


def test_ciclo_vida_inicia_y_detiene_los_tres_consumidores(monkeypatch) -> None:
    def session_factory() -> Session:
        raise AssertionError("El lifecycle no debe abrir sesiones globales")

    entrada = _ComponenteDouble()
    registrada = _ComponenteDouble()
    rechazada = _ComponenteDouble()
    despacho = _ComponenteDouble()
    _ThreadDouble.instancias = []

    monkeypatch.setattr(
        "orquestacion_trabajos.infraestructura.ciclo_vida.create_session_factory",
        lambda: session_factory,
    )
    monkeypatch.setattr(
        CicloVidaPulsar,
        "_crear_consumidor_entrada",
        lambda _self: entrada,
    )
    monkeypatch.setattr(
        CicloVidaPulsar,
        "_crear_consumidor_cotizacion_registrada",
        lambda _self: registrada,
    )
    monkeypatch.setattr(
        CicloVidaPulsar,
        "_crear_consumidor_cotizacion_rechazada",
        lambda _self: rechazada,
    )
    monkeypatch.setattr(
        "orquestacion_trabajos.infraestructura.ciclo_vida.DespachoOutbox",
        lambda _factory: despacho,
    )
    monkeypatch.setattr(
        "orquestacion_trabajos.infraestructura.ciclo_vida.threading.Thread",
        _ThreadDouble,
    )

    ciclo_vida = CicloVidaPulsar()
    ciclo_vida.iniciar()

    assert ciclo_vida.session_factory is session_factory
    assert entrada.inicios == registrada.inicios == rechazada.inicios == 1
    assert ciclo_vida.esta_listo()
    assert [thread.name for thread in _ThreadDouble.instancias] == [
        "ConsumidorEntrada",
        "ConsumidorCotizacionRegistrada",
        "ConsumidorCotizacionRechazada",
        "DespachoOutbox",
    ]

    ciclo_vida.detener()

    assert entrada.detenciones == registrada.detenciones == rechazada.detenciones == 1
    assert despacho.detenciones == 1
    assert all(thread.unido for thread in _ThreadDouble.instancias)


def test_factory_de_resultados_compone_dependencias_en_la_session_recibida() -> None:
    session: Session = Mock(spec=Session)
    ciclo_vida = CicloVidaPulsar()

    handler = ciclo_vida._crear_handler_aplicar_cotizacion(session)

    assert isinstance(handler.repositorio, SqlAlchemyRepositorioTrabajos)
    assert isinstance(handler.registro_salidas, SqlAlchemyOutbox)
    assert handler.repositorio._session is session
    assert handler.registro_salidas._session is session
