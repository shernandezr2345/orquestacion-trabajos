# Bloque 07 - Preparación de infraestructura Pulsar

Fecha: 2026-09-14
Estado: broker Apache Pulsar real disponible para el Paso 8.

## Docker

Docker Desktop está operativo:

```text
Client: 28.2.2
Server: Docker Desktop 4.42.1
Engine: 28.2.2
```

Antes de iniciar el broker no había contenedores en ejecución y los puertos TCP `6650` y `8080` estaban libres. El repositorio no contiene `docker-compose.yml`.

## Contenedor Pulsar

Se creó un único contenedor standalone de desarrollo:

```text
docker run -d --name orquestacion-pulsar -p 6650:6650 -p 8080:8080 apachepulsar/pulsar:4.1.3 bin/pulsar standalone
```

Datos verificados:

| Elemento | Valor |
| --- | --- |
| Contenedor | `orquestacion-pulsar` |
| Imagen | `apachepulsar/pulsar:4.1.3` |
| ID | `2327b04a1d5bdf7ed1d01eec861fa0730cb993c1b65e873beecf8579496ad12b` |
| Pulsar | `4.1.3` |
| Broker | `pulsar://localhost:6650` |
| Administración HTTP | `http://localhost:8080` |
| Clúster HTTP | `standalone` |

`docker ps` confirmó el estado `Up` y las publicaciones `6650:6650/tcp` y `8080:8080/tcp`. El endpoint `GET /admin/v2/clusters` respondió HTTP `200` con `["standalone"]`.

## Topics y suscripciones

Se utilizó el script existente como módulo, preservando los imports de proyecto:

```text
uv run python -m scripts.preparar_pulsar --listar
```

El script conectó correctamente al broker, verificó/creó estos topics y no publicó mensajes de negocio:

- `persistent://public/default/solicitud-partner-lista-v1`
- `persistent://public/default/solicitar-cotizacion-v1`
- `persistent://public/default/trabajo-creado-v1`
- `persistent://public/default/cotizacion-registrada-v1`
- `persistent://public/default/cotizacion-rechazada-v1`

El broker confirma estas suscripciones:

| Topic | Suscripción |
| --- | --- |
| `solicitud-partner-lista-v1` | `orquestacion-solicitudes-v1` |
| `cotizacion-registrada-v1` | `orquestacion-cotizacion-registrada-v1` |
| `cotizacion-rechazada-v1` | `orquestacion-cotizacion-rechazada-v1` |

## Límite de este paso

No se publicó ningún evento, no se crearon datos de negocio y no se ejecutaron pruebas de consumidores. El broker queda disponible para la validación real del Paso 8.

No se modificó código, configuración, contratos, Records Avro, PostgreSQL, Inbox, Outbox ni tests. No se hizo commit.

## Paso 8 - Validación real Entrada a Orquestación

Fecha/hora de la publicación: `2026-09-14T05:10:33.736322Z`.

### Ejecución

La aplicación se inició mediante su lifespan real de FastAPI con los consumers habilitados. Se abrieron dos suscripciones temporales de observación, una por salida del Outbox, antes de publicar el evento de entrada. Ambas fueron eliminadas al terminar la corrida.

Se publicó un único Record Avro `SolicitudDePartnerListaParaAtencionV1` en:

```text
persistent://public/default/solicitud-partner-lista-v1
```

La publicación usó `AvroSchema(SolicitudDePartnerListaParaAtencionV1)` y clave de partición igual a `id_solicitud`.

### Evidencia real

| Dato | Valor |
| --- | --- |
| `event_id` | `paso8-entrada-eb8d672fa3df` |
| `id_solicitud` | `paso8-solicitud-eb8d672fa3df` |
| `id_trabajo` | `7d69fe63-0f80-44b1-8779-f199d7187d4f` |
| Resultado de publicación | `(9,0,-1,-1)` |
| Lifecycle habilitado | `true` |
| Trabajos con esa solicitud | `1` |
| Estado final | `PENDIENTE_COTIZACION` |
| Inbox | `1` fila para `orquestacion-solicitudes-v1` y el `event_id` enviado |

Las dos filas Outbox asociadas a la misma solicitud quedaron en estado `PROCESADA`:

| Tipo | Destino |
| --- | --- |
| `TrabajoCreado.v1` | `persistent://public/default/trabajo-creado-v1` |
| `SolicitarCotizacion.v1` | `persistent://public/default/solicitar-cotizacion-v1` |

Las suscripciones temporales recibieron y deserializaron ambos mensajes mediante sus `AvroSchema` correspondientes:

| Mensaje observado | Identificador | Trabajo | Solicitud | Causación |
| --- | --- | --- | --- | --- |
| `TrabajoCreado.v1` | `event_id=c307b946-5572-4319-ac8e-1c67533a48a6` | `7d69fe63-0f80-44b1-8779-f199d7187d4f` | `paso8-solicitud-eb8d672fa3df` | `paso8-entrada-eb8d672fa3df` |
| `SolicitarCotizacion.v1` | `command_id=4afbf7b5-120e-44e3-8e27-195e3c3a2a27` | `7d69fe63-0f80-44b1-8779-f199d7187d4f` | `paso8-solicitud-eb8d672fa3df` | `paso8-entrada-eb8d672fa3df` |

### Duplicado controlado

Se publicó una vez más el mismo Record, con el mismo `event_id` y contenido. El broker devolvió `(9,1,-1,-1)`.

Evidencia observada después de esa repetición:

- Trabajo: `1` fila.
- Inbox: `1` fila.
- Outbox: `2` filas.
- Suscripciones temporales: ningún mensaje nuevo en los dos topics de salida.
- Backlog de `orquestacion-solicitudes-v1`: `0`.

Por tanto, la repetición no creó Trabajo ni salidas Outbox adicionales. La prueba no instrumentó la invocación interna del handler, por lo que solo se afirma la ausencia de efectos durables duplicados.

### ACK y transacción

**Evidencia real:** el backlog de la suscripción de Entrada fue `0` después de persistir el Trabajo, Inbox y ambas filas Outbox, y después de la repetición controlada. Esto demuestra que el broker recibió confirmación de los mensajes procesados.

**Observación/inferencia:** Pulsar y los logs vigentes no exponen una traza correlacionada que permita observar directamente el instante relativo de `commit` y ACK. El orden `session.commit()` seguido de `consumer.acknowledge(mensaje)` se verificó por inspección del consumer y por las pruebas de composición; no se presenta como medición temporal directa del broker.

### Validaciones técnicas

```text
uv run pytest -q
82 passed, 2 warnings in 5.19s

uv run ruff check .
All checks passed!

uv run mypy .
Success: no issues found in 57 source files
```

`uv run ruff format --check .` falla únicamente por `tests/unitarias/infraestructura/test_consumidor_entrada_avro.py`, archivo previo fuera del alcance. No fue modificado.

### Problemas y límites

- Infraestructura: ninguno durante la corrida real; broker, PostgreSQL y lifecycle se conectaron correctamente.
- Código: ninguno bloqueante detectado en este flujo mínimo.
- Limitación: no hay trazabilidad temporal de producción para demostrar observacionalmente `COMMIT -> ACK`; la evidencia directa disponible es persistencia durable, mensajes confirmados y backlog cero.

No se implementó E3, E4, E8 ni Seguimiento. No se modificaron dominio, contratos, Records Avro, Inbox, Outbox ni código de producción. No se hizo commit.
