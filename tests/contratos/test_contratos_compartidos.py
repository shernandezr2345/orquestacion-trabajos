import json
from pathlib import Path

import pytest
from pulsar.schema import AvroSchema

from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.entrada import (
    SolicitudDePartnerListaParaAtencionV1,
)

CONTRACTS = Path(__file__).resolve().parents[2] / "docs/contratos"


@pytest.mark.parametrize(
    "record,name",
    [
        (SolicitudDePartnerListaParaAtencionV1, "solicitud-lista"),
        (CotizacionRegistradaV1, "cotizacion-registrada"),
        (CotizacionRechazadaV1, "cotizacion-rechazada"),
    ],
)
def test_schema_matches_shared_contract(record, name):
    assert record.schema() == json.loads((CONTRACTS / f"{name}-v1.avsc").read_text())


def test_rejection_decodes_without_provider_or_category():
    document = json.loads((CONTRACTS / "cotizacion-rechazada-v1.ejemplo.json").read_text())
    schema = AvroSchema(CotizacionRechazadaV1)
    decoded = schema.decode(schema.encode(CotizacionRechazadaV1(**document)))
    assert decoded.motivo == document["motivo"]


@pytest.mark.parametrize(
    "tenant,namespace", [("public", "default"), ("custom", "contracts-isolated")]
)
def test_routes_preserve_topics_and_subscriptions(tenant, namespace):
    from orquestacion_trabajos.config.rutas import destinos, fuentes
    from orquestacion_trabajos.config.settings import Settings

    settings = Settings(pulsar_tenant=tenant, pulsar_namespace=namespace)
    prefix = f"persistent://{tenant}/{namespace}"
    assert [
        (source.nombre, source.topico, source.suscripcion) for source in fuentes(settings)[:3]
    ] == [
        ("entrada", f"{prefix}/solicitud-partner-lista-v1", "orquestacion-solicitudes-v1"),
        (
            "registrada",
            f"{prefix}/cotizacion-registrada-v1",
            "orquestacion-cotizacion-registrada-v1",
        ),
        ("rechazada", f"{prefix}/cotizacion-rechazada-v1", "orquestacion-cotizacion-rechazada-v1"),
    ]
    assert {
        kind: topic
        for kind, topic in destinos(settings).items()
        if kind in {"TrabajoCreado.v1", "SolicitarCotizacion.v1"}
    } == {
        "TrabajoCreado.v1": f"{prefix}/trabajo-creado-v1",
        "SolicitarCotizacion.v1": f"{prefix}/solicitar-cotizacion-v1",
    }
