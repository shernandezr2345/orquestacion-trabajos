from __future__ import annotations

from datetime import UTC, datetime

from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo, TrabajoEstado
from orquestacion_trabajos.modulos.trabajos.dominio.objetos_valor import (
    CondicionesAtencion,
    OrigenSolicitud,
    ResultadoCotizacion,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import TrabajoORM


class TrabajoMapper:
    @staticmethod
    def a_orm(trabajo: Trabajo) -> TrabajoORM:
        resultado = trabajo.resultado
        return TrabajoORM(
            id=str(trabajo.id),
            id_solicitud=trabajo.id_solicitud,
            id_partner=trabajo.id_partner,
            categoria=trabajo.categoria,
            tipo_solicitud=trabajo.tipo_solicitud,
            tipo_red=trabajo.tipo_red,
            referencia_externa=trabajo.referencia_externa,
            id_politica=trabajo.id_politica,
            version_politica=trabajo.version_politica,
            estado=trabajo.estado.value,
            version=trabajo.version,
            resultado_estado=resultado.estado if resultado is not None else None,
            resultado_id_peticion=resultado.id_peticion if resultado is not None else None,
            resultado_id_cotizacion=resultado.id_cotizacion if resultado is not None else None,
            resultado_id_proveedor=resultado.id_proveedor if resultado is not None else None,
            resultado_categoria=resultado.categoria if resultado is not None else None,
            resultado_tipo_red=resultado.tipo_red if resultado is not None else None,
            resultado_importe_menor=resultado.importe_menor if resultado is not None else None,
            resultado_moneda=resultado.moneda if resultado is not None else None,
            resultado_motivo=resultado.motivo if resultado is not None else None,
        )

    @staticmethod
    def desde_orm(row: TrabajoORM) -> Trabajo:
        resultado = None
        if row.resultado_estado is not None:
            resultado = ResultadoCotizacion(
                id_trabajo=row.id,
                id_solicitud=row.id_solicitud,
                id_partner=row.id_partner,
                id_peticion=row.resultado_id_peticion or "",
                id_cotizacion=row.resultado_id_cotizacion or "",
                id_proveedor=row.resultado_id_proveedor or "",
                estado=row.resultado_estado,
                categoria=row.resultado_categoria or row.categoria,
                tipo_red=row.resultado_tipo_red or row.tipo_red,
                importe_menor=row.resultado_importe_menor,
                moneda=row.resultado_moneda,
                motivo=row.resultado_motivo,
            )

        trabajo = Trabajo(
            origen=OrigenSolicitud(
                id_solicitud=row.id_solicitud,
                id_partner=row.id_partner,
                categoria=row.categoria,
                tipo_solicitud=row.tipo_solicitud,
                tipo_red=row.tipo_red,
                referencia_externa=row.referencia_externa,
                id_politica=row.id_politica,
                version_politica=row.version_politica,
            ),
            condiciones=CondicionesAtencion(
                categoria=row.categoria,
                tipo_solicitud=row.tipo_solicitud,
                tipo_red=row.tipo_red,
            ),
            estado=TrabajoEstado(row.estado),
            resultado=resultado,
            id=row.id,
            version=row.version,
        )
        trabajo.limpiar_eventos()
        return trabajo

    @staticmethod
    def forzar_instante() -> datetime:
        return datetime.now(UTC)
