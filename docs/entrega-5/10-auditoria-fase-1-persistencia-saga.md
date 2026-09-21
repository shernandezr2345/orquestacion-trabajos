# AUDITORÍA FASE 1

## 1. Correcto
- La separación Domain -> Ports -> Infrastructure está implementada correctamente en [src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py), [src/orquestacion_trabajos/modulos/sagas/dominio/repositorios.py](src/orquestacion_trabajos/modulos/sagas/dominio/repositorios.py), [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py) y [src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py).
- El dominio de Saga no depende de SQLAlchemy, PostgreSQL ni Session; usa clases de dominio y puertos en [src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py) y [src/orquestacion_trabajos/modulos/sagas/dominio/repositorios.py](src/orquestacion_trabajos/modulos/sagas/dominio/repositorios.py).
- SagaInstance implementa los campos requeridos por diseño y estados restringidos a RUNNING, COMPENSATING, COMPLETED, COMPENSATED en [src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py#L11).
- SagaLog implementa los campos definidos y tipos de registro/resultados restringidos por checks en [src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L47).
- La relación 1:N SagaInstance -> SagaLog por id_saga está implementada con FK RESTRICT en [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py#L67) y ORM en [src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L72).
- Concurrencia optimista está implementada con version y condición en UPDATE WHERE version esperada en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L85).
- Detección de conflicto de concurrencia y excepción dedicada está implementada en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L24) y validada por [tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py](tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py#L347).
- Regla de banderas seguimiento_abierto_confirmado => seguimiento_apertura_solicitada está protegida en dominio por validación y autoajuste en [src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py#L111) y en base de datos por check constraint en [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py#L40).
- UnidadTrabajoSagasSQL reutiliza la frontera transaccional existente y crea ambos repositorios sobre la misma sesión en [src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py#L25).
- La migración 0002 incluye PK, FK, UNIQUE, índices, checks, nullability y defaults para saga_instance y saga_log en [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py).

## 2. Observaciones
- A. Fechas: created_at y updated_at son String(64), no timestamp real, tanto en Saga como en el patrón preexistente del proyecto.
- Evidencia Saga: [src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L31) y [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py#L29).
- Evidencia patrón existente: Trabajo usa String(64) para creado_en en [src/orquestacion_trabajos/modulos/trabajos/infraestructura/orm.py](src/orquestacion_trabajos/modulos/trabajos/infraestructura/orm.py#L27) e Inbox/Outbox usan String en [src/orquestacion_trabajos/seedwork/infraestructura/orm.py](src/orquestacion_trabajos/seedwork/infraestructura/orm.py#L20).
- Conclusión A: es consistente con el proyecto actual, pero semánticamente no es timestamp nativo de base de datos.
- B. Idempotencia: uq_saga_log_idempotencia usa columnas id_saga + tipo_mensaje + coalesce(event_id, command_id), con filtro parcial event_id IS NOT NULL OR command_id IS NOT NULL, en [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py#L85) y [src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L60).
- Comportamiento B cuando event_id existe y command_id null: message_id efectivo es event_id.
- Comportamiento B cuando command_id existe y event_id null: message_id efectivo es command_id.
- Comportamiento B cuando ambos existen: coalesce toma event_id y command_id queda fuera de la clave única.
- Comportamiento B cuando ambos son null: la fila queda fuera del índice único parcial y puede repetirse.
- Comportamiento B con tipo_mensaje null: al estar nullable, debilita la unicidad práctica para esa dimensión.
- Conclusión B: coincide parcialmente con id_saga + tipo_mensaje + message_id; hay ambigüedad operativa cuando ambos IDs existen y no hay cobertura específica en tests.
- C. Consistencia de banderas:
- Dominio: validación explícita y autoajuste en [src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py#L111).
- Aplicación: no existe capa de aplicación Saga implementada todavía (esperado en Fase 1).
- Persistencia/repo: utiliza métodos de dominio para mutaciones en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L72).
- Base de datos: check constraint en [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py#L40).
- D. Optimistic locking:
- Lectura de version: obtener_por_id_saga y obtener_por_id_solicitud guardan _loaded_versions en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L46).
- Incremento de version: _marcar_mutacion en dominio incrementa version en [src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py#L107).
- Update con control de version: UPDATE WHERE id_saga y version esperada en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L85).
- Detección de conflicto: si returning no devuelve fila, lanza SagaConcurrencyConflictError en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L105).
- Test de evidencia: [tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py](tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py#L347).
- E. Append-only:
- El repositorio de SagaLog solo expone registrar/listar/obtener_ultimo/buscar_por_message_id en [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L111).
- No existen métodos update/delete en ese repositorio.
- Riesgo E: no hay protección de base de datos para impedir updates/deletes directos fuera del repositorio.
- F. Transacción:
- UnidadTrabajoSagasSQL usa una sola sesión para sagas y saga_logs en [src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py#L25).
- UnidadTrabajoSQL abre transacción con begin, confirma con flush+commit y hace rollback en exit en [src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py](src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py#L30).
- Ante rollback, se revierten SagaInstance y SagaLog en la misma transacción por compartir sesión.
- Cobertura F: hay test de commit atómico en [tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py](tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py#L419), pero no hay test explícito de rollback atómico en Saga.
- G. Arquitectura:
- Se respeta el patrón; no se observaron dependencias SQL en dominio.
- H. Migración:
- PK/FK/UNIQUE/índices/checks/nullability/defaults/restrict/downgrade están presentes en [migraciones/versions/0002_saga_persistencia.py](migraciones/versions/0002_saga_persistencia.py).
- Orden correcto: crea saga_instance antes de saga_log y en downgrade elimina saga_log antes de saga_instance.
- Observación H relevante: created_at y updated_at son NOT NULL sin server default en migración (la generación de valor queda en la aplicación/ORM).
- I. Tests de persistencia:
- Los 14 tests usan DB real vía SQLAlchemy y tablas reales creadas por metadata; no usan mocks del repositorio.
- Cobertura superficial I1: test append-only valida ausencia de métodos, no imposibilidad de update/delete a nivel DB.
- Cobertura superficial I2: estrategia de idempotencia no prueba caso ambos IDs presentes ni ambos null.
- Cobertura superficial I3: no hay test de rollback atómico para Saga UoW.
- Cobertura superficial I4: al tener fallback SQLite en [tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py](tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py#L32), algunos comportamientos PostgreSQL específicos pueden no validarse siempre.
- Observación adicional: en [tests/test_migraciones.py](tests/test_migraciones.py#L58) se espera version_num igual a 0001 después de migrar a head, lo cual entra en tensión con la existencia de la revisión 0002.

## 3. Fuera de alcance
- No se encontró implementación accidental de SagaCoordinator.
- No se encontraron handlers de Saga nuevos.
- No se encontraron cambios funcionales nuevos en Pulsar o Avro para Saga.
- No se implementó Inbox nuevo para Saga.
- No se implementó Outbox nuevo para Saga.
- No se implementó BFF.
- No se implementaron compensaciones funcionales completas.
- Cambios detectados fuera del núcleo Saga pero justificables para Fase 1:
- Ajuste de metadata en [migraciones/env.py](migraciones/env.py) para registrar tablas Saga en Alembic.
- Ajuste de prueba de migraciones en [tests/test_migraciones.py](tests/test_migraciones.py).

## 4. Riesgos antes de Fase 2
- Riesgo 1: semántica de idempotencia incompleta cuando event_id y command_id vienen ambos informados; coalesce prioriza event_id y puede ocultar diferencias por command_id.
- Riesgo 2: filas de SagaLog con event_id y command_id null quedan fuera del índice único de idempotencia; si se usan para casos deduplicables, podrían duplicarse.
- Riesgo 3: append-only no está blindado en base de datos; un acceso directo podría modificar historia.
- Riesgo 4: pruebas de Saga pueden correr en SQLite por fallback, dejando sin verificar diferencias PostgreSQL específicas del índice funcional/parcial.
- Riesgo 5: expectativa de versión en migraciones test (0001 en head) puede romper validación de pipeline al ejecutar con PostgreSQL real.

## 5. Veredicto
APROBADA CON CORRECCIONES MENORES
