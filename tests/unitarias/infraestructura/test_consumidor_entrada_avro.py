from unittest.mock import Mock

from orquestacion_trabajos.modulos.trabajos.infraestructura.consumidores import procesador
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.entrada import (
    SolicitudDePartnerListaParaAtencionV1,
)


def _record() -> SolicitudDePartnerListaParaAtencionV1:
    return SolicitudDePartnerListaParaAtencionV1(
        tipo="SolicitudDePartnerListaParaAtencion.v1",
        version_contrato=1,
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


def test_entry_adapter_preserves_complete_envelope():
    crear = Mock()
    procesador("entrada", "test", crear, Mock())(Mock(value=Mock(return_value=_record())))
    comando = crear.ejecutar.call_args.args[0]
    assert comando.solicitud.event_id == "evt-1"
    assert '"version_solicitud": 2' in comando.contenido
    assert comando.consumidor == "test"
