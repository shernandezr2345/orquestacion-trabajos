from __future__ import annotations

import logging
from datetime import UTC, datetime

import pulsar
from config.rutas import rutas
from config.settings import settings
from pulsar.schema import AvroSchema
from sqlalchemy import select
from sqlalchemy.orm import Session

from orquestacion_trabajos.infraestructura.esquemas_python.v1.orquestacion import (
    SolicitarCotizacionV1,
    TrabajoCreadoV1,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import OutboxORM

logger = logging.getLogger(__name__)


class DespachoOutbox:
    """Despacho de salidas desde Outbox a Pulsar."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        self.client: pulsar.Client | None = None
        self.producers: dict[str, pulsar.Producer] = {}
        self._running = False

    def conectar(self) -> None:
        """Conectar a Pulsar y crear productores."""
        if self.client is not None:
            return

        url_pulsar = settings.pulsar_url
        logger.info(f"Conectando a Pulsar para despacho en {url_pulsar}")

        self.client = pulsar.Client(url_pulsar)

        # Crear productor para SolicitarCotizacion.v1
        self.producers["SolicitarCotizacion.v1"] = self.client.create_producer(
            rutas.topico_solicitar_cotizacion,
            schema=AvroSchema(SolicitarCotizacionV1),
        )
        logger.info(f"Productor creado para {rutas.topico_solicitar_cotizacion}")

        # Crear productor para TrabajoCreado.v1
        self.producers["TrabajoCreado.v1"] = self.client.create_producer(
            rutas.topico_trabajo_creado,
            schema=AvroSchema(TrabajoCreadoV1),
        )
        logger.info(f"Productor creado para {rutas.topico_trabajo_creado}")

    def iniciar(self) -> None:
        """Iniciar el despacho (bloqueante)."""
        if not self.producers:
            self.conectar()

        self._running = True
        logger.info("Despacho Outbox iniciado")

        try:
            while self._running:
                self._procesar_pendientes()
                import time

                time.sleep(2)  # Procesar cada 2 segundos
        except KeyboardInterrupt:
            logger.info("Despacho interrumpido")
        except Exception:
            logger.exception("Error en despacho")
        finally:
            self.desconectar()

    def desconectar(self) -> None:
        """Desconectar de Pulsar."""
        self._running = False
        for tipo, producer in self.producers.items():
            try:
                producer.close()
                logger.info(f"Productor {tipo} cerrado")
            except Exception as e:  # noqa: BLE001 - cierre debe continuar
                logger.error(f"Error cerrando productor {tipo}: {e}")
        self.producers = {}

        if self.client is not None:
            try:
                self.client.close()
                logger.info("Cliente Pulsar de despacho cerrado")
            except Exception as e:  # noqa: BLE001 - cierre debe continuar
                logger.error(f"Error cerrando cliente Pulsar: {e}")
            self.client = None

    def _procesar_pendientes(self) -> None:
        """Procesar entradas PENDIENTE del Outbox."""
        session: Session = self.session_factory()
        try:
            # Leer salidas pendientes
            stmt = select(OutboxORM).where(OutboxORM.estado == "PENDIENTE").limit(10)
            salidas_pendientes = session.execute(stmt).scalars().all()

            if not salidas_pendientes:
                return

            logger.info(f"Procesando {len(salidas_pendientes)} salidas pendientes")

            for salida in salidas_pendientes:
                try:
                    self._publicar_salida(session, salida)
                except Exception:
                    logger.exception("Error publicando salida %s (tipo=%s)", salida.id, salida.tipo)
                    # Continuar con la siguiente; la salida permanece PENDIENTE

        finally:
            session.close()

    def _publicar_salida(self, session: Session, salida: OutboxORM) -> None:
        tipo_salida = salida.tipo

        producer = self.producers.get(tipo_salida)
        if producer is None:
            logger.error(f"No hay productor para tipo {tipo_salida}")
            return

        record = self._record_para_salida(salida)
        if record is None:
            logger.error("No hay Record Avro para tipo %s", tipo_salida)
            return

        try:
            message_id = producer.send(record, partition_key=str(record.id_trabajo))
            logger.info(
                f"Salida publicada: tipo={tipo_salida}, id={salida.id}, message_id={message_id}"
            )

            salida.estado = "PROCESADA"
            salida.procesado_en = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            session.commit()
            logger.info(f"Salida {salida.id} marcada como PROCESADA")

        except Exception:
            logger.exception("Error publicando salida %s", salida.id)
            session.rollback()
            raise

    @staticmethod
    def _record_para_salida(
        salida: OutboxORM,
    ) -> TrabajoCreadoV1 | SolicitarCotizacionV1 | None:
        record_types: dict[str, type[TrabajoCreadoV1 | SolicitarCotizacionV1]] = {
            "TrabajoCreado.v1": TrabajoCreadoV1,
            "SolicitarCotizacion.v1": SolicitarCotizacionV1,
        }
        record_cls = record_types.get(salida.tipo)
        if record_cls is None:
            return None
        return record_cls(**dict(salida.payload))
