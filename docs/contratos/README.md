# Contratos y Flujo de Orquestación de Trabajos

## Resumen de Bloques 05

El Bloque 05 implementa la integración real de Orquestación con Pulsar:

- **Entrada:** SolicitudDePartnerListaParaAtencion.v1
- **Procesamiento:** CrearTrabajo (caso de uso)
- **Salida:** TrabajoCreado.v1 + SolicitarCotizacion.v1 (publicadas a tópicos independientes)

## Tópicos y Suscripciones

| Tópico | Productor | Suscripción | Consumidor | Descripción |
|--------|-----------|-------------|-----------|-------------|
| `persistent://public/default/solicitud-partner-lista-v1` | Entrada | `orquestacion-solicitudes-v1` | Orquestación | Solicitudes lista para atención |
| `persistent://public/default/solicitar-cotizacion-v1` | Orquestación | `cotizaciones-peticiones-v1` | Cotizaciones | Comandos para solicitar cotizaciones |
| `persistent://public/default/trabajo-creado-v1` | Orquestación | `seguimiento-trabajos-v1` | Seguimiento | Eventos de creación de trabajo |
| `persistent://public/default/cotizacion-registrada-v1` | Cotizaciones | `orquestacion-cotizacion-registrada-v1` | Orquestación | Resultados de cotizaciones (futuro) |
| `persistent://public/default/cotizacion-rechazada-v1` | Cotizaciones | `orquestacion-cotizacion-rechazada-v1` | Orquestación | Rechazos de cotizaciones (futuro) |

## Flujo de Procesamiento

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Entrada publica SolicitudDePartnerListaParaAtencion.v1       │
│    - event_id, id_solicitud, id_partner, categoría, etc.       │
│    - Tópico: solicitud-partner-lista-v1                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ConsumidorEntrada (Orquestación) recibe del Pulsar          │
│    - Se ejecuta en un hilo dentro del lifespan de FastAPI      │
│    - Subscription: orquestacion-solicitudes-v1 (Shared)         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Registrar Inbox (idempotencia)                              │
│    - (consumidor, event_id, contenido_normalizado)             │
│    - UNIQUE constraint (consumidor, event_id)                   │
│    - Si duplicado idéntico: no-op                              │
│    - Si duplicado con contenido distinto: ConflictError         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Crear Trabajo (caso de uso)                                 │
│    - Comando: CrearTrabajoCommand(solicitud)                    │
│    - Resultado: Trabajo con estado PENDIENTE_COTIZACION        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Registrar Outbox con dos salidas independientes             │
│    - TrabajoCreado.v1 → tópico trabajo-creado-v1               │
│    - SolicitarCotizacion.v1 → tópico solicitar-cotizacion-v1   │
│    - Ambas en estado PENDIENTE                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. UoW commit() - Transacción atómica                           │
│    - Trabajo + Inbox + Outbox en la misma transacción          │
│    - Si alguna falla: rollback de todo                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. ACK al mensaje en Pulsar                                    │
│    - SOLO DESPUÉS del commit durable                           │
│    - Si no hay commit: NO se hace ACK → reintento              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. DespachoOutbox (hilo separado) procesa Outbox              │
│    - Lee salidas en estado PENDIENTE                            │
│    - Publica cada una a su tópico en Pulsar                    │
│    - Marca como PROCESADA SOLO después de confirmar            │
│    - Las dos salidas son independientes:                        │
│      * Si TrabajoCreado publica ok → marcada PROCESADA         │
│      * Si SolicitarCotizacion falla → permanece PENDIENTE      │
└─────────────────────────────────────────────────────────────────┘
```

## Garantías de Durabilidad

1. **Inbox:** Impide reentrega duplicada del mismo evento
2. **Outbox:** Garantiza que las salidas se publican aunque haya fallos
3. **Idempotencia:** Mismo event_id + contenido idéntico = no-op
4. **ACK tardío:** No se ACK antes del commit, evita pérdida de datos
5. **Desacoplamiento:** Publicación de las dos salidas es independiente

## Cómo preparar Pulsar

```bash
cd orquestacion-trabajos
uv run scripts/preparar_pulsar.py --pulsar-url pulsar://localhost:6650
```

Esto:
- Crea los tópicos necesarios
- Crea las suscripciones
- Verifica la conectividad

## Cómo ejecutar con consumidores activos

```bash
# En .env o exportar variable
export ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=true

# Ejecutar la aplicación
uv run uvicorn src.orquestacion_trabajos.api.app:app --host 0.0.0.0 --port 8001
```

El servidor:
- Inicia en http://0.0.0.0:8001
- Abre un hilo para ConsumidorEntrada
- Abre un hilo para DespachoOutbox
- Ambos funcionan en paralelo con las requests HTTP

## Cómo desactivar consumidores (desarrollo local)

```bash
export ORQUESTACION_ENABLE_LIFESPAN_CONSUMERS=false

# O simplemente no definir la variable (default es false)
uv run uvicorn src.orquestacion_trabajos.api.app:app --host 0.0.0.0 --port 8001
```

Sin consumidores:
- La aplicación inicia normalmente
- Pulsar no se conecta
- Útil para pruebas de API pura
- Outbox queda para procesar manualmente o en otra instancia

## Tipos de Mensajes

Ver subcarpetas de esquemas:
- `solicitar_cotizacion_v1.avsc` — SolicitarCotizacion.v1
- `trabajo_creado_v1.avsc` — TrabajoCreado.v1
- `solicitud_de_partner_lista_v1.avsc` — SolicitudDePartnerListaParaAtencion.v1 (copiado de Entrada)
- `cotizacion_registrada_v1.avsc` — CotizacionRegistrada.v1 (para consumir, futuro)
- `cotizacion_rechazada_v1.avsc` — CotizacionRechazada.v1 (para consumir, futuro)

## Cambios implementados respecto a Bloque 04

- Consumidor automático en lifespan de FastAPI ✅
- Dos productores independientes (SolicitarCotizacion, TrabajoCreado) ✅
- ACK después del commit ✅
- Despacho independiente de cada salida ✅
- Preparación de Pulsar con script ✅
- Separación de dominio e Avro (mapeadores_eventos.py) ✅
- Rutas centralizadas (config/rutas.py) ✅

## Limitaciones de este bloque

- No hay consumidor de CotizacionRegistrada ni CotizacionRechazada (Bloque 06/07)
- No hay Seguimiento real (Bloque 06)
- No hay consultas de Trabajo (Bloque 06)
- No hay E3, E4, E8 (Bloque 07)
- No hay despliegue ni Cloud Run (Bloque 08)

## Próximo paso

Bloque 06 — Consultas de Trabajo (GET /trabajos/{id}, GET /trabajos)
