from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import AplicarCotizacionCommand
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import UnidadTrabajoTrabajos
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import ResultadoCotizacion


class AplicarCotizacionHandler:
    def __init__(self, crear_unidad: Callable[[], UnidadTrabajoTrabajos]) -> None:
        self.crear_unidad = crear_unidad

    def ejecutar(self, comando: AplicarCotizacionCommand) -> Trabajo:
        with self.crear_unidad() as unidad:
            nuevo = unidad.preparar_entrada(
                comando.consumidor,
                comando.resultado.event_id,
                comando.contenido or json.dumps(asdict(comando.resultado), sort_keys=True),
            )
            resultado_entrada = comando.resultado
            trabajo = unidad.trabajos.obtener_por_id(resultado_entrada.id_trabajo)
            if trabajo is None:
                raise ValueError(f"Trabajo {resultado_entrada.id_trabajo} no existe")

            if not nuevo:
                unidad.confirmar()
                return trabajo

            resultado = ResultadoCotizacion(
                id_trabajo=resultado_entrada.id_trabajo,
                id_solicitud=resultado_entrada.id_solicitud,
                id_partner=resultado_entrada.id_partner,
                id_peticion=resultado_entrada.id_peticion,
                id_cotizacion=resultado_entrada.id_cotizacion,
                id_proveedor=resultado_entrada.id_proveedor,
                estado=resultado_entrada.estado,
                categoria=resultado_entrada.categoria,
                tipo_red=resultado_entrada.tipo_red,
                importe_menor=resultado_entrada.importe_menor,
                moneda=resultado_entrada.moneda,
                motivo=resultado_entrada.motivo,
            )

            trabajo.aplicar_resultado(resultado, version_esperada=comando.version_esperada)
            unidad.trabajos.guardar(trabajo)
            unidad.confirmar()
            return trabajo
