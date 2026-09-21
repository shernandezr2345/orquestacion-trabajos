# 09 - Implementacion Persistencia Saga

## 1. Alcance implementado

Esta fase implementa unicamente persistencia de Saga para orquestacion-trabajos:

- SagaInstance (dominio + ORM + repositorio).
- SagaLog append-only (dominio + ORM + repositorio).
- Unit of Work SQL para Saga.
- Migracion de base de datos para `saga_instance` y `saga_log`.
- Pruebas automatizadas de persistencia para Saga.
- Ajustes minimos de metadata de migraciones/tests para incluir tablas de Saga.

No se implemento:

- SagaCoordinator.
- handlers de Saga.
- integracion Pulsar/Avro nueva.
- Inbox/Outbox nuevos.
- API nueva para consulta de Saga.
- compensaciones funcionales.

## 2. Estructura de saga_instance

Tabla: `saga_instance`

Campos implementados:

- `id_saga` (PK, string 64, inmutable en dominio).
- `id_solicitud` (UNIQUE + index).
- `id_trabajo` (nullable).
- `estado` (check: RUNNING, COMPENSATING, COMPLETED, COMPENSATED).
- `paso_actual` (string controlado en dominio por enum `SagaStepName`).
- `seguimiento_apertura_solicitada` (bool, default false).
- `seguimiento_abierto_confirmado` (bool, default false).
- `version` (int, default 1, usado para optimistic locking).
- `created_at` (string ISO UTC).
- `updated_at` (string ISO UTC).

Restriccion de consistencia aplicada:

- `seguimiento_abierto_confirmado=true` implica `seguimiento_apertura_solicitada=true`.

## 3. Estructura de saga_log

Tabla: `saga_log`

Campos implementados:

- `log_id` (PK, string 64).
- `id_saga` (FK -> `saga_instance.id_saga`).
- `id_solicitud`.
- `id_trabajo` (nullable).
- `paso`.
- `tipo_registro`.
- `tipo_mensaje` (nullable).
- `event_id` (nullable).
- `command_id` (nullable).
- `causacion` (nullable).
- `estado_anterior` (nullable).
- `estado_nuevo` (nullable).
- `resultado`.
- `detalle` (nullable).
- `created_at`.

Checks aplicados:

- `tipo_registro` solo en: EVENT_RECEIVED, COMMAND_EMITTED, EVENT_EMITTED, LOCAL_OPERATION, STATE_CHANGED, DUPLICATE, LATE, OUT_OF_ORDER, IGNORED.
- `resultado` solo en: APPLIED, NO_OP_DUPLICATE, NO_OP_LATE, NO_OP_OUT_OF_ORDER, REJECTED_CONFLICT.

Append-only:

- El repositorio solo implementa insercion y consultas; no expone update/delete.

## 4. Repositorios creados

### SagaRepository

Archivo: `src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py`

Metodos implementados:

- `crear`
- `obtener_por_id_saga`
- `obtener_por_id_solicitud`
- `actualizar_estado`
- `actualizar_paso`
- `asignar_id_trabajo`
- `marcar_seguimiento_apertura_solicitada`
- `marcar_seguimiento_abierto_confirmado`

Concurrencia:

- optimistic locking con `version` en `UPDATE ... WHERE id_saga=? AND version=?`.
- ante version obsoleta: `SagaConcurrencyConflictError`.

### SagaLogRepository

Archivo: `src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py`

Metodos implementados:

- `registrar`
- `listar_por_saga` (orden cronologico por `created_at`, `log_id`).
- `obtener_ultimo_por_saga`
- `buscar_por_message_id` (por `event_id` o `command_id`).

## 5. Unit of Work implementado/adaptado

Archivo: `src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py`

Implementacion:

- `UnidadTrabajoSagasSQL` reutiliza `UnidadTrabajoSQL` del seedwork.
- Expone repositorios `sagas` y `saga_logs` en la misma transaccion.
- Incluye restricciones reintentables:
  - `uq_saga_instance_id_solicitud`
  - `uq_saga_log_idempotencia`

Esto deja preparada la frontera transaccional para futuras operaciones junto con outbox.

## 6. Migraciones

### Nueva revision

- `migraciones/versions/0002_saga_persistencia.py`
- `down_revision = "0001"`

### Objetos creados

- Tabla `saga_instance`.
- Tabla `saga_log`.

### PK/FK/UNIQUE/indices

`saga_instance`:

- PK: `id_saga`
- UNIQUE: `uq_saga_instance_id_solicitud` en `id_solicitud`
- indices: `ix_saga_instance_id_solicitud`, `ix_saga_instance_estado`

`saga_log`:

- PK: `log_id`
- FK: `id_saga` -> `saga_instance.id_saga` (RESTRICT)
- indices: `ix_saga_log_saga_created` (`id_saga`, `created_at`), `ix_saga_log_solicitud_created` (`id_solicitud`, `created_at`)
- indice unico idempotencia: `uq_saga_log_idempotencia` sobre (`id_saga`, `tipo_mensaje`, `coalesce(event_id, command_id)`)

## 7. Estrategia de concurrencia

Estrategia implementada en esta fase:

- optimistic locking con campo `version` en SagaInstance.
- el repositorio registra version cargada y valida version esperada al actualizar.

Nota:

- El diseno menciona `SELECT FOR UPDATE` como opcion; esta fase implementa el componente optimista para persistencia base.
- El uso explicito de locks pesimistas puede incorporarse en la fase del coordinador si el flujo lo exige.

## 8. Estrategia de idempotencia preparada

Persistencia preparada para la llave logica:

- `id_saga + tipo_mensaje + message_id`
- `message_id = coalesce(event_id, command_id)`

Implementado con:

- indice unico funcional `uq_saga_log_idempotencia`.
- metodo de busqueda `buscar_por_message_id`.

No se implemento Inbox nuevo en esta fase.

## 9. Tests ejecutados

Archivo nuevo de pruebas:

- `tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py`

Pruebas incluidas:

1. creacion inicial con `id_trabajo=NULL`, estado RUNNING y banderas false.
2. asignacion posterior de `id_trabajo`.
3. `seguimiento_apertura_solicitada=true` sin auto-confirmar apertura.
4. `seguimiento_abierto_confirmado=true` respetando implicacion de consistencia.
5. registro `EVENT_RECEIVED`.
6. registro `COMMAND_EMITTED`.
7. registro `STATE_CHANGED` RUNNING -> COMPENSATING.
8. recuperacion cronologica de logs.
9. verificacion de UNIQUE `id_solicitud`.
10. validacion append-only desde el repositorio.
11. conflicto de concurrencia por version.
12. busqueda por `id_saga` e `id_solicitud`.
13. busqueda por `message_id`.
14. confirmacion atomica en UoW de Saga + SagaLog.

Configuracion minima de test:

- Si `ORQUESTACION_DATABASE_URL` existe, usa esa base.
- Si no existe, fallback a SQLite en memoria (StaticPool) solo para estas pruebas nuevas.

## 10. Resultado de tests y validaciones

Comandos ejecutados y resultado:

1. `uv run --locked pytest tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py -q`
- Resultado: `14 passed`.

2. `uv run --locked pytest tests/unitarias/aplicacion/test_trabajos_aplicacion.py -q`
- Resultado: `11 passed`.

3. `uv run --locked ruff check src/orquestacion_trabajos/modulos/sagas tests/unitarias/infraestructura/sagas migraciones/env.py migraciones/versions/0002_saga_persistencia.py tests/test_migraciones.py`
- Resultado: `All checks passed`.

4. `uv run --locked mypy src/orquestacion_trabajos/modulos/sagas tests/unitarias/infraestructura/sagas`
- Resultado: sin errores (salida vacia).

5. `uv run --locked alembic upgrade head --sql`
- Primera ejecucion: falla por variable de entorno ausente `ORQUESTACION_DATABASE_URL`.
- Reintento con variable temporal SQLite: SQL de migraciones 0001 y 0002 generado correctamente.

## 11. Archivos creados

- `src/orquestacion_trabajos/modulos/sagas/__init__.py`
- `src/orquestacion_trabajos/modulos/sagas/dominio/__init__.py`
- `src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py`
- `src/orquestacion_trabajos/modulos/sagas/dominio/repositorios.py`
- `src/orquestacion_trabajos/modulos/sagas/infraestructura/__init__.py`
- `src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py`
- `src/orquestacion_trabajos/modulos/sagas/infraestructura/mapeadores.py`
- `src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py`
- `src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py`
- `migraciones/versions/0002_saga_persistencia.py`
- `tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py`

## 12. Archivos modificados

- `migraciones/env.py`
- `tests/test_migraciones.py`

## 13. Correcciones Fase 1.1

Se aplicaron unicamente correcciones menores sobre pruebas y validacion, sin redisenar Saga.

### 13.1 Rollback atomico probado

- Se agrego prueba explicita de rollback atomico para SagaInstance + SagaLog:
  - `test_15_uow_rollback_atomico_revierte_saga_y_log`
  - Archivo: `tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py`
- Escenario probado:
  1. crear saga inicial,
  2. abrir `UnidadTrabajoSagasSQL`,
  3. modificar saga,
  4. registrar log,
  5. lanzar error antes de commit,
  6. verificar en nueva sesion que ni la mutacion ni el log quedaron persistidos.

### 13.2 Idempotencia probada en los cuatro escenarios

Se agregaron pruebas que documentan comportamiento actual de:

`id_saga + tipo_mensaje + coalesce(event_id, command_id)`

- Caso A (`event_id=E1`, `command_id=NULL`): `test_16_idempotencia_caso_a_event_id_y_command_id_null`.
- Caso B (`event_id=NULL`, `command_id=C1`): `test_17_idempotencia_caso_b_command_id_y_event_id_null`.
- Caso C (`event_id=E1`, `command_id=C1`): `test_18_idempotencia_caso_c_coalesce_prioriza_event_id`.
- Caso D (`event_id=NULL`, `command_id=NULL`): `test_19_idempotencia_caso_d_ambos_ids_null_no_participa_indice_parcial`.

### 13.3 Migracion test corregido

- Se corrigio expectativa desactualizada en:
  - `tests/test_migraciones.py`
- Cambio:
  - `SELECT version_num FROM alembic_version` ahora espera `0002` despues de `alembic upgrade head`.

### 13.4 Validacion PostgreSQL

- PostgreSQL estuvo disponible para esta ejecucion.
- Validaciones ejecutadas sobre PostgreSQL:
  - pruebas Saga persistencia,
  - pruebas de migraciones.

### 13.5 Archivos modificados

- `src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py`
- `tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py`
- `tests/test_migraciones.py`
- `docs/entrega-5/09-implementacion-persistencia-saga.md`

### 13.6 Archivos nuevos

- Ninguno en esta Fase 1.1.

### 13.7 Tests ejecutados y resultados

1. `uv run --locked pytest tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py -q`
  - Resultado (SQLite fallback): `19 passed`.
2. `uv run --locked pytest tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py -q`
  - Resultado (PostgreSQL): `19 passed`.
3. `uv run --locked pytest tests/test_migraciones.py -q`
  - Resultado (PostgreSQL): `3 passed`.
4. `uv run --locked pytest tests/unitarias/aplicacion/test_trabajos_aplicacion.py -q`
  - Resultado (PostgreSQL env): `11 passed`.
5. `uv run --locked ruff check tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py tests/test_migraciones.py src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py`
  - Resultado: `All checks passed`.
6. `uv run --locked mypy src/orquestacion_trabajos/modulos/sagas tests/unitarias/infraestructura/sagas`
  - Resultado: `Success: no issues found`.
7. `uv run --locked alembic upgrade head --sql`
  - Resultado: SQL de revisiones `0001` y `0002` generado correctamente (validacion no destructiva).

### 13.8 Veredicto Fase 1.1

APROBADA PARA FASE 2

## 14. Pendientes para FASE 2

1. Implementar SagaCoordinator y handlers de aplicacion de Saga.
2. Integrar persistencia Saga con el flujo real de eventos/comandos.
3. Definir y aplicar politica final para el caso `CotizacionRechazada` (pendiente del diseno).
4. Confirmar catalogo final cerrado de `paso_actual` si el equipo decide ajustes.
5. Integrar persistencia Saga con outbox/inbox en el flujo de coordinacion completo (sin redisenar tablas actuales).
6. Agregar pruebas de integracion E2E con mensajeria y compensaciones, fuera del alcance de Fase 1.
