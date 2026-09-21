# 1. Resumen ejecutivo

Se realizo revision tecnica pre-commit de FASE 3 sobre coordinator, consumidores, persistencia, tests y documentos de diseno/contratos.

Resultado global:

- Hay avances correctos en estructura de SagaCoordinator, idempotencia base, manejo LATE/OUT_OF_ORDER, y atomicidad transaccional.
- Se detectan 2 problemas bloqueantes de logica funcional:
  - Validacion de causacion acoplada al ultimo comando del tipo, no al comando causal exacto.
  - Cierre de compensaciones no exige cancelacion de seguimiento cuando solo existe seguimiento_apertura_solicitada=true.
- Se detecta 1 riesgo semantico relevante:
  - COMMAND_EMITTED se usa con dos significados (emitido y persistido en outbox vs emitido solo como intencion en SagaLog).

Veredicto: NO APROBADO PARA COMMIT.

# 2. Revision COMMAND_EMITTED

Resultado: RIESGO

Evidencia:

- Para contratos con outbox real, COMMAND_EMITTED se registra despues de leer payload en outbox:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L232)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L250)
  - [unidad_trabajo.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py#L99)
  - [unidad_trabajo.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py#L104)
- Para contratos pendientes, COMMAND_EMITTED se registra sin outbox, con detalle explicito "PENDIENTE DE CONTRATO EXTERNO: no publicado en outbox":
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L623)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L665)
- SagaLog soporta COMMAND_EMITTED como tipo de registro, sin obligar correspondencia con outbox:
  - [entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py#L35)
  - [orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L53)

Conclusion:

Actualmente COMMAND_EMITTED significa "comando decidido/emitido por el coordinator" y no necesariamente "persistido en outbox listo para publicacion". Es consistente con la implementacion actual, pero introduce ambiguedad semantica operacional.

# 3. Revision causacion

Resultado: ERROR

Evidencia:

- La validacion toma solo el ultimo command_id emitido por tipo de comando:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L588)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L601)
- Si no existe comando previo compatible, retorna sin conflicto:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L611)
- Conflicto se dispara solo cuando hay esperado y causacion ausente o distinta:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L613)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L617)

Analisis por casos solicitados:

- Caso A (CMD-001 y causacion CMD-001): acepta solo si CMD-001 sigue siendo el ultimo del tipo.
- Caso B (CMD-001 luego CMD-002 y llega evento con causacion CMD-001): lo rechaza por esperar CMD-002, aunque la causacion sea valida historicamente.
- Caso C (causacion CMD-999): lo rechaza (correcto cuando existe esperado).
- Caso D (no existe comando previo): no rechaza, deja pasar (incorrecto para regla solicitada).

Conclusion:

La implementacion valida contra "ultimo comando por tipo" y no contra "comando causal exacto". Esto puede producir falsos conflictos y falsos positivos de aceptacion.

# 4. Revision seguimiento solicitado/confirmado

Resultado: ERROR

Evidencia:

- Emision de cancelacion de seguimiento en compensacion usa solicitada OR confirmada:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L320)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L410)
- Cierre de compensacion exige seguimiento cancelado solo cuando confirmado=true:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L745)
- Invariante de dominio (confirmed implica requested) esta bien modelado:
  - [entidades.py](src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py#L112)
  - [orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L20)

Conclusion:

Hay inconsistencia: se emite CancelarSeguimientoTrabajo cuando requested=true, pero el cierre no espera confirmacion de cancelacion salvo confirmed=true. Esto habilita cierre prematuro en requested=true/confirmed=false.

# 5. Revision cierre de compensaciones

Resultado: ERROR

Evidencia:

- Logica central de cierre:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L729)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L757)
- Criterios actuales: trabajo cancelado local + atencion cancelada + seguimiento cancelado solo si confirmado.

Evaluacion casos:

- Caso A (CotizacionRechazada sin seguimiento): correcto.
- Caso B (CotizacionRechazada con seguimiento abierto confirmado): correcto.
- Caso C (AperturaSeguimientoFallida): riesgo de cierre prematuro cuando requested=true y confirmed=false, pese a haberse emitido cancelacion de seguimiento.

Conclusion:

La regla implementada no refleja completamente "compensaciones requeridas"; refleja "confirmaciones minimas segun seguimiento_abierto_confirmado".

# 6. Revision CotizacionRechazada

Resultado: ERROR

Evidencia:

- No emite AnularCotizacion en esta rama (correcto):
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L254)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L290)
- Cambia a COMPENSATING y registra cancelacion local:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L289)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L304)
- Emite RegistrarAtencionCancelada y CancelarSeguimiento si requested/confirmed:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L314)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L321)

Problema:

- Puede cerrar COMPENSATED sin esperar SeguimientoTrabajoCancelado en escenario requested=true/confirmed=false.

# 7. Revision AperturaSeguimientoFallida

Resultado: ERROR

Evidencia:

- Pasa a COMPENSATING y emite AnularCotizacion:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L360)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L377)
- En CotizacionAnulada ejecuta cadena de compensacion esperada:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L392)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L436)

Problema:

- Misma condicion de cierre prematuro por requested=true/confirmed=false si AtencionCancelada llega antes de confirmacion de cancelacion de seguimiento.

# 8. Idempotencia

Resultado: OK

Evidencia:

- Dedupe por id_saga + tipo_mensaje + (event_id o command_id):
  - [repositorios.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py#L145)
  - [orm.py](src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py#L63)
- Control de duplicados en coordinator:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L68)
- Cobertura de tests de duplicate:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L399)
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L807)

Observacion:

No hay prueba negativa especifica de causacion invalida en eventos nuevos; es un gap de cobertura, no una falla de mecanismo idempotente.

# 9. Late / Out of Order

Resultado: OK

Evidencia:

- Late se evalua antes de transiciones:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L80)
- Out of order se evalua por paso habilitado y corta ejecucion:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L93)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L168)
- Tests cubren NO_OP_LATE y NO_OP_OUT_OF_ORDER:
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L405)
  - [test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L497)

# 10. Consumidores

Resultado: RIESGO

Evidencia:

- consumidor convierte record a envelope y delega en coordinator sin logica de negocio adicional:
  - [consumidores.py](src/orquestacion_trabajos/modulos/trabajos/infraestructura/consumidores.py#L48)
  - [consumidores.py](src/orquestacion_trabajos/modulos/trabajos/infraestructura/consumidores.py#L63)
- cableado del coordinator en bootstrap:
  - [bootstrap.py](src/orquestacion_trabajos/config/bootstrap.py#L66)
  - [bootstrap.py](src/orquestacion_trabajos/config/bootstrap.py#L83)
- rutas activas de entrada siguen limitadas a 3 fuentes:
  - [rutas.py](src/orquestacion_trabajos/config/rutas.py#L12)
  - [rutas.py](src/orquestacion_trabajos/config/rutas.py#L26)

Conclusion:

La arquitectura infraestructura -> aplicacion -> dominio se mantiene. Riesgo: los eventos nuevos de FASE 3 no aparecen cableados en rutas activas; puede limitar el comportamiento end-to-end fuera de pruebas unitarias.

# 11. Atomicidad

Resultado: OK

Evidencia:

- Coordinator ejecuta todo dentro de una unica UoW y confirma al final:
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L56)
  - [coordinator.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L108)
- UoW desactiva autoflush, abre transaccion y hace flush+commit en confirmar:
  - [unidad_trabajo_sqlalchemy.py](src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py#L32)
  - [unidad_trabajo_sqlalchemy.py](src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py#L57)
- Handlers reutilizados no hacen commit si reciben unidad externa:
  - [crear_trabajo.py](src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/crear_trabajo.py#L20)
  - [aplicar_cotizacion.py](src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py#L17)

# 12. Problemas encontrados

| # | Problema | Severidad | Archivo | Metodo | Accion recomendada |
|---|---|---|---|---|---|
| 1 | Validacion de causacion contra ultimo comando del tipo, no contra comando causal exacto. Puede rechazar eventos validos (CMD-001) si ya existe CMD-002, y aceptar cuando no hay comando previo. | CRITICO | [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L601) | _validar_causacion_con_comando_emitido, _ultimo_command_id_emitido | Validar causacion por command_id exacto emitido y exigir existencia de comando causal compatible. |
| 2 | Cierre de compensacion no exige SeguimientoTrabajoCancelado cuando requested=true y confirmed=false, aunque ya se emitio CancelarSeguimientoTrabajo. | CRITICO | [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L729) | _compensaciones_confirmadas, _cerrar_compensacion_si_corresponde | Definir requerimiento de cancelacion de seguimiento segun compensacion solicitada, no solo segun abierto_confirmado. |
| 3 | Semantica dual de COMMAND_EMITTED: algunos registros implican outbox persistido y otros solo intencion sin outbox. | MEDIO | [src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py](src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py#L623) | _emitir_comando_pendiente_contrato, _ejecutar_transicion | Mantener criterio explicito/documentado y alertar en observabilidad para no interpretarlo como publicacion garantizada. |
| 4 | Eventos nuevos de FASE 3 no aparecen en rutas activas de consumidores; posible brecha de comportamiento en runtime real. | MEDIO | [src/orquestacion_trabajos/config/rutas.py](src/orquestacion_trabajos/config/rutas.py#L12) | fuentes | Confirmar alcance de despliegue de FASE 3 y si el wiring quedara en fase posterior por restriccion contractual. |
| 5 | Cobertura de pruebas no incluye negativos explicitos para causacion invalida en eventos nuevos. | BAJO | [tests/unitarias/aplicacion/sagas/test_saga_coordinator.py](tests/unitarias/aplicacion/sagas/test_saga_coordinator.py#L814) | tests de FASE 3 | Agregar pruebas negativas de causacion cuando se habilite ventana de cambios. |

# 13. Cambios obligatorios antes del commit

## BLOQUEANTES

- Corregir validacion de causacion para que no dependa de "ultimo comando" y exija correspondencia causal exacta.
- Corregir regla de cierre de compensaciones para no cerrar en COMPENSATED cuando se emitio cancelacion de seguimiento y aun no hay confirmacion.

## NO BLOQUEANTES

- Alinear semantica operativa/observabilidad de COMMAND_EMITTED (emitido vs publicado).
- Confirmar alcance de wiring runtime de eventos FASE 3 en rutas activas.
- Completar cobertura de pruebas negativas de causacion.

# 14. Veredicto

NO APROBADO PARA COMMIT

Justificacion:

Existen 2 defectos funcionales bloqueantes en causacion y cierre de compensaciones que pueden producir rechazo incorrecto de eventos causales validos y cierres prematuros de saga compensada.