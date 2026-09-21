# ANALISIS SOLICITUDES-PARTNER PARA ORQUESTACION

## 1. Resumen del servicio

Responsabilidad real encontrada:
- Servicio de entrada B2B2C para registro de solicitudes de partner, evaluacion de admisibilidad y habilitacion/cancelacion de atencion.
- Expone API HTTP para registro/consulta y mensajeria Pulsar para integracion.
- Evidencia: solicitud-partner/README.md, solicitud-partner/src/solicitudes_partner/api/solicitudes.py:74, solicitud-partner/src/solicitudes_partner/config/bootstrap.py:225.

Bounded context real:
- Solicitudes de Partner (modulo principal).
- Reglas de Partner (modulo interno para evaluacion).
- Evidencia: solicitud-partner/README.md, solicitud-partner/src/solicitudes_partner/modulos/solicitudes, solicitud-partner/src/solicitudes_partner/modulos/reglas_partner.

Aggregates relevantes:
- IMPLEMENTADO: SolicitudPartner (aggregate raiz).
  - Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/dominio/entidades.py.
- IMPLEMENTADO: AttentionResult (resultado de atencion por solicitud).
  - Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/dominio/entidades.py.

Commands relevantes:
- IMPLEMENTADO: RegistrarSolicitudPartner.v1.
- IMPLEMENTADO: RegistrarAtencionHabilitada.v1.
- IMPLEMENTADO: RegistrarAtencionCancelada.v1.
- Evidencia: solicitud-partner/src/solicitudes_partner/config/bootstrap.py:225, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/comandos.py.

Queries relevantes:
- IMPLEMENTADO HTTP:
  - GET /solicitudes/{id_solicitud}
  - GET /solicitudes
  - GET /solicitudes/{id_solicitud}/atencion
  - GET /operaciones/{id_operacion}
- Evidencia: solicitud-partner/docs/contratos/openapi.json:132, solicitud-partner/docs/contratos/openapi.json:8, solicitud-partner/docs/contratos/openapi.json:190, solicitud-partner/docs/contratos/openapi.json:244.

Eventos relevantes:
- IMPLEMENTADO (integracion externa): SolicitudDePartnerListaParaAtencion.v1.
- IMPLEMENTADO (respuestas de atencion): AtencionHabilitadaRegistrada.v1, AtencionCanceladaRegistrada.v1.
- IMPLEMENTADO (CQRS lectura): SolicitudDePartnerActualizada.v1.
- Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py:50, solicitud-partner/src/solicitudes_partner/config/bootstrap.py:290.

Participacion en la Saga de Hogar de los Alpes:
- Como productor del evento de entrada para iniciar/continuar flujo en Orquestacion: SolicitudDePartnerListaParaAtencion.v1.
- Como consumidor de comandos del orquestador para marcar atencion habilitada/cancelada.
- Como productor de eventos de confirmacion de esos comandos.
- Evidencia: solicitud-partner/src/solicitudes_partner/config/rutas.py:15, solicitud-partner/src/solicitudes_partner/config/bootstrap.py:240, solicitud-partner/src/solicitudes_partner/config/bootstrap.py:246, solicitud-partner/src/solicitudes_partner/config/bootstrap.py:300, solicitud-partner/src/solicitudes_partner/config/bootstrap.py:305.

Contexto de commits solicitados:
- 040e12a: introduce/ajusta comandos de atencion, respuestas, API operativa y migraciones 0004/0005.
- 57975d2: solo cambia uv.lock (sin cambios funcionales visibles en codigo).
- 0f4d04f: refuerza integracion Pulsar y contrato solicitud-lista.
- Evidencia: git log y git show ejecutados sobre solicitud-partner.

## 2. Contratos Avro encontrados

Estado general:
- DOCUMENTADO: contratos en solicitud-partner/docs/contratos.
- IMPLEMENTADO: clases Avro en solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1.
- CONFIGURADO: topicos en Settings.

### Contrato: registrar-solicitud-partner-v1.avsc

- Nombre: RegistrarSolicitudPartnerV1
- Tipo: Command
- Version: 1 (campo version_contrato)
- Namespace: bff.comandos
- Nombre Avro: RegistrarSolicitudPartnerV1
- Evidencia: solicitud-partner/docs/contratos/registrar-solicitud-partner-v1.avsc, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/comandos.py.

Campos:
- command_id, string, obligatorio, identidad del comando (deduplicacion de command inbox).
- tipo, string, obligatorio, debe corresponder a RegistrarSolicitudPartner.v1 al parsear.
- version_contrato, int, obligatorio, validado en parse_command = 1.
- instante, string, obligatorio, timestamp del comando.
- id_partner, string, obligatorio, partner emisor.
- referencia_externa, string, obligatorio, clave de negocio de solicitud.
- categoria, string, obligatorio, categoria de la solicitud.
- tipo_solicitud, string, obligatorio, SINIESTRO o INSTALACION.
- aprobacion_previa, null|boolean, opcional, requerida para SINIESTRO en validacion de dominio.

Identificadores:
- event_id: NO PRESENTE
- command_id: PRESENTE
- id_solicitud: NO PRESENTE
- id_trabajo: NO PRESENTE
- id_saga: NO PRESENTE
- correlacion: NO PRESENTE
- event_time: NO PRESENTE
- command_time: NO PRESENTE
- causacion: NO PRESENTE
- version: PRESENTE como version_contrato
- otro: id_partner PRESENTE

### Contrato: registrar-atencion-habilitada-v1.avsc

- Nombre: RegistrarAtencionHabilitadaV1
- Tipo: Command
- Version: 1
- Namespace: orquestacion.eventos
- Nombre Avro: RegistrarAtencionHabilitadaV1
- Evidencia: solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/comandos.py.

Campos:
- command_id, string, obligatorio, ID de comando (inbox).
- tipo, string, obligatorio, esperado RegistrarAtencionHabilitada.v1.
- version_contrato, int, obligatorio, esperado 1.
- instante, string, obligatorio, timestamp del comando.
- id_partner, string, obligatorio.
- correlacion, string, obligatorio, validado para que sea igual a id_solicitud.
- causacion, string, obligatorio, causa del comando.
- id_saga, string, obligatorio.
- id_solicitud, string, obligatorio.
- id_trabajo, string, obligatorio.

Identificadores:
- event_id: NO PRESENTE
- command_id: PRESENTE
- id_solicitud: PRESENTE
- id_trabajo: PRESENTE
- id_saga: PRESENTE
- correlacion: PRESENTE
- event_time: NO PRESENTE
- command_time: NO PRESENTE
- causacion: PRESENTE
- version: PRESENTE como version_contrato
- otro: id_partner PRESENTE

### Contrato: registrar-atencion-cancelada-v1.avsc

- Nombre: RegistrarAtencionCanceladaV1
- Tipo: Command
- Version: 1
- Namespace: orquestacion.eventos
- Nombre Avro: RegistrarAtencionCanceladaV1
- Evidencia: solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/comandos.py.

Campos:
- command_id, string, obligatorio.
- tipo, string, obligatorio, esperado RegistrarAtencionCancelada.v1.
- version_contrato, int, obligatorio.
- instante, string, obligatorio.
- id_partner, string, obligatorio.
- correlacion, string, obligatorio.
- causacion, string, obligatorio.
- id_saga, string, obligatorio.
- id_solicitud, string, obligatorio.
- id_trabajo, string, obligatorio.
- codigo_motivo, string, obligatorio.
- detalle, string, obligatorio.

Identificadores:
- event_id: NO PRESENTE
- command_id: PRESENTE
- id_solicitud: PRESENTE
- id_trabajo: PRESENTE
- id_saga: PRESENTE
- correlacion: PRESENTE
- event_time: NO PRESENTE
- command_time: NO PRESENTE
- causacion: PRESENTE
- version: PRESENTE como version_contrato
- otro: id_partner PRESENTE

### Contrato: atencion-habilitada-registrada-v1.avsc

- Nombre: AtencionHabilitadaRegistradaV1
- Tipo: Event
- Version: 1
- Namespace: entrada.eventos
- Nombre Avro: AtencionHabilitadaRegistradaV1
- Evidencia: solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/eventos.py.

Campos:
- event_id, string, obligatorio, generado al registrar confirmacion.
- tipo, string, obligatorio, AtencionHabilitadaRegistrada.v1.
- version_contrato, int, obligatorio.
- instante, string, obligatorio.
- id_partner, string, obligatorio.
- correlacion, string, obligatorio.
- causacion, string, obligatorio, mapeado al command_id del comando entrante.
- id_saga, string, obligatorio.
- id_solicitud, string, obligatorio.
- id_trabajo, string, obligatorio.
- registrada_en, string, obligatorio, timestamp de persistencia del estado habilitado.

Identificadores:
- event_id: PRESENTE
- command_id: NO PRESENTE
- id_solicitud: PRESENTE
- id_trabajo: PRESENTE
- id_saga: PRESENTE
- correlacion: PRESENTE
- event_time: NO PRESENTE
- command_time: NO PRESENTE
- causacion: PRESENTE
- version: PRESENTE como version_contrato
- otro: id_partner PRESENTE

### Contrato: atencion-cancelada-registrada-v1.avsc

- Nombre: AtencionCanceladaRegistradaV1
- Tipo: Event
- Version: 1
- Namespace: entrada.eventos
- Nombre Avro: AtencionCanceladaRegistradaV1
- Evidencia: solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/eventos.py.

Campos:
- event_id, string, obligatorio.
- tipo, string, obligatorio, AtencionCanceladaRegistrada.v1.
- version_contrato, int, obligatorio.
- instante, string, obligatorio.
- id_partner, string, obligatorio.
- correlacion, string, obligatorio.
- causacion, string, obligatorio (command_id origen).
- id_saga, string, obligatorio.
- id_solicitud, string, obligatorio.
- id_trabajo, string, obligatorio.
- registrada_en, string, obligatorio.

Identificadores:
- event_id: PRESENTE
- command_id: NO PRESENTE
- id_solicitud: PRESENTE
- id_trabajo: PRESENTE
- id_saga: PRESENTE
- correlacion: PRESENTE
- event_time: NO PRESENTE
- command_time: NO PRESENTE
- causacion: PRESENTE
- version: PRESENTE como version_contrato
- otro: id_partner PRESENTE

### Contrato adicional relevante: solicitud-lista-v1.avsc

- Nombre: SolicitudListaV1
- Tipo: Event
- Version: 1
- Namespace: NO PRESENTE en el archivo avsc exportado
- Nombre Avro: SolicitudListaV1
- tipo semantico: SolicitudDePartnerListaParaAtencion.v1
- Evidencia: solicitud-partner/docs/contratos/solicitud-lista-v1.avsc, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py:50.

Campos e identificadores clave:
- event_id, correlacion, id_solicitud presentes.
- id_saga: NO PRESENTE.
- id_trabajo: NO PRESENTE.
- causacion: NO PRESENTE.

## 3. Matriz de mensajeria

Estado:
- IMPLEMENTADO: mensajeria Pulsar para comandos de entrada, evento solicitud-lista y respuestas de atencion.
- IMPLEMENTADO: outbox/inbox para durabilidad e idempotencia.
- CONFIGURADO: topicos en variables de entorno y Settings.

| Direccion | Tipo | Mensaje | Topic | Producer | Consumer | Correlacion | ID |
|---|---|---|---|---|---|---|---|
| Entrada externa -> solicitudes-partner | Command | RegistrarSolicitudPartner.v1 | PARTNER_REGISTRATION_TOPIC | Cliente externo/BFF/orquestador | CommandConsumer contrato RegistrarSolicitudPartner.v1 | NO PRESENTE | command_id |
| Orquestacion -> solicitudes-partner | Command | RegistrarAtencionHabilitada.v1 | PARTNER_ENABLE_ATTENTION_TOPIC | Orquestacion | CommandConsumer contrato RegistrarAtencionHabilitada.v1 | correlacion (debe igualar id_solicitud) | command_id |
| Orquestacion -> solicitudes-partner | Command | RegistrarAtencionCancelada.v1 | PARTNER_CANCEL_ATTENTION_TOPIC | Orquestacion | CommandConsumer contrato RegistrarAtencionCancelada.v1 | correlacion (debe igualar id_solicitud) | command_id |
| solicitudes-partner -> integraciones | Event | SolicitudDePartnerListaParaAtencion.v1 | PARTNER_PULSAR_TOPIC | DespachadorOutbox + PublicadorPulsar | Consumidores externos (suscripciones propias) | correlacion = id_solicitud | event_id |
| solicitudes-partner -> CQRS interno | Event | SolicitudDePartnerActualizada.v1 | PARTNER_CQRS_TOPIC | DespachadorOutbox + PublicadorPulsar | ConsumidorProyeccion | NO PRESENTE (usa id_solicitud en payload) | event_id |
| solicitudes-partner -> Orquestacion | Event | AtencionHabilitadaRegistrada.v1 | PARTNER_ATTENTION_ENABLED_TOPIC | compose_attention_publishers | Orquestacion (esperado) | correlacion | event_id |
| solicitudes-partner -> Orquestacion | Event | AtencionCanceladaRegistrada.v1 | PARTNER_ATTENTION_CANCELLED_TOPIC | compose_attention_publishers | Orquestacion (esperado) | correlacion | event_id |

Detalles de Pulsar realmente implementados:
- Subscriptions de command consumers:
  - entrada-registrar-solicitud-partner-v1
  - entrada-registrar-atencion-habilitada-v1
  - entrada-registrar-atencion-cancelada-v1
  - Evidencia: solicitud-partner/src/solicitudes_partner/config/bootstrap.py:225.
- Subscription type: Shared.
  - Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/consumidores.py:46.
- Initial position: Earliest.
  - Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/consumidores.py:45.
- Negative ACK redelivery delay: 1000 ms.
  - Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/consumidores.py:48.
- Message key (partition_key): id_solicitud para solicitudes-lista, lectura CQRS y replies de atencion.
  - Evidencia: solicitud-partner/src/solicitudes_partner/config/bootstrap.py:130, :191, :329.
- Properties publicadas: event_id y tipo.
  - Evidencia: solicitud-partner/src/solicitudes_partner/seedwork/infraestructura/publicador_pulsar.py:56.
- Headers HTTP no aplican a mensajeria; para API se usa X-Partner-Laboratorio.

## 4. Eventos que recibe Orquestacion

Evento objetivo revisado: SolicitudDePartnerListaParaAtencion.v1

Resultado:
- IMPLEMENTADO.
- Evidencia principal:
  - Construccion del mensaje: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py:43.
  - tipo exacto: SolicitudDePartnerListaParaAtencion.v1 en linea 50.
  - destino externo integracion.solicitud_lista.v1: solicitud-partner/src/solicitudes_partner/config/rutas.py:15.
  - publicacion a topico PARTNER_PULSAR_TOPIC: solicitud-partner/src/solicitudes_partner/config/bootstrap.py (componer_publicacion).

Donde se genera:
- Se genera cuando SolicitudPartner pasa a estado LISTA_PARA_ATENCION por evaluacion admisible.
- Evidencia:
  - transition en aggregate: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/dominio/entidades.py:106.
  - tipo de evento final admisible: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/dominio/entidades.py:120.
  - clase de evento: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/dominio/eventos.py:75.

Condicion que lo dispara:
- Resultado de evaluacion ADMISIBLE.
- Si es NO_ADMISIBLE se emite SolicitudPartnerRechazada y no va al destino externo de lista.
- Evidencia: solicitud-partner/src/solicitudes_partner/config/rutas.py:27, :28.

Payload real:
- event_id, tipo, version_contrato, instante, correlacion, id_solicitud, version_solicitud, id_partner, referencia_externa, categoria, tipo_solicitud, aprobacion_previa, tipo_red, id_politica, version_politica.
- Evidencia: solicitud-partner/docs/contratos/solicitud-lista-v1.avsc.

Topic:
- Configurable con PARTNER_PULSAR_TOPIC.
- Default: persistent://public/default/solicitud-partner-lista-v1.
- Evidencia: solicitud-partner/.env.example:6, solicitud-partner/src/solicitudes_partner/config/settings.py.

event_id:
- PRESENTE y estable para deduplicacion del consumidor.
- Evidencia: solicitud-partner/docs/contratos/solicitud-lista-v1.avsc.

id_solicitud:
- PRESENTE.

correlacion:
- PRESENTE y mapeada como id_solicitud.
- Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py:53.

estado de la solicitud al publicar:
- LISTA_PARA_ATENCION (version_solicitud 2).

cuando se publica:
- Despacho outbox posterior al commit de la transicion de dominio.

retry:
- IMPLEMENTADO en outbox por reprogramacion y reenvio.
- Evidencia: solicitud-partner/src/solicitudes_partner/seedwork/infraestructura/outbox.py.

idempotencia:
- Productor: identidad por event_id y destino en outbox.
- Consumidor de ejemplo: dedup por event_id en SQLite.
- Evidencia: solicitud-partner/src/solicitudes_partner/seedwork/infraestructura/outbox.py, solicitud-partner/scripts/consumir_eventos.py.

Inbox:
- En este flujo de salida no aplica inbox de entrada.
- Para consumo en otro servicio, se espera inbox propio del consumidor.

Si existe SolicitudDePartnerListaParaAtencion.v1:
- SI, IMPLEMENTADO.

## 5. Commands que envia Orquestacion

### RegistrarAtencionHabilitada.v1

Contrato Avro:
- IMPLEMENTADO en docs y en schema Python.
- Evidencia: solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc.

Campos:
- command_id, tipo, version_contrato, instante, id_partner, correlacion, causacion, id_saga, id_solicitud, id_trabajo.

Topic:
- PARTNER_ENABLE_ATTENTION_TOPIC.
- Default: persistent://public/default/registrar-atencion-habilitada-v1.
- Evidencia: solicitud-partner/.env.example:13.

Quien lo consume:
- CommandConsumer con contrato RegistrarAtencionHabilitada.v1.
- Handlers de aplicacion: EnableAttentionHandler.
- Evidencia: solicitud-partner/src/solicitudes_partner/config/bootstrap.py:240, :254.

Como se procesa:
- parse_command -> EnableAttentionCommand.
- Validaciones:
  - correlacion debe ser igual a id_solicitud.
  - solicitud debe existir, partner coincidir y estado LISTA_PARA_ATENCION.
  - saga_id/work_id deben coincidir si ya existia resultado previo.
- Persistencia:
  - dedup en inbox con nombre_consumidor solicitudes.comandos y id_evento=command_id.
  - upsert de solicitudes.atenciones.
  - emision de reply AtencionHabilitadaRegistrada.v1 a outbox.
- Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py:87, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py:56, solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/handlers/record_attention.py:25.

Idempotencia:
- Si el mismo command_id llega de nuevo con igual contenido, prepare_command devuelve False y no reprocesa.
- Si llega mismo command_id con contenido distinto, ContractConflict.

Respuesta/evento posterior:
- AtencionHabilitadaRegistrada.v1.
- Destination outbox: integracion.atencion_habilitada.v1.
- Topic: PARTNER_ATTENTION_ENABLED_TOPIC.

### RegistrarAtencionCancelada.v1

Contrato Avro:
- IMPLEMENTADO.
- Evidencia: solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc.

Campos:
- command_id, tipo, version_contrato, instante, id_partner, correlacion, causacion, id_saga, id_solicitud, id_trabajo, codigo_motivo, detalle.

Topic:
- PARTNER_CANCEL_ATTENTION_TOPIC.
- Default: persistent://public/default/registrar-atencion-cancelada-v1.
- Evidencia: solicitud-partner/.env.example:14.

Quien lo consume:
- CommandConsumer + CancelAttentionHandler.

Como se procesa:
- parse_command -> CancelAttentionCommand.
- validaciones equivalentes de solicitud/partner/estado/saga/work.
- persistencia en solicitudes.atenciones como ATENCION_CANCELADA.
- reply AtencionCanceladaRegistrada.v1.

Idempotencia:
- Igual estrategia de command inbox por command_id.

Respuesta/evento posterior:
- AtencionCanceladaRegistrada.v1.
- Destination outbox: integracion.atencion_cancelada.v1.
- Topic: PARTNER_ATTENTION_CANCELLED_TOPIC.

## 6. Eventos de respuesta

### AtencionHabilitadaRegistrada.v1

Quien lo produce:
- solicitudes-partner via record_reply + outbox + compose_attention_publishers.

Cuando se produce:
- Despues de persistir resultado habilitado en solicitudes.atenciones y confirmar transaccion.

Payload:
- event_id, tipo, version_contrato, instante, id_partner, correlacion, causacion, id_saga, id_solicitud, id_trabajo, registrada_en.

Topic:
- PARTNER_ATTENTION_ENABLED_TOPIC.

event_id / id_solicitud / id_trabajo / correlacion:
- PRESENTES.

Relacion con comando origen:
- causacion = command_id del comando recibido.
- Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py (serialize_reply).

retry:
- Outbox reintenta si no confirma envio.

deduplicacion:
- En productor por id_evento + destino en outbox.
- En consumidor, no implementado aqui (debe hacerlo el consumidor externo).

### AtencionCanceladaRegistrada.v1

Quien lo produce:
- solicitudes-partner, mismo pipeline de replies.

Cuando se produce:
- Despues de persistir estado cancelado.

Payload:
- Misma estructura que habilitada, con tipo AtencionCanceladaRegistrada.v1.
- Nota: NO incluye codigo_motivo ni detalle en el evento de salida.

Topic:
- PARTNER_ATTENTION_CANCELLED_TOPIC.

event_id / id_solicitud / id_trabajo / correlacion:
- PRESENTES.

Relacion con comando origen:
- causacion = command_id del comando de cancelacion.

retry y deduplicacion:
- Igual que evento habilitada.

## 7. Flujo real de atencion habilitada

Flujo real:

API/Command
- Command Avro RegistrarAtencionHabilitada.v1 llega por topic de comandos.

Aplicacion
- CommandConsumer recibe, parsea y llama EnableAttentionHandler.

Aggregate/Domain
- Se valida solicitud LISTA_PARA_ATENCION.
- Se carga/crea AttentionResult.
- Se aplica enable.

Persistencia
- Command inbox (mensajeria.inbox) registra command_id por consumidor solicitudes.comandos.
- Tabla solicitudes.atenciones se guarda con estado ATENCION_HABILITADA.

Evento/Command
- Se crea AttentionConfirmation y se serializa AtencionHabilitadaRegistrada.v1.

Pulsar
- Outbox destino integracion.atencion_habilitada.v1.
- Publicador a PARTNER_ATTENTION_ENABLED_TOPIC.

Siguiente componente
- Orquestacion (u otro consumidor) suscrito al topic de respuesta.

Evidencia principal:
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/consumidores.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/handlers/record_attention.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/unidad_trabajo.py:43
- solicitud-partner/src/solicitudes_partner/config/bootstrap.py:310

## 8. Flujo real de atencion cancelada

Flujo real:

API/Command
- Command Avro RegistrarAtencionCancelada.v1 por topic de comandos.

Aplicacion
- CommandConsumer -> CancelAttentionHandler.

Aggregate/Domain
- Valida solicitud y coherencia de partner/saga/work.
- Aplica cancel con reason_code y detail.

Persistencia
- Inbox dedup por command_id.
- solicitudes.atenciones actualizado/guardado como ATENCION_CANCELADA.

Evento/Command
- AttentionConfirmation serializa AtencionCanceladaRegistrada.v1.

Pulsar
- Outbox destino integracion.atencion_cancelada.v1.
- Publicacion a PARTNER_ATTENTION_CANCELLED_TOPIC.

Siguiente componente
- Orquestacion consumidor del evento de cancelacion.

Evidencia:
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/handlers/record_attention.py:92
- solicitud-partner/src/solicitudes_partner/config/rutas.py:17
- solicitud-partner/src/solicitudes_partner/config/bootstrap.py:305

## 9. CQRS

Archivos solicitados:
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/confirmaciones.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/consultas.py

Commands existentes:
- RegistrationCommand.
- EnableAttentionCommand.
- CancelAttentionCommand.

Handlers de command:
- RegisterOperationHandler.
- EnableAttentionHandler.
- CancelAttentionHandler.

Confirmaciones:
- ConfirmacionRegistroSolicitud (HTTP registro).
- AttentionConfirmation (base para eventos Atencion*Registrada).

Queries:
- RequestStatusQueryHandler.operation.
- RequestStatusQueryHandler.attention.
- ConsultarSolicitudHandler, ListarSolicitudesHandler.

Relacion command -> evento:
- Attention commands generan AttentionConfirmation y luego Atencion*Registrada.v1.
- RegistrarSolicitudPartner.v1 genera OperationResult y, por flujo interno, puede terminar produciendo SolicitudDePartnerListaParaAtencion.v1 si queda admisible.

Donde se ejecuta la logica de aplicacion:
- En handlers de aplicacion, orquestados por UnidadTrabajoSolicitudesSQL.
- Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/handlers.

## 10. Command Inbox / idempotencia

Tabla existente:
- mensajeria.inbox.
- Evidencia: solicitud-partner/migraciones/versions/0001_persistencia.py:37.

Campos:
- nombre_consumidor (PK parte 1)
- id_evento (PK parte 2)
- documento
- procesada_en
- Evidencia: solicitud-partner/src/solicitudes_partner/seedwork/infraestructura/inbox.py.

Uso exacto:
- Command handlers usan prepare_command, que delega en prepare_message con:
  - consumidor fijo solicitudes.comandos
  - id_evento = command.command_id
  - documento = serialize_command(command)
- Evidencia: solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/unidad_trabajo.py:43-46.

Que identifica como duplicado:
- Misma clave compuesta (nombre_consumidor, id_evento).

Que ID utiliza:
- command_id del comando entrante.

Como registra comando procesado:
- INSERT ON CONFLICT DO NOTHING en inbox.
- Si inserta, retorna True y procesa.
- Si ya existe y documento igual, retorna False (dedup).
- Si ya existe y documento distinto, error de conflicto.
- Evidencia: solicitud-partner/src/solicitudes_partner/seedwork/infraestructura/inbox.py.

Que ocurre si llega dos veces:
- mismo command_id + mismo contenido: no reprocesa, retorna resultado previo o no-op segun handler.
- mismo command_id + distinto contenido: ContractConflict.

Que ocurre ante error:
- Si falla antes de commit, rollback revierte inbox, estado de negocio y outbox.
- Evidencia: solicitud-partner/tests/integracion/test_request_commands_persistence.py (test_sql_failure_after_outbox_write_rolls_back_all).

Participacion en RegistrarAtencionHabilitada:
- SI participa.

Participacion en RegistrarAtencionCancelada:
- SI participa.

No confusiones:
- NO es SagaLog.
- NO es tabla outbox.
- Es inbox general de mensajeria reutilizado por consumidores.

Cambio de commit 0005:
- Se normaliza nombre_consumidor desde solicitudes.comandos.e5 a solicitudes.comandos.
- Evidencia: solicitud-partner/migraciones/versions/0005_command_inbox_name.py:11.

## 11. Persistencia

Migraciones revisadas:
- 0004_operaciones_atenciones.py
- 0005_command_inbox_name.py

Tablas y estructuras relevantes:

1) solicitudes.operaciones
- PK: id_operacion
- FK: id_solicitud -> solicitudes.solicitudes(id)
- Check: ck_operacion_resultado
- Uso: estado de procesamiento de RegistrarSolicitudPartner.
- Evidencia: solicitud-partner/migraciones/versions/0004_operaciones_atenciones.py:10.

2) solicitudes.atenciones
- PK: id_solicitud
- FK: id_solicitud -> solicitudes.solicitudes(id)
- Campos: id_saga, id_trabajo, estado, habilitada_en, cancelada_en, codigo_motivo, detalle
- Check: ck_atencion_resultado
- Uso: evidencia de atencion habilitada/cancelada.
- Evidencia: solicitud-partner/migraciones/versions/0004_operaciones_atenciones.py:24.

3) mensajeria.inbox
- PK compuesta (nombre_consumidor, id_evento)
- Uso: dedup de comandos/eventos consumidos.
- Evidencia: solicitud-partner/migraciones/versions/0001_persistencia.py:37.

4) mensajeria.outbox
- PK: id
- UNIQUE: (id_evento, destino)
- Index: ix_salida_pendiente
- Uso: entrega durable con retry.
- Evidencia: solicitud-partner/migraciones/versions/0001_persistencia.py:41.

5) migracion 0005
- UPDATE de nombre_consumidor en inbox.

Que evidencia necesita Orquestador para considerar procesado RegistrarAtencionHabilitada:
- Minimo tecnico recomendado:
  - recibir AtencionHabilitadaRegistrada.v1 con causacion=command_id enviado.
  - y correlacion/id_solicitud esperados.
- Evidencia interna en solicitudes-partner (si se audita DB):
  - fila en solicitudes.atenciones con estado ATENCION_HABILITADA y habilitada_en no nulo.

Que evidencia necesita para RegistrarAtencionCancelada:
- recibir AtencionCanceladaRegistrada.v1 con causacion=command_id.
- evidencia interna equivalente:
  - solicitudes.atenciones estado ATENCION_CANCELADA, cancelada_en no nulo, codigo_motivo/detalle no nulos.

## 12. API util para pruebas

DOCUMENTADO + IMPLEMENTADO:
- POST /solicitudes
- GET /solicitudes/{id_solicitud}
- GET /solicitudes
- GET /solicitudes/{id_solicitud}/atencion
- GET /operaciones/{id_operacion}
- Evidencia: solicitud-partner/docs/contratos/openapi.json:8, :132, :190, :244.

Endpoints relacionados con solicitudes:
- POST /solicitudes dispara comando de aplicacion RegistrarSolicitudPartner (via handler HTTP, no via Pulsar).
- GET de solicitud y listado consultan vista CQRS.

Endpoints relacionados con atencion:
- GET /solicitudes/{id_solicitud}/atencion consulta estado de atencion en lectura combinada.
- NO ENCONTRADO endpoint HTTP para habilitar/cancelar atencion; eso se hace por comandos Pulsar.

Endpoint operaciones:
- GET /operaciones/{id_operacion} sirve para inspeccionar resultado de comando de registro de solicitud.

Separacion importante:
- API para pruebas/entrada externa:
  - HTTP en solicitud-partner/src/solicitudes_partner/api.
- Comunicacion entre microservicios:
  - Pulsar commands/events en topics configurables.
- Conclusion: Orquestacion no necesita consumir esta API para integrar saga de atencion.

## 13. Configuracion Pulsar

Variables exactas encontradas:
- PARTNER_PULSAR_URL
- PARTNER_PULSAR_TOPIC
- PARTNER_CQRS_TOPIC
- PARTNER_CQRS_SUBSCRIPTION
- PARTNER_REGISTRATION_TOPIC
- PARTNER_ENABLE_ATTENTION_TOPIC
- PARTNER_CANCEL_ATTENTION_TOPIC
- PARTNER_ATTENTION_ENABLED_TOPIC
- PARTNER_ATTENTION_CANCELLED_TOPIC
- Evidencia: solicitud-partner/.env.example:5-16, solicitud-partner/src/solicitudes_partner/config/settings.py:51-74.

Configuracion de consumidores/producers:
- CommandConsumer: Shared, Earliest, negative_ack_redelivery_delay_ms=1000.
- PublicadorPulsar: properties event_id y tipo; partition_key id_solicitud.

Database:
- PARTNER_DATABASE_URL (postgresql+psycopg obligatorio en runtime DB).
- Evidencia: solicitud-partner/src/solicitudes_partner/config/database.py.

Compose:
- Postgres 17.6 y Pulsar 4.1.3 para entorno local.
- Evidencia: solicitud-partner/docker-compose.yaml.

## 14. Tests existentes

Cobertura relevante encontrada:

- Contratos Avro comandos y replies:
  - solicitud-partner/tests/contratos/test_request_commands.py
- Integracion E2E transporte de comandos y replies:
  - solicitud-partner/tests/integracion/test_request_commands_transport.py:109
- Persistencia de comandos/atencion/idempotencia:
  - solicitud-partner/tests/integracion/test_request_commands_persistence.py
- Migraciones e inbox rename:
  - solicitud-partner/tests/integracion/test_migraciones.py:62
- Semantica de ack/nack consumidor:
  - solicitud-partner/tests/unitarias/test_command_consumer.py:13

Escenarios pedidos:

Prueba 1: Registrar/activar atencion
- SI existe.
- Evidencia: test_real_ingress_http_attention_and_recovery.

Prueba 2: Cancelar atencion
- SI existe.
- Evidencia: mismo test anterior envia RegistrarAtencionCancelada y valida reply/evento.

Prueba 3: Comando duplicado
- SI existe.
- Evidencia: test_attention_deduplicates_and_cancellation_wins, test_registration_deduplicates_and_exposes_errors.

Prueba 4: Error/reintento
- SI existe.
- Evidencia:
  - redelivery_after_commit_before_ack.
  - outbox_resends_same_event_after_publish_before_mark.
  - tests de ack/nack en consumidor unitario.

Prueba 5: Evento generado despues del procesamiento
- SI existe.
- Evidencia:
  - validaciones de replies Atencion*Registrada posteriores al procesamiento.
  - validacion outbox en test_concurrent_enable_cancel_and_durable_replies.

## 15. Matriz de integracion para Orquestacion

### A. Matriz para SagaCoordinator

| Paso Saga | Mensaje | Direccion | Topic | Correlacion | Resultado esperado |
|---|---|---|---|---|---|
| Recepcion de oportunidad de atencion | SolicitudDePartnerListaParaAtencion.v1 | solicitudes-partner -> orquestacion | PARTNER_PULSAR_TOPIC | correlacion=id_solicitud | Saga inicia/avanza con solicitud lista |
| Solicitar habilitacion | RegistrarAtencionHabilitada.v1 | orquestacion -> solicitudes-partner | PARTNER_ENABLE_ATTENTION_TOPIC | correlacion=id_solicitud (obligatorio) | Solicitud de atencion habilitada procesada |
| Confirmacion de habilitacion | AtencionHabilitadaRegistrada.v1 | solicitudes-partner -> orquestacion | PARTNER_ATTENTION_ENABLED_TOPIC | correlacion=id_solicitud | Paso de saga confirmado habilitado |
| Solicitar cancelacion | RegistrarAtencionCancelada.v1 | orquestacion -> solicitudes-partner | PARTNER_CANCEL_ATTENTION_TOPIC | correlacion=id_solicitud (obligatorio) | Solicitud de cancelacion procesada |
| Confirmacion de cancelacion | AtencionCanceladaRegistrada.v1 | solicitudes-partner -> orquestacion | PARTNER_ATTENTION_CANCELLED_TOPIC | correlacion=id_solicitud | Paso de saga confirmado cancelado |

### B. Diferencias con el diseno de Entrega 5

Comparacion implementado real vs expectativas tipicas del diseno de saga (segun contratos solicitados):

- ✅ Coincide: existen comandos RegistrarAtencionHabilitada.v1 y RegistrarAtencionCancelada.v1.
- ✅ Coincide: existen eventos AtencionHabilitadaRegistrada.v1 y AtencionCanceladaRegistrada.v1.
- ✅ Coincide: existe evento SolicitudDePartnerListaParaAtencion.v1.
- ✅ Coincide: correlacion, causacion, id_saga, id_solicitud, id_trabajo presentes en contratos de atencion.
- ⚠️ Diferencia: contratos usan campo instante, no command_time/event_time.
- ⚠️ Diferencia: namespace de comandos de atencion es orquestacion.eventos (nombre semantico mixto command/event).
- ⚠️ Diferencia: AtencionCanceladaRegistrada.v1 no transporta codigo_motivo ni detalle, aunque el comando de cancelacion si los trae y se persisten.
- ⚠️ Diferencia: command inbox no es una tabla separada por modulo, sino mensajeria.inbox compartida por consumidor.
- ❌ No implementado: evento llamado exactamente SolicitudDePartnerListaParaAtencion con otro nombre de archivo/record distinto. El record real es SolicitudListaV1 con tipo=SolicitudDePartnerListaParaAtencion.v1.
- ❓ No se pudo determinar: politicas de DLQ centralizada en broker para comandos de atencion (no se observa configuracion dedicada en codigo).

## 16. Diferencias con el diseno de Entrega 5

Resumen estructurado por estado:

DOCUMENTADO:
- Contratos Avro de comandos y replies de atencion en docs/contratos.

IMPLEMENTADO:
- Consumo real de comandos por topics dedicados.
- Persistencia de atenciones en tabla solicitudes.atenciones.
- Emision de eventos Atencion*Registrada por outbox.

CONFIGURADO:
- Topicos y suscripciones por variables PARTNER_*.
- Shared subscription para consumidores de comandos.

NO ENCONTRADO:
- API HTTP para ejecutar habilitacion/cancelacion de atencion.
- Campo event_time o command_time en contratos de atencion.
- Campo id_saga o id_trabajo en SolicitudDePartnerListaParaAtencion.v1.

## 17. Escenarios de prueba para Orquestacion

Sin implementar, escenarios que este repositorio habilita probar:

Happy Path
- Orquestacion consume SolicitudDePartnerListaParaAtencion.v1.
- Orquestacion publica RegistrarAtencionHabilitada.v1.
- solicitudes-partner procesa y publica AtencionHabilitadaRegistrada.v1.
- Orquestacion confirma avance de saga por causacion=command_id.

Cancelacion
- Orquestacion publica RegistrarAtencionCancelada.v1.
- solicitudes-partner procesa y publica AtencionCanceladaRegistrada.v1.
- Orquestacion confirma rama de cancelacion.

Duplicado
- Reenvio del mismo command_id en habilitar/cancelar.
- Resultado esperado: no reproceso de negocio; dedup por inbox.

Error
- Fallo despues de commit y antes de ACK: puede haber redelivery.
- Resultado esperado: comando/evento reenviado sin duplicar efecto persistente.
- Evidencia de comportamiento: tests de redelivery y outbox resend.

## 18. Riesgos / dudas / informacion faltante

Riesgos tecnicos para SagaCoordinator:
- El evento AtencionCanceladaRegistrada.v1 no incluye codigo_motivo/detalle; si Orquestacion requiere esa causa en su estado, debera obtenerla por otra via o ajustar contrato en otro incremento.
- Correlacion se exige igual a id_solicitud para comandos de atencion; cualquier estrategia de correlacion alternativa fallara por validacion.
- Si Orquestacion reutiliza command_id con payload distinto, solicitudes-partner respondera con conflicto de contrato.
- La API HTTP no reemplaza comandos de integracion para atencion.

Dudas abiertas:
- Politica exacta de reintento desde el lado Orquestacion (numero de intentos/backoff) no esta definida en este repositorio.
- No hay evidencia de DLQ dedicada por cada topic de comando de atencion en codigo.

Informacion faltante para cierre de integracion total:
- Parametros finales de despliegue compartido (topics definitivos por ambiente).
- Contrato esperado del lado Orquestacion para trazabilidad de motivos de cancelacion en evento de respuesta.

## 19. Conclusion

El repositorio solicitudes-partner SI implementa los elementos minimos para integrar SagaCoordinator de orquestacion-trabajos en Entrega 5:
- evento de entrada SolicitudDePartnerListaParaAtencion.v1,
- comandos de atencion habilitada/cancelada,
- eventos de confirmacion Atencion*Registrada,
- idempotencia de comandos via command inbox,
- entrega durable con outbox y reintentos.

Para el diseno del SagaCoordinator, la correlacion operativa principal debe usar id_solicitud (campo correlacion en comandos/eventos), y la confirmacion de procesamiento debe apoyarse en causacion=command_id en los eventos de respuesta.

NO se detecta en este repositorio necesidad de integrar por API HTTP para atencion entre microservicios; el canal implementado es mensajeria Pulsar.
