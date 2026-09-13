from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pulsar
from config.rutas import rutas
from config.settings import settings

from orquestacion_trabajos.infraestructura.mapeadores_eventos import MapeadorEventoEntrada
from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import CrearTrabajoCommand
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyInbox,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


class ConsumidorEntrada:
    """Consumidor de SolicitudDePartnerListaParaAtencion desde Pulsar."""

    def __init__(
        self,
        session_factory,
        repositorio_trabajo_factory,
        unidad_trabajo_factory,
        handler_crear_trabajo=None,
        handler_factory=None,
    ) -> None:
        self.session_factory = session_factory
        self.repositorio_trabajo_factory = repositorio_trabajo_factory
        self.unidad_trabajo_factory = unidad_trabajo_factory
        self.handler_crear_trabajo = handler_crear_trabajo
        self.handler_factory = handler_factory
        self.client: pulsar.Client | None = None
        self.consumer: pulsar.Consumer | None = None
        self._running = False

    def conectar(self) -> None:
        """Conectar a Pulsar y crear consumidor."""
        if self.client is not None:
            return

        url_pulsar = settings.pulsar_url
        logger.info(f"Conectando a Pulsar en {url_pulsar}")

        self.client = pulsar.Client(url_pulsar)

        # Crear consumidor con configuración de Shared
        self.consumer = self.client.subscribe(
            rutas.topico_solicitud_entrada,
            subscription_name=rutas.suscripcion_solicitud_entrada,
            consumer_type=pulsar.ConsumerType.Shared,
            message_listener=self._procesar_mensaje,
        )
        logger.info(
            f"Consumidor creado para {rutas.topico_solicitud_entrada} "
            f"con suscripción {rutas.suscripcion_solicitud_entrada}"
        )

    def iniciar(self) -> None:
        """Iniciar el consumidor (bloqueante)."""
        if self.consumer is None:
            self.conectar()

        self._running = True
        logger.info("Consumidor de Entrada iniciado")

        try:
            # El message_listener se ejecuta automáticamente en un hilo
            # Este loop simplemente mantiene el consumidor activo
            while self._running:
                import time

                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Consumidor interrumpido")
        except Exception:
            logger.exception("Error en consumidor")
        finally:
            self.desconectar()

    def desconectar(self) -> None:
        """Desconectar de Pulsar."""
        self._running = False
        if self.consumer is not None:
            try:
                self.consumer.close()
                logger.info("Consumidor cerrado")
            except Exception as e:  # noqa: BLE001 - cierre debe continuar
                logger.error(f"Error cerrando consumidor: {e}")
            self.consumer = None

        if self.client is not None:
            try:
                self.client.close()
                logger.info("Cliente Pulsar cerrado")
            except Exception as e:  # noqa: BLE001 - cierre debe continuar
                logger.error(f"Error cerrando cliente Pulsar: {e}")
            self.client = None

    def _procesar_mensaje(self, consumer: pulsar.Consumer, mensaje: pulsar.Message) -> None:
        """Procesar un mensaje recibido (callback del listener)."""
        try:
            # Deserializar el payload Avro
            datos = json.loads(mensaje.data().decode("utf-8"))
            event_id = str(datos.get("event_id", ""))
            id_solicitud = str(datos.get("id_solicitud", ""))

            logger.info(f"Mensaje recibido: event_id={event_id}, id_solicitud={id_solicitud}")

            # Traducir a tipo de dominio
            solicitud = MapeadorEventoEntrada.mensaje_a_solicitud(datos)

            # Crear sesión y UoW para esta transacción
            session: Session = self.session_factory()
            try:
                # Registrar en Inbox para idempotencia
                consumidor = rutas.suscripcion_solicitud_entrada
                inbox = SqlAlchemyInbox(session)

                contenido_normalizado = json.dumps(
                    {
                        "event_id": event_id,
                        "id_solicitud": id_solicitud,
                        "id_partner": datos.get("id_partner"),
                    },
                    sort_keys=True,
                )

                inbox.registrar(
                    consumidor=consumidor,
                    id_mensaje=event_id,
                    contenido=contenido_normalizado,
                )

                # Crear handler para esta sesión
                if self.handler_factory is not None:
                    handler = self.handler_factory.crear_handler(session)
                else:
                    # Fallback al handler predefinido
                    handler = self.handler_crear_trabajo

                # Ejecutar caso de uso con UoW integrada
                comando = CrearTrabajoCommand(solicitud=solicitud)
                trabajo = handler.ejecutar(comando)

                logger.info(f"Trabajo creado: id={trabajo.id}")

                # Commit de la transacción (incluye Inbox, Trabajo, Outbox)
                session.commit()

                # ACK SOLO DESPUÉS del commit durable
                consumer.acknowledge(mensaje)
                logger.info(f"ACK confirmado para evento {event_id}")

            except Exception:
                session.rollback()
                logger.exception("Error procesando mensaje")
                # NO hacer ACK; el mensaje será reentregado
                # Opcionalmente, negative acknowledge
                # consumer.negativeAcknowledge(mensaje)
                raise
            finally:
                session.close()

        except Exception:
            logger.exception("Error crítico en procesador de mensajes")
