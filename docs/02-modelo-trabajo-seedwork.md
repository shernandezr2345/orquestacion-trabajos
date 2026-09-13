# 02 — Modelo de Trabajo y seedwork

Estado: pendiente. Servicio: orquestacion. Ver [modelo y secuencia](README.md), [base común](../02-base-de-implementacion.md) y [contratos](../01-contratos-y-datos.md).

Dependencia local: [01](01-base-tecnologica.md). Las dependencias entre servicios están en el índice.

**Objetivo:** implementar las transiciones de la tabla con identidad/versiones y datos propios.

**Archivos:** `modulos/trabajos/dominio/{entidades,objetos_valor,eventos,repositorios,excepciones}.py`; `seedwork/dominio/{entidades,objetos_valor,eventos}.py`; `tests/unitarias/dominio/test_trabajos.py`. En objetos valor agrupar `OrigenSolicitud`, `CondicionesAtencion`, `ResultadoCotizacion` si las invariantes justifican esos tipos. No importar `SolicitudPartner` ni tipos de Cotizaciones.

**Red:** una solicitud lista produce PENDIENTE_COTIZACION; cotización ajena falla; mismo resultado no duplica; contrario falla; versión esperada antigua falla; reconstruir COTIZADO conserva versión sin eventos.

**Green:** implementar métodos de agregado y hechos internos `TrabajoCreado` y `CotizacionAplicada`. El evento interno de creación permite preparar TrabajoCreado.v1 y el comando público como dos mensajes distintos; crear un comando no transforma su intención en evento empresarial.

**Decisión:** creación y petición se confirman en una misma operación local; no añadir segundo módulo para justificar una vuelta por bus. Evento pendiente, serialización pública y publicación son etapas distintas.

**Cierre:** matriz de estados y pruebas negativas verificadas sin PostgreSQL. Verificar datos completos de creación y ausencia de eventos nuevos al reconstruir.
