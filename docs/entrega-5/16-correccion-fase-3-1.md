# 1. Resumen ejecutivo

Se implementaron las correcciones criticas solicitadas para FASE 3 del Saga Coordinator, sin cambios de contratos Avro, steps, estados, ni topics.

Resultado:

- Corregida la validacion de causacion para enlazar por `command_id` exacto emitido por la saga.
- Corregida la regla de cierre de compensacion para esperar cancelacion de seguimiento cuando aplique por apertura solicitada.
- Ajustada la semantica observacional de `COMMAND_EMITTED` mediante `detalle` explicito para distinguir outbox real vs contrato pendiente.
- Agregada cobertura obligatoria de regresion en pruebas unitarias del coordinator.

# 2. Correcciones aplicadas en coordinator

Archivo modificado:

- [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py)

Cambios clave:

- Validacion de causacion previa a `EVENT_RECEIVED/APPLIED` para evitar doble registro conflictivo con misma identidad de mensaje.
- Inclusión de `flush` antes de leer outbox y registrar `COMMAND_EMITTED` de `SolicitarCotizacion.v1`.
- Nuevas utilidades para resolver causalidad exacta por `command_id`.
- Regla unificada para determinar si se requiere cancelar seguimiento durante compensacion.

Referencias puntuales:

- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L110)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L154)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L556)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L568)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L584)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L702)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L735)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L763)

# 3. Causacion exacta (fix critico 1)

Antes:

- Se validaba contra el ultimo comando emitido por tipo.

Ahora:

- Se exige `envelope.causacion`.
- Se busca el `COMMAND_EMITTED` exacto por `command_id` en el historial de la misma saga.
- Si no existe, se rechaza con `REJECTED_CONFLICT`.
- Si existe pero pertenece a otro tipo de comando, se rechaza con `REJECTED_CONFLICT`.

Impacto funcional:

- Se acepta causalidad historica valida (no solo el ultimo comando del tipo).
- Se evita aceptar mensajes con causacion inexistente o incompatible.

# 4. Cierre de compensacion (fix critico 2)

Antes:

- El cierre esperaba `SeguimientoTrabajoCancelado.v1` solo cuando `seguimiento_abierto_confirmado=true`.

Ahora:

- La necesidad de cancelacion de seguimiento se calcula con regla unica:
  - `seguimiento_apertura_solicitada=true`, o
  - `seguimiento_abierto_confirmado=true`, o
  - existencia de comando `CancelarSeguimientoTrabajo.v1` emitido en logs.
- Con esa regla, la saga no cierra `COMPENSATED` hasta completar confirmaciones requeridas.

Impacto funcional:

- Evita cierre prematuro en escenario requested=true / confirmed=false.

# 5. Semantica COMMAND_EMITTED y wiring

Semantica:

- Se mantuvo un solo tipo de log `COMMAND_EMITTED`, pero con `detalle` diferenciador:
  - outbox real: "Comando persistido en outbox para publicacion".
  - contrato pendiente: "PENDIENTE DE CONTRATO EXTERNO: no publicado en outbox".

Referencia:

- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L41)
- [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L264)

Wiring runtime:

- No se agregaron nuevas fuentes/topics para no inventar contratos no desplegados.
- Se mantiene cableado actual de 3 fuentes y 2 destinos ya existentes.

Referencias:

- [src/orquestacion_trabajos/config/rutas.py](src/orquestacion_trabajos/config/rutas.py#L12)
- [src/orquestacion_trabajos/config/rutas.py](src/orquestacion_trabajos/config/rutas.py#L29)
- [src/orquestacion_trabajos/config/bootstrap.py](src/orquestacion_trabajos/config/bootstrap.py#L73)

# 6. Pruebas agregadas y ajustadas

Archivo modificado:

- [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py)

Nuevas pruebas obligatorias cubiertas:

- causalidad historica valida:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1136)
- causacion sin comando emitido:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1223)
- causacion de tipo de comando incompatible:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1267)
- compensacion espera cancelacion de seguimiento cuando apertura fue solicitada:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1308)
- confirmacion parcial no cierra compensacion:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1383)
- apertura fallida no permite cierre sin cotizacion anulada:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1437)
- cotizacion rechazada no emite anular cotizacion:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1498)

Ajustes necesarios por la nueva regla estricta:

- helper para causalidad real de `SolicitarCotizacion.v1` y happy-path de atencion habilitada con secuencia causal completa.
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L364)
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L775)

# 7. Validaciones ejecutadas

Comandos ejecutados en `orquestacion-trabajos`:

- `pytest tests/unitarias/aplicacion/sagas/test_saga_coordinator.py -q`
  - Resultado: `26 passed`.
- `ruff check .`
  - Resultado: `All checks passed`.
- `mypy .`
  - Resultado: `Success: no issues found in 90 source files`.
- `git diff --check`
  - Resultado: sin hallazgos (sin errores de whitespace/diff).

# 8. Estado final y alcance

Estado final:

- Correcciones criticas de FASE 3 aplicadas y verificadas con pruebas.
- Cobertura obligatoria solicitada incorporada.
- Sin commit ni push, de acuerdo con la instruccion.

Alcance y restricciones respetadas:

- Sin cambios en contratos Avro.
- Sin cambios en nombres de topics.
- Sin cambios en estados/steps de dominio fuera de la logica de cierre requerida.
- Sin cambios de wiring que inventen integraciones no existentes.
