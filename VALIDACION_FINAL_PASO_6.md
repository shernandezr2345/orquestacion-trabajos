# Resultado - Reconstrucción Paso 6, Bloque 07

Fecha: 2026-09-13

## Archivos modificados

- `src/orquestacion_trabajos/infraestructura/consumidores.py`
- `tests/unitarias/infraestructura/test_consumidores_resultados_avro.py`

## Composición transaccional

Cada mensaje de resultado abre una única Session SQLAlchemy. Esa misma sesión se entrega a `SqlAlchemyInbox`, al factory de `AplicarCotizacionHandler`, a `SqlAlchemyRepositorioTrabajos` y a `SqlAlchemyOutbox`.

La identidad de Inbox es `(consumidor, event_id)`, donde consumidor es la suscripción estable de cada consumer:

- `orquestacion-cotizacion-registrada-v1`
- `orquestacion-cotizacion-rechazada-v1`

El consumer lee el Record Avro con `mensaje.value()`, mapea a `ResultadoCotizacionEntrada`, registra Inbox y, si no es una reentrega, ejecuta `AplicarCotizacionHandler` usando las dependencias SQL de la misma sesión.

## Flujo y recuperación

- `CotizacionRegistradaV1` aplica estado `COTIZADO`.
- `CotizacionRechazadaV1` aplica estado `COTIZACION_RECHAZADA`.
- El commit ocurre antes de `consumer.acknowledge(mensaje)`.
- Una excepción del handler o del commit provoca rollback y no ACK; la excepción se propaga.
- Una reentrega con igual consumidor, `event_id` y contenido no repite el handler ni el Outbox, pero realiza commit y ACK.
- Igual consumidor y `event_id` con contenido distinto conserva la semántica existente: lanza `InboxConflictError`, no aplica un segundo efecto y no hace ACK.
- El mismo `event_id` en las dos suscripciones crea dos registros Inbox independientes.

## Pruebas

Las pruebas específicas usan PostgreSQL real y cubren happy path registrada/rechazada, persistencia de Inbox, Trabajo y Outbox, misma sesión, orden commit antes de ACK, error del handler, error de commit, redelivery, conflicto Inbox y consumidores independientes.

```text
uv run pytest tests/unitarias/infraestructura/test_consumidores_resultados_avro.py -q
12 passed in 1.27s

uv run pytest -q
80 passed, 2 warnings in 4.61s

uv run ruff check .
All checks passed!

uv run mypy .
Success: no issues found in 56 source files
```

`ruff format --check .` falla sin ejecutar formatter. Reporta:

- `tests/unitarias/infraestructura/test_consumidor_entrada_avro.py` (previo, fuera del alcance)
- `tests/unitarias/infraestructura/test_consumidores_resultados_avro.py` (una línea de cierre de la prueba reconstruida)

`git diff --check` pasa. El estado Git contiene las dos modificaciones del Paso 6 y este reporte Markdown sin seguimiento. No se hizo commit.

## Confirmaciones de alcance

- No se integró lifecycle.
- No se implementó E3, E4, E8 ni Seguimiento.
- No se inició Pulsar real.
- No se modificaron Aggregate, estados de dominio, contratos, schemas Avro, Records Avro, mapeadores, `despacho.py`, `ciclo_vida.py`, rutas, ORM, Inbox ni Outbox.
