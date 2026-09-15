from unittest.mock import Mock

import pytest

from orquestacion_trabajos.modulos.trabajos.infraestructura.consumidores import procesador
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)


def _registrada(
    id_trabajo: str = "trab-1",
    event_id: str = "evt-1",
    importe_menor: int = 15000000,
    id_solicitud: str = "sol-1",
) -> CotizacionRegistradaV1:
    return CotizacionRegistradaV1(
        tipo="CotizacionRegistrada.v1",
        version_contrato=1,
        version_cotizacion=1,
        event_id=event_id,
        instante="2026-09-13T00:00:00Z",
        correlacion=id_solicitud,
        causacion="cmd-1",
        id_peticion=id_trabajo,
        id_trabajo=id_trabajo,
        id_solicitud=id_solicitud,
        id_partner="partner-1",
        id_cotizacion="cot-1",
        id_proveedor="prov-1",
        categoria="SINIESTRO",
        tipo_red="GENERAL_HDA",
        importe_menor=importe_menor,
        moneda="COP",
        version_catalogo=1,
    )


def _rechazada(
    id_trabajo: str = "trab-1", event_id: str = "evt-2", id_solicitud: str = "sol-1"
) -> CotizacionRechazadaV1:
    return CotizacionRechazadaV1(
        tipo="CotizacionRechazada.v1",
        version_contrato=1,
        version_cotizacion=1,
        event_id=event_id,
        instante="2026-09-13T00:00:00Z",
        correlacion=id_solicitud,
        causacion="cmd-1",
        id_peticion=id_trabajo,
        id_trabajo=id_trabajo,
        id_solicitud=id_solicitud,
        id_partner="partner-1",
        motivo="SIN_OFERTA_PARA_CATEGORIA",
        version_catalogo=1,
    )


@pytest.mark.parametrize(
    "tipo,record,estado",
    [("registrada", _registrada(), "ACEPTADA"), ("rechazada", _rechazada(), "RECHAZADA")],
)
def test_result_adapter_preserves_envelope(tipo, record, estado):
    aplicar = Mock()
    procesador(tipo, "test", Mock(), aplicar)(Mock(value=Mock(return_value=record)))
    comando = aplicar.ejecutar.call_args.args[0]
    assert comando.resultado.estado == estado
    assert '"causacion": "cmd-1"' in comando.contenido
    assert comando.consumidor == "test"
