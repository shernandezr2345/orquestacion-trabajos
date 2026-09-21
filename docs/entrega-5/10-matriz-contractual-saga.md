# 10 - Matriz Contractual Saga (Auditoria FASE 2 - previa a implementacion)

## 1. Objetivo

Construir una auditoria contractual y funcional de la Saga de Entrega 5 para definir, sin cambios de codigo de produccion, el comportamiento esperado del SagaCoordinator en FASE 2.

Alcance de esta auditoria:
- Solo contratos y diseno existente en repositorio.
- Sin inventar campos, estados, steps, tablas, endpoints, contratos ni topics nuevos.
- Sin asumir implementaciones internas de cotizaciones o seguimiento-trabajos.

## 2. Fuentes

Fuentes contractuales/diseno principales:
- contratos-saga-propuesta.md
- orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md
- orquestacion-trabajos/docs/entrega-5/07-diseno-saga-steps.md
- orquestacion-trabajos/docs/entrega-5/08-diseno-persistencia-saga.md
- orquestacion-trabajos/docs/entrega-5/13-diseno-tecnico-saga-coordinator.md

Contratos Avro disponibles:
- orquestacion-trabajos/docs/contratos/*.avsc
- solicitud-partner/docs/contratos/*.avsc
- cotizaciones/docs/contratos/*.avsc
- seguimiento-trabajos/docs/contratos/*.avsc

Codigo y pruebas relevantes:
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/sagas/aplicacion/coordinador.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/sagas/infraestructura/orm.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/sagas/infraestructura/repositorios.py
- orquestacion-trabajos/src/orquestacion_trabajos/config/rutas.py
- orquestacion-trabajos/tests/unitarias/aplicacion/sagas/test_saga_coordinator.py
- orquestacion-trabajos/tests/contratos/test_contratos_compartidos.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py

Fuente PDF solicitada:
- orquestacion-trabajos/docs/entrega-5/hda-entrega5-propuesta-saga-bff.pdf
- Estado: no se obtuvo texto estructurado utilizable en esta sesion (lectura binaria). Se uso como referencia documental de contexto, y se privilegio el contrato MD como fuente operativa trazable.

## 3. Inventario de contratos

| Mensaje | Tipo | Version | Productor | Consumidor | Direccion | Proposito | Fuente |
|---|---|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | Evento | v1 | solicitudes-partner | orquestacion-trabajos | Entrada -> Orquestacion | Disparar inicio de saga | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| TrabajoCreado.v1 | Evento | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Proyeccion de trabajo | orquestacion-trabajos/docs/contratos/trabajo-creado-v1.avsc |
| SolicitarCotizacion.v1 | Comando | v1 | orquestacion-trabajos | cotizaciones | Orquestacion -> Cotizaciones | Solicitar cotizacion | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| CotizacionRegistrada.v1 | Evento | v1 | cotizaciones | orquestacion-trabajos, seguimiento-trabajos | Cotizaciones -> Orquestacion/Seguimiento | Informar cotizacion propuesta | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRechazada.v1 | Evento | v1 | cotizaciones | orquestacion-trabajos, seguimiento-trabajos | Cotizaciones -> Orquestacion/Seguimiento | Informar rechazo de cotizacion | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| AbrirSeguimientoTrabajo.v1 | Comando | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Pedir apertura de seguimiento | contratos-saga-propuesta.md |
| SeguimientoTrabajoAbierto.v1 | Evento | v1 | seguimiento-trabajos | orquestacion-trabajos | Seguimiento -> Orquestacion | Confirmar apertura de seguimiento | contratos-saga-propuesta.md |
| AperturaSeguimientoFallida.v1 | Evento | v1 | seguimiento-trabajos | orquestacion-trabajos | Seguimiento -> Orquestacion | Informar fallo de apertura | contratos-saga-propuesta.md |
| CancelarSeguimientoTrabajo.v1 | Comando | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Pedir cancelacion de seguimiento | contratos-saga-propuesta.md |
| SeguimientoTrabajoCancelado.v1 | Evento | v1 | seguimiento-trabajos | orquestacion-trabajos | Seguimiento -> Orquestacion | Confirmar cancelacion de seguimiento | contratos-saga-propuesta.md |
| AnularCotizacion.v1 | Comando | v1 | orquestacion-trabajos | cotizaciones | Orquestacion -> Cotizaciones | Pedir anulacion de cotizacion | contratos-saga-propuesta.md |
| CotizacionAnulada.v1 | Evento | v1 | cotizaciones | orquestacion-trabajos | Cotizaciones -> Orquestacion | Confirmar anulacion de cotizacion | contratos-saga-propuesta.md |
| RegistrarAtencionHabilitada.v1 | Comando | v1 | orquestacion-trabajos | solicitudes-partner | Orquestacion -> Entrada | Solicitar registro de atencion habilitada | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | Evento | v1 | solicitudes-partner | orquestacion-trabajos | Entrada -> Orquestacion | Confirmar atencion habilitada | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| RegistrarAtencionCancelada.v1 | Comando | v1 | orquestacion-trabajos | solicitudes-partner | Orquestacion -> Entrada | Solicitar registro de atencion cancelada | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | Evento | v1 | solicitudes-partner | orquestacion-trabajos | Entrada -> Orquestacion | Confirmar atencion cancelada | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| TrabajoCancelado.v1 | Evento | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Informar cancelacion de trabajo | contratos-saga-propuesta.md |

Estado de disponibilidad de contratos:
- Implementados en Avro dentro del workspace: SolicitudDePartnerListaParaAtencion, TrabajoCreado, SolicitarCotizacion, CotizacionRegistrada, CotizacionRechazada, RegistrarAtencionHabilitada, AtencionHabilitadaRegistrada, RegistrarAtencionCancelada, AtencionCanceladaRegistrada.
- Definidos en propuesta, sin Avro final en workspace de Orquestacion: AbrirSeguimientoTrabajo, SeguimientoTrabajoAbierto, AperturaSeguimientoFallida, CancelarSeguimientoTrabajo, SeguimientoTrabajoCancelado, AnularCotizacion, CotizacionAnulada, TrabajoCancelado.

## 4. Matriz de campos

### 4.1 Contratos con Avro implementado

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | event_id | string | Si | solicitud-partner | identidad de evento | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | tipo | string | Si | solicitud-partner | valor contractual | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | version_contrato | int | Si | solicitud-partner | version 1 | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | instante | string | Si | solicitud-partner | ISO UTC textual | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | correlacion | string | Si | solicitud-partner | correlacion == id_solicitud | solicitud-partner/docs/contratos/README.md |
| SolicitudDePartnerListaParaAtencion.v1 | causacion | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_saga | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_solicitud | string | Si | solicitud-partner | identidad de negocio | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_trabajo | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_partner | string | Si | solicitud-partner | identidad de partner | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | extras reales | version_solicitud, referencia_externa, categoria, tipo_solicitud, aprobacion_previa, tipo_red, id_politica, version_politica | Segun campo | solicitud-partner | payload de negocio | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| SolicitarCotizacion.v1 | command_id | string | Si | orquestacion | identidad de comando | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | tipo | string | Si | orquestacion | default SolicitarCotizacion.v1 | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | version_contrato | int | Si | orquestacion | default 1 | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | instante | string | Si | orquestacion | ISO UTC textual | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | correlacion | string | Si | orquestacion | correlacion == id_solicitud (regla en cotizaciones) | cotizaciones/docs/contratos/README.md |
| SolicitarCotizacion.v1 | causacion | string | Si | orquestacion | debe ser event_id que causa la solicitud | cotizaciones/docs/contratos/README.md |
| SolicitarCotizacion.v1 | id_saga | N/A | No existe | N/A | no definido en este contrato | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_solicitud | string | Si | orquestacion | identidad de negocio | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_trabajo | string | Si | orquestacion | identidad de trabajo | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_partner | string | Si | orquestacion | identidad de partner | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | extras reales | id_peticion, categoria, tipo_solicitud, tipo_red, id_politica, version_politica | Segun campo | orquestacion | payload de cotizacion | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| CotizacionRegistrada.v1 | event_id | string | Si | cotizaciones | identidad de evento | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | tipo | string | Si | cotizaciones | valor contractual | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | version_contrato | int | Si | cotizaciones | version 1 (revisiones compatibles posibles) | cotizaciones/docs/contratos/README.md |
| CotizacionRegistrada.v1 | instante | string | Si | cotizaciones | ISO UTC textual | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | correlacion | string | Si | cotizaciones | correlacion == id_solicitud (regla funcional) | cotizaciones/docs/contratos/README.md |
| CotizacionRegistrada.v1 | causacion | string | Si | cotizaciones | causacion == command_id de SolicitarCotizacion | cotizaciones/docs/contratos/README.md |
| CotizacionRegistrada.v1 | id_saga | N/A | No existe | N/A | no definido en este contrato | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_solicitud | string | Si | cotizaciones | identidad de negocio | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_trabajo | string | Si | cotizaciones | identidad de trabajo | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_partner | string | Si | cotizaciones | identidad de partner | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | extras reales | id_peticion, version_catalogo, version_cotizacion, id_cotizacion, id_proveedor, importe_menor, moneda, categoria, tipo_red | Segun campo | cotizaciones | payload resultado | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| CotizacionRechazada.v1 | event_id | string | Si | cotizaciones | identidad de evento | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | tipo | string | Si | cotizaciones | valor contractual | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | version_contrato | int | Si | cotizaciones | version 1 | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | instante | string | Si | cotizaciones | ISO UTC textual | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | correlacion | string | Si | cotizaciones | correlacion == id_solicitud (regla funcional) | cotizaciones/docs/contratos/README.md |
| CotizacionRechazada.v1 | causacion | string | Si | cotizaciones | causacion == command_id de SolicitarCotizacion | cotizaciones/docs/contratos/README.md |
| CotizacionRechazada.v1 | id_saga | N/A | No existe | N/A | no definido en este contrato | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_solicitud | string | Si | cotizaciones | identidad de negocio | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_trabajo | string | Si | cotizaciones | identidad de trabajo | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_partner | string | Si | cotizaciones | identidad de partner | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | extras reales | id_peticion, version_catalogo, version_cotizacion, motivo | Segun campo | cotizaciones | payload rechazo | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| RegistrarAtencionHabilitada.v1 | command_id | string | Si | orquestacion | identidad comando | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | tipo/version/instante | string/int/string | Si | orquestacion | metadatos de comando | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | correlacion | string | Si | orquestacion | correlation == request_id (validado en dominio entrada) | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py |
| RegistrarAtencionHabilitada.v1 | causacion | string | Si | orquestacion | identidad causal previa | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | id_saga/id_solicitud/id_trabajo/id_partner | string | Si | orquestacion | identidades de saga y negocio | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | event_id | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| AtencionHabilitadaRegistrada.v1 | event_id | string | Si | solicitudes-partner | identidad evento | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | tipo/version/instante | string/int/string | Si | solicitudes-partner | metadatos de evento | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | correlacion | string | Si | solicitudes-partner | correlacion == id_solicitud | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py |
| AtencionHabilitadaRegistrada.v1 | causacion | string | Si | solicitudes-partner | causacion == command_id recibido | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py |
| AtencionHabilitadaRegistrada.v1 | id_saga/id_solicitud/id_trabajo/id_partner | string | Si | solicitudes-partner | identidades de saga y negocio | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | extras reales | registrada_en | string | solicitudes-partner | instante de confirmacion | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | command_id | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| RegistrarAtencionCancelada.v1 | command_id | string | Si | orquestacion | identidad comando | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | tipo/version/instante | string/int/string | Si | orquestacion | metadatos de comando | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | correlacion | string | Si | orquestacion | correlation == request_id (validado en dominio entrada) | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py |
| RegistrarAtencionCancelada.v1 | causacion | string | Si | orquestacion | identidad causal previa | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | id_saga/id_solicitud/id_trabajo/id_partner | string | Si | orquestacion | identidades de saga y negocio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | extras reales | codigo_motivo, detalle | string,string | orquestacion | motivo de cancelacion | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | event_id | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Origen | Regla | Fuente |
|---|---|---|---|---|---|---|
| AtencionCanceladaRegistrada.v1 | event_id | string | Si | solicitudes-partner | identidad evento | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | tipo/version/instante | string/int/string | Si | solicitudes-partner | metadatos de evento | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | correlacion | string | Si | solicitudes-partner | correlacion == id_solicitud | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py |
| AtencionCanceladaRegistrada.v1 | causacion | string | Si | solicitudes-partner | causacion == command_id recibido | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py |
| AtencionCanceladaRegistrada.v1 | id_saga/id_solicitud/id_trabajo/id_partner | string | Si | solicitudes-partner | identidades de saga y negocio | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | extras reales | registrada_en | string | solicitudes-partner | instante de confirmacion | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | command_id | N/A | No existe | N/A | no definido en este contrato | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |

### 4.2 Contratos definidos solo en propuesta (sin Avro final en este repo)

Regla comun propuesta para estos mensajes:
- Base comun: tipo, version_contrato, instante, correlacion, causacion, id_saga, id_solicitud, id_trabajo, id_partner.
- Comandos: command_id.
- Eventos: event_id.
- Fuente: contratos-saga-propuesta.md (tabla de campos comunes y campos especificos).

Campos especificos definidos documentalmente:
- AbrirSeguimientoTrabajo.v1: id_cotizacion.
- SeguimientoTrabajoAbierto.v1: id_seguimiento, abierto_en.
- AperturaSeguimientoFallida.v1: codigo_motivo, detalle.
- CancelarSeguimientoTrabajo.v1: codigo_motivo, detalle.
- SeguimientoTrabajoCancelado.v1: id_seguimiento nullable, cancelado_en.
- AnularCotizacion.v1: id_peticion, id_cotizacion, codigo_motivo, detalle.
- CotizacionAnulada.v1: id_peticion, id_cotizacion, anulada_en.
- TrabajoCancelado.v1: codigo_motivo, detalle, cancelado_en, version_trabajo.

Observacion contractual:
- En estos contratos, los tipos Avro concretos y orden de campos aun no estan congelados en el workspace de Orquestacion.

## 5. Identidad y correlacion

Definiciones operativas:
- id_solicitud: identidad de negocio y correlacion transversal.
- id_saga: identidad tecnica de instancia Saga.
- id_trabajo: identidad del agregado Trabajo.
- event_id: identidad de evento.
- command_id: identidad de comando.
- causacion: enlace causal al mensaje previo.

Reglas validadas en fuentes:
- correlacion == id_solicitud:
  - definido en solicitud-partner (validacion de comando de atencion).
  - definido funcionalmente en cotizaciones para SolicitarCotizacion y resultados.
  - definido en propuesta de Saga para nuevos contratos.
- causacion == command_id emitido:
  - definido en serializacion de respuesta de solicitud-partner para Atencion*Registrada.
  - definido documentalmente en cotizaciones para Cotizacion* como respuesta al comando.
- evento.id_saga == saga.id_saga:
  - aplicable solo donde el contrato trae id_saga (Atencion* y contratos propuestos).
  - no aplicable en contratos actuales de cotizacion/solicitud porque no traen id_saga.
- evento.id_solicitud == saga.id_solicitud, evento.id_trabajo == saga.id_trabajo:
  - validable cuando el campo existe y saga ya tiene esos datos.

Comportamiento actual del coordinator frente a identidad:
- Resuelve por id_saga cuando viene.
- Si no viene id_saga, resuelve por id_solicitud.
- Si faltan ambos, no procesa ni crea log (no-op silencioso).
- Si hay inconsistencia de ids/correlacion, registra EVENT_RECEIVED + REJECTED_CONFLICT.

## 6. Happy Path (solo desde contratos)

| Paso | Entrada | Accion Orquestador | Salida | Servicio | Estado Saga | Paso Saga |
|---|---|---|---|---|---|---|
| 1 | SolicitudDePartnerListaParaAtencion.v1 | Crear Saga y crear Trabajo | TrabajoCreado.v1 + SolicitarCotizacion.v1 | seguimiento-trabajos + cotizaciones | RUNNING | SOLICITAR_COTIZACION |
| 2 | CotizacionRegistrada.v1 | Avanzar flujo de cotizacion exitosa | AbrirSeguimientoTrabajo.v1 | seguimiento-trabajos | RUNNING | ABRIR_SEGUIMIENTO |
| 3 | SeguimientoTrabajoAbierto.v1 | Confirmar apertura de seguimiento | RegistrarAtencionHabilitada.v1 | solicitudes-partner | RUNNING | REGISTRAR_ATENCION_HABILITADA |
| 4 | AtencionHabilitadaRegistrada.v1 | Cerrar saga por exito | N/A | N/A | COMPLETED | COMPLETAR_SAGA |

Puntos pendientes de definicion contractual operativa real:
- Confirmacion de Avro/topic final de AbrirSeguimientoTrabajo y SeguimientoTrabajoAbierto.
- Por ello, el tramo post-cotizacion hasta COMPLETED es PENDIENTE DE DEFINICION de integracion real, aunque esta definido conceptualmente en propuesta.

## 7. Cotizacion rechazada (compensacion)

| Paso | Evento | Accion | Comando/Operacion | Destino | Estado Saga |
|---|---|---|---|---|---|
| 1 | CotizacionRechazada.v1 | Cancelar Trabajo local | Operacion local + (propuesta) TrabajoCancelado.v1 | local + seguimiento-trabajos | RUNNING o COMPENSATING (decision pendiente) |
| 2 | CotizacionRechazada.v1 / TrabajoCancelado.v1 | Registrar cancelacion de atencion | RegistrarAtencionCancelada.v1 | solicitudes-partner | RUNNING o COMPENSATING (decision pendiente) |
| 3 | AtencionCanceladaRegistrada.v1 | Cierre de ruta compensada por rechazo | N/A | N/A | COMPENSATED (propuesta de diseno) |

Determinacion contractual:
- La propuesta explicita que NO se envia AnularCotizacion.v1 en esta rama.
- El salto exacto RUNNING -> COMPENSATING para este caso no esta completamente cerrado en todas las fuentes; se mantiene como decision de diseno pendiente.

## 8. Fallo de apertura de seguimiento

| Paso | Evento | Accion definida | Comando/Operacion | Destino | Estado |
|---|---|---|---|---|---|
| 1 | AperturaSeguimientoFallida.v1 | Iniciar compensacion | Cambio de estado | local | COMPENSATING |
| 2 | AperturaSeguimientoFallida.v1 | Compensar cotizacion | AnularCotizacion.v1 | cotizaciones | COMPENSATING |
| 3 | CotizacionAnulada.v1 | Continuar compensacion | Cancelar trabajo local + TrabajoCancelado.v1 | local + seguimiento-trabajos | COMPENSATING |
| 4 | TrabajoCancelado.v1 | Continuar compensacion | RegistrarAtencionCancelada.v1 | solicitudes-partner | COMPENSATING |
| 5 | AtencionCanceladaRegistrada.v1 | Condicional por bandera de apertura | CancelarSeguimientoTrabajo.v1 (si aplica) | seguimiento-trabajos | COMPENSATING |
| 6 | SeguimientoTrabajoCancelado.v1 o condicion satisfecha | Finalizar compensacion | N/A | N/A | COMPENSATED |

Determinacion:
- Esta secuencia esta definida en propuesta/diseno, pero depende de contratos Avro no congelados para mensajes de seguimiento y anulacion.

## 9. Estados

Estados validos unicos:
- RUNNING
- COMPENSATING
- COMPLETED
- COMPENSATED

| Estado Actual | Evento/Condicion | Accion | Estado Siguiente | Fuente |
|---|---|---|---|---|
| RUNNING | avance normal de pasos | continuar saga | RUNNING | 07-diseno-saga-steps.md |
| RUNNING | AtencionHabilitadaRegistrada.v1 | cierre exitoso | COMPLETED | contratos-saga-propuesta.md, coordinator actual |
| RUNNING | AperturaSeguimientoFallida.v1 | iniciar compensacion | COMPENSATING | 07-diseno-saga-steps.md |
| RUNNING | CotizacionRechazada.v1 | ruta compensada por rechazo | COMPENSATING o cierre compensado (pendiente) | 07-diseno-saga-steps.md |
| COMPENSATING | compensaciones confirmadas | finalizar compensacion | COMPENSATED | contratos-saga-propuesta.md |
| COMPLETED | evento posterior | no-op tardio | COMPLETED | coordinator actual |
| COMPENSATED | evento posterior | no-op tardio | COMPENSATED | coordinator actual |

## 10. SagaSteps

SagaStepName existentes en codigo:
- CREAR_TRABAJO
- SOLICITAR_COTIZACION
- ABRIR_SEGUIMIENTO
- REGISTRAR_ATENCION_HABILITADA
- COMPLETAR_SAGA
- CANCELAR_TRABAJO_POR_RECHAZO
- REGISTRAR_ATENCION_CANCELADA
- INICIAR_COMPENSACION_APERTURA
- CANCELAR_TRABAJO_COMPENSACION
- REGISTRAR_ATENCION_CANCELADA_COMPENSACION
- CANCELAR_SEGUIMIENTO_SI_APLICA
- FINALIZAR_COMPENSACION

Relacion contractual minima pedida:
- CREAR_TRABAJO <-> SolicitudDePartnerListaParaAtencion.v1
- SOLICITAR_COTIZACION <-> SolicitarCotizacion/Cotizacion*
- ABRIR_SEGUIMIENTO <-> AbrirSeguimientoTrabajo.v1
- REGISTRAR_ATENCION_HABILITADA <-> RegistrarAtencionHabilitada.v1
- COMPLETAR_SAGA <-> AtencionHabilitadaRegistrada.v1
- FINALIZAR_COMPENSACION <-> AtencionCanceladaRegistrada.v1 y/o SeguimientoTrabajoCancelado.v1

GAP de cobertura runtime actual:
- El coordinator implementado hoy no ejecuta aun pasos intermedios de seguimiento y anulacion definidos en propuesta.

## 11. Comportamiento esperado del Coordinator

| Evento recibido | Estado esperado | Paso esperado | Validaciones | Accion | Comando generado | Nuevo estado |
|---|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | RUNNING/inicio | CREAR_TRABAJO | identidad + dedupe + orden | crear/reusar trabajo y avanzar paso | SolicitarCotizacion.v1 | RUNNING |
| CotizacionRegistrada.v1 | RUNNING | SOLICITAR_COTIZACION | identidad + dedupe + orden | aplicar resultado y avanzar a ABRIR_SEGUIMIENTO | AbrirSeguimientoTrabajo.v1 | RUNNING |
| CotizacionRechazada.v1 | RUNNING | SOLICITAR_COTIZACION | identidad + dedupe + orden | aplicar rechazo y abrir ruta compensada por rechazo | RegistrarAtencionCancelada.v1 (sin AnularCotizacion) | RUNNING/COMPENSATING (pendiente) |
| SeguimientoTrabajoAbierto.v1 | RUNNING | ABRIR_SEGUIMIENTO | identidad + dedupe + orden | marcar apertura confirmada y avanzar | RegistrarAtencionHabilitada.v1 | RUNNING |
| AperturaSeguimientoFallida.v1 | RUNNING | ABRIR_SEGUIMIENTO | identidad + dedupe + orden | iniciar compensacion | AnularCotizacion.v1 | COMPENSATING |
| CotizacionAnulada.v1 | COMPENSATING | INICIAR_COMPENSACION_APERTURA | identidad + dedupe + orden | continuar compensacion | RegistrarAtencionCancelada.v1 | COMPENSATING |
| AtencionHabilitadaRegistrada.v1 | RUNNING | COMPLETAR_SAGA | identidad + dedupe + orden | cerrar saga | N/A | COMPLETED |
| AtencionCanceladaRegistrada.v1 | COMPENSATING o rama rechazo | FINALIZAR_COMPENSACION | identidad + dedupe + orden | cerrar compensacion o continuar condicional | CancelarSeguimientoTrabajo.v1 (si aplica) | COMPENSATING/COMPENSATED |
| Duplicado de cualquier evento | Cualquiera | Cualquiera | misma llave idempotencia | no-op | ninguno | sin cambio |
| Evento tardio (saga terminal) | COMPLETED/COMPENSATED | N/A | estado terminal | no-op tardio | ninguno | sin cambio |
| Evento fuera de orden | RUNNING/COMPENSATING | paso no habilitado | paso esperado no coincide | no-op fuera de orden | ninguno | sin cambio |
| Conflicto de identidad | Cualquiera | Cualquiera | ids/correlacion incompatibles | rechazo de conflicto | ninguno | sin cambio |
| Evento sin id_saga y sin id_solicitud | Cualquiera | Cualquiera | no se puede resolver saga | no-op silencioso (estado actual de codigo) | ninguno | sin cambio |

## 12. Idempotencia

Diseno actual en persistencia Saga:
- llave: id_saga + tipo_mensaje + coalesce(event_id, command_id)
- indice unico: uq_saga_log_idempotencia
- lookup de dedupe: buscar_por_message_id por event_id o command_id

| Evento | message_id | Dedupe | Primera vez | Duplicado | Resultado SagaLog |
|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | event_id | Si | aplica transicion inicial | no-op | DUPLICATE + NO_OP_DUPLICATE |
| CotizacionRegistrada.v1 | event_id | Si | aplica transicion de cotizacion | no-op | DUPLICATE + NO_OP_DUPLICATE |
| CotizacionRechazada.v1 | event_id | Si | aplica ruta de rechazo | no-op | DUPLICATE + NO_OP_DUPLICATE |
| AtencionHabilitadaRegistrada.v1 | event_id | Si | aplica cierre exitoso | no-op | DUPLICATE + NO_OP_DUPLICATE |
| AtencionCanceladaRegistrada.v1 | event_id | Si | aplica cierre compensado | no-op | DUPLICATE + NO_OP_DUPLICATE |
| (propuesto) SeguimientoTrabajoAbierto.v1 | event_id | Si | aplica avance de seguimiento | no-op | DUPLICATE + NO_OP_DUPLICATE |
| (propuesto) AperturaSeguimientoFallida.v1 | event_id | Si | aplica inicio compensacion | no-op | DUPLICATE + NO_OP_DUPLICATE |
| (propuesto) CotizacionAnulada.v1 | event_id | Si | aplica avance compensacion | no-op | DUPLICATE + NO_OP_DUPLICATE |
| (propuesto) SeguimientoTrabajoCancelado.v1 | event_id | Si | aplica cierre compensacion | no-op | DUPLICATE + NO_OP_DUPLICATE |

Representacion de conflicto en modelo actual:
- EVENT_RECEIVED + REJECTED_CONFLICT.
- No existe SagaLogTipoRegistro.CONFLICT en enum ni en constraint de BD.

## 13. Dependencias

| Servicio | Contratos conocidos | Informacion necesaria | Informacion interna irrelevante |
|---|---|---|---|
| solicitudes-partner | SolicitudDePartnerListaParaAtencion.v1, RegistrarAtencionHabilitada.v1, AtencionHabilitadaRegistrada.v1, RegistrarAtencionCancelada.v1, AtencionCanceladaRegistrada.v1 | schema Avro, topicos, semantica de correlacion/causacion, ids requeridos | tablas, aggregate internos, handlers internos, endpoints internos no contractuales |
| cotizaciones | SolicitarCotizacion.v1, CotizacionRegistrada.v1, CotizacionRechazada.v1, (propuesto) AnularCotizacion.v1, CotizacionAnulada.v1 | schema Avro, topicos, reglas de causacion/correlacion, semantica de anulacion | modelo interno de pricing, persistencia interna, API interna |
| seguimiento-trabajos | TrabajoCreado.v1, CotizacionRegistrada.v1, CotizacionRechazada.v1, (propuesto) AbrirSeguimientoTrabajo.v1, SeguimientoTrabajoAbierto.v1, AperturaSeguimientoFallida.v1, CancelarSeguimientoTrabajo.v1, SeguimientoTrabajoCancelado.v1, TrabajoCancelado.v1 | schema Avro y semantica de eventos/confirmaciones | tablas internas de seguimiento, endpoints internos, decisiones internas de proyeccion |

Principio aplicado:
- Orquestacion depende de contratos, no de implementaciones internas.

## 14. Gaps

| GAP | Impacto | Bloquea Coordinator? | Bloquea pruebas? | Responsable | Decision requerida | Clasificacion |
|---|---|---|---|---|---|---|
| No hay Avro congelado de AbrirSeguimientoTrabajo.v1 | no se puede integrar realmente el paso post-cotizacion | No (logica base si) | Si para E2E real | orquestacion + seguimiento | schema final y topic final | DEPENDENCIA EXTERNA |
| No hay Avro de SeguimientoTrabajoAbierto/AperturaSeguimientoFallida | no se puede cerrar happy path completo ni iniciar compensacion por fallo de apertura en runtime real | Parcial | Si E2E | seguimiento + orquestacion | contrato final | DEPENDENCIA EXTERNA |
| No hay Avro de CancelarSeguimientoTrabajo/SeguimientoTrabajoCancelado | no se puede cerrar compensacion completa con seguimiento | Parcial | Si E2E | seguimiento + orquestacion | contrato final y regla condicional | DEPENDENCIA EXTERNA |
| No hay Avro de AnularCotizacion/CotizacionAnulada | no se puede ejecutar compensacion por fallo de apertura contra cotizaciones | Parcial | Si E2E | cotizaciones + orquestacion | contrato final de anulacion | DEPENDENCIA EXTERNA |
| No hay Avro de TrabajoCancelado.v1 | no se puede publicar contrato de cancelacion de trabajo a seguimiento en forma final | No para coordinator base | Si E2E compensacion | orquestacion + seguimiento | contrato final | DEPENDENCIA EXTERNA |
| Rama exacta de estado para CotizacionRechazada (RUNNING->COMPENSATING o cierre alterno) | ambiguedad en transicion de estado | Si (para cerrar FASE 2 sin ambiguedad) | Si (tests de estado definitivo) | equipo saga | decision de diseno de estado | DECISION DE DISENO |
| Mensaje sin id_saga/id_solicitud queda no-op silencioso | observabilidad incompleta en errores de entrada | No | No | orquestacion | definir si debe quedar log tecnico | NO BLOQUEANTE |
| correlacion==id_solicitud en contratos de cotizaciones no esta expresado en Avro (si en reglas funcionales) | riesgo de divergencia entre productores/consumidores | No inmediato | Potencial en pruebas de conformidad futuras | cotizaciones/orquestacion | documentar como regla contractual dura | DECISION DE DISENO |
| Seguimiento-trabajos declara schemas provisionales locales | posible desalineacion con owner final | No para coordinator base | Si para integracion cruzada | seguimiento-trabajos | reemplazar por export owner final | DEPENDENCIA EXTERNA |

## 15. Comparacion contra implementacion actual

| Comportamiento esperado | Implementado | Falta | Diferencia | Accion |
|---|---|---|---|---|
| Resolver saga por id_saga o id_solicitud | Si | No | sin diferencia relevante | mantener |
| Detectar conflictos de identidad | Si | No | usa EVENT_RECEIVED + REJECTED_CONFLICT | mantener (modelo vigente) |
| Manejar duplicados/tardios/fuera de orden | Si | No | clasificacion completa para eventos actuales | mantener |
| Crear saga y generar SolicitarCotizacion desde evento inicial | Si | No | ya en runtime | mantener |
| Procesar CotizacionRegistrada | Parcial | Si | avanza paso a ABRIR_SEGUIMIENTO pero no emite AbrirSeguimientoTrabajo real | implementar cuando contrato este congelado |
| Procesar CotizacionRechazada | Parcial | Si | deja ruta pendiente y no define cierre final | decision de diseno + implementacion |
| Procesar AtencionHabilitadaRegistrada | Si | No | cierre a COMPLETED implementado | mantener |
| Procesar AtencionCanceladaRegistrada | Si | Parcial | cierre a COMPENSATED implementado, pero ruta completa previa depende de contratos faltantes | completar despues de contratos |
| Compensacion por AperturaSeguimientoFallida | No | Si | no hay consumidores/contratos/runtime para ese tramo | depende de contratos seguimiento/cotizaciones |
| Soporte de AnularCotizacion/CotizacionAnulada | No | Si | no existe en rutas/destinos actuales | depende de contrato y wiring |
| Soporte de CancelarSeguimiento/SeguimientoTrabajoCancelado | No | Si | no existe en rutas/destinos actuales | depende de contrato y wiring |
| Publicacion de TrabajoCancelado.v1 | No (contractual) | Si | no existe destino/schema final | depende de contrato |

## 16. Decisiones pendientes

1. Definir de forma final la transicion de estado en ruta CotizacionRechazada.
2. Congelar contratos Avro/topic de los 8 mensajes pendientes de seguimiento/compensacion.
3. Confirmar formalmente reglas de correlacion y causacion en todos los contratos (incluyendo cotizaciones).
4. Definir politica de trazabilidad para mensaje sin identificadores (mantener no-op silencioso o registrar log tecnico).
5. Confirmar lectura oficial del PDF hda-entrega5-propuesta-saga-bff contra el contrato MD para eliminar ambiguedad documental.

## 17. Conclusion

La base de FASE 1 deja listo el coordinator para avanzar en FASE 2 sobre eventos actuales, pero la implementacion completa del flujo Saga contractual (happy path extendido y compensaciones completas) depende de contratos pendientes de seguimiento y anulacion de cotizacion.

No se requiere modificar estados ni SagaStepName para continuar; la brecha principal es contractual/integracion, no de modelo base.

### YA IMPLEMENTADO

- Persistencia de SagaInstance y SagaLog.
- Resolucion de saga por id_saga/id_solicitud.
- Validaciones de duplicate, late, out_of_order y conflicto de identidad.
- Ruta inicial SolicitudDePartnerListaParaAtencion -> crear trabajo -> SolicitarCotizacion.
- Manejo de CotizacionRegistrada/CotizacionRechazada en estado/paso actual.
- Cierre por AtencionHabilitadaRegistrada y AtencionCanceladaRegistrada.
- Idempotencia por id_saga + tipo_mensaje + coalesce(event_id, command_id).

### PUEDE IMPLEMENTARSE AHORA

- Fortalecer tests de conformidad contractual para mensajes ya disponibles.
- Preparar handlers/coordinator para ramas adicionales usando contratos ya definidos en propuesta (sin activar integracion real) si el equipo lo aprueba.
- Documentar reglas estrictas de correlacion/causacion por mensaje en pruebas de contrato.

### DEPENDE DE CONTRATOS

- AbrirSeguimientoTrabajo.v1
- SeguimientoTrabajoAbierto.v1
- AperturaSeguimientoFallida.v1
- CancelarSeguimientoTrabajo.v1
- SeguimientoTrabajoCancelado.v1
- AnularCotizacion.v1
- CotizacionAnulada.v1
- TrabajoCancelado.v1

### DEPENDE DE COTIZACIONES

- Implementacion y contrato final de AnularCotizacion.v1/CotizacionAnulada.v1.
- Confirmacion de reglas de causacion/correlacion en anulacion.

### DEPENDE DE SEGUIMIENTO

- Implementacion y contrato final de apertura/cancelacion de seguimiento.
- Confirmacion de semantica de SeguimientoTrabajoCancelado cuando no hubo id_seguimiento previo.

### DECISIONES DEL EQUIPO

- Ruta de estado definitiva para CotizacionRechazada.
- Politica de trazabilidad para eventos sin identificadores.
- Cierre de ambiguedad documental entre propuesta MD y PDF.

### RECOMENDACION PARA LA SIGUIENTE FASE

Congelar primero los contratos pendientes (Avro + topics + ownership + reglas de correlacion/causacion), y solo despues implementar en coordinator las ramas de seguimiento y compensacion faltantes para evitar retrabajo y divergencia entre servicios.
