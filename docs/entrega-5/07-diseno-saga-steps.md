# 07 - Diseno Saga Steps

## 1. Objetivo

Definir el modelo conceptual de SagaStep para Entrega 5 en Orquestacion de Trabajos, sin implementar codigo, sin modificar contratos, y manteniendo el dominio Trabajo como Aggregate Root independiente.

Decision base:

- [CONTRATO DEL EQUIPO] La Saga se modela como Process Manager / Orchestrator con estado persistente propio.
- [CONTRATO DEL EQUIPO] Los estados de Saga son RUNNING, COMPENSATING, COMPLETED y COMPENSATED.

## 2. Fuentes utilizadas

Prioridad aplicada:

1. [CONTRATO DEL EQUIPO] docs/entrega-5/contratos-saga-propuesta.md
2. [CONTRATO DEL EQUIPO] docs/entrega-5/hda-entrega5-propuesta-saga-bff.pdf
3. [ADAPTACIÓN DEL TUTORIAL] docs/entrega-5/06-mapeo-tutorial-saga-vs-hogar-alpes.md
4. [EXISTENTE] docs/entrega-5/AUDITORIA_ENTREGA5_ORQUESTACION_TRABAJOS.md

Observacion sobre fuente PDF:

- [PROPUESTA] En este entorno no se pudo obtener render de texto completo del PDF por bloqueo del visor local; se logró extraer metadato de titulo y estructura tecnica del archivo, pero no todo el contenido textual.
- [PROPUESTA] Para cerrar esta brecha documental, conviene validar manualmente el PDF en un visor local del equipo y confirmar que no contradiga el contrato MD.

## 3. Decision sobre SagaStep

Decision principal:

- [PROPUESTA] SagaStep debe modelarse como Value Object inmutable de catalogo de transicion (definicion de paso), no como Entity.

Justificacion DDD:

- [PROPUESTA] La identidad y ciclo de vida mutable pertenecen a la instancia de Saga (Process Manager persistido), no a la definicion del paso.
- [PROPUESTA] Un paso es una regla declarativa reutilizable: trigger, comando, evento esperado, evento de falla, compensacion, siguiente paso.
- [PROPUESTA] Al ser inmutable, SagaStep reduce riesgo de inconsistencias en decisiones de coordinacion.

Alternativas evaluadas:

- [PROPUESTA] Entity para SagaStep: descartada porque no aporta identidad de negocio propia.
- [PROPUESTA] Solo Enum sin estructura: insuficiente para representar reglas de transicion y compensacion.

## 4. Decision sobre SagaStatus

- [CONTRATO DEL EQUIPO] SagaStatus debe existir y restringirse a RUNNING, COMPENSATING, COMPLETED, COMPENSATED.
- [PROPUESTA] No agregar estados extra en esta fase para evitar desviarse del contrato acordado.

## 5. Modelo conceptual

### 5.1 Abstracciones minimas recomendadas

- [PROPUESTA] SagaStatus (enum): RUNNING, COMPENSATING, COMPLETED, COMPENSATED.
- [PROPUESTA] SagaStepName (enum): identificadores estables de pasos.
- [PROPUESTA] SagaStep (value object): definicion de comportamiento del paso.
- [PROPUESTA] SagaTransition (value object de registro): transición ejecutada (evento recibido, decision, nuevo estado).

### 5.2 Abstracciones que no se recomiendan por ahora

- [PROPUESTA] CompensationStep separado: no necesario; compensacion puede ser propiedad del SagaStep.
- [PROPUESTA] Maquinas de estado duplicadas por flujo: no necesario; una sola politica con ramas condicionadas es suficiente.

### 5.3 Campos conceptuales de SagaStep

- [PROPUESTA] nombre_paso
- [PROPUESTA] evento_que_activa
- [PROPUESTA] comando
- [PROPUESTA] servicio_receptor
- [PROPUESTA] evento_exito
- [PROPUESTA] evento_falla
- [PROPUESTA] comando_compensacion
- [PROPUESTA] evento_compensacion
- [PROPUESTA] siguiente_paso_exito
- [PROPUESTA] siguiente_paso_falla
- [PROPUESTA] reglas_transicion (incluye condiciones como seguimiento_ya_abierto)

## 6. Tabla completa de pasos

Incluye happy path y ramas de compensacion.

| PASO | EVENTO QUE LO ACTIVA | COMANDO | SERVICIO RECEPTOR | EVENTO DE EXITO | EVENTO DE FALLA | COMPENSACIÓN | EVENTO DE COMPENSACIÓN | SIGUIENTE PASO |
|---|---|---|---|---|---|---|---|---|
| INICIAR_SAGA_Y_CREAR_TRABAJO | SolicitudDePartnerListaParaAtencion.v1 | Operacion local crear Trabajo + registrar saga | Orquestacion (local) | TrabajoCreado.v1 | (sin contrato de falla publico) | Ninguna | N/A | SOLICITAR_COTIZACION |
| SOLICITAR_COTIZACION | TrabajoCreado.v1 | SolicitarCotizacion.v1 | Cotizaciones | CotizacionRegistrada.v1 | CotizacionRechazada.v1 | AnularCotizacion.v1 (solo si ya hubo CotizacionRegistrada) | CotizacionAnulada.v1 | Exito: ABRIR_SEGUIMIENTO, Falla: CANCELAR_TRABAJO_POR_RECHAZO |
| ABRIR_SEGUIMIENTO | CotizacionRegistrada.v1 | AbrirSeguimientoTrabajo.v1 | Seguimiento | SeguimientoTrabajoAbierto.v1 | AperturaSeguimientoFallida.v1 | CancelarSeguimientoTrabajo.v1 (solo si el seguimiento llego a abrirse) | SeguimientoTrabajoCancelado.v1 | Exito: REGISTRAR_ATENCION_HABILITADA, Falla: INICIAR_COMPENSACION_APERTURA |
| REGISTRAR_ATENCION_HABILITADA | SeguimientoTrabajoAbierto.v1 | RegistrarAtencionHabilitada.v1 | Entrada | AtencionHabilitadaRegistrada.v1 | (sin contrato de falla publico) | N/A | N/A | COMPLETAR_SAGA |
| COMPLETAR_SAGA | AtencionHabilitadaRegistrada.v1 | N/A | N/A | Saga COMPLETED | N/A | N/A | N/A | FIN |
| CANCELAR_TRABAJO_POR_RECHAZO | CotizacionRechazada.v1 | Operacion local cancelar Trabajo + publicar TrabajoCancelado.v1 | Orquestacion (local) y Seguimiento (evento) | TrabajoCancelado.v1 | (sin contrato de falla publico) | N/A | N/A | REGISTRAR_ATENCION_CANCELADA |
| REGISTRAR_ATENCION_CANCELADA | TrabajoCancelado.v1 o estado local de trabajo cancelado | RegistrarAtencionCancelada.v1 | Entrada | AtencionCanceladaRegistrada.v1 | (sin contrato de falla publico) | N/A | N/A | FINALIZAR_COMPENSACION |
| INICIAR_COMPENSACION_APERTURA | AperturaSeguimientoFallida.v1 | AnularCotizacion.v1 | Cotizaciones | CotizacionAnulada.v1 | (sin contrato de falla publico) | Reintentar mismo comando | CotizacionAnulada.v1 | CANCELAR_TRABAJO_COMPENSACION |
| CANCELAR_TRABAJO_COMPENSACION | CotizacionAnulada.v1 | Operacion local cancelar Trabajo + publicar TrabajoCancelado.v1 | Orquestacion (local) y Seguimiento (evento) | TrabajoCancelado.v1 | (sin contrato de falla publico) | N/A | N/A | REGISTRAR_ATENCION_CANCELADA_COMPENSACION |
| REGISTRAR_ATENCION_CANCELADA_COMPENSACION | TrabajoCancelado.v1 | RegistrarAtencionCancelada.v1 | Entrada | AtencionCanceladaRegistrada.v1 | (sin contrato de falla publico) | N/A | N/A | CANCELAR_SEGUIMIENTO_SI_APLICA |
| CANCELAR_SEGUIMIENTO_SI_APLICA | AtencionCanceladaRegistrada.v1 y bandera seguimiento_abierto=true | CancelarSeguimientoTrabajo.v1 | Seguimiento | SeguimientoTrabajoCancelado.v1 | (sin contrato de falla publico) | Reintentar mismo comando | SeguimientoTrabajoCancelado.v1 | FINALIZAR_COMPENSACION |
| FINALIZAR_COMPENSACION | AtencionCanceladaRegistrada.v1 y (si aplica) SeguimientoTrabajoCancelado.v1 | N/A | N/A | Saga COMPENSATED | N/A | N/A | N/A | FIN |

## 7. Happy Path

Secuencia oficial representada:

1. [CONTRATO DEL EQUIPO] SolicitudDePartnerListaParaAtencion.v1.
2. [CONTRATO DEL EQUIPO] Iniciar Saga y crear Trabajo.
3. [CONTRATO DEL EQUIPO] SolicitarCotizacion.v1.
4. [CONTRATO DEL EQUIPO] CotizacionRegistrada.v1.
5. [CONTRATO DEL EQUIPO] AbrirSeguimientoTrabajo.v1.
6. [CONTRATO DEL EQUIPO] SeguimientoTrabajoAbierto.v1.
7. [CONTRATO DEL EQUIPO] RegistrarAtencionHabilitada.v1.
8. [CONTRATO DEL EQUIPO] AtencionHabilitadaRegistrada.v1.
9. [CONTRATO DEL EQUIPO] Saga COMPLETED.

## 8. Caso CotizacionRechazada

Politica de diseno:

- [CONTRATO DEL EQUIPO] Al recibir CotizacionRechazada.v1 no se envia AnularCotizacion.v1.
- [CONTRATO DEL EQUIPO] Se cancela Trabajo localmente en Orquestacion.
- [CONTRATO DEL EQUIPO] Se publica TrabajoCancelado.v1 para Seguimiento.
- [CONTRATO DEL EQUIPO] Se envia RegistrarAtencionCancelada.v1 y se espera AtencionCanceladaRegistrada.v1.
- [PROPUESTA] La Saga termina en COMPENSATED para reflejar cierre por ruta de compensacion/fracaso funcional.

## 9. Compensacion por AperturaSeguimientoFallida

Politica de diseno:

- [CONTRATO DEL EQUIPO] AperturaSeguimientoFallida.v1 mueve la Saga a COMPENSATING.
- [CONTRATO DEL EQUIPO] Enviar AnularCotizacion.v1 y esperar CotizacionAnulada.v1.
- [CONTRATO DEL EQUIPO] Cancelar Trabajo localmente y publicar TrabajoCancelado.v1.
- [CONTRATO DEL EQUIPO] Enviar RegistrarAtencionCancelada.v1 y esperar AtencionCanceladaRegistrada.v1.
- [CONTRATO DEL EQUIPO] Si hay seguimiento abierto, enviar CancelarSeguimientoTrabajo.v1 y esperar SeguimientoTrabajoCancelado.v1.
- [CONTRATO DEL EQUIPO] Cerrar en COMPENSATED cuando todas las compensaciones requeridas confirmen.

## 10. Caso Seguimiento ya abierto

Regla necesaria:

- [CONTRATO DEL EQUIPO] La secuencia de compensacion depende de efectos ya aplicados.
- [PROPUESTA] Mantener una bandera de efecto aplicado: seguimiento_abierto_confirmado.
- [PROPUESTA] Si seguimiento_abierto_confirmado = true, se vuelve obligatoria la compensacion CancelarSeguimientoTrabajo.v1.
- [PROPUESTA] Si seguimiento_abierto_confirmado = false, no se incluye ese paso.

## 11. Transiciones

### 11.1 Transiciones de estado

- [CONTRATO DEL EQUIPO] RUNNING -> RUNNING en avance normal por paso.
- [CONTRATO DEL EQUIPO] RUNNING -> COMPLETED al recibir AtencionHabilitadaRegistrada.v1.
- [CONTRATO DEL EQUIPO] RUNNING -> COMPENSATING al recibir AperturaSeguimientoFallida.v1.
- [CONTRATO DEL EQUIPO] RUNNING -> COMPENSATING o ruta de cierre compensado al recibir CotizacionRechazada.v1 (sin anular cotizacion).
- [CONTRATO DEL EQUIPO] COMPENSATING -> COMPENSATED cuando todas las compensaciones requeridas están confirmadas.

### 11.2 Reglas de transicion por evento

- [PROPUESTA] Solo se acepta un evento si es valido para el paso actual o para una compensacion pendiente explícita.
- [PROPUESTA] Evento fuera del paso esperado no cambia estado; se registra como fuera_de_orden para reintento/observabilidad.

## 12. Idempotencia

Politica de diseno:

- [EXISTENTE] Reusar Inbox por mensaje para deduplicar entrega.
- [CONTRATO DEL EQUIPO] Mismo ID y mismo contenido: un solo efecto.
- [CONTRATO DEL EQUIPO] Mismo ID y contenido distinto: conflicto, no confirmar éxito.
- [PROPUESTA] Cada transición de Saga debe ser idempotente por llave (id_saga, paso, tipo_mensaje, id_mensaje).
- [PROPUESTA] Reintentos de transporte no crean nueva Saga para la misma solicitud.

## 13. Eventos tardíos

Politica de diseno:

- [PROPUESTA] Evento tardío de un paso ya cerrado se ignora funcionalmente y se registra en Saga Log como tardio.
- [PROPUESTA] Si el evento tardío confirma una compensación aún pendiente, sí puede aplicarse.
- [CONTRATO DEL EQUIPO] Habilitación tardía tras cancelación no debe reactivar atención.

## 14. Eventos fuera de orden

Politica de diseno:

- [PROPUESTA] Evento de un paso futuro en RUNNING se marca fuera_de_orden y no avanza Saga.
- [PROPUESTA] Evento de compensación recibido antes del comando de compensación se marca fuera_de_orden.
- [PROPUESTA] Duplicado de confirmación de compensación se acepta como no-op.
- [PROPUESTA] Evento después de COMPLETED: no-op + registro de inconsistencia.
- [PROPUESTA] Evento después de COMPENSATED: no-op + registro de inconsistencia.

## 15. Mapeo con Tutorial 8

Adopción conceptual:

- [ADAPTACIÓN DEL TUTORIAL] Paso de Saga como catálogo declarativo.
- [ADAPTACIÓN DEL TUTORIAL] Coordinador central que decide siguiente comando por evento.
- [ADAPTACIÓN DEL TUTORIAL] Modelo de compensación explícita por transacción.

No adopción literal:

- [ADAPTACIÓN DEL TUTORIAL] No copiar implementación incompleta o TODO del tutorial.
- [ADAPTACIÓN DEL TUTORIAL] No copiar comandos/eventos de dominio Aeroalpes.

## 16. Elementos del tutorial que NO se deben copiar

- [ADAPTACIÓN DEL TUTORIAL] Placeholders de comandos sin contrato real.
- [ADAPTACIÓN DEL TUTORIAL] Errores de implementación detectados en el seedwork del tutorial (referencias sin self, imports faltantes, transición a compensación en rama de éxito).
- [ADAPTACIÓN DEL TUTORIAL] Acoplamiento a estructura particular de ese proyecto.

## 17. Impacto futuro en orquestacion-trabajos

- [EXISTENTE] Trabajo permanece como Aggregate Root de su dominio.
- [PROPUESTA] Se agregará estado persistente de Saga y Saga Log sin reemplazar Inbox/Outbox.
- [EXISTENTE] Infraestructura de UoW, idempotencia e integración Pulsar ya existe y sirve como base.
- [PROPUESTA] El Coordinador de Saga vivirá en capa de aplicación y usará repositorios/infraestructura existentes.

## 18. Proximo paso recomendado

- [PROPUESTA] Definir contrato interno de modelo de Saga (campos, invariantes y reglas de transición) y el esquema conceptual de Saga Log.
- [PROPUESTA] Revisar en equipo la tabla de pasos y validar formalmente dos decisiones: estado final para CotizacionRechazada y condición exacta de CancelarSeguimientoTrabajo.
- [PROPUESTA] Con esa validación, pasar a Fase 3 de diseño técnico de persistencia y mapeadores sin implementar aún.

---

## Inconsistencias o conflictos detectados

1. [CONTRATO DEL EQUIPO] El contrato principal está en documento Markdown y es consistente sobre nombres de eventos/comandos.
2. [PROPUESTA] El PDF no pudo leerse completamente en este entorno por bloqueo del visor local; no se detectó contradicción explícita, pero se recomienda verificación manual.
3. [ADAPTACIÓN DEL TUTORIAL] El tutorial 8 contiene código con TODO y errores técnicos, por lo que su uso debe ser conceptual y no literal.
