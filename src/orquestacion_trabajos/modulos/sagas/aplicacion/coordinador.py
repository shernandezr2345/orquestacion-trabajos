from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from orquestacion_trabajos.modulos.sagas.aplicacion.eventos import SagaMessageEnvelope
from orquestacion_trabajos.modulos.sagas.aplicacion.unidad_trabajo import UnidadTrabajoSaga
from orquestacion_trabajos.modulos.sagas.dominio.entidades import (
    SagaInstance,
    SagaLog,
    SagaLogResultado,
    SagaLogTipoRegistro,
    SagaStatus,
    SagaStepName,
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
from orquestacion_trabajos.modulos.trabajos.aplicacion.mensajes import (
    MapeadorEventoEntrada,
    MapeadorResultadoCotizacion,
)


class SagaConflictError(ValueError):
    pass


DETALLE_CANCELACION_TRABAJO_LOCAL = "Trabajo cancelado localmente como compensacion"
DETALLE_COMMAND_EMITTED_OUTBOX = "Comando persistido en outbox para publicacion"


class SagaCoordinator:
    def __init__(
        self,
        crear_unidad: Callable[[], UnidadTrabajoSaga],
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
                tipo_comando_causal = self._tipo_comando_causal_esperado(envelope.tipo_mensaje)
                if tipo_comando_causal is not None:
                    self._validar_causacion_con_comando_emitido(
                        unidad,
                        saga=saga,
                        envelope=envelope,
                        tipo_comando=tipo_comando_causal,
                    )
            except SagaConflictError as error:
                self._registrar_conflicto(unidad, envelope, saga=saga, detalle=str(error))
                unidad.confirmar()
                return
            self._registrar(
                unidad,
                saga=saga,
                envelope=envelope,
                tipo=SagaLogTipoRegistro.EVENT_RECEIVED,
                resultado=SagaLogResultado.APPLIED,
            )
            self._ejecutar_transicion(unidad, saga, envelope, consumidor=consumidor)
            unidad.confirmar()

    def _resolver_saga(
        self, unidad: UnidadTrabajoSaga, envelope: SagaMessageEnvelope
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
        if (
            by_solicitud is None
            and envelope.tipo_mensaje == "SolicitudDePartnerListaParaAtencion.v1"
        ):
            saga = SagaInstance.crear(id_solicitud=envelope.id_solicitud or "")
            unidad.sagas.crear(saga)
            unidad.sincronizar()
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
        self, unidad: UnidadTrabajoSaga, saga: SagaInstance, envelope: SagaMessageEnvelope
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
            "SeguimientoTrabajoAbierto.v1": SagaStepName.ABRIR_SEGUIMIENTO,
            "AperturaSeguimientoFallida.v1": SagaStepName.ABRIR_SEGUIMIENTO,
            "AtencionHabilitadaRegistrada.v1": SagaStepName.REGISTRAR_ATENCION_HABILITADA,
            "CotizacionAnulada.v1": SagaStepName.INICIAR_COMPENSACION_APERTURA,
            "AtencionCanceladaRegistrada.v1": SagaStepName.FINALIZAR_COMPENSACION,
            "SeguimientoTrabajoCancelado.v1": SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA,
        }.get(envelope.tipo_mensaje)
        if esperado is None:
            return False
        if envelope.tipo_mensaje == "SolicitudDePartnerListaParaAtencion.v1":
            return saga.paso_actual in {
                SagaStepName.CREAR_TRABAJO,
                SagaStepName.SOLICITAR_COTIZACION,
            }
        if envelope.tipo_mensaje == "AtencionCanceladaRegistrada.v1":
            return saga.paso_actual in {
                SagaStepName.REGISTRAR_ATENCION_CANCELADA,
                SagaStepName.REGISTRAR_ATENCION_CANCELADA_COMPENSACION,
                SagaStepName.FINALIZAR_COMPENSACION,
                SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA,
            }
        if envelope.tipo_mensaje == "SeguimientoTrabajoCancelado.v1":
            return saga.paso_actual in {
                SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA,
                SagaStepName.FINALIZAR_COMPENSACION,
            }
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
        unidad: UnidadTrabajoSaga,
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
            if saga.id_trabajo is not None:
                return
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
            unidad.sincronizar()
            comando = self._ultimo_payload(unidad, "SolicitarCotizacion.v1", saga.id_solicitud)
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
                    detalle=DETALLE_COMMAND_EMITTED_OUTBOX,
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
                unidad.sagas.marcar_seguimiento_apertura_solicitada(saga)
                self._emitir_comando(
                    unidad,
                    saga=saga,
                    tipo_mensaje="AbrirSeguimientoTrabajo.v1",
                    causacion=envelope.message_id,
                    extras={
                        "id_cotizacion": envelope.payload.get("id_cotizacion"),
                        "id_partner": envelope.payload.get("id_partner"),
                    },
                )
            else:
                estado_anterior = saga.estado
                unidad.sagas.actualizar_estado(saga, SagaStatus.COMPENSATING)
                unidad.sagas.actualizar_paso(saga, SagaStepName.CANCELAR_TRABAJO_POR_RECHAZO)
                self._registrar_estado(
                    unidad,
                    saga=saga,
                    envelope=envelope,
                    estado_anterior=estado_anterior,
                    estado_nuevo=SagaStatus.COMPENSATING,
                )
                self._registrar_cancelacion_local_trabajo(unidad, saga=saga, envelope=envelope)
                self._emitir_evento(
                    unidad,
                    saga=saga,
                    tipo_mensaje="TrabajoCancelado.v1",
                    causacion=envelope.message_id,
                    extras={
                        "codigo_motivo": "COTIZACION_RECHAZADA",
                        "detalle": "Compensacion por cotizacion rechazada",
                    },
                )
                unidad.sagas.actualizar_paso(saga, SagaStepName.REGISTRAR_ATENCION_CANCELADA)
                self._emitir_comando(
                    unidad,
                    saga=saga,
                    tipo_mensaje="RegistrarAtencionCancelada.v1",
                    causacion=envelope.message_id,
                    extras={
                        "codigo_motivo": "COTIZACION_RECHAZADA",
                        "detalle": "No hubo propuesta valida de cotizacion",
                    },
                )
                if saga.seguimiento_apertura_solicitada or saga.seguimiento_abierto_confirmado:
                    unidad.sagas.actualizar_paso(saga, SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA)
                    self._emitir_comando(
                        unidad,
                        saga=saga,
                        tipo_mensaje="CancelarSeguimientoTrabajo.v1",
                        causacion=envelope.message_id,
                        extras={
                            "codigo_motivo": "COMPENSACION_COTIZACION_RECHAZADA",
                            "detalle": "Cancelacion por rama compensada",
                        },
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

        if envelope.tipo_mensaje == "SeguimientoTrabajoAbierto.v1":
            unidad.sagas.marcar_seguimiento_abierto_confirmado(saga)
            unidad.sagas.actualizar_paso(saga, SagaStepName.REGISTRAR_ATENCION_HABILITADA)
            self._emitir_comando(
                unidad,
                saga=saga,
                tipo_mensaje="RegistrarAtencionHabilitada.v1",
                causacion=envelope.message_id,
                extras={"id_partner": envelope.payload.get("id_partner")},
            )
            return

        if envelope.tipo_mensaje == "AperturaSeguimientoFallida.v1":
            estado_anterior = saga.estado
            unidad.sagas.actualizar_estado(saga, SagaStatus.COMPENSATING)
            unidad.sagas.actualizar_paso(saga, SagaStepName.INICIAR_COMPENSACION_APERTURA)
            self._registrar_estado(
                unidad,
                saga=saga,
                envelope=envelope,
                estado_anterior=estado_anterior,
                estado_nuevo=SagaStatus.COMPENSATING,
            )
            self._emitir_comando(
                unidad,
                saga=saga,
                tipo_mensaje="AnularCotizacion.v1",
                causacion=envelope.message_id,
                extras={
                    "id_cotizacion": envelope.payload.get("id_cotizacion"),
                    "codigo_motivo": envelope.payload.get("codigo_motivo") or "APERTURA_FALLIDA",
                    "detalle": envelope.payload.get("detalle")
                    or "Compensacion por apertura fallida",
                },
            )
            return

        if envelope.tipo_mensaje == "CotizacionAnulada.v1":
            unidad.sagas.actualizar_paso(saga, SagaStepName.CANCELAR_TRABAJO_COMPENSACION)
            self._registrar_cancelacion_local_trabajo(unidad, saga=saga, envelope=envelope)
            self._emitir_evento(
                unidad,
                saga=saga,
                tipo_mensaje="TrabajoCancelado.v1",
                causacion=envelope.message_id,
                extras={
                    "codigo_motivo": "COMPENSACION_APERTURA_FALLIDA",
                    "detalle": "Cancelacion luego de cotizacion anulada",
                },
            )
            unidad.sagas.actualizar_paso(
                saga, SagaStepName.REGISTRAR_ATENCION_CANCELADA_COMPENSACION
            )
            self._emitir_comando(
                unidad,
                saga=saga,
                tipo_mensaje="RegistrarAtencionCancelada.v1",
                causacion=envelope.message_id,
                extras={
                    "codigo_motivo": "COMPENSACION_APERTURA_FALLIDA",
                    "detalle": "Compensacion de atencion tras apertura fallida",
                },
            )
            if saga.seguimiento_apertura_solicitada or saga.seguimiento_abierto_confirmado:
                unidad.sagas.actualizar_paso(saga, SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA)
                self._emitir_comando(
                    unidad,
                    saga=saga,
                    tipo_mensaje="CancelarSeguimientoTrabajo.v1",
                    causacion=envelope.message_id,
                    extras={
                        "codigo_motivo": "COMPENSACION_APERTURA_FALLIDA",
                        "detalle": "Cancelacion de seguimiento por compensacion",
                    },
                )
            else:
                unidad.sagas.actualizar_paso(saga, SagaStepName.FINALIZAR_COMPENSACION)
            self._cerrar_compensacion_si_corresponde(unidad, saga=saga, envelope=envelope)
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
            self._cerrar_compensacion_si_corresponde(unidad, saga=saga, envelope=envelope)
            return

        if envelope.tipo_mensaje == "SeguimientoTrabajoCancelado.v1":
            self._cerrar_compensacion_si_corresponde(unidad, saga=saga, envelope=envelope)
            return

        raise SagaConflictError("Tipo de mensaje no soportado en esta fase del coordinator")

    def _registrar_conflicto(
        self,
        unidad: UnidadTrabajoSaga,
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
        unidad: UnidadTrabajoSaga,
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
        unidad: UnidadTrabajoSaga,
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
        if envelope.tipo_mensaje in {
            "SolicitarCotizacion.v1",
            "AbrirSeguimientoTrabajo.v1",
            "CancelarSeguimientoTrabajo.v1",
            "AnularCotizacion.v1",
        }:
            return None, envelope.message_id
        if envelope.tipo_mensaje.endswith(".v1") and envelope.tipo_mensaje.startswith("Registrar"):
            return None, envelope.message_id
        if envelope.message_id.startswith("CMD-") or envelope.message_id.startswith("cmd-"):
            return None, envelope.message_id
        return envelope.message_id, None

    @staticmethod
    def _ultimo_payload(
        unidad: UnidadTrabajoSaga, tipo: str, id_solicitud: str
    ) -> dict[str, Any] | None:
        payloads = [
            payload
            for payload in unidad.outbox_por_tipo(tipo=tipo)
            if payload.get("id_solicitud") == id_solicitud
        ]
        if not payloads:
            return None
        return payloads[-1]

    @staticmethod
    def _logs_saga(unidad: UnidadTrabajoSaga, id_saga: str) -> list[SagaLog]:
        return unidad.saga_logs.listar_por_saga(id_saga)

    @staticmethod
    def _tipo_comando_causal_esperado(tipo_mensaje: str) -> str | None:
        return {
            "CotizacionRegistrada.v1": "SolicitarCotizacion.v1",
            "CotizacionRechazada.v1": "SolicitarCotizacion.v1",
            "SeguimientoTrabajoAbierto.v1": "AbrirSeguimientoTrabajo.v1",
            "AperturaSeguimientoFallida.v1": "AbrirSeguimientoTrabajo.v1",
            "CotizacionAnulada.v1": "AnularCotizacion.v1",
            "AtencionHabilitadaRegistrada.v1": "RegistrarAtencionHabilitada.v1",
            "AtencionCanceladaRegistrada.v1": "RegistrarAtencionCancelada.v1",
            "SeguimientoTrabajoCancelado.v1": "CancelarSeguimientoTrabajo.v1",
        }.get(tipo_mensaje)

    def _comando_emitido_por_id(
        self,
        unidad: UnidadTrabajoSaga,
        *,
        saga: SagaInstance,
        command_id: str,
    ) -> SagaLog | None:
        logs = self._logs_saga(unidad, saga.id_saga)
        for log in reversed(logs):
            if (
                log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
                and log.command_id == command_id
            ):
                return log
        return None

    def _validar_causacion_con_comando_emitido(
        self,
        unidad: UnidadTrabajoSaga,
        *,
        saga: SagaInstance,
        envelope: SagaMessageEnvelope,
        tipo_comando: str,
    ) -> None:
        if not envelope.causacion:
            raise SagaConflictError(
                f"causacion ausente; se esperaba referencia a comando {tipo_comando}"
            )
        comando_causal = self._comando_emitido_por_id(
            unidad,
            saga=saga,
            command_id=envelope.causacion,
        )
        if comando_causal is None:
            raise SagaConflictError(
                f"causacion {envelope.causacion} sin command_id emitido por la saga"
            )
        if comando_causal.tipo_mensaje != tipo_comando:
            raise SagaConflictError(
                "causacion inconsistente; "
                f"command_id {envelope.causacion} corresponde a {comando_causal.tipo_mensaje}, "
                f"se esperaba {tipo_comando}"
            )

    def _emitir_comando(
        self,
        unidad: UnidadTrabajoSaga,
        *,
        saga: SagaInstance,
        tipo_mensaje: str,
        causacion: str,
        extras: dict[str, object | None] | None = None,
    ) -> str:
        command_id = str(uuid4())
        payload: dict[str, object] = {
            "command_id": command_id,
            "tipo": tipo_mensaje,
            "version_contrato": 1,
            "instante": SagaLog.now_iso(),
            "correlacion": saga.id_solicitud,
            "causacion": causacion,
            "id_saga": saga.id_saga,
            "id_solicitud": saga.id_solicitud,
        }
        if saga.id_trabajo:
            payload["id_trabajo"] = saga.id_trabajo
        trabajo = unidad.trabajos.obtener_por_id(saga.id_trabajo or "")
        if trabajo is None:
            raise SagaConflictError("Trabajo de saga no encontrado")
        payload["id_partner"] = trabajo.id_partner

        if extras:
            for key, value in extras.items():
                if value is not None:
                    payload[key] = value
        if tipo_mensaje == "AnularCotizacion.v1":
            if trabajo.resultado is None or trabajo.resultado.id_cotizacion is None:
                raise SagaConflictError("Compensacion sin cotizacion persistida")
            payload["id_cotizacion"] = trabajo.resultado.id_cotizacion
            payload["id_peticion"] = trabajo.resultado.id_peticion
        unidad.registrar_mensaje(tipo_mensaje, payload)
        self._registrar(
            unidad,
            saga=saga,
            envelope=SagaMessageEnvelope(
                tipo_mensaje=tipo_mensaje,
                message_id=command_id,
                payload=payload,
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=saga.id_trabajo,
                correlacion=saga.id_solicitud,
                causacion=causacion,
            ),
            tipo=SagaLogTipoRegistro.COMMAND_EMITTED,
            resultado=SagaLogResultado.APPLIED,
            detalle=DETALLE_COMMAND_EMITTED_OUTBOX,
        )
        return command_id

    def _emitir_evento(
        self,
        unidad: UnidadTrabajoSaga,
        *,
        saga: SagaInstance,
        tipo_mensaje: str,
        causacion: str,
        extras: dict[str, object | None] | None = None,
    ) -> str:
        event_id = str(uuid4())
        payload: dict[str, object] = {
            "event_id": event_id,
            "tipo": tipo_mensaje,
            "version_contrato": 1,
            "instante": SagaLog.now_iso(),
            "correlacion": saga.id_solicitud,
            "causacion": causacion,
            "id_saga": saga.id_saga,
            "id_solicitud": saga.id_solicitud,
        }
        if saga.id_trabajo:
            payload["id_trabajo"] = saga.id_trabajo
        trabajo = unidad.trabajos.obtener_por_id(saga.id_trabajo or "")
        if trabajo is None:
            raise SagaConflictError("Trabajo de saga no encontrado")
        payload["id_partner"] = trabajo.id_partner

        if extras:
            for key, value in extras.items():
                if value is not None:
                    payload[key] = value
        payload["cancelado_en"] = payload["instante"]
        payload["version_trabajo"] = trabajo.version
        unidad.registrar_mensaje(tipo_mensaje, payload)
        self._registrar(
            unidad,
            saga=saga,
            envelope=SagaMessageEnvelope(
                tipo_mensaje=tipo_mensaje,
                message_id=event_id,
                payload=payload,
                id_saga=saga.id_saga,
                id_solicitud=saga.id_solicitud,
                id_trabajo=saga.id_trabajo,
                correlacion=saga.id_solicitud,
                causacion=causacion,
            ),
            tipo=SagaLogTipoRegistro.EVENT_EMITTED,
            resultado=SagaLogResultado.APPLIED,
            detalle=DETALLE_COMMAND_EMITTED_OUTBOX,
        )
        return event_id

    def _requiere_cancelar_seguimiento(
        self,
        *,
        saga: SagaInstance,
        logs: list[SagaLog] | None = None,
    ) -> bool:
        if saga.seguimiento_apertura_solicitada or saga.seguimiento_abierto_confirmado:
            return True
        if logs is None:
            return False
        return any(
            log.tipo_registro == SagaLogTipoRegistro.COMMAND_EMITTED
            and log.tipo_mensaje == "CancelarSeguimientoTrabajo.v1"
            and log.resultado == SagaLogResultado.APPLIED
            for log in logs
        )

    def _registrar_cancelacion_local_trabajo(
        self,
        unidad: UnidadTrabajoSaga,
        *,
        saga: SagaInstance,
        envelope: SagaMessageEnvelope,
    ) -> None:
        trabajo = unidad.trabajos.obtener_por_id(saga.id_trabajo or "")
        if trabajo is None:
            raise SagaConflictError("Trabajo de saga no encontrado")
        trabajo.cancelar()
        unidad.trabajos.guardar(trabajo)
        self._registrar(
            unidad,
            saga=saga,
            envelope=envelope,
            tipo=SagaLogTipoRegistro.LOCAL_OPERATION,
            resultado=SagaLogResultado.APPLIED,
            detalle=DETALLE_CANCELACION_TRABAJO_LOCAL,
        )

    def _compensaciones_confirmadas(self, unidad: UnidadTrabajoSaga, *, saga: SagaInstance) -> bool:
        unidad.sincronizar()
        logs = self._logs_saga(unidad, saga.id_saga)
        trabajo_cancelado = any(
            log.tipo_registro == SagaLogTipoRegistro.LOCAL_OPERATION
            and (log.detalle or "") == DETALLE_CANCELACION_TRABAJO_LOCAL
            and log.resultado == SagaLogResultado.APPLIED
            for log in logs
        )
        atencion_cancelada = any(
            log.tipo_registro == SagaLogTipoRegistro.EVENT_RECEIVED
            and log.tipo_mensaje == "AtencionCanceladaRegistrada.v1"
            and log.resultado == SagaLogResultado.APPLIED
            for log in logs
        )
        requiere_cancelar_seguimiento = self._requiere_cancelar_seguimiento(saga=saga, logs=logs)
        seguimiento_cancelado = any(
            log.tipo_registro == SagaLogTipoRegistro.EVENT_RECEIVED
            and log.tipo_mensaje == "SeguimientoTrabajoCancelado.v1"
            and log.resultado == SagaLogResultado.APPLIED
            for log in logs
        )
        return (
            trabajo_cancelado
            and atencion_cancelada
            and (not requiere_cancelar_seguimiento or seguimiento_cancelado)
        )

    def _cerrar_compensacion_si_corresponde(
        self,
        unidad: UnidadTrabajoSaga,
        *,
        saga: SagaInstance,
        envelope: SagaMessageEnvelope,
    ) -> None:
        if self._compensaciones_confirmadas(unidad, saga=saga):
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

        if self._requiere_cancelar_seguimiento(saga=saga):
            unidad.sagas.actualizar_paso(saga, SagaStepName.CANCELAR_SEGUIMIENTO_SI_APLICA)
        else:
            unidad.sagas.actualizar_paso(saga, SagaStepName.FINALIZAR_COMPENSACION)
