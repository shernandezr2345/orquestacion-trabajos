# 07 — Integración, fan-out y experimentos

Estado: pendiente. Servicio: orquestacion. Ver [modelo](README.md), [contratos](../01-contratos-y-datos.md) y [experimentos](../03-integracion-experimentos-y-entrega.md). Dependencia: [06](06-consultas-trabajo.md).

**Objetivo:** comprobar el recorrido automático con Cotizaciones y Seguimiento, recuperación E8 y lectura compatible E3.

**Archivos:** tests de integración de creación/resultados, scripts de solicitud/carga, test de lector tolerante y docs/evidencias/07-*.md. No crear scripts de trabajos ejecutados, evidencia de ejecución ni comandos de cierre.

**Trabajo:** desde Entrada real observar un Trabajo, una petición, TrabajoCreado y el resultado aplicado. Seguimiento recibe creación y resultado con suscripciones propias. Pausar envío de TrabajoCreado para forzar resultado primero: Seguimiento conserva parcial y luego completa. No usar el GET de Seguimiento para decidir una transición de Orquestación.

**Pruebas:** creación simultánea/repetida no duplica ninguna de las dos salidas; enviar una y fallar la otra conserva el pendiente correcto. Durante caída de Cotizaciones, Entrada acepta y Trabajo queda PENDIENTE_COTIZACION. Tras retorno, un resultado coherente lo actualiza. IDs y estado sobreviven reinicios; ACK nunca precede al commit.

**E3 reformulado:** congelar imagen/schema del lector v1 antes de que Cotizaciones añada duracion_estimada_minutos. Orquestación no usa ese campo: debe aplicar resultados de escritor v1/v2 con el mismo código, sin exigir version_contrato==1 ni rechazar campos desconocidos. Comparar el contenido de negocio conocido por ese lector; no adoptar una nueva estimación como actualización de una cotización anterior.

**E4:** medir nuevos trabajos/resultados persistidos y pendientes por etapa; mantener el comparador de carga y recursos. Seguimiento mide su demora por separado. No afirmar que el flujo termina antes de comprobar las dos bases.

**Cierre:** un recorrido inicial automático atraviesa los cuatro servicios; resultados consistentes y salidas reconciliadas; lector de Orquestación intacto durante E3. Evidencia de aceptación E8 se obtiene de Entrada, no solamente de la vista.
