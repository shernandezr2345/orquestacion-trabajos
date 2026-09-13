from __future__ import annotations

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import AplicarCotizacionCommand
from orquestacion_trabajos.modulos.trabajos.aplicacion.idempotencia import InMemoryIdempotencia
from orquestacion_trabajos.modulos.trabajos.aplicacion.registro_salidas import (
    InMemoryRegistroSalidas,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.unidad_trabajo import InMemoryUnidadTrabajo
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import ResultadoCotizacion
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos


class AplicarCotizacionHandler:
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

    def ejecutar(self, comando: AplicarCotizacionCommand) -> Trabajo:
        resultado_entrada = comando.resultado
        trabajo = self.repositorio.obtener_por_id(resultado_entrada.id_trabajo)
        if trabajo is None:
            raise ValueError(f"Trabajo {resultado_entrada.id_trabajo} no existe")

        clave_evento = f"cotizacion:event_id:{resultado_entrada.event_id}"
        clave_peticion = f"cotizacion:peticion:{resultado_entrada.id_peticion}"
        self.idempotencia.registrar(clave_evento, resultado_entrada)
        self.idempotencia.registrar(clave_peticion, {"id_peticion": resultado_entrada.id_peticion})

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
        self.repositorio.guardar(trabajo)
        self.unidad_trabajo.confirmar()

        self.registro_salidas.registrar(
            "CotizacionAplicada",
            {
                "id_trabajo": str(trabajo.id),
                "id_solicitud": trabajo.id_solicitud,
                "id_partner": trabajo.id_partner,
                "id_peticion": resultado.id_peticion,
                "id_cotizacion": resultado.id_cotizacion,
                "estado": resultado.estado,
            },
        )
        return trabajo
