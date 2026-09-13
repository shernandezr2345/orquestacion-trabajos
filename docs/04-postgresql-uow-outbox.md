# 04 — PostgreSQL, repositorios y salida durable

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: [03](03-casos-uso-idempotencia.md). Las dependencias entre servicios están en el índice.

**Objetivo:** conservar cada paso y resolver concurrencia con transacciones reales.

**Archivos:** `infraestructura/{orm,repositorios,mapeadores,serializacion,unidad_trabajo}.py`, `seedwork/infraestructura/{inbox,outbox}.py`, `migraciones/versions/0001_trabajos.py`, pruebas de repositorios/UoW/concurrencia/outbox.

**Modelo SQL propuesto:** `trabajos` (PK id_trabajo, UNIQUE id_solicitud e id_peticion, versión, estado, origen y condiciones, resultado de cotización); `inbox` (UNIQUE consumidor/id_mensaje, contenido); archivo de mensajes y `outbox` por destino si se reutiliza esa estructura de Entrada. Guardar datos de creación y dos salidas con IDs distintos. Una confirmación de publicación no marca la otra; una repetición de la solicitud tampoco regenera ninguna.

**Trabajo:** repositorios reciben la misma Session de UoW. Escritura con versión esperada y control de filas afectadas. Una colisión de UNIQUE empresarial relee en una transacción nueva, compara contenido y devuelve existente o conflicto; no capturar cualquier IntegrityError como duplicado. Serialización durable guarda los campos de correlación e instante originales. Publicación no ocurre dentro de la transacción.

**Pruebas PostgreSQL obligatorias:** migración vacía; round-trip en todos los estados; fallo entre inbox/Trabajo/outbox deja cero cambios; dos creaciones simultáneas producen un Trabajo y una petición; dos creaciones generan un único TrabajoCreado y un único SolicitarCotizacion; fallo en la segunda salida revierte toda la creación; resultado contradictorio conserva el anterior; reserva vencida no cambia la nueva; reinicio conserva salidas.

**Cierre:** evidencia SQL de atomicidad y carreras; script de inspección propio, no SQL en bootstrap. Entregar al equipo esquema y criterio de deduplicación, sin compartir credenciales/base.
