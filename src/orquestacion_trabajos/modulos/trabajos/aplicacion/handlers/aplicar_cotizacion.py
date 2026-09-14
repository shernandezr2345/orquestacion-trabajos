from __future__ import annotations

from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import AplicarCotizacionCommand
from orquestacion_trabajos.modulos.trabajos.aplicacion.idempotencia import InMemoryIdempotencia
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import ResultadoCotizacion
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos


class AplicarCotizacionHandler:
    def __init__(
        self,
        repositorio: RepositorioTrabajos,
        idempotencia: InMemoryIdempotencia,
    ) -> None:
        self.repositorio = repositorio
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
        return trabajo
