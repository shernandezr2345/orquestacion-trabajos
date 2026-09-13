# 05 — Entrada y cotización mediante Pulsar

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: [04](04-postgresql-uow-outbox.md). Las dependencias entre servicios están en el índice.

**Objetivo:** iniciar automáticamente el Trabajo con el contrato real de Entrada y enviar el comando público.

**Archivos:** `infraestructura/{consumidores,mapeadores_eventos}.py`, `infraestructura/esquemas/`, `infraestructura/{ciclo_vida,despacho}.py` y `api/app.py`, `config/rutas.py`, `scripts/preparar_pulsar.py`, `docs/contratos/`. Exportar el schema de SolicitarCotizacion.v1 y TrabajoCreado.v1; incorporar copias verificadas de los schemas de Entrada y resultados de Cotizaciones.

**Trabajo:** consumir `orquestacion-solicitudes-v1`, crear efecto y ACK después de commit. Publicador manda TrabajoCreado y SolicitarCotizacion por destinos independientes y solo marca cada salida tras su confirmación. No prometer orden entre tópicos. El lector de CotizacionRegistrada tolera revisiones compatibles y campos adicionales desde v1; congelarlo antes de E3. Dos consumidores de resultados invocan el mismo caso de uso mediante traducción explícita. No reenviar solicitudes a Cotizaciones usando el nombre de evento original. Shared reparte carga y exige protección SQL ya implementada.

**Pruebas:** productor real de Entrada → nuevo consumidor → una fila, comando y evento de creación reales; retrasar la salida de creación y comprobar que Cotizaciones puede resolver antes de que Seguimiento la reciba; durante desarrollo, productor de contrato puede sustituir temporalmente a Cotizaciones pero se etiqueta como doble. Reabrir consumidor tras commit sin ACK y comprobar un efecto. Broker caído deja outbox recuperable. Dato inválido no recibe ACK exitoso.

**Cierre:** servicios autónomos con un arranque integrado cada uno, tópico/suscripciones documentados y primer intercambio real Orquestación/Cotizaciones cuando ambos estén disponibles. Si solo pasó con doble, cerrar adaptador local y dejar explícitamente pendiente integración grupal.

**Ejecución y cierre:** integrar los adaptadores en el lifespan de FastAPI y ejecutar las pruebas de composición de la [base común](../02-base-de-implementacion.md). No se inicia otro ejecutable: el mismo arranque atiende HTTP y consume Pulsar aunque no haya solicitudes HTTP. En los productores también despacha outbox; registrar estado de cada bucle y conservar suscripciones al cerrar.
