# Re-auditoría Técnica Fase 3.1

## 1. Alcance

Se realizo re-auditoria tecnica sobre Fase 3.1 del Saga Coordinator en Orquestacion de Trabajos, comparando:

- diseno y objetivos de fase,
- hallazgos de la revision previa,
- correcciones reportadas,
- codigo actual,
- resultados de pruebas y calidad.

Documentos revisados:

- [docs/entrega-5/13-diseno-tecnico-saga-coordinator.md](docs/entrega-5/13-diseno-tecnico-saga-coordinator.md)
- [docs/entrega-5/14-implementacion-fase-3-saga-coordinator.md](docs/entrega-5/14-implementacion-fase-3-saga-coordinator.md)
- [docs/entrega-5/15-revision-tecnica-precommit-fase-3.md](docs/entrega-5/15-revision-tecnica-precommit-fase-3.md)
- [docs/entrega-5/16-correccion-fase-3-1.md](docs/entrega-5/16-correccion-fase-3-1.md)

Codigo auditado principal:

- [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py)
- [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py)
- [src/orquestacion_trabajos/modulos/trabajos/infraestructura/consumidores.py](src/orquestacion_trabajos/modulos/trabajos/infraestructura/consumidores.py)
- [src/orquestacion_trabajos/config/rutas.py](src/orquestacion_trabajos/config/rutas.py)
- [src/orquestacion_trabajos/config/bootstrap.py](src/orquestacion_trabajos/config/bootstrap.py)

## 2. Hallazgo #1 — Causación

- Estado anterior:
  - la validacion comparaba contra ultimo command_id por tipo y podia rechazar causalidad historica valida o aceptar sin comando causal real.

- Corrección encontrada:
  - se determina tipo de comando causal esperado por evento.
  - se exige causacion presente.
  - se busca command_id exacto en logs COMMAND_EMITTED de la misma saga.
  - se valida compatibilidad tipo de comando causal.
  - en conflicto, se registra REJECTED_CONFLICT sin ejecutar transicion de negocio.

- Evidencia en código:
  - mapeo evento -> tipo de comando causal esperado: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L556)
  - busqueda por command_id exacto en logs de la saga: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L568)
  - validacion causal estricta (ausente, inexistente, incompatible): [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L584)
  - validacion causal ejecutada antes de EVENT_RECEIVED/APPLIED: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L110)

- Pruebas:
  - causalidad historica valida: [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1136)
  - causacion inexistente: [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1223)
  - causacion incompatible: [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1267)

- Estado: RESUELTO

## 3. Hallazgo #2 — Compensación

- Estado anterior:
  - la compensacion podia cerrar antes de recibir SeguimientoTrabajoCancelado cuando solo existia seguimiento_apertura_solicitada=true.

- Corrección encontrada:
  - regla unica para requerir cancelacion de seguimiento:
    - seguimiento_apertura_solicitada=true, o
    - seguimiento_abierto_confirmado=true, o
    - comando CancelarSeguimientoTrabajo.v1 emitido.
  - cierre a COMPENSATED solo cuando compensaciones requeridas estan confirmadas.

- Evidencia en código:
  - regla de requerimiento de cancelacion: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L702)
  - verificacion de compensaciones confirmadas: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L735)
  - cierre condicional y permanencia en COMPENSATING cuando falta confirmacion: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L763)

- Pruebas:
  - apertura solicitada + atencion cancelada mantiene COMPENSATING hasta seguimiento cancelado: [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1308)
  - confirmacion parcial no cierra: [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L1383)
  - caso con seguimiento y cierre al recibir seguimiento cancelado: [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L999)

- Estado: RESUELTO

## 4. COMMAND_EMITTED

Resultado de re-auditoria: RESUELTO CON RIESGO CONTROLADO.

- Se mantiene un solo tipo de registro COMMAND_EMITTED, pero ahora con detalle explicito para separar:
  - comando persistido en outbox,
  - comando solo decidido por coordinator para contrato externo pendiente.

Evidencia:

- etiqueta outbox real: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L41)
- uso en comando tomado desde outbox: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L264)
- etiqueta de contrato pendiente: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L653)
- etiqueta de evento pendiente: [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L698)

Conclusion:

- SagaLog no afirma falsamente que todo comando fue publicado.
- La distincion esta explicitada por detalle y es auditable.

## 5. Wiring

Resultado de re-auditoria: PARCIALMENTE IMPLEMENTADO POR ALCANCE CONTRACTUAL.

Estado real de entrada conectado:

- fuentes activas: entrada, cotizacion registrada, cotizacion rechazada.
  - [src/orquestacion_trabajos/config/rutas.py](src/orquestacion_trabajos/config/rutas.py#L12)

Estado real de salida conectado:

- destinos con outbox/publicacion: TrabajoCreado.v1 y SolicitarCotizacion.v1.
  - [src/orquestacion_trabajos/config/rutas.py](src/orquestacion_trabajos/config/rutas.py#L29)
  - [src/orquestacion_trabajos/config/bootstrap.py](src/orquestacion_trabajos/config/bootstrap.py#L129)

Conclusión:

- eventos de Fase 3 asociados a contratos externos no congelados siguen como pendiente de wiring runtime real.
- no se detecta invento de topics.

## 6. Idempotencia

Resultado de re-auditoria: OK.

Evidencia:

- dedupe por id_saga + tipo_mensaje + coalesce(event_id, command_id):
  - [src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L63)
- busqueda por message_id en coordinator/repo:
  - [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L168)
  - [src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L145)
- pruebas de duplicate:
  - [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L390)

## 7. Late / Out of Order

Resultado de re-auditoria: OK.

Evidencia:

- corte por estado terminal (late): [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L84)
- corte por paso no habilitado (out of order): [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L96)
- pruebas de late y out_of_order:
  - [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L412)
  - [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L480)

## 8. Atomicidad

Resultado de re-auditoria: OK.

Evidencia:

- coordinator opera en una unica UoW y confirma al final del procesamiento:
  - [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L60)
  - [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L124)
- UoW hace flush y commit en confirmar, rollback en salida con error:
  - [src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py](src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py#L62)
  - [src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py](src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py#L70)

## 9. Pruebas ejecutadas

Comandos ejecutados:

- pytest tests/unitarias/aplicacion/sagas/test_saga_coordinator.py -q
  - resultado: 26 passed.
- pytest -q
  - resultado: 122 passed, 22 failed, 8 errors.

Clasificacion de fallas en pytest completo:

- Fallas de infraestructura/configuracion:
  - ORQUESTACION_DATABASE_URL ausente (KeyError/None) en migraciones, api y pruebas SQL de infraestructura.
  - no se evidencia regresion especifica del coordinator en la bateria focalizada.

## 10. Ruff / Mypy / diff check

- ruff check .
  - All checks passed.
- mypy .
  - Success: no issues found in 90 source files.
- git diff --check
  - sin hallazgos.

## 11. Hallazgos residuales

- MEDIUM
  - Wiring parcial de eventos Fase 3 hacia runtime real, condicionado por contratos/topics externos no congelados aun.

- LOW
  - La semantica de COMMAND_EMITTED sigue unificada en un solo tipo de log (decision valida de diseno), aunque ya mitigada por detalle explicito.

- INFO
  - Las fallas de pytest completo corresponden a precondicion de entorno (ORQUESTACION_DATABASE_URL), no a defecto funcional probado en coordinator Fase 3.1.

No se identifican hallazgos CRITICAL ni HIGH en el alcance auditado de Fase 3.1.

## 12. Veredicto técnico

APROBADO PARA SIGUIENTE VALIDACIÓN
