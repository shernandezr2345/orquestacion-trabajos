from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import settings


@dataclass(frozen=True)
class RutasPulsar:
    """Definición centralizada de tópicos y suscripciones de Pulsar."""

    # Tópicos de consumo
    topico_solicitud_entrada: str = field(
        default_factory=lambda: (
            f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}/solicitud-partner-lista-v1"
        )
    )
    suscripcion_solicitud_entrada: str = "orquestacion-solicitudes-v1"
    tipo_suscripcion_entrada: str = "Shared"  # Permite múltiples instancias

    # Tópicos de publicación (Outbox)
    topico_solicitar_cotizacion: str = field(
        default_factory=lambda: (
            f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}/solicitar-cotizacion-v1"
        )
    )
    topico_trabajo_creado: str = field(
        default_factory=lambda: (
            f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}/trabajo-creado-v1"
        )
    )

    # Tópicos de consumo de resultados (futuros bloques)
    topico_cotizacion_registrada: str = field(
        default_factory=lambda: (
            f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}/cotizacion-registrada-v1"
        )
    )
    suscripcion_cotizacion_registrada: str = "orquestacion-cotizacion-registrada-v1"
    tipo_suscripcion_cotizacion_registrada: str = "Shared"

    topico_cotizacion_rechazada: str = field(
        default_factory=lambda: (
            f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}/cotizacion-rechazada-v1"
        )
    )
    suscripcion_cotizacion_rechazada: str = "orquestacion-cotizacion-rechazada-v1"
    tipo_suscripcion_cotizacion_rechazada: str = "Shared"


rutas = RutasPulsar()
