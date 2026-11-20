# Verificación de los criterios de aceptación

Probado por: Jaime Cotes. Fecha: 20 de noviembre de 2026.
Aplicación probada: https://alertas-eafit-g4-hhcxg0c5cae2hjbr.westus3-01.azurewebsites.net

| Criterio | Qué hice | Resultado | Observación |
| --- | --- | --- | --- |
| HU-01-1 (Aviso < 30 s) | Revisé el tiempo de aviso mostrado en las tarjetas de alertas pendientes y el reporte de latencia | Cumple | Los eventos registrados muestran tiempos de aviso menores a 30 s (0,14 a 0,26 s en medición del servicio; sin cámaras reales) |
| HU-01-2 (Sala, fecha, hora y captura) | Abrí la pestaña Alertas como guardia y revisé el detalle de un evento | Cumple | Muestra sala, fecha, hora y espacio de captura (en eventos simulados sin imagen la captura sale vacía) |
| HU-01-3 (Registro en historial) | Verifiqué en la pestaña Historial que los eventos recibidos aparezcan listados | Cumple | Todos los eventos quedan registrados automáticamente en el historial |
| HU-02-1 (Datos y estado en historial) | Consulté la tabla de Historial como guardia y jefe de seguridad | Cumple | Muestra fecha, hora, sala, tipo de evento y estado (pendiente, confirmado o descartado) |
| HU-02-2 (Filtros de historial) | Filtré el historial seleccionando una sala, un rango de fechas y un estado | Cumple | El listado filtra correctamente los registros según los parámetros elegidos |
| HU-03-1 (QR visible en sala/equipo) | Revisé el estado de despliegue físico de los carteles con QR | Parcial | El diseño del cartel y la ruta pública funcionan, pero falta instalarlos físicamente en las salas |
| HU-03-2 (Acceso directo al chat de Saúl) | Verifiqué el enlace del QR hacia el canal de soporte | Cumple | Abre directamente el chat de Saúl en Teams sin pasos intermedios |
| HU-03-3 (Reutilización de Aranda) | Verifiqué el flujo de reporte de fallas desde el aviso | Cumple | Reutiliza el canal de Saúl y tickets de Aranda sin crear un sistema paralelo |
| HU-04-1 (Generación de ticket) | Entré como guardia, revisé una alerta pendiente y pulsé Confirmar hurto | Parcial | Genera el ticket con formato SAUL-AAAA-NNNNN en módulo simulado (sin conexión real a API de Aranda) |
| HU-04-2 (Equipo pendiente de reposición) | Revisé la pestaña Equipos tras confirmar un hurto sobre un equipo | Cumple | El equipo asociado cambia su estado a "Pendiente de reposición" con su número de ticket |
| HU-05-1 (Panel de cifras) | Entré como jefe de seguridad y Gestión de Activos y abrí Panel de cifras | Cumple | Muestra hurtos por sala, por mes, costo estimado acumulado y porcentaje de falsas alarmas |
| HU-06-1 (Aviso de caso abierto en QR) | Abrí el enlace "Ver aviso" de un equipo con ticket activo y de uno sin casos | Cumple | Muestra públicamente si el equipo tiene un caso abierto o está disponible sin exponer datos personales |
| HU-06-2 (Origen en sistema único) | Verifiqué de dónde toma el estado la vista pública del equipo | Parcial | Toma la información de la tabla de tickets simulados del prototipo |