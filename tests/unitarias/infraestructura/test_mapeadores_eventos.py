from __future__ import annotations

import json

import pytest

from orquestacion_trabajos.infraestructura.mapeadores_eventos import (
    MapeadorEventoEntrada,
    MapeadorResultadoCotizacion,
    MapeadorTrabajoAvro,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
)


class TestMapeadorEventoEntrada:
    """Pruebas del mapeador de eventos de Entrada."""

    def test_mensaje_a_solicitud_convierte_correctamente(self):
        """Traducir mensaje Avro a SolicitudListaParaAtencion."""
        mensaje = {
            "event_id": "evt-123",
            "id_solicitud": "sol-456",
            "id_partner": "partner-789",
            "categoria": "SINIESTRO",
            "tipo_solicitud": "SINIESTRO",
            "tipo_red": "GENERAL_HDA",
            "referencia_externa": "ref-001",
            "id_politica": "pol-123",
            "version_politica": 1,
        }

        solicitud = MapeadorEventoEntrada.mensaje_a_solicitud(mensaje)

        assert solicitud.event_id == "evt-123"
        assert solicitud.id_solicitud == "sol-456"
        assert solicitud.id_partner == "partner-789"
        assert solicitud.categoria == "SINIESTRO"
        assert solicitud.tipo_red == "GENERAL_HDA"

    def test_mensaje_a_solicitud_maneja_campos_faltantes(self):
        """Manejar campos faltantes en mensaje."""
        mensaje = {
            "event_id": "evt-123",
            "id_solicitud": "sol-456",
        }

        solicitud = MapeadorEventoEntrada.mensaje_a_solicitud(mensaje)

        assert solicitud.event_id == "evt-123"
        assert solicitud.id_solicitud == "sol-456"
        # Otros campos serán cadena vacía
        assert isinstance(solicitud.id_partner, str)


class TestMapeadorTrabajoAvro:
    """Pruebas del mapeador de Trabajo a Avro."""

    @pytest.fixture
    def trabajo(self):
        """Crear un Trabajo de prueba."""
        origen = OrigenSolicitud(
            id_solicitud="sol-123",
            id_partner="partner-456",
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
            referencia_externa="ref-001",
            id_politica="pol-789",
            version_politica=1,
        )
        condiciones = CondicionesAtencion(
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
        )
        return Trabajo.crear(origen, condiciones)

    def test_trabajo_a_solicitar_cotizacion(self, trabajo):
        """Traducir Trabajo a SolicitarCotizacion.v1."""
        evento_origen_id = "evt-original"

        comando = MapeadorTrabajoAvro.trabajo_a_solicitar_cotizacion(trabajo, evento_origen_id)

        assert comando["tipo"] == "SolicitarCotizacion.v1"
        assert comando["version_contrato"] == 1
        assert comando["id_trabajo"] == str(trabajo.id)
        assert comando["id_solicitud"] == "sol-123"
        assert comando["id_partner"] == "partner-456"
        assert comando["categoria"] == "SINIESTRO"
        assert "command_id" in comando
        assert comando["causacion"] == evento_origen_id

    def test_trabajo_a_trabajo_creado(self, trabajo):
        """Traducir Trabajo a TrabajoCreado.v1."""
        evento_origen_id = "evt-original"

        evento = MapeadorTrabajoAvro.trabajo_a_trabajo_creado(trabajo, evento_origen_id)

        assert evento["tipo"] == "TrabajoCreado.v1"
        assert evento["version_contrato"] == 1
        assert evento["id_trabajo"] == str(trabajo.id)
        assert evento["id_solicitud"] == "sol-123"
        assert evento["estado"] == "PENDIENTE_COTIZACION"
        assert evento["version_trabajo"] == 1
        assert "event_id" in evento
        assert evento["causacion"] == evento_origen_id

    def test_ambos_mapeadores_producen_json_serializable(self, trabajo):
        """Los mapeadores producen datos serializables a JSON."""
        evento_origen_id = "evt-original"

        comando = MapeadorTrabajoAvro.trabajo_a_solicitar_cotizacion(trabajo, evento_origen_id)
        evento = MapeadorTrabajoAvro.trabajo_a_trabajo_creado(trabajo, evento_origen_id)

        # Verificar que pueden ser serializados a JSON
        comando_json = json.dumps(comando)
        evento_json = json.dumps(evento)

        assert isinstance(comando_json, str)
        assert isinstance(evento_json, str)


class TestMapeadorResultadoCotizacion:
    """Pruebas del mapeador de resultados de Cotizaciones."""

    def test_cotizacion_registrada_a_resultado(self):
        """Traducir CotizacionRegistrada.v1 a ResultadoCotizacionEntrada."""
        mensaje = {
            "event_id": "evt-cot-123",
            "id_trabajo": "trab-456",
            "id_solicitud": "sol-789",
            "id_partner": "partner-111",
            "id_peticion": "pet-222",
            "id_cotizacion": "cot-333",
            "id_proveedor": "prov-444",
            "categoria": "SINIESTRO",
            "tipo_red": "GENERAL_HDA",
            "importe_menor": 5000000,
            "moneda": "COP",
        }

        resultado = MapeadorResultadoCotizacion.cotizacion_registrada_a_resultado(mensaje)

        assert resultado.event_id == "evt-cot-123"
        assert resultado.id_trabajo == "trab-456"
        assert resultado.estado == "ACEPTADA"
        assert resultado.importe_menor == 5000000
        assert resultado.moneda == "COP"

    def test_cotizacion_rechazada_a_resultado(self):
        """Traducir CotizacionRechazada.v1 a ResultadoCotizacionEntrada."""
        mensaje = {
            "event_id": "evt-rech-123",
            "id_trabajo": "trab-456",
            "id_solicitud": "sol-789",
            "id_partner": "partner-111",
            "id_peticion": "pet-222",
            "categoria": "SINIESTRO",
            "tipo_red": "GENERAL_HDA",
            "motivo": "SIN_OFERTA_PARA_CATEGORIA",
        }

        resultado = MapeadorResultadoCotizacion.cotizacion_rechazada_a_resultado(mensaje)

        assert resultado.event_id == "evt-rech-123"
        assert resultado.id_trabajo == "trab-456"
        assert resultado.estado == "RECHAZADA"
        assert resultado.motivo == "SIN_OFERTA_PARA_CATEGORIA"
