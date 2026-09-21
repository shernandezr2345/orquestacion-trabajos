# Mapeo Tutorial Saga vs Hogar de los Alpes

Fecha: 2026-09-20  
Alcance: fase de estudio sin implementación.  
Restricciones aplicadas: no se modificó código en tutorial-8-sagas ni en orquestacion-trabajos durante el análisis.

## [TUTORIAL] 1) Inventario del módulo sagas del tutorial

Ruta analizada: tutorial-8-sagas/src/aeroalpes/modulos/sagas/

### 1.1 Capa aplicacion

| ARCHIVO | CLASE/FUNCIÓN | RESPONSABILIDAD OBSERVADA | CAPA | PATRÓN UTILIZADO |
|---|---|---|---|---|
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | CoordinadorReservas | Define pasos de saga en inicializar_pasos y delega a CoordinadorOrquestacion | Aplicación | Orchestrator / Process Manager |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | inicializar_pasos | Construye lista de Inicio, Transaccion, Fin con comando/evento/error/compensación | Aplicación | State machine declarativa por pasos |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | iniciar | Persistir primer paso en saga log (TODO) | Aplicación | Saga log hook |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | terminar | Persistir último paso en saga log (definición sin self) | Aplicación | Saga completion hook |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | persistir_en_saga_log | Stub/TODO de persistencia | Aplicación | Persistencia diferida por repositorio |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | construir_comando | Stub/TODO de transformación evento->comando | Aplicación | Mapper evento-comando |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | oir_mensaje | Recibe EventoDominio y dispara coordinador.procesar_evento | Aplicación | Event listener |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/cliente.py | RegistrarUsuario, DesactivarUsuario, ValidarUsuario | Placeholders de comandos (sin herencia de Comando) | Aplicación | Command placeholder |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/gds.py | ConfirmarReserva, RevertirConfirmacion | Placeholders de comandos | Aplicación | Command placeholder |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/pagos.py | PagarReserva, RevertirPago | Placeholders de comandos | Aplicación | Command placeholder |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/notificaciones.py | (vacío) | Sin implementación | Aplicación | N/A |

### 1.2 Capa dominio

| ARCHIVO | CLASE | RESPONSABILIDAD OBSERVADA | CAPA | PATRÓN UTILIZADO |
|---|---|---|---|---|
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/pagos.py | EventoPago | Tipo base para eventos de pagos de saga | Dominio | Domain Event (tipo base) |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/pagos.py | ReservaPagada, PagoFallido, PagoRevertido | Eventos de avance/fallo/compensación de pagos | Dominio | Domain Event |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/gds.py | EventoGDS | Tipo base para eventos de GDS de saga | Dominio | Domain Event (tipo base) |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/gds.py | ReservaGDSConfirmada, ConfirmacionGDSRevertida, ConfirmacionFallida | Eventos de avance/fallo/compensación de GDS | Dominio | Domain Event |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/cliente.py | EventoCliente | Tipo base para eventos de cliente | Dominio | Domain Event (tipo base) |
| tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/cliente.py | ReservaCreada, ReservaCancelada, ReservaAprobada, ReservaPagada | Eventos declarados en archivo cliente (inconsistentes por referencia a EventoReserva) | Dominio | Domain Event (incompleto) |

### 1.3 Elementos solicitados y su presencia real

- [TUTORIAL] Entidades en módulo sagas: no hay entidades explícitas en modulos/sagas.
- [TUTORIAL] Value Objects en módulo sagas: no hay value objects explícitos en modulos/sagas.
- [TUTORIAL] Aggregate en módulo sagas: no hay aggregate de Saga en modulos/sagas.
- [TUTORIAL] Repositorios/interfaces de Saga en módulo sagas: no existen implementaciones concretas; hay TODO de persistencia en CoordinadorReservas.persistir_en_saga_log.
- [TUTORIAL] Persistencia de Saga: no implementada en modulos/sagas.
- [TUTORIAL] Infraestructura de Saga en modulos/sagas: no existe carpeta infraestructura; se apoya en seedwork/aplicacion/sagas.py.

## [TUTORIAL] 2) Flujo reconstruido del tutorial (código real)

### 2.1 Flujo esperado por diseño del coordinador

Evento inicial (ReservaCreada)  
↓  
CoordinadorReservas.procesar_evento (heredado de CoordinadorOrquestacion)  
↓  
Transaccion index 1 identificada por obtener_paso_dado_un_evento  
↓  
Si éxito: publicar comando siguiente (según lógica base en seedwork)  
↓  
Evento siguiente (ReservaPagada)  
↓  
Nueva transición  
↓  
ConfirmarReserva  
↓  
ReservaGDSConfirmada  
↓  
AprobarReserva  
↓  
ReservaAprobada  
↓  
Fin

Referencias:

- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py
- tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py

### 2.2 Flujo de compensación esperado por diseño

Fallo (PagoFallido o ConfirmacionFallida o AprobacionReservaFallida)  
↓  
CoordinadorOrquestacion.procesar_evento detecta paso.error  
↓  
Publicar comando de compensación del paso anterior  
↓  
Evento de compensación (ej. PagoRevertido o ConfirmacionGDSRevertida o ReservaCancelada)  
↓  
Saga continúa transiciones hasta estado final compensado

Referencias:

- tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py

### 2.3 Estado de implementabilidad real del flujo

El flujo está conceptualmente modelado, pero la implementación está incompleta o inconsistente en varios puntos observables:

- [TUTORIAL] saga_reservas.py usa PagoFallido en inicializar_pasos pero no lo importa.
- [TUTORIAL] terminar() en CoordinadorReservas está definida sin parámetro self.
- [TUTORIAL] seedwork/aplicacion/sagas.py usa referencias sin self en varios métodos (ejemplo: construir_comando, pasos, es_ultima_transaccion).
- [TUTORIAL] seedwork/aplicacion/sagas.py en rama de éxito publica self.pasos[index+1].compensacion en lugar de comando normal siguiente.
- [TUTORIAL] construir_comando y persistir_en_saga_log están en TODO.

Conclusión de esta sección: el tutorial sí entrega patrón y estructura de Saga, pero no una implementación cerrada lista para ejecución completa.

## [TUTORIAL] 3) Modelo de dominio de Saga en el tutorial

### 3.1 Cómo representa la Saga

- Identidad de Saga: id_correlacion (en CoordinadorSaga y Paso)
  - Archivo: tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py
- Estado/paso actual: index en Paso/Transaccion y lista pasos en CoordinadorOrquestacion
  - Archivo: tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py
- Comandos pendientes: implícitos por navegación de pasos (index+1 / index-1)
- Eventos recibidos: evaluados con isinstance(evento, paso.evento) o paso.error
- Compensaciones: atributo compensacion en Transaccion
- Resultado final: llegar a Fin y llamar terminar()

### 3.2 Qué abstracción es la Saga en el tutorial

Con base en el código analizado:

- [TUTORIAL] La Saga está modelada principalmente como Process Manager / Orchestrator en capa de aplicación (CoordinadorSaga -> CoordinadorOrquestacion -> CoordinadorReservas).
- [TUTORIAL] No está modelada como Aggregate Root de dominio en modulos/sagas.
- [TUTORIAL] No existe una entidad Saga persistida con repositorio propio implementado.

## [TUTORIAL] 4) Capa de aplicación del tutorial y su interacción con dominio

- [TUTORIAL] CoordinadorReservas consume eventos y decide transición de paso.
- [TUTORIAL] Los eventos de dominio que disparan transición viven en:
  - modulos/vuelos/dominio/eventos/reservas.py
  - modulos/sagas/dominio/eventos/pagos.py
  - modulos/sagas/dominio/eventos/gds.py
- [TUTORIAL] Los comandos de saga definidos en modulos/sagas/aplicacion/comandos son placeholders.
- [TUTORIAL] El comando CrearReserva sí tiene handler real fuera del módulo sagas:
  - tutorial-8-sagas/src/aeroalpes/modulos/vuelos/aplicacion/comandos/crear_reserva.py

## [EXISTENTE] 5) Estado actual en orquestacion-trabajos (resumen para mapeo)

Referencias base en código actual:

- Aggregate Root Trabajo: orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/dominio/entidades.py
- Commands: CrearTrabajoCommand y AplicarCotizacionCommand en orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/aplicacion/comandos.py
- Domain events internos: TrabajoCreado y CotizacionAplicada en orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/dominio/eventos.py
- Consumers/Producers Pulsar: rutas en orquestacion-trabajos/src/orquestacion_trabajos/config/rutas.py
- Inbox/Outbox/UoW: seedwork/infraestructura en orquestacion-trabajos/src/orquestacion_trabajos/seedwork/infraestructura/
- Persistencia SQLAlchemy + Alembic: orquestacion-trabajos/src/orquestacion_trabajos/config/database.py y orquestacion-trabajos/migraciones/versions/0001_persistencia.py

## [ADAPTACIÓN] 6) Matriz de adaptación tutorial -> Hogar de los Alpes

| CONCEPTO TUTORIAL | ARCHIVO TUTORIAL | RESPONSABILIDAD | EQUIVALENTE EN NUESTRO PROYECTO | ADAPTACIÓN NECESARIA |
|---|---|---|---|---|
| Saga | tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py (CoordinadorSaga) | Orquestar pasos por eventos/comandos | No existe módulo Saga explícito | Crear módulo Saga explícito en aplicación+dominio |
| Saga State | tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py (index/pasos) | Llevar progreso | No existe estado global de Saga; solo estado de Trabajo | Definir estado RUNNING/COMPENSATING/COMPLETED/COMPENSATED |
| Saga Coordinator | tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py | Definir transiciones | No existe coordinador; handlers separados por caso de uso | Crear SagaCoordinator dedicado |
| Saga Step | tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py (Paso/Transaccion/Inicio/Fin) | Modelar etapas | No existe abstracción de paso | Agregar pasos explícitos y reglas |
| Saga ID | tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py (id_correlacion) | Identidad/correlación | Existe correlación por id_solicitud en eventos actuales | Definir id_saga persistido y mantener id_solicitud como correlación funcional |
| Correlation ID | Eventos pagos/gds con id_correlacion | Encadenar mensajes | En orquestación actual se usa correlacion=id_solicitud | Preservar convención actual e incorporar id_saga nuevo |
| Command | modulos/sagas/aplicacion/comandos/*.py | Acciones entre servicios | CrearTrabajoCommand/AplicarCotizacionCommand (internos) | Agregar comandos de Saga de integración (abrir/cancelar/anular/registrar) |
| Event | modulos/sagas/dominio/eventos/*.py | Disparar transiciones | Eventos existentes de cotización y trabajo | Agregar eventos de seguimiento/atención/anulación como disparadores de Saga |
| Compensation | Transaccion.compensacion | Revertir efectos | No hay compensación multi-servicio explícita | Implementar flujo de compensación idempotente |
| Repository | TODO en persistir_en_saga_log | Persistir saga | Repositorio de Trabajo + inbox/outbox existentes | Crear repositorio Saga y SagaLog |
| Persistence | TODO en saga_reservas.py | Durabilidad de pasos | Tablas trabajos/inbox/outbox | Agregar tablas saga y saga_log |
| Handler | oir_mensaje + procesar_evento | Reaccionar a eventos | consumidores.py + handlers de aplicación | Introducir handler de eventos de Saga centralizado |
| State Transition | CoordinadorOrquestacion.procesar_evento | Avanzar/compensar | Lógica distribuida en CrearTrabajo y AplicarCotizacion | Centralizar transición en coordinador |
| Saga completion | terminar() | Cierre exitoso | No existe | Definir criterio de cierre + evento/log final |
| Saga failure | rama error + compensación | Cierre compensado | No existe | Definir compensación total y estado final compensado |

## [PROPUESTA] 7) Estructura recomendada para agregar Saga en orquestacion-trabajos

Se recomienda crear (sin hacerlo aún) una estructura explícita:

- modulos/sagas/
  - dominio/
    - entidades.py
    - eventos.py
    - objetos_valor.py
    - repositorios.py
    - servicios.py
  - aplicacion/
    - comandos.py
    - handlers/
      - iniciar_saga.py
      - avanzar_saga.py
      - compensar_saga.py
    - coordinadores/
      - saga_hogar_alpes.py
    - unidad_trabajo.py
  - infraestructura/
    - orm.py
    - repositorios.py
    - mapeadores_eventos.py
    - consumidores.py
    - unidad_trabajo.py

### Distribución de responsabilidades propuesta

- [PROPUESTA] Dominio Saga: estado, invariantes y transiciones válidas.
- [PROPUESTA] Aplicación Saga: coordinación de pasos, construcción de comandos de integración, decisión de compensación.
- [PROPUESTA] Infraestructura Saga: persistencia saga/saga_log, mapeo envelopes, integración con inbox/outbox existente.

## [ADAPTACIÓN] 8) Reutilizable conceptualmente vs específico Aeroalpes

### Reutilizable conceptualmente

- [TUTORIAL] Coordinador de orquestación basado en pasos.
- [TUTORIAL] Estructura Paso/Transaccion/Inicio/Fin.
- [TUTORIAL] Mapeo evento -> transición -> comando siguiente.
- [TUTORIAL] Compensación por transacción.
- [TUTORIAL] Saga log para trazabilidad durable.

### Específico del dominio Aeroalpes (no copiar)

- [TUTORIAL] Comandos y eventos de reserva de vuelos (CrearReserva, AprobarReserva, CancelarReserva, Pago/GDS de ese dominio).
- [TUTORIAL] Tipos y payloads concretos de Reserva.
- [TUTORIAL] Wiring específico de Flask y módulos hoteles/vehículos/vuelos.
- [TUTORIAL] Implementaciones placeholder/incompletas del tutorial.

## [ADAPTACIÓN] 9) Mapeo de nuestro flujo Entrega 5 usando patrones del tutorial

### 9.1 Flujo exitoso objetivo

SolicitudDePartnerListaParaAtencion  
↓  
[EXISTENTE] CrearTrabajoHandler.ejecutar  
↓  
[EXISTENTE] Outbox publica SolicitarCotizacion.v1  
↓  
CotizacionRegistrada  
↓  
[PROPUESTA] SagaCoordinator emite AbrirSeguimientoTrabajo.v1  
↓  
SeguimientoTrabajoAbierto  
↓  
[PROPUESTA] SagaCoordinator emite RegistrarAtencionHabilitada.v1  
↓  
COMPLETED

Patrón tutorial aplicado:

- [TUTORIAL] Transaccion + evento de éxito -> comando siguiente (CoordinadorOrquestacion.procesar_evento)

### 9.2 Flujo compensación objetivo

AperturaSeguimientoFallida  
↓  
COMPENSATING  
↓  
[PROPUESTA] AnularCotizacion.v1  
↓  
[PROPUESTA] Cancelar Trabajo (estado CANCELADO + evento TrabajoCancelado.v1)  
↓  
[PROPUESTA] RegistrarAtencionCancelada.v1  
↓  
COMPENSATED

Patrón tutorial aplicado:

- [TUTORIAL] evento de error -> compensación del paso anterior (Transaccion.compensacion)

## 10) Cierre solicitado

### 10.1 Qué conceptos del tutorial adoptaremos

- [TUTORIAL] Coordinador de orquestación explícito.
- [TUTORIAL] Máquina de estados por pasos de Saga.
- [TUTORIAL] Compensación explícita por transición fallida.
- [TUTORIAL] Registro durable de avance (Saga Log).

### 10.2 Qué conceptos NO adoptaremos

- [TUTORIAL] Clases placeholder sin implementación real.
- [TUTORIAL] Errores de wiring/lógica observables en seedwork del tutorial.
- [TUTORIAL] Comandos/eventos de dominio de vuelos Aeroalpes.
- [TUTORIAL] Acoplamiento a estructura Flask de ese proyecto.

### 10.3 Estructura propuesta para modulos/sagas

- [PROPUESTA] modulos/sagas/dominio/
- [PROPUESTA] modulos/sagas/aplicacion/
- [PROPUESTA] modulos/sagas/infraestructura/

### 10.4 Modelo de Saga propuesto

- [PROPUESTA] Entidad/Aggregate Saga con id_saga, id_solicitud, id_trabajo, estado, paso_actual, timestamps, versión.
- [PROPUESTA] Estados: RUNNING, COMPENSATING, COMPLETED, COMPENSATED.
- [PROPUESTA] Reglas idempotentes por mensaje de entrada usando inbox existente.

### 10.5 Responsabilidades del Saga Coordinator

- [PROPUESTA] Traducir eventos de integración a transiciones.
- [PROPUESTA] Resolver siguiente comando o comando de compensación.
- [PROPUESTA] Publicar comandos por outbox en misma UoW transaccional cuando aplique.
- [PROPUESTA] Garantizar que transición inválida no altere estado.

### 10.6 Responsabilidades del Saga Log

- [PROPUESTA] Persistir cada transición con: id_saga, paso, evento/command_id, estado anterior/nuevo, instante y resultado.
- [PROPUESTA] Soportar reanudación tras fallos y auditoría de compensaciones.
- [PROPUESTA] Servir evidencia operativa sin depender de logs efímeros.

### 10.7 Próximo paso de implementación recomendado

- [PROPUESTA] Diseñar primero el modelo de dominio Saga y el esquema de persistencia saga + saga_log, antes de crear nuevos consumers/producers de contratos de Entrega 5.

---

## Anexo A: Referencias de código utilizadas

### Tutorial Saga

- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/coordinadores/saga_reservas.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/cliente.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/gds.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/pagos.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/aplicacion/comandos/notificaciones.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/cliente.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/gds.py
- tutorial-8-sagas/src/aeroalpes/modulos/sagas/dominio/eventos/pagos.py
- tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/sagas.py
- tutorial-8-sagas/src/aeroalpes/seedwork/aplicacion/comandos.py
- tutorial-8-sagas/src/aeroalpes/api/__init__.py

### Orquestación Trabajos

- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/dominio/entidades.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/dominio/eventos.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/dominio/objetos_valor.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/aplicacion/comandos.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/crear_trabajo.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/aplicacion/handlers/aplicar_cotizacion.py
- orquestacion-trabajos/src/orquestacion_trabajos/modulos/trabajos/infraestructura/unidad_trabajo.py
- orquestacion-trabajos/src/orquestacion_trabajos/config/rutas.py
- orquestacion-trabajos/src/orquestacion_trabajos/seedwork/infraestructura/inbox.py
- orquestacion-trabajos/src/orquestacion_trabajos/seedwork/infraestructura/outbox.py
- orquestacion-trabajos/src/orquestacion_trabajos/seedwork/infraestructura/despacho_outbox.py
- orquestacion-trabajos/migraciones/versions/0001_persistencia.py
