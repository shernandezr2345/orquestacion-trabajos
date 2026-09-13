from __future__ import annotations

from orquestacion_trabajos.modulos.trabajos.aplicacion.consultas import (
    FiltroTrabajos,
    PuertoConsultaTrabajos,
    TrabajoConsulta,
)


class ConsultarTrabajosHandler:
    def __init__(self, consulta: PuertoConsultaTrabajos) -> None:
        self.consulta = consulta

    def por_id(self, trabajo_id: str) -> TrabajoConsulta | None:
        return self.consulta.consultar_por_id(trabajo_id)

    def listar(self, filtro: FiltroTrabajos) -> list[TrabajoConsulta]:
        return self.consulta.consultar(filtro)
