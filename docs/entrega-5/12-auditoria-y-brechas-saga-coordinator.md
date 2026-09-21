# AUDITORIA DEL REPOSITORIO Y MATRIZ DE BRECHAS - SAGA COORDINATOR (ENTREGA 5)

## 1. Alcance y criterio

Este documento cubre SOLO auditoria read-only del repositorio para preparar la implementacion del SagaCoordinator.

No se modifico codigo.

Fuente de verdad funcional y contractual:
- docs/entrega-5/10-matrices-contratos-saga.md
- docs/entrega-5/07-diseno-saga-steps.md
- docs/entrega-5/08-diseno-persistencia-saga.md
- docs/entrega-5/09-implementacion-persistencia-saga.md

Regla aplicada:
- No inventar contratos, campos, payloads, topics ni comportamiento.

## 2. Inventario auditado

### 2.1 SagaInstance / agregado Saga

Archivo:
- src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py

Responsabilidad:
- Define estados de saga: RUNNING, COMPENSATING, COMPLETED, COMPENSATED.
- Define pasos de saga (SagaStepName).
- Define taxonomia de SagaLog (tipo_registro y resultado).
- Define entidad SagaInstance con banderas:
  - seguimiento_apertura_solicitada
  - seguimiento_abierto_confirmado

Estado actual:
- IMPLEMENTADO.

Relacion con SagaCoordinator:
- Base directa del estado, paso y reglas de transicion.

Brecha:
- No existe aun una capa coordinadora que aplique estas transiciones a eventos de negocio en runtime.

### 2.2 SagaRepository

Archivos:
- src/orquestacion_trabajos/modulos/sagas/dominio/repositorios.py
- src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py

Responsabilidad:
- CRUD y cambios de estado/paso para SagaInstance.
- Busqueda por id_saga e id_solicitud.
- Persistencia de SagaLog.
- Deteccion de duplicado por message_id dentro de una saga.
- Control de concurrencia por version (optimistic lock).

Estado actual:
- IMPLEMENTADO.

Relacion con SagaCoordinator:
- Permite resolver saga por id_saga o por id_solicitud cuando el evento no trae id_saga.

Brecha:
- No hay handlers de coordinacion que consuman estos repositorios en el flujo principal de mensajes.

### 2.3 SagaLog

Archivos:
- src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py
- src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py
- src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py

Responsabilidad:
- Registro append-only de eventos, comandos, cambios de estado y no-op.
- Tipos de registro disponibles:
  - EVENT_RECEIVED
  - COMMAND_EMITTED
  - EVENT_EMITTED
  - LOCAL_OPERATION
  - STATE_CHANGED
  - DUPLICATE
  - LATE
  - OUT_OF_ORDER
  - IGNORED
- Resultados disponibles:
  - APPLIED
  - NO_OP_DUPLICATE
  - NO_OP_LATE
  - NO_OP_OUT_OF_ORDER
  - REJECTED_CONFLICT

Estado actual:
- IMPLEMENTADO.

Relacion con SagaCoordinator:
- Permite materializar auditoria exacta de validaciones previas a transicion.

Brecha:
- Aunque el modelo existe, todavia no hay flujo coordinador que escriba LATE/OUT_OF_ORDER/CONFLICT para eventos de saga reales.

### 2.4 UnitOfWork

Archivos:
- src/orquestacion_trabajos/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py
- src/orquestacion_trabajos/modulos/sagas/infraestructura/unidad_trabajo.py
- src/orquestacion_trabajos/modulos/trabajos/infraestructura/unidad_trabajo.py

Responsabilidad:
- Atomicidad transaccional con commit/rollback.
- Reglas de colision de persistencia (constraints reintentables).
- Integracion inbox/outbox en flujo de trabajos.

Estado actual:
- IMPLEMENTADO para Saga y para Trabajos.

Relacion con SagaCoordinator:
- Soporta consistencia SagaInstance + SagaLog por unidad transaccional.

Brecha:
- No esta cableado aun un UoW de saga en el pipeline principal de consumidores.

### 2.5 EventBus / CommandBus / Publisher

Archivos:
- src/orquestacion_trabajos/seedwork/infraestructura/publicador_pulsar.py
- src/orquestacion_trabajos/seedwork/infraestructura/consumidor_pulsar.py
- src/orquestacion_trabajos/seedwork/infraestructura/despacho_outbox.py

Responsabilidad:
- Consumo Pulsar.
- Publicacion Pulsar.
- Despacho de outbox.

Estado actual:
- IMPLEMENTADO como infraestructura de transporte.

Relacion con SagaCoordinator:
- Es la via correcta de comunicacion asincrona.

Brecha:
- No existe EventBus/CommandBus explicito por dominio de Saga; el wiring actual opera sobre modulo trabajos.

### 2.6 Handlers existentes

Archivos:
- src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/crear_trabajo.py
- src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py

Responsabilidad:
- Crear trabajo desde SolicitudDePartnerListaParaAtencion.
- Aplicar CotizacionRegistrada/CotizacionRechazada al agregado Trabajo.

Estado actual:
- IMPLEMENTADO.

Relacion con SagaCoordinator:
- Son piezas reutilizables dentro del flujo coordinado.

Brecha:
- No crean ni actualizan SagaInstance.
- No registran SagaLog de validaciones de saga.

### 2.7 Schemas Avro existentes

Implementados en orquestacion-trabajos:
- docs/contratos/solicitud-lista-v1.avsc
- docs/contratos/trabajo-creado-v1.avsc
- docs/contratos/solicitar-cotizacion-v1.avsc
- docs/contratos/cotizacion-registrada-v1.avsc
- docs/contratos/cotizacion-rechazada-v1.avsc

Disponibles en solicitud-partner y usados por la matriz como implementados:
- solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc
- solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc
- solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc
- solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc

Estado actual:
- PARCIAL respecto al flujo completo de saga de la entrega.

Brecha:
- No existen Avro implementados en este servicio para:
  - AbrirSeguimientoTrabajo.v1
  - SeguimientoTrabajoAbierto.v1
  - AperturaSeguimientoFallida.v1
  - CancelarSeguimientoTrabajo.v1
  - SeguimientoTrabajoCancelado.v1
  - AnularCotizacion.v1
  - CotizacionAnulada.v1
  - TrabajoCancelado.v1

### 2.8 Configuracion Pulsar

Archivos:
- src/orquestacion_trabajos/config/rutas.py
- src/orquestacion_trabajos/config/bootstrap.py
- src/orquestacion_trabajos/config/settings.py

Estado actual:
- Consumidores definidos:
  - solicitud-partner-lista-v1
  - cotizacion-registrada-v1
  - cotizacion-rechazada-v1
- Destinos definidos:
  - trabajo-creado-v1
  - solicitar-cotizacion-v1

Relacion con SagaCoordinator:
- Confirma el pipeline operativo actual.

Brecha:
- No hay topics/subscriptions configurados para mensajes de seguimiento ni comandos/eventos de atencion de saga completa.

### 2.9 Tests existentes

Archivo clave de Saga:
- tests/unitarias/infraestructura/sagas/test_repositorios_saga_sql.py

Cobertura actual:
- Persistencia SagaInstance.
- Reglas de consistencia de banderas.
- SagaLog append-only.
- Concurrencia por version.
- Idempotencia por indice unico (casos A/B/C/D con coalesce).
- UoW commit y rollback atomico para Saga.

Brecha:
- No hay tests de coordinacion funcional de saga:
  - Happy Path completo.
  - LATE.
  - OUT_OF_ORDER.
  - CONFLICT.
  - Compensacion por fallo de seguimiento.

## 3. Matriz de brechas vs reglas de Entrega 5

| Requisito objetivo | Evidencia actual | Estado | Clasificacion |
|---|---|---|---|
| Estados validos RUNNING/COMPENSATING/COMPLETED/COMPENSATED | Enums + constraints implementados | Cumple base | DEFINIDO |
| Resolucion saga por id_saga y por id_solicitud | Repositorio soporta ambas busquedas | Cumple base | DEFINIDO |
| Idempotencia id_saga + tipo_mensaje + message_id | Indice uq_saga_log_idempotencia + pruebas | Cumple base | DEFINIDO |
| Duplicado produce NO_OP_DUPLICATE | Modelo y pruebas de indice existen | Parcial (no flujo coordinator) | INFERIDO |
| Validacion LATE y registro NO_OP_LATE | Enum existe | No aplicado en runtime | NO DEFINIDO |
| Validacion OUT_OF_ORDER y registro NO_OP_OUT_OF_ORDER | Enum existe | No aplicado en runtime | NO DEFINIDO |
| Validacion CONFLICT con REJECTED_CONFLICT | Enum existe | No aplicado en runtime | NO DEFINIDO |
| Happy Path de saga (hasta COMPLETED) | Solo pipeline trabajos (crear/aplicar cotizacion) | Parcial | INFERIDO |
| Rama compensacion por AperturaSeguimientoFallida | Mensajes y wiring no implementados | Falta | NO DEFINIDO |
| Regla condicional CancelarSeguimientoTrabajo por bandera | Bandera existe en SagaInstance | Parcial | INFERIDO |
| Rama CotizacionRechazada formalizada | Documentacion marca decision pendiente | Pendiente | NO DEFINIDO |
| Atomicidad SagaInstance + SagaLog | UoW saga implementado y probado | Cumple base | DEFINIDO |
| Integracion de contratos propuestos de seguimiento/compensacion | Solo en documento de propuesta | Parcial | NO DEFINIDO EN CONTRATOS ACTUALES |

## 4. Decisiones pendientes identificadas

1. Ruta exacta para CotizacionRechazada:
- RUNNING -> COMPENSATING
- o cierre compensado directo

Estado:
- DECISION PENDIENTE (explicitado en docs/entrega-5/07-diseno-saga-steps.md y docs/entrega-5/08-diseno-persistencia-saga.md).

2. Alcance operativo de mensajes propuestos (seguimiento/cotizacion compensatoria):
- Definidos en propuesta, no implementados como contratos activos en este servicio.

Estado:
- PARCIAL.

3. Estandarizacion final de eventos ignorados/tardios:
- Hay enums definitivos en codigo, pero falta aplicacion sistematica en coordinator.

Estado:
- PENDIENTE DE IMPLEMENTACION.

4. Igualdad formal correlacion == id_solicitud en cotizaciones:
- En contratos esta presente correlacion e id_solicitud, pero la igualdad opera como regla de negocio.

Estado:
- INFERIDO.

## 5. Conclusiones de auditoria

1. La base de persistencia para SagaCoordinator ya existe y esta bien encaminada:
- SagaInstance
- SagaRepository
- SagaLog
- UoW saga
- Reglas de idempotencia por indice unico

2. El gap principal no es de persistencia sino de orquestacion aplicativa:
- Falta coordinator/harness de eventos para aplicar validaciones y transiciones.

3. El flujo actual de orquestacion-trabajos sigue centrado en modulo trabajos:
- entrada -> crear trabajo -> solicitar cotizacion -> aplicar resultado

4. La implementacion del nucleo del SagaCoordinator es viable sin inventar contratos:
- usando los eventos/contratos hoy implementados,
- y dejando como pendientes las ramas dependientes de contratos aun propuestos.

## 6. Recomendacion para siguiente fase (sin implementar aun)

Diseñar e implementar en este orden:
1. Capa SagaCoordinator con validaciones (DUPLICATE, LATE, OUT_OF_ORDER, CONFLICT).
2. Wiring en bootstrap para que eventos entren por coordinator.
3. Registro transaccional SagaInstance + SagaLog por evento.
4. Pruebas unitarias del coordinator para:
- happy path soportado por contratos actuales
- idempotencia
- late
- out_of_order
- conflict

Mantener fuera de alcance hasta decision/contrato final:
- ramas completas de seguimiento y compensaciones que dependen de mensajes aun no implementados en Avro dentro del servicio.
