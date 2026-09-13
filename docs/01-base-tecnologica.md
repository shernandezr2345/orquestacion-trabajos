# 01 — Base tecnológica

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: ninguna.

**Objetivo:** preparar un servicio instalable independiente de Entrada. Crear `pyproject.toml`, `uv.lock`, `src/orquestacion_trabajos/api/app.py`, `config/settings.py`, `config/database.py`, `.env.example`, pruebas iniciales y CI. Reservar configuración propia `ORQUESTACION_*`, puerto HTTP propuesto 8001; no copiar prefijos `PARTNER_*`.

**Trabajo:** seguir la base común; fijar Python/cliente compatible; crear Engine/sessionmaker sin abrir conexión; factoría de app con lifespan; cierre de recursos; `/health/live`. Incorporar seedwork mínimo solo cuando 02 lo utilice. No levantar consumidores desde import ni desde el test health.

**Verificación:** import de cliente Pulsar y plataforma; crear/iniciar app con red bloqueada y overrides; verificar factoría con driver real sin conexión; instalar wheel fuera del árbol fuente. Test falla si un módulo intenta conectar al broker durante import.

**Cierre:** entorno reproducible y checks unitarios verdes; documentar comandos. La app vacía todavía no es un microservicio funcional para la rúbrica. Entregar al equipo versiones elegidas y ruta del paquete.

**Composición acordada:** un único proceso FastAPI por instancia. Preparar lifespan con dependencias falsas en 01; integrar consumo y, si aplica, despacho en 05 siguiendo el [ciclo de vida común](../02-base-de-implementacion.md). Los puertos indicados son locales; en Cloud Run escuchar en `0.0.0.0` y el puerto suministrado por `PORT`.
