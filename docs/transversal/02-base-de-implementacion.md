# Base de implementación común

Aplicar a los ocho incrementos de cada servicio. Son instrucciones de trabajo futuro; los comandos de los nuevos repositorios se concretarán en su incremento 01.

## Organización y responsabilidad

Crear repositorios hermanos de Entrada, no subpaquetes dentro de ella: `orquestacion-trabajos`, `cotizaciones` y `seguimiento-trabajos`, bajo `entrega4`. Esta carpeta contiene únicamente planes.

Usar módulos y capas del curso. La convención local de Entrada y el acuerdo específico de las conversaciones usan español sin tildes para nombres propios; conservar contratos y vocabulario del Event Storming. Si el equipo decide otra convención para los repositorios nuevos, mantener un único criterio dentro de cada uno y nunca traducir campos del contrato público unilateralmente.

```text
src/<paquete>/
  api/app.py
  api/<recurso>.py
  config/settings.py
  config/database.py
  config/bootstrap.py
  config/rutas.py
  modulos/<modulo>/
    dominio/entidades.py
    dominio/objetos_valor.py
    dominio/eventos.py
    dominio/repositorios.py
    aplicacion/comandos.py
    aplicacion/consultas.py
    aplicacion/unidad_trabajo.py
    aplicacion/handlers/
    infraestructura/orm.py
    infraestructura/repositorios.py
    infraestructura/mapeadores.py
    infraestructura/mapeadores_eventos.py
    infraestructura/serializacion.py
    infraestructura/consumidores.py
    infraestructura/esquemas/
  seedwork/dominio/
  seedwork/aplicacion/
  seedwork/infraestructura/
  infraestructura/ciclo_vida.py
  infraestructura/despacho.py
migraciones/versions/
tests/unitarias/
tests/api/
tests/contratos/
tests/integracion/
scripts/
docs/contratos/
docs/evidencias/
```

Crear únicamente archivos con responsabilidad real. Seguimiento prescinde de despacho/outbox porque no publica hechos. `servicios.py` y `excepciones.py` se añaden donde haya reglas o errores concretos. No crear carpetas vacías para fingir dos dominios.

| Lugar | Responsabilidad y límite |
|---|---|
| entidades/objetos_valor | Estado e invariantes; sin SQLAlchemy, Pulsar, FastAPI o imports de dominio ajeno |
| eventos | Hechos internos inmutables; no son por sí mismos schema Avro |
| handlers | Caso de uso y coordinación de puertos; traduce datos externos a tipos propios |
| repositorios de dominio | Puertos mínimos; no un CRUD genérico sin uso |
| infraestructura/repositorios | Toda operación SQL del módulo, incluidas lecturas/proyecciones |
| UoW | Coordina misma sesión/transacción; delega escritura a repositorios |
| mapeadores | Conversión ORM ↔ tipos propios; reconstruir no emite eventos nuevos |
| mapeadores_eventos/esquemas | Contratos de mensajería y conversión Avro, separados del import SQL |
| bootstrap | Construye dependencias y conecta handlers; no consulta SQL ni toma decisiones de negocio |
| rutas | Una definición de destinos; no copias divergentes en varios consumidores |
| infraestructura/ciclo_vida | Inicia/supervisa/cierra los hilos de consumo y despacho desde lifespan; sin reglas empresariales |
| infraestructura/despacho | Reserva, publica y confirma salidas durables; componente interno de los productores |

Seedwork local: identidad, objetos valor, eventos pendientes y abstracciones de reloj/UoW cuando se usen. No copiar un framework completo ni introducir clases fábrica que solo envuelvan los constructores de bootstrap. No crear `contratos.py` como mera reexportación.

## Base tecnológica del incremento 01

Tomar como punto de partida Python 3.12, uv, FastAPI, SQLAlchemy 2.0, psycopg, Alembic, pytest, Ruff y mypy. Entrada documenta cliente Pulsar 3.13.0 y broker 4.1.3 probados juntos, PostgreSQL 17.6; son una referencia de interoperabilidad, no una afirmación de que sean las últimas versiones.

Consultar documentación oficial mediante `find-docs` al concretar sintaxis/configuración, resolver cada lockfile y registrar la plataforma. Verificar import del cliente nativo Pulsar antes de fijar la imagen Python. No elegir otra versión de Python y descubrir al final que no hay wheel compatible.

En este incremento probar instalación, factoría de Engine sin conectar, creación/inicio/cierre de API con dependencias falsas y `/health/live`. Importar dominio o persistencia no debe importar Pulsar; construir la app no debe abrir conexiones de red sin una necesidad explícita. Los componentes de mensajería conectan al entrar en lifespan operativo, no al importar su módulo ni al construir la factoría. Los tests de API inyectan un ciclo de vida falso.

Verificar wheel instalado en un entorno no editable desde fuera de `src`; evita un proyecto que funciona solo por la ruta de trabajo. CI unitario no requiere Docker. CI de integración levanta infraestructura real y falla si no está disponible; no ocultar el problema con skips.

## Ciclo de vida integrado

Cada instancia ejecuta **un proceso ASGI y un contenedor de aplicación**. `api/app.py` declara lifespan, `config/bootstrap.py` ensambla dependencias y `infraestructura/ciclo_vida.py` administra sus recursos. No hay CLI de consumo ni despliegue de despacho aparte; no crear procesos ASGI múltiples dentro del contenedor, pues multiplicarían los mismos bucles sin visibilidad de capacidad.

1. Entrar en lifespan: crear recursos operativos e iniciar un hilo por suscripción lógica y uno de despacho donde exista outbox. Cada operación crea/cierra su propia Session; nunca compartir una Session entre hilos. Seguimiento tiene tres fuentes y ningún despacho.
2. Ejecutar `receive`, ACK y E/S SQL síncrona fuera del event loop. Los hilos son acotados y referenciados por el ciclo de vida, no uno nuevo por mensaje ni `BackgroundTasks` por petición. Un `create_task` alrededor de E/S síncrona no basta. En rutas HTTP, usar ejecución compatible con E/S síncrona fuera del event loop.
3. Supervisar excepción y estado de cada bucle. Un fallo de conectividad mantiene pendientes y reintenta con espera acotada; el timeout sin mensajes no es error de salud. `/health/live` verifica vida del proceso y `/health/ready` informa DB, conexión y bucles requeridos. No depende de la salud de otro microservicio. Readiness es diagnóstico de la aplicación; no suponer que detiene consumo ni que Cloud Run lo consulta automáticamente.
4. Al recibir cierre: marcar readiness no disponible, señalar parada, dejar de recibir/reservar trabajo nuevo y completar o revertir la operación en curso. Usar timeout de recepción corto (propuesta: 1 s) y límites de conexión/envío/SQL compatibles con un presupuesto total de cierre menor a 10 s. Cerrar consumidores/productores/cliente y unir hilos dentro del presupuesto; liberar Engine cuando ya no haya operaciones. Cancelar una tarea asyncio no detiene por sí solo un hilo.
5. Si llega un corte forzado, no hacer ACK ni marcar outbox por intentar apagar. El siguiente arranque recupera pendientes con las mismas suscripciones y reservas. Cerrar un consumidor no implica eliminar su suscripción; no usar unsubscribe durante shutdown.

Cloud Run puede reemplazar instancias aun con capacidad mínima. La recuperación depende de PostgreSQL y Pulsar externos, nunca del disco efímero ni de una cola en memoria. El plazo de apagado se verifica contra el [contrato de ejecución](https://docs.cloud.google.com/run/docs/container-contract#lifecycle); no se garantiza drenar todo el backlog durante shutdown.

**Pruebas de composición obligatorias en 05/08:** iniciar/cerrar lifespan dos veces sin duplicar hilos ni filtrar recursos; recibir mensajes sin peticiones HTTP; GET responde mientras `receive` espera; errores internos visibles en readiness; parada durante espera, transacción y envío; reinicio después de commit sin ACK; dos instancias con mismo mensaje y reservas concurrentes. En 01 bastan dobles; en 05 usar PostgreSQL/Pulsar y en 08 repetir en la plataforma real.

## Transacciones y entrega

```text
Consumidor recibe y valida mensaje
  → traduce al caso de uso local
  → UoW: inbox + efecto de negocio + salidas
  → commit
  → ACK individual

Publicador
  → reserva salida durable y cierra transacción corta
  → envía fuera de la transacción SQL
  → espera confirmación del broker
  → marca salida, verificando identidad de reserva
```

Una entrada inbox usa `(consumidor, id_mensaje)` y contenido normalizado. Duplicado idéntico no repite efecto; mismo ID con contenido distinto es conflicto. A esto se suma una UNIQUE de identidad empresarial: un emisor puede equivocarse y reenviar la misma petición con otro ID.

Cada UoW usa sesión propia. No guardar una Session global compartida entre peticiones o consumidores. Un fallo antes del commit revierte también el inbox; no dejar la marca que impediría reintentar. Actualizaciones concurrentes usan versión esperada o bloqueo dentro del repositorio; no basta almacenar un contador sin condición en SQL.

Partir de un bucle de despacho por instancia productora, dentro del mismo proceso FastAPI. Al escalar el servicio hay varios despachos concurrentes sobre su misma base: probar reservas también entre instancias. Si se reutilizan reservas de Entrada, conservar token de propiedad: A vencido no puede marcar/reprogramar la reserva obtenida después por B. Un envío duplicado sigue siendo posible y debe conservar ID/contenido. Usar plazos acotados, sin renovación continua ni scheduler sofisticado.

No hacer transacción distribuida entre bases, ni mantener SQL abierto mientras se espera al broker. Si se genera un mensaje interno además del público, outbox registra destinos separados y solo marca el destino confirmado. No obligar a todos los servicios a reproducir los tres destinos de Entrada.

## Errores sin plataforma de replay

| Situación | Comportamiento mínimo |
|---|---|
| Petición empresarial válida pero sin oferta | Persistir rechazo + outbox + inbox; ACK después del commit |
| Duplicado coherente | Recuperar efecto confirmado; ACK sin segunda mutación |
| PostgreSQL/Pulsar inaccesible | Conservar pendiente; reintento con espera acotada; sin ACK de trabajo perdido |
| Mensaje inválido o contradictorio | Log con ID y motivo, conservarlo sin ACK, pausar ese bucle de consumo para inspección y marcar readiness no disponible; no bucle rápido infinito |
| Política/catálogo requerido ausente | Error de configuración recuperable; no inventar rechazo de negocio |

La política simple de pausar la fuente afectada ante mensaje venenoso es una limitación aceptada de la POC. El supervisor conserva motivo/ID y expone el fallo: la API no debe aparentar procesamiento saludable. No vincular liveness a este error ni provocar un ciclo de reinicios automáticos; el operador corrige la causa y reinicia el servicio completo. Con varias réplicas, detener la corrida inválida para evitar que el mensaje rote entre ellas. Para los controles negativos usar tópicos de prueba separados y reiniciables. En corridas válidas exigir cero mensajes inválidos y cero pendientes sin explicación. No contar un mensaje detenido o en DLQ como negocio completado. Si se incorpora DLQ nativa, documentar el soporte real del cliente; no asumir opciones del SDK Java en Python.

## Probar lo que importa

Para código no trivial: primero test rojo del comportamiento, implementación mínima y refactorización. La fase 03 puede usar dobles en memoria; su evidencia debe decir que aún no hay durabilidad ni proceso autónomo.

| Nivel | Prueba mínima |
|---|---|
| Unidad | Invariantes, estados, duplicados, conflictos, dinero o combinación de fragmentos; sin red |
| Aplicación | UoW, resultados, salidas y rollback con puertos falsos |
| Contrato | Ejemplos y schemas, Avro binario, traducción y campos requeridos |
| PostgreSQL | Migración vacía, round-trip, rollback, UNIQUE y carreras sincronizadas |
| Pulsar | Publicación/consumo real, commit sin ACK, reinicio con misma suscripción |
| HTTP | GET real tras consumo, ausencia y filtros; jamás fallback al productor |
| Experimental | Métricas y fallas de E3/E4/E8 con cuatro servicios y recursos registrados |

No sustituir las pruebas de carrera por Postman. Postman/curl sí ayudan a demostrar API; pytest controla ventanas exactas de transacción y fallos. Tampoco usar solamente inspección de imports para probar comunicación: mostrar cambios persistidos por consumidores reales.

No confundir `fila creada`, `evento enviado`, `salida marcada` y `vista convergida`. Cada espera de test debe observar la etapa que afirma y tener timeout, en vez de sleeps arbitrarios.

## Verificación y evidencia por incremento

Entrada registra estos comandos reales en su [evidencia 06](../entrada-solicitudes-partner/docs/plans/evidencia-06-cqrs-api.md):

```bash
uv run --locked pytest tests -q -s --tb=short
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src tests scripts migraciones
uv run --locked python scripts/verify_distribution.py
git diff --check
```

**No asumir que ya funcionan en los nuevos repositorios.** En 01 configurar suites/rutas y crear la verificación de distribución equivalente; cuando aún no haya migraciones no incluir una ruta inexistente. Antes de cada commit o push solicitado ejecutar la suite completa vigente del servicio, lint, formato, tipos y empaquetado. No publicar con checks pendientes ni hacer commit por el solo hecho de ejecutar el plan.

Cada `docs/evidencias/NN-*.md` registra: alcance terminado, test rojo significativo, comandos realmente ejecutados, resultados, IDs de demo, versiones, limitaciones y siguiente dependencia. No fijar “253 tests” como objetivo: ese conteo pertenece a Entrada.
