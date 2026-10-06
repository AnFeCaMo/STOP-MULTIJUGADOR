# STOP Multijugador Web 🎮

Una plataforma web multijugador en tiempo real para el clásico juego de **STOP** (Tutti Frutti / Bachillerato), desarrollada con una arquitectura Cliente-Servidor moderna basada en **FastAPI**, **WebSockets**, y un frontend ligero en **HTML5**, **CSS3** y **JavaScript Vanilla**.

Permite que múltiples compañeros jueguen simultáneamente desde sus computadores abriendo **Google Chrome**, sin necesidad de instalar Python, Pygame ni descargar ningún archivo en sus máquinas cliente.

---

## 1. Tecnologías Utilizadas

### Backend
* **Python 3.10+**
* **FastAPI**: Framework web asíncrono y de alto rendimiento.
* **Uvicorn**: Servidor ASGI ultrarrápido para producción y desarrollo.
* **WebSockets**: Comunicación bidireccional en tiempo real entre el servidor y todos los navegadores.
* **Validación y votación en memoria**: nombres y respuestas reconocidas se validan automáticamente; una respuesta desconocida con la letra correcta puede pasar a votación WebSocket.

### Frontend
* **HTML5 Semántico**: Estructura limpia y accesible.
* **CSS3 Moderno**: Diseño oscuro (*Dark Slate / Indigo*), tarjetas elevadas, botones ergonómicos, tipografía moderna y diseño 100% responsivo.
* **JavaScript Vanilla (ES6+)**: Detección dinámica del host WebSocket (`window.location.host`), sincronización en tiempo real, sistema de reconexión automática y renderizado dinámico de pantallas.

---

## 2. Estructura del Proyecto

```text
STOP-MULTIJUGADOR/
├── backend/
│   ├── __init__.py
│   ├── servidor.py         # Lógica central del juego, control de estado y puntuaciones
│   ├── validaciones.py     # Diccionario y validación local por categorías
│   └── web_server.py       # Aplicación FastAPI y endpoint WebSocket (/ws)
├── frontend/
│   ├── index.html          # Interfaz web única (SPA) con todas las pantallas
│   ├── style.css           # Estilos oscuros, responsivos y componentes visuales
│   └── app.js              # Cliente WebSocket, manejo de estados y eventos
├── web_server.py           # Punto de entrada directo para iniciar el servidor
├── tests/                  # Pruebas organizadas por fase y funcionalidad
│   ├── test_fase*.py
│   └── test_*.py
├── .gitignore              # Archivos locales que no deben distribuirse
├── requirements.txt        # Dependencias del proyecto
└── README.md               # Documentación completa del proyecto
```

---

## 3. Instalación y Requisitos

### Requisitos previos
* Python 3.10 o superior instalado en el servidor.
* Navegador Google Chrome (o cualquier navegador moderno con soporte para WebSockets).

### Pasos de instalación

1. **Clonar o ubicarse en el directorio del proyecto:**
   ```bash
   cd STOP-MULTIJUGADOR
   ```

2. **Crear y activar un entorno virtual (opcional pero recomendado):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   *(En Windows: `venv\Scripts\activate`)*

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 4. Cómo Iniciar el Servidor

El servidor escucha en `0.0.0.0` en el puerto `8000`.

Puedes iniciarlo con cualquiera de los dos comandos siguientes:

### Opción A (Recomendada):
```bash
python3 web_server.py
```

### Opción B (Con Uvicorn directo):
```bash
python -m uvicorn backend.web_server:app --host 0.0.0.0 --port 8000
```

---

## 5. Cómo Jugar desde Google Chrome

Los jugadores **no deben instalar nada**. Solo deben abrir su navegador Google Chrome y navegar a la dirección correspondiente:

### Si juegas en la misma computadora (Local):
Abre una o más pestañas de Chrome en:
```text
http://127.0.0.1:8000
```

### Si juegas en red
Los participantes abren en el navegador la dirección del equipo que ejecuta el servidor, por ejemplo `http://192.168.1.20:8000`. El frontend detecta automáticamente el host y el protocolo WebSocket (`ws://` o `wss://`).

---

## 6. Despliegue en Render

Crear un **Web Service** conectado al proyecto con:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python -m uvicorn backend.web_server:app --host 0.0.0.0 --port $PORT`

El servidor sirve el frontend y el endpoint WebSocket desde el mismo proceso. El estado de las salas vive en memoria; se debe desplegar una sola instancia/proceso y tener presente que un reinicio termina las partidas activas. No se requiere base de datos, API de pago ni archivo de configuración adicional.

---

## 7. Flujo de Juego y Reglas

### A. Registro y Sala de Espera
1. Cada jugador escribe su nombre y presiona **ENTRAR A LA SALA**.
2. El primer jugador en conectarse se convierte automáticamente en el **👑 Anfitrión**.
3. Los jugadores esperan en la sala mientras ven en vivo la lista de participantes conectados.
4. El anfitrión elige entre **4 y 10 rondas**, selecciona al menos **3 categorías** y presiona **INICIAR RONDA**.

### B. Ronda Activa
1. El servidor selecciona una letra aleatoria que no se haya usado en la partida.
2. Cada participante completa las categorías activas que configuró el anfitrión:
   * **1. Nombre**
   * **2. Apellido**
   * **3. Ciudad**
   * **4. Fruta**
   * **5. Animal**
   * **6. Cosa**
3. Cada ronda dura 60 segundos. El primer jugador en terminar puede confirmar **¡STOP!**; si nadie lo hace, la ronda cierra al agotarse el tiempo.
4. El servidor finaliza la ronda de inmediato y descarta presiones de STOP posteriores.

### C. Validación, votación y resultados
El servidor aplica estas reglas:
* Si la respuesta no comienza con la letra de la ronda, obtiene 0 puntos.
* Si comienza con la letra y se reconoce, se valida automáticamente. Los nombres conocidos también se reconocen automáticamente.
* Si comienza con la letra pero no se reconoce, pasa a votación.
* El jugador que escribió una respuesta **no puede votar su propia respuesta**.
* La mayoría de votos **SÍ** aprueba la respuesta; una mayoría de votos **NO** la rechaza. En caso de empate, la respuesta queda rechazada.
* **10 puntos:** respuesta válida y única.
* **5 puntos:** respuesta válida pero repetida por dos o más jugadores.
* **0 puntos:** respuesta vacía, con letra incorrecta o rechazada por votación.
* Una respuesta válida y única vale 10 puntos; una válida repetida vale 5.
* Si un jugador obtiene 10 puntos en todas las categorías activas, recibe **+10 de ronda perfecta**.
* La partida muestra clasificación, respuestas e historial; al final presenta estadísticas y permite al anfitrión iniciar una nueva partida en la misma sala.
* Una persona que entra durante una ronda o votación es espectadora y pasa a jugador elegible al cerrarse esa ronda.

Después de STOP, las respuestas pendientes aparecen en una pantalla de votación. Cuando termina la votación, los resultados muestran el **desglose de puntos debajo de cada respuesta**, además de los puntos de la ronda, el **TOTAL ACUMULADO** y el **HISTORIAL**.

### D. Cambio Dinámico de Anfitrión y Desconexiones
Si el anfitrión cierra Chrome o se desconecta, el servidor transfiere automáticamente el rol de anfitrión al siguiente jugador conectado sin interrumpir la partida.

La sala muestra el estado de cada participante: conectado, desconectado, reconectando, escribiendo, completó o espectador. Una sesión desconectada durante cinco minutos se etiqueta como ausente. Los avisos de entrada, desconexión y reconexión se muestran temporalmente en la interfaz.

Los estados emocionales automáticos acompañan la presencia y los resultados: 😎 esperando, 🤔 escribiendo, 😱 STOP, 🥳 ganando, 😭 perdiendo, 🔥 ronda perfecta, 🏆 victoria, 😴 desconectado y 🔄 reconectando. Al entrar se muestra «✨ 👋 ¡Nombre se ha unido!», al salir «👋 Nombre abandonó la partida.» y al reconectar «🔄 ¡Nombre se reconectó!».

Al confirmar STOP, el servidor cierra la ronda una sola vez y anuncia «💥 STOP 💥» junto con el nombre del jugador. El avatar de quien presionó salta brevemente y se reproducen tonos de alerta e impacto generados localmente con Web Audio API.

---

## 8. Pruebas Automatizadas

Las pruebas están organizadas en la carpeta `tests/`. Instala las dependencias de la aplicación con `pip install -r requirements.txt` y pytest como dependencia de desarrollo con `pip install pytest`. Después ejecuta la batería completa:
```bash
python -m pytest -q
```

---

## 9. Créditos del Proyecto

**Desarrollado por el Ing. Andrés Camacho y la Ing. Yulesi Carraza**

## Mejoras V2 — Experiencia de juego y gamificación
### Gestión inteligente de reconexiones y partidas abandonadas

- Si todos los participantes se desconectan, la sala conserva la partida durante una ventana breve de **8 segundos** para permitir una reconexión legítima.
- Si alguien de la partida original vuelve con su token dentro de esa ventana, recupera exactamente su sesión y la partida continúa.
- Al perder la conexión, el banner «🔄 Reconectando...» permanece visible hasta que el servidor confirma la sesión; al recuperar la partida muestra «✅ Conexión recuperada». El cliente vuelve a entrar en el código de sala guardado y el servidor restaura el mismo jugador sin duplicarlo.
- Si nadie vuelve, el servidor limpia automáticamente jugadores, espectadores, historial, puntuaciones, letras y estado de la partida, dejando una sala nueva.
- Si entra un usuario nuevo sin token cuando la sala estaba abandonada, no hereda la partida anterior: se inicia una sala limpia.
- Si al menos un jugador permanece conectado, la partida nunca se reinicia por desconexiones parciales.
- Las salas con código se retiran del registro si siguen vacías al terminar la ventana de reconexión; sus temporizadores y avisos pendientes también se cancelan. La sala predeterminada se conserva.
- Al cerrar una votación se conservan los resultados resumidos y los detalles finales, pero se liberan de memoria los votos individuales temporales. Los temporizadores de ronda completados se retiran de su registro.


- Duración predeterminada de cada ronda: **60 segundos**.
- Animación de inicio de ronda y anuncio de letra.
- Secuencia breve de letras antes de revelar la letra final compartida de cada ronda; al reconectar se conserva la letra del servidor y no se reinicia la animación de una ronda que ya está en curso.
- Animación especial al presionar **STOP**, con emoji 😂 y nombre del jugador.
- Temporizador con alerta ⚠️ en los últimos 10 segundos, cuenta regresiva visual y sonido de suspenso del 5 al 1, y anuncio «💥 ¡TIEMPO!» con audio al llegar a cero.
- Audio local con música ambiental de concentración opcional, control independiente de música, volumen general y sonidos para votación, resultados, victoria, derrota y logros, además de STOP e impacto. El audio se sintetiza con Web Audio API y no utiliza servicios externos.
- Estados de jugadores en tiempo real: **escribiendo** / **completó**. En resultados, cada respuesta se etiqueta como **✅ Correcta +10**, **⚠️ Repetida +5** o **❌ No válida +0**, respetando la puntuación y validación existentes.
- Pantalla **🗳️ VOTACIÓN** con conteos visibles de SÍ/NO, bloqueo inmediato de votos repetidos y validación del servidor que impide votar la propia respuesta o votar después de cerrarse la fase.
- Resultados presentados brevemente como «⏳ Calculando...» → «✅ Respuesta aceptada» → puntuación final; se conservan los datos confirmados por el servidor al reconectar.
- Selección de 21 personajes emoji locales, guardada en el navegador y asociada a la sesión para conservarla al reconectar.
- El avatar se muestra junto a cada jugador en la sala, la ronda, la votación, los resultados y el historial.
- Animaciones CSS ligeras por personaje (saltos, balanceos, flotación y movimiento mecánico), limitadas a transformaciones y compatibles con la preferencia de movimiento reducido del sistema.
- Puntos de ronda con animación de entrada.
- Los puntos positivos vuelan desde el resultado de cada jugador hasta su total en la clasificación; los cero no reproducen una celebración y los resultados repetidos no vuelven a animarse.
- Confeti ligero y temporal en victoria, nuevos logros/campeón y ronda perfecta; se limita a 42 piezas, se evita repetir por mensaje duplicado y se oculta si el usuario prefiere movimiento reducido.
- Perfil temporal durante la partida con avatar, nombre, victorias de partida, puntos, rondas ganadas y STOP; se mantiene solo en la memoria de la partida y se limpia al finalizarla o reiniciarla.
- Sistema de logros: 🏆 Primera victoria, ⚡ Respuesta rápida, 🔥 3 rondas consecutivas, 🎯 Todas las respuestas válidas, 😂 Rey del STOP, 👑 Campeón (primer lugar al terminar), 🧠 Experto (200 puntos acumulados) y 🚀 STOP relámpago (STOP en 5 segundos o menos). Los logros nuevos se anuncian una sola vez con una animación de desbloqueo.
- Estadísticas finales resumidas: rondas, jugadores, palabras válidas, STOP realizados, mejor jugador y mayor puntuación, además de métricas detalladas.
- En el cierre de la partida, las estadísticas por jugador distinguen victorias de partida y rondas ganadas, e incluyen respuestas válidas, no válidas, repetidas, validadas/rechazadas, enviadas, promedio de puntos por ronda jugada y mejor ronda. Los empates cuentan para cada jugador empatado.
- Al finalizar la partida se muestra un podio animado para los tres primeros lugares; el ganador recibe corona y la celebración final existente. La clasificación del servidor sigue siendo la fuente del orden y la puntuación.
- El MVP Rey del STOP se elige entre quienes presionaron STOP: gana quien más veces lo hizo; en empate se compara puntuación acumulada, nombre y finalmente ID para producir un resultado estable. Si nadie presiona STOP, no se asigna el título.
- Cada sala se crea con un código aleatorio de cuatro caracteres para compartir. Los jugadores pueden crear una sala o unirse con un código existente; las salas conservan partidas y listas independientes. El código se recuerda junto al token de sesión para reconectar a la sala correcta.
- Las salas simultáneas mantienen aislados anfitrión, ronda, letra, respuestas, votos, puntuaciones, historial, estado y temporizador; iniciar o cerrar la ronda de una sala no modifica las otras.
- El estado de completitud de cada jugador se calcula una vez al serializar la ronda. Los broadcasts reutilizan la serialización por rol y envían los mensajes en paralelo, manteniendo el aislamiento y el indicador de espectador.
- Sonidos generados con Web Audio API, sin archivos externos ni servicios de pago.
- Animaciones realizadas con CSS/JavaScript, sin librerías de pago ni dependencias externas adicionales.
- Pruebas automatizadas ampliadas para las nuevas funciones.

## 10. Estado V4 y auditoría de fases

Esta versión integra la evolución definida en el **Código Maestro STOP MULTIJUGADOR V4** sobre la arquitectura existente, sin reconstruir el proyecto desde cero.

### Fases integradas

- **Fase 0:** diagnóstico, línea base y configuración reproducible de pruebas.
- **Fases 1–5:** reconexión por token, limpieza de sesiones, seguridad de acciones, anfitrión y estados de presencia.
- **Fases 6–10:** avatares locales, animaciones ligeras, reacciones predefinidas, emociones automáticas y avisos de entrada/salida/reconexión.
- **Fases 11–18:** STOP único, temporizador de 60 segundos, audio Web Audio API, animación de letra, estados de respuesta, animación de puntuación, votación y resultados progresivos.
- **Fases 19–24:** logros, perfil temporal, estadísticas, podio, Rey del STOP y confeti.
- **Fases 25–29:** códigos de sala, multisala aislada, optimización de broadcasts, limpieza de memoria y reconexión de experiencia completa.
- **Fases 30–34:** batería ampliada de pruebas, regresión, auditoría de archivos/dependencias, documentación y prueba final de flujo.

### Verificación realizada sobre esta entrega

La batería completa actual contiene **115 pruebas automatizadas** y fue ejecutada después de integrar las pruebas de cierre V4:

```text
115 passed
```

También se verificó que:

- `python -m pytest -q` funciona desde la raíz gracias a `pythonpath = .` en `pytest.ini`.
- El servidor ASGI inicia correctamente con Uvicorn.
- La página principal responde por HTTP 200.
- El WebSocket acepta una conexión, crea una sala y devuelve su código de cuatro caracteres.
- No se distribuyen `.venv/`, `__pycache__/`, `.pytest_cache/` ni archivos `.pyc` en el paquete final.
- No se requieren APIs de pago ni recursos externos para audio o animaciones.

### Ejecución de pruebas

```bash
python -m pytest -q
```

Resultado esperado de esta entrega:

```text
115 passed
```

> Nota: Render debe ejecutarse como una sola instancia/proceso si se desea mantener el estado de las salas en memoria. Un reinicio del servicio elimina las partidas activas, tal como corresponde a esta arquitectura sin base de datos.
