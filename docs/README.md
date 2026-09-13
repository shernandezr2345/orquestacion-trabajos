# Plan de construcción — Orquestación de Trabajos

Estado: pendiente. Responsable: compañero de Orquestación por asignar. Repositorio previsto: `entrega4/orquestacion-trabajos`; paquete `orquestacion_trabajos`; módulo `trabajos`. Leer primero [decisiones](../00-decisiones-y-alcance.md), [contratos](../01-contratos-y-datos.md) y [base común](../02-base-de-implementacion.md).

## Resultado y límites

Recibir la solicitud lista de Entrada, crear exactamente un Trabajo, solicitar una cotización por Pulsar y conservar su resultado. Publicar `TrabajoCreado.v1` al crear el trabajo para que Seguimiento construya su vista. En E3, consumir el resultado de cotización evolucionado con el mismo lector v1 tolerante. La consulta permite observar el estado propio sin leer bases de otros servicios.

No implementar motor de workflows, Saga, matching, auditoría del partner, facturación, asignación automática ni toda la ejecución. No llamar a Cotizaciones por HTTP. No considerar un resultado de cotización como cierre del Trabajo.

## Modelo mínimo elegido

Agregado `Trabajo`: identidad propia, solicitud origen, partner, categoría, condición de red, referencia/versión de política, petición de cotización, estado, versión y resultado de cotización opcional. No se modelan datos ni comandos de ejecución/cierre en este alcance.

| Recorrido | Estado anterior | Operación | Estado siguiente |
|---|---|---|---|
| Atención normal | inexistente | Crear desde solicitud lista y generar petición | PENDIENTE_COTIZACION |
| Atención normal | PENDIENTE_COTIZACION | Aplicar CotizacionRegistrada | COTIZADO |
| Atención normal | PENDIENTE_COTIZACION | Aplicar CotizacionRechazada | COTIZACION_RECHAZADA |

Crear el Trabajo confirma dos salidas independientes: TrabajoCreado.v1 para Seguimiento y SolicitarCotizacion.v1 para Cotizaciones. Cada una conserva ID propio y se reintenta por separado. Reconstruir desde SQL no produce eventos nuevos.

Invariantes: una solicitud crea un Trabajo y una petición; respuestas ajenas o contradictorias fallan; resultados idénticos no repiten transición. No se implementa ejecución ni cierre. Seguimiento puede observar un resultado antes de que Orquestación lo aplique: no usar su vista como autoridad del Trabajo.

## Secuencia

| Incremento | Resultado | Dependencia |
|---|---|---|
| [01](01-base-tecnologica.md) | Entorno y app importables/instalables | Ninguna |
| [02](02-modelo-trabajo-seedwork.md) | Trabajo y reglas sin I/O | 01 |
| [03](03-casos-uso-idempotencia.md) | Casos de uso, UoW falsa y mensajes | 02 |
| [04](04-postgresql-uow-outbox.md) | Trabajo, inbox y outbox atómicos en PostgreSQL | 03 |
| [05](05-pulsar-contratos.md) | Consumo de Entrada y comando/resultados por Pulsar | 04; contratos de Cotizaciones, no su implementación |
| [06](06-consultas-trabajo.md) | Consultas del estado real y demo HTTP | 05 |
| [07](07-integracion-experimentos.md) | Fan-out, lector E3 y pruebas E8/E4 | 06; servicios reales para cierre grupal |
| [08](08-despliegue-sustentacion.md) | Imagen, despliegue y sustentación | 07 |

## Arranque y despliegue

Una instancia contiene un único proceso FastAPI: API y consumo de Pulsar administrados por lifespan y despacho del outbox. Se detiene, reinicia y escala el servicio completo. Los planes 01, 05 y 08 concretan la [base común](../02-base-de-implementacion.md) y el [protocolo de plataforma](../03-integracion-experimentos-y-entrega.md).
