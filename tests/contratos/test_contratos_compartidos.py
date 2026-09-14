import json
from pathlib import Path

import pytest
from pulsar.schema import AvroSchema

from orquestacion_trabajos.infraestructura.esquemas_python.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)
from orquestacion_trabajos.infraestructura.esquemas_python.v1.entrada import (
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


def test_topics_use_configured_namespace(monkeypatch):
    from dataclasses import replace

    import config.rutas as route_module

    monkeypatch.setattr(
        route_module,
        "settings",
        replace(route_module.settings, pulsar_namespace="contracts-isolated"),
    )
    routes = route_module.RutasPulsar()
    assert (
        routes.topico_solicitud_entrada
        == "persistent://public/contracts-isolated/solicitud-partner-lista-v1"
    )
    assert (
        routes.topico_trabajo_creado == "persistent://public/contracts-isolated/trabajo-creado-v1"
    )
