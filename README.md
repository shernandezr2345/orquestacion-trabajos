# Orquestación de Trabajos

## Paso 01: base tecnológica

Este repositorio prepara la base instalable del servicio de Orquestación sin arrancar consumidores ni depender de la red del broker durante la importación.

### Comandos

```bash
uv sync --extra dev
uv run pytest tests -q
uv run ruff check .
uv run python -m compileall src config tests
```

### Variables de entorno

Copiar `.env.example` a `.env` y ajustar los valores locales.

### Ruta del paquete

`src/orquestacion_trabajos`

### Puerto local

`8001`
