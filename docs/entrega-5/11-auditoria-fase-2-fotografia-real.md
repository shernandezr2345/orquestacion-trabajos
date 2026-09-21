# 11 - Auditoria FASE 2 (fotografia real, sin implementacion)

Regla aplicada en esta entrega:
- No se implemento codigo.
- No se crearon contratos Avro.
- No se crearon topics.
- No se modifico el SagaCoordinator.

Repositorios auditados:
- Disponible: orquestacion-trabajos
- Disponible: seguimiento-trabajos
- Disponible: cotizaciones

## A. Arquitectura actual por repositorio

### orquestacion-trabajos
- Patron: servicio FastAPI con consumo Pulsar + outbox.
- SagaCoordinator central ya existe y esta conectado al runtime.
- Entradas activas en runtime: SolicitudDePartnerListaParaAtencion.v1, CotizacionRegistrada.v1, CotizacionRechazada.v1.
- Salidas activas en runtime: TrabajoCreado.v1, SolicitarCotizacion.v1.
- Evidencia:
  - src/orquestacion_trabajos/config/rutas.py
  - src/orquestacion_trabajos/config/bootstrap.py
  - src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py

### seguimiento-trabajos
- Patron: proyeccion de lectura, sin bus de comandos propio para saga de apertura/cancelacion.
- Consumidores activos: TrabajoCreado.v1, CotizacionRegistrada.v1, CotizacionRechazada.v1.
- No hay implementacion de apertura/cancelacion de seguimiento como contratos de saga FASE 2.
- Evidencia:
  - src/seguimiento_trabajos/config/rutas.py
  - src/seguimiento_trabajos/config/bootstrap.py
  - src/seguimiento_trabajos/modulos/seguimiento/infraestructura/mapeadores_eventos.py
  - src/seguimiento_trabajos/modulos/seguimiento/dominio/objetos_valor.py

### cotizaciones
- Patron: consume comando SolicitarCotizacion.v1 y publica resultado CotizacionRegistrada.v1 o CotizacionRechazada.v1.
- No hay implementacion productiva de AnularCotizacion.v1 ni CotizacionAnulada.v1.
- Evidencia:
  - src/cotizaciones/config/settings.py
  - src/cotizaciones/config/bootstrap.py
  - src/cotizaciones/modulos/cotizaciones/infraestructura/consumidor_peticiones.py
  - src/cotizaciones/modulos/cotizaciones/infraestructura/mapeadores_eventos.py

## B. Matriz de contratos reales (A implementados, B propuestos, C por crear)

### B.A Contratos existentes e implementados
| Mensaje | Avro real en workspace | Productor | Consumidor real | Estado |
|---|---|---|---|---|
| SolicitarCotizacion.v1 | Si | orquestacion-trabajos | cotizaciones | IMPLEMENTADO |
| CotizacionRegistrada.v1 | Si | cotizaciones | orquestacion-trabajos, seguimiento-trabajos | IMPLEMENTADO |
| CotizacionRechazada.v1 | Si | cotizaciones | orquestacion-trabajos, seguimiento-trabajos | IMPLEMENTADO |
| TrabajoCreado.v1 | Si | orquestacion-trabajos | seguimiento-trabajos | IMPLEMENTADO |
| AtencionHabilitadaRegistrada.v1 | Si (owner solicitud-partner) | solicitud-partner | SagaCoordinator (logica), no conectado en rutas activas | PARCIAL |
| AtencionCanceladaRegistrada.v1 | Si (owner solicitud-partner) | solicitud-partner | SagaCoordinator (logica), no conectado en rutas activas | PARCIAL |

### B.B Contratos propuestos en documentacion
| Mensaje | Definido en docs | Avro congelado en repos auditados | Estado |
|---|---|---|---|
| AbrirSeguimientoTrabajo.v1 | Si | No | DEFINIDO |
| SeguimientoTrabajoAbierto.v1 | Si | No | DEFINIDO |
| AperturaSeguimientoFallida.v1 | Si | No | DEFINIDO |
| CancelarSeguimientoTrabajo.v1 | Si | No | DEFINIDO |
| SeguimientoTrabajoCancelado.v1 | Si | No | DEFINIDO |
| AnularCotizacion.v1 | Si | No | DEFINIDO |
| CotizacionAnulada.v1 | Si | No | DEFINIDO |
| TrabajoCancelado.v1 | Si | No | DEFINIDO |

### B.C Contratos que requieren creacion
- Requieren Avro + topic + suscripciones + wiring productivo:
  - AbrirSeguimientoTrabajo.v1
  - SeguimientoTrabajoAbierto.v1
  - AperturaSeguimientoFallida.v1
  - CancelarSeguimientoTrabajo.v1
  - SeguimientoTrabajoCancelado.v1
  - AnularCotizacion.v1
  - CotizacionAnulada.v1
  - TrabajoCancelado.v1

## C. Matriz de brechas FASE 2

| Mensaje | Avro | Productor | Consumidor | Topic | Handler | Persistencia | Tests | Estado | Clasificacion |
|---|---|---|---|---|---|---|---|---|---|
| CotizacionRegistrada.v1 | Si | Cotizaciones | Orquestacion y Seguimiento | Si | Si | Si | Si | Activo | IMPLEMENTADO |
| AbrirSeguimientoTrabajo.v1 | No | Propuesto Orquestacion | Propuesto Seguimiento | No | No | No | No | No activo | PENDIENTE |
| SeguimientoTrabajoAbierto.v1 | No | Propuesto Seguimiento | Propuesto Orquestacion | No | No | No | No | No activo | PENDIENTE |
| RegistrarAtencionHabilitada.v1 | Si (owner solicitud-partner) | Propuesto Orquestacion en FASE 2 | solicitud-partner | No en rutas actuales de Orquestacion | No en coordinator actual | No | No | No activo en FASE 2 | PARCIAL |
| AtencionHabilitadaRegistrada.v1 | Si (owner solicitud-partner) | solicitud-partner | Coordinator (si llega envelope) | No en rutas actuales de Orquestacion | Si (coordinator) | Si (estado/paso) | Si (unitario) | Logica existe, wiring no | PARCIAL |
| AperturaSeguimientoFallida.v1 | No | Propuesto Seguimiento | Propuesto Orquestacion | No | No | No | No | No activo | PENDIENTE |
| AnularCotizacion.v1 | No | Propuesto Orquestacion | Propuesto Cotizaciones | No | No | No | No | No activo | PENDIENTE |
| CotizacionAnulada.v1 | No | Propuesto Cotizaciones | Propuesto Orquestacion | No | No | No | No | No activo | PENDIENTE |
| TrabajoCancelado.v1 | No | Propuesto Orquestacion | Propuesto Seguimiento | No | No | No | No | No activo | PENDIENTE |
| RegistrarAtencionCancelada.v1 | Si (owner solicitud-partner) | Propuesto Orquestacion en compensacion | solicitud-partner | No en rutas actuales de Orquestacion | No en coordinator actual | No | No | No activo en FASE 2 | PARCIAL |
| AtencionCanceladaRegistrada.v1 | Si (owner solicitud-partner) | solicitud-partner | Coordinator (si llega envelope) | No en rutas actuales de Orquestacion | Si (coordinator) | Si (estado/paso) | Si (unitario) | Logica existe, wiring no | PARCIAL |
| CancelarSeguimientoTrabajo.v1 | No | Propuesto Orquestacion | Propuesto Seguimiento | No | No | No | No | No activo | PENDIENTE |
| SeguimientoTrabajoCancelado.v1 | No | Propuesto Seguimiento | Propuesto Orquestacion | No | No | No | No | No activo | PENDIENTE |

## D. Happy Path: implementado vs faltante

Flujo objetivo:
CotizacionRegistrada.v1 -> AbrirSeguimientoTrabajo.v1 -> SeguimientoTrabajoAbierto.v1 -> RegistrarAtencionHabilitada.v1 -> AtencionHabilitadaRegistrada.v1 -> COMPLETED

Estado real:
- Implementado hoy:
  - Consumo de CotizacionRegistrada.v1 en Orquestacion y Seguimiento.
  - En Orquestacion, SagaCoordinator avanza paso a ABRIR_SEGUIMIENTO pero deja registro IGNORED indicando comando pendiente de contrato.
- Faltante:
  - Contrato + topic + producer de AbrirSeguimientoTrabajo.v1.
  - Consumer/handler en Seguimiento para apertura de seguimiento.
  - Evento SeguimientoTrabajoAbierto.v1 (contrato + emision + consumo).
  - Emision real de RegistrarAtencionHabilitada.v1 desde Orquestacion.
  - Conexion de fuente AtencionHabilitadaRegistrada.v1 en rutas runtime de Orquestacion.

## E. Compensacion: implementada vs faltante

Flujo objetivo:
AperturaSeguimientoFallida.v1 -> AnularCotizacion.v1 -> CotizacionAnulada.v1 -> TrabajoCancelado.v1 -> RegistrarAtencionCancelada.v1 -> AtencionCanceladaRegistrada.v1 -> (opcional) CancelarSeguimientoTrabajo.v1 -> SeguimientoTrabajoCancelado.v1

Estado real:
- Implementado hoy:
  - Manejo de CotizacionRechazada.v1 separado, con ruta pendiente (sin AnularCotizacion) y sin cerrar decision final de estado.
  - Manejo de AtencionCanceladaRegistrada.v1 en coordinator si llega envelope (cierra a COMPENSATED).
- Faltante:
  - Toda la cadena contractual/productiva de AperturaSeguimientoFallida, AnularCotizacion, CotizacionAnulada, TrabajoCancelado, CancelarSeguimientoTrabajo, SeguimientoTrabajoCancelado.
  - Wiring runtime para consumir/publicar esos mensajes.

## F. Topics y subscriptions existentes (reales)

### Orquestacion
- Fuentes:
  - persistent://<tenant>/<namespace>/solicitud-partner-lista-v1, suscripcion orquestacion-solicitudes-v1
  - persistent://<tenant>/<namespace>/cotizacion-registrada-v1, suscripcion orquestacion-cotizacion-registrada-v1
  - persistent://<tenant>/<namespace>/cotizacion-rechazada-v1, suscripcion orquestacion-cotizacion-rechazada-v1
- Destinos:
  - persistent://<tenant>/<namespace>/trabajo-creado-v1
  - persistent://<tenant>/<namespace>/solicitar-cotizacion-v1

### Seguimiento
- Fuentes:
  - persistent://public/default/trabajo-creado-v1, suscripcion seguimiento-trabajos-v1
  - persistent://public/default/cotizacion-registrada-v1, suscripcion seguimiento-cotizacion-registrada
  - persistent://public/default/cotizacion-rechazada-v1, suscripcion seguimiento-cotizacion-rechazada-v1

### Cotizaciones
- Fuente:
  - persistent://public/default/solicitar-cotizacion-v1, suscripcion cotizaciones-peticiones-v1
- Destinos:
  - persistent://public/default/cotizacion-registrada-v1
  - persistent://public/default/cotizacion-rechazada-v1

## G. Dependencias entre repositorios

- Orquestacion depende de Cotizaciones para resultados de cotizacion y, en FASE 2, eventual anulacion.
- Orquestacion depende de Seguimiento para apertura/cancelacion de seguimiento (hoy no implementado).
- Seguimiento depende de eventos de Orquestacion y Cotizaciones para su proyeccion.
- Cotizaciones depende del comando de Orquestacion para iniciar resolucion.
- Mensajes de atencion (habilitada/cancelada) dependen del owner solicitud-partner para integracion completa, aunque este repo no era objetivo principal de auditoria.

## H. Contratos que realmente necesitan ser creados

Necesitan creacion real (no solo propuesta):
- AbrirSeguimientoTrabajo.v1
- SeguimientoTrabajoAbierto.v1
- AperturaSeguimientoFallida.v1
- CancelarSeguimientoTrabajo.v1
- SeguimientoTrabajoCancelado.v1
- AnularCotizacion.v1
- CotizacionAnulada.v1
- TrabajoCancelado.v1

## I. Tests existentes

### Orquestacion
- 15 tests unitarios del SagaCoordinator, incluyendo duplicate, late, out_of_order, conflict, rollback y rutas actuales.
- Evidencia: tests/unitarias/aplicacion/sagas/test_saga_coordinator.py

### Seguimiento
- Tests de contrato y mapeo para TrabajoCreado, CotizacionRegistrada, CotizacionRechazada.
- Evidencia: tests/contratos/test_eventos_v1.py

### Cotizaciones
- Tests unitarios, de contratos e integracion para SolicitarCotizacion, CotizacionRegistrada y CotizacionRechazada.
- Evidencia: tests/contratos, tests/integracion, tests/unitarias

## J. Tests que deberan agregarse

- Orquestacion:
  - unitarios para AbrirSeguimientoTrabajo, SeguimientoTrabajoAbierto, AperturaSeguimientoFallida, AnularCotizacion, CotizacionAnulada, CancelarSeguimientoTrabajo, SeguimientoTrabajoCancelado, TrabajoCancelado.
  - contrato para nuevos Avro y rutas topic/suscripcion.
  - integracion E2E de happy path completo y compensacion completa.
- Seguimiento:
  - contrato/consumer/handler para AbrirSeguimientoTrabajo y CancelarSeguimientoTrabajo.
  - pruebas de publicacion para SeguimientoTrabajoAbierto, AperturaSeguimientoFallida, SeguimientoTrabajoCancelado.
- Cotizaciones:
  - contrato/consumer/handler para AnularCotizacion.
  - contrato/publicacion para CotizacionAnulada.

## K. Decisiones pendientes

- Definir transicion exacta para rama CotizacionRechazada:
  - RUNNING -> COMPENSATING
  - o RUNNING -> COMPENSATED
- Definir ownership final y versionado de cada contrato faltante.
- Definir reglas duras de correlacion/causacion para contratos nuevos.
- Definir comportamiento de observabilidad para mensajes sin id_saga ni id_solicitud (hoy no-op).

## L. Riesgos

- Riesgo de retrabajo si se implementa codigo antes de congelar contratos y topics.
- Riesgo de divergencia entre repositorios por schemas provisionales (explicito en seguimiento-trabajos/docs/contratos/README.md).
- Riesgo de integrar parcialmente el coordinator sin consumers/productores listos en servicios pares.
- Riesgo de huecos de trazabilidad en eventos sin identificadores de saga/solicitud.

## M. Orden recomendado de implementacion

1. Congelar contratos faltantes (Avro, campos, ownership, topics, subscriptions).
2. Implementar primero cadena Happy Path FASE 2:
   - AbrirSeguimientoTrabajo -> SeguimientoTrabajoAbierto -> RegistrarAtencionHabilitada -> AtencionHabilitadaRegistrada.
3. Implementar luego cadena de compensacion por fallo de apertura:
   - AperturaSeguimientoFallida -> AnularCotizacion -> CotizacionAnulada -> TrabajoCancelado -> RegistrarAtencionCancelada -> AtencionCanceladaRegistrada -> CancelarSeguimientoTrabajo -> SeguimientoTrabajoCancelado.
4. Cerrar decision de estado de CotizacionRechazada y solo entonces codificar su ruta final.
5. Ejecutar bateria de pruebas por capas: contrato -> unitarias -> integracion -> E2E cruzado.

## Evidencia principal usada (archivos)

- orquestacion-trabajos/src/orquestacion_trabajos/config/rutas.py
- orquestacion-trabajos/src/orquestacion_trabajos/config/bootstrap.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py
- orquestacion-trabajos/tests/unitarias/aplicacion/sagas/test_saga_coordinator.py
- orquestacion-trabajos/tests/contratos/test_contratos_compartidos.py
- seguimiento-trabajos/src/seguimiento_trabajos/config/rutas.py
- seguimiento-trabajos/src/seguimiento_trabajos/config/bootstrap.py
- seguimiento-trabajos/src/seguimiento_trabajos/modulos/seguimiento/dominio/objetos_valor.py
- seguimiento-trabajos/src/seguimiento_trabajos/modulos/seguimiento/infraestructura/mapeadores_eventos.py
- seguimiento-trabajos/tests/contratos/test_eventos_v1.py
- seguimiento-trabajos/docs/contratos/README.md
- cotizaciones/src/cotizaciones/config/settings.py
- cotizaciones/src/cotizaciones/config/bootstrap.py
- cotizaciones/src/cotizaciones/modulos/cotizaciones/infraestructura/consumidor_peticiones.py
- cotizaciones/src/cotizaciones/modulos/cotizaciones/infraestructura/mapeadores_eventos.py
- cotizaciones/docs/contratos/README.md
