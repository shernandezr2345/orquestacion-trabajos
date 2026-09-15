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
    )


def destinos(settings: Settings) -> dict[str, str]:
    prefix = f"persistent://{settings.pulsar_tenant}/{settings.pulsar_namespace}"
    return {
        "TrabajoCreado.v1": f"{prefix}/trabajo-creado-v1",
        "SolicitarCotizacion.v1": f"{prefix}/solicitar-cotizacion-v1",
    }
