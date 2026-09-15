#!/usr/bin/env python3
"""Script para preparar el entorno de Pulsar: crear tópicos y suscripciones."""

from __future__ import annotations

import argparse
import logging
import sys

import pulsar

from orquestacion_trabajos.config.rutas import destinos, fuentes
from orquestacion_trabajos.config.settings import Settings

settings = Settings.from_environment()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PreparadorPulsar:
    """Preparar tópicos y suscripciones en Pulsar."""

    def __init__(self, url_pulsar: str) -> None:
        self.url_pulsar = url_pulsar
        self.client: pulsar.Client | None = None
        self.admin_client = None

    def conectar(self) -> bool:
        """Conectar a Pulsar."""
        try:
            logger.info(f"Conectando a Pulsar en {self.url_pulsar}")
            self.client = pulsar.Client(self.url_pulsar)
            logger.info("Conexión a Pulsar exitosa")
            return True
        except pulsar.PulsarException as e:
            logger.error(f"Error conectando a Pulsar: {e}")
            return False

    def crear_topicos(self) -> bool:
        """Crear tópicos necesarios."""
        if self.client is None:
            logger.error("Cliente Pulsar no conectado")
            return False

        topicos = [fuente.topico for fuente in fuentes(settings)] + list(
            destinos(settings).values()
        )

        for topico in topicos:
            try:
                # Crear productor para verificar/crear tópico
                producer = self.client.create_producer(topico)
                producer.close()
                logger.info(f"✓ Tópico verificado/creado: {topico}")
            except pulsar.PulsarException as e:
                logger.error(f"✗ Error creando tópico {topico}: {e}")
                return False

        return True

    def crear_suscripciones(self) -> bool:
        """Crear suscripciones necesarias."""
        if self.client is None:
            logger.error("Cliente Pulsar no conectado")
            return False

        suscripciones = [(fuente.topico, fuente.suscripcion) for fuente in fuentes(settings)]

        for topico, nombre_suscripcion in suscripciones:
            try:
                # Crear consumidor para verificar/crear suscripción
                consumer = self.client.subscribe(
                    topico,
                    subscription_name=nombre_suscripcion,
                    consumer_type=pulsar.ConsumerType.Shared,
                )
                consumer.close()
                logger.info(f"✓ Suscripción verificada/creada: {nombre_suscripcion} en {topico}")
            except pulsar.PulsarException as e:
                logger.error(f"✗ Error creando suscripción {nombre_suscripcion} en {topico}: {e}")
                return False

        return True

    def listar_topicos(self) -> bool:
        """Listar tópicos en Pulsar."""
        if self.client is None:
            logger.error("Cliente Pulsar no conectado")
            return False

        topicos_esperados = [fuente.topico for fuente in fuentes(settings)] + list(
            destinos(settings).values()
        )

        logger.info("\nTópicos esperados:")
        for topico in topicos_esperados:
            logger.info(f"  {topico}")

        return True

    def desconectar(self) -> None:
        """Desconectar de Pulsar."""
        if self.client is not None:
            try:
                self.client.close()
                logger.info("Cliente Pulsar cerrado")
            except pulsar.PulsarException as e:
                logger.error(f"Error cerrando cliente: {e}")


def main() -> int:
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(description="Preparar entorno de Pulsar para Orquestación")
    parser.add_argument(
        "--pulsar-url",
        default=settings.pulsar_url,
        help=f"URL de Pulsar (default: {settings.pulsar_url})",
    )
    parser.add_argument(
        "--crear-topicos",
        action="store_true",
        default=True,
        help="Crear tópicos",
    )
    parser.add_argument(
        "--crear-suscripciones",
        action="store_true",
        default=True,
        help="Crear suscripciones",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Listar configuración esperada",
    )

    args = parser.parse_args()

    preparador = PreparadorPulsar(args.pulsar_url)

    try:
        if not preparador.conectar():
            return 1

        if args.listar:
            preparador.listar_topicos()

        if args.crear_topicos:
            logger.info("\nCreando tópicos...")
            if not preparador.crear_topicos():
                return 1

        if args.crear_suscripciones:
            logger.info("\nCreando suscripciones...")
            if not preparador.crear_suscripciones():
                return 1

        logger.info("\n✓ Preparación completada exitosamente")
        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrumpido por usuario")
        return 130
    except (OSError, pulsar.PulsarException):
        logger.exception("Error fatal")
        return 1
    finally:
        preparador.desconectar()


if __name__ == "__main__":
    sys.exit(main())
