# Auditoria Tecnica de orquestacion-trabajos para Entrega 5

Fecha de auditoria: 2026-09-20  
Alcance: revision completa en modo lectura del repositorio orquestacion-trabajos y contraste contra contratos-saga-propuesta.md.  
Restricciones cumplidas durante el diagnostico: no se modificaron archivos del servicio, no se hicieron migraciones y no se hicieron commits.

## 1. Estructura del proyecto

Estructura principal validada:

- Codigo fuente del servicio en src/orquestacion_trabajos/
- Migraciones Alembic en migraciones/
- Scripts operativos en scripts/
- Pruebas en tests/
- Contratos documentados en docs/contratos/

Punto de entrada de app: src/orquestacion_trabajos/api/app.py

## 2. Framework y lenguaje

- Lenguaje: Python 3.12 (pyproject.toml)
- API: FastAPI
- Persistencia: SQLAlchemy + Alembic + psycopg
- Mensajeria: Apache Pulsar con Avro (pulsar-client[avro])

## 3. Arquitectura por capas

Capas y composicion identificadas:

- API HTTP: src/orquestacion_trabajos/api/trabajos.py
- Aplicacion: comandos, consultas y handlers en modulos/trabajos/aplicacion/
- Dominio: entidad Trabajo, VOs y eventos internos en modulos/trabajos/dominio/
- Infraestructura: repositorios SQL, consumidores Pulsar, despacho outbox, esquemas Avro en modulos/trabajos/infraestructura/
- Seedwork transversal: contratos base, UoW SQL, inbox/outbox y ciclos en seedwork/
- Wiring y bootstrap: config/bootstrap.py

## 4. Aggregate Roots

Aggregate Root efectivo:

- Trabajo (modulos/trabajos/dominio/entidades.py)

Observacion:

- El servicio aun no tiene un Aggregate Root de Saga ni una entidad de coordinacion explicita.

## 5. Entities

Entidades principales:

- Trabajo

Estados actuales de Trabajo:

- PENDIENTE_COTIZACION
- COTIZADO
- COTIZACION_RECHAZADA

## 6. Value Objects

VOs de dominio:

- OrigenSolicitud
- CondicionesAtencion
- ResultadoCotizacion

Ubicacion:

- modulos/trabajos/dominio/objetos_valor.py

## 7. Commands

Comandos de aplicacion internos:

- CrearTrabajoCommand
- AplicarCotizacionCommand

DTOs de entrada para esos comandos:

- SolicitudListaParaAtencion
- ResultadoCotizacionEntrada

Ubicacion:

- modulos/trabajos/aplicacion/comandos.py

## 8. Queries

Consultas implementadas:

- consultar_por_id
- consultar

DTOs de consulta:

- TrabajoConsulta
- ResultadoCotizacionConsulta
- FiltroTrabajos

Ubicacion:

- modulos/trabajos/aplicacion/consultas.py
- modulos/trabajos/infraestructura/repositorios.py
- api/trabajos.py

## 9. Domain Events

Eventos de dominio internos detectados:

- TrabajoCreado (interno)
- CotizacionAplicada (interno)

Ubicacion:

- modulos/trabajos/dominio/eventos.py

## 10. Integration Events

Contratos de integracion usados por el servicio:

- SolicitudDePartnerListaParaAtencion.v1 (consume)
- TrabajoCreado.v1 (produce)
- SolicitarCotizacion.v1 (produce)
- CotizacionRegistrada.v1 (consume)
- CotizacionRechazada.v1 (consume)

Ubicacion de esquemas Python Avro:

- modulos/trabajos/infraestructura/esquemas/v1/entrada.py
- modulos/trabajos/infraestructura/esquemas/v1/orquestacion.py
- modulos/trabajos/infraestructura/esquemas/v1/cotizaciones.py

## 11. Consumers Pulsar

Consumers activos en composicion:

- entrada
- registrada
- rechazada

Fuentes configuradas:

- solicitud-partner-lista-v1 con suscripcion orquestacion-solicitudes-v1
- cotizacion-registrada-v1 con suscripcion orquestacion-cotizacion-registrada-v1
- cotizacion-rechazada-v1 con suscripcion orquestacion-cotizacion-rechazada-v1

Ubicacion:

- config/rutas.py
- config/bootstrap.py
- modulos/trabajos/infraestructura/consumidores.py
- seedwork/infraestructura/consumidor_pulsar.py

## 12. Producers Pulsar

Producers (via outbox + despachador) activos:

- TrabajoCreado.v1
- SolicitarCotizacion.v1

Destinos configurados:

- trabajo-creado-v1
- solicitar-cotizacion-v1

Ubicacion:

- config/rutas.py
- config/bootstrap.py
- modulos/trabajos/infraestructura/despacho.py
- seedwork/infraestructura/publicador_pulsar.py

## 13. Topics

Topics de entrada (consume):

- persistent://{tenant}/{namespace}/solicitud-partner-lista-v1
- persistent://{tenant}/{namespace}/cotizacion-registrada-v1
- persistent://{tenant}/{namespace}/cotizacion-rechazada-v1

Topics de salida (produce):

- persistent://{tenant}/{namespace}/trabajo-creado-v1
- persistent://{tenant}/{namespace}/solicitar-cotizacion-v1

Fuente:

- config/rutas.py

## 14. Subscriptions

Subscriptions propias de este servicio:

- orquestacion-solicitudes-v1
- orquestacion-cotizacion-registrada-v1
- orquestacion-cotizacion-rechazada-v1

Nota:

- Suscripciones de servicios consumidores externos como seguimiento-trabajos-v1 y cotizaciones-peticiones-v1 aparecen en docs, no en la ejecucion interna de este proceso.

## 15. Inbox

Implementacion:

- Tabla inbox con unique (consumidor, id_mensaje)
- Dedupe por id_mensaje por consumidor
- Si mismo id con contenido distinto: InboxConflictError

Ubicacion:

- seedwork/infraestructura/orm.py
- seedwork/infraestructura/inbox.py

## 16. Outbox

Implementacion:

- Tabla outbox con estado PENDIENTE/PROCESADA
- Despacho una fila por transaccion
- Seleccion con FOR UPDATE SKIP LOCKED
- Marca PROCESADA solo despues de publicar

Ubicacion:

- seedwork/infraestructura/orm.py
- seedwork/infraestructura/outbox.py
- seedwork/infraestructura/despacho_outbox.py

## 17. Base de datos

Motor:

- PostgreSQL via SQLAlchemy

Configuracion:

- ORQUESTACION_DATABASE_URL
- Pool con pre_ping y timeouts

Ubicacion:

- config/database.py
- config/settings.py

## 18. Tablas

Tablas del modelo actual:

- trabajos
- inbox
- outbox

Migracion base:

- migraciones/versions/0001_persistencia.py

## 19. Repositorios

Repositorio de dominio:

- RepositorioTrabajos (contrato abstracto)

Repositorio concreto:

- SqlAlchemyRepositorioTrabajos

Funciones destacadas:

- guardar
- obtener_por_id
- obtener_por_solicitud
- consultar_por_id
- consultar

Ubicacion:

- modulos/trabajos/dominio/repositorios.py
- modulos/trabajos/infraestructura/repositorios.py

## 20. Casos de uso

Casos de uso implementados:

- CrearTrabajoHandler.ejecutar
- AplicarCotizacionHandler.ejecutar
- ConsultarTrabajosHandler.por_id
- ConsultarTrabajosHandler.listar

Ubicacion:

- modulos/trabajos/aplicacion/handlers/crear_trabajo.py
- modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py
- modulos/trabajos/aplicacion/handlers/consultar_trabajos.py

## 21. Manejo de errores

Mecanismos observados:

- Clasificacion REINTENTAR vs PAUSAR en consumidor de infraestructura
- NACK en errores transitorios; ACK solo despues de procesar correctamente
- Error SQL a HTTP 503 en API
- ConcurrencyConflictError en repositorio al actualizar version optimista
- ColisionPersistencia para restricciones de unicidad reintentables

Ubicacion:

- modulos/trabajos/infraestructura/consumidores.py
- seedwork/infraestructura/consumidor_pulsar.py
- api/app.py
- modulos/trabajos/infraestructura/repositorios.py
- seedwork/infraestructura/unidad_trabajo_sqlalchemy.py

## 22. Idempotencia

Controles identificados:

- Inbox dedup por (consumidor, id_mensaje)
- Conflicto cuando mismo ID trae payload diferente
- Idempotencia por id_solicitud al crear Trabajo (unique + validacion de igualdad de origen)
- Resultado terminal no puede ser reemplazado por otro distinto

Ubicacion:

- seedwork/infraestructura/inbox.py
- modulos/trabajos/infraestructura/orm.py
- modulos/trabajos/aplicacion/handlers/crear_trabajo.py
- modulos/trabajos/dominio/entidades.py

## 23. Tests existentes

Cobertura existente por area:

- Dominio: tests/unitarias/dominio/test_trabajos.py
- Aplicacion: tests/unitarias/aplicacion/test_trabajos_aplicacion.py
- Infraestructura de consumidores/despacho/esquemas/repositorio:
  - tests/unitarias/infraestructura/test_consumidor_pulsar.py
  - tests/unitarias/infraestructura/test_consumidor_entrada_avro.py
  - tests/unitarias/infraestructura/test_consumidores_resultados_avro.py
  - tests/unitarias/infraestructura/test_despacho_avro.py
  - tests/unitarias/infraestructura/test_mapeadores_eventos.py
  - tests/unitarias/infraestructura/test_repositorio_trabajos_sql.py
  - tests/unitarias/infraestructura/test_esquemas_python.py
  - tests/unitarias/infraestructura/test_cotizaciones_avro.py
- API: tests/api/test_trabajos.py
- Salud y alineacion: tests/test_health.py, tests/test_alineacion.py
- Migraciones: tests/test_migraciones.py
- Contratos compartidos: tests/contratos/test_contratos_compartidos.py

## Ubicacion exacta de contratos solicitados

### 1) SolicitudDePartnerListaParaAtencion.v1

- Archivo:
  - modulos/trabajos/infraestructura/esquemas/v1/entrada.py
  - modulos/trabajos/infraestructura/consumidores.py
  - modulos/trabajos/infraestructura/mapeadores_eventos.py
- Clase:
  - SolicitudListaV1 (alias SolicitudDePartnerListaParaAtencionV1)
  - MapeadorEventoEntrada
- Metodo:
  - mensaje_a_solicitud
  - procesador (rama tipo entrada)
- Rol:
  - Consumer
- Topic:
  - persistent://{tenant}/{namespace}/solicitud-partner-lista-v1
- Persistencia relacionada:
  - registro en inbox
  - creacion/lectura de trabajo
  - generacion de 2 salidas en outbox

### 2) TrabajoCreado.v1

- Archivo:
  - modulos/trabajos/infraestructura/esquemas/v1/orquestacion.py
  - modulos/trabajos/infraestructura/mapeadores_eventos.py
  - modulos/trabajos/infraestructura/unidad_trabajo.py
  - seedwork/infraestructura/despacho_outbox.py
- Clase:
  - TrabajoCreadoV1
  - MapeadorTrabajoAvro
- Metodo:
  - trabajo_a_trabajo_creado
  - registrar_creacion
  - despachar_siguiente
- Rol:
  - Producer
- Topic:
  - persistent://{tenant}/{namespace}/trabajo-creado-v1
- Persistencia relacionada:
  - fila outbox tipo TrabajoCreado.v1, luego PROCESADA al publicar

### 3) SolicitarCotizacion.v1

- Archivo:
  - modulos/trabajos/infraestructura/esquemas/v1/orquestacion.py
  - modulos/trabajos/infraestructura/mapeadores_eventos.py
  - modulos/trabajos/infraestructura/unidad_trabajo.py
  - seedwork/infraestructura/despacho_outbox.py
- Clase:
  - SolicitarCotizacionV1
  - MapeadorTrabajoAvro
- Metodo:
  - trabajo_a_solicitar_cotizacion
  - registrar_creacion
  - despachar_siguiente
- Rol:
  - Producer
- Topic:
  - persistent://{tenant}/{namespace}/solicitar-cotizacion-v1
- Persistencia relacionada:
  - fila outbox tipo SolicitarCotizacion.v1, luego PROCESADA al publicar

### 4) CotizacionRegistrada.v1

- Archivo:
  - modulos/trabajos/infraestructura/esquemas/v1/cotizaciones.py
  - modulos/trabajos/infraestructura/mapeadores_eventos.py
  - modulos/trabajos/infraestructura/consumidores.py
  - modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py
- Clase:
  - CotizacionRegistradaV1
  - MapeadorResultadoCotizacion
  - AplicarCotizacionHandler
- Metodo:
  - cotizacion_registrada_a_resultado
  - procesador (rama tipo registrada)
  - ejecutar
- Rol:
  - Consumer
- Topic:
  - persistent://{tenant}/{namespace}/cotizacion-registrada-v1
- Persistencia relacionada:
  - inbox dedupe
  - actualizacion de trabajo con resultado aceptado

### 5) CotizacionRechazada.v1

- Archivo:
  - modulos/trabajos/infraestructura/esquemas/v1/cotizaciones.py
  - modulos/trabajos/infraestructura/mapeadores_eventos.py
  - modulos/trabajos/infraestructura/consumidores.py
  - modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py
- Clase:
  - CotizacionRechazadaV1
  - MapeadorResultadoCotizacion
  - AplicarCotizacionHandler
- Metodo:
  - cotizacion_rechazada_a_resultado
  - procesador (rama tipo rechazada)
  - ejecutar
- Rol:
  - Consumer
- Topic:
  - persistent://{tenant}/{namespace}/cotizacion-rechazada-v1
- Persistencia relacionada:
  - inbox dedupe
  - actualizacion de trabajo con resultado rechazado

## Comparacion contra contratos-saga-propuesta.md

### Hallazgo global

El servicio implementa correctamente la base transaccional de mensajeria (inbox/outbox/UoW/ack tardio) y los 5 contratos existentes, pero no implementa aun la coordinacion completa de Saga propuesta para Entrega 5.

## Matriz de brecha Entrega 5

| REQUISITO DE ENTREGA 5 | IMPLEMENTADO | FALTA | ARCHIVO AFECTADO | CAMBIO PROPUESTO |
|---|---|---|---|---|
| Conservar contratos v1 existentes (5 contratos base) | Si | Ajuste menor de consistencia documental | docs/contratos/README.md | Actualizar texto para reflejar que ya hay consumo de resultados de cotizacion |
| Orquestacion como coordinador de Saga | No | Modelo de Saga y reglas de coordinacion | modulos/trabajos/dominio/, modulos/trabajos/aplicacion/ | Introducir agregado/proceso de Saga con estados y transiciones |
| Saga Log durable | No | Tabla(s) y repositorio de saga log | migraciones/versions/0001_persistencia.py, seedwork/infraestructura/orm.py | Agregar persistencia de pasos y estado de saga |
| AbrirSeguimientoTrabajo.v1 | No | Contrato, mapeo, producer y destino | modulos/trabajos/infraestructura/esquemas/v1/, config/rutas.py, config/bootstrap.py | Incorporar contrato Avro y salida outbox |
| SeguimientoTrabajoAbierto.v1 | No | Contrato, topic y consumer | config/rutas.py, config/bootstrap.py, infraestructura/consumidores.py | Agregar fuente y handler de avance de saga |
| AperturaSeguimientoFallida.v1 | No | Contrato, topic y consumer | config/rutas.py, config/bootstrap.py, infraestructura/consumidores.py | Agregar fuente y handler de compensacion |
| CancelarSeguimientoTrabajo.v1 | No | Contrato y producer | esquemas/v1/, mapeadores_eventos.py, unidad_trabajo.py | Emitir comando de compensacion en outbox |
| SeguimientoTrabajoCancelado.v1 | No | Contrato y consumer | rutas.py, bootstrap.py, consumidores.py | Consumir confirmacion para cerrar compensacion |
| AnularCotizacion.v1 / CotizacionAnulada.v1 | No | Comando/evento de compensacion con su flujo | esquemas/v1/, rutas.py, bootstrap.py, handlers | Implementar ida y vuelta de anulacion |
| RegistrarAtencionHabilitada.v1 / AtencionHabilitadaRegistrada.v1 | No | Integracion con Entrada para cierre exitoso | rutas.py, bootstrap.py, handlers | Enviar comando y consumir confirmacion |
| RegistrarAtencionCancelada.v1 / AtencionCanceladaRegistrada.v1 | No | Integracion con Entrada para cierre compensado | rutas.py, bootstrap.py, handlers | Enviar comando y consumir confirmacion |
| TrabajoCancelado.v1 | No | Estado CANCELADO y evento publico | dominio/entidades.py, esquemas/v1/orquestacion.py, mapeadores_eventos.py | Extender estado y publicar evento |
| Campo id_saga y correlacion de Saga en mensajes nuevos | No | Definicion y propagacion del id_saga | esquemas/v1/, mapeadores_eventos.py | Incluir id_saga y causacion consistente |
| Estados Saga RUNNING/COMPENSATING/COMPLETED/COMPENSATED | No | Maquina de estados de saga | dominio/ y aplicacion/ | Implementar reglas y persistencia de transiciones |
| Idempotencia de nuevos pasos de Saga | Parcial (base existe) | Extender dedupe a nuevos contratos/eventos | inbox/outbox + nuevos handlers | Reusar inbox/outbox/UoW en cada nuevo paso |

## Conclusiones tecnicas

1. La base tecnica para una Saga robusta ya existe: UoW atomica, inbox/outbox, dedupe, ACK posterior a commit y reintentos.
2. El alcance actual es una orquestacion de trabajo-cotizacion, no una Saga multi-paso con compensaciones cruzadas.
3. La mayor brecha de Entrega 5 es funcional de coordinacion y contratos nuevos, mas que de infraestructura.
4. El repositorio esta en una buena posicion para evolucionar sin reescribir su base transversal.

## Riesgos observados para Entrega 5

- Riesgo de dispersion de reglas de Saga si no se centralizan transiciones en un solo proceso de aplicacion.
- Riesgo de inconsistencia en correlacion/causacion si se agregan mensajes sin estandarizar envelope.
- Riesgo de estados huerfanos sin saga log durable para retomar compensaciones tras fallos.

## Recomendacion de prioridad (solo diagnostico)

1. Definir modelo de Saga y tabla de Saga Log.
2. Incorporar contratos de Seguimiento (abrir/cancelar + respuestas).
3. Incorporar contratos de Entrada para registrar atencion habilitada/cancelada.
4. Incorporar contratos de anulacion de Cotizacion.
5. Extender pruebas de idempotencia, compensacion y orden de eventos para los nuevos pasos.
