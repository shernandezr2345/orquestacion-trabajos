# Fuentes revisadas y lecciones incorporadas

Revisión realizada entre el 12 y el 13 de septiembre de 2026, hora de Bogotá. Se consultaron las nueve conversaciones con sus páginas históricas disponibles, requisitos y archivos locales. No se consultó NotebookLM de nuevo: se revisaron sus conclusiones citadas en las conversaciones y se priorizaron los documentos del proyecto.

## Actualización aprobada en esta conversación

El 2026-09-13 Nicolás aprobó reemplazar Scoring por Seguimiento de Trabajos después de revisar el diagrama y el costo de preparar cierres. Se retiraron sus ocho planes, fixtures de ejecución y comando de cierre. Se añadió TrabajoCreado a Orquestación; Cotizaciones publica resultados a dos suscripciones independientes. E3 ahora evoluciona CotizacionRegistrada con duración estimada opcional; E8 conserva Entrada como artefacto y Cotizaciones como fallo. Las referencias históricas siguientes conservan sus nombres/conclusiones originales: no son instrucciones vigentes para implementar Scoring.

La actualización posterior retira procesos/despliegues separados para API, consumo y despacho. Se sigue la conclusión final de [Organiza planes de microservicios (2)](codex://threads/01a09ac6-801e-7cb3-9345-bf4007becd44), que reemplazó su recomendación inicial de Worker Pools por mensajería dentro de FastAPI. La consulta de esa tarea se completó con su registro local, porque la lectura resumida omitía los últimos mensajes. No se volvió a consultar NotebookLM ni se presenta la revisión del tutorial allí citada como una nueva comprobación propia.

## Conversaciones

| Fuente | Aporte retenido y corrección relevante |
|---|---|
| [Organiza planes de microservicios (2)](codex://threads/01a09ac6-801e-7cb3-9345-bf4007becd44) | Acuerdo vigente: lifespan integra consumidores/outbox; un Cloud Run Service por microservicio, CPU fuera de HTTP, PostgreSQL externo y Pulsar conservado. Se concreta E/S síncrona en hilos internos y escala manual para experimentos. |
| [Iniciar microservicio de partners](codex://threads/01a096fb-8fab-78c1-91b0-56a4053d8896) | Dominio/microservicio/módulo/capa no son equivalentes. Seedwork local y CQRS de Entrada son acuerdos centrales; se retiró imposición de vertical slices y CQRS opcional. |
| [Revisa tutoriales de solución](codex://threads/01a096f0-75dc-7022-a3a7-17bb02184c4c) | Organización AeroAlpes en módulos/capas, puertos/adaptadores y eventos; tutoriales son scaffolding con simplificaciones, no implementación lista para producción. |
| [Analiza POC de entrega 4](codex://threads/01a096c6-b4ec-7542-941f-2090d6ab95b6) | Cuatro servicios con persistencia, comando distribuido, scoring basado en cierres y criterios medibles E3/E4/E8. Mercado B2C y consumidores históricos requieren alcance explícito. |
| [Audita el primer plan (2)](codex://threads/01a0978c-8344-7a00-8417-08cf173c6ebd) | Driver desde el inicio, import del cliente nativo, no red en unitarios/imports, wheel en entorno limpio. |
| [Audita el segundo plan](codex://threads/01a09794-18c0-7a51-a73f-e3fbaf932dd9) | Reglas basadas en aprobación/red del enunciado; identidad y reconstrucción; separar entidades/objetos valor/servicios; vocabulario español. |
| [Audita el tercer plan](codex://threads/01a097ca-e94c-7750-ae01-231a0c037bf7) | UoW por paso conserva recepción; bus interno no es publicación persistente; bootstrap en config; retirar reexportaciones inútiles; traducción hacia tipos propios sin cadena adicional innecesaria. |
| [Auditar cuarto plan](codex://threads/01a09828-e3b2-77e3-8cef-2922662a7c23) | Inbox/efecto/outbox atómicos, carrera por identidad/versiones, reserva vencida no modifica otra; pytest PostgreSQL y Postman cumplen fines distintos. |
| [Auditar quinto plan](codex://threads/01a09884-472c-77a2-95a7-08de89b1735d) | Bus interno durable para módulos; Pulsar público y CQRS según rol; no plataforma de replay; SQL en repositorio, rutas únicas y mapeadores SQL/Avro separados. |
| [Audita sexto plan](codex://threads/01a098e8-2fa3-7073-b140-508c9d9b6341) | API única y proyector separado en Entrada; no migración productiva/roles innecesarios; proyección sin retroceso; agrupación de archivos y funciones de composición suficientes. |

Una respuesta antigua puede describir un diseño luego retirado. Se contrastaron especialmente las correcciones del plan 05 con el plan 07 actual de Entrada: el fan-out reducido prueba mecanismos; no autoriza afirmar el ciclo empresarial de tres servicios con simples registros de recepción.

## Documentos y código

| Fuente local | Uso en estos planes |
|---|---|
| [Enunciado conjunto](../Entrega-004y005-POCArquitecturaEnunciado.pdf), pp. 2–4 | Python, mínimo cuatro servicios, comandos/eventos, Pulsar, almacenamiento y distinción parcial/final |
| [Rúbrica parcial](../Entrega-004-EntregaParcial.pdf), pp. 3–5 | 100 puntos y peso de sustentación; no confundir propuesta con evidencia |
| [Proyecto Hogar de los Alpes](../../Proyecto-202614-HogarDeLosAlpes.pdf), pp. 9–13 y 17–19 | Aprobación previa, red homologada, ciclo real, crecimiento y scoring basado en historia |
| [Plan del compañero](../Plan_POC_Entrega_4_Hogar_de_los_Alpes_v2.pdf) | Intención de cuatro servicios y E3/E4/E8; se corrigen reparto, comandos y significado de Scoring |
| [Análisis crítico](../analisis-critico-plan-poc-v2.md) | Fuentes históricas, discrepancias de fichas, fallos y protocolo original; sus propuestas no se tratan todas como aprobadas |
| [Arquitectura entrega 2](../../entrega2/hogar_alpes_entrega_2/README.md) | Continuidad de contextos y decisiones tácticas |
| [Recepción durante caída de Cotizaciones](../../entrega3/escenario-2-decisiones-y-justificacion.md) | Alcance preciso de resiliencia y reconciliación por ID |
| [Planes vigentes de Entrada](../entrada-solicitudes-partner/docs/plans/README.md) | Acuerdos locales y estado 01–06 frente a 07–08 pendientes |
| [Contrato público](../entrada-solicitudes-partner/docs/contratos/README.md) | Evento, campo, tópico, esquema y semántica reales |
| [Modelo implementado](../entrada-solicitudes-partner/docs/modelo-dominio.md) | Dos módulos y condiciones de red/admisibilidad |
| [Plan 07 de Entrada](../entrada-solicitudes-partner/docs/plans/07-integracion-experimentos.md) | POC reducida de mecanismos y límites frente a los escenarios originales |
| [Evidencia 06](../entrada-solicitudes-partner/docs/plans/evidencia-06-cqrs-api.md) | 253 pruebas históricamente documentadas, 55 de integración y límites de CQRS |

Se contrastaron además las fichas enviadas de E3/E4/E8 en la extracción conservada en `tmp/pdfs/entrega4-review/entrega3-enviada.txt`. Esta ruta es evidencia auxiliar local de una revisión previa, no un archivo que deba copiarse como entregable. E3 usa TrabajoCerrado y cinco no interesados; E4 fija 500 ms/4×/10 %; E8 mide cero confirmadas sin registro durable. E3 citado aquí es la ficha histórica; la ficha vigente propuesta en estos planes está reformulada. Los documentos `escenario-1/2/3-decisiones-y-justificacion.md` de entrega 3 describen tres escenarios de resiliencia: su número local no se debe confundir con E3 de extensibilidad.

La referencia Git de Entrada al inspeccionar fue `0f4d04fab155966f88ef006f036bf2c0065fb8cb`, con modificaciones y archivos no versionados. Por ello los planes se basan en la **copia de trabajo**, no afirman que todo esté en ese commit. No se alteraron esos cambios.

## Lecciones traducidas a acciones verificables

| Error o confusión previa | Regla concreta del nuevo plan | Dónde se comprueba |
|---|---|---|
| Un nombre de servicio se usa para un consumidor que solo imprime | Efecto empresarial, tablas y consulta propios | Cortes A/B, incremento 06 de cada servicio |
| Se confunde registrar evento en memoria con entregarlo | Separar pendientes del agregado, commit, publicación y ACK | 03/04/05, pruebas entre ventanas de falla |
| Se afirma comunicación porque existen imports/handlers | Mostrar procesos reales e IDs en tablas del receptor | Smoke e integración 05/07 |
| Ausencia de política se vuelve rechazo empresarial | Error técnico conserva pendiente; rechazo solo con datos válidos | Catálogo de Cotizaciones y fixtures comunes |
| Un handler recibe el agregado ajeno | Traducir mensaje a valores propios | Consumidores/mapeadores de 05 |
| UoW/bootstrap ejecutan SQL empresarial | Delegar al repositorio con misma Session | Organización y revisión de 04 |
| Resultado llega antes de creación | Guardar fragmentos y combinar por trabajo con inbox atómico; creación tardía no borra resultado | Planes 02–05 de Seguimiento |
| Vista se confunde con estado autoritativo | Informar hechos recibidos y completitud; Orquestación decide su propio estado | Contrato y API de Seguimiento |
| Se copian rutas en varios lugares | Fuente única simple de destinos por servicio | `config/rutas.py` |
| Persistencia importa Pulsar por un mapeador | Separar conversión SQL y Avro | Test de aislamiento e import del wheel |
| Se divide cada conversión/consulta en otro archivo | Agrupar por responsabilidad; no una clase por archivo obligatoria | Base común, incremento 06 |
| Se agregan roles, migración histórica y replay sin objetivo | Laboratorio limpio y recuperación de sus propios pendientes | Alcance y protocolo experimental |
| Versiones de agregado guardadas sin proteger carreras | UPDATE condicional/bloqueo y UNIQUE con prueba concurrente | Integración PostgreSQL 04 |
| Una reserva vieja puede confirmar trabajo nuevo | Token de reserva y actualización condicional | Tests de outbox |
| Un mensaje con ACK antes del commit desaparece | ACK solo tras efecto/inbox confirmados | Caída después de commit antes de ACK |
| Una cotización se convierte en cierre ficticio | Eliminar cierre y su fixture; observar cotización con Seguimiento | Recorrido vigente y planes de Orquestación |
| El cuarto servicio necesita un hecho fuera del recorrido | Sustituir Scoring por vista de trabajos; reformular E3 explícitamente | Decisión aprobada y ficha E3 reformulada |
| Se despliega API/consumo/despacho por separado sin necesidad de la POC | Un proceso por instancia, ciclo de vida integrado y pruebas HTTP/mensajería | D08/D13/D17 y planes 01/05/08 |
| Un bucle síncrono bloquea el event loop o queda huérfano al cerrar | Hilos administrados, timeouts y cierre acotado; estado de componentes visible | Base común y pruebas de composición |
| Más aceptación se presenta como más capacidad | Throughput persistido, comparadores y backlog | E4 |
| Se borra el estado para probar recuperación | Conservar volúmenes, IDs e inbox/suscripciones | E8 |

Referencias de implementación inspeccionadas: [UoW SQL](../entrada-solicitudes-partner/src/solicitudes_partner/seedwork/infraestructura/unidad_trabajo_sqlalchemy.py), [rutas](../entrada-solicitudes-partner/src/solicitudes_partner/config/rutas.py), [proyección](../entrada-solicitudes-partner/src/solicitudes_partner/modulos/solicitudes/infraestructura/proyecciones.py), [carreras](../entrada-solicitudes-partner/tests/integracion/test_concurrencia.py), [reservas/outbox](../entrada-solicitudes-partner/tests/integracion/test_outbox.py) y [versiones de proyección](../entrada-solicitudes-partner/tests/integracion/test_proyeccion.py). Son referencias para aprender y adaptar, no una dependencia compartida ni permiso para copiar el dominio.

## Comprobación técnica externa

Se utilizó `find-docs` con Context7 y documentación oficial Pulsar 4.1 para contrastar ACK individual en Shared y compatibilidad Avro. Referencias: [mensajería](https://pulsar.apache.org/docs/4.1.x/concepts-messaging/), [esquemas](https://pulsar.apache.org/docs/4.1.x/schema-understand/) y [cliente Python con Avro](https://pulsar.apache.org/docs/4.1.x/schema-get-started/). La implementación deberá comprobar flags/API concretos contra las versiones que bloquee cada servicio; no se trasladan ejemplos Java a Python sin verificar soporte.

Para esta actualización se verificaron [lifespan de FastAPI](https://fastapi.tiangolo.com/advanced/events/), [concurrencia y funciones síncronas](https://fastapi.tiangolo.com/async/), [recepción síncrona del cliente Python Pulsar](https://pulsar.apache.org/api/python/3.8.x/pulsar.Consumer.html), [CPU/facturación Cloud Run](https://docs.cloud.google.com/run/docs/configuring/billing-settings), [contrato de ejecución](https://docs.cloud.google.com/run/docs/container-contract) y [escala manual](https://docs.cloud.google.com/run/docs/configuring/services/manual-scaling). La referencia Python accesible es 3.8.x: confirma recepción bloqueante, timeout y distinción close/unsubscribe; no cambia el lockfile 3.13.0 de referencia. Validar métodos y cierre con la versión finalmente instalada. Se eligieron hilos administrados y escala manual como concreciones del plan, no como citas literales del tutorial.

No se construyó grafo: no hay `graphify-out/graph.json` consultable en el proyecto. La revisión fue de archivos y conversaciones. No se ejecutó nuevamente la suite de Entrada, no se hicieron cargas, despliegues, commits ni cambios al servicio durante esta planificación.
