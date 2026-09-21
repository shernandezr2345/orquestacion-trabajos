# Entrega 5 - Implementacion FASE 3 SagaCoordinator

## 1. Objetivo

Implementar la FASE 3 del SagaCoordinator en orquestacion-trabajos, cerrando la ruta de compensacion aprobada para:

- CotizacionRechazada.v1
- AperturaSeguimientoFallida.v1

Restricciones aplicadas durante toda la implementacion:

- No se crearon estados nuevos.
- No se modifico SagaStatus.
- No se crearon SagaStepName nuevos.
- No se inventaron contratos.
- No se agregaron topics nuevos.
- No se implemento AnularCotizacion en la rama CotizacionRechazada.

## 2. Alcance implementado

Se implemento logica de coordinator para:

- Validacion de causacion contra comandos emitidos previamente.
- Emision trazable de comandos/eventos pendientes de contrato externo (solo en SagaLog, sin publicacion real en outbox para contratos no congelados).
- Flujo CotizacionRechazada con transicion RUNNING -> COMPENSATING.
- Flujo AperturaSeguimientoFallida con AnularCotizacion y continuidad de compensaciones.
- Cierre de compensacion centralizado con confirmaciones reales de eventos.

## 3. Archivos impactados

### Modificados

- src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py
- tests/unitarias/aplicacion/sagas/test_saga_coordinator.py
- src/orquestacion_trabajos/modulos/trabajos/infraestructura/consumidores.py

### Creados

- docs/entrega-5/14-implementacion-fase-3-saga-coordinator.md

## 4. Flujo de negocio implementado

### 4.1 Rama CotizacionRechazada.v1

Comportamiento final:

1. Valida causacion respecto al ultimo SolicitarCotizacion.v1.
2. Aplica resultado de cotizacion sobre trabajo.
3. Cambia estado a COMPENSATING.
4. Registra cancelacion local de trabajo.
5. Registra evento pendiente TrabajoCancelado.v1 (sin outbox real).
6. Emite comando pendiente RegistrarAtencionCancelada.v1.
7. Si hay seguimiento solicitado/abierto, emite CancelarSeguimientoTrabajo.v1 y espera confirmacion.
8. Cierra en COMPENSATED solo cuando se cumplen confirmaciones requeridas.

Nota clave de restriccion:

- En esta rama no se emite AnularCotizacion.v1.

### 4.2 Rama AperturaSeguimientoFallida.v1

Comportamiento final:

1. Valida causacion respecto a AbrirSeguimientoTrabajo.v1.
2. Cambia estado a COMPENSATING.
3. Emite AnularCotizacion.v1 (pendiente de contrato externo).
4. Al recibir CotizacionAnulada.v1:
   - registra cancelacion local de trabajo,
   - registra TrabajoCancelado.v1 (pendiente),
   - emite RegistrarAtencionCancelada.v1,
   - si corresponde, emite CancelarSeguimientoTrabajo.v1,
   - evalua cierre de compensacion.

## 5. Reglas tecnicas de coordinator

### 5.1 Gate de pasos habilitados

Se ampliaron reglas para aceptar de forma controlada:

- SeguimientoTrabajoAbierto.v1
- AperturaSeguimientoFallida.v1
- CotizacionAnulada.v1
- SeguimientoTrabajoCancelado.v1

Y se flexibilizo AtencionCanceladaRegistrada.v1 para pasos de compensacion esperados.

### 5.2 Validacion de causacion

Para mensajes dependientes de comando previo, se valida:

- causacion presente
- causacion igual al command_id emitido por saga para el tipo de comando esperado

Si no cumple, se registra conflicto de saga y no se aplican efectos.

### 5.3 Cierre de compensacion

Se centralizo en dos metodos:

- _compensaciones_confirmadas
- _cerrar_compensacion_si_corresponde

Criterios de cierre:

- existe cancelacion local de trabajo,
- existe AtencionCanceladaRegistrada.v1 aplicado,
- si hubo seguimiento abierto confirmado, existe SeguimientoTrabajoCancelado.v1 aplicado.

## 6. Idempotencia, orden y conflictos

Se preserva la semantica ya existente:

- DUPLICATE -> NO_OP_DUPLICATE
- LATE -> NO_OP_LATE
- OUT_OF_ORDER -> NO_OP_OUT_OF_ORDER
- Inconsistencias de ids/causacion -> REJECTED_CONFLICT

No se relajaron reglas previas, solo se ampliaron casos validos para FASE 3.

## 7. Pruebas unitarias agregadas/ajustadas

Archivo:

- tests/unitarias/aplicacion/sagas/test_saga_coordinator.py

Cobertura relevante de FASE 3:

- test_happy_path_atencion_cancelada_y_idempotencia
- test_cotizacion_registrada_emite_abrir_seguimiento_pendiente_contrato
- test_seguimiento_abierto_emite_registrar_atencion_habilitada
- test_cotizacion_rechazada_con_seguimiento_abierto_espera_confirmaciones
- test_apertura_fallida_emite_anular_y_cotizacion_anulada_continua_compensacion

## 8. Resultados de validacion

Comandos ejecutados en este cierre:

- python -m pytest tests/unitarias/aplicacion/sagas/test_saga_coordinator.py -q
- python -m ruff check .
- python -m mypy .
- git diff --check

Resultados observados:

- Saga coordinator tests: 19 passed.
- Ruff: sin errores luego de ordenar imports en consumidores.py.
- Mypy: success, sin issues.
- git diff --check: limpio.

Nota sobre pytest completo del repositorio:

- Persisten fallos de entorno por ORQUESTACION_DATABASE_URL ausente en pruebas que requieren PostgreSQL/migraciones.
- Es un prerrequisito de infraestructura, no una regresion funcional de los cambios de saga.

## 9. Riesgos y brechas abiertas

- Los contratos marcados como pendientes externos siguen sin Avro/topic congelado en esta entrega, por diseno y restriccion acordada.
- El coordinator registra trazabilidad de esos comandos/eventos, pero no hace publicacion real outbox para dichos contratos no congelados.
- La validacion integral E2E multi-servicio requiere ambiente con DB y mensajeria completos.

## 10. Confirmaciones explicitas

Se confirma que en esta implementacion:

- No se crearon estados nuevos.
- No se modifico SagaStatus.
- No se crearon SagaStepName nuevos.
- No se inventaron contratos.
- No se agregaron topics nuevos.
- No se implemento AnularCotizacion en la rama CotizacionRechazada.
- Se implemento RUNNING -> COMPENSATING -> COMPENSATED para la ruta CotizacionRechazada con confirmaciones.
- Se implemento AperturaSeguimientoFallida con compensacion via AnularCotizacion/CotizacionAnulada y continuidad de cadena de compensacion.
