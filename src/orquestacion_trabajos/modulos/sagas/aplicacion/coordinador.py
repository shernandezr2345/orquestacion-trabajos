from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from orquestacion_trabajos.modulos.sagas.aplicacion.eventos import SagaMessageEnvelope
from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaInstance,
    SagaLog,
    SagaLogResultado,
    SagaLogTipoRegistro,
    SagaStatus,
    SagaStepName,
)
from orquestacion_trabajos.modulos.sagas.infraestructura.unidad_trabajo import (
    UnidadTrabajoSagaTrabajosSQL,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.comandos import (
    AplicarCotizacionCommand,
    CrearTrabajoCommand,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.aplicar_cotizacion import (
    AplicarCotizacionHandler,
)
from orquestacion_trabajos.modulos.trabajos.aplicacion.handlers.crear_trabajo import (
    CrearTrabajoHandler,
)
from orquestacion_trabajos.modulos.trabajos.infraestructura.mapeadores_eventos import (
    MapeadorEventoEntrada,
    MapeadorResultadoCotizacion,
)


class SagaConflictError(ValueError):
    pass


class SagaCoordinator:
    """Coordina transiciones de Saga con una unica transaccion."""

    def __init__(
        self,
        crear_unidad: Callable[[], UnidadTrabajoSagaTrabajosSQL],
        crear_handler: CrearTrabajoHandler,
        aplicar_handler: AplicarCotizacionHandler,
    ) -> None:
        self._crear_unidad = crear_unidad
        self._crear_handler = crear_handler
        self._aplicar_handler = aplicar_handler

    def procesar(self, envelope: SagaMessageEnvelope, *, consumidor: str) -> None:
        with self._crear_unidad() as unidad:
            saga = self._resolver_saga(unidad, envelope)
            if saga is None:
                self._registrar_conflicto(
                    unidad,
                    envelope,
                    detalle="No fue posible resolver una saga para el mensaje recibido",
                )
                unidad.confirmar()
                return

            if self._es_duplicado(unidad, saga, envelope):
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    tipo=SagaLogTipoRegistro.DUPLICATE,
                    resultado=SagaLogResultado.NO_OP_DUPLICATE,
                    detalle="Mensaje duplicado: no se reaplican efectos",
                )
                unidad.confirmar()
                return

            if self._es_tardio(saga):
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    tipo=SagaLogTipoRegistro.LATE,
                    resultado=SagaLogResultado.NO_OP_LATE,
                    detalle="Saga en estado terminal; no se aplican efectos",
                )
                unidad.confirmar()
                return

            if not self._paso_habilitado(saga, envelope):
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    tipo=SagaLogTipoRegistro.OUT_OF_ORDER,
                    resultado=SagaLogResultado.NO_OP_OUT_OF_ORDER,
                    detalle="Evento fuera de orden para el paso actual de la saga",
                )
                unidad.confirmar()
                return

            try:
                self._validar_consistencia(saga, envelope)
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    tipo=SagaLogTipoRegistro.EVENT_RECEIVED,
                    resultado=SagaLogResultado.APPLIED,
                )
                self._ejecutar_transicion(unidad, saga, envelope, consumidor=consumidor)
            except SagaConflictError as error:
                self._registrar_conflicto(unidad, envelope, saga=saga, detalle=str(error))
            unidad.confirmar()

    def _resolver_saga(
        self, unidad: UnidadTrabajoSagaTrabajosSQL, envelope: SagaMessageEnvelope
    ) -> SagaInstance | None:
        if envelope.id_saga is None and envelope.id_solicitud is None:
            return None

        if envelope.id_saga is not None:
            by_saga = unidad.sagas.obtener_por_id_saga(envelope.id_saga)
            if by_saga is None:
                if envelope.tipo_mensaje == "SolicitudDePartnerListaParaAtencion.v1":
                    return None
                return None
            if envelope.id_solicitud and by_saga.id_solicitud != envelope.id_solicitud:
                return by_saga
            if envelope.id_solicitud:
                by_solicitud = unidad.sagas.obtener_por_id_solicitud(envelope.id_solicitud)
                if by_solicitud is not None and by_solicitud.id_saga != by_saga.id_saga:
                    return by_saga
            return by_saga

        by_solicitud = unidad.sagas.obtener_por_id_solicitud(envelope.id_solicitud or "")
        if by_solicitud is None and envelope.tipo_mensaje == "SolicitudDePartnerListaParaAtencion.v1":
            saga = SagaInstance.crear(id_solicitud=envelope.id_solicitud or "")
            unidad.sagas.crear(saga)
            unidad.sesion.flush()
            return saga
        return by_solicitud

    @staticmethod
    def _es_tardio(saga: SagaInstance) -> bool:
        return saga.estado in {SagaStatus.COMPLETED, SagaStatus.COMPENSATED}

    @staticmethod
    def _message_ids(envelope: SagaMessageEnvelope) -> tuple[str | None, str | None]:
        if envelope.message_id.startswith("cmd-"):
            return None, envelope.message_id
        return envelope.message_id, None

    def _es_duplicado(
        self, unidad: UnidadTrabajoSagaTrabajosSQL, saga: SagaInstance, envelope: SagaMessageEnvelope
    ) -> bool:
        if not envelope.message_id:
            return False
        existing = unidad.saga_logs.buscar_por_message_id(
            id_saga=saga.id_saga,
            tipo_mensaje=envelope.tipo_mensaje,
            message_id=envelope.message_id,
        )
        return existing is not None

    def _paso_habilitado(self, saga: SagaInstance, envelope: SagaMessageEnvelope) -> bool:
        esperado = {
            "SolicitudDePartnerListaParaAtencion.v1": SagaStepName.CREAR_TRABAJO,
            "TrabajoCreado.v1": SagaStepName.SOLICITAR_COTIZACION,
            "CotizacionRegistrada.v1": SagaStepName.SOLICITAR_COTIZACION,
            "CotizacionRechazada.v1": SagaStepName.SOLICITAR_COTIZACION,
            "AtencionHabilitadaRegistrada.v1": SagaStepName.COMPLETAR_SAGA,
            "AtencionCanceladaRegistrada.v1": SagaStepName.FINALIZAR_COMPENSACION,
        }.get(envelope.tipo_mensaje)
        if esperado is None:
            return False
        if envelope.tipo_mensaje == "SolicitudDePartnerListaParaAtencion.v1":
            return saga.paso_actual in {SagaStepName.CREAR_TRABAJO, SagaStepName.SOLICITAR_COTIZACION}
        return saga.paso_actual == esperado

    def _validar_consistencia(self, saga: SagaInstance, envelope: SagaMessageEnvelope) -> None:
        if envelope.id_solicitud and saga.id_solicitud != envelope.id_solicitud:
            raise SagaConflictError("id_solicitud inconsistente respecto a la saga")
        if envelope.id_trabajo and saga.id_trabajo and saga.id_trabajo != envelope.id_trabajo:
            raise SagaConflictError("id_trabajo inconsistente respecto a la saga")
        if envelope.correlacion and saga.id_solicitud != envelope.correlacion:
            raise SagaConflictError("correlacion inconsistente respecto a id_solicitud")

    def _ejecutar_transicion(
        self,
        unidad: UnidadTrabajoSagaTrabajosSQL,
        saga: SagaInstance,
        envelope: SagaMessageEnvelope,
        *,
        consumidor: str,
    ) -> None:
        if envelope.tipo_mensaje == "SolicitudDePartnerListaParaAtencion.v1":
            solicitud = MapeadorEventoEntrada.mensaje_a_solicitud(envelope.payload)
            trabajo = self._crear_handler.ejecutar(
                CrearTrabajoCommand(
                    solicitud=solicitud,
                    consumidor=consumidor,
                    contenido=json.dumps(envelope.payload, sort_keys=True, default=str),
                ),
                unidad=unidad,
            )
            unidad.sagas.asignar_id_trabajo(saga, str(trabajo.id))
            unidad.sagas.actualizar_paso(saga, SagaStepName.SOLICITAR_COTIZACION)
            self._registrar(
                unidad,
                saga=saga,
                envelope=envelope,
                tipo=SagaLogTipoRegistro.LOCAL_OPERATION,
                resultado=SagaLogResultado.APPLIED,
                detalle="Trabajo creado/reusado y saga preparada para solicitar cotizacion",
            )
            comando = self._ultimo_payload(unidad, "SolicitarCotizacion.v1")
            if comando is not None:
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=SagaMessageEnvelope(
                        tipo_mensaje="SolicitarCotizacion.v1",
                        message_id=str(comando.get("command_id", "")),
                        payload=comando,
                        id_solicitud=saga.id_solicitud,
                        id_trabajo=saga.id_trabajo,
                        correlacion=str(comando.get("correlacion", "")) or None,
                        causacion=str(comando.get("causacion", "")) or None,
                    ),
                    tipo=SagaLogTipoRegistro.COMMAND_EMITTED,
                    resultado=SagaLogResultado.APPLIED,
                )
            return

        if envelope.tipo_mensaje in {"CotizacionRegistrada.v1", "CotizacionRechazada.v1"}:
            mapper = (
                MapeadorResultadoCotizacion.cotizacion_registrada_a_resultado
                if envelope.tipo_mensaje == "CotizacionRegistrada.v1"
                else MapeadorResultadoCotizacion.cotizacion_rechazada_a_resultado
            )
            self._aplicar_handler.ejecutar(
                AplicarCotizacionCommand(
                    resultado=mapper(envelope.payload),
                    consumidor=consumidor,
                    contenido=json.dumps(envelope.payload, sort_keys=True, default=str),
                ),
                unidad=unidad,
            )
            if envelope.tipo_mensaje == "CotizacionRegistrada.v1":
                unidad.sagas.actualizar_paso(saga, SagaStepName.ABRIR_SEGUIMIENTO)
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    tipo=SagaLogTipoRegistro.IGNORED,
                    resultado=SagaLogResultado.APPLIED,
                    detalle="Siguiente comando AbrirSeguimientoTrabajo.v1 pendiente de contrato",
                )
            else:
                unidad.sagas.actualizar_paso(saga, SagaStepName.CANCELAR_TRABAJO_POR_RECHAZO)
                self._registrar(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    tipo=SagaLogTipoRegistro.IGNORED,
                    resultado=SagaLogResultado.APPLIED,
                    detalle="Ruta final para CotizacionRechazada permanece como decision pendiente",
                )
            self._registrar(
                unidad,
                saga=saga,
                envelope=envelope,
                tipo=SagaLogTipoRegistro.LOCAL_OPERATION,
                resultado=SagaLogResultado.APPLIED,
                detalle="Resultado de cotizacion aplicado sobre Trabajo",
            )
            return

        if envelope.tipo_mensaje == "AtencionHabilitadaRegistrada.v1":
            estado_anterior = saga.estado
            unidad.sagas.actualizar_estado(saga, SagaStatus.COMPLETED)
            unidad.sagas.actualizar_paso(saga, SagaStepName.COMPLETAR_SAGA)
            self._registrar_estado(
                unidad,
                saga=saga,
                envelope=envelope,
                estado_anterior=estado_anterior,
                estado_nuevo=SagaStatus.COMPLETED,
            )
            return

        if envelope.tipo_mensaje == "AtencionCanceladaRegistrada.v1":
            estado_anterior = saga.estado
            unidad.sagas.actualizar_estado(saga, SagaStatus.COMPENSATED)
            unidad.sagas.actualizar_paso(saga, SagaStepName.FINALIZAR_COMPENSACION)
            self._registrar_estado(
                unidad,
                saga=saga,
                envelope=envelope,
                estado_anterior=estado_anterior,
                estado_nuevo=SagaStatus.COMPENSATED,
            )
            return

        raise SagaConflictError("Tipo de mensaje no soportado en esta fase del coordinator")

    def _registrar_conflicto(
        self,
        unidad: UnidadTrabajoSagaTrabajosSQL,
        envelope: SagaMessageEnvelope,
        *,
        saga: SagaInstance | None = None,
        detalle: str,
    ) -> None:
        if saga is None:
            if envelope.id_solicitud is None:
                return
            saga = unidad.sagas.obtener_por_id_solicitud(envelope.id_solicitud)
        if saga is None:
            return
        self._registrar(
            unidad,
            saga=saga,
            envelope=envelope,
            tipo=SagaLogTipoRegistro.EVENT_RECEIVED,
            resultado=SagaLogResultado.REJECTED_CONFLICT,
            detalle=detalle,
        )

    def _registrar_estado(
        self,
        unidad: UnidadTrabajoSagaTrabajosSQL,
        *,
        saga: SagaInstance,
        envelope: SagaMessageEnvelope,
        estado_anterior: SagaStatus,
        estado_nuevo: SagaStatus,
    ) -> None:
        self._registrar(
            unidad,
            saga=saga,
            envelope=envelope,
            tipo=SagaLogTipoRegistro.STATE_CHANGED,
            resultado=SagaLogResultado.APPLIED,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
        )

    def _registrar(
        self,
        unidad: UnidadTrabajoSagaTrabajosSQL,
        *,
        saga: SagaInstance,
        envelope: SagaMessageEnvelope,
        tipo: SagaLogTipoRegistro,
        resultado: SagaLogResultado,
        detalle: str | None = None,
        estado_anterior: SagaStatus | None = None,
        estado_nuevo: SagaStatus | None = None,
    ) -> None:
        tipos_con_identidad_mensaje = {
            SagaLogTipoRegistro.EVENT_RECEIVED,
            SagaLogTipoRegistro.COMMAND_EMITTED,
            SagaLogTipoRegistro.EVENT_EMITTED,
        }
        if tipo in tipos_con_identidad_mensaje:
            event_id, command_id = self._ids_desde_envelope(envelope)
        else:
            event_id, command_id = None, None
        unidad.saga_logs.registrar(
            SagaLog(
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=saga.id_trabajo,
                paso=saga.paso_actual.value,
                tipo_registro=tipo,
                tipo_mensaje=envelope.tipo_mensaje,
                event_id=event_id,
                command_id=command_id,
                causacion=envelope.causacion,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                resultado=resultado,
                detalle=detalle,
                created_at=SagaLog.now_iso(),
            )
        )

    @staticmethod
    def _ids_desde_envelope(envelope: SagaMessageEnvelope) -> tuple[str | None, str | None]:
        if envelope.tipo_mensaje.endswith(".v1") and envelope.tipo_mensaje.startswith("Solicitar"):
            return None, envelope.message_id
        if envelope.tipo_mensaje.endswith(".v1") and envelope.tipo_mensaje.startswith("Registrar"):
            return None, envelope.message_id
        if envelope.message_id.startswith("CMD-") or envelope.message_id.startswith("cmd-"):
            return None, envelope.message_id
        return envelope.message_id, None

    @staticmethod
    def _ultimo_payload(
        unidad: UnidadTrabajoSagaTrabajosSQL, tipo: str
    ) -> dict[str, Any] | None:
        payloads = unidad.outbox_por_tipo(tipo=tipo)
        if not payloads:
            return None
        return payloads[-1]
