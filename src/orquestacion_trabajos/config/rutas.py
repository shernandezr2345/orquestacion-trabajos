from dataclasses import dataclass

from orquestacion_trabajos.config.settings import Settings


@dataclass(frozen=True)
class Fuente:
    nombre: str
    topico: str
    suscripcion: str


def fuentes(settings: Settings) -> tuple[Fuente, ...]:
    prefix = f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}"
    return (
        Fuente(
            "entrada",
            f"{prefix}/solicitud-partner-lista-v1",
            "orquestacion-solicitudes-v1",
        ),
        Fuente(
            "registrada",
            f"{prefix}/cotizacion-registrada-v1",
            "orquestacion-cotizacion-registrada-v1",
        ),
        Fuente(
            "rechazada",
            f"{prefix}/cotizacion-rechazada-v1",
            "orquestacion-cotizacion-rechazada-v1",
        ),
        Fuente(
            "seguimiento-abierto",
            f"{prefix}/seguimiento-trabajo-abierto-v1",
            "orquestacion-seguimiento-trabajo-abierto-v1",
        ),
        Fuente(
            "apertura-fallida",
            f"{prefix}/apertura-seguimiento-fallida-v1",
            "orquestacion-apertura-seguimiento-fallida-v1",
        ),
        Fuente(
            "seguimiento-cancelado",
            f"{prefix}/seguimiento-trabajo-cancelado-v1",
            "orquestacion-seguimiento-trabajo-cancelado-v1",
        ),
        Fuente(
            "atencion-habilitada",
            f"{prefix}/atencion-habilitada-registrada-v1",
            "orquestacion-atencion-habilitada-registrada-v1",
        ),
        Fuente(
            "atencion-cancelada",
            f"{prefix}/atencion-cancelada-registrada-v1",
            "orquestacion-atencion-cancelada-registrada-v1",
        ),
        Fuente(
            "cotizacion-anulada",
            f"{prefix}/cotizacion-anulada-v1",
            "orquestacion-cotizacion-anulada-v1",
        ),
    )


def destinos(settings: Settings) -> dict[str, str]:
    prefix = f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}"
    return {
        "TrabajoCreado.v1": f"{prefix}/trabajo-creado-v1",
        "SolicitarCotizacion.v1": f"{prefix}/solicitar-cotizacion-v1",
        "AbrirSeguimientoTrabajo.v1": f"{prefix}/abrir-seguimiento-trabajo-v1",
        "CancelarSeguimientoTrabajo.v1": f"{prefix}/cancelar-seguimiento-trabajo-v1",
        "RegistrarAtencionHabilitada.v1": f"{prefix}/registrar-atencion-habilitada-v1",
        "RegistrarAtencionCancelada.v1": f"{prefix}/registrar-atencion-cancelada-v1",
        "AnularCotizacion.v1": f"{prefix}/anular-cotizacion-v1",
        "TrabajoCancelado.v1": f"{prefix}/trabajo-cancelado-v1",
    }
