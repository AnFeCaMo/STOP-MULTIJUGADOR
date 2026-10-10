# 🔎 Auditoría final — STOP Multijugador V6

## Resultado

La versión V6 fue revisada desde la raíz y corregida sin depender de una sala predeterminada.

### Estado inicial

- El proceso arranca con `0` salas activas.
- No existe código global `7K4P` ni fallback equivalente.
- Un WebSocket recién abierto no recibe una partida automáticamente.
- La sala solo existe después de una acción explícita de creación.
- Un usuario nuevo solo puede unirse a un código existente.

### Salas y ciclo de vida

- `GestorSalas` es el único registro de salas.
- Las salas se crean con códigos aleatorios de cuatro caracteres.
- Las salas abandonadas mantienen una ventana de reconexión de 8 segundos.
- Si nadie vuelve, el estado de la partida se limpia y la sala se elimina del registro.
- Un token desconocido no revive una sala antigua.
- Dos salas permanecen aisladas.

### WebSocket

- Validación de mensajes JSON.
- Límite de 64 KiB por mensaje.
- Rate limit por conexión.
- Validación de nombre, avatar, acción de sala y código.
- Límite de 20 jugadores y 20 espectadores por sala.
- Sesiones con tokens criptográficamente aleatorios.
- Reconexión controlada por token y código de sala.

### Render

- `GET /health` devuelve estado `200`.
- `render.yaml` apunta a `/health`.
- La aplicación raíz responde `200`.

### Código

- `backend/v4_game.py` eliminado por duplicar el motor activo.
- Tests duplicados exactos eliminados.
- README actualizado a V6.
- Sintaxis Python y JavaScript validada.

### Audio

La música de fondo es un MP3 local servido desde `/audio/background.mp3`; no depende de un proveedor externo. El navegador la inicia tras una interacción del usuario y la interfaz permite ajustar su volumen.

## Pruebas finales

```text
150 passed
```

Incluye una prueba WebSocket de extremo a extremo con tres jugadores y pruebas de estado inicial, salas, límites, `/health`, ausencia de sala predeterminada, categorías y funciones del juego. Las pruebas de fases anteriores incluyen la categoría `color`, que permanece activa aunque el anfitrión no la seleccione.

## Límite operativo y publicación

Render está configurado para una instancia. Las salas y sesiones existen solo en memoria, por lo que un reinicio las elimina y varias instancias no compartirían partidas. No escalar horizontalmente sin almacenamiento y coordinación compartidos.

El propietario confirma que tiene autorización para publicar y usar los personajes y retratos Dragon Ball incluidos. Conserva junto con el proyecto la autorización escrita y sus condiciones de uso.
