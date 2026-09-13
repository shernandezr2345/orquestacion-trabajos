# Contratos, identidad y datos de laboratorio

Estado: contrato de Entrada **existente**; contratos restantes **diseñados aquí, pendientes de exportar a Avro y probar por sus propietarios**. Los nombres propuestos son una decisión de integración de estos planes, no evidencia de código existente.

## Tipos de mensajes y justificación

| Mensaje | Clasificación elegida | Motivo |
|---|---|---|
| SolicitarCotizacion | Comando distribuido | Pide una acción al propietario; puede fallar y aún no representa un hecho |
| SolicitudDePartnerListaParaAtencion | Evento de integración | Comunica una transición confirmada de Entrada con condiciones suficientes para iniciar atención |
| CotizacionRegistrada/CotizacionRechazada | Eventos de integración | Informan una resolución confirmada al dueño del Trabajo |
| TrabajoCreado.v1 | Evento de integración | Informa la creación confirmada e identidad de la petición; Seguimiento no consulta Orquestación |
| Actualizaciones CQRS de Entrada | Eventos con carga del estado público de lectura | Son fotografías versionadas de la solicitud y permiten converger sin aplicar todas las transiciones anteriores |
| TrabajoCreado y otros hechos del agregado | Eventos de dominio internos | Expresan cambios del modelo; un adaptador define los contratos públicos cuando hay destinatario |

Integración describe la frontera y carga de estado describe el contenido: no son categorías necesariamente excluyentes. Se eligen payloads suficientes para el efecto previsto, evitando llamadas síncronas al productor y evitando publicar el ORM completo. Tener varios campos no convierte cualquier mensaje en una fotografía completa de estado.

## 1. Fuente de verdad de Entrada

Consumir exactamente [SolicitudDePartnerListaParaAtencion.v1](../entrada-solicitudes-partner/docs/contratos/README.md), su [esquema](../entrada-solicitudes-partner/docs/contratos/solicitud-lista-v1.avsc) y su [ejemplo](../entrada-solicitudes-partner/docs/contratos/solicitud-lista-v1.ejemplo.json). No renombrarlo a `SolicitudRegistrada` ni usar el tópico CQRS.

| Dato vigente | Regla para Orquestación |
|---|---|
| `event_id`, `instante` | Identidad e instante originales; mantenerlos al deduplicar y auditar |
| `tipo`, `version_contrato` | `SolicitudDePartnerListaParaAtencion.v1`, `1` |
| `correlacion`, `id_solicitud` | UUID de solicitud; clave Pulsar igual a `id_solicitud` |
| `version_solicitud` | 2 para este recorrido vigente; no es versión de esquema |
| `id_partner`, `referencia_externa`, `categoria` | Conservar la referencia y datos necesarios; no releer Entrada |
| `tipo_solicitud`, `aprobacion_previa` | SINIESTRO/INSTALACION; booleano o nulo según contrato |
| `tipo_red` | GENERAL_HDA u HOMOLOGADA_PARTNER |
| `id_politica`, `version_politica` | Trazabilidad de la evaluación, no autorización para recalcularla |

El evento no contiene proveedor, importe, plazo SLA ni evidencia de ejecución. **Ninguno se infiere de `tipo_red` o de `id_politica`.** Orquestación conserva esas condiciones; Cotizaciones usa datos sintéticos propios para proponer; Seguimiento usa únicamente datos de esos contratos. No ampliar Entrada para proporcionar datos que no posee.

## 2. Canales y suscripciones

Todos los tópicos siguientes usan el prefijo `persistent://public/default/`. El prefijo se conserva para simplificar la integración con Entrada; no se cambia durante una recuperación.

| Tópico | Contrato lógico | Productor | Suscripción consumidora propuesta | Clave |
|---|---|---|---|---|
| `solicitud-partner-lista-v1` | SolicitudDePartnerListaParaAtencion.v1 | Entrada | `orquestacion-solicitudes-v1` | id_solicitud |
| `solicitar-cotizacion-v1` | SolicitarCotizacion.v1 | Orquestación | `cotizaciones-peticiones-v1` | id_trabajo |
| `cotizacion-registrada-v1` | CotizacionRegistrada.v1 | Cotizaciones | `orquestacion-cotizacion-registrada-v1` | id_trabajo |
| `cotizacion-rechazada-v1` | CotizacionRechazada.v1 | Cotizaciones | `orquestacion-cotizacion-rechazada-v1` | id_trabajo |
| `trabajo-creado-v1` | TrabajoCreado.v1 | Orquestación | `seguimiento-trabajos-v1` | id_trabajo |
| `cotizacion-registrada-v1` | CotizacionRegistrada.v1, revisiones Avro 1 y 2 | Cotizaciones | `seguimiento-cotizacion-registrada` | id_trabajo |
| `cotizacion-rechazada-v1` | CotizacionRechazada.v1 | Cotizaciones | `seguimiento-cotizacion-rechazada-v1` | id_trabajo |
| `cotizacion-registrada-v1` | lector v1 congelado | Cotizaciones | `e3-historico-01` a `e3-historico-05` | id_trabajo |

Una suscripción distinta entrega una copia a cada efecto lógico; réplicas de ese efecto comparten nombre. Los cinco históricos son dobles experimentales con datos propios. No se cuentan como servicios adicionales. `atencion` y `estadisticas` del laboratorio de Entrada no se reutilizan como si ya fueran las suscripciones empresariales.

Cada tópico contiene un tipo de registro para evitar un envelope genérico con payloads arbitrarios. Los dos resultados de cotización usan tópicos diferentes para no introducir uniones complejas. Shared exige ACK individual y no garantiza orden; el consumidor valida estado y concurrencia. [Documentación de mensajería, Pulsar 4.1](https://pulsar.apache.org/docs/4.1.x/concepts-messaging/).

## 3. Envelope propuesto para los nuevos contratos

| Campo | Tipo Avro propuesto | Semántica |
|---|---|---|
| `event_id` en eventos / `command_id` en comandos | string | UUID; uno por hecho/intención, no por intento de envío |
| `tipo` | string | Nombre lógico documentado, no nombre de clase importable |
| `version_contrato` | int | Revisión de estructura, independiente de versión del agregado |
| `instante` | string | ISO 8601 UTC con zona; reloj inyectable en pruebas |
| `correlacion` | string | id_solicitud a través del recorrido |
| `causacion` | string | ID del mensaje que originó este resultado/comando |

Los nuevos campos no se añaden retroactivamente a Entrada. TrabajoCreado y SolicitarCotizacion tienen IDs distintos y comparten como causación el event_id de Entrada; el resultado de cotización referencia el command_id. Mantener identidad, contenido e instante por salida durante todos sus reintentos.

**Versión compatible:** CotizacionRegistrada conserva `tipo="CotizacionRegistrada.v1"`, tópico `cotizacion-registrada-v1` y fullname Avro `CotizacionRegistradaV1` en ambas revisiones. El sufijo v1 identifica la familia compatible; `version_contrato=1|2` identifica revisión de schema. El lector v1 valida campos conocidos e ignora adiciones compatibles: no exige `version_contrato == 1`. Los demás contratos permanecen en revisión 1. Esta convención se prueba antes de congelar lectores; no basta que el broker acepte el schema.

## 4. SolicitarCotizacion.v1

Además del envelope de comando:

| Campos | Tipo | Regla |
|---|---|---|
| `id_peticion`, `id_trabajo`, `id_solicitud`, `id_partner` | string UUID | Orquestación crea la petición y el trabajo una sola vez |
| `categoria`, `tipo_solicitud`, `tipo_red` | string | Valores trasladados de la solicitud lista |
| `id_politica` | string UUID | Política aplicada originalmente |
| `version_politica` | int | Positivo |

Se solicita registrar una oferta de laboratorio para esa categoría/red. Cotizaciones es el único destinatario empresarial. No se le ordena ejecutar/cerrar el Trabajo. Las réplicas del servicio se reparten la intención; no la ejecutan cada una.

**Idempotencia:** mismo `id_peticion` y contenido equivalente devuelve el resultado ya registrado incluso si cambió el catálogo. Misma identidad con categoría/red/trabajo diferentes es conflicto, no una nueva cotización. Mantener en el registro una representación canónica de la petición original.

## 5. CotizacionRegistrada.v1 y CotizacionRechazada.v1

Ambos incluyen envelope de evento, `id_peticion`, `id_trabajo`, `id_solicitud`, `id_partner`, `version_catalogo` (int) y `version_cotizacion` (int, 1 en el mínimo).

La registrada agrega `id_cotizacion` y `id_proveedor` (UUID string), `importe_menor` (long >0), `moneda` (string, COP en el laboratorio), `categoria`, `tipo_red`. Guardar dinero en unidades menores enteras; por ejemplo COP 150.000,00 se representa como 15.000.000 con escala 2. No mezclar pesos enteros y centavos ni usar float. La convención es del laboratorio.

La rechazada agrega `motivo` (string: `SIN_OFERTA_PARA_CATEGORIA` o `SIN_PROVEEDOR_EN_RED`). No tiene un precio o proveedor ficticio. Falta total del catálogo/configuración no produce rechazo: es error técnico recuperable.

El consumidor de Orquestación verifica que petición, trabajo, solicitud y partner correspondan a su registro. Una respuesta desconocida no crea un trabajo. Resultados idénticos son no-op; propuesta y rechazo contradictorios no sobrescriben el estado ni generan otro evento.

## 6. TrabajoCreado.v1 y evolución de CotizacionRegistrada

TrabajoCreado incluye envelope de evento y `id_trabajo`, `id_solicitud`, `id_partner`, `id_peticion` (UUID string), `referencia_externa`, `categoria`, `tipo_solicitud`, `tipo_red`, `id_politica`, `version_politica`, `creado_en` (UTC), `estado="PENDIENTE_COTIZACION"` y `version_trabajo=1`. El record se llama `TrabajoCreadoV1`. Orquestación crea este evento y el comando de cotización en la misma transacción que el Trabajo, con dos salidas independientes. No garantizar orden entre sus publicaciones.

**E3 reformulado:** la revisión 2 de CotizacionRegistrada agrega solamente `duracion_estimada_minutos`, tipo Avro `['null','int']`, default null. Es la duración de ejecución estimada en la oferta sintética del proveedor, no un plazo de comienzo, compromiso SLA ni duración observada. Si se informa, debe ser >0; null es desconocido y no se convierte a cero.

El dato pertenece al catálogo de Cotizaciones: se carga en una nueva versión, se copia a la resolución persistida antes del outbox y no se relee al reenviar. El escritor v1 omite el campo; el escritor v2 lo envía cuando existe. Generar nuevas peticiones para nuevas ofertas; una petición ya resuelta conserva su resultado original. No enriquecer un evento antiguo con el mismo ID ni republicar históricos como si fueran nuevos.

Seguimiento v2 expone el detalle y permite filtrar por `duracion_maxima_minutos`: solo ofertas con duración conocida menor o igual al límite cumplen. Esto es capacidad nueva verificable, no solo añadir configuración. Orquestación y lectores v1 continúan usando los campos anteriores.

### Combinación de eventos en Seguimiento

Persistir un fragmento de creación y otro de resultado por id_trabajo, más inbox. Cada fragmento conserva tipo, ID, revisión y datos originales. No comparar version_trabajo con version_cotizacion: pertenecen a propietarios diferentes.

| Datos recibidos | Vista observable |
|---|---|
| Ninguno | 404 |
| Solo creación | PENDIENTE_COTIZACION; creacion_recibida=true |
| Solo propuesta | COTIZACION_REGISTRADA; creacion_recibida=false, referencia/fecha de creación null |
| Solo rechazo | COTIZACION_RECHAZADA; creacion_recibida=false |
| Creación + resultado coherente | Mismo resultado, creacion_recibida=true y datos completos |

Estos estados describen hechos recibidos, **no el estado confirmado de Orquestación**. Proyectar no autoriza transiciones empresariales. Rechazo y propuesta para una misma petición son incompatibles; un resultado con identidad distinta a creación también lo es. Revertir inbox y actualización ante conflicto. Preservar el fragmento previo y diagnosticar el mensaje, sin ACK exitoso.

Duplicado técnico: misma identidad y contenido normalizado → no-op. Duplicado empresarial: nuevo event_id, mismo trabajo/petición/tipo y datos de negocio → mismo efecto. Mismo hecho con datos distintos → conflicto. Comparar el contenido que conoce el lector; v1 no incorpora un campo desconocido a su modelo. V2 normaliza ausencia a null, pero nunca reemplaza una duración conocida con null por redelivery. Las dos revisiones describen nuevos hechos; no autorizan mutar un hecho ya recibido.

Concurrencia: crear o asegurar la fila por id_trabajo y bloquearla durante combinación/inbox. Creación tardía solo completa su fragmento y no borra el resultado. Si falta para siempre la creación, conservar vista parcial y reportar pendiente de proyección; no consultar otro servicio ni fabricar datos.

## 7. Compatibilidad que se debe demostrar

Mantener tópico y fullname Avro de CotizacionRegistrada; configurar y leer de vuelta `FULL_TRANSITIVE` para ese tópico. Conservar ambos schemas exportados, fixtures binarios y versiones de productores/lectores. El broker registra esquemas por tópico; la estrategia comprueba compatibilidad en ambas direcciones con el histórico. Se debe demostrar además la semántica con el SDK Python real. [Esquemas y compatibilidad, Pulsar 4.1](https://pulsar.apache.org/docs/4.1.x/schema-understand/).

| Escritor | Lector | Resultado esperado |
|---|---|---|
| v1 | v1 | Vista de creación y resultado de referencia |
| v2 | v1 congelado | Ignora dato adicional y mantiene su efecto |
| v1 histórico | v2 | Duración desconocida; conserva resto de la oferta |
| v2 | v2 | Muestra/filtra duración y conserva deduplicación |
| Cambio incompatible | Registro/CI | Rechazo comprobado en tópico de control separado |

El tiempo CI <1 min corresponde al job de compatibilidad definido, no a toda la suite. Exportar schemas desde los adaptadores concretos: un JSON ilustrativo no prueba Avro binario ni el comportamiento del lector/escritor.

## 8. Fixtures comunes y reconciliación

Preparar un manifiesto con IDs deterministas por corrida, semilla y checksum. No reutilizar las identidades de otro ensayo dentro de la misma base salvo al probar duplicados.

| Fixture | Resultado esperado |
|---|---|
| Siniestro aprobado, política con red general, oferta disponible | Entrada lista; un Trabajo; una petición; propuesta |
| Siniestro aprobado, red homologada y proveedor sintético asociado al partner | Misma secuencia respetando partner/red |
| Siniestro con aprobación false | Entrada rechazada; cero trabajos/cotizaciones por esa solicitud |
| Siniestro sin aprobación | Error HTTP de validación antes del registro |
| Instalación sin aprobación, política válida | Entrada lista; oferta según catálogo |
| Política ausente | RECIBIDA y pendiente interno; no evento público aún |
| Categoría sin oferta en catálogo presente | Petición procesada y rechazo empresarial persistente |
| Catálogo ausente | Error técnico, pendiente conservado; no rechazo empresarial |
| Oferta v2 con duración 30 / 90 / null | Filtro máximo 60 incluye solo la de 30; todas siguen consultables por ID |
| Resultado antes de TrabajoCreado | Vista parcial durable; creación posterior completa sin retroceso |
| Creación y resultado simultáneos | Una vista final, dos fragmentos coherentes y dos marcas inbox |
| Propuesta y rechazo de la misma petición | Conflicto visible; no sobrescribir ni confirmar como éxito |

Cada productor entrega sus schemas, ejemplos, validadores y lista de reglas semánticas. Los consumidores incorporan una copia versionada del contrato, con checksum, sin importar el paquete Python ni el ORM del productor. Los tests de contrato usan el mismo ejemplo, pero verifican bytes y reglas desde ambos lados.
