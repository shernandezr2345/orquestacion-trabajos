from collections.abc import Callable
from dataclasses import dataclass

import pulsar
from pulsar.schema import AvroSchema
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from orquestacion_trabajos.config.database import Database
from orquestacion_trabajos.config.persistencia import crear_uow
from orquestacion_trabajos.config.rutas import destinos, fuentes
from orquestacion_trabajos.config.settings import Settings
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.consultar_trabajos import (
    ConsultarTrabajosHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.consumidores import (
    clasificar_error,
    procesador,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.despacho import publicacion
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.cotizaciones import (
    CotizacionRechazadaV1,
    CotizacionRegistradaV1,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.entrada import (
    SolicitudDePartnerListaParaAtencionV1,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.orquestacion import (
    SolicitarCotizacionV1,
    TrabajoCreadoV1,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.repositorios import (
    SqlAlchemyRepositorioTrabajos,
)
from orquestacion_trabajos.seedwork.infraestructura.ciclos import AccionError, FalloPaso
from orquestacion_trabajos.seedwork.infraestructura.consumidor_pulsar import ConsumidorPulsar
from orquestacion_trabajos.seedwork.infraestructura.despacho_outbox import DespachadorOutbox
from orquestacion_trabajos.seedwork.infraestructura.publicador_pulsar import PublicadorPulsar


@dataclass(frozen=True)
class Componente:
    nombre: str
    paso: Callable[[], bool]
    cerrar: Callable[[], None]


def componer_consulta(sesion: Session) -> ConsultarTrabajosHandler:
    return ConsultarTrabajosHandler(SqlAlchemyRepositorioTrabajos(sesion))


def componer_consumidores(base: Database, settings: Settings) -> list[Componente]:
    fabrica = crear_uow(base, settings)
    crear, aplicar = CrearTrabajoHandler(fabrica), AplicarCotizacionHandler(fabrica)
    componentes = []
    schemas = {
        "entrada": SolicitudDePartnerListaParaAtencionV1,
        "registrada": CotizacionRegistradaV1,
        "rechazada": CotizacionRechazadaV1,
    }
    for fuente in fuentes(settings):
        consumidor = ConsumidorPulsar(
            settings.pulsar_url,
            fuente.topico,
            fuente.suscripcion,
            AvroSchema(schemas[fuente.nombre]),
            procesador(fuente.nombre, fuente.suscripcion, crear, aplicar),
            clasificar_error,
        )
        componentes.append(
            Componente(fuente.suscripcion, consumidor.procesar_siguiente, consumidor.cerrar)
        )
    return componentes


def componer_despacho(base: Database, settings: Settings, tipo: str, schema: type) -> Componente:
    destino = destinos(settings)[tipo]
    publicador = PublicadorPulsar(
        settings.pulsar_url, destino, AvroSchema(schema), lambda payload: schema(**payload)
    )
    despacho = DespachadorOutbox(base.session_factory, destino, publicacion(publicador))

    def paso() -> bool:
        try:
            publicador.abrir()
            return despacho.despachar_siguiente()
        except Exception as error:
            accion = (
                AccionError.REINTENTAR
                if isinstance(
                    error,
                    (
                        SQLAlchemyError,
                        OSError,
                        pulsar.Timeout,
                        pulsar.ConnectError,
                        pulsar.NotConnected,
                        pulsar.AlreadyClosed,
                        pulsar.LookupError,
                        pulsar.BrokerPersistenceError,
                        pulsar.ServiceUnitNotReady,
                    ),
                )
                else AccionError.PAUSAR
            )
            raise FalloPaso(accion, {"motivo": type(error).__name__, "destino": destino}) from error

    return Componente(tipo, paso, publicador.cerrar)


def componer_componentes(base: Database, settings: Settings) -> list[Componente]:
    return [
        *componer_consumidores(base, settings),
        componer_despacho(base, settings, "TrabajoCreado.v1", TrabajoCreadoV1),
        componer_despacho(base, settings, "SolicitarCotizacion.v1", SolicitarCotizacionV1),
    ]
