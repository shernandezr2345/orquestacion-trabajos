from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from config.database import create_session_factory

from orquestacion_trabajos.infraestructura.consumidores import (
    ConsumidorCotizacionRechazada,
    ConsumidorCotizacionRegistrada,
    ConsumidorEntrada,
)
from orquestacion_trabajos.infraestructura.despacho import DespachoOutbox
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.idempotencia import InMemoryIdempotencia
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyOutbox,
    SqlAlchemyRepositorioTrabajos,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.unidad_trabajo import (
    SQLAlchemyUnidadTrabajo,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CicloVidaPulsar:
    """Gestiona el ciclo de vida de consumidores y dispatcher de Pulsar en FastAPI."""

    def __init__(self) -> None:
        self.consumidor_entrada: ConsumidorEntrada | None = None
        self.consumidor_cotizacion_registrada: ConsumidorCotizacionRegistrada | None = None
        self.consumidor_cotizacion_rechazada: ConsumidorCotizacionRechazada | None = None
        self.despacho_outbox: DespachoOutbox | None = None
        self.thread_consumidor: threading.Thread | None = None
        self.thread_cotizacion_registrada: threading.Thread | None = None
        self.thread_cotizacion_rechazada: threading.Thread | None = None
        self.thread_despacho: threading.Thread | None = None
        self.session_factory: Callable[[], Session] | None = None

    def iniciar(self) -> None:
        """Iniciar consumidores y dispatcher en hilos separados."""
        try:
            logger.info("Iniciando ciclo de vida de Pulsar")

            # Crear session factory
            self.session_factory = create_session_factory()

            # Inicializar consumidor de Entrada
            self.consumidor_entrada = self._crear_consumidor_entrada()
            self.consumidor_cotizacion_registrada = self._crear_consumidor_cotizacion_registrada()
            self.consumidor_cotizacion_rechazada = self._crear_consumidor_cotizacion_rechazada()

            # Inicializar despacho de Outbox
            self.despacho_outbox = DespachoOutbox(self.session_factory)

            # Iniciar consumidor en hilo
            self.thread_consumidor = threading.Thread(
                target=self.consumidor_entrada.iniciar,
                daemon=True,
                name="ConsumidorEntrada",
            )
            self.thread_consumidor.start()
            logger.info("Hilo de consumidor iniciado")

            self.thread_cotizacion_registrada = threading.Thread(
                target=self.consumidor_cotizacion_registrada.iniciar,
                daemon=True,
                name="ConsumidorCotizacionRegistrada",
            )
            self.thread_cotizacion_registrada.start()

            self.thread_cotizacion_rechazada = threading.Thread(
                target=self.consumidor_cotizacion_rechazada.iniciar,
                daemon=True,
                name="ConsumidorCotizacionRechazada",
            )
            self.thread_cotizacion_rechazada.start()

            # Iniciar despacho en hilo
            self.thread_despacho = threading.Thread(
                target=self.despacho_outbox.iniciar,
                daemon=True,
                name="DespachoOutbox",
            )
            self.thread_despacho.start()
            logger.info("Hilo de despacho iniciado")

        except Exception:
            logger.exception("Error iniciando ciclo de vida Pulsar")
            self.detener()
            raise

    def detener(self) -> None:
        """Detener consumidores y dispatcher."""
        logger.info("Deteniendo ciclo de vida de Pulsar")

        if self.consumidor_entrada is not None:
            try:
                self.consumidor_entrada.desconectar()
            except Exception:
                logger.exception("Error deteniendo consumidor")

        for consumidor in (
            self.consumidor_cotizacion_registrada,
            self.consumidor_cotizacion_rechazada,
        ):
            if consumidor is not None:
                try:
                    consumidor.desconectar()
                except Exception:
                    logger.exception("Error deteniendo consumidor de resultado")

        if self.despacho_outbox is not None:
            try:
                self.despacho_outbox.desconectar()
            except Exception:
                logger.exception("Error deteniendo despacho")

        # Esperar a que los hilos terminen (máximo 10 segundos)
        if self.thread_consumidor is not None and self.thread_consumidor.is_alive():
            self.thread_consumidor.join(timeout=5)
            logger.info("Hilo de consumidor detenido")

        for thread in (
            self.thread_cotizacion_registrada,
            self.thread_cotizacion_rechazada,
        ):
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)

        if self.thread_despacho is not None and self.thread_despacho.is_alive():
            self.thread_despacho.join(timeout=5)
            logger.info("Hilo de despacho detenido")

        logger.info("Ciclo de vida de Pulsar detenido")

    def esta_listo(self) -> bool:
        return (
            self.consumidor_entrada is not None
            and self.consumidor_cotizacion_registrada is not None
            and self.consumidor_cotizacion_rechazada is not None
            and self.despacho_outbox is not None
            and self.thread_consumidor is not None
            and self.thread_cotizacion_registrada is not None
            and self.thread_cotizacion_rechazada is not None
            and self.thread_despacho is not None
            and self.thread_consumidor.is_alive()
            and self.thread_cotizacion_registrada.is_alive()
            and self.thread_cotizacion_rechazada.is_alive()
            and self.thread_despacho.is_alive()
        )

    def _crear_consumidor_entrada(self) -> ConsumidorEntrada:
        """Crear consumidor de Entrada con sus dependencias."""

        # Crear consumidor con factory de handler
        class HandlerFactory:
            def __init__(self, session_factory):
                self.session_factory = session_factory

            def crear_handler(self, session):
                repo = SqlAlchemyRepositorioTrabajos(session)
                uow = SQLAlchemyUnidadTrabajo(session)
                registro_salidas = SqlAlchemyOutbox(session)
                idempotencia = InMemoryIdempotencia()
                return CrearTrabajoHandler(
                    repositorio=repo,
                    unidad_trabajo=uow,
                    registro_salidas=registro_salidas,
                    idempotencia=idempotencia,
                )

        # Por ahora, crear un handler ficticio que será reemplazado en el consumidor
        consumidor = ConsumidorEntrada(
            session_factory=self.session_factory,
            repositorio_trabajo_factory=lambda s: SqlAlchemyRepositorioTrabajos(s),
            unidad_trabajo_factory=lambda s: SQLAlchemyUnidadTrabajo(s),
            handler_crear_trabajo=None,
            handler_factory=HandlerFactory(self.session_factory),
        )

        return consumidor

    def _crear_handler_aplicar_cotizacion(self, session: Session) -> AplicarCotizacionHandler:
        return AplicarCotizacionHandler(
            repositorio=SqlAlchemyRepositorioTrabajos(session),
            idempotencia=InMemoryIdempotencia(),
        )

    def _crear_consumidor_cotizacion_registrada(self) -> ConsumidorCotizacionRegistrada:
        return ConsumidorCotizacionRegistrada(
            self.session_factory,
            self._crear_handler_aplicar_cotizacion,
        )

    def _crear_consumidor_cotizacion_rechazada(self) -> ConsumidorCotizacionRechazada:
        return ConsumidorCotizacionRechazada(
            self.session_factory,
            self._crear_handler_aplicar_cotizacion,
        )
