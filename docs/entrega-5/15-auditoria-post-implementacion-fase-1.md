# Auditoria Post-Implementacion FASE 1 (SagaCoordinator)

## A. Hallazgos

1. Saga steps (antes vs despues FASE 1)

- Verificacion en modelo actual: src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py:18-30.
- Verificacion de cambios locales: no hay modificaciones en ese archivo en el worktree de FASE 1 (git diff/status sin cambios para entidades.py).

Estado por paso solicitado:

- CREAR_TRABAJO: ya existia antes de FASE 1.
- SOLICITAR_COTIZACION: ya existia antes de FASE 1.
- ABRIR_SEGUIMIENTO: ya existia antes de FASE 1.
- CANCELAR_TRABAJO_POR_RECHAZO: ya existia antes de FASE 1.
- COMPLETAR_SAGA: ya existia antes de FASE 1.
- FINALIZAR_COMPENSACION: ya existia antes de FASE 1.

Conclusion: ninguno de esos pasos fue creado durante FASE 1; FASE 1 los consumo en runtime desde el coordinator.

2. CONFLICT (modelo, ORM, repositorio, tests)

- No existe tipo_registro=CONFLICT en el enum de dominio: src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py:33-42.
- No existe CONFLICT en la restriccion ORM de tipo_registro: src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py:53.
- Si existe resultado REJECTED_CONFLICT en enum y ORM:
  - src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py:45-50
  - src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py:57
- En coordinator, el conflicto se registra como EVENT_RECEIVED + REJECTED_CONFLICT:
  - src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py:325-326
- Test que valida conflicto funcional:
  - tests/unitarias/aplicacion/sagas/test_saga_coordinator.py:314
  - tests/unitarias/aplicacion/sagas/test_saga_coordinator.py:348

Por que FASE 1 usa EVENT_RECEIVED + REJECTED_CONFLICT:

- Porque el modelo vigente no permite tipo_registro=CONFLICT, pero si permite representar rechazo por conflicto en resultado.
- Esta decision esta soportada por el esquema actual (enum + check constraints) sin migraciones.

Que implicaria agregar CONFLICT formalmente:

- Agregar valor CONFLICT en SagaLogTipoRegistro (dominio).
- Ajustar check constraint ck_saga_log_tipo_registro en ORM/DB.
- Crear migracion Alembic para la nueva restriccion en base de datos.
- Ajustar mapper/tests y probablemente consultas/reportes que asumen catalogo actual de tipos.

3. Idempotencia

- El lookup de duplicados se decide por message_id consultando ambos campos:
  - src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py:145-156
  - condicion: event_id == message_id OR command_id == message_id
- El indice de idempotencia se define por coalesce(event_id, command_id):
  - src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py:63-68
- En coordinator, la deduplicacion se ejecuta antes de transicion:
  - src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py:65
  - src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py:153-160
- Solo algunos tipos de log guardan event_id/command_id (EVENT_RECEIVED, COMMAND_EMITTED, EVENT_EMITTED):
  - src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py:361-366

Confirmacion solicitada:

- Si: event_id/command_id se usa para deduplicacion.
- Si: la deduplicacion funciona aunque no todos los tipos de SagaLog guarden esos IDs, porque la identidad de mensaje persiste en los tipos usados para identidad (principalmente EVENT_RECEIVED).

4. Resolucion de saga (codigo y tests)

Codigo:

- Busqueda por id_saga: coordinator.py:121-122.
- Fallback por id_solicitud: coordinator.py:135.
- Caso conflicto cuando ambos no corresponden: el flujo retorna la saga resuelta por id_saga y luego _validar_consistencia rechaza inconsistencias (id_solicitud/correlacion/id_trabajo): coordinator.py:126-133 y 181-186.
- Comportamiento cuando faltan ambos: retorna None inmediatamente: coordinator.py:118-119.

Cobertura de tests explicitos:

- Busqueda por id_saga: cobertura parcial/indirecta (casos construyen envelope con id_saga en conflicto/out_of_order), no hay prueba dedicada de ruta exitosa solo-por-id_saga.
- Fallback por id_solicitud: si hay cobertura explicita e indirecta en el happy path y otros flujos que no envian id_saga:
  - test_happy_path... (linea 175)
  - test_idempotencia... (linea 197)
  - test_cotizacion_registrada... (linea 395)
  - test_cotizacion_rechazada... (linea 421)
- Conflicto cuando ambos no corresponden: si hay test explicito de inconsistencia (linea 314).
- Faltan ambos: no existe test explicito.

5. AtencionHabilitada / AtencionCancelada

- Aparecen porque el coordinator ya contempla esos contratos en validacion de paso y en transicion:
  - Mapeo de paso esperado: coordinator.py:171-172
  - Transicion a COMPLETED/COMPLETAR_SAGA: coordinator.py:279-287
  - Transicion a COMPENSATED/FINALIZAR_COMPENSACION: coordinator.py:292-300

Confirmacion de origen de pasos:

- COMPLETAR_SAGA y FINALIZAR_COMPENSACION ya existian previamente en SagaStepName (entidades.py:23 y 30).
- FASE 1 no los introdujo en el enum; FASE 1 los activo en el runtime del coordinator.

## B. Cambios de diseno introducidos por FASE 1

1. Se introdujo un SagaCoordinator transaccional con resolucion de saga, clasificacion de mensajes y aplicacion de transiciones.
2. Se introdujo SagaMessageEnvelope como contrato interno de procesamiento.
3. Se incorporo una UoW combinada saga+trabajos para atomicidad saga/trabajo/inbox/outbox/log.
4. Se habilito ejecucion de handlers de trabajo dentro de una UoW externa (sin romper uso previo standalone).
5. Se inyecto el coordinator en pipeline real (bootstrap + consumidor) con fallback compatible.
6. Se establecio estrategia de identidad de mensaje en logs solo para tipos que representan identidad (evitando colisiones de indice de idempotencia).

## C. Cambios que respetan la matriz

1. SolicitudDePartnerListaParaAtencion.v1: crea/reusa trabajo y deja comando de SolicitarCotizacion.
2. CotizacionRegistrada.v1: aplica resultado y avanza a ABRIR_SEGUIMIENTO (comando siguiente pendiente por contrato).
3. CotizacionRechazada.v1: aplica rechazo y avanza a CANCELAR_TRABAJO_POR_RECHAZO (decision final pendiente).
4. Duplicados, tardios y fuera de orden se tratan como no-op con clasificacion explicita.
5. Conflictos de consistencia se rechazan como REJECTED_CONFLICT manteniendo compatibilidad con modelo vigente.

## D. Cambios que requieren aprobacion

1. Introducir tipo_registro=CONFLICT formal (requiere cambios de enum, constraint y migracion).
2. Definir comportamiento final contractual para la rama CotizacionRechazada (estado terminal y/o compensaciones).
3. Implementar pasos post-cotizacion pendientes por contrato (abrir/cancelar seguimiento y sus comandos/eventos).
4. Si se desea, formalizar regla de resolucion cuando llega id_saga valido con id_solicitud inconsistente (actualmente se resuelve por id_saga y luego valida conflicto).

## E. Tests faltantes

1. Caso explicito: resolver saga solo por id_saga en ruta exitosa (sin id_solicitud).
2. Caso explicito: mensaje sin id_saga e id_solicitud (actualmente retorna None; falta asercion de comportamiento esperado de logging/no-op).
3. Caso explicito: ambos ids presentes pero apuntando a dos sagas existentes distintas (conflicto de correspondencia cruzada).
4. Casos felices de AtencionHabilitadaRegistrada.v1 y AtencionCanceladaRegistrada.v1 en paso habilitado (hoy hay cobertura de out-of-order, no de exito completo).
5. Caso de idempotencia para eventos de atencion (misma message_id repetida).
