# Sistema de Alertas EAFIT

Prototipo del proyecto de la materia **Sistemas de Información** (Universidad EAFIT, 2026-2).
Avisa al personal de seguridad cuando detecta un comportamiento sospechoso en una sala de cómputo, guarda un
historial de eventos y, al confirmarse un hurto, crea el ticket de incidente y actualiza el estado del equipo.

Equipo: Simón Banda, Jaime Cotes y David Duarte. Profesor: Juan Carlos Quintero Vallejo.

> **Alcance del prototipo.** El detector usa YOLOv8 preentrenado (reconoce personas y equipos, no "robos") con tres
> reglas de comportamiento. La integración con Aranda está **simulada**: crea el ticket con los mismos campos que el
> formulario real, pero lo guarda en la base de datos propia. Todos los datos son de prueba.

## Historias de usuario

| HU | Qué hace | Dónde está |
|----|----------|------------|
| HU-01 | Alerta automática con sala, hora y captura, en menos de 30 s | `POST /api/eventos`, `/alertas`, `app/services/eventos.py` |
| HU-02 | Historial de eventos con filtros por sala, fechas y estado | `GET /api/eventos`, `/historial` |
| HU-03 | QR hacia el chat de Saúl en Teams (diseñado en el Sprint 1) | Evidencia en el informe; `/aviso/{serie}` para el QR del equipo |
| HU-04 | Al confirmar un hurto: ticket de incidente y equipo "pendiente de reposición" | `POST /api/eventos/{id}/confirmar`, `app/services/aranda_mock.py` |
| HU-05 | Panel de hurtos por sala y mes, costo estimado y calidad de las alertas | `GET /api/reportes/cifras`, `/panel` |
| HU-06 | Aviso al estudiante si el equipo tiene un caso abierto | `GET /api/publico/equipos/{serie}`, `/aviso/{serie}` |

## Cómo funciona

```
 Video / webcam ──► Detector (YOLOv8 ONNX + reglas) ──► POST /api/eventos ──► Servicio web (FastAPI) ──► Base de datos
                     app/detection/worker.py             X-API-Key            │                          (SQLite / PostgreSQL)
                                                                              ├─► Pantalla del guardia en vivo (SSE)
                                                                              ├─► Aviso a Teams (webhook)
                                                                              └─► Ticket simulado de Aranda (al confirmar)
```

Reglas de comportamiento (`app/detection/rules.py`):

1. **equipo_retirado**: un portátil que se veía estable desaparece mientras hay una persona en cuadro.
2. **permanencia_prolongada**: una persona permanece junto a un equipo más de 8 s.
3. **presencia_fuera_de_horario**: hay una persona en la sala entre las 22:00 y las 06:00.

El tiempo del criterio "menos de 30 segundos" se mide entre el instante en que el detector dispara la regla
(`ocurrido_en`) y el instante en que el servicio termina de avisar (`notificado_en`). Queda guardado en cada evento.

## Requisitos

- Python 3.12 o superior.
- Para el detector: un video de prueba o una webcam.

## Instalación y ejecución local

```bash
python -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env                 # en Windows: copy .env.example .env
# Edite .env: defina SECRET_KEY y DETECTOR_API_KEY (instrucciones dentro del archivo)
```

Cargue las variables del `.env` en su terminal (o defínalas a mano) y cree los datos de prueba:

```bash
python -m scripts.seed --historial   # crea salas, equipos y 3 usuarios de prueba; imprime la contraseña
uvicorn app.main:app --reload        # http://localhost:8000
```

Usuarios de prueba (misma contraseña, la que imprimió `scripts.seed`):

| Correo | Rol | Qué puede hacer |
|--------|-----|-----------------|
| `guardia@prueba.local` | guardia | Ver y decidir alertas, historial, capturas |
| `jefe@prueba.local` | jefe_seguridad | Todo lo anterior y el panel de cifras |
| `activos@prueba.local` | gestion_activos | Historial (sin capturas), panel y equipos |

### Ejecutar el detector

```bash
export DETECTOR_API_KEY=...          # la misma del servicio
python -m app.detection.worker --fuente videos/demo.mp4 --sala-id 1 --api-url http://localhost:8000
# con webcam:  --fuente 0
# probar la regla de fuera de horario:  --hora-simulada 23
```

El modelo `models/yolov8n.onnx` ya viene en el repositorio. Para regenerarlo: `python -m scripts.exportar_modelo`.

### Medir el criterio de 30 segundos

```bash
export DETECTOR_API_KEY=...
python -m scripts.medir_latencia --api-url http://localhost:8000 --sala-id 1 --n 30
```

Guarda `resultados_latencia.csv` con el detalle de cada evento.

## Pruebas

```bash
python -m pytest -q
```

Las pruebas cubren las reglas de detección con secuencias simuladas y los criterios de aceptación de las historias
de usuario (HU-01, HU-02, HU-04, HU-05 y HU-06), además de permisos por rol, bitácora de consultas y cabeceras de seguridad.
Se ejecutan automáticamente en GitHub Actions (`.github/workflows/ci.yml`).

## Variables de entorno

Ver `.env.example`. Ningún secreto va en el código ni en el repositorio: `SECRET_KEY`, `DETECTOR_API_KEY`,
`TEAMS_WEBHOOK_URL` y `DATABASE_URL` se definen en el ambiente de ejecución.

## Seguridad y datos personales (Ley 1581 de 2012)

- La IA detecta objetos y comportamientos; **no reconoce rostros**.
- Roles: guardia, jefe de seguridad y Gestión de Activos. Gestión de Activos no ve las capturas.
- Contraseñas con scrypt; sesión en cookie `HttpOnly` y `SameSite=Lax` (con `Secure` cuando `APP_ENV=prod`).
- Cada consulta del historial, de un evento o de una captura queda en la tabla `auditoria`.
- Cabeceras de seguridad y política CSP estricta (sin scripts ni estilos en línea).
- Todos los datos del prototipo son de prueba. Pendiente antes de un uso real: política de retención de las
  capturas (se propuso 30 días) y validación jurídica de la universidad.

## Despliegue

Pasos resumidos para Azure App Service (Azure for Students) con base de datos PostgreSQL:

1. Cree un **App Service** Linux con Python 3.12 y una base **Azure Database for PostgreSQL**.
2. En *Configuración > Variables de entorno* defina `APP_ENV=prod`, `APP_BASE_URL`, `DATABASE_URL`, `SECRET_KEY`,
   `DETECTOR_API_KEY`, `SEED_PASSWORD` y, si lo usa, `TEAMS_WEBHOOK_URL`.
3. Comando de inicio: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Conecte el repositorio de GitHub (*Centro de implementación*) para desplegar en cada cambio a `main`.
5. Cree los datos de prueba una vez: `python -m scripts.seed --historial` desde la consola SSH del App Service.
6. Compruebe `https://<su-app>.azurewebsites.net/salud`.

También se incluye un `Dockerfile` para ejecutar el servicio en cualquier proveedor de contenedores.

Ejecute **un solo proceso**: las alertas en vivo se reparten en memoria (suficiente para el piloto; para varios
procesos habría que usar un servicio de mensajería como Redis o Azure Web PubSub).

## Limitaciones conocidas

- El detector depende de la calidad del video y no se ha probado con cámaras reales de EAFIT.
- Las reglas pueden dar falsas alarmas (por ejemplo, si una persona tapa un portátil unos segundos); por eso el
  guardia confirma o descarta cada evento y el panel muestra el porcentaje de falsas alarmas.
- La integración con Aranda es simulada hasta confirmar con Gestión de Activos si hay API o ambiente de pruebas.
- No hay limitación de intentos de inicio de sesión (pendiente para una fase siguiente).

## Licencias de terceros

YOLOv8 (Ultralytics) se distribuye bajo AGPL-3.0; se usa aquí con fines académicos. Para un uso comercial habría que
revisar su licencia o usar otro modelo.
