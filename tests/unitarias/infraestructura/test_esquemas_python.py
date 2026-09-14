from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pulsar.schema import AvroSchema, Record

from orquestacion_trabajos.infraestructura.esquemas_python.v1.entrada import (
    SolicitudDePartnerListaParaAtencionV1,
)
from orquestacion_trabajos.infraestructura.esquemas_python.v1.orquestacion import (
    SolicitarCotizacionV1,
    TrabajoCreadoV1,
)

ROOT = Path(__file__).parents[3]


def _schema_path(name: str) -> Path:
    return ROOT / "src" / "orquestacion_trabajos" / "infraestructura" / "esquemas" / name


def _normalizar_schema(schema: dict[str, object]) -> dict[str, object]:
    fields = cast(list[dict[str, object]], schema["fields"])
    return {
        "type": schema["type"],
        "name": schema["name"],
        "namespace": schema.get("namespace"),
        "fields": [
            {key: field[key] for key in ("name", "type", "default") if key in field}
            for field in fields
        ],
    }


def test_records_corresponden_exactamente_con_los_avsc() -> None:
    contratos: list[tuple[type[Record], str]] = [
        (SolicitudDePartnerListaParaAtencionV1, "solicitud_de_partner_lista_v1.avsc"),
        (TrabajoCreadoV1, "trabajo_creado_v1.avsc"),
        (SolicitarCotizacionV1, "solicitar_cotizacion_v1.avsc"),
    ]

    for record_cls, filename in contratos:
        esperado = cast(
            dict[str, object],
            json.loads(_schema_path(filename).read_text(encoding="utf-8")),
        )
        generado = cast(dict[str, object], record_cls.schema())
        assert _normalizar_schema(generado) == _normalizar_schema(esperado)


def test_solicitud_record_instancia_payload_valido_y_default_opcional() -> None:
    record = SolicitudDePartnerListaParaAtencionV1(
        event_id="evt-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        referencia_externa="ref-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        id_politica="pol-1",
        version_politica=1,
        version_solicitud=2,
    )

    assert record.tipo == "SolicitudDePartnerListaParaAtencion.v1"
    assert record.version_contrato == 1
    assert record.aprobacion_previa is None


def test_records_de_orquestacion_aplican_defaults() -> None:
    trabajo = TrabajoCreadoV1(
        event_id="evt-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        causacion="evt-entrada",
        id_trabajo="trab-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        id_peticion="trab-1",
        referencia_externa="ref-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        id_politica="pol-1",
        version_politica=1,
        creado_en="2026-09-13T00:00:00Z",
    )
    comando = SolicitarCotizacionV1(
        command_id="cmd-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        causacion="evt-entrada",
        id_peticion="trab-1",
        id_trabajo="trab-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        id_politica="pol-1",
        version_politica=1,
    )

    assert trabajo.estado == "PENDIENTE_COTIZACION"
    assert trabajo.version_trabajo == 1
    assert comando.tipo == "SolicitarCotizacion.v1"
    assert comando.version_contrato == 1


def test_campos_requeridos_estan_marcados_como_requeridos() -> None:
    for record_cls in (
        SolicitudDePartnerListaParaAtencionV1,
        TrabajoCreadoV1,
        SolicitarCotizacionV1,
    ):
        fields = record_cls._fields
        required_fields = [name for name, field in fields.items() if field._required]
        assert required_fields


def test_no_se_acepta_none_en_un_campo_requerido() -> None:
    with pytest.raises(TypeError):
        SolicitarCotizacionV1(
            command_id=None,
            instante="2026-09-13T00:00:00Z",
            correlacion="sol-1",
            causacion="evt-entrada",
            id_peticion="trab-1",
            id_trabajo="trab-1",
            id_solicitud="sol-1",
            id_partner="partner-1",
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
            id_politica="pol-1",
            version_politica=1,
        )


def test_avro_schema_se_construye_y_hace_round_trip_binario() -> None:
    entrada = SolicitudDePartnerListaParaAtencionV1(
        event_id="evt-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        referencia_externa="ref-1",
        categoria="SINIESTRO",
        tipo_solicitud="SINIESTRO",
        tipo_red="GENERAL_HDA",
        id_politica="pol-1",
        version_politica=1,
        version_solicitud=2,
    )
    records: list[Record] = [
        entrada,
        TrabajoCreadoV1(
            event_id="evt-2",
            instante="2026-09-13T00:00:00Z",
            correlacion="sol-1",
            causacion="evt-1",
            id_trabajo="trab-1",
            id_solicitud="sol-1",
            id_partner="partner-1",
            id_peticion="trab-1",
            referencia_externa="ref-1",
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
            id_politica="pol-1",
            version_politica=1,
            creado_en="2026-09-13T00:00:00Z",
        ),
        SolicitarCotizacionV1(
            command_id="cmd-1",
            instante="2026-09-13T00:00:00Z",
            correlacion="sol-1",
            causacion="evt-1",
            id_peticion="trab-1",
            id_trabajo="trab-1",
            id_solicitud="sol-1",
            id_partner="partner-1",
            categoria="SINIESTRO",
            tipo_solicitud="SINIESTRO",
            tipo_red="GENERAL_HDA",
            id_politica="pol-1",
            version_politica=1,
        ),
    ]

    for record in records:
        schema = AvroSchema(type(record))
        encoded = schema.encode(record)
        decoded = schema.decode(encoded)
        assert decoded == record

    assert entrada.aprobacion_previa is None
