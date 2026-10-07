# 🎮 STOP MULTIJUGADOR — V5

Juego STOP multijugador web en tiempo real con FastAPI + WebSocket y frontend HTML/CSS/JavaScript.

## Estado V5

- Estado inicial completamente vacío: el servidor arranca con **0 salas**.
- No existe sala global ni código de sala predeterminado.
- El primer jugador debe crear una sala o introducir un código existente.
- Unirse a una sala inexistente se rechaza.
- Las salas abandonadas se limpian después de la ventana de reconexión.
- La reconexión legítima por token conserva la partida durante esa ventana.
- Un usuario nuevo nunca hereda una partida abandonada.
- Un único `GestorSalas` administra creación, consulta y eliminación de salas.
- `/health` está disponible para el health check de Render.
- Límite de 20 jugadores y 20 espectadores por sala.
- Límite de 20 caracteres para nombres en backend y frontend.
- Límite de 64 KiB por mensaje WebSocket y rate limit por conexión.
- Tokens de sesión criptográficamente aleatorios.
- Validación de avatar, respuestas, votos y acciones del anfitrión en servidor.
- Motor duplicado `v4_game.py` eliminado.
- Tests duplicados exactos eliminados.
- Prueba de extremo a extremo con tres jugadores incluida.
- Las notificaciones muestran cuando un jugador se ha unido o ha salido; al desconectarse se informa que abandonó la partida y al volver se informa que se reconectó.
- El confeti de celebración se deduplica por evento para evitar efectos repetidos.

## 🎵 Música

La V5 incluye música de fondo continua generada localmente con Web Audio API. No descarga pistas de terceros, no usa una API de pago y no requiere una suscripción.

- Se activa por defecto después de la primera interacción del usuario para respetar las políticas de autoplay del navegador.
- Puede activarse/desactivarse.
- Tiene control de volumen.
- Se mantiene en bucle durante la sesión.
- Los efectos de juego continúan separados de la música.

## Ejecutar localmente

```bash
pip install -r requirements.txt
uvicorn backend.web_server:app --host 0.0.0.0 --port 8000
```

Abrir `http://localhost:8000`.

Health check:

```text
GET /health
```

Respuesta esperada:

```json
{"status":"ok","version":"5.0.0","salas_activas":0}
```

## Tests

```bash
pytest -q
```

La suite V5 incluye pruebas unitarias, reglas de negocio, ciclo de vida, reconexión, audio, aislamiento de salas y una prueba WebSocket de extremo a extremo con tres jugadores.

## Render

`render.yaml` utiliza:

- build: `pip install -r requirements.txt`
- start: `uvicorn backend.web_server:app --host 0.0.0.0 --port $PORT`
- health check: `/health`
- auto deploy: activado

## Estructura

```text
backend/
  servidor.py       # motor de juego
  web_server.py     # FastAPI, WebSocket y GestorSalas
  validaciones.py   # validación de respuestas
frontend/
  index.html
  style.css
  app.js
tests/
  ...               # suite V5
render.yaml
requirements.txt
```

## Licencias de audio

La música de fondo de V5 es **síntesis generada por el propio navegador** mediante Web Audio API, por lo que no incorpora archivos musicales externos ni dependencias de pago.
