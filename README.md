# Orquestación de Trabajos

POC de HdA con Saga de atención. Consume solicitudes de Entrada, crea Trabajo/Saga,
coordina cotización y seguimiento y registra el resultado en Entrada. Las compensaciones
cancelan efectos reales y esperan confirmaciones de los participantes. Cada servicio
conserva su propia base.

[Auditoría y pruebas de integración de cinco servicios](../bff-partners/docs/evidencias/saga-real/README.md).
Cambios locales verificados, sin commit. La consulta HTTP de Saga/Log sigue pendiente.

## Estructura

Todo el código instalable vive en `src/orquestacion_trabajos/`:

- `api/`: consultas HTTP y salud.
- `config/rutas.py`: catálogo de fuentes (tópico y suscripción) y destinos de publicación.
- `config/bootstrap.py`: construye handlers, consumidores y despacho con sus dependencias.
- `config/persistencia.py`: compone la UoW y verifica los destinos pendientes.
- `config/procesamiento.py`: compone 17 ciclos y coordina su cierre con presupuesto total.
- `config/settings.py` y `database.py`: configuración y conexiones.
- `modulos/trabajos/dominio/`: Trabajo y reglas de transición.
- `modulos/trabajos/aplicacion/`: casos de uso y puertos; no importa SQL, Pulsar ni mapeadores de infraestructura.
- `modulos/trabajos/infraestructura/`: repositorios, UoW, consumidores, despacho y esquemas Avro.
- `seedwork/aplicacion/`: contrato de UoW y errores de persistencia.
- `seedwork/infraestructura/`: metadata, inbox/outbox, UoW SQL, consumidor, publicador y ciclos genéricos.
- `seedwork/dominio/`: entidades, valores y eventos locales.

[Correcciones de esta POC](docs/correcciones-poc-2026-09-14.md).
[Contratos](docs/contratos/README.md).

## Ejecutar localmente

```bash
uv sync --locked --group dev
export ORQUESTACION_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/orquestacion_trabajos'
export ORQUESTACION_PULSAR_URL='pulsar://localhost:6650'
export ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=true
uv run --locked alembic upgrade head
uv run --locked uvicorn orquestacion_trabajos.api.app:create_app --factory --host 127.0.0.1 --port 8001
```

Crear previamente la base elegida. El arranque prepara productores/consumidores con
sus schemas Avro; el script histórico preparar_pulsar.py no debe usarse para
reconfigurar tópicos con schemas ya registrados. `.env.example` es una plantilla: copiarla a `.env`
no carga sus variables automáticamente. El arranque usa las variables exportadas.
`ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=false` permite servir consultas sin mensajería; readiness responde 503.
Sin `ORQUESTACION_DATABASE_URL`, liveness sigue disponible y las consultas responden 503.
Cada app crea y cierra su propio engine; importar módulos no crea recursos globales.

Consultas: `GET /trabajos/{id}` y `GET /trabajos?id_solicitud=…`.
`/health/live` responde 200; `/health/ready` responde 503 cuando falla la base,
no están conectados los componentes requeridos, hay un consumidor pausado o falla el despacho.
La salud no reemplaza una prueba de publicación de extremo a extremo.

## Verificar

La suite recrea tablas: `ORQUESTACION_DATABASE_URL` debe apuntar a una base
exclusiva de pruebas, nunca a la base con datos de una demostración.

```bash
uv run --locked pytest tests -q
uv run --locked ruff check src tests scripts migraciones
uv run --locked ruff format --check src tests scripts migraciones
uv run --locked mypy src tests migraciones
uv run --locked python scripts/export_contracts.py --check
uv run --locked python scripts/verify_distribution.py
```

Para probar los cuatro microservicios desde la raíz del workspace:

```bash
python proyecto/entrega4/integracion/scripts/run_local.py
```

## Garantías y límites

- El handler abre la UoW y confirma Inbox, Trabajo y salidas en una misma transacción.
  El consumidor genérico hace ACK solo después del retorno exitoso.
- Una reentrega compara el mensaje completo; un resultado terminal distinto se rechaza.
- La petición del resultado debe corresponder al Trabajo y las actualizaciones SQL
  comprueban la versión leída para evitar sobrescrituras concurrentes.
- El despacho procesa una fila por transacción usando `FOR UPDATE SKIP LOCKED`.
  Conserva la fila pendiente si falla la publicación y vuelve a intentar.
- La entrega es al menos una vez: caer después del envío y antes del commit puede
  repetir el mismo mensaje; la deduplicación pertenece al consumidor.
- Los errores transitorios conocidos hacen NACK. Un mensaje contradictorio pausa el consumidor
  sin ACK; conservar la evidencia y corregir la causa antes de reiniciar.
- 17 ciclos no daemon: nueve consumidores de eventos y ocho despachos de outbox.
  La parada se señala a todos y comparte un presupuesto de 9 segundos. Cada hilo cierra su transporte.
  Si un hilo sigue vivo, el cierre falla visiblemente y no se dispone su engine.
- Se mantienen tablas y variables de esta POC. El outbox conserva bloqueo SQL durante el envío
  (una fila por destino); no incorpora las reservas con vencimiento de Entrada.
  La validación exhaustiva del envelope y la inyección de reloj/IDs del plan 02 siguen pendientes.

Pulsar/SQL tienen esperas acotadas de conexión y publicación. Esto no constituye
una certificación de alta disponibilidad ni de cierre bajo todas las fallas posibles.

## Migraciones

`migraciones/versions/0001_persistencia.py` crea el esquema inicial equivalente al ORM.
Las revisiones contienen operaciones explícitas y no dependen del modelo futuro.
La API no crea tablas; ejecutar `uv run --locked alembic upgrade head` antes de arrancarla.

```bash
uv run --locked alembic current
uv run --locked alembic check
uv run --locked alembic revision --autogenerate -m "describe_schema_change"
```

Revisar cada revisión generada antes de aplicarla. Se requiere
`ORQUESTACION_DATABASE_URL` explícita. Para revisar el SQL sin conexión:
`uv run --locked alembic upgrade head --sql`.

Las bases antiguas creadas con `create_all` no se adoptan automáticamente. Esta
línea base se aplica a una base nueva; conservar las bases anteriores. Adoptar una
base existente requiere comprobar su esquema y datos antes de decidir cómo registrar
su versión. No usar `stamp head` para omitir esa revisión. `downgrade base` elimina
las tres tablas y solo se prueba sobre bases temporales.
