from collections.abc import Callable

from orquestacion_trabajos.seedwork.infraestructura.publicador_pulsar import PublicadorPulsar


def publicacion(publicador: PublicadorPulsar) -> Callable[[str, dict[str, object]], None]:
    def publicar(tipo: str, payload: dict[str, object]) -> None:
        identificador = "command_id" if tipo == "SolicitarCotizacion.v1" else "event_id"
        publicador.publicar(
            payload,
            str(payload["id_trabajo"]),
            {"tipo": tipo, identificador: str(payload[identificador])},
        )

    return publicar
