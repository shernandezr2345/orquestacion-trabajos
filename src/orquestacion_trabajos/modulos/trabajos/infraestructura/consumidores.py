import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from orquestacion_trabajos.modulos.sagas.aplicacion.coordinador import SagaCoordinator
from orquestacion_trabajos.modulos.sagas.aplicacion.eventos import SagaMessageEnvelope
from orquestacion_trabajos.modulos.sagas.infraestructura.repositorios import (
    SagaConcurrencyConflictError,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    AplicarCotizacionCommand,
    CrearTrabajoCommand,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.mapeadores_eventos import (
    MapeadorEventoEntrada,
    MapeadorResultadoCotizacion,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    ConcurrencyConflictError,
)
from orquestacion_trabajos.seedwork.aplicacion.excepciones import ColisionPersistencia
from orquestacion_trabajos.seedwork.infraestructura.ciclos import AccionError


def clasificar_error(error: Exception) -> AccionError:
    if isinstance(
        error,
        (
            OperationalError,
            PoolTimeout,
            InterfaceError,
            ColisionPersistencia,
            ConcurrencyConflictError,
            SagaConcurrencyConflictError,
            ConnectionError,
            OSError,
        ),
    ):
        return AccionError.REINTENTAR
    return AccionError.PAUSAR


def procesador(
    tipo: str,
    suscripcion: str,
    crear: CrearTrabajoHandler,
    aplicar: AplicarCotizacionHandler,
    coordinator: SagaCoordinator | None = None,
) -> Callable[[Any], None]:
    def procesar(mensaje: Any) -> None:
        record = mensaje.value()
        datos = (
            record
            if isinstance(record, dict)
            else {nombre: getattr(record, nombre) for nombre in record._fields}
        )
        contenido = json.dumps(datos, sort_keys=True, default=str)

        if coordinator is not None:
            tipo_mensaje = str(datos.get("tipo", ""))
            message_id = str(datos.get("event_id") or datos.get("command_id") or "")
            coordinator.procesar(
                SagaMessageEnvelope(
                    tipo_mensaje=tipo_mensaje,
                    message_id=message_id,
                    payload=datos,
                    id_saga=str(datos.get("id_saga", "")) or None,
                    id_solicitud=str(datos.get("id_solicitud", "")) or None,
                    id_trabajo=str(datos.get("id_trabajo", "")) or None,
                    correlacion=str(datos.get("correlacion", "")) or None,
                    causacion=str(datos.get("causacion", "")) or None,
                ),
                consumidor=suscripcion,
            )
            return

        if tipo == "entrada":
            solicitud = MapeadorEventoEntrada.mensaje_a_solicitud(datos)
            crear.ejecutar(CrearTrabajoCommand(solicitud, suscripcion, contenido))
        else:
            mapper = (
                MapeadorResultadoCotizacion.cotizacion_registrada_a_resultado
                if tipo == "registrada"
                else MapeadorResultadoCotizacion.cotizacion_rechazada_a_resultado
            )
            aplicar.ejecutar(
                AplicarCotizacionCommand(mapper(datos), consumidor=suscripcion, contenido=contenido)
            )

    return procesar
