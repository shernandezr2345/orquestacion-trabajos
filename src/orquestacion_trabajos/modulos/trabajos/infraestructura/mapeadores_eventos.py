from datetime import UTC, datetime
from uuid import uuid4

from orquestacion_trabajos.modulos.trabajos.aplicacion.mensajes import (
    MapeadorEventoEntrada,
    MapeadorResultadoCotizacion,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo

__all__ = ["MapeadorEventoEntrada", "MapeadorResultadoCotizacion", "MapeadorTrabajoAvro"]


class MapeadorTrabajoAvro:
    """Traducir Trabajo a mensajes Avro para publicación."""

    @staticmethod
    def trabajo_a_solicitar_cotizacion(
        trabajo: Trabajo, evento_origen_id: str
    ) -> dict[str, object]:
        """Traducir Trabajo a comando SolicitarCotizacion.v1."""
        ahora = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "command_id": str(uuid4()),
            "tipo": "SolicitarCotizacion.v1",
            "version_contrato": 1,
            "instante": ahora,
            "correlacion": trabajo.id_solicitud,
            "causacion": evento_origen_id,
            "id_peticion": str(trabajo.id),
            "id_trabajo": str(trabajo.id),
            "id_solicitud": trabajo.id_solicitud,
            "id_partner": trabajo.id_partner,
            "categoria": trabajo.categoria,
            "tipo_solicitud": trabajo.tipo_solicitud,
            "tipo_red": trabajo.tipo_red,
            "id_politica": trabajo.id_politica,
            "version_politica": trabajo.version_politica,
        }

    @staticmethod
    def trabajo_a_trabajo_creado(trabajo: Trabajo, evento_origen_id: str) -> dict[str, object]:
        """Traducir Trabajo a evento TrabajoCreado.v1."""
        ahora = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "event_id": str(uuid4()),
            "tipo": "TrabajoCreado.v1",
            "version_contrato": 1,
            "instante": ahora,
            "correlacion": trabajo.id_solicitud,
            "causacion": evento_origen_id,
            "id_trabajo": str(trabajo.id),
            "id_solicitud": trabajo.id_solicitud,
            "id_partner": trabajo.id_partner,
            "id_peticion": str(trabajo.id),
            "referencia_externa": trabajo.referencia_externa,
            "categoria": trabajo.categoria,
            "tipo_solicitud": trabajo.tipo_solicitud,
            "tipo_red": trabajo.tipo_red,
            "id_politica": trabajo.id_politica,
            "version_politica": trabajo.version_politica,
            "creado_en": ahora,
            "estado": trabajo.estado.value,
            "version_trabajo": trabajo.version,
        }
