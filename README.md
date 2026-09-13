# Orquestación de Trabajos

**Estado:** Bloques 01-05 Implementados  
**Próximo:** Bloque 06 — Consultas de Trabajo

## Estructura

- **Bloque 01** (Base Tecnológica): Entorno, app instalable, dependencias  
- **Bloque 02** (Modelo): Agregado Trabajo, eventos de dominio  
- **Bloque 03** (Aplicación): Casos de uso, UoW en memoria, idempotencia  
- **Bloque 04** (PostgreSQL + Inbox/Outbox): Persistencia real, transacciones atómicas  
- **Bloque 05** (Pulsar): Consumo de Entrada, publicación de resultados ✅ **ACTUAL**

## Configuración Rápida

### Instalación

```bash
uv sync --extra dev
```

### Variables de Entorno

Copiar `.env.example` a `.env`:

```bash
ORQUESTACION_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/orquestacion_trabajos
ORQUESTACION_PULSAR_URL=pulsar://localhost:6650
ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=false  # true para activar consumidores Pulsar
```

### Base de Datos

```bash
# Crear BD y tablas (primera vez)
uv run python -c "from config.database import engine; from orquestacion_trabajos.modulos.trabajos.infraestructura.orm import Base; Base.metadata.create_all(engine)"
```

### Pulsar (para Bloque 05+)

```bash
# Preparar tópicos y suscripciones
uv run scripts/preparar_pulsar.py --pulsar-url pulsar://localhost:6650
```

## Ejecución

### Sin Consumidores (Desarrollo Local)

```bash
uv run uvicorn src.orquestacion_trabajos.api.app:app --host 0.0.0.0 --port 8001
```

API disponible en http://0.0.0.0:8001  
/health/live, /health/ready

### Con Consumidores (Bloque 05+)

```bash
export ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=true
uv run uvicorn src.orquestacion_trabajos.api.app:app --host 0.0.0.0 --port 8001
```

- ConsumidorEntrada: escucha en solicitud-partner-lista-v1
- DespachoOutbox: publica SolicitarCotizacion.v1 y TrabajoCreado.v1
- Ambos en hilos daemon del lifespan

## Validación

```bash
# Pruebas unitarias (Bloques 01-05)
uv run pytest tests -q

# Linting y formato
uv run ruff check .
uv run ruff format --check .

# Tipos
uv run mypy src tests scripts config

# Distribución
uv run python -c "import orquestacion_trabajos; print('✓ Importación exitosa')"
```

## Rutas de Pulsar

| Tópico | Suscripción | Dirección |
|--------|-------------|-----------|
| solicitud-partner-lista-v1 | orquestacion-solicitudes-v1 | Entrada → Orquestación |
| solicitar-cotizacion-v1 | cotizaciones-peticiones-v1 | Orquestación → Cotizaciones |
| trabajo-creado-v1 | seguimiento-trabajos-v1 | Orquestación → Seguimiento |
| cotizacion-registrada-v1 | orquestacion-cotizacion-registrada-v1 | Cotizaciones → Orquestación (futuro) |
| cotizacion-rechazada-v1 | orquestacion-cotizacion-rechazada-v1 | Cotizaciones → Orquestación (futuro) |

Ver [docs/contratos/README.md](docs/contratos/README.md) para flujo completo.

## Documentación

- [Decisiones y Alcance](docs/transversal/00-decisiones-y-alcance.md)
- [Contratos y Datos](docs/transversal/01-contratos-y-datos.md)
- [Base de Implementación](docs/transversal/02-base-de-implementacion.md)
- [Flujo y Contratos Bloque 05](docs/contratos/README.md)
- [Reporte Bloque 05](REPORTE_BLOQUE_05.md)
- [Diseño Bloque 04 (Versionado Optimista)](docs/04-versionado-optimista.md)

## Arquitectura

### Capas

```
api/app.py (FastAPI lifespan)
    ↓
infraestructura/ciclo_vida.py (consumidores en hilos)
    ├─ infraestructura/consumidores.py (Pulsar → BD)
    └─ infraestructura/despacho.py (BD → Pulsar)
    ↓
aplicacion/handlers/ (casos de uso)
    ↓
dominio/ (Trabajo, reglas)
    ↓
infraestructura/repositorios.py (persistencia)
    ├─ ORM (Trabajo, Inbox, Outbox)
    └─ UoW (transacciones atómicas)
```

### Garantías

- **Idempotencia:** Inbox (UNIQUE consumidor + event_id)
- **Durabilidad:** UoW atómico (Trabajo + Inbox + Outbox)
- **ACK Tardío:** Confirmación SOLO después de commit
- **Recuperación:** Outbox persistente ante fallos de Pulsar

## Próximo Bloque

**Bloque 06 — Consultas de Trabajo**

- GET /trabajos/{id}
- GET /trabajos?estado=...
- Proyección / Seguimiento opcional
- Aplicador de resultados de Cotizaciones

---

**Puertos Locales:** 8001 (Orquestación), 5432 (PostgreSQL), 6650 (Pulsar)

**Estructura:** src/orquestacion_trabajos/modulos/trabajos/{dominio, aplicacion, infraestructura}
