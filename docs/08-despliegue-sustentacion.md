# 08 — Despliegue y sustentación

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: [07](07-integracion-experimentos.md). Las dependencias entre servicios están en el índice.

**Objetivo:** entregar una imagen y un único arranque FastAPI con API, consumidores y despacho integrados, base/volumen propios y migraciones previas a réplicas.

**Trabajo:** construir imagen bloqueada; configurar host de Pulsar accesible; suscripciones antes de enviar; señales de apagado; logs con mensaje/solicitud/trabajo/petición; documentación del puerto y variables; verificar instalación limpia. Registrar hash de imagen/commit y cambios de trabajo si no hay commit.

**Verificación:** arrancar desde dependencias bloqueadas y base de laboratorio nueva; repetir el smoke con cuatro servicios; reiniciar sin borrar estado; comprobar consultas y pendientes desde otro proceso. Ejecutar suite completa, lint, formato, tipos y empaquetado del servicio; guardar comandos y resultados junto a evidencia del despliegue.

**Guion de 5 minutos:** recibir solicitud → Trabajo/inbox y dos salidas → evento TrabajoCreado en Seguimiento → comando a Cotizaciones → pausa con Trabajo pendiente → resultado después de recuperar → vista de Seguimiento. Mostrar resultado antes de creación con pausa controlada, y explicar que la vista no es autoridad del Trabajo. Durante E3, Cotizaciones/Seguimiento evolucionan y Orquestación mantiene su mismo artefacto lector.

**Cierre:** otro compañero reproduce el recorrido con comandos documentados; suite completa/lint/tipos pasan en el entorno del servicio; evidencia de despliegue real y contribuciones. El responsable también lidera la integración grupal/E4, pero conserva tiempo asignado a su microservicio. Saga y BFF quedan para entrega 5.

**Plataforma:** un Cloud Run Service, un contenedor de aplicación y un proceso ASGI por instancia; CPU/facturación por instancia, escala manual habitual 1. PostgreSQL en Cloud SQL propio, Pulsar en infraestructura externa y migraciones como paso previo. Aplicar el [protocolo común](../03-integracion-experimentos-y-entrega.md) para conectividad, escala y SIGTERM. Verificar consumo y avance durable durante un intervalo sin HTTP antes de declarar el despliegue listo. Nunca persistir estado empresarial en el filesystem del contenedor.
