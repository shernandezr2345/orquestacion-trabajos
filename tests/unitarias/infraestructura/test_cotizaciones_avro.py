from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pulsar.schema import AvroSchema

from orquestacion_trabajos.infraestructura.esquemas_python.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
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


def _registrada() -> CotizacionRegistradaV1:
    return CotizacionRegistradaV1(
        event_id="evt-cot-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        causacion="cmd-1",
        id_peticion="pet-1",
        id_trabajo="trab-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        id_cotizacion="cot-1",
        id_proveedor="prov-1",
        categoria="SINIESTRO",
        tipo_red="GENERAL_HDA",
        importe_menor=15000000,
        moneda="COP",
        version_catalogo=1,
    )


def _rechazada() -> CotizacionRechazadaV1:
    return CotizacionRechazadaV1(
        event_id="evt-rech-1",
        instante="2026-09-13T00:00:00Z",
        correlacion="sol-1",
        causacion="cmd-1",
        id_peticion="pet-1",
        id_trabajo="trab-1",
        id_solicitud="sol-1",
        id_partner="partner-1",
        id_proveedor="prov-1",
        categoria="SINIESTRO",
        tipo_red="GENERAL_HDA",
        motivo="SIN_OFERTA_PARA_CATEGORIA",
        version_catalogo=1,
    )


def test_cotizacion_registrada_corresponde_con_avsc() -> None:
    esperado = cast(
        dict[str, object],
        json.loads(_schema_path("cotizacion_registrada_v1.avsc").read_text(encoding="utf-8")),
    )
    generado = cast(dict[str, object], CotizacionRegistradaV1.schema())
    assert _normalizar_schema(generado) == _normalizar_schema(esperado)


def test_cotizacion_rechazada_corresponde_con_avsc() -> None:
    esperado = cast(
        dict[str, object],
        json.loads(_schema_path("cotizacion_rechazada_v1.avsc").read_text(encoding="utf-8")),
    )
    generado = cast(dict[str, object], CotizacionRechazadaV1.schema())
    assert _normalizar_schema(generado) == _normalizar_schema(esperado)


def test_avro_schema_registrada_construye() -> None:
    assert isinstance(AvroSchema(CotizacionRegistradaV1), AvroSchema)


def test_avro_schema_rechazada_construye() -> None:
    assert isinstance(AvroSchema(CotizacionRechazadaV1), AvroSchema)


def test_round_trip_binario_cotizacion_registrada() -> None:
    record = _registrada()
    schema = AvroSchema(CotizacionRegistradaV1)

    decoded = schema.decode(schema.encode(record))

    assert decoded == record
    assert decoded.importe_menor == 15000000
    assert decoded.moneda == "COP"
    assert decoded.version_cotizacion == 1


def test_round_trip_binario_cotizacion_rechazada() -> None:
    record = _rechazada()
    schema = AvroSchema(CotizacionRechazadaV1)

    decoded = schema.decode(schema.encode(record))

    assert decoded == record
    assert decoded.motivo == "SIN_OFERTA_PARA_CATEGORIA"
    assert decoded.version_cotizacion == 1
