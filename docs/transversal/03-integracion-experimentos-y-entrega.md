# Integración, experimentos y entrega del equipo

Estado: protocolo por ejecutar. Los valores de laboratorio elegidos aquí no son resultados ni requisitos originales, salvo los identificados como heredados.

## 1. Reparto y dependencias

| Rol | Servicio principal | Trabajo transversal | Revisión cruzada |
|---|---|---|---|
| Nicolás | Entrada y Reglas | Dataset de solicitudes y evidencia de recepción/CQRS | Contrato e idempotencia de Orquestación |
| Responsable Orquestación | Trabajos y comandos | Integración/infraestructura compartida y E4 | Contrato de creación para Seguimiento |
| Responsable Cotizaciones | Ofertas y resultados | E8, backlog y recuperación | Atomicidad/outbox de Entrada |
| Responsable Seguimiento | Vista de trabajos y consulta | E3 reformulado, esquemas y lectores antiguos; Cotizaciones implementa escritor v2 | Contratos de creación/resultados |

Los nombres de los compañeros quedan por asignar; no bloquean la preparación técnica. Infraestructura es responsabilidad transversal: **no reemplaza el desarrollo de Orquestación**. Cada integrante debe poder sustentar los cuatro servicios y los tres experimentos.

## 2. Orden para avanzar sin esperarse

| Hito | Trabajo simultáneo posible | Entregable/gate |
|---|---|---|
| H0: contrato | Cada responsable lee su plan y fija esquema del mensaje que produce | Schemas, ejemplo, tópico, suscripción, claves y reglas documentados |
| H1: modelo | Los tres completan 01–03 con dobles del contrato | Modelos, pruebas rojas/verdes y aplicación independiente |
| H2: persistencia | Los tres completan 04 | Base propia, migraciones, rollback y carreras demostradas |
| H3: primer intercambio | Orquestación/Cotizaciones completan 05; Seguimiento consume creación/resultados de contrato | Entrada real crea trabajo; comando real genera resultado; ningún import cruzado |
| H4: vista y evolución | Seguimiento congela v1 y desarrolla lector/consulta v2; Cotizaciones entrega escritor v2 | Duración estimada desde oferta; cuatro servicios automáticos y Orquestación sin cambios |
| H5: experimento | Equipo ejecuta E8, E3 y luego E4 | IDs conciliados y datos crudos por corrida |
| H6: entrega | Despliegue, repetición por otro integrante y guion | Cuatro servicios operativos; trazabilidad completa y límites |

Priorizar H3 temprano, antes de perfeccionar APIs o infraestructura. No desarrollar los tres servicios aislados hasta el final. Si un contrato propuesto cambia, registrar productor/consumidor afectados y actualizar fixtures antes de seguir, sin modificar unilateralmente Entrada.

Planificación sugerida, no compromiso de duración: primera sesión H0–H1; segunda H2–H3; tercera H4–H5; cierre H6 con margen de recuperación. Medir avance por gates, no por cantidad de archivos o tests. La fecha institucional debe verificarse en la plataforma del curso; no se asume vigente una fecha solo porque apareció en una conversación.

## 3. Infraestructura de laboratorio y entrega

**Desarrollo:** Pulsar standalone existente de Entrada y PostgreSQL locales. Cada servicio nuevo arranca en un único contenedor/proceso FastAPI, con HTTP y bucles internos de mensajería.

**Entrega grupal objetivo:** un Cloud Run Service por microservicio, con un contenedor de aplicación y un proceso ASGI por instancia. PostgreSQL externo en una instancia Cloud SQL propia por servicio, conservando D07 y registrando el costo de cuatro instancias; no almacenar las bases dentro de Cloud Run. Pulsar se despliega en VM con broker, BookKeeper y metadatos explícitos. Un clúster mínimo en un solo host es laboratorio sin alta disponibilidad. Registrar quorum/ensemble válidos según bookies reales; no afirmar redundancia con un único nodo.

**Entrada existente:** antes de afirmar cuatro despliegues uniformes, adaptar su composición para iniciar/cerrar evaluación interna, despacho y proyección desde lifespan, conservando bus interno durable, CQRS y contratos. Es tarea de integración pendiente de Nicolás, con pruebas de recepción/reinicio; esta actualización no modifica su código ni declara terminada esa adaptación. El primer smoke puede usar Entrada con su arranque actual, y debe identificarlo en el manifiesto.

**Cloud Run:** habilitar CPU/facturación por instancia para que la mensajería avance sin tráfico HTTP. Las instancias siguen siendo reemplazables. [Configuración oficial de CPU y facturación](https://docs.cloud.google.com/run/docs/configuring/billing-settings). Escuchar en `0.0.0.0:$PORT`; los puertos 8001/8002/8003 de los planes son convenios locales, no puertos externos fijos. Conservar los prefijos propios para el resto de configuración. [Contrato del contenedor](https://docs.cloud.google.com/run/docs/container-contract).

**Capacidad controlada para la POC:** elegir escala manual con 1 instancia por servicio. E4 fija Cotizaciones en 1/2/4; E8 la deshabilita con 0 y la restaura con 1. Usar una revisión activa sin revisiones antiguas etiquetadas que mantengan consumidores. Esperar y registrar el número efectivo de instancias y conexiones al broker antes de medir. Esta decisión sustituye mínimo/máximo 1 del ejemplo de la conversación para simplificar los experimentos; no demuestra autoescalamiento. [Escala manual oficial](https://docs.cloud.google.com/run/docs/configuring/services/manual-scaling).

Plantilla de operación futura, con proyecto/región/servicio de laboratorio explícitos; no ejecutada durante esta planificación:

```bash
gcloud run services update "$LAB_SERVICE" --project "$LAB_PROJECT" --region "$LAB_REGION" --scaling=1
```

El runner experimental cambia únicamente el valor a 0, 2 o 4 según el brazo, registra el estado previo y restaura la configuración al terminar, incluso si falla una aserción. No usar mínimo 0 de autoescalamiento ni matar una instancia como sustituto de una caída sostenida. No confundir escala solicitada con escala observada.

Antes de ejecutar, verificar documentación de la versión elegida y concretar Compose/automatización del clúster. Si solo hay standalone al cerrar, documentar la brecha de los 5 puntos de clúster y resolverla para la entrega; cambiar el nombre del contenedor no la resuelve. Kubernetes no es requisito.

Crear conectividad de Cloud Run hacia Cloud SQL y la VM de Pulsar (salida VPC y rutas/firewall según el entorno), direcciones anunciadas accesibles desde el contenedor, persistencia externa y migraciones como tarea previa, no al iniciar cada réplica. El Compose de Entrada anuncia `127.0.0.1` y sirve a procesos del host: no copiar esa dirección a clientes en contenedores o en otra máquina. El responsable de infraestructura entrega `.env.example` sin secretos y comandos de comprobación de conectividad.

**Suscripciones y retención:** preparar antes del tráfico; conservar cursores durante fallas. La configuración local de Entrada documenta backlog 50 MiB/30 min y retención 1 h/100 MiB; **no basta copiarla automáticamente** a una prueba más grande. Medir tamaño medio y tasa por tópico, dimensionar caída/histórico y margen. Evitar expulsión de pendientes; si se llena el broker, conservar salida en outbox y reportar presión del sistema.

El laboratorio no exige IAM de producción, roles SQL por cada capa, migración histórica universal o plataforma de replay. Sí exige evitar que un reset accidental destruya la evidencia: usar base/tópicos identificados por corrida, y separar “preparar entorno limpio” de “recuperar entorno existente”.

## 4. Manifiesto y evidencia por corrida

Crear futuros artefactos en `evidencias/<experimento>/<corrida>/` del repositorio de integración elegido por el equipo:

```text
manifiesto.json
operaciones.jsonl
metricas.csv
reconciliacion.json
logs/
informe.md
```

Manifiesto: fecha UTC/Bogotá, IDs de corrida, commits y hashes de imágenes, lockfiles, cambios locales relevantes, versión de schemas, número solicitado/observado de instancias completas por servicio, modo de escala y revisión activa, CPU/RAM/límites por contenedor y host, tasas ofrecidas/efectivas, dataset/semilla, tamaño de mensajes, configuración de pool y broker, suscripciones, retención, catálogo/políticas y ventanas.

`operaciones.jsonl` guarda intentos/aceptaciones y IDs; `metricas.csv` guarda intervalos y latencias crudas; reconciliación compara conjuntos de IDs por etapa. El informe incluye hipótesis, configuración, resultado, fallos, conclusión y límites. Capturas de consola sirven de apoyo, no reemplazan registros analizables.

Si se comparan tiempos entre procesos, sincronizar relojes o usar tiempos observados en el harness común. No mezclar hora de reenvío con instante del hecho. Para latencia de aceptación usar reloj monotónico del cliente; para tiempos distribuidos registrar método y posible error.

## 5. Smoke antes de medir

1. Arrancar bases y Pulsar, migrar, preparar suscripciones y cargar políticas/catálogo sintéticos.
2. Iniciar cada servicio completo por su único arranque FastAPI, sin imports ni bases compartidas; registrar la composición efectiva de Entrada hasta completar su adaptación. Verificar consumo sin peticiones HTTP y respuesta HTTP mientras el consumidor espera mensajes.
3. Registrar siniestro aprobado, instalación y rechazo en Entrada. Verificar que el rechazo de Entrada no crea Trabajo ni vista en Seguimiento.
4. Para admisibles, verificar solicitud → trabajo → petición → cotización → resultado aplicado en Orquestación.
5. Verificar que TrabajoCreado y el resultado llegan a Seguimiento; consultar la vista. Retrasar creación para observar parcial y luego completarla. Repetir sin pausa: todo avanza desde la solicitud inicial, sin pasos manuales por trabajo.
6. Reentregar un mensaje por cada frontera: un efecto persistente, sin mensajes empresariales nuevos indebidos.
7. Reiniciar procesos conservando estado y verificar convergencia. No pasar a carga mientras existan pérdidas/contradicciones no explicadas.

## 6. E8 — Recepción durante caída de Cotizaciones

**Artefacto evaluado: Entrada de Solicitudes de Partner. Servicio que falla: Cotizaciones. Seguimiento es observador adicional, no reemplazo del artefacto.**

**Ficha heredada:** Entrada confirma solicitudes y ninguna confirmada queda sin registro persistente recuperable. El fallo es Cotizaciones, manteniendo Entrada y persistencia operativas. La recuperación de cotizaciones y una latencia de recepción son extensiones de laboratorio.

**Parámetros elegidos:** dataset válido y admisible para la corrida principal; tasa λ determinada en calibración; 2 min de referencia, 5 min de caída y hasta 5 min de recuperación con tráfico activo. Meta adicional de aceptación: todas las operaciones únicas válidas del dataset se aceptan dentro de 5 s por intento y p95 ≤500 ms. Los 500 ms se reutilizan de E4; 5 s/5 min son límites nuevos del ensayo.

**Procedimiento:**

1. Registrar línea base e identificar réplicas de Cotizaciones. Crear operaciones de control y verificar el recorrido completo hasta resultado.
2. Detener todas las instancias completas de Cotizaciones: en Cloud Run aplicar escala manual 0; en local detener sus contenedores. Verificar ausencia de consumidores/publicadores activos antes de contar los 5 min. API, consumo y despacho deben quedar detenidos; mantener generador, bases, Pulsar y resto del sistema activos. Registrar latencia de la orden de parada aparte de la ventana de caída.
3. Registrar cada respuesta de Entrada, errores, outbox y trabajos pendientes. Comprobar continuidad positiva; cero pérdidas rechazando todo no es éxito.
4. Reiniciar Entrada o inspeccionar desde conexión nueva para demostrar que lo confirmado no era solo memoria. Conservar IDs, bases y suscripciones.
5. Restablecer Cotizaciones con escala manual 1 en Cloud Run o su mismo contenedor local, imagen y configuración conservadas. Medir recuperación desde la orden de restauración, incluyendo arranque, hasta drenar la cohorte mientras sigue la tasa λ. No borrar inbox ni reiniciar cursor.
6. Al terminar el plazo, cortar la cohorte de IDs originados durante la caída y reconciliarla aunque haya tráfico posterior. Reportar tiempo hasta completar esa cohorte y backlog total.

**Criterios:** `A` = solicitudes únicas cuya recepción fue confirmada; `D` = registros durables recuperables. Debe cumplirse `A − D = ∅`, con evidencia de pendiente/publicación para su continuación. Para la cohorte admisible, trabajos y peticiones únicos deben corresponder; cada petición termina en propuesta/rechazo válido o pendiente explícito. Éxito de recuperación exige cero pendientes de la cohorte al plazo, cero efectos duplicados y ausencia de mensajes perdidos, no cero reentregas.

**Dimensionamiento:** con tasa r destinada a Cotizaciones y caída T, backlog aproximado r×T; drenaje ideal B/(μ−r) requiere μ>r. Aumentar μ si no alcanza, registrar cambio y repetir; no cambiar umbrales después de ver resultados. Cuotas compartidas pueden propagar la caída, por lo que observar también outbox de Entrada/Orquestación.

**Evidencia adicional de Seguimiento:** una vez recibido TrabajoCreado, la vista muestra PENDIENTE_COTIZACION durante la caída y el resultado después de recuperar. Conciliar esos IDs y la creación recibida. Una vista parcial/faltante solo evidencia retraso de esa proyección, no pérdida de recepción: E8 se comprueba contra los registros durables de Entrada.

**Límites:** no demuestra 99,9 % mensual, pérdida de broker/base/host, recuperación regional ni cierre de trabajos durante la caída. Separar resultado de la medida literal E8 de la extensión de recuperación.

## 7. E3 reformulado — Evolución de CotizacionRegistrada

**Cambio aprobado por Nicolás:** la ficha anterior evoluciona TrabajoCerrado para Scoring. Se sustituye por CotizacionRegistrada para Seguimiento y se elimina el cierre de laboratorio. No afirmar que se ejecutó literalmente la ficha anterior; actualizar la descripción entregable y justificar la reformulación ante el tutor. La autorización del usuario no equivale a aceptación académica ya obtenida.

| Elemento de la ficha reformulada | Definición |
|---|---|
| Atributo / fuente | Extensibilidad; equipo propietario de Cotizaciones |
| Estímulo | Añadir duración estimada de oferta y una consulta que la aprovecha |
| Ambiente | Operación normal de laboratorio, v1 publicado, Orquestación y cinco lectores de prueba congelados |
| Artefacto | Contrato CotizacionRegistrada, productor Cotizaciones, Seguimiento y consumidores no interesados, registro de schemas y CI |
| Respuesta | Evolución compatible, duración opcional con default null; Seguimiento muestra/filtra; lectores no interesados funcionan sin cambios |
| Medidas | Cero redespliegues de no interesados por la evolución, cero incompatibilidades en tráfico válido, CI <60 s, esfuerzo <=2 días-persona, cero históricos republicados y ambos órdenes de actualización |

**Dato nuevo:** duracion_estimada_minutos proviene del catálogo sintético versionado de Cotizaciones y se persiste con la oferta. Es duración prevista, no SLA ni trabajo ejecutado. Seguimiento v2 muestra el dato y filtra por duración máxima; null queda desconocido y no entra en el filtro. Generar nuevas peticiones con duración 30/90/null; máximo 60 incluye solo 30.

**Preparación:** congelar escritor v1 de Cotizaciones, Seguimiento v1, Orquestación v1 y cinco dobles v1. Estos últimos mantienen la cardinalidad experimental heredada; Orquestación es un lector real adicional. Registrar hashes, funciones y límites de los dobles; no cuentan como cinco servicios. Preparar suscripciones y retención antes de producir histórico v1 mediante el recorrido normal de solicitudes.

Configurar/verificar FULL_TRANSITIVE en cotizacion-registrada-v1, mismo fullname CotizacionRegistradaV1 y tipo CotizacionRegistrada.v1. El sufijo identifica la familia compatible; version_contrato 1/2 identifica revisión. Lectores antiguos deben tolerar adiciones y no rechazar por igualdad estricta del número. El tópico de rechazo y TrabajoCreado permanecen sin cambios.

**Brazos:**

1. Referencia escritor v1 → lectores v1: conciliar ofertas y vistas.
2. Productor primero: escritor v2 con lectores antiguos intactos; luego Seguimiento v2.
3. Consumidor primero: Seguimiento v2 con escritor v1; luego escritor v2.
4. Histórico: lector v2 lee v1 retenido desde suscripción de ensayo; duración desconocida. Esto es incorporación de lector, no prueba de recuperación E8.
5. Reversión: drenar primero las salidas v2 de Cotizaciones y registrar ese punto; escritor vuelve a v1 con lector v2 activo, y nuevas ofertas sin duración no borran las anteriores. Este brazo no afirma rollback con outbox v2 pendiente. No cambiar contenido de mensajes ya persistidos para simular una revisión.
6. Control incompatible: cambio de schema rechazado en tópico aislado.

Para brazos comparativos se permiten bases nuevas. Para afirmar upgrade/rollback in situ, conservar datos y aplicar migración aditiva nullable antes del cambio de binarios; probar escritor/lector v1 contra SQL ampliado. Registrar ambos experimentos separadamente. Ningún brazo exige reconstrucción de toda la base ni republicación de históricos.

**Pruebas de efecto:** Orquestación aplica ofertas v1/v2 con el mismo artefacto; cinco dobles conservan sus efectos; Seguimiento v2 muestra y filtra; ambas permutaciones creación/resultado y redelivery convergen. Comparar conjuntos de IDs, no solo logs sin excepción. La duración conocida no se elimina al completar una creación tardía.

**Mediciones:** cero redespliegues de los cinco dobles y Orquestación por evolución; cero DLQ/incompatibilidad con mensajes válidos; job de compatibilidad <60 s (no toda la suite); esfuerzo real <=2 días-persona; cero republicaciones. Distinguir preparación inicial de lectores de redespliegue provocado por el cambio. Si no se mide un objetivo, queda sin evidencia.

**Límites:** los dobles no representan cinco semánticas empresariales omitidas. La nueva ficha conserva atributo y mecanismo, pero cambia productor, evento y consumidor interesado. Añadir una suscripción sin capacidad nueva o separar tópicos para v1/v2 no demuestra este experimento.

## 8. E4 — Escalamiento ante 4× demanda

**Herencia:** 4× solicitudes durante hasta 48 h; p95 aceptación ≤500 ms; cero mensajes perdidos; degradación marketplace ≤10 %. **Recorte elegido:** ensayo de 2 min de calentamiento y 10 min medidos, tres repeticiones por condición. No demuestra sostener 48 h.

Primero calibrar λ con una réplica y una carga bajo saturación (propuesta inicial: alrededor de 50 % de la capacidad sostenida observada). Registrar cómo se obtuvo y congelar λ antes de comparar. Si no se produce presión con 4λ, reportar que la capacidad inicial bastaba; no fabricar degradación ni concluir que escalar mejoró algo no medido.

| Condición | Llegada ofrecida | Instancias completas de Cotizaciones | Propósito |
|---|---:|---:|---|
| A | λ | 1 | Base |
| B | 4λ | 1 | Control a igual capacidad |
| C | 4λ | 2 | Primera ampliación |
| D | 4λ | 4 | Segunda ampliación |

Escalar Cotizaciones completo: cada instancia suma API, consumidor y despacho. Mantener los otros servicios constantes y registrar si el límite se desplaza a DB/Orquestación/broker. No atribuir el resultado exclusivamente al consumo ni afirmar escala independiente por componente. Comparar B/C/D con idéntica llegada, catálogo y recursos por réplica; costo total crece y se reporta. Mantener pool SQL por instancia, host del broker y payload; registrar que el máximo total de conexiones SQL crece con las instancias y comprobar que cabe en la base. Esperar estabilización del número observado de instancias antes del calentamiento.

Usar generador de tasa ofrecida controlada y registrar tasa realmente emitida: uno que espera cada respuesta puede bajar carga al saturar el sistema y ocultar el fallo. Rechazos de transporte/timeouts se incluyen; no calcular p95 solo sobre éxitos sin informar los fallos. Reordenar o alternar corridas para limitar sesgo de caché/calor; preparar datasets equivalentes.

**Métricas:** p50/p95/p99 de aceptación, tasa aceptada, throughput de nuevos efectos persistidos por etapa, latencia hasta resultado en Orquestación, solicitudes pendientes de evaluación, outbox, backlog por suscripción, edad del pendiente más antiguo, errores, CPU/RAM, conexiones DB y lag CQRS de Entrada, demora de vista en Seguimiento y cantidad/edad de vistas sin creación. Seguimiento no sustituye la lectura del estado autoritativo en Orquestación. No usar ACKs o número de mensajes como conteo empresarial.

Para estabilidad, registrar backlog en ventanas de 60 s y su tendencia durante la fase estable. Éxito técnico requiere capacidad efectiva al menos igual a llegada elegible, sin crecimiento sostenido de pendientes, y conciliación/drenaje final con plazo fijado (propuesta 5 min). Reportar pendiente máximo y pendiente al cierre; una recta promedio sola puede ocultar picos.

**Brecha marketplace y decisión explícita:** no añadir un quinto servicio completo dentro de estos planes. En el alcance base se mide E4 parcialmente y el criterio B2C queda **no demostrado**. Para ampliarlo, el equipo debe implementar/identificar una operación B2C real mínima, por ejemplo consulta de estado de un Trabajo de marketplace en Orquestación con dataset B2C, ejecutarla con carga constante antes/durante 4× B2B2C y describir exactamente los componentes que atraviesa. Un `/health` o un GET de Entrada no sirven como sustituto.

La operación B2C propuesta puede acreditar ese slice de consulta, no todo el marketplace. Definir su alcance con el tutor si se pretende cobertura literal. Medir `100 × (p95_durante / p95_base − 1)` ≤10 % y sostener su tasa de éxitos; reportar base, durante y errores. Este es un gate para afirmar E4 completo, no un requisito silenciosamente eliminado.

**Límites:** escalar manualmente demuestra efecto de capacidad horizontal, no autoescalamiento por lag. Si se promete autoescalamiento, añadir política/controlador y medir activación como experimento separado. 25 millones de requests diarios no son 25 millones de solicitudes de entrada. El dimensionamiento para 48 h es una estimación, no evidencia experimental de operación continua.

## 9. Correspondencia con la rúbrica

| Ítem | Puntos | Evidencia necesaria | Estado al escribir estos planes |
|---|---:|---|---|
| 4 servicios / 3 escenarios | 30 | Cuatro efectos empresariales y reportes E3/E4/E8 | Pendiente; E3 reformulado debe justificarse; E4 tiene brecha B2C/ventana |
| Comandos y eventos | 20 | SolicitarCotizacion y hechos públicos por Pulsar | Contrato Entrada existe; resto planificado |
| Clúster Pulsar | 5 | Despliegue/configuración y uso real de clúster | Standalone de Entrada es referencia local, no cierre |
| Tipos, esquemas y evolución | 5 | Avro, clasificación y matriz de compatibilidad | Entrada v1 existe; evolución E3 pendiente |
| Topología de datos | 5 | Cuatro propietarios/instancias/volúmenes y límites de host | Descentralizada propuesta |
| CRUD/ES en 4 servicios | 25 | Tablas, operaciones y consultas persistentes | Solo Entrada verificada en evidencia histórica |
| Actividades individuales | 5 | Contribuciones reales y revisión cruzada | Responsables por asignar salvo Nicolás |
| Despliegue | 5 | Imágenes/procesos accesibles y demo reproducible | Despliegue grupal pendiente |

No calcular una nota esperada a partir de planes. El tutor decide si el recorte experimental cumple el ítem; las limitaciones deben ser visibles.

## 10. Paquete final y sustentación

Entregar README grupal con servicios/rutas, arquitectura y topología, mapa de mensajes, catálogo de decisiones, instrucciones de arranque/parada/recuperación, tres informes con datos crudos, limitaciones, contribuciones y enlaces a commits/PRs reales. Incluir captura de cada servicio consultando su estado después de un reinicio y evidencia de componentes Pulsar. Separar resultados cuantitativos de inferencias sobre crecimiento del negocio.

Practicar una secuencia conjunta: solicitud admitida y rechazada → Trabajo → comando de cotización → respuesta → pausa/recuperación → vista de Seguimiento → evolución de duración estimada → comparador de carga. Cada persona debe explicar agregado/DTO, evento/comando, UoW/outbox/inbox, modelo de lectura, esquema/versión y significado de una métrica.

El 70 % corresponde a sustentación y 30 % a trabajo práctico según la rúbrica. No basta tener código generado que solo su autor entiende. Conservar para entrega 5 el backlog de Saga con compensaciones reales, BFF y refinamiento de vistas/mapa a partir de resultados; no introducirlos como requisito de cierre de estos incrementos.
