# 🔎 Auditoría final — STOP Multijugador V5

## Resultado

La versión V5 fue revisada desde la raíz y corregida sin depender de una sala predeterminada.

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
- README actualizado a V5.
- Sintaxis Python y JavaScript validada.

### Audio

La música de fondo es síntesis local mediante Web Audio API. No se descarga audio externo, no depende de un proveedor de pago y puede activarse/desactivarse con control de volumen. Se inicia después de una interacción del usuario para respetar el bloqueo de autoplay de los navegadores.

## Pruebas finales

```text
127 passed
```

Incluye una prueba WebSocket de extremo a extremo con tres jugadores y pruebas nuevas de V5 para estado inicial, salas, límites, `/health`, ausencia de sala predeterminada y música.
