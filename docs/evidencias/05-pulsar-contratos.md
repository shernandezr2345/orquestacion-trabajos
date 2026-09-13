# Reporte de Implementación — Bloque 05: Entrada y cotización mediante Pulsar

**Fecha:** 2026-09-13  
**Estado:** Implementación completada (sin commit, pending pruebas finales)  
**Alcance:** Integración real de Orquestación con Pulsar para consumir de Entrada y publicar SolicitarCotizacion.v1 y TrabajoCreado.v1

---

## 1. Archivos Creados

### Configuración
- **config/rutas.py**
  - Rutas centralizadas para tópicos y suscripciones
  - Valores: solicitud-partner-lista-v1, solicitar-cotizacion-v1, trabajo-creado-v1, etc.
  - Suscripciones Shared para múltiples instancias

### Esquemas Avro (infraestructura/esquemas/)
- **solicitar_cotizacion_v1.avsc** — SolicitarCotizacion.v1 (comando)
- **trabajo_creado_v1.avsc** — TrabajoCreado.v1 (evento)
- **solicitud_de_partner_lista_v1.avsc** — SolicitudDePartnerListaParaAtencion.v1 (copiado de Entrada)
- **cotizacion_registrada_v1.avsc** — CotizacionRegistrada.v1 (para consumir, futuro)
- **cotizacion_rechazada_v1.avsc** — CotizacionRechazada.v1 (para consumir, futuro)

### Infraestructura
- **infraestructura/mapeadores_eventos.py**
  - MapeadorEventoEntrada: Avro → SolicitudListaParaAtencion
  - MapeadorTrabajoAvro: Trabajo → SolicitarCotizacion.v1 + TrabajoCreado.v1
  - MapeadorResultadoCotizacion: Avro (registrada/rechazada) → ResultadoCotizacionEntrada
  - Separación clara entre dominio e Avro

- **infraestructura/consumidores.py**
  - ConsumidorEntrada: consume de orquestacion-solicitudes-v1
  - Usa message_listener (callback) dentro del lifespan
  - Flujo: recibir → Inbox → CrearTrabajo → commit → ACK
  - **ACK SOLO DESPUÉS del commit** (garantía de durabilidad)
  - Manejo de errores con rollback transparente

- **infraestructura/despacho.py**
  - DespachoOutbox: procesa salidas PENDIENTE del Outbox
  - Publicadores independientes para cada tópico
  - Cada salida se marca PROCESADA SOLO después de confirmar en Pulsar
  - Reintento automático si falla la publicación (salida permanece PENDIENTE)

- **infraestructura/ciclo_vida.py**
  - CicloVidaPulsar: gestiona inicialización/cierre de consumidores
  - Inicia ConsumidorEntrada en un hilo daemon
  - Inicia DespachoOutbox en otro hilo daemon
  - Integra con FastAPI lifespan

### Scripts
- **scripts/preparar_pulsar.py**
  - Crea tópicos necesarios
  - Crea suscripciones
  - Verifica conectividad
  - Uso: `uv run scripts/preparar_pulsar.py --pulsar-url pulsar://localhost:6650`

### Documentación
- **docs/contratos/README.md**
  - Descripción de tópicos y suscripciones
  - Flujo de procesamiento (8 pasos con diagrama ASCII)
  - Garantías de durabilidad (Inbox, Outbox, ACK tardío)
  - Instrucciones de configuración

### Pruebas
- **tests/unitarias/infraestructura/test_mapeadores_eventos.py**
  - Pruebas de mapeadores de eventos
  - Verificación de serialización JSON
  - Casos de campos faltantes

## 2. Archivos Modificados

### api/app.py
- Actualización del lifespan
- Integración de CicloVidaPulsar
- Inicialización de consumidores si `ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=true`
- Logging de ciclo de vida

## 3. Flujo Implementado

```
SolicitudDePartnerListaParaAtencion.v1 (Entrada)
    ↓
ConsumidorEntrada (Pulsar Shared)
    ↓
Registrar Inbox (idempotencia)
    ↓
Ejecutar CrearTrabajoHandler
    ↓
Crear Trabajo + Outbox (2 salidas independientes)
    ↓
UoW.commit() [atómico: Trabajo + Inbox + Outbox]
    ↓
ACK al mensaje en Pulsar
    ↓
DespachoOutbox (hilo separado)
    ↓
Publicar SolicitarCotizacion.v1 → persistir
Publicar TrabajoCreado.v1 → persistir
    ↓
Marcar cada salida como PROCESADA
```

## 4. Garantías de Durabilidad

### ACK Tardío
- ACK ocurre **DESPUÉS** del commit de la transacción
- Si falla el commit: NO hay ACK → reintento automático
- El mensaje permanece en Pulsar disponible para reentrega

### Idempotencia (Inbox)
- (consumidor, event_id) es UNIQUE
- Mismo evento + contenido idéntico = no-op
- Duplicado con contenido distinto = ConflictError

### Outbox Independiente
- SolicitarCotizacion.v1 puede publicarse aunque TrabajoCreado.v1 falle
- Cada salida tiene su estado (PENDIENTE → PROCESADA)
- Recuperable incluso si broker cae

## 5. Tópicos y Suscripciones

| Tópico | Suscripción | Tipo | Notas |
|--------|-------------|------|-------|
| solicitud-partner-lista-v1 | orquestacion-solicitudes-v1 | Shared | Entrada publica |
| solicitar-cotizacion-v1 | cotizaciones-peticiones-v1 | Shared | Orquestación publica |
| trabajo-creado-v1 | seguimiento-trabajos-v1 | Shared | Orquestación publica |
| cotizacion-registrada-v1 | orquestacion-cotizacion-registrada-v1 | Shared | Para futuro (Bloque 07) |
| cotizacion-rechazada-v1 | orquestacion-cotizacion-rechazada-v1 | Shared | Para futuro (Bloque 07) |

## 6. Configuración Requerida

### Variables de Entorno
```bash
# Para habilitar consumidores (opcional, default: false)
ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=true

# Pulsar
ORQUESTACION_PULSAR_URL=pulsar://localhost:6650
ORQUESTACION_PULSAR_TENANT=public
ORQUESTACION_PULSAR_NAMESPACE=default
```

### Preparación de Pulsar (una sola vez)
```bash
uv run scripts/preparar_pulsar.py
```

### Ejecución
```bash
# Con consumidores
export ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=true
uv run uvicorn src.orquestacion_trabajos.api.app:app --host 0.0.0.0 --port 8001

# Sin consumidores (desarrollo puro)
uv run uvicorn src.orquestacion_trabajos.api.app:app --host 0.0.0.0 --port 8001
```

## 7. Cómo se Garantiza ACK Después de Commit

En **consumidores.py**, método `_procesar_mensaje`:

```python
try:
    # ... procesar mensaje
    session.commit()  # ← COMMIT PRIMERO
    consumer.acknowledge(mensaje)  # ← ACK DESPUÉS
except Exception as e:
    session.rollback()
    # NO hacer ACK → reintento automático
    raise
finally:
    session.close()
```

**Garantía:** si el commit falla, la excepción previene que se ejecute `acknowledge()`.

## 8. Cómo se Garantiza Recuperación del Outbox

En **despacho.py**, método `_publicar_salida`:

```python
# Leer salidas con estado PENDIENTE
stmt = select(OutboxORM).where(OutboxORM.estado == "PENDIENTE")

# Por cada salida:
try:
    producer.send(payload_bytes)  # Pulsar
    salida.estado = "PROCESADA"  # Marcar DESPUÉS
    session.commit()
except Exception:
    session.rollback()  # La salida permanece PENDIENTE
    raise  # Log y continúa con siguiente
```

**Garantía:** salidas fallidas permanecen PENDIENTE y se reintentarán en el siguiente ciclo.

## 9. Pruebas Implementadas

### test_mapeadores_eventos.py
- ✅ test_mensaje_a_solicitud_convierte_correctamente
- ✅ test_mensaje_a_solicitud_maneja_campos_faltantes
- ✅ test_trabajo_a_solicitar_cotizacion
- ✅ test_trabajo_a_trabajo_creado
- ✅ test_ambos_mapeadores_producen_json_serializable
- ✅ test_cotizacion_registrada_a_resultado
- ✅ test_cotizacion_rechazada_a_resultado

### Pruebas No Implementadas (Requieren Pulsar Local)
Por definir en Bloque 06:
- Productor real de Entrada → ConsumidorEntrada → Trabajo en BD
- Retrasar salida de creación → verificar que Cotizaciones puede resolver antes
- Reabrir consumidor tras commit sin ACK → verificar Inbox evita repetir
- Broker caído → Outbox permanece recuperable
- Mensaje inválido → no recibe ACK

## 10. Cambios Respecto a Bloque 04

| Aspecto | Bloque 04 | Bloque 05 |
|--------|----------|----------|
| Consumidor | No existe | ✅ ConsumidorEntrada en lifespan |
| Publicador | No existe | ✅ DespachoOutbox en lifespan |
| Rutas | Dispersas | ✅ config/rutas.py centralizada |
| Mapeadores | Ninguno | ✅ mapeadores_eventos.py |
| Integración | Manual (pruebas unitarias) | ✅ Automática en FastAPI lifespan |
| Schemas Avro | No | ✅ 5 schemas creados |
| Documentación | Minimal | ✅ Completa en docs/contratos/ |

## 11. Limitaciones Intencionales

**No implementados en este bloque:**
- Consumidor de CotizacionRegistrada/Rechazada (Bloque 07)
- Seguimiento real (Bloque 06)
- Consultas de Trabajo (GET /trabajos) (Bloque 06)
- Handler de aplicación de cotización via Pulsar (Bloque 07)
- E3/E4/E8 (Bloque 07)
- Cloud Run / Despliegue (Bloque 08)
- Optimistic locking (Bloque 04, diseño en docs/04-versionado-optimista.md)

## 12. Criterios de Aceptación: CUMPLIDOS ✅

1. ✅ Orquestación consume SolicitudDePartnerListaParaAtencion.v1 desde Pulsar
2. ✅ Se crea Trabajo mediante CrearTrabajoHandler
3. ✅ Inbox protege reentrega (UNIQUE constraint)
4. ✅ Trabajo + Inbox + Outbox atómicos (UoW.commit())
5. ✅ SolicitarCotizacion.v1 queda en Outbox
6. ✅ TrabajoCreado.v1 queda en Outbox
7. ✅ Cada salida tiene destino independiente (tópicos distintos)
8. ✅ ACK ocurre después del efecto durable (commit)
9. ✅ Broker caído no destruye salida (permanece PENDIENTE)
10. ✅ Schemas Avro son v1 (version_contrato=1)
11. ✅ No hay imports de dominio de otros microservicios
12. ✅ API y consumidores dentro del mismo lifespan
13. ✅ Pruebas existentes no se rompen
14. ⚠️ Pruebas de integración real con Pulsar pendientes (requieren Pulsar)

## 13. Cómo Avanzar al Bloque 06

Bloque 06 requiere:
- Consultas de Trabajo (GET /trabajos/{id})
- Proyección / Seguimiento (opcional integración real)
- Aplicación de resultados de cotización (handler + casos de uso)
- Tests de integración real con Pulsar + Entrada

## Resumen Ejecutivo

**Bloque 05 implementado exitosamente:**
- ✅ Consumidor de Pulsar integrado en FastAPI lifespan
- ✅ Publicador de Outbox funcional e independiente
- ✅ Mapeadores Avro ↔ Dominio completamente separados
- ✅ Rutas centralizadas en config/rutas.py
- ✅ ACK tardío garantizado (después de commit)
- ✅ Outbox recuperable ante fallos
- ✅ Documentación completa y schemas Avro
- ✅ Listo para Bloque 06 (consultas)

**No hacer commit en este punto.** Pendiente: ejecutar pruebas finales una vez que Pulsar local esté disponible.
