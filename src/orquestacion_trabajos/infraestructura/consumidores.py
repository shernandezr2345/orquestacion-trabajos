from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pulsar
from config.rutas import rutas
from config.settings import settings
from pulsar.schema import AvroSchema

from orquestacion_trabajos.infraestructura.esquemas_python.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)
from orquestacion_trabajos.infraestructura.esquemas_python.v1.entrada import (
    SolicitudDePartnerListaParaAtencionV1,
)
from orquestacion_trabajos.infraestructura.mapeadores_eventos import (
    MapeadorEventoEntrada,
    MapeadorResultadoCotizacion,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    AplicarCotizacionCommand,
    CrearTrabajoCommand,
)
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
            schema=AvroSchema(SolicitudDePartnerListaParaAtencionV1),
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
            record = mensaje.value()
            datos = {nombre: getattr(record, nombre) for nombre in record._fields}
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


class _ConsumidorResultadoCotizacion:
    tipo_evento: str
    topico: str
    suscripcion: str
    schema_record: type

    def __init__(self, session_factory, handler_factory) -> None:
        self.session_factory = session_factory
        self.handler_factory = handler_factory
        self.client: pulsar.Client | None = None
        self.consumer: pulsar.Consumer | None = None

    def conectar(self) -> None:
        if self.client is not None:
            return

        self.client = pulsar.Client(settings.pulsar_url)
        self.consumer = self.client.subscribe(
            self.topico,
            subscription_name=self.suscripcion,
            consumer_type=pulsar.ConsumerType.Shared,
            schema=AvroSchema(self.schema_record),
            message_listener=self._procesar_mensaje,
        )
        logger.info(
            "Consumer de %s creado para %s con suscripción %s",
            self.tipo_evento,
            self.topico,
            self.suscripcion,
        )

    def desconectar(self) -> None:
        if self.consumer is not None:
            self.consumer.close()
            self.consumer = None
        if self.client is not None:
            self.client.close()
            self.client = None

    def _procesar_mensaje(self, consumer: pulsar.Consumer, mensaje: pulsar.Message) -> None:
        session: Session = self.session_factory()
        try:
            record = mensaje.value()
            datos = {nombre: getattr(record, nombre) for nombre in record._fields}
            resultado = self._mapear_resultado(datos)
            contenido = json.dumps(datos, sort_keys=True, default=str)
            inbox = SqlAlchemyInbox(session)
            ya_procesado = inbox.ya_procesado(
                consumidor=self.suscripcion,
                id_mensaje=resultado.event_id,
            )
            inbox.registrar(
                consumidor=self.suscripcion,
                id_mensaje=resultado.event_id,
                contenido=contenido,
            )

            if not ya_procesado:
                comando = AplicarCotizacionCommand(resultado=resultado)
                self.handler_factory(session).ejecutar(comando)

            session.commit()
            consumer.acknowledge(mensaje)
        except Exception:
            session.rollback()
            logger.exception("Error procesando resultado de cotización")
            raise
        finally:
            session.close()

    def _mapear_resultado(self, datos: dict[str, object]):
        raise NotImplementedError


class ConsumidorCotizacionRegistrada(_ConsumidorResultadoCotizacion):
    tipo_evento = "CotizacionRegistrada.v1"
    topico = rutas.topico_cotizacion_registrada
    suscripcion = rutas.suscripcion_cotizacion_registrada
    schema_record = CotizacionRegistradaV1

    def _mapear_resultado(self, datos: dict[str, object]):
        return MapeadorResultadoCotizacion.cotizacion_registrada_a_resultado(datos)


class ConsumidorCotizacionRechazada(_ConsumidorResultadoCotizacion):
    tipo_evento = "CotizacionRechazada.v1"
    topico = rutas.topico_cotizacion_rechazada
    suscripcion = rutas.suscripcion_cotizacion_rechazada
    schema_record = CotizacionRechazadaV1

    def _mapear_resultado(self, datos: dict[str, object]):
        return MapeadorResultadoCotizacion.cotizacion_rechazada_a_resultado(datos)
