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
├── test_juego.py           # Prueba de extremo a extremo mediante WebSockets
├── test_fase1.py           # Experiencia completa de ronda
├── test_fase2.py           # Espectadores y reconexión
├── test_fase3.py           # Clasificación, historial y nueva partida
├── test_fase4.py           # Configuración de partida
├── test_fase5.py           # Letras únicas y ronda perfecta
├── test_fase6.py           # Estadísticas
├── test_fase7.py           # Estructura UX/UI
├── test_auditoria.py       # Salas con 2, 5 y 10 participantes
├── test_reglas.py           # Validación automática y votación
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
uvicorn web_server:app --host 0.0.0.0 --port 8000
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

## 6. Flujo de Juego y Reglas

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

---

## 7. Pruebas Automatizadas

El proyecto incluye pruebas de reglas, fases y una prueba de extremo a extremo ([test_juego.py](test_juego.py)). Las pruebas de fases cubren temporizador, espectadores, reconexión, rondas e historial, configuración, bonus, estadísticas y nueva partida.

Instala las dependencias con `pip install -r requirements.txt`. Después ejecuta las pruebas:
```bash
for test_file in test_fase*.py test_auditoria.py test_reglas.py test_juego.py; do python3 "$test_file" || exit 1; done
```

---

## 8. Créditos del Proyecto

**Desarrollado por el Ing. Andrés Camacho y la Ing. Yulesi Carraza**

## Mejoras V2 — Experiencia de juego y gamificación

- Duración predeterminada de cada ronda: **60 segundos**.
- Animación de inicio de ronda y anuncio de letra.
- Animación especial al presionar **STOP**, con emoji 😂 y nombre del jugador.
- Temporizador con alerta visual durante los últimos 10 segundos y cuenta regresiva sonora en los últimos 5.
- Estados de jugadores en tiempo real: **escribiendo** / **completó**.
- Puntos de ronda con animación de entrada.
- Celebración final con confeti y sonido opcional.
- Perfil temporal del jugador durante la partida.
- Sistema de logros: 🏆 Primera victoria, ⚡ Respuesta rápida, 🔥 3 rondas consecutivas, 🎯 Todas las respuestas válidas y 😂 Rey del STOP.
- Estadísticas finales resumidas: rondas, jugadores, palabras válidas, STOP realizados, mejor jugador y mayor puntuación, además de métricas detalladas.
- Sonidos generados con Web Audio API, sin archivos externos ni servicios de pago.
- Animaciones realizadas con CSS/JavaScript, sin librerías de pago ni dependencias externas adicionales.
- Pruebas automatizadas ampliadas para las nuevas funciones.
