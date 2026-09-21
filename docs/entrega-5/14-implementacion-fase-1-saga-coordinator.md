# Entrega 5 - Implementacion FASE 1 SagaCoordinator

## 1. Resultado

Se implemento la FASE 1 del SagaCoordinator en el servicio `orquestacion-trabajos` con ejecucion real en runtime:

- Resolucion/creacion de saga por `id_saga` o `id_solicitud`.
- Clasificacion y registro de casos `DUPLICATE`, `LATE`, `OUT_OF_ORDER`, `REJECTED_CONFLICT`.
- Ejecucion atomica en una sola unidad de trabajo para saga + trabajo + inbox + outbox + logs.
- Reuso de handlers existentes (`CrearTrabajoHandler`, `AplicarCotizacionHandler`) sin romper compatibilidad previa.
- Inyeccion del coordinator en el pipeline real de consumidores via bootstrap.

## 2. Archivos modificados y creados

### Creados

- `src/orquestacion_trabajos/modulos/sagas/aplicacion/__init__.py`
- `src/orquestacion_trabajos/modulos/sagas/aplicacion/eventos.py`
- `src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py`
- `tests/unitarias/aplicacion/sagas/test_saga_coordinator.py`

### Modificados

- `src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py`
- `src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/crear_trabajo.py`
- `src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py`
- `src/orquestacion_trabajos/modulos/trabajos/infraestructura/consumidores.py`
- `src/orquestacion_trabajos/config/bootstrap.py`

## 3. Flujo implementado (FASE 1)

### 3.1 SolicitudDePartnerListaParaAtencion.v1

1. Se resuelve/crea saga.
2. Se registra `EVENT_RECEIVED`.
3. Se ejecuta `CrearTrabajoHandler` en la misma UoW.
4. Se asigna `id_trabajo` a la saga.
5. Se avanza paso a `SOLICITAR_COTIZACION`.
6. Se registra `LOCAL_OPERATION`.
7. Si existe comando en outbox `SolicitarCotizacion.v1`, se registra `COMMAND_EMITTED`.

### 3.2 CotizacionRegistrada.v1

1. Validaciones de orden, consistencia e idempotencia.
2. Se aplica resultado de cotizacion sobre Trabajo.
3. Saga avanza a paso `ABRIR_SEGUIMIENTO`.
4. Se registra `IGNORED` para indicar que `AbrirSeguimientoTrabajo.v1` queda pendiente por contrato no implementado.
5. Se registra `LOCAL_OPERATION`.

### 3.3 CotizacionRechazada.v1

1. Validaciones de orden, consistencia e idempotencia.
2. Se aplica resultado de cotizacion sobre Trabajo.
3. Saga avanza a paso `CANCELAR_TRABAJO_POR_RECHAZO`.
4. Se registra `IGNORED` indicando decision pendiente sobre ruta final.
5. Se registra `LOCAL_OPERATION`.

## 4. Matriz evento -> comportamiento

| Evento | Paso esperado | Accion FASE 1 | Resultado |
|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | CREAR_TRABAJO | Crear/reusar trabajo + emitir solicitar cotizacion | APPLIED |
| CotizacionRegistrada.v1 | SOLICITAR_COTIZACION | Aplicar cotizacion + mover a ABRIR_SEGUIMIENTO | APPLIED + pendiente comando siguiente |
| CotizacionRechazada.v1 | SOLICITAR_COTIZACION | Aplicar rechazo + mover a CANCELAR_TRABAJO_POR_RECHAZO | APPLIED + decision final pendiente |
| AtencionHabilitadaRegistrada.v1 | COMPLETAR_SAGA | Marcar saga COMPLETED | APPLIED |
| AtencionCanceladaRegistrada.v1 | FINALIZAR_COMPENSACION | Marcar saga COMPENSATED | APPLIED |
| Cualquier evento duplicado | N/A | No re-aplica efectos | NO_OP_DUPLICATE |
| Evento tardio en saga terminal | N/A | No re-aplica efectos | NO_OP_LATE |
| Evento fuera de orden | N/A | No re-aplica efectos | NO_OP_OUT_OF_ORDER |
| IDs o contenido incompatibles | N/A | Rechazo por conflicto | REJECTED_CONFLICT |

## 5. Pruebas agregadas

Archivo: `tests/unitarias/aplicacion/sagas/test_saga_coordinator.py`

Casos cubiertos:

- `test_happy_path_inicial_crea_saga_trabajo_y_comando`
- `test_idempotencia_no_repite_efectos_ni_emision`
- `test_late_completed_registra_no_op_late`
- `test_late_compensated_registra_no_op_late`
- `test_out_of_order_evento_futuro`
- `test_conflict_ids_inconsistentes`
- `test_conflict_contenido_incompatible`
- `test_rollback_si_falla_operacion_posterior`
- `test_cotizacion_registrada_avanza_solo_en_paso_habilitado`
- `test_cotizacion_rechazada_mantiene_ruta_pendiente_sin_compensaciones`

## 6. Ejecucion de pruebas

Entorno usado para validar:

- Python: `3.12.10`
- Interpreter: `orquestacion-trabajos/.venv/Scripts/python.exe`

Comandos ejecutados:

- `python -m pytest tests/unitarias/aplicacion/sagas/test_saga_coordinator.py -q`
- `python -m pytest -q`

Resultado:

- `10 passed` en pruebas nuevas del coordinator.
- `136 passed, 2 warnings` en suite completa.

## 7. Brechas y decisiones pendientes

1. No se implementan comandos/eventos de pasos no soportados por contrato vigente en FASE 1 (por ejemplo apertura/cancelacion de seguimiento), solo se deja trazabilidad `IGNORED`.
2. Para `CotizacionRechazada.v1` se mantiene decision pendiente de estado terminal final (no se forza compensacion no definida).
3. El tipo de registro `CONFLICT` no existe en el enum actual; se materializa conflicto con `EVENT_RECEIVED + REJECTED_CONFLICT` para mantener compatibilidad con esquema vigente.

## 8. Riesgos residuales

- Si se requiere estrictamente `tipo_registro=CONFLICT`, se necesita cambio de modelo + migracion DB + ajustes en tests.
- Los siguientes pasos de saga (post-cotizacion) quedan en backlog contractual; la orquestacion completa depende de cerrar esos contratos.
- Las pruebas actuales son unitarias; falta evidencia de extremo a extremo con broker real para toda la secuencia multi-servicio.
