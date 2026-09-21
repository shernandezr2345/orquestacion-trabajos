# HdA · Entrega 5 · Acuerdo de contratos para Saga y BFF

**Estado:** propuesta para revisión y acuerdo del equipo. Los contratos nuevos todavía no están implementados ni congelados como esquemas Avro.

## Propósito

Definir un único acuerdo común de mensajes, campos, estados y comportamiento para que cada integrante pueda implementar su servicio de forma independiente.

La solución mantiene Entrada de Solicitudes, Orquestación de Trabajos, Cotizaciones y Seguimiento. Orquestación incorpora el coordinador y el Saga Log; Seguimiento amplía su dominio con apertura y cancelación del seguimiento operativo. Se añade un BFF REST separado.

La Saga habilita la atención de una solicitud: crea un Trabajo, obtiene una cotización y abre su seguimiento operativo. Completar la Saga no significa que el servicio domiciliario haya terminado.

## 1. Contratos existentes que se conservan

| Contrato | Productor → consumidor | Uso |
|---|---|---|
| `SolicitudDePartnerListaParaAtencion.v1` | Entrada → Orquestación | Iniciar el procesamiento de una solicitud admitida. |
| `TrabajoCreado.v1` | Orquestación → Seguimiento | Alimentar la proyección del Trabajo. |
| `SolicitarCotizacion.v1` | Orquestación → Cotizaciones | Solicitar la propuesta. |
| `CotizacionRegistrada.v1` | Cotizaciones → Orquestación y Seguimiento | Informar la propuesta registrada. |
| `CotizacionRechazada.v1` | Cotizaciones → Orquestación y Seguimiento | Informar que no se obtuvo propuesta. |

Se conservan nombres, campos, tópicos y revisiones compatibles, incluida la duración incorporada en E3. Los consumidores utilizan el esquema publicado por el propietario; no definen variantes independientes.

## 2. Nuevos contratos para la Saga

Todos los comandos y eventos de esta sección llevan el sufijo `.v1` y viajan por Pulsar.

| Comando | Emisor → receptor | Evento de respuesta |
|---|---|---|
| `AbrirSeguimientoTrabajo.v1` | Orquestación → Seguimiento | `SeguimientoTrabajoAbierto.v1` o `AperturaSeguimientoFallida.v1` |
| `CancelarSeguimientoTrabajo.v1` | Orquestación → Seguimiento | `SeguimientoTrabajoCancelado.v1` |
| `AnularCotizacion.v1` | Orquestación → Cotizaciones | `CotizacionAnulada.v1` |
| `RegistrarAtencionHabilitada.v1` | Orquestación → Entrada | `AtencionHabilitadaRegistrada.v1` |
| `RegistrarAtencionCancelada.v1` | Orquestación → Entrada | `AtencionCanceladaRegistrada.v1` |

Se añade `TrabajoCancelado.v1`, publicado por Orquestación y consumido por Seguimiento, para actualizar la proyección incluso cuando la apertura operativa nunca se completó.

Cancelar el Trabajo es una operación local de Orquestación; no requiere un comando externo hacia otro servicio.

## 3. Campos comunes y correlación

Los mensajes nuevos de la Saga comparten estos campos:

| Campo | Regla |
|---|---|
| `command_id` o `event_id` | UUID del mensaje. Se conserva al reenviar. Los comandos usan `command_id`; los eventos, `event_id`. |
| `tipo` | Nombre completo del contrato, por ejemplo `AnularCotizacion.v1`. |
| `version_contrato` | `1` para estos contratos nuevos. |
| `instante` | Fecha y hora UTC del mensaje original. |
| `correlacion` | `id_solicitud`, conservando la convención actual. |
| `causacion` | ID del comando o evento que originó este mensaje. |
| `id_saga` | Identidad asignada por Orquestación al iniciar la Saga. |
| `id_solicitud` | Solicitud vinculada. |
| `id_trabajo` | Trabajo vinculado. |
| `id_partner` | Partner propietario de la solicitud. |

`correlacion` no cambia de significado para representar `id_saga`. Orquestación asocia los eventos existentes con la Saga mediante la identidad de solicitud, sin modificar todos los esquemas.

Se conserva el alcance actual: una Saga por solicitud y una petición de cotización por Trabajo. Reintentar transporte no crea otra Saga.

## 4. Campos específicos

Además de los campos comunes:

| Contrato | Campos adicionales propuestos |
|---|---|
| `AbrirSeguimientoTrabajo.v1` | `id_cotizacion` |
| `SeguimientoTrabajoAbierto.v1` | `id_seguimiento`, `abierto_en` |
| `AperturaSeguimientoFallida.v1` | `codigo_motivo`, `detalle` |
| `CancelarSeguimientoTrabajo.v1` | `codigo_motivo`, `detalle` |
| `SeguimientoTrabajoCancelado.v1` | `id_seguimiento` nullable, `cancelado_en` |
| `AnularCotizacion.v1` | `id_peticion`, `id_cotizacion`, `codigo_motivo`, `detalle` |
| `CotizacionAnulada.v1` | `id_peticion`, `id_cotizacion`, `anulada_en` |
| `RegistrarAtencionHabilitada.v1` | Campos comunes suficientes. |
| `AtencionHabilitadaRegistrada.v1` | `registrada_en` |
| `RegistrarAtencionCancelada.v1` | `codigo_motivo`, `detalle` |
| `AtencionCanceladaRegistrada.v1` | `registrada_en` |
| `TrabajoCancelado.v1` | `codigo_motivo`, `detalle`, `cancelado_en`, `version_trabajo` |

`CancelarSeguimientoTrabajo.v1` identifica el seguimiento por Trabajo, sin exigir conocer `id_seguimiento`. Esto permite cancelar cuando la apertura ya se ejecutó, pero su respuesta todavía no llegó.

Los consumidores interpretan `codigo_motivo`. `detalle` es texto explicativo y no se analiza para decidir transiciones.

## 5. Comportamiento compartido

| Situación | Comportamiento acordado propuesto |
|---|---|
| Mismo mensaje recibido varias veces | Un solo efecto de negocio. |
| Mismo ID con contenido distinto | Conflicto de contrato; no sobrescribir datos ni confirmar éxito. |
| Caída temporal de base de datos o transporte | Reintentar. No emitir un rechazo de negocio por indisponibilidad temporal. |
| Apertura rechazada definitivamente | Emitir `AperturaSeguimientoFallida.v1`; Orquestación inicia compensación. |
| Cancelación de Seguimiento antes de su apertura | Registrar la cancelación por Trabajo y confirmarla. Una apertura tardía no puede reactivarlo. |
| Cotización ya anulada | No repetir efectos; garantizar que su confirmación pueda entregarse. |
| Actualización de atención duplicada | Mantener el resultado sin duplicar cambios. |
| Habilitación tardía después de cancelación | No volver a habilitar la solicitud. |
| Compensación sin confirmar | Mantener la Saga en `COMPENSATING`. |

Cada participante persiste efecto, inbox y evento de respuesta en outbox dentro de su transacción local, cuando corresponda. El ACK se realiza después del commit.

Para demostrar el fallo de apertura se propone `codigo_motivo = FALLO_CONTROLADO_APERTURA`. La inyección se configura en el laboratorio y ocurre antes de persistir la apertura; no se añade un campo público como `fallar=true` al contrato empresarial.

## 6. Estados y transiciones

| Componente | Estados propuestos |
|---|---|
| Saga | `RUNNING`, `COMPENSATING`, `COMPLETED`, `COMPENSATED` |
| Trabajo | Estados actuales y nuevo `CANCELADO`. |
| Cotización | Estados actuales y nuevo `ANULADA`. |
| Seguimiento operativo | `ABIERTO`, `CANCELADO`. |
| Resultado de atención en Entrada | `PENDIENTE`, `ATENCION_HABILITADA`, `ATENCION_CANCELADA`. |

En Entrada, el resultado de atención se mantiene separado de la admisibilidad. Una solicitud puede ser admisible y terminar con atención cancelada.

### Transiciones principales del coordinador

| Resultado recibido | Acción siguiente |
|---|---|
| `SolicitudDePartnerListaParaAtencion.v1` | Iniciar Saga, crear Trabajo y solicitar cotización. |
| `CotizacionRegistrada.v1` | Solicitar apertura de Seguimiento. |
| `SeguimientoTrabajoAbierto.v1` | Solicitar registro de atención habilitada. |
| `AtencionHabilitadaRegistrada.v1` | Completar la Saga. |
| `CotizacionRechazada.v1` | Cancelar Trabajo y registrar atención cancelada, sin intentar anular una propuesta inexistente. |
| `AperturaSeguimientoFallida.v1` | Iniciar compensación: anular cotización, cancelar Trabajo y registrar atención cancelada. |
| Confirmación de todas las compensaciones requeridas | Terminar la Saga como `COMPENSATED`. |

Si Seguimiento llegó a abrirse antes de una cancelación, también se solicita su cancelación y se espera la confirmación. No se borran los registros originales para simular un rollback.

## 7. Ingreso y consultas del BFF

### Comando de ingreso

`RegistrarSolicitudPartner.v1`, publicado por el BFF y consumido por Entrada:

- `command_id`, `tipo`, `version_contrato`, `instante`.
- `id_partner`.
- `referencia_externa`.
- `categoria`.
- `tipo_solicitud`.
- `aprobacion_previa`, conservando la diferencia entre `null` y `false`.

Este mensaje antecede a la creación de la solicitud y la Saga; no exige los campos comunes de identidad de Saga de la sección 3.

El BFF obtiene el partner de la identidad autorizada; no confía únicamente en un identificador enviado en el cuerpo.

### Respuesta de recepción

Entrada conserva la asignación de `id_solicitud`. El BFF responde `202` después de que Pulsar confirme la publicación, con la identidad del comando como `id_operacion`:

```json
{
  "id_operacion": "UUID-del-comando",
  "estado": "RECIBIDA",
  "consulta": "/api/operaciones/UUID-del-comando"
}
```

`RECIBIDA` significa que el comando fue recibido por el broker; no acredita aceptación de negocio ni persistencia de la solicitud en Entrada.

Entrada persiste la asociación entre `command_id` e `id_solicitud`. El BFF consulta esa asociación mediante un endpoint de Entrada. Si el comando aún no se ha procesado, se indica que el resultado no está disponible todavía. Las solicitudes inadmisibles no inician una Saga.

### API externa propuesta

| Endpoint | Uso |
|---|---|
| `POST /api/solicitudes` | Publicar el comando de ingreso. |
| `GET /api/operaciones/{id}` | Consultar el resultado del comando y su asociación con la solicitud. |
| `GET /api/solicitudes/{id}` | Consultar admisibilidad y resultado de atención. |
| `GET /api/seguimiento/{id_trabajo}` | Consultar proyección y seguimiento operativo. |
| `GET /api/sagas/{id}` | Consultar estado global y pasos del Saga Log. |

El endpoint de operaciones amplía la propuesta inicial para evitar devolver un `id_solicitud` antes de que Entrada lo haya asignado. Las consultas entre BFF y servicios pueden usar HTTP.

## 8. Un único acuerdo común para trabajar por separado

Este documento es el acuerdo compartido que el equipo está definiendo. **No es una entrega adicional que cada integrante deba preparar por separado.**

Los esquemas Avro, ejemplos y reglas se preparan una sola vez como parte del acuerdo, y todos utilizan las mismas versiones. Cada responsable implementa el comportamiento de su servicio contra esos contratos:

| Responsable del componente | Implementación independiente |
|---|---|
| Entrada | Ingreso desde BFF, asociación de operación y solicitud, resultados de atención y respuestas. |
| Orquestación | Coordinador, Saga Log, transiciones, comandos y cancelación del Trabajo. |
| Cotizaciones | Anulación de cotización y confirmación. |
| Seguimiento | Apertura/cancelación operativa, respuestas y actualización de la proyección. |
| BFF | Publicación de ingreso y API de consultas. |

Los comandos se acuerdan entre emisor y receptor. Los eventos describen hechos confirmados por el servicio que los publica. Los contratos se distribuyen como artefactos; no requieren importar el código interno de otro microservicio.
