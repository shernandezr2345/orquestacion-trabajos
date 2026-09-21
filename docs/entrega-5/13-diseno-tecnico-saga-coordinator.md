# DISENO TECNICO DEL SAGA COORDINATOR - ENTREGA 5

## A. Arquitectura propuesta del SagaCoordinator

### Objetivo

Definir el componente de orquestacion en runtime que hoy falta, sin inventar contratos ni comportamiento fuera de lo documentado en Entrega 5.

### Responsabilidades exactas

1. Recibir un evento ya decodificado por el consumidor.
2. Construir un envelope interno con:
- tipo_mensaje
- message_id (event_id o command_id)
- id_saga (si existe)
- id_solicitud (si existe)
- id_trabajo (si existe)
- correlacion (si existe)
- causacion (si existe)
- payload
3. Resolver la instancia de Saga.
4. Aplicar validaciones en este orden:
- DUPLICATE
- LATE
- OUT_OF_ORDER
- CONFLICT
5. Ejecutar transicion valida de Saga (estado/paso).
6. Registrar SagaLog para cada decision.
7. Disparar siguiente accion solo si esta soportada por contratos actuales.
8. Confirmar todo en una unica unidad transaccional.

### Flujo interno obligatorio

EVENT_RECEIVED
-> resolucion de Saga
-> idempotencia
-> validacion de estado
-> validacion de paso
-> clasificacion (DUPLICATE/LATE/OUT_OF_ORDER/CONFLICT)
-> transicion de Saga
-> SagaLog
-> emision del siguiente comando/evento
-> UnitOfWork

### Clasificacion de soporte

- DEFINIDO:
  - Estados RUNNING, COMPENSATING, COMPLETED, COMPENSATED.
  - SagaLog (tipos y resultados).
  - Repositorio Saga con busqueda por id_saga e id_solicitud.
  - Idempotencia por indice unico.
- INFERIDO:
  - Envelope interno como objeto de aplicacion.
  - Orden exacto de validaciones previas a transicion.
- PENDIENTE:
  - Decision formal de ruta para CotizacionRechazada.
- NO SOPORTADO:
  - Ramas que requieren contratos aun no implementados.

## B. Diagrama textual del flujo

```text
Consumidor Pulsar
  -> decode Avro
  -> envelope
  -> SagaCoordinator.process(envelope)

SagaCoordinator.process
  -> abrir UnitOfWork
  -> EVENT_RECEIVED (intento de procesamiento)
  -> resolver saga (id_saga o id_solicitud)
  -> validar idempotencia (id_saga + tipo_mensaje + message_id)
     -> si DUPLICATE: log DUPLICATE/NO_OP_DUPLICATE, commit, fin
  -> validar estado terminal
     -> si LATE: log LATE/NO_OP_LATE, commit, fin
  -> validar paso habilitado
     -> si OUT_OF_ORDER: log OUT_OF_ORDER/NO_OP_OUT_OF_ORDER, commit, fin
  -> validar consistencia de identificadores y contenido
     -> si CONFLICT: log EVENT_RECEIVED/REJECTED_CONFLICT, commit, fin
  -> aplicar accion de negocio (reusando handlers existentes)
  -> actualizar estado/paso de saga
  -> registrar SagaLog de transicion y de emision
  -> confirmar UnitOfWork
```

## C. Tabla evento -> estado -> accion -> siguiente mensaje

### Reglas de resolucion de Saga

1. Si el mensaje trae id_saga:
- Resolver por id_saga.
2. Si no trae id_saga y trae id_solicitud:
- Resolver por id_solicitud.
3. Si faltan ambos:
- CONFLICT.
4. Si trae ambos y no son consistentes:
- CONFLICT.

### Tabla de comportamiento (eventos actualmente implementados)

| Evento | Saga buscada por | Estado esperado | Paso esperado | Accion | Estado resultante | Siguiente mensaje | SagaLog exito | Duplicado | Tardio | Fuera de orden | Conflicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | id_solicitud | no existe saga previa o saga en inicio controlado | inicio | crear saga + reutilizar crear_trabajo + asignar id_trabajo + mover paso a SOLICITAR_COTIZACION | RUNNING | SolicitarCotizacion.v1 | EVENT_RECEIVED/APPLIED + LOCAL_OPERATION/APPLIED + COMMAND_EMITTED/APPLIED | DUPLICATE/NO_OP_DUPLICATE | LATE/NO_OP_LATE si saga terminal | OUT_OF_ORDER/NO_OP_OUT_OF_ORDER si paso incompatible | EVENT_RECEIVED/REJECTED_CONFLICT |
| TrabajoCreado.v1 | id_solicitud | RUNNING | SOLICITAR_COTIZACION | confirmar avance interno sin duplicar dominio | RUNNING | ninguno obligatorio | EVENT_RECEIVED/APPLIED | DUPLICATE/NO_OP_DUPLICATE | LATE/NO_OP_LATE | OUT_OF_ORDER/NO_OP_OUT_OF_ORDER | EVENT_RECEIVED/REJECTED_CONFLICT |
| CotizacionRegistrada.v1 | id_solicitud | RUNNING | SOLICITAR_COTIZACION | reutilizar aplicar_cotizacion + mover paso a ABRIR_SEGUIMIENTO | RUNNING | AbrirSeguimientoTrabajo.v1 | EVENT_RECEIVED/APPLIED + LOCAL_OPERATION/APPLIED + COMMAND_EMITTED/APPLIED | DUPLICATE/NO_OP_DUPLICATE | LATE/NO_OP_LATE | OUT_OF_ORDER/NO_OP_OUT_OF_ORDER | EVENT_RECEIVED/REJECTED_CONFLICT |
| CotizacionRechazada.v1 | id_solicitud | RUNNING | SOLICITAR_COTIZACION | reutilizar aplicar_cotizacion + registrar ruta pendiente sin cerrar por intuicion | DECISION PENDIENTE | DECISION PENDIENTE | EVENT_RECEIVED/APPLIED (hasta donde aplique) | DUPLICATE/NO_OP_DUPLICATE | LATE/NO_OP_LATE | OUT_OF_ORDER/NO_OP_OUT_OF_ORDER | EVENT_RECEIVED/REJECTED_CONFLICT |
| AtencionHabilitadaRegistrada.v1 | id_saga preferente; fallback id_solicitud | RUNNING | COMPLETAR_SAGA o REGISTRAR_ATENCION_HABILITADA (segun cableado final) | cerrar saga por exito | COMPLETED | ninguno | EVENT_RECEIVED/APPLIED + STATE_CHANGED/APPLIED | DUPLICATE/NO_OP_DUPLICATE | LATE/NO_OP_LATE | OUT_OF_ORDER/NO_OP_OUT_OF_ORDER | EVENT_RECEIVED/REJECTED_CONFLICT |
| AtencionCanceladaRegistrada.v1 | id_saga preferente; fallback id_solicitud | COMPENSATING | FINALIZAR_COMPENSACION o REGISTRAR_ATENCION_CANCELADA (segun cableado final) | cerrar compensacion | COMPENSATED | ninguno | EVENT_RECEIVED/APPLIED + STATE_CHANGED/APPLIED | DUPLICATE/NO_OP_DUPLICATE | LATE/NO_OP_LATE | OUT_OF_ORDER/NO_OP_OUT_OF_ORDER | EVENT_RECEIVED/REJECTED_CONFLICT |

### Maquina de estados explicita (sin estados nuevos)

- RUNNING -> RUNNING (avances intermedios)
- RUNNING -> COMPLETED (cierre exitoso)
- RUNNING -> COMPENSATING (solo cuando la rama este formalmente definida)
- COMPENSATING -> COMPENSATED (cierre de compensacion)
- COMPLETED y COMPENSATED son terminales

## D. Tabla de responsabilidades por componente

| Componente | Responsabilidad |
|---|---|
| Consumer | Decodifica mensaje, arma envelope y delega en SagaCoordinator |
| SagaCoordinator | Resolve saga, valida reglas, decide transiciones, registra SagaLog, dispara siguiente accion |
| Handlers de aplicacion (crear_trabajo/aplicar_cotizacion) | Ejecutan logica de dominio de Trabajo sin logica de coordinacion |
| Repositorio Saga | Recupera y persiste SagaInstance/SagaLog, soporta idempotencia por consulta |
| UnitOfWork | Atomicidad de saga, logs y efectos de salida |
| Publisher/Outbox | Entrega asincrona de mensajes emitidos |

## E. Cambios minimos necesarios en archivos existentes

1. config/bootstrap.py
- Incorporar wiring del SagaCoordinator en el pipeline de consumidores.

2. modulos/trabajos/infraestructura/consumidores.py
- Delegar en SagaCoordinator en lugar de invocar handlers de trabajos de forma aislada.

3. Integracion transaccional
- Ajuste minimo para que la coordinacion de saga y la ejecucion de handlers compartan unidad transaccional coherente.

4. config/rutas.py
- Solo ajustar rutas para eventos/acciones que ya tengan contrato implementado y validado para esta fase.

Clasificacion:
- DEFINIDO: necesidad de cablear coordinator + validaciones + logs.
- INFERIDO: estrategia exacta de composicion UoW compartida.
- PENDIENTE: detalle operativo de algunos eventos de atencion por ambiente.
- NO SOPORTADO: contratos aun inexistentes de seguimiento/compensacion.

## F. Tests que deberan crearse

1. Happy Path (nucleo soportado)
- SolicitudDePartnerListaParaAtencion.v1 crea saga y dispara SolicitarCotizacion.v1.
- CotizacionRegistrada.v1 avanza paso esperado.

2. Idempotencia
- Repeticion de eventos criticos no reaplica transicion.
- No reemite comando.
- Registra DUPLICATE + NO_OP_DUPLICATE.

3. LATE
- Evento recibido con saga en COMPLETED o COMPENSATED.
- Registra NO_OP_LATE.

4. OUT_OF_ORDER
- Evento de paso futuro no habilitado.
- Registra NO_OP_OUT_OF_ORDER.

5. CONFLICT
- IDs inconsistentes o contenido incompatible.
- Registra REJECTED_CONFLICT.

6. Atomicidad/rollback
- Si falla una accion, no quedan Saga ni SagaLog en estado parcial.

7. Alcance de no soporte
- Eventos que dependen de contratos inexistentes deben quedar marcados como no soportados en esta fase.

## G. Decisiones pendientes

1. CotizacionRechazada:
- RUNNING -> COMPENSATING
- o RUNNING -> COMPENSATED
Estado: DECISION PENDIENTE.

2. Contratos pendientes de implementar:
- AbrirSeguimientoTrabajo.v1
- SeguimientoTrabajoAbierto.v1
- AperturaSeguimientoFallida.v1
- CancelarSeguimientoTrabajo.v1
- SeguimientoTrabajoCancelado.v1
- AnularCotizacion.v1
- CotizacionAnulada.v1
- TrabajoCancelado.v1
Estado: PENDIENTE DE CONTRATO.

3. Cableado final de eventos de atencion en orquestacion por ambiente:
Estado: PENDIENTE.

## H. Riesgos tecnicos

1. Doble transaccion coordinator/handlers si no se unifica UoW.
2. Inconsistencia de auditoria si SagaLog no queda en la misma transaccion que la transicion.
3. Reintentos con efectos duplicados si no se prioriza la validacion de idempotencia.
4. Bloqueo funcional parcial hasta definir ruta de CotizacionRechazada.
5. Acoplamiento prematuro si se intenta implementar ramas con contratos aun inexistentes.

## Alcance explicito de compensaciones en esta fase

NO SOPORTADO EN IMPLEMENTACION ACTUAL DEL COORDINATOR (solo identificado):
- AbrirSeguimientoTrabajo.v1
- SeguimientoTrabajoAbierto.v1
- AperturaSeguimientoFallida.v1
- CancelarSeguimientoTrabajo.v1
- SeguimientoTrabajoCancelado.v1
- AnularCotizacion.v1
- CotizacionAnulada.v1
- TrabajoCancelado.v1
