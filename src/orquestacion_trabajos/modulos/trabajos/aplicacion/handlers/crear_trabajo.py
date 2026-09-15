from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import CrearTrabajoCommand
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import UnidadTrabajoTrabajos
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
)


class CrearTrabajoHandler:
    def __init__(self, crear_unidad: Callable[[], UnidadTrabajoTrabajos]) -> None:
        self.crear_unidad = crear_unidad

    def ejecutar(self, comando: CrearTrabajoCommand) -> Trabajo:
        with self.crear_unidad() as unidad:
            unidad.preparar_entrada(
                comando.consumidor,
                comando.solicitud.event_id,
                comando.contenido or json.dumps(asdict(comando.solicitud), sort_keys=True),
            )
            solicitud = comando.solicitud

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
            existing = unidad.trabajos.obtener_por_solicitud(solicitud.id_solicitud)
            if existing is not None:
                if existing.origen != origen:
                    raise ValueError("La solicitud existente tiene condiciones diferentes")

                unidad.confirmar()
                return existing

            condiciones = CondicionesAtencion(
                categoria=solicitud.categoria,
                tipo_solicitud=solicitud.tipo_solicitud,
                tipo_red=solicitud.tipo_red,
            )

            trabajo = Trabajo.crear(origen, condiciones)

            unidad.trabajos.guardar(trabajo)

            unidad.registrar_creacion(trabajo, solicitud.event_id)

            unidad.confirmar()
            return trabajo
