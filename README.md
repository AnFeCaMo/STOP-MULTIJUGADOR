# STOP Multijugador

Juego de STOP en tiempo real con FastAPI, WebSocket y frontend HTML/CSS/JavaScript.

**Desarrollado por el Ing. Andrés Camacho y la Ing. Yulesi Carranza.**

## Inicio local

Instala las dependencias del servidor y arráncalo:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m uvicorn backend.web_server:app --host 127.0.0.1 --port 8001
```

Abre <http://localhost:8001>. La ruta `./.venv/bin/python -m uvicorn backend.web_server:app --host 127.0.0.1 --port 8001` también es el comando recomendado para iniciar el servidor desde el entorno virtual.

El archivo de compatibilidad `web_server.py` en la raíz permite iniciar el mismo servidor en el puerto 8000 con `python web_server.py`. En Render, `render.yaml` conserva el arranque con el puerto asignado por la plataforma.

## Despliegue

El servicio está configurado para una instancia de Render. Las salas, sesiones y partidas se guardan en memoria: un reinicio las termina y no se deben ejecutar varias instancias si los jugadores necesitan compartir salas. Render Free suspende el servicio tras 15 minutos sin tráfico y el primer acceso posterior requiere un arranque en frío. Para disponibilidad continua o varias instancias, hace falta elegir un plan adecuado y añadir almacenamiento y coordinación compartidos antes de escalar.

El propietario confirma que tiene permiso para publicar y usar los personajes y retratos de Dragon Ball incluidos en el juego. Conserva junto con el proyecto cualquier autorización escrita y sus condiciones de uso.

## Desarrollo y pruebas

Instala además las herramientas de desarrollo:

```bash
./.venv/bin/python -m pip install -r requirements-dev.txt
./.venv/bin/python -m pytest -q
```

La suite está agrupada en `tests/features/`, `tests/integration/` y `tests/regression/`. `pytest.ini` descubre las pruebas de forma recursiva bajo `tests/`.

El generador de los retratos usa Pillow. Para regenerar los 260 SVG desde la tabla fuente:

```bash
python3 tools/generar_avatares_vectoriales.py
```

## Funciones del juego

- Salas aisladas, anfitrión, espectadores, WebSocket y reconexión por sesión.
- Temporizador, STOP, categorías estándar y personalizadas, validación híbrida y votación.
- Puntuación, resultados, clasificación, perfil temporal, logros e historial.
- Música local con controles de volumen independientes para música y efectos.
- Veinte personajes de Dragon Ball, cada uno con doce expresiones locales. El menú usa la expresión normal; durante la partida los estados se activan por eventos del juego.
- Las notificaciones indican cuando un jugador se ha unido, abandonó la partida o se reconectó. El confeti de celebración se deduplica por evento.
- Diseño adaptable a escritorio y móviles, con respeto a `prefers-reduced-motion`.

Las categorías geográficas amplias se agrupan como **Ciudad**. Frutas, tubérculos y plantas se agrupan como **Fruta**. Las respuestas que cumplen la letra pero no se pueden validar automáticamente pasan a votación.

## Salud del servidor

`GET /health` responde, por ejemplo:

```json
{"status":"ok","version":"6.0.0","salas_activas":0}
```

## Estructura

```text
backend/
  data/                 Catálogos locales JSON
  servidor.py           Estado y reglas del juego
  validaciones.py        Normalización y validación de respuestas
  web_server.py          FastAPI, WebSocket, salas y recursos HTTP
frontend/
  assets/
    audio/              Música local de fondo
    avatars/            Retratos y expresiones Dragon Ball locales
  avatar-catalog.js     IDs estables, nombres y rutas locales
  app.js                Cliente, pantallas y conexión WebSocket
  index.html
  style.css
docs/                   Auditorías e informes de proyecto
tests/
  features/             Pruebas de funciones del juego y la interfaz
  integration/          Pruebas de interacción entre componentes
  regression/           Pruebas de fases y endurecimiento anteriores
tools/                  Generadores de recursos
  source-assets/       Entradas locales de generadores; no se sirven al navegador
requirements.txt        Dependencias de ejecución
requirements-dev.txt    Dependencias de desarrollo
render.yaml             Configuración de despliegue en Render
```

La música se sirve en `/audio/background.mp3`; el health check de Render usa `/health`. Los detalles de atribución y permiso declarado para los avatares están en `frontend/assets/avatars/LICENCIA.md`.
