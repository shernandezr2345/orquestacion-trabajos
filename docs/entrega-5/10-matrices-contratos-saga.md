# ANALISIS DE CONTRATOS E INTEGRACION - ENTREGA 5

## 1. Objetivo

Definir una fuente unica de verdad para implementar el SagaCoordinator de orquestacion-trabajos sin inventar informacion, usando solo contratos y documentos existentes.

Este documento NO implementa SagaCoordinator. Solo consolida matrices de contratos, correlacion, validaciones y transiciones para:
- Happy Path
- Compensaciones
- Idempotencia
- Integracion futura con cotizaciones
- Integracion futura con seguimiento-trabajos

## 2. Fuentes utilizadas

Fuentes principales (definicion de Saga y contratos):
- orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md
- contratos-saga-propuesta.md
- orquestacion-trabajos/docs/entrega-5/07-diseno-saga-steps.md
- orquestacion-trabajos/docs/entrega-5/08-diseno-persistencia-saga.md
- orquestacion-trabajos/docs/entrega-5/09-implementacion-persistencia-saga.md

Contratos Avro existentes (implementados hoy):
- orquestacion-trabajos/docs/contratos/solicitud-lista-v1.avsc
- orquestacion-trabajos/docs/contratos/trabajo-creado-v1.avsc
- orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc
- orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc
- orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc
- solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc
- solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc
- solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc
- solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc
- solicitud-partner/docs/contratos/solicitud-lista-v1.avsc

Implementacion actual relevante:
- orquestacion-trabajos/src/orquestacion_trabajos/config/bootstrap.py
- orquestacion-trabajos/src/orquestacion_trabajos/config/rutas.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/sagas/dominio/entidades.py
- solicitud-partner/src/solicitudes_partner/config/bootstrap.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/comandos.py
- solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/esquemas/v1/eventos.py

Observacion sobre PDF solicitado como fuente:
- orquestacion-trabajos/docs/entrega-5/hda-entrega5-propuesta-saga-bff.pdf
- Estado de uso: NO DEFINIDO EN LOS CONTRATOS ACTUALES (no se extrajo texto estructurado en este analisis; se usaron fuentes MD como base contractual).

## 3. Convenciones

- DEFINIDO: aparece explicitamente en contratos/documentos citados.
- INFERIDO: se deduce del flujo acordado, pero no esta formalizado como schema implementado.
- NO DEFINIDO EN LOS CONTRATOS ACTUALES: no hay informacion contractual suficiente.

Reglas metodologicas aplicadas:
- No se asumio implementacion interna de cotizaciones ni seguimiento-trabajos.
- No se inventaron payloads fuera de contrato.
- Se separa contrato propuesto de contrato implementado.

## 4. Matriz de inventario de mensajes

| # | Mensaje | Tipo | Version | Productor | Consumidor | Direccion | Momento del flujo | Correlacion | Estado de Saga relacionado | Fuente |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SolicitudDePartnerListaParaAtencion.v1 | Event | v1 | solicitudes-partner | orquestacion-trabajos | Entrada -> Orquestacion | Inicio de saga | correlacion=id_solicitud (DEFINIDO en implementacion de solicitud-partner) | RUNNING | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc; solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py |
| 2 | TrabajoCreado.v1 | Event | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Despues de crear trabajo | correlacion=id_solicitud (DEFINIDO por contrato avro) | RUNNING | orquestacion-trabajos/docs/contratos/trabajo-creado-v1.avsc |
| 3 | SolicitarCotizacion.v1 | Command | v1 | orquestacion-trabajos | cotizaciones | Orquestacion -> Cotizaciones | Paso solicitar cotizacion | correlacion=id_solicitud (DEFINIDO por contrato avro) | RUNNING | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| 4 | CotizacionRegistrada.v1 | Event | v1 | cotizaciones | orquestacion-trabajos y seguimiento-trabajos | Cotizaciones -> Orquestacion/Seguimiento | Exito de cotizacion | correlacion (DEFINIDO); igualdad con id_solicitud INFERIDO por convencion | RUNNING | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc; orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 5 | CotizacionRechazada.v1 | Event | v1 | cotizaciones | orquestacion-trabajos y seguimiento-trabajos | Cotizaciones -> Orquestacion/Seguimiento | Falla de cotizacion | correlacion (DEFINIDO); igualdad con id_solicitud INFERIDO por convencion | RUNNING -> COMPENSATING o cierre compensado (decision pendiente) | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc; orquestacion-trabajos/docs/entrega-5/07-diseno-saga-steps.md |
| 6 | AbrirSeguimientoTrabajo.v1 | Command | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Tras CotizacionRegistrada | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | RUNNING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 7 | SeguimientoTrabajoAbierto.v1 | Event | v1 | seguimiento-trabajos | orquestacion-trabajos | Seguimiento -> Orquestacion | Exito apertura seguimiento | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | RUNNING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 8 | AperturaSeguimientoFallida.v1 | Event | v1 | seguimiento-trabajos | orquestacion-trabajos | Seguimiento -> Orquestacion | Falla apertura seguimiento | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | RUNNING -> COMPENSATING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md; orquestacion-trabajos/docs/entrega-5/07-diseno-saga-steps.md |
| 9 | CancelarSeguimientoTrabajo.v1 | Command | v1 | orquestacion-trabajos | seguimiento-trabajos | Orquestacion -> Seguimiento | Compensacion | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | COMPENSATING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 10 | SeguimientoTrabajoCancelado.v1 | Event | v1 | seguimiento-trabajos | orquestacion-trabajos | Seguimiento -> Orquestacion | Confirmacion compensacion seguimiento | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | COMPENSATING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 11 | AnularCotizacion.v1 | Command | v1 | orquestacion-trabajos | cotizaciones | Orquestacion -> Cotizaciones | Compensacion por AperturaSeguimientoFallida | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | COMPENSATING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 12 | CotizacionAnulada.v1 | Event | v1 | cotizaciones | orquestacion-trabajos | Cotizaciones -> Orquestacion | Confirmacion anulacion | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | COMPENSATING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 13 | TrabajoCancelado.v1 | Event | v1 | orquestacion-trabajos | seguimiento-trabajos y potencialmente orquestacion (logica local) | Orquestacion -> Seguimiento | Compensacion de trabajo | correlacion=id_solicitud (DEFINIDO en propuesta, no en avro implementado) | COMPENSATING | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| 14 | RegistrarAtencionHabilitada.v1 | Command | v1 | orquestacion-trabajos | solicitudes-partner | Orquestacion -> Entrada | Tras SeguimientoTrabajoAbierto | correlacion=id_solicitud (DEFINIDO en contrato implementado) | RUNNING | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| 15 | AtencionHabilitadaRegistrada.v1 | Event | v1 | solicitudes-partner | orquestacion-trabajos | Entrada -> Orquestacion | Confirmacion atencion habilitada | correlacion=id_solicitud (DEFINIDO en contrato implementado) | COMPLETED | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| 16 | RegistrarAtencionCancelada.v1 | Command | v1 | orquestacion-trabajos | solicitudes-partner | Orquestacion -> Entrada | Compensacion | correlacion=id_solicitud (DEFINIDO en contrato implementado) | COMPENSATING | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| 17 | AtencionCanceladaRegistrada.v1 | Event | v1 | solicitudes-partner | orquestacion-trabajos | Entrada -> Orquestacion | Confirmacion atencion cancelada | correlacion=id_solicitud (DEFINIDO en contrato implementado) | COMPENSATED | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |

Notas de estado de implementacion:
- Implementados hoy en codigo/avro: 1,2,3,4,5,14,15,16,17.
- Definidos en propuesta pero NO implementados en avro dentro del workspace: 6,7,8,9,10,11,12,13.

## 5. Matriz de campos

### 5.1 Mensajes con contrato Avro implementado

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | event_id | string | SI | identidad del evento | solicitudes-partner | UUID textual | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | tipo | string | SI | tipo contractual | solicitudes-partner | valor esperado SolicitudDePartnerListaParaAtencion.v1 | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | version_contrato | int | SI | version del schema | solicitudes-partner | 1 | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | instante | string | SI | timestamp de evento | solicitudes-partner | formato fecha/hora en texto | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | correlacion | string | SI | correlacion de negocio | solicitudes-partner | correlacion=id_solicitud (DEFINIDO en implementacion) | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/mapeadores_eventos.py |
| SolicitudDePartnerListaParaAtencion.v1 | id_solicitud | string | SI | identidad de solicitud | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_partner | string | SI | identidad de partner | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_saga | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | id_trabajo | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | causacion | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |
| SolicitudDePartnerListaParaAtencion.v1 | command_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/solicitud-lista-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| SolicitarCotizacion.v1 | command_id | string | SI | identidad del comando | orquestacion | UUID textual | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | tipo | string | SI | tipo contractual | orquestacion | default contractual SolicitarCotizacion.v1 | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | version_contrato | int | SI | version schema | orquestacion | default 1 | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | instante | string | SI | tiempo comando | orquestacion | formato fecha/hora en texto | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | correlacion | string | SI | correlacion negocio | orquestacion | INFERIDO: id_solicitud | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc; orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SolicitarCotizacion.v1 | causacion | string | SI | relacion causal | orquestacion | debe apuntar al evento previo | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_trabajo | string | SI | identidad trabajo | orquestacion | no vacio | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_solicitud | string | SI | identidad solicitud | orquestacion | no vacio | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_partner | string | SI | identidad partner | orquestacion | no vacio | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | id_saga | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |
| SolicitarCotizacion.v1 | event_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | orquestacion-trabajos/docs/contratos/solicitar-cotizacion-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| CotizacionRegistrada.v1 | event_id | string | SI | identidad evento | cotizaciones | UUID textual | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | tipo | string | SI | tipo contractual | cotizaciones | valor contractual esperado | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | version_contrato | int | SI | version schema | cotizaciones | valor de contrato vigente | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | instante | string | SI | tiempo evento | cotizaciones | formato fecha/hora en texto | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | correlacion | string | SI | correlacion negocio | cotizaciones | INFERIDO: id_solicitud | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc; orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionRegistrada.v1 | causacion | string | SI | causalidad | cotizaciones | debe apuntar a command_id de SolicitarCotizacion.v1 | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_trabajo | string | SI | identidad trabajo | cotizaciones | no vacio | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_solicitud | string | SI | identidad solicitud | cotizaciones | no vacio | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_partner | string | SI | identidad partner | cotizaciones | no vacio | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | id_saga | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |
| CotizacionRegistrada.v1 | command_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | orquestacion-trabajos/docs/contratos/cotizacion-registrada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| CotizacionRechazada.v1 | event_id | string | SI | identidad evento | cotizaciones | UUID textual | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | tipo | string | SI | tipo contractual | cotizaciones | valor contractual esperado | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | version_contrato | int | SI | version schema | cotizaciones | valor de contrato vigente | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | instante | string | SI | tiempo evento | cotizaciones | formato fecha/hora en texto | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | correlacion | string | SI | correlacion negocio | cotizaciones | INFERIDO: id_solicitud | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc; orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionRechazada.v1 | causacion | string | SI | causalidad | cotizaciones | debe apuntar a command_id de SolicitarCotizacion.v1 | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_trabajo | string | SI | identidad trabajo | cotizaciones | no vacio | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_solicitud | string | SI | identidad solicitud | cotizaciones | no vacio | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_partner | string | SI | identidad partner | cotizaciones | no vacio | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | id_saga | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |
| CotizacionRechazada.v1 | command_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | orquestacion-trabajos/docs/contratos/cotizacion-rechazada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| RegistrarAtencionHabilitada.v1 | command_id | string | SI | identidad comando | orquestacion | UUID textual | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | tipo | string | SI | tipo contractual | orquestacion | valor esperado RegistrarAtencionHabilitada.v1 | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | version_contrato | int | SI | version schema | orquestacion | 1 | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | instante | string | SI | tiempo comando | orquestacion | formato fecha/hora en texto | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | correlacion | string | SI | correlacion de negocio | orquestacion | correlacion=id_solicitud (DEFINIDO en validacion del consumidor) | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py |
| RegistrarAtencionHabilitada.v1 | causacion | string | SI | causalidad | orquestacion | debe apuntar al evento/accion anterior en saga | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | id_saga | string | SI | identidad saga | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | id_solicitud | string | SI | identidad solicitud | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | id_trabajo | string | SI | identidad trabajo | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | id_partner | string | SI | identidad partner | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |
| RegistrarAtencionHabilitada.v1 | event_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/registrar-atencion-habilitada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| AtencionHabilitadaRegistrada.v1 | event_id | string | SI | identidad evento | solicitudes-partner | UUID textual | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | tipo | string | SI | tipo contractual | solicitudes-partner | AtencionHabilitadaRegistrada.v1 | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | version_contrato | int | SI | version schema | solicitudes-partner | 1 | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | instante | string | SI | tiempo evento | solicitudes-partner | formato fecha/hora en texto | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | correlacion | string | SI | correlacion negocio | solicitudes-partner | correlacion=id_solicitud (INFERIDO por contrato y flujo) | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | causacion | string | SI | causalidad | solicitudes-partner | command_id de RegistrarAtencionHabilitada.v1 | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py |
| AtencionHabilitadaRegistrada.v1 | id_saga | string | SI | identidad saga | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | id_solicitud | string | SI | identidad solicitud | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | id_trabajo | string | SI | identidad trabajo | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | id_partner | string | SI | identidad partner | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |
| AtencionHabilitadaRegistrada.v1 | command_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/atencion-habilitada-registrada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| RegistrarAtencionCancelada.v1 | command_id | string | SI | identidad comando | orquestacion | UUID textual | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | tipo | string | SI | tipo contractual | orquestacion | valor esperado RegistrarAtencionCancelada.v1 | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | version_contrato | int | SI | version schema | orquestacion | 1 | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | instante | string | SI | tiempo comando | orquestacion | formato fecha/hora en texto | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | correlacion | string | SI | correlacion de negocio | orquestacion | correlacion=id_solicitud (DEFINIDO en validacion del consumidor) | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/aplicacion/comandos.py |
| RegistrarAtencionCancelada.v1 | causacion | string | SI | causalidad | orquestacion | debe apuntar al evento/accion anterior en saga | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | id_saga | string | SI | identidad saga | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | id_solicitud | string | SI | identidad solicitud | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | id_trabajo | string | SI | identidad trabajo | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | id_partner | string | SI | identidad partner | orquestacion | no vacio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | codigo_motivo | string | SI | motivo de cancelacion | orquestacion | texto no vacio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | detalle | string | SI | detalle de cancelacion | orquestacion | texto no vacio | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |
| RegistrarAtencionCancelada.v1 | event_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/registrar-atencion-cancelada-v1.avsc |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| AtencionCanceladaRegistrada.v1 | event_id | string | SI | identidad evento | solicitudes-partner | UUID textual | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | tipo | string | SI | tipo contractual | solicitudes-partner | AtencionCanceladaRegistrada.v1 | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | version_contrato | int | SI | version schema | solicitudes-partner | 1 | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | instante | string | SI | tiempo evento | solicitudes-partner | formato fecha/hora en texto | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | correlacion | string | SI | correlacion negocio | solicitudes-partner | correlacion=id_solicitud (INFERIDO por contrato y flujo) | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | causacion | string | SI | causalidad | solicitudes-partner | command_id de RegistrarAtencionCancelada.v1 | solicitud-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/serializacion.py |
| AtencionCanceladaRegistrada.v1 | id_saga | string | SI | identidad saga | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | id_solicitud | string | SI | identidad solicitud | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | id_trabajo | string | SI | identidad trabajo | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | id_partner | string | SI | identidad partner | solicitudes-partner | no vacio | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |
| AtencionCanceladaRegistrada.v1 | command_id | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | solicitud-partner/docs/contratos/atencion-cancelada-registrada-v1.avsc |

### 5.2 Mensajes de Saga definidos en propuesta (sin Avro implementado en workspace)

Para estos mensajes, solo se declaran campos definidos en propuesta.

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| AbrirSeguimientoTrabajo.v1 | command_id o event_id | UUID textual | SI | identidad de mensaje | orquestacion | comandos usan command_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | tipo | string | SI | tipo contractual | orquestacion | AbrirSeguimientoTrabajo.v1 | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | version_contrato | int | SI | version schema | orquestacion | 1 | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | instante | string | SI | instante original | orquestacion | UTC textual | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | correlacion | string | SI | correlacion de negocio | orquestacion | id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | causacion | string | SI | causalidad | orquestacion | id mensaje previo | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | id_saga | string | SI | identidad saga | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | id_solicitud | string | SI | identidad solicitud | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | id_trabajo | string | SI | identidad trabajo | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | id_partner | string | SI | identidad partner | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | id_cotizacion | string | SI | cotizacion a abrir en seguimiento | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AbrirSeguimientoTrabajo.v1 | tipo exacto Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| SeguimientoTrabajoAbierto.v1 | event_id | UUID textual | SI | identidad evento | seguimiento | eventos usan event_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoAbierto.v1 | campos comunes (tipo,version_contrato,instante,correlacion,causacion,id_saga,id_solicitud,id_trabajo,id_partner) | segun propuesta | SI | trazabilidad | seguimiento | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoAbierto.v1 | id_seguimiento | string | SI | identidad seguimiento | seguimiento | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoAbierto.v1 | abierto_en | string | SI | instante de apertura | seguimiento | timestamp textual | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoAbierto.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| AperturaSeguimientoFallida.v1 | event_id | UUID textual | SI | identidad evento | seguimiento | eventos usan event_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AperturaSeguimientoFallida.v1 | campos comunes | segun propuesta | SI | trazabilidad | seguimiento | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AperturaSeguimientoFallida.v1 | codigo_motivo | string | SI | causa de fallo | seguimiento | texto no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AperturaSeguimientoFallida.v1 | detalle | string | SI | detalle de fallo | seguimiento | texto | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AperturaSeguimientoFallida.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| CancelarSeguimientoTrabajo.v1 | command_id | UUID textual | SI | identidad comando | orquestacion | comandos usan command_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CancelarSeguimientoTrabajo.v1 | campos comunes | segun propuesta | SI | trazabilidad | orquestacion | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CancelarSeguimientoTrabajo.v1 | codigo_motivo | string | SI | motivo de cancelacion | orquestacion | texto no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CancelarSeguimientoTrabajo.v1 | detalle | string | SI | detalle | orquestacion | texto | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CancelarSeguimientoTrabajo.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| SeguimientoTrabajoCancelado.v1 | event_id | UUID textual | SI | identidad evento | seguimiento | eventos usan event_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoCancelado.v1 | campos comunes | segun propuesta | SI | trazabilidad | seguimiento | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoCancelado.v1 | id_seguimiento | string nullable | NO | referencia seguimiento | seguimiento | puede ser null | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoCancelado.v1 | cancelado_en | string | SI | instante de cancelacion | seguimiento | timestamp textual | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| SeguimientoTrabajoCancelado.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| AnularCotizacion.v1 | command_id | UUID textual | SI | identidad comando | orquestacion | comandos usan command_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AnularCotizacion.v1 | campos comunes | segun propuesta | SI | trazabilidad | orquestacion | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AnularCotizacion.v1 | id_peticion | string | SI | peticion de cotizacion original | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AnularCotizacion.v1 | id_cotizacion | string | SI | cotizacion a anular | orquestacion | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AnularCotizacion.v1 | codigo_motivo | string | SI | motivo de anulacion | orquestacion | texto no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AnularCotizacion.v1 | detalle | string | SI | detalle | orquestacion | texto | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| AnularCotizacion.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| CotizacionAnulada.v1 | event_id | UUID textual | SI | identidad evento | cotizaciones | eventos usan event_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionAnulada.v1 | campos comunes | segun propuesta | SI | trazabilidad | cotizaciones | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionAnulada.v1 | id_peticion | string | SI | peticion asociada | cotizaciones | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionAnulada.v1 | id_cotizacion | string | SI | cotizacion anulada | cotizaciones | no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionAnulada.v1 | anulada_en | string | SI | instante anulacion | cotizaciones | timestamp textual | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| CotizacionAnulada.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

| Mensaje | Campo | Tipo | Obligatorio | Proposito | Valor/origen | Regla de validacion | Fuente |
|---|---|---|---|---|---|---|---|
| TrabajoCancelado.v1 | event_id | UUID textual | SI | identidad evento | orquestacion | eventos usan event_id | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| TrabajoCancelado.v1 | campos comunes | segun propuesta | SI | trazabilidad | orquestacion | correlacion=id_solicitud | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| TrabajoCancelado.v1 | codigo_motivo | string | SI | motivo de cancelacion | orquestacion | texto no vacio | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| TrabajoCancelado.v1 | detalle | string | SI | detalle | orquestacion | texto | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| TrabajoCancelado.v1 | cancelado_en | string | SI | instante de cancelacion | orquestacion | timestamp textual | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| TrabajoCancelado.v1 | version_trabajo | int | SI | version de agregado trabajo | orquestacion | entero positivo | orquestacion-trabajos/docs/entrega-5/contratos-saga-propuesta.md |
| TrabajoCancelado.v1 | tipos exactos Avro | N/A | N/A | N/A | N/A | NO DEFINIDO EN LOS CONTRATOS ACTUALES | N/A |

## 6. Happy Path

| Paso | Evento recibido | Accion del Orquestador | Comando emitido | Servicio destino | Resultado esperado | Nuevo paso Saga | Estado Saga |
|---|---|---|---|---|---|---|---|
| 1 | SolicitudDePartnerListaParaAtencion.v1 | Crear SagaInstance e iniciar flujo | Operacion local crear trabajo | orquestacion (local) | Trabajo creado | SOLICITAR_COTIZACION | RUNNING |
| 2 | TrabajoCreado.v1 (interno de flujo) | Continuar coordinacion | SolicitarCotizacion.v1 | cotizaciones | Cotizacion en proceso | ABRIR_SEGUIMIENTO | RUNNING |
| 3 | CotizacionRegistrada.v1 | Avanzar saga | AbrirSeguimientoTrabajo.v1 | seguimiento-trabajos | Apertura solicitada | REGISTRAR_ATENCION_HABILITADA | RUNNING |
| 4 | SeguimientoTrabajoAbierto.v1 | Avanzar saga | RegistrarAtencionHabilitada.v1 | solicitudes-partner | Registro de atencion habilitada solicitado | COMPLETAR_SAGA | RUNNING |
| 5 | AtencionHabilitadaRegistrada.v1 | Cerrar saga por exito | N/A | N/A | Saga completada | FIN | COMPLETED |

Notas:
- Paso 2 usa TrabajoCreado.v1 como parte del pipeline actual de orquestacion; el flujo exacto de disparo del coordinador es INFERIDO porque SagaCoordinator aun no existe.
- La secuencia objetivo coincide con orquestacion-trabajos/docs/entrega-5/07-diseno-saga-steps.md.

## 7. Compensacion Cotizacion Rechazada

| Paso | Evento | Accion Orquestador | Comando/Operacion | Destino | Resultado esperado | Estado Saga |
|---|---|---|---|---|---|---|
| A1 | CotizacionRechazada.v1 | Iniciar ruta de cierre compensado | Operacion local cancelar trabajo | orquestacion (local) | Trabajo en estado cancelado | RUNNING o COMPENSATING (decision pendiente) |
| A2 | CotizacionRechazada.v1 (continuacion) | Publicar hecho de cancelacion de trabajo | TrabajoCancelado.v1 | seguimiento-trabajos | Proyeccion de seguimiento actualizada | RUNNING o COMPENSATING (decision pendiente) |
| A3 | TrabajoCancelado.v1 o estado local cancelado | Solicitar cancelacion de atencion | RegistrarAtencionCancelada.v1 | solicitudes-partner | Cancelacion de atencion solicitada | RUNNING o COMPENSATING (decision pendiente) |
| A4 | AtencionCanceladaRegistrada.v1 | Cerrar compensacion | N/A | N/A | Saga cerrada compensada | COMPENSATED |

Regla explicitada en diseno:
- No enviar AnularCotizacion.v1 en este escenario.
- Fuente: orquestacion-trabajos/docs/entrega-5/07-diseno-saga-steps.md.

## 8. Compensacion Fallo Seguimiento

| Paso | Evento | Accion Orquestador | Comando/Operacion | Destino | Resultado esperado | Estado Saga |
|---|---|---|---|---|---|---|
| B1 | AperturaSeguimientoFallida.v1 | Iniciar compensacion | Cambiar estado de saga | orquestacion (local) | Saga en compensacion | COMPENSATING |
| B2 | AperturaSeguimientoFallida.v1 | Compensar cotizacion | AnularCotizacion.v1 | cotizaciones | Solicitud de anulacion enviada | COMPENSATING |
| B3 | CotizacionAnulada.v1 | Continuar compensacion | Operacion local cancelar trabajo + publicar TrabajoCancelado.v1 | orquestacion local + seguimiento-trabajos | Trabajo cancelado publicado | COMPENSATING |
| B4 | TrabajoCancelado.v1 | Continuar compensacion | RegistrarAtencionCancelada.v1 | solicitudes-partner | Cancelacion de atencion solicitada | COMPENSATING |
| B5 | AtencionCanceladaRegistrada.v1 | Condicional segun bandera de seguimiento | CancelarSeguimientoTrabajo.v1 (si aplica) | seguimiento-trabajos | Cancelacion de seguimiento solicitada o no requerida | COMPENSATING |
| B6 | SeguimientoTrabajoCancelado.v1 (si aplica) o condicion satisfecha | Finalizar compensacion | N/A | N/A | Saga compensada | COMPENSATED |

Regla sobre CancelarSeguimientoTrabajo.v1:
- Emitir si seguimiento_apertura_solicitada=true.
- NO emitir si seguimiento_apertura_solicitada=false.
- Fuente: orquestacion-trabajos/docs/entrega-5/08-diseno-persistencia-saga.md.

## 9. Identificadores y correlacion

| Identificador | Quien lo genera | Quien lo recibe | Proposito | Regla | Ejemplo dentro de Saga |
|---|---|---|---|---|---|
| id_solicitud | entrada/solicitudes-partner (origen) | todos los servicios de la saga | identidad de negocio y correlacion global | correlacion=id_solicitud en contratos de saga propuestos y contratos actuales de atencion | mismo id_solicitud viaja desde SolicitudDePartnerListaParaAtencion hasta Atencion*Registrada |
| id_saga | orquestacion-trabajos | mensajes de saga hacia servicios externos y eventos de respuesta | identidad tecnica de instancia de saga | una saga por id_solicitud (persistencia fase 1) | RegistrarAtencionHabilitada incluye id_saga |
| id_trabajo | orquestacion-trabajos al crear trabajo | cotizaciones, seguimiento, entrada (atencion) | identidad del trabajo asociado | requerido en mensajes de atencion y cotizacion actuales | SolicitarCotizacion incluye id_trabajo |
| correlacion | emisor de cada mensaje | consumidor del mensaje | correlacion de negocio transversal | correlacion=id_solicitud (regla declarada) | validacion en solicitud-partner exige correlation=request_id |
| event_id | emisor de eventos | consumidor de eventos | idempotencia y trazabilidad de eventos | estable en reintentos | CotizacionRegistrada.event_id |
| command_id | emisor de comandos | consumidor de comandos | idempotencia y trazabilidad de comandos | estable en reintentos | RegistrarAtencionCancelada.command_id |
| causacion | emisor del mensaje actual | consumidor | encadenar causalidad | cuando exista, apunta a command_id/event_id origen | AtencionCanceladaRegistrada.causacion = command_id de RegistrarAtencionCancelada |

Validaciones solicitadas (aplican solo donde el campo existe):
- correlacion == id_solicitud: DEFINIDO para comandos de atencion (validado en solicitud-partner) y DEFINIDO en propuesta saga; en algunos contratos existentes de cotizacion es INFERIDO por convencion.
- evento.id_saga == saga.id_saga: NO DEFINIDO EN LOS CONTRATOS ACTUALES para CotizacionRegistrada/CotizacionRechazada/SolicitudDePartnerListaParaAtencion (porque no traen id_saga).
- evento.id_solicitud == saga.id_solicitud: DEFINIDO cuando el campo existe.
- evento.id_trabajo == saga.id_trabajo: DEFINIDO cuando el campo existe.
- evento.correlacion == saga.id_solicitud: DEFINIDO/INFERIDO segun contrato indicado arriba.
- evento.causacion == command_id emitido: DEFINIDO para respuestas de atencion y cotizacion (campo existe), sujeto a politica del emisor.

## 10. Validaciones del SagaCoordinator

Base de terminologia SagaLog (implementada en fase 1):
- tipo_registro: EVENT_RECEIVED, COMMAND_EMITTED, EVENT_EMITTED, LOCAL_OPERATION, STATE_CHANGED, DUPLICATE, LATE, OUT_OF_ORDER, IGNORED
- resultado: APPLIED, NO_OP_DUPLICATE, NO_OP_LATE, NO_OP_OUT_OF_ORDER, REJECTED_CONFLICT

| Evento recibido | Validacion | Accion si valida | Accion si invalida | Resultado SagaLog |
|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | event_id no procesado; id_solicitud presente | crear/continuar saga y crear trabajo | duplicado -> no-op; contenido distinto con mismo event_id -> conflicto | DUPLICATE+NO_OP_DUPLICATE o EVENT_RECEIVED+REJECTED_CONFLICT |
| CotizacionRegistrada.v1 | saga existente por id_solicitud; estado RUNNING; paso esperado de cotizacion | emitir AbrirSeguimientoTrabajo.v1 | si saga terminal -> LATE; si paso no esperado -> OUT_OF_ORDER; si ids contradicen estado -> REJECTED_CONFLICT | LATE/NO_OP_LATE o OUT_OF_ORDER/NO_OP_OUT_OF_ORDER o EVENT_RECEIVED/REJECTED_CONFLICT |
| CotizacionRechazada.v1 | saga existente por id_solicitud; estado RUNNING | ejecutar rama compensada por rechazo | misma logica de invalidacion de orden/tardia/duplicado/conflicto | segun caso |
| SeguimientoTrabajoAbierto.v1 | saga existente; estado RUNNING; paso apertura solicitado | emitir RegistrarAtencionHabilitada.v1 y marcar bandera seguimiento_abierto_confirmado | tardio/fuera de orden/conflicto | segun caso |
| AperturaSeguimientoFallida.v1 | saga existente; estado RUNNING | mover a COMPENSATING y emitir AnularCotizacion.v1 | tardio/fuera de orden/conflicto | segun caso |
| CotizacionAnulada.v1 | saga en COMPENSATING | cancelar trabajo y avanzar compensacion | fuera de orden/tardio/conflicto | segun caso |
| SeguimientoTrabajoCancelado.v1 | saga en COMPENSATING y cancelacion de seguimiento pendiente | cerrar compensacion pendiente de seguimiento | fuera de orden/tardio/conflicto | segun caso |
| AtencionHabilitadaRegistrada.v1 | saga en RUNNING y paso registrar atencion habilitada | estado COMPLETED | tardio/fuera de orden/conflicto | segun caso |
| AtencionCanceladaRegistrada.v1 | saga en compensacion o rama compensada por rechazo | finalizar compensacion (o continuar con cancelacion de seguimiento si aplica) | tardio/fuera de orden/conflicto | segun caso |

Reglas transversales:
- Duplicados: llave sugerida por fase 1: id_saga + tipo_mensaje + message_id (message_id = event_id o command_id).
- LATE: evento valido pero llega con saga en estado terminal o paso superado.
- OUT_OF_ORDER: evento de un paso futuro o no habilitado por estado/paso actual.
- CONFLICT: mismo identificador con contenido incompatible o ids no consistentes con saga.

## 11. Estados y transiciones

| Estado actual | Evento/condicion | Accion | Estado siguiente | Permitido |
|---|---|---|---|---|
| RUNNING | SolicitudDePartnerListaParaAtencion.v1 | iniciar saga y flujo | RUNNING | SI |
| RUNNING | CotizacionRegistrada.v1 | solicitar apertura seguimiento | RUNNING | SI |
| RUNNING | SeguimientoTrabajoAbierto.v1 | solicitar atencion habilitada | RUNNING | SI |
| RUNNING | AtencionHabilitadaRegistrada.v1 | completar saga | COMPLETED | SI |
| RUNNING | AperturaSeguimientoFallida.v1 | iniciar compensacion | COMPENSATING | SI |
| RUNNING | CotizacionRechazada.v1 | rama de cierre compensado | COMPENSATING o cierre compensado directo (decision pendiente) | PARCIAL |
| COMPENSATING | Confirmaciones de compensacion completas | finalizar compensacion | COMPENSATED | SI |
| COMPLETED | cualquier evento de negocio posterior | ignorar funcionalmente y registrar | COMPLETED | SI (no-op) |
| COMPENSATED | cualquier evento de negocio posterior | ignorar funcionalmente y registrar | COMPENSATED | SI (no-op) |
| COMPLETED | transicion a otro estado | N/A | NO APLICA | NO |
| COMPENSATED | transicion a otro estado | N/A | NO APLICA | NO |

Estados validos unicos:
- RUNNING
- COMPENSATING
- COMPLETED
- COMPENSATED

## 12. Commands vs Events del orquestador

| Mensaje | Lo recibe Orquestacion? | Lo produce Orquestacion? | Es Command/Event? | Accion del Coordinator |
|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | SI | NO | Event | iniciar saga |
| TrabajoCreado.v1 | N/A (interno de orquestacion para integracion) | SI | Event | salida tras crear trabajo |
| SolicitarCotizacion.v1 | NO | SI | Command | solicitar cotizacion |
| CotizacionRegistrada.v1 | SI | NO | Event | avanzar a apertura seguimiento |
| CotizacionRechazada.v1 | SI | NO | Event | ruta de compensacion/cierre por rechazo |
| AbrirSeguimientoTrabajo.v1 | NO | SI (propuesto) | Command | solicitar apertura seguimiento |
| SeguimientoTrabajoAbierto.v1 | SI (propuesto) | NO | Event | avanzar a atencion habilitada |
| AperturaSeguimientoFallida.v1 | SI (propuesto) | NO | Event | iniciar compensacion |
| CancelarSeguimientoTrabajo.v1 | NO | SI (propuesto) | Command | compensar seguimiento |
| SeguimientoTrabajoCancelado.v1 | SI (propuesto) | NO | Event | confirmar compensacion seguimiento |
| AnularCotizacion.v1 | NO | SI (propuesto) | Command | compensar cotizacion |
| CotizacionAnulada.v1 | SI (propuesto) | NO | Event | confirmar compensacion cotizacion |
| RegistrarAtencionHabilitada.v1 | NO | SI (propuesto, ya existe contrato en solicitud-partner) | Command | habilitar atencion |
| AtencionHabilitadaRegistrada.v1 | SI (propuesto, ya existe contrato en solicitud-partner) | NO | Event | completar saga |
| RegistrarAtencionCancelada.v1 | NO | SI (propuesto, ya existe contrato en solicitud-partner) | Command | cancelar atencion |
| AtencionCanceladaRegistrada.v1 | SI (propuesto, ya existe contrato en solicitud-partner) | NO | Event | cerrar compensacion |
| TrabajoCancelado.v1 | NO | SI (propuesto) | Event | notificar cancelacion de trabajo |

## 13. Idempotencia

Diseno persistencia fase 1 (orquestacion):
- llave de deduplicacion: id_saga + tipo_mensaje + message_id
- message_id = event_id o command_id
- fuente: orquestacion-trabajos/docs/entrega-5/09-implementacion-persistencia-saga.md

| Mensaje | Identificador de deduplicacion | Puede repetirse? | Accion primera vez | Accion duplicado | Registro SagaLog |
|---|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | id_saga + tipo + event_id | SI | aplicar inicio/avance | no-op | DUPLICATE + NO_OP_DUPLICATE |
| CotizacionRegistrada.v1 | id_saga + tipo + event_id | SI | aplicar avance | no-op | DUPLICATE + NO_OP_DUPLICATE |
| CotizacionRechazada.v1 | id_saga + tipo + event_id | SI | aplicar rama compensada | no-op | DUPLICATE + NO_OP_DUPLICATE |
| SeguimientoTrabajoAbierto.v1 | id_saga + tipo + event_id | SI | aplicar avance | no-op | DUPLICATE + NO_OP_DUPLICATE |
| AperturaSeguimientoFallida.v1 | id_saga + tipo + event_id | SI | aplicar compensacion | no-op | DUPLICATE + NO_OP_DUPLICATE |
| CotizacionAnulada.v1 | id_saga + tipo + event_id | SI | aplicar confirmacion compensacion | no-op | DUPLICATE + NO_OP_DUPLICATE |
| SeguimientoTrabajoCancelado.v1 | id_saga + tipo + event_id | SI | aplicar confirmacion compensacion | no-op | DUPLICATE + NO_OP_DUPLICATE |
| AtencionHabilitadaRegistrada.v1 | id_saga + tipo + event_id | SI | completar saga | no-op | DUPLICATE + NO_OP_DUPLICATE |
| AtencionCanceladaRegistrada.v1 | id_saga + tipo + event_id | SI | compensar/cerrar | no-op | DUPLICATE + NO_OP_DUPLICATE |

Nota:
- Para mensajes que no incluyen id_saga en contrato (ejemplo CotizacionRegistrada actual), el enlace a saga requiere resolucion por id_solicitud. Esa resolucion es DEFINIDA por diseno, no por avro.

## 14. Dependencias externas

| Servicio | Mensajes que recibe | Mensajes que produce | Lo que Orquestacion necesita conocer | Lo que NO necesita conocer |
|---|---|---|---|---|
| solicitudes-partner | RegistrarAtencionHabilitada.v1, RegistrarAtencionCancelada.v1 | SolicitudDePartnerListaParaAtencion.v1, AtencionHabilitadaRegistrada.v1, AtencionCanceladaRegistrada.v1 | contratos, topicos, correlacion, causacion, ids de negocio | tablas internas, handlers internos, API HTTP interna de entrada |
| cotizaciones | SolicitarCotizacion.v1, AnularCotizacion.v1 (propuesto) | CotizacionRegistrada.v1, CotizacionRechazada.v1, CotizacionAnulada.v1 (propuesto) | contratos de comandos/eventos, reglas de correlacion, causalidad | modelo interno de cotizacion, endpoints internos, persistencia interna |
| seguimiento-trabajos | TrabajoCreado.v1, AbrirSeguimientoTrabajo.v1 (propuesto), CancelarSeguimientoTrabajo.v1 (propuesto), TrabajoCancelado.v1 (propuesto) | SeguimientoTrabajoAbierto.v1 (propuesto), AperturaSeguimientoFallida.v1 (propuesto), SeguimientoTrabajoCancelado.v1 (propuesto) | contratos, orden de eventos de compensacion, ids requeridos | implementacion interna, tablas internas, endpoints internos |

Principio validado:
- Orquestacion depende de contratos, no de implementaciones internas.

## 15. Informacion faltante

| Mensaje | Definido actualmente | Informacion faltante | Bloquea Coordinator? | Puede simularse? |
|---|---|---|---|---|
| SolicitudDePartnerListaParaAtencion.v1 | DISPONIBLE | ninguna critica para coordinator | NO | SI |
| SolicitarCotizacion.v1 | DISPONIBLE | ninguna critica para coordinator | NO | SI |
| CotizacionRegistrada.v1 | DISPONIBLE | regla formal exacta correlacion=id_solicitud no explicitada en avro | NO (se asume convencion de negocio ya usada) | SI |
| CotizacionRechazada.v1 | DISPONIBLE | decision final de estado saga para rechazo (COMPENSATING vs cierre compensado directo) | PARCIAL | SI |
| AbrirSeguimientoTrabajo.v1 | PARCIAL | Avro final y topic oficial en servicios | NO para implementar coordinator base; SI para integracion real | SI |
| SeguimientoTrabajoAbierto.v1 | PARCIAL | Avro final y topic oficial | NO para logica; SI para integracion real | SI |
| AperturaSeguimientoFallida.v1 | PARCIAL | Avro final y topic oficial | NO para logica; SI para integracion real | SI |
| CancelarSeguimientoTrabajo.v1 | PARCIAL | Avro final y topic oficial | NO para logica; SI para integracion real | SI |
| SeguimientoTrabajoCancelado.v1 | PARCIAL | Avro final y topic oficial | NO para logica; SI para integracion real | SI |
| AnularCotizacion.v1 | PARCIAL | Avro final y topic oficial | NO para logica; SI para integracion real | SI |
| CotizacionAnulada.v1 | PARCIAL | Avro final y topic oficial | NO para logica; SI para integracion real | SI |
| RegistrarAtencionHabilitada.v1 | DISPONIBLE | alineacion final de topic por ambiente | NO | SI |
| AtencionHabilitadaRegistrada.v1 | DISPONIBLE | ninguna critica para coordinator | NO | SI |
| RegistrarAtencionCancelada.v1 | DISPONIBLE | alineacion final de topic por ambiente | NO | SI |
| AtencionCanceladaRegistrada.v1 | DISPONIBLE | no incluye codigo_motivo/detalle en evento de respuesta | NO (si no se requiere ese detalle para transicion) | SI |
| TrabajoCancelado.v1 | PARCIAL | Avro final y topic oficial | NO para logica local; SI para integracion real con seguimiento | SI |

Criterio aplicado:
- DISPONIBLE: existe contrato implementado (avsc y/o implementacion activa en servicio).
- PARCIAL: definido en propuesta, pero sin avro implementado en workspace.
- NO DEFINIDO: no hay definicion suficiente.

## 16. Inconsistencias o decisiones pendientes

1. Estado final en rama CotizacionRechazada:
- En 07-diseno-saga-steps se indica cierre compensado, pero el detalle exacto de transicion RUNNING -> COMPENSATING o atajo de cierre aun aparece como decision pendiente.
- Estado: DECISION PENDIENTE.

2. Reglas de correlacion explicitas en contratos de cotizaciones:
- Avro incluye correlacion e id_solicitud, pero no declara formalmente correlacion==id_solicitud en el schema.
- Estado: INFERIDO por convencion, no explicitado en contrato.

3. Contratos de seguimiento y compensacion (nuevo set de saga):
- Existen en propuesta MD, pero no hay schemas Avro implementados en el workspace para AbrirSeguimientoTrabajo, SeguimientoTrabajoAbierto, AperturaSeguimientoFallida, CancelarSeguimientoTrabajo, SeguimientoTrabajoCancelado, AnularCotizacion, CotizacionAnulada, TrabajoCancelado.
- Estado: PARCIAL.

4. Diferencia entre propuesta 08 y enum implementado de resultados de SagaLog:
- En 08 aparecen etiquetas textuales tipo IGNORED_POST_COMPLETED/IGNORED_POST_COMPENSATED (propuesta narrativa), pero enum implementado usa tipo_registro IGNORED y resultado APPLIED/NO_OP/REJECTED_CONFLICT.
- Estado: REQUIERE DECISION DE NORMALIZACION TERMINOLOGICA.

5. PDF de propuesta hda-entrega5-propuesta-saga-bff:
- No se uso como fuente textual estructurada en este analisis.
- Estado: VALIDACION MANUAL RECOMENDADA POR EL EQUIPO.

6. No HTTP entre microservicios para la saga:
- El flujo de saga definido es por mensajeria (Pulsar).
- El BFF puede consultar por HTTP, pero eso no es comunicacion saga entre microservicios de dominio.
- Estado: CONSISTENTE con criterio de no usar HTTP para coordinacion de saga.

## 17. Conclusion

Los contratos actuales permiten implementar YA la base del SagaCoordinator en orquestacion-trabajos:
- modelo de estado y transiciones de saga,
- validaciones de ids/correlacion/orden,
- SagaLog con clasificacion DUPLICATE/LATE/OUT_OF_ORDER/CONFLICT,
- idempotencia por llave aprobada en Fase 1.

Lo que falta para integracion real completa no bloquea el diseno ni la implementacion base del coordinator; bloquea la conexion real end-to-end de algunas ramas porque aun no hay Avro implementado para mensajes nuevos de seguimiento y compensacion con cotizaciones.

### PODEMOS IMPLEMENTAR AHORA

- SagaCoordinator base (maquina de estados RUNNING/COMPENSATING/COMPLETED/COMPENSATED).
- Handlers para eventos ya disponibles:
  - SolicitudDePartnerListaParaAtencion.v1
  - CotizacionRegistrada.v1
  - CotizacionRechazada.v1
  - AtencionHabilitadaRegistrada.v1
  - AtencionCanceladaRegistrada.v1
- Emision de comandos ya contratados/disponibles:
  - SolicitarCotizacion.v1
  - RegistrarAtencionHabilitada.v1
  - RegistrarAtencionCancelada.v1
- SagaLog e idempotencia segun Fase 1.

### DEPENDE DE CONTRATOS PENDIENTES

- Definicion Avro final (y topicos finales) de:
  - AbrirSeguimientoTrabajo.v1
  - SeguimientoTrabajoAbierto.v1
  - AperturaSeguimientoFallida.v1
  - CancelarSeguimientoTrabajo.v1
  - SeguimientoTrabajoCancelado.v1
  - AnularCotizacion.v1
  - CotizacionAnulada.v1
  - TrabajoCancelado.v1

### DEPENDE DE IMPLEMENTACION DE COTIZACIONES

- Soporte real de AnularCotizacion.v1 -> CotizacionAnulada.v1.
- Semantica operacional real de anulacion e idempotencia en cotizaciones.

### DEPENDE DE IMPLEMENTACION DE SEGUIMIENTO

- Soporte real de AbrirSeguimientoTrabajo.v1 y respuestas de apertura/falla.
- Soporte real de CancelarSeguimientoTrabajo.v1 y SeguimientoTrabajoCancelado.v1.
- Consumo operativo de TrabajoCancelado.v1 para proyeccion consistente.

### DECISIONES QUE DEBE TOMAR EL EQUIPO

- Regla final para rama CotizacionRechazada (ruta de estado exacta).
- Normalizacion terminologica final de resultados SagaLog para eventos ignorados/tardios.
- Confirmacion final de correlacion en eventos de cotizaciones (igualdad formal correlacion=id_solicitud).
- Confirmacion final del contenido del PDF de propuesta frente al contrato MD.