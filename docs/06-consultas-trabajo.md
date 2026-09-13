# 06 — Consultas de Trabajo

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: [05](05-pulsar-contratos.md). Las dependencias entre servicios están en el índice.

**Objetivo:** exponer `GET /trabajos/{id}` y `GET /trabajos?id_solicitud=...&limite=...&offset=...` con estado persistido y vínculos de la operación.

**Archivos:** `aplicacion/consultas.py`, `aplicacion/handlers/consultar_trabajos.py`, `infraestructura/vistas.py` para DTO de infraestructura si hace falta, operaciones SQL de consulta en `infraestructura/repositorios.py`, `api/trabajos.py`, OpenAPI exportado. No crear cinco archivos para una lectura.

**Decisión CQRS:** separar dependencias de lectura/escritura dentro de una API. La consulta usa un puerto/DTO propio sobre `trabajos`; no necesita una segunda tabla asíncrona. CQRS no implica replicar automáticamente el diseño de Entrada. La eventualidad visible viene de la llegada de resultados de Cotizaciones.

**Contrato HTTP:** 200 con ID/estado/versión/petición/resultado; 404 si no existe; paginación acotada con orden estable por fecha e ID. No fallback HTTP/SQL a Entrada. Health comprueba vida del proceso; readiness comprueba DB y estado de los bucles integrados, sin exigir que Cotizaciones esté sano.

**Pruebas:** consumir solicitud y observar PENDIENTE_COTIZACION; respuesta cambia a COTIZADO o COTIZACION_RECHAZADA; detenido Cotizaciones, GET sigue respondiendo pendiente. Filtrar por solicitud sin devolver registros ajenos. Endpoints de negocio mutadores entre servicios quedan excluidos; comandos llegan por Pulsar.

**Cierre:** demo GET sobre procesos reales y base propia, sin usar tablas de otro servicio. No crear proyector adicional salvo un experimento posterior que lo justifique.
