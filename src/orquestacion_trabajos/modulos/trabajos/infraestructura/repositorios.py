from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from orquestacion_trabajos.modulos.trabajos.aplicacion.consultas import (
    FiltroTrabajos,
    ResultadoCotizacionConsulta,
    TrabajoConsulta,
)
from orquestacion_trabajos.modulos.trabajos.dominio.entidades import Trabajo
from orquestacion_trabajos.modulos.trabajos.dominio.repositorios import RepositorioTrabajos
from orquestacion_trabajos.modulos.trabajos.infraestructura.mapeadores import TrabajoMapper
from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import (
    TrabajoORM,
)


class ConcurrencyConflictError(RuntimeError):
    pass


class SqlAlchemyRepositorioTrabajos(RepositorioTrabajos):
    def __init__(self, session: Session) -> None:
        self._session = session
        self._loaded_versions: dict[str, int] = {}

    def _sesion(self) -> Session:
        return self._session

    def guardar(self, trabajo: Trabajo) -> None:
        session = self._sesion()
        try:
            row = session.get(TrabajoORM, str(trabajo.id))
            mapped = TrabajoMapper.a_orm(trabajo)
            if row is None:
                session.add(mapped)
            else:
                expected_version = self._loaded_versions.get(str(trabajo.id))
                if expected_version is None:
                    raise ValueError("Debe cargar el trabajo antes de actualizarlo")
                saved_id = session.scalar(
                    update(TrabajoORM)
                    .where(TrabajoORM.id == str(trabajo.id), TrabajoORM.version == expected_version)
                    .values(
                        estado=mapped.estado,
                        version=mapped.version,
                        resultado_estado=mapped.resultado_estado,
                        resultado_id_peticion=mapped.resultado_id_peticion,
                        resultado_id_cotizacion=mapped.resultado_id_cotizacion,
                        resultado_id_proveedor=mapped.resultado_id_proveedor,
                        resultado_categoria=mapped.resultado_categoria,
                        resultado_tipo_red=mapped.resultado_tipo_red,
                        resultado_importe_menor=mapped.resultado_importe_menor,
                        resultado_moneda=mapped.resultado_moneda,
                        resultado_motivo=mapped.resultado_motivo,
                    )
                    .returning(TrabajoORM.id)
                )
                if saved_id is None:
                    raise ConcurrencyConflictError("Conflicto de concurrencia al guardar trabajo")
            self._loaded_versions[str(trabajo.id)] = trabajo.version

        except IntegrityError as exc:
            raise ValueError("Conflicto de unicidad al guardar trabajo") from exc

    def obtener_por_id(self, trabajo_id: str) -> Trabajo | None:
        session = self._sesion()
        row = session.get(TrabajoORM, trabajo_id)
        if row is None:
            return None
        self._loaded_versions[row.id] = row.version
        return TrabajoMapper.desde_orm(row)

    def obtener_por_solicitud(self, id_solicitud: str) -> Trabajo | None:
        session = self._sesion()
        row = session.execute(
            select(TrabajoORM).where(TrabajoORM.id_solicitud == id_solicitud)
        ).scalar_one_or_none()
        if row is None:
            return None
        self._loaded_versions[row.id] = row.version
        return TrabajoMapper.desde_orm(row)

    def consultar_por_id(self, trabajo_id: str) -> TrabajoConsulta | None:
        row = self._sesion().get(TrabajoORM, trabajo_id)
        return self._a_consulta(row) if row is not None else None

    def consultar(self, filtro: FiltroTrabajos) -> list[TrabajoConsulta]:
        stmt = (
            select(TrabajoORM)
            .order_by(TrabajoORM.creado_en.asc(), TrabajoORM.id.asc())
            .limit(filtro.limite)
            .offset(filtro.offset)
        )
        if filtro.id_solicitud is not None:
            stmt = stmt.where(TrabajoORM.id_solicitud == filtro.id_solicitud)

        rows = self._sesion().execute(stmt).scalars().all()
        return [self._a_consulta(row) for row in rows]

    @staticmethod
    def _a_consulta(row: TrabajoORM) -> TrabajoConsulta:
        resultado = None
        if row.resultado_estado is not None:
            resultado = ResultadoCotizacionConsulta(
                estado=row.resultado_estado,
                id_peticion=row.resultado_id_peticion,
                id_cotizacion=row.resultado_id_cotizacion,
                id_proveedor=row.resultado_id_proveedor,
                importe_menor=row.resultado_importe_menor,
                moneda=row.resultado_moneda,
                motivo=row.resultado_motivo,
            )

        return TrabajoConsulta(
            id=row.id,
            estado=row.estado,
            version=row.version,
            creado_en=row.creado_en,
            id_solicitud=row.id_solicitud,
            id_partner=row.id_partner,
            categoria=row.categoria,
            tipo_solicitud=row.tipo_solicitud,
            tipo_red=row.tipo_red,
            referencia_externa=row.referencia_externa,
            id_politica=row.id_politica,
            version_politica=row.version_politica,
            resultado=resultado,
        )
