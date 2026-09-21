# 08 - Diseno Persistencia Saga

## 1. Objetivo

Definir el diseno de persistencia para SagaInstance y SagaLog en Orquestacion de Trabajos, sin implementar codigo ni crear artefactos tecnicos, manteniendo:

- [CONTRATO DEL EQUIPO] Saga como Process Manager u Orchestrator.
- [CONTRATO DEL EQUIPO] Trabajo como Aggregate Root independiente.
- [CONTRATO DEL EQUIPO] Estados permitidos: RUNNING, COMPENSATING, COMPLETED, COMPENSATED.

## 2. Fuentes utilizadas

Orden de prioridad aplicado:

1. [CONTRATO DEL EQUIPO] docs/entrega-5/contratos-saga-propuesta.md
2. [CONTRATO DEL EQUIPO] docs/entrega-5/07-diseno-saga-steps.md
3. [EXISTENTE] docs/entrega-5/AUDITORIA_ENTREGA5_ORQUESTACION_TRABAJOS.md
4. [ADAPTACION DEL TUTORIAL] docs/entrega-5/06-mapeo-tutorial-saga-vs-hogar-alpes.md
5. [PROPUESTA] docs/entrega-5/hda-entrega5-propuesta-saga-bff.pdf

Nota de trazabilidad:

- [PROPUESTA] El PDF no se pudo leer completamente en este entorno por restricciones del visor local; se usaron contrato y disenos previos como fuente principal de verdad.

## 3. Modelo SagaInstance

Definicion conceptual:

- [PROPUESTA] SagaInstance representa el estado actual y mutable de una saga de atencion por solicitud.
- [PROPUESTA] SagaInstance no es historial; para historial se usa SagaLog.
- [CONTRATO DEL EQUIPO] id_saga es generado por Orquestacion al iniciar la saga.

## 4. Campos e invariantes

### 4.1 Campos base

| Campo | Tipo conceptual | Obligatorio | Proposito | Invariante | Persistir |
|---|---|---|---|---|---|
| id_saga | UUID | Si | Identidad tecnica de la saga | Inmutable; generado por Orquestacion | Si |
| id_solicitud | UUID o string estable de negocio | Si | Correlacion de negocio | Inmutable; una saga por solicitud | Si |
| id_trabajo | UUID o string estable de negocio | No al inicio; Si despues de crear trabajo | Vinculo con dominio Trabajo | Puede iniciar en NULL; debe existir para pasos que operen sobre Trabajo | Si |
| estado | Enum SagaStatus | Si | Estado actual de coordinacion | Solo RUNNING, COMPENSATING, COMPLETED, COMPENSATED | Si |
| paso_actual | String controlado o enum de paso | Si | Paso vigente en maquina de pasos | Debe pertenecer al catalogo de pasos acordado | Si |
| version | Entero | Si | Concurrencia optimista | Incrementa en cada transicion aplicada | Si |
| created_at | Timestamp UTC | Si | Auditoria de creacion | Inmutable | Si |
| updated_at | Timestamp UTC | Si | Auditoria de ultimo cambio | Debe actualizarse por transicion real aplicada | Si |

### 4.2 Campos adicionales justificados

| Campo | Tipo conceptual | Obligatorio | Justificacion | Persistir |
|---|---|---|---|---|
| seguimiento_apertura_solicitada | Booleano | Si, default false | [PROPUESTA] Distingue que se emitio AbrirSeguimientoTrabajo.v1 aunque no exista confirmacion | Si |
| seguimiento_abierto_confirmado | Booleano | Si, default false | [CONTRATO DEL EQUIPO] Compensacion condicional: solo cancelar seguimiento si realmente llego a abrirse | Si |

Reglas de consistencia entre banderas:

- [PROPUESTA] seguimiento_apertura_solicitada=true significa que Orquestacion ya emitio AbrirSeguimientoTrabajo.v1.
- [PROPUESTA] seguimiento_abierto_confirmado=true significa que Orquestacion recibio SeguimientoTrabajoAbierto.v1.
- [PROPUESTA] seguimiento_abierto_confirmado=true implica seguimiento_apertura_solicitada=true.
- [PROPUESTA] seguimiento_apertura_solicitada=true no implica seguimiento_abierto_confirmado=true.

Regla de compensacion sin ambiguedad:

- [CONTRATO DEL EQUIPO] Si seguimiento_apertura_solicitada=true, se debe emitir CancelarSeguimientoTrabajo.v1 al compensar, incluso cuando no exista confirmacion de apertura.
- [CONTRATO DEL EQUIPO] Si seguimiento_apertura_solicitada=false, no corresponde emitir CancelarSeguimientoTrabajo.v1.

Matriz de lectura operativa:

| seguimiento_apertura_solicitada | seguimiento_abierto_confirmado | Interpretacion | Accion de compensacion |
|---|---|---|---|
| false | false | No se solicito apertura | No emitir CancelarSeguimientoTrabajo.v1 |
| true | false | Se solicito apertura, sin confirmacion aun | Emitir CancelarSeguimientoTrabajo.v1 |
| true | true | Apertura confirmada | Emitir CancelarSeguimientoTrabajo.v1 |

Reglas globales:

- [CONTRATO DEL EQUIPO] correlacion sigue siendo id_solicitud; no se reemplaza por id_saga.
- [CONTRATO DEL EQUIPO] un retry de transporte no crea una saga nueva.
- [PROPUESTA] id_solicitud e id_saga son inmutables en SagaInstance.
- [PROPUESTA] una saga puede existir temporalmente con id_trabajo = NULL mientras se ejecuta CREAR_TRABAJO.
- [PROPUESTA] no se ejecutan pasos que requieren Trabajo si id_trabajo es NULL.

### 4.3 Tabla final de SagaInstance

| Campo | Tipo conceptual | NOT NULL | NULLABLE | DEFAULT | Regla funcional |
|---|---|---|---|---|---|
| id_saga | UUID | Si | No | Sin default funcional de negocio | Generado por Orquestacion |
| id_solicitud | UUID/string | Si | No | Sin default | Correlacion de negocio, unico por solicitud |
| id_trabajo | UUID/string | No | Si | NULL | Se completa luego de CREAR_TRABAJO |
| estado | Enum SagaStatus | Si | No | RUNNING | Sin estados nuevos |
| paso_actual | String/enum paso | Si | No | CREAR_TRABAJO | Paso actual de la saga |
| seguimiento_apertura_solicitada | Booleano | Si | No | false | true al emitir AbrirSeguimientoTrabajo.v1 |
| seguimiento_abierto_confirmado | Booleano | Si | No | false | true al recibir SeguimientoTrabajoAbierto.v1 |
| version | Entero | Si | No | 1 | Control de concurrencia optimista |
| created_at | Timestamp UTC | Si | No | now() | Inmutable |
| updated_at | Timestamp UTC | Si | No | now() | Cambia en mutaciones reales |

## 5. Estados

### 5.1 Significado

- [CONTRATO DEL EQUIPO] RUNNING: saga en camino feliz o evaluando eventos de avance.
- [CONTRATO DEL EQUIPO] COMPENSATING: saga ejecutando o esperando compensaciones.
- [CONTRATO DEL EQUIPO] COMPLETED: saga finalizada por camino exitoso.
- [CONTRATO DEL EQUIPO] COMPENSATED: saga finalizada por camino compensado.

### 5.2 Cambios reales de estado permitidos

- [CONTRATO DEL EQUIPO] RUNNING -> COMPENSATING
- [CONTRATO DEL EQUIPO] RUNNING -> COMPLETED
- [CONTRATO DEL EQUIPO] COMPENSATING -> COMPENSATED

Aclaracion de permanencia:

- [CONTRATO DEL EQUIPO] RUNNING puede permanecer en RUNNING durante eventos intermedios exitosos.
- [PROPUESTA] Esta permanencia no se modela como STATE_CHANGED RUNNING -> RUNNING; se registra como recepcion de evento y emision de comando.

### 5.3 Transiciones prohibidas

- [PROPUESTA] COMPLETED -> cualquier otro estado.
- [PROPUESTA] COMPENSATED -> cualquier otro estado.
- [PROPUESTA] RUNNING -> COMPENSATED directo, salvo que el equipo defina explicitamente ese atajo.

Terminalidad:

- [CONTRATO DEL EQUIPO] COMPLETED y COMPENSATED son terminales.

## 6. Paso actual

Decision:

- [PROPUESTA] Persistir paso_actual como string controlado (catalogo estable de pasos), no como entero opaco.

Justificacion:

- [PROPUESTA] Mejora observabilidad y depuracion en demos sin joins adicionales.
- [PROPUESTA] Alinea con diseno de pasos de docs/entrega-5/07-diseno-saga-steps.md.
- [PROPUESTA] Evita acoplarse a un orden numerico fragil.

Regla:

- [PROPUESTA] paso_actual debe estar validado contra catalogo de SagaStepName en dominio.

## 7. Identidad y correlacion

Politica:

- [CONTRATO DEL EQUIPO] id_saga es identidad de la instancia.
- [CONTRATO DEL EQUIPO] id_solicitud es correlacion de negocio.
- [CONTRATO DEL EQUIPO] debe existir una saga por solicitud.

Estrategia para garantizar una saga por solicitud:

- [PROPUESTA] Restriccion unica global sobre id_solicitud en SagaInstance.
- [PROPUESTA] Indice por id_saga para acceso primario.

Razon:

- [PROPUESTA] La regla del contrato no habla de solo activas; habla de una saga por solicitud. Por tanto, unique global es la opcion mas fiel.

## 8. Concurrencia

Problema a resolver:

- [EXISTENTE] Pueden llegar eventos concurrentes o retries para la misma saga.

Estrategia recomendada:

- [PROPUESTA] Combinacion de bloqueo pesimista por fila y version optimista:
  - leer SagaInstance con SELECT FOR UPDATE al procesar un evento para serializar decisiones por saga;
  - actualizar con chequeo de version para detectar escrituras obsoletas.

Por que combinada:

- [PROPUESTA] FOR UPDATE reduce carreras en tiempo real.
- [PROPUESTA] version protege de actualizaciones perdidas cuando hay reintentos o caminos alternos.

## 9. Modelo SagaLog

Definicion conceptual:

- [PROPUESTA] SagaLog es historial de coordinacion de la saga, no estado actual.
- [PROPUESTA] SagaLog conserva trazabilidad de decisiones, no reemplaza Inbox.

### 9.1 Campos propuestos

| Campo | Tipo conceptual | Obligatorio | Proposito |
|---|---|---|---|
| log_id | UUID o bigserial | Si | Identidad tecnica del registro de log |
| id_saga | UUID | Si | Vinculo a SagaInstance |
| id_solicitud | UUID o string | Si | Correlacion de negocio para consulta directa |
| id_trabajo | UUID o string | No | Referencia del trabajo cuando ya existe |
| paso | String controlado | Si | Paso al que corresponde el registro |
| tipo_registro | Enum | Si | EVENT_RECEIVED, COMMAND_EMITTED, EVENT_EMITTED, LOCAL_OPERATION, STATE_CHANGED, DUPLICATE, LATE, OUT_OF_ORDER, IGNORED |
| tipo_mensaje | String | No | Nombre de contrato, si aplica |
| event_id | UUID/string | No | Identidad del evento recibido o emitido |
| command_id | UUID/string | No | Identidad del comando emitido |
| causacion | UUID/string | No | ID del mensaje que origina el mensaje actual |
| estado_anterior | SagaStatus | No | Estado previo a cambio real de estado |
| estado_nuevo | SagaStatus | No | Estado resultante de cambio real de estado |
| resultado | String controlado | Si | APPLIED, NO_OP_DUPLICATE, NO_OP_LATE, NO_OP_OUT_OF_ORDER, REJECTED_CONFLICT |
| detalle | Texto corto | No | Motivo operativo o diagnostico |
| created_at | Timestamp UTC | Si | Instante del registro |

### 9.2 Tabla final de SagaLog

| Campo | Tipo conceptual | NOT NULL | NULLABLE | DEFAULT | Regla funcional |
|---|---|---|---|---|---|
| log_id | UUID o bigserial | Si | No | autogenerado | PK del registro |
| id_saga | UUID | Si | No | Sin default | FK a SagaInstance |
| id_solicitud | UUID/string | Si | No | Sin default | Correlacion de negocio |
| id_trabajo | UUID/string | No | Si | NULL | Puede ser NULL al inicio de saga |
| paso | String/enum paso | Si | No | Sin default | Paso donde ocurre el hecho |
| tipo_registro | Enum de log | Si | No | Sin default | Clasificacion del registro |
| tipo_mensaje | String | No | Si | NULL | Contrato de comando/evento si aplica |
| event_id | UUID/string | No | Si | NULL | Identidad de evento |
| command_id | UUID/string | No | Si | NULL | Identidad de comando |
| causacion | UUID/string | No | Si | NULL | Evento/comando que causo el mensaje actual |
| estado_anterior | SagaStatus | No | Si | NULL | Solo en cambios reales de estado |
| estado_nuevo | SagaStatus | No | Si | NULL | Solo en cambios reales de estado |
| resultado | String controlado | Si | No | Sin default | Resultado del procesamiento |
| detalle | Texto corto | No | Si | NULL | Contexto de negocio/tecnico |
| created_at | Timestamp UTC | Si | No | now() | Registro append-only |

Diferencia con Inbox y Outbox:

- [EXISTENTE] Inbox: deduplicacion de mensajes recibidos.
- [EXISTENTE] Outbox: garantiza publicacion despues del commit.
- [PROPUESTA] SagaLog: trazabilidad de decisiones, transiciones, comandos, eventos y operaciones locales de la saga.

## 10. Append-only

Decision:

- [PROPUESTA] SagaLog debe ser append-only.

Justificacion:

- [PROPUESTA] Preserva trazabilidad completa de decisiones.
- [PROPUESTA] Facilita auditoria de fallos y eventos tardios.
- [PROPUESTA] Evita reescrituras que oculten historia.

Regla:

- [PROPUESTA] Una vez insertado un registro de SagaLog no se actualiza ni borra en operaciones normales.

## 11. Idempotencia

Politica para SagaLog y transiciones:

- [CONTRATO DEL EQUIPO] mismo ID y contenido igual: un solo efecto.
- [CONTRATO DEL EQUIPO] mismo ID y contenido distinto: conflicto.

Clave recomendada:

- [PROPUESTA] llave idempotente de coordinacion: id_saga + tipo_mensaje + message_id.

Donde:

- [PROPUESTA] message_id toma event_id o command_id segun corresponda.

Comportamiento:

- [PROPUESTA] si la llave existe con mismo contenido logico: registrar entrada de tipo DUPLICATE o NO_OP_DUPLICATE.
- [PROPUESTA] si existe con contenido incompatible: registrar REJECTED_CONFLICT y no alterar SagaInstance.

## 12. Eventos tardios y fuera de orden

Politica de registro:

- [PROPUESTA] Evento tardio: registrar en SagaLog como LATE, estado sin cambio salvo que confirme compensacion pendiente.
- [PROPUESTA] Evento fuera de orden: registrar como OUT_OF_ORDER, sin cambio de paso ni estado.
- [PROPUESTA] Evento duplicado: registrar como DUPLICATE o NO_OP_DUPLICATE.
- [PROPUESTA] Evento post COMPLETED: registrar como IGNORED_POST_COMPLETED.
- [PROPUESTA] Evento post COMPENSATED: registrar como IGNORED_POST_COMPENSATED.

Sin nuevos estados:

- [CONTRATO DEL EQUIPO] estos casos son observabilidad y politica del coordinador, no nuevos estados de saga.

## 13. Relacion entre tablas

Relacion conceptual:

- [PROPUESTA] saga_instance 1:N saga_log.

Integridad:

- [PROPUESTA] saga_log.id_saga referencia saga_instance.id_saga.
- [PROPUESTA] integridad referencial obligatoria por foreign key.
- [PROPUESTA] no se elimina saga_instance con historial activo en uso normal.

## 14. Indices

Indices recomendados:

- [PROPUESTA] PK o unique en id_saga de saga_instance.
- [PROPUESTA] unique en id_solicitud de saga_instance.
- [PROPUESTA] indice por estado en saga_instance para monitoreo operativo.
- [PROPUESTA] indice en saga_log por id_saga y created_at para historial cronologico.
- [PROPUESTA] indice en saga_log por id_solicitud y created_at para trazas de negocio.
- [PROPUESTA] unique funcional para idempotencia de mensaje en saga_log, segun llave definida.

## 15. Separacion Inbox vs SagaLog

Definiciones:

- [EXISTENTE] INBOX: deduplicacion de mensajes recibidos.
- [EXISTENTE] OUTBOX: garantia de publicacion de mensajes despues del commit.
- [PROPUESTA] SAGA LOG: trazabilidad de decisiones de la saga (eventos, comandos, operaciones locales, transiciones y no-op).

Regla:

- [CONTRATO DEL EQUIPO] SagaLog no reemplaza Inbox.

Flujo conceptual:

Mensaje recibido  
-> Inbox  
-> duplicado?  
-> si: ignorar funcionalmente y opcionalmente registrar traza en SagaLog  
-> no: SagaCoordinator  
-> SagaInstance  
-> SagaLog  
-> Outbox  
-> commit

## 16. Unit of Work y Outbox

Integracion requerida:

- [EXISTENTE] Reusar UoW transaccional ya presente en el servicio.
- [PROPUESTA] En una misma transaccion deben ocurrir, cuando aplique:
  - lectura y cambio de SagaInstance,
  - insercion append-only en SagaLog,
  - cambio de dominio asociado (por ejemplo Trabajo),
  - registro en Outbox de comandos o eventos resultantes.

Garantia requerida:

- [PROPUESTA] Atomicidad transaccional: o se confirman todas las operaciones, o ninguna.
- [EXISTENTE] Esto sigue el patron ya usado por Trabajo con inbox/outbox y UoW.

## 17. Repositorios

Solo diseno de interfaces minimas.

### 17.1 SagaRepository

- [PROPUESTA] crear
- [PROPUESTA] obtener_por_id_saga
- [PROPUESTA] obtener_por_id_solicitud
- [PROPUESTA] actualizar_estado
- [PROPUESTA] actualizar_paso
- [PROPUESTA] marcar_seguimiento_apertura_solicitada
- [PROPUESTA] marcar_seguimiento_abierto_confirmado
- [PROPUESTA] asignar_id_trabajo
- [PROPUESTA] incrementar_version

### 17.2 SagaLogRepository

- [PROPUESTA] registrar
- [PROPUESTA] listar_por_saga
- [PROPUESTA] buscar_por_message_id
- [PROPUESTA] obtener_ultimos_por_saga

## 18. Mapeo DDD

### Dominio

- [CONTRATO DEL EQUIPO] SagaStatus
- [CONTRATO DEL EQUIPO] SagaStep como Value Object inmutable
- [PROPUESTA] SagaInstance como entidad de proceso
- [PROPUESTA] invariantes de transicion

### Aplicacion

- [CONTRATO DEL EQUIPO] SagaCoordinator
- [PROPUESTA] politicas de aceptacion de eventos duplicados, tardios y fuera de orden
- [PROPUESTA] coordinacion de compensaciones
- [PROPUESTA] operacion local Trabajo.cancelar() sin dependencia de Pulsar en dominio

### Infraestructura

- [PROPUESTA] modelos de persistencia SQL
- [PROPUESTA] mapeadores entre dominio y persistencia
- [PROPUESTA] implementaciones concretas de SagaRepository y SagaLogRepository
- [EXISTENTE] UoW, Inbox y Outbox reusados
- [EXISTENTE] PostgreSQL y SQLAlchemy como base de persistencia

## 19. Diagrama conceptual

```mermaid
erDiagram
    SAGA_INSTANCE ||--o{ SAGA_LOG : "1 a N"

    SAGA_INSTANCE {
        uuid id_saga PK
        string id_solicitud UK
        string id_trabajo NULLABLE
        string estado
        string paso_actual
        boolean seguimiento_apertura_solicitada
        boolean seguimiento_abierto_confirmado
        int version
        datetime created_at
        datetime updated_at
    }

    SAGA_LOG {
        uuid log_id PK
        uuid id_saga FK
        string id_solicitud
        string id_trabajo NULLABLE
        string paso
        string tipo_registro
        string tipo_mensaje
        string event_id
        string command_id
        string causacion
        string estado_anterior
        string estado_nuevo
        string resultado
        string detalle
        datetime created_at
    }
```

## 20. Ejemplos de registros

### 20.1 Ejemplo SagaInstance inicial (sin trabajo creado)

- [PROPUESTA] id_saga: SAGA-001
- [PROPUESTA] id_solicitud: SOL-001
- [PROPUESTA] id_trabajo: NULL
- [PROPUESTA] estado: RUNNING
- [PROPUESTA] paso_actual: CREAR_TRABAJO
- [PROPUESTA] seguimiento_apertura_solicitada: false
- [PROPUESTA] seguimiento_abierto_confirmado: false
- [PROPUESTA] version: 1

### 20.2 Ejemplo SagaInstance despues de crear Trabajo

- [PROPUESTA] id_saga: SAGA-001
- [PROPUESTA] id_solicitud: SOL-001
- [PROPUESTA] id_trabajo: TRAB-001
- [PROPUESTA] estado: RUNNING
- [PROPUESTA] paso_actual: SOLICITAR_COTIZACION
- [PROPUESTA] seguimiento_apertura_solicitada: false
- [PROPUESTA] seguimiento_abierto_confirmado: false
- [PROPUESTA] version: 2

### 20.3 Ejemplo SagaLog camino exitoso

1. [PROPUESTA] EVENT_RECEIVED SolicitudDePartnerListaParaAtencion.v1 event_id=EVT-001 causacion=NULL resultado=APPLIED
2. [PROPUESTA] LOCAL_OPERATION Trabajo.crear() detalle="creacion local de trabajo" resultado=APPLIED
3. [PROPUESTA] EVENT_EMITTED TrabajoCreado.v1 event_id=EVT-TRAB-001 causacion=EVT-001
4. [PROPUESTA] COMMAND_EMITTED SolicitarCotizacion.v1 command_id=CMD-002 causacion=EVT-TRAB-001
5. [PROPUESTA] EVENT_RECEIVED CotizacionRegistrada.v1 event_id=EVT-002 causacion=CMD-002 resultado=APPLIED
6. [PROPUESTA] COMMAND_EMITTED AbrirSeguimientoTrabajo.v1 command_id=CMD-003 causacion=EVT-002
7. [PROPUESTA] Marca en SagaInstance: seguimiento_apertura_solicitada=true
8. [PROPUESTA] EVENT_RECEIVED SeguimientoTrabajoAbierto.v1 event_id=EVT-003 causacion=CMD-003 resultado=APPLIED
9. [PROPUESTA] Marca en SagaInstance: seguimiento_abierto_confirmado=true
10. [PROPUESTA] COMMAND_EMITTED RegistrarAtencionHabilitada.v1 command_id=CMD-004 causacion=EVT-003
11. [PROPUESTA] EVENT_RECEIVED AtencionHabilitadaRegistrada.v1 event_id=EVT-004 causacion=CMD-004 resultado=APPLIED
12. [PROPUESTA] STATE_CHANGED RUNNING -> COMPLETED

Nota:

- [PROPUESTA] Cuando una saga continua en RUNNING durante pasos intermedios, no se registra STATE_CHANGED RUNNING -> RUNNING.

### 20.4 Ejemplo SagaLog compensado (TrabajoCancelado correcto)

1. [PROPUESTA] EVENT_RECEIVED AperturaSeguimientoFallida.v1 event_id=EVT-010 causacion=CMD-003
2. [PROPUESTA] STATE_CHANGED RUNNING -> COMPENSATING
3. [PROPUESTA] COMMAND_EMITTED AnularCotizacion.v1 command_id=CMD-011 causacion=EVT-010
4. [PROPUESTA] EVENT_RECEIVED CotizacionAnulada.v1 event_id=EVT-011 causacion=CMD-011
5. [PROPUESTA] LOCAL_OPERATION Trabajo.cancelar() detalle="cancelacion local en orquestacion" resultado=APPLIED
6. [PROPUESTA] EVENT_EMITTED TrabajoCancelado.v1 event_id=EVT-012 causacion=EVT-011
7. [PROPUESTA] COMMAND_EMITTED RegistrarAtencionCancelada.v1 command_id=CMD-012 causacion=EVT-012
8. [PROPUESTA] EVENT_RECEIVED AtencionCanceladaRegistrada.v1 event_id=EVT-013 causacion=CMD-012
9. [PROPUESTA] Si seguimiento_apertura_solicitada=true, COMMAND_EMITTED CancelarSeguimientoTrabajo.v1
10. [PROPUESTA] EVENT_RECEIVED SeguimientoTrabajoCancelado.v1 si aplica
11. [PROPUESTA] STATE_CHANGED COMPENSATING -> COMPENSATED

### 20.5 Ejemplo de duplicado

1. [PROPUESTA] EVENT_RECEIVED CotizacionRegistrada.v1 event_id=EVT-002 resultado=APPLIED
2. [PROPUESTA] EVENT_RECEIVED CotizacionRegistrada.v1 event_id=EVT-002 resultado=NO_OP_DUPLICATE tipo_registro=DUPLICATE

### 20.6 Ejemplo de tardio

1. [PROPUESTA] Saga ya en COMPENSATED
2. [PROPUESTA] EVENT_RECEIVED SeguimientoTrabajoAbierto.v1 event_id=EVT-099 resultado=NO_OP_LATE tipo_registro=LATE

### 20.7 Ejemplo fuera de orden

1. [PROPUESTA] Saga en paso SOLICITAR_COTIZACION
2. [PROPUESTA] EVENT_RECEIVED SeguimientoTrabajoAbierto.v1 event_id=EVT-150 resultado=NO_OP_OUT_OF_ORDER tipo_registro=OUT_OF_ORDER

## 21. Decisiones tomadas

1. [CONTRATO DEL EQUIPO] Separar estado actual SagaInstance de historial SagaLog.
2. [CONTRATO DEL EQUIPO] Mantener estados RUNNING, COMPENSATING, COMPLETED, COMPENSATED sin agregar otros.
3. [CONTRATO DEL EQUIPO] Correlacion de negocio por id_solicitud, id_saga como identidad tecnica.
4. [PROPUESTA] Usar unique global por id_solicitud para garantizar una saga por solicitud.
5. [PROPUESTA] SagaLog append-only para trazabilidad.
6. [PROPUESTA] Concurrencia combinada: FOR UPDATE + version.
7. [PROPUESTA] paso_actual como string controlado por catalogo de pasos.
8. [PROPUESTA] id_trabajo nullable al inicio y obligatorio para pasos que operan sobre Trabajo.

## 22. Decisiones pendientes

1. [PROPUESTA] Confirmar si ruta CotizacionRechazada debe pasar formalmente por COMPENSATING o puede cerrar directamente en COMPENSATED tras completar sus acciones.
2. [PROPUESTA] Confirmar lista final de valores de paso_actual para congelar catalogo.
3. [PROPUESTA] Definir formato exacto de message_id unificado cuando existan mensajes sin event_id o command_id explicito.
4. [PROPUESTA] Validar manualmente el PDF para descartar contradicciones no visibles en este entorno.

## 23. Proximo paso de implementacion

- [PROPUESTA] Pasar a diseno tecnico de esquema fisico y contratos de repositorio concretos (sin codificar todavia), alineando llaves unicas, indices y reglas de transaccion con UoW existente.

## 24. Correcciones aplicadas

1. id_trabajo nullable durante inicio.
2. seguimiento_apertura_solicitada.
3. causacion en SagaLog.
4. TrabajoCancelado como operacion local / EVENT_EMITTED.
5. separacion Inbox vs SagaLog.
6. RUNNING -> RUNNING como permanencia y no transicion.

## 25. Estado del diseno

DISENO LISTO PARA REVISION TECNICA ANTES DE IMPLEMENTACION

---

## Conflictos o inconsistencias detectados

1. [CONTRATO DEL EQUIPO] No hay contradiccion funcional en contratos de nombres de comandos y eventos.
2. [PROPUESTA] Existe riesgo de ambiguedad en la ruta CotizacionRechazada respecto al paso intermedio de estado, por redaccion en diseno previo.
3. [PROPUESTA] El PDF no fue legible completamente en este entorno; requiere validacion visual manual.
