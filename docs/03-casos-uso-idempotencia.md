# 03 — Casos de uso e idempotencia

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: [02](02-modelo-trabajo-seedwork.md). Las dependencias entre servicios están en el índice.

**Objetivo:** coordinar puertos y salidas, todavía con dobles en memoria.

**Archivos:** `aplicacion/comandos.py`, `aplicacion/unidad_trabajo.py`, `aplicacion/handlers/{crear_trabajo,aplicar_cotizacion}.py`, `config/bootstrap.py`, dobles de reloj/IDs/repositorios/UoW en tests. La traducción del contrato de Entrada construye tipos propios; no pasa el Record Avro al agregado.

| Handler | Una UoW confirma |
|---|---|
| Crear trabajo | Inbox de evento de Entrada + Trabajo + petición con ID estable + TrabajoCreado y SolicitarCotizacion en outbox, cada uno con ID propio |
| Aplicar resultado | Inbox + transición/resultado del Trabajo; no emite cierre |

**Trabajo:** registrar contenido original normalizado y clave empresarial `id_solicitud`; misma solicitud coherente con nuevo event_id también es idempotente. Generar `id_trabajo`, `id_peticion` y `command_id` una vez, conservarlos en persistencia. Respuesta cotizada/rechazada se vincula por petición, no solo correlación. Construir bootstrap con funciones `componer_*`; sin clases fábrica redundantes.

**Pruebas:** fallo al preparar cualquiera de las dos salidas revierte Trabajo/inbox y ambas salidas; evento repetido después de cambiar configuración conserva petición; dato contradictorio produce conflicto. Si dos mensajes de resultado tienen IDs distintos pero mismo contenido de negocio, no repetir transición.

**Cierre:** flujo completo de casos de uso probado con dobles; documento explica que todavía no se ejecuta autónomamente ni existe durabilidad. No cerrar 05 por estas pruebas.
