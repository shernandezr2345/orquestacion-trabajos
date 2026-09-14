# Paso 9 - Validación real de resultados de cotizaciones

Fecha: 2026-09-14
Broker: Apache Pulsar 4.1.3, `pulsar://localhost:6650`.

## Ejecución

Se inició el lifespan real de FastAPI con los consumers habilitados. Se crearon dos Trabajos controlados mediante el flujo real de Entrada porque el Trabajo usado en el Paso 8 ya no existía en PostgreSQL. No se invocó ningún handler manualmente.

Cada resultado se publicó con el Record Avro y schema del consumer:

- `AvroSchema(CotizacionRegistradaV1)` en `persistent://public/default/cotizacion-registrada-v1`.
- `AvroSchema(CotizacionRechazadaV1)` en `persistent://public/default/cotizacion-rechazada-v1`.

## Evidencia Real

### CotizacionRegistrada.v1

| Campo | Valor |
| --- | --- |
| `event_id` | `paso9-registrada-c6a642e752d7` |
| Publicación Pulsar | `(12,0,-1,-1)` |
| Trabajo | `dbb7f6ca-6d64-4a7f-9f12-5ad5e0fdc1c7` |
| Solicitud | `paso9-solicitud-registrada-c6a642e752d7` |
| Estado inicial | `PENDIENTE_COTIZACION`, versión `1` |
| Estado final | `COTIZADO`, versión `2` |
| Resultado persistido | `ACEPTADA`, `importe_menor=15000000`, `moneda=COP`, `id_cotizacion=paso9-cotizacion-c6a642e752d7` |
| Inbox | una fila en `orquestacion-cotizacion-registrada-v1` |
| Efecto Outbox | una fila `CotizacionAplicada`, estado `PENDIENTE` |

Se repitió exactamente el mismo Record; el broker respondió `(12,1,-1,-1)`. Tras la repetición hubo un Trabajo, una fila Inbox, una fila `CotizacionAplicada`, estado `COTIZADO` y versión `2`.

### CotizacionRechazada.v1

| Campo | Valor |
| --- | --- |
| `event_id` | `paso9-rechazada-c6a642e752d7` |
| Publicación Pulsar | `(13,0,-1,-1)` |
| Trabajo | `90e669dd-b3a8-4563-899e-f03241f7274c` |
| Solicitud | `paso9-solicitud-rechazada-c6a642e752d7` |
| Estado inicial | `PENDIENTE_COTIZACION`, versión `1` |
| Estado final | `COTIZACION_RECHAZADA`, versión `2` |
| Resultado persistido | `RECHAZADA`, `motivo=SIN_OFERTA_PARA_CATEGORIA` |
| Inbox | una fila en `orquestacion-cotizacion-rechazada-v1` |
| Efecto Outbox | una fila `CotizacionAplicada`, estado `PENDIENTE` |

Se repitió exactamente el mismo Record; el broker respondió `(13,1,-1,-1)`. Tras la repetición hubo un Trabajo, una fila Inbox, una fila `CotizacionAplicada`, estado `COTIZACION_RECHAZADA` y versión `2`.

### Identidad y ACK

Las filas Inbox pertenecen a suscripciones distintas:

- `orquestacion-cotizacion-registrada-v1`
- `orquestacion-cotizacion-rechazada-v1`

Por tanto, los consumers tienen identidades Inbox independientes. Las estadísticas del broker mostraron backlog `0` para ambas suscripciones tras los eventos iniciales y los duplicados.

## Observación/Inferencia

La confirmación del broker y el backlog cero demuestran que los mensajes fueron ACKed después de que los efectos persistidos fueran observables en PostgreSQL. El orden temporal exacto no fue medido mediante traza: se infiere de la implementación actual, que llama `session.commit()` antes de `consumer.acknowledge(mensaje)`.

## Hallazgo del Paso 9 y cierre del Paso 10

Durante la corrida original, el handler registró `CotizacionAplicada` en Outbox y el dispatcher informó `No hay productor para tipo CotizacionAplicada`; esas filas quedaron `PENDIENTE`. La evidencia del Paso 9 se conserva como observación histórica.

La decisión D19 formalizó que `CotizacionAplicada` es un evento interno de dominio: no tiene contrato público, topic, Record Avro ni consumer externo. En el Paso 10 se retiró únicamente su registro desde `AplicarCotizacionHandler` hacia `RegistroSalidas`; el agregado continúa registrando el evento interno. Las pruebas PostgreSQL de ambos consumers de resultados verifican ahora que no se crea ninguna fila Outbox al aplicar una cotización.

## Calidad

```text
uv run pytest -q
82 passed, 2 warnings in 4.62s

uv run ruff check .
All checks passed!

uv run mypy .
Success: no issues found in 57 source files
```

`uv run ruff format --check .` falla solo por `tests/unitarias/infraestructura/test_consumidor_entrada_avro.py`, archivo previo fuera del alcance y no modificado.

## Confirmaciones

- `CotizacionRegistrada.v1` funcionó de extremo a extremo.
- `CotizacionRechazada.v1` funcionó de extremo a extremo.
- Los estados persistidos son correctos.
- Inbox evitó efectos durables duplicados.
- Los consumers tienen identidades Inbox independientes.
- El orden `COMMIT -> ACK` es evidencia de código y confirmación indirecta de broker, no una medición temporal directa.
- `CotizacionAplicada` permanece como evento interno y no entra al Outbox de integración.
- No se implementó E3, E4, E8, Seguimiento, Saga ni BFF.
- No se modificaron dominio, contratos, Records Avro, topics, subscriptions, Inbox, Outbox ni infraestructura Pulsar.
- No se hizo commit.
