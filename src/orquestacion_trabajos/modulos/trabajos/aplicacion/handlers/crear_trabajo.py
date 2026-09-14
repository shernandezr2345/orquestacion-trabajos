from __future__ import annotations

from config.rutas import rutas

from orquestacion_trabajos.infraestructura.mapeadores_eventos import MapeadorTrabajoAvro
from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import CrearTrabajoCommand
from orquestacion_trabajos.modulos.trabajos.aplicacion.idempotencia import InMemoryIdempotencia
from orquestacion_trabajos.modulos.trabajos.aplicacion.registro_salidas import (
    RegistroSalidas,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import UnidadTrabajo
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
)
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos


class CrearTrabajoHandler:
    def __init__(
        self,
        repositorio: RepositorioTrabajos,
        unidad_trabajo: UnidadTrabajo,
        registro_salidas: RegistroSalidas,
        idempotencia: InMemoryIdempotencia,
    ) -> None:
        self.repositorio = repositorio
        self.unidad_trabajo = unidad_trabajo
        self.registro_salidas = registro_salidas
        self.idempotencia = idempotencia

    def ejecutar(self, comando: CrearTrabajoCommand) -> Trabajo:
        solicitud = comando.solicitud

        clave_evento = f"trabajo:event_id:{solicitud.event_id}"
        clave_solicitud = f"trabajo:solicitud:{solicitud.id_solicitud}"

        if self.repositorio.obtener_por_solicitud(solicitud.id_solicitud) is not None:
            trabajo = self.repositorio.obtener_por_solicitud(solicitud.id_solicitud)
            if trabajo is not None:
                self.idempotencia.registrar(clave_evento, solicitud)
                return trabajo

        origen = OrigenSolicitud(
            id_solicitud=solicitud.id_solicitud,
            id_partner=solicitud.id_partner,
            categoria=solicitud.categoria,
            tipo_solicitud=solicitud.tipo_solicitud,
            tipo_red=solicitud.tipo_red,
            referencia_externa=solicitud.referencia_externa,
            id_politica=solicitud.id_politica,
            version_politica=solicitud.version_politica,
        )
        condiciones = CondicionesAtencion(
            categoria=solicitud.categoria,
            tipo_solicitud=solicitud.tipo_solicitud,
            tipo_red=solicitud.tipo_red,
        )

        trabajo = Trabajo.crear(origen, condiciones)
        self.idempotencia.registrar(clave_evento, solicitud)
        self.idempotencia.registrar(clave_solicitud, {"id_solicitud": solicitud.id_solicitud})

        self.repositorio.guardar(trabajo)

        trabajo_creado = MapeadorTrabajoAvro.trabajo_a_trabajo_creado(trabajo, solicitud.event_id)
        solicitar_cotizacion = MapeadorTrabajoAvro.trabajo_a_solicitar_cotizacion(
            trabajo, solicitud.event_id
        )
        self.registro_salidas.registrar(
            tipo="TrabajoCreado.v1",
            payload=trabajo_creado,
            destino=rutas.topico_trabajo_creado,
        )
        self.registro_salidas.registrar(
            tipo="SolicitarCotizacion.v1",
            payload=solicitar_cotizacion,
            destino=rutas.topico_solicitar_cotizacion,
        )

        return trabajo
