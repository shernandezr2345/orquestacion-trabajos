# Decisiones de diseño y alcance

Estado: sustitución de Scoring por Seguimiento aprobada por Nicolás el 2026-09-13; detalles técnicos definidos para ejecutar los planes. Fuente normativa: [enunciado de entregas 4 y 5](../Entrega-004y005-POCArquitecturaEnunciado.pdf), páginas 2–4, y [rúbrica parcial](../Entrega-004-EntregaParcial.pdf), páginas 3–5.

## Precedencia

El enunciado y la rúbrica gobiernan lo exigido. Los acuerdos posteriores y la implementación vigente de Entrada gobiernan su frontera y su contrato. El análisis crítico inicial y el PDF del compañero explican alternativas, pero no reemplazan las correcciones posteriores. Cuando este plan amplía el laboratorio reducido de Entrada, lo declara expresamente.

No todas las conversaciones contienen la misma propuesta: se retiraron recomendaciones iniciales de CQRS opcional, Pulsar entre Solicitudes y Reglas, categorías artificiales, fachadas de reexportación y fragmentación excesiva de archivos. No se deben recuperar como requisitos.

## Registro de decisiones

| ID | Decisión | Por qué y costo aceptado |
|---|---|---|
| D01 | Sustituir Scoring por Seguimiento, junto con Entrada, Orquestación y Cotizaciones | Cambio aprobado por Nicolás. Cuatro servicios con persistencia y un recorrido automático, sin cierre preparado. |
| D02 | Un recorrido de solicitud, cotización y seguimiento | Evita desarrollar ejecución/cierre para probar el cuarto servicio. Cambia la ficha E3 y mantiene E8/E4 con sus límites. |
| D03 | Seguimiento consume TrabajoCreado y resultados de Cotizaciones | Construye una vista útil con mensajes reales; no decide el estado de Orquestación ni confirma que este aplicó una respuesta. |
| D04 | Una petición de cotización por trabajo en esta POC; cada resultado es propuesta o rechazo | Facilita deduplicación y reconciliación. Recotización, visitas y múltiples rondas quedan fuera. La clave de negocio debe dejar explícita esa restricción. |
| D05 | Proveedores, ofertas y duración estimada sintéticos y versionados | Permiten pruebas reproducibles con preparación inicial. No requieren fixtures de ejecución ni acciones manuales de cierre. |
| D06 | CRUD relacional en los cuatro servicios; no Event Sourcing | Los experimentos necesitan persistencia, atomicidad y recuperación. No necesitan reconstruir todos los agregados desde eventos. Inbox, outbox y proyecciones no son un event store. |
| D07 | Una instancia PostgreSQL propia por servicio; Cloud SQL en GCP y volumen propio en local | Conserva D07 y la topología descentralizada: quitar procesos separados no fusiona bases. Cuatro instancias administradas tienen costo fijo; registrarlo antes del despliegue. No compartir tablas ni credenciales. |
| D08 | Un proceso FastAPI por instancia, con consumo y despacho administrados por lifespan; CQRS según necesidad | Retira despliegues separados y simplifica la POC. API y mensajería comparten recursos, reinicio y escala. Orquestación/Cotizaciones consultan datos propios; Seguimiento proyecta en su base. La adaptación operativa de Entrada se identifica como pendiente de integración. |
| D09 | DDD táctico, módulos y capas hexagonales, seedwork local | Usa la organización del curso. No se impone una reestructuración por vertical slices ni un framework de arquitectura. Las reglas viven en el dominio, SQL en repositorios y ensamblaje en `config/bootstrap.py`. |
| D10 | No imponer dos módulos empresariales a cada servicio | Los dos de Entrada tienen una razón concreta y ya demuestran comunicación interna. Un módulo cohesivo por servicio nuevo basta; Seguimiento puede ser un módulo de proyección sin agregado empresarial; consulta, outbox y consumo no son dominios. |
| D11 | Copiar selectivamente ideas/piezas técnicas de Entrada; ninguna dependencia de su paquete | Evita un monolito distribuido por imports. Cada servicio controla su seedwork y lockfile. Los esquemas públicos sí se intercambian como artefactos versionados. |
| D12 | Efecto + inbox y outbox cuando hay salidas en una transacción; publicación fuera de ella; ACK después del commit | Cierra las ventanas de pérdida relevantes. Se acepta entrega al menos una vez y se deduplican efectos; no se promete exactamente una vez en la red. |
| D13 | Bucles síncronos en hilos del mismo proceso, suscripción Shared y un despacho por instancia productora | Reutiliza el cliente nativo sin bloquear el event loop HTTP. Cada réplica contiene todos los componentes; las reservas protegen despachos concurrentes. Shared no garantiza orden: reglas de estado, inbox y restricciones SQL protegen carreras. |
| D14 | Avro y evolución compatible de CotizacionRegistrada en el mismo tópico | E3 cambia de artefacto y consumidor. Se conserva compatibilidad v1/v2; Orquestación y lectores no interesados permanecen congelados. |
| D15 | Laboratorio limpio por corrida; recuperación conserva bases, volúmenes y suscripciones | No hay producción que migrar. Borrar una base o crear una suscripción nueva para hacer pasar recuperación invalida esa evidencia. |
| D16 | Saga y BFF completos para entrega 5 | No son condiciones del parcial. Estados pendientes e IDs ayudan a la continuidad, pero una cadena con reintentos no se presenta como Saga. |
| D17 | Un Cloud Run Service por microservicio; Pulsar en VM y PostgreSQL externo | Sigue la conversación posterior: CPU disponible fuera de HTTP y una instancia habitual por servicio. Para experimentos elegir escala manual 0/1/2/4 por reproducibilidad. Clúster Pulsar explícito para entrega; standalone solo para desarrollo, sin afirmar alta disponibilidad. |
| D18 | No esperar el código de otro compañero para iniciar | Los contratos propuestos y fixtures permiten avanzar por separado. La integración real sigue siendo un criterio obligatorio antes de declarar los cuatro servicios listos. |

## Alternativas consideradas

**Tres consumidores directos del evento de Entrada.** Es la menor implementación y sigue siendo adecuada para demostrar fan-out, persistencia y recuperación de consumidores. Se descarta como diseño final de los otros servicios porque omite el comando distribuido y no demuestra cotización ni seguimiento de trabajos. Puede utilizarse durante el primer smoke de Pulsar con su nombre de laboratorio.

**Ciclo empresarial completo.** Modelar proveedores verificados, matching, selección, ejecución, aprobaciones, cierre, facturación y crédito daría más fidelidad, pero añade servicios e integraciones ajenos al objetivo parcial. Se descarta para esta entrega.

**Recorte elegido.** Orquestación crea el Trabajo y genera, en una transacción, TrabajoCreado y SolicitarCotizacion como salidas independientes. Cotizaciones resuelve automáticamente desde su catálogo; Orquestación y Seguimiento reciben el mismo resultado. Se elimina la alternativa de Scoring y cierres preparados porque agregaba un segundo recorrido artificial al ensayo. E3 se reformula explícitamente; no se reescriben los documentos históricos de entregas anteriores.

**Costo aceptado:** no hay orden global entre creación y resultado. Seguimiento conserva dos fragmentos por trabajo, los combina de forma atómica y expone si falta la creación. No espera ni consulta al productor para completar datos; tampoco descarta la respuesta que llegue primero.

## Fronteras de negocio

| Servicio | Es dueño de | No decide |
|---|---|---|
| Entrada y porción de Reglas | Recepción, admisibilidad y condición de red según política identificada | Cobertura del seguro, proveedor seleccionado, precio, cierre |
| Orquestación | Identidad/estado del Trabajo, petición, evento de creación y aplicación de resultado | Precio ofertado, política inicial del partner, vista de Seguimiento |
| Cotizaciones | Petición recibida, oferta o rechazo y versión del catálogo sintético usado | Si el Trabajo está ejecutado/cerrado; cobertura aseguradora |
| Seguimiento | Vista local de creación y resultado; detalle consultable de la cotización | Estado autoritativo del Trabajo, precio ofertado y decisiones de negocio |

La agrupación Entrada + Reglas fue una adaptación aprobada para la POC. No significa que el TO-BE original despliegue esas dos capacidades juntas. Orquestación de Trabajos tampoco es el motor completo de reglas de Partner.

## Qué se considera terminado

El incremento termina cuando pasa su verificación y se registra evidencia reproducible. El servicio termina cuando funciona en procesos reales, sobre su base y Pulsar, con consultas y reinicio comprobados. El trabajo grupal termina cuando hay cuatro servicios desplegados, tres experimentos ejecutados y límites trazados a cada ficha.

No convertir una corrección futura en requisito del incremento presente: compatibilidad v1/v2 pertenece al experimento E3, escala a E4, Saga/BFF a entrega 5. Atomicidad, deduplicación y ACK correcto sí pertenecen a la primera integración real.

## Cambio explícito de E3

La autorización de Nicolás cubre la sustitución y actualización de estos planes. La ficha reformulada evoluciona CotizacionRegistrada para Seguimiento; no es la ficha original TrabajoCerrado/Scoring. Documentar el cambio en la entrega y contrastar su aceptación académica al sustentar. E8 conserva Entrada como artefacto y Cotizaciones como dependencia fallida. E4 no queda cubierto íntegramente por añadir Seguimiento: la operación B2C y las 48 horas siguen teniendo los límites documentados.

## Sustitución del despliegue separado

Decisión aprobada por Nicolás al pedir retirar los workers según [Organiza planes de microservicios (2)](codex://threads/01a09ac6-801e-7cb3-9345-bf4007becd44). D08/D13/D17 reemplazan la propuesta anterior de API y mensajería en procesos independientes. Se mantiene separación de responsabilidades en código; inicio, parada y escala pertenecen al servicio completo. No añadir Celery, Cloud Tasks, Worker Pools ni CDC para este alcance.

El ejemplo de la conversación se concreta con hilos de E/S administrados por `lifespan`: envolver `receive()` síncrono en `asyncio.create_task` no lo vuelve no bloqueante. El outbox sigue siendo durable; iniciar una tarea en memoria no reemplaza persistir la intención.

Para las corridas se elige escala manual de Cloud Run con 1 instancia habitual, en lugar de combinar mínimo/máximo 1 del ejemplo: permite una caída controlada a 0 y comparaciones 1/2/4 sin cambiar el artefacto. No se ensaya autoescalamiento por backlog. CPU y facturación por instancia siguen siendo necesarias. Fuera del protocolo, usar autoescalamiento con mínimo/máximo 1 es una alternativa operativa, no mezclar modos dentro de una comparación. Ver [configuración y procedimiento](03-integracion-experimentos-y-entrega.md).

Los cambios se limitan a esta carpeta. Entrada implementada conserva su composición actual; adaptar sus tareas internas al mismo ciclo de vida es un prerrequisito pendiente para afirmar un despliegue grupal uniforme. Su dominio, CQRS y contrato público permanecen vigentes.
