from __future__ import annotations

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import CrearTrabajoCommand
from orquestacion_trabajos.modulos.trabajos.aplicacion.idempotencia import InMemoryIdempotencia
from orquestacion_trabajos.modulos.trabajos.aplicacion.registro_salidas import (
    InMemoryRegistroSalidas,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import InMemoryUnidadTrabajo
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
        unidad_trabajo: InMemoryUnidadTrabajo,
        registro_salidas: InMemoryRegistroSalidas,
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
        self.unidad_trabajo.confirmar()

        self.registro_salidas.registrar(
            "TrabajoCreado.v1",
            {
                "id_trabajo": str(trabajo.id),
                "id_solicitud": trabajo.id_solicitud,
                "id_partner": trabajo.id_partner,
                "categoria": trabajo.categoria,
                "tipo_solicitud": trabajo.tipo_solicitud,
                "tipo_red": trabajo.tipo_red,
                "referencia_externa": trabajo.referencia_externa,
                "id_politica": trabajo.id_politica,
                "version_politica": trabajo.version_politica,
                "version_trabajo": trabajo.version,
            },
        )
        self.registro_salidas.registrar(
            "SolicitarCotizacion.v1",
            {
                "id_peticion": str(trabajo.id),
                "id_trabajo": str(trabajo.id),
                "id_solicitud": trabajo.id_solicitud,
                "id_partner": trabajo.id_partner,
                "categoria": trabajo.categoria,
                "tipo_solicitud": trabajo.tipo_solicitud,
                "tipo_red": trabajo.tipo_red,
                "id_politica": trabajo.id_politica,
                "version_politica": trabajo.version_politica,
            },
        )

        return trabajo
