// ==================== CONFIGURACIÓN Y ESTADO ====================
const CATEGORIAS = ["nombre", "apellido", "ciudad", "fruta", "animal", "cosa"];
const AVATARES = [
  { id: "oso", emoji: "🐻", nombre: "Oso" },
  { id: "gallina", emoji: "🐔", nombre: "Gallina" },
  { id: "gato", emoji: "🐱", nombre: "Gato" },
  { id: "perro", emoji: "🐶", nombre: "Perro" },
  { id: "mono", emoji: "🐵", nombre: "Mono" },
  { id: "zorro", emoji: "🦊", nombre: "Zorro" },
  { id: "rana", emoji: "🐸", nombre: "Rana" },
  { id: "panda", emoji: "🐼", nombre: "Panda" },
  { id: "koala", emoji: "🐨", nombre: "Koala" },
  { id: "tigre", emoji: "🐯", nombre: "Tigre" },
  { id: "leon", emoji: "🦁", nombre: "León" },
  { id: "conejo", emoji: "🐰", nombre: "Conejo" },
  { id: "cerdo", emoji: "🐷", nombre: "Cerdo" },
  { id: "vaca", emoji: "🐮", nombre: "Vaca" },
  { id: "pinguino", emoji: "🐧", nombre: "Pingüino" },
  { id: "unicornio", emoji: "🦄", nombre: "Unicornio" },
  { id: "robot", emoji: "🤖", nombre: "Robot" },
  { id: "alien", emoji: "👽", nombre: "Alien" },
  { id: "videojuego", emoji: "👾", nombre: "Videojuego" },
  { id: "fantasma", emoji: "👻", nombre: "Fantasma" },
  { id: "calabaza", emoji: "🎃", nombre: "Calabaza" }
];
const REACCIONES = [
  { id: "jaja", texto: "😂 JAJA" },
  { id: "facil", texto: "😎 Fácil" },
  { id: "te_gane", texto: "😏 Te gané" },
  { id: "vamos", texto: "🔥 ¡Vamos!" },
  { id: "bien_jugado", texto: "👏 Bien jugado" },
  { id: "que_paso", texto: "😱 ¿Qué pasó?" },
  { id: "no_puede_ser", texto: "😭 No puede ser" },
  { id: "pensando", texto: "🤔 Estoy pensando" },
  { id: "ganamos", texto: "🥳 ¡Ganamos!" },
  { id: "buena_partida", texto: "❤️ Buena partida" }
];
let categoriasActivas = [...CATEGORIAS];
const ETIQUETAS_CATEGORIA = { nombre: "Nombre", apellido: "Apellido", ciudad: "Ciudad", fruta: "Fruta", animal: "Animal", cosa: "Cosa" };

let socket = null;
let reconectarInterval = null;
let tokenSesion = localStorage.getItem("stop_token") || "";
let nombreGuardado = localStorage.getItem("stop_nombre") || "";
let avatarSeleccionado = localStorage.getItem("stop_avatar") || "oso";
let reconectando = false;
let sesionReemplazada = false;
let miId = null;
let miNombre = "";
let esAnfitrion = false;
let esEspectador = false;
let estadoJuego = "LOGIN"; // LOGIN, SALA, JUEGO, VOTACION, RESULTADOS
let debounceRespuestasTimer = null;
let temporizadorVisual = null;
let tiempoAgotadoNotificado = false;
let temporizadorAnimacionLetra = null;
let animacionLetraId = 0;
let ultimaAnimacionLetra = null;
let sonidoActivado = localStorage.getItem("stop_sonido") !== "0";
let musicaActivada = localStorage.getItem("stop_musica") === "1";
let volumenAudio = Number(localStorage.getItem("stop_volumen_audio") ?? "0.35");
if (!Number.isFinite(volumenAudio)) volumenAudio = 0.35;
volumenAudio = Math.min(1, Math.max(0, volumenAudio));
let audioContext = null;
let gananciaMusica = null;
let osciladoresMusica = [];
let intervaloMusica = null;
let toastTimeout = null;
let rondaConEfectoStop = null;
let rondaConSonidoVotacion = null;
let rondaConSonidoResultados = null;
let ultimaAnimacionPuntaje = null;
let temporizadoresResultado = [];
const eventosConfeti = new Set();

// Elementos DOM principales
const toastEl = document.getElementById("toast");
const bannerReconnect = document.getElementById("banner-reconnect");
const dotConexion = document.getElementById("dot-conexion");
const textoConexion = document.getElementById("texto-conexion");

// ==================== DETECCIÓN DINÁMICA DE WEBSOCKET ====================
function obtenerWebSocketUrl() {
  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocolo}://${window.location.host}/ws`;
}

function inicializarWebSocket() {
  if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) return;
  const wsUrl = obtenerWebSocketUrl();
  console.log("Conectando WebSocket a:", wsUrl);

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket conectado exitosamente.");
    if (dotConexion) {
      dotConexion.className = "dot-online";
      textoConexion.textContent = "Conectado al servidor";
    }

    if (reconectarInterval) {
      clearInterval(reconectarInterval);
      reconectarInterval = null;
    }

    if (tokenSesion && nombreGuardado) {
      const codigoSalaGuardado = localStorage.getItem("stop_codigo_sala") || "7K4P";
      enviarMensaje({ tipo: "estado_reconexion", token: tokenSesion, codigo_sala: codigoSalaGuardado });
      enviarMensaje({
        tipo: "conexion",
        nombre: nombreGuardado,
        token: tokenSesion,
        avatar: avatarSeleccionado,
        accion_sala: "unir",
        codigo_sala: codigoSalaGuardado,
      });
    } else {
      bannerReconnect.classList.add("hidden");
      reconectando = false;
    }
  };

  socket.onmessage = (evento) => {
    try {
      const msg = JSON.parse(evento.data);
      manejarMensajeServidor(msg);
    } catch (e) {
      console.error("Error al procesar mensaje JSON del servidor:", e);
    }
  };

  socket.onclose = (evento) => {
    console.warn("WebSocket desconectado.");
    if (dotConexion) {
      dotConexion.className = "dot-offline";
      textoConexion.textContent = "🔄 Reconectando...";
    }
    reconectando = true;
    bannerReconnect.classList.remove("hidden");

    if (evento.code === 4001) {
      sesionReemplazada = true;
      reconectando = false;
      textoConexion.textContent = "Sesión activa en otra pestaña";
      bannerReconnect.classList.add("hidden");
      return;
    }

    if (!reconectarInterval && !sesionReemplazada) {
      reconectarInterval = setInterval(() => {
        console.log("Reintentando conexión...");
        inicializarWebSocket();
      }, 2500);
    }
  };

  socket.onerror = (err) => {
    console.error("Error en WebSocket:", err);
  };
}

function enviarMensaje(objeto) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(objeto));
  } else {
    mostrarToast("No hay conexión con el servidor.", "error");
  }
}

function limpiarSesionGuardada() {
  tokenSesion = "";
  nombreGuardado = "";
  miId = null;
  miNombre = "";
  esAnfitrion = false;
  esEspectador = false;
  avatarSeleccionado = "oso";
  ["stop_token", "stop_nombre", "stop_codigo_sala", "stop_avatar"].forEach((clave) => {
    localStorage.removeItem(clave);
  });
  const inputNombre = document.getElementById("input-nombre");
  if (inputNombre) inputNombre.value = "";
  const accionSala = document.getElementById("accion-sala");
  if (accionSala) accionSala.value = "crear";
  const inputCodigo = document.getElementById("input-codigo-sala");
  if (inputCodigo) inputCodigo.value = "";
  actualizarCamposCodigoSala();
  renderizarSelectorAvatares();
  cambiarPantalla("LOGIN");
}

// ==================== MANEJO DE MENSAJES DEL SERVIDOR ====================
function manejarMensajeServidor(msg) {
  const tipo = msg.tipo;
  if (Object.prototype.hasOwnProperty.call(msg, "espectador")) {
    esEspectador = !!msg.espectador;
    actualizarInfoUsuario();
  }

  switch (tipo) {
    case "error":
      if (msg.codigo === "sesion_expirada") {
        limpiarSesionGuardada();
        reconectando = false;
        bannerReconnect.classList.add("hidden");
      }
      mostrarToast(msg.mensaje || "Ocurrió un error", "error");
      if (reconectando) {
        reconectando = false;
        bannerReconnect.classList.add("hidden");
        if (textoConexion) textoConexion.textContent = "Conexión disponible; revisa el mensaje";
      }
      break;

    case "notificacion":
      if (["entrada", "salida", "reconexion"].includes(msg.evento)) {
        mostrarNotificacionJugador(msg);
      } else {
        mostrarToast(msg.mensaje || "Actualización de la sala.", msg.estado || "info");
      }
      break;

    case "reaccion":
      mostrarReaccion(msg);
      break;

    case "bienvenida":
      miId = msg.id;
      miNombre = msg.nombre;
      tokenSesion = msg.token || tokenSesion;
      nombreGuardado = miNombre;
      if (msg.codigo_sala) {
        localStorage.setItem("stop_codigo_sala", msg.codigo_sala);
        const codigoSalaEl = document.getElementById("codigo-sala-activo");
        if (codigoSalaEl) codigoSalaEl.textContent = msg.codigo_sala;
      }
      avatarSeleccionado = AVATARES.some((avatar) => avatar.id === msg.avatar) ? msg.avatar : "oso";
      localStorage.setItem("stop_token", tokenSesion);
      localStorage.setItem("stop_nombre", nombreGuardado);
      localStorage.setItem("stop_avatar", avatarSeleccionado);
      esAnfitrion = !!msg.es_anfitrion;
      esEspectador = !!msg.es_espectador;
      actualizarInfoUsuario();
      if (msg.reconectado || reconectando) {
        if (textoConexion) textoConexion.textContent = "✅ Conexión recuperada";
        mostrarToast("✅ Conexión recuperada", "success");
      }
      bannerReconnect.classList.add("hidden");
      reconectando = false;
      break;

    case "sala":
      limpiarPerfilesTemporales();
      eventosConfeti.clear();
      actualizarSala(msg);
      break;

    case "ronda":
      reproducirSonido("ronda");
      iniciarPantallaJuego(msg);
      actualizarJugadoresEnPartida(msg.jugadores || [], msg.espectadores || []);
      renderizarPerfilTemporal(msg);
      break;

    case "jugadores":
      actualizarJugadoresEnPartida(msg.jugadores || [], msg.espectadores || []);
      renderizarPerfilTemporal(msg);
      break;

    case "votacion":
      detenerTemporizadorVisual();
      cancelarAnimacionLetra();
      bloquearCamposRonda();
      if (estadoJuego !== "VOTACION") reproducirSonido("votacion");
      if (msg.motivo_cierre === "stop") mostrarEfectoStop(msg.quien_stop || "Un jugador", msg.stopper_id, msg.ronda);
      else if (!tiempoAgotadoNotificado) reproducirSonido("tiempo");
      mostrarPantallaVotacion(msg);
      break;

    case "resultados":
      detenerTemporizadorVisual();
      cancelarAnimacionLetra();
      bloquearCamposRonda();
      if (estadoJuego !== "RESULTADOS") window.setTimeout(() => reproducirSonido("resultados"), 300);
      if (msg.motivo_cierre === "stop") mostrarEfectoStop(msg.quien_stop || "Un jugador", msg.stopper_id, msg.ronda);
      else if (!tiempoAgotadoNotificado) reproducirSonido("tiempo");
      mostrarPantallaResultados(msg, estadoJuego !== "RESULTADOS");
      break;

    default:
      console.log("Mensaje no reconocido:", msg);
  }
}

// ==================== ANIMACIONES Y SONIDO ====================
function obtenerAudioContext() {
  try {
    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === "suspended") audioContext.resume();
    return audioContext;
  } catch (_) { return null; }
}

function reproducirSonido(tipo) {
  if (!sonidoActivado || volumenAudio === 0) return;
  const ctx = obtenerAudioContext();
  if (!ctx) return;
  const patrones = {
    tic: [[620, 0.04, 0.035]],
    suspenso: [[740, 0.08, 0.045], [620, 0.11, 0.06]],
    ronda: [[440, 0.07, 0.06], [660, 0.08, 0.07], [880, 0.12, 0.08]],
    stop: [[220, 0.08, 0.08], [110, 0.16, 0.12]],
    alerta: [[880, 0.09, 0.07], [660, 0.12, 0.08]],
    impacto: [[90, 0.12, 0.16], [55, 0.2, 0.12]],
    tiempo: [[180, 0.16, 0.1], [120, 0.2, 0.12]],
    votacion: [[523, 0.08, 0.045], [659, 0.11, 0.055]],
    resultados: [[392, 0.1, 0.045], [494, 0.14, 0.05]],
    ganador: [[523, 0.08, 0.07], [659, 0.08, 0.07], [784, 0.16, 0.1], [1047, 0.25, 0.12]],
    derrota: [[294, 0.12, 0.055], [220, 0.16, 0.06], [196, 0.22, 0.05]],
    logro: [[784, 0.07, 0.055], [988, 0.09, 0.06], [1175, 0.16, 0.07]],
    punto: [[740, 0.07, 0.04]]
  };
  if (!patrones[tipo]) return;
  let retraso = 0;
  (patrones[tipo] || []).forEach(([frecuencia, duracion, volumen]) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = ["stop", "impacto"].includes(tipo) ? "sawtooth" : "sine";
    osc.frequency.value = frecuencia;
    const volumenFinal = Math.max(0.0001, volumen * volumenAudio);
    gain.gain.setValueAtTime(0.0001, ctx.currentTime + retraso);
    gain.gain.exponentialRampToValueAtTime(volumenFinal, ctx.currentTime + retraso + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + retraso + duracion);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime + retraso);
    osc.stop(ctx.currentTime + retraso + duracion + 0.02);
    retraso += duracion * 0.85;
  });
}

function alternarSonido() {
  sonidoActivado = !sonidoActivado;
  localStorage.setItem("stop_sonido", sonidoActivado ? "1" : "0");
  const boton = document.getElementById("btn-sonido");
  if (boton) {
    boton.textContent = sonidoActivado ? "🔊 Sonidos activados" : "🔇 Sonidos desactivados";
    boton.setAttribute("aria-pressed", String(sonidoActivado));
  }
  if (sonidoActivado) reproducirSonido("punto");
}

function alternarMusica() {
  musicaActivada = !musicaActivada;
  localStorage.setItem("stop_musica", musicaActivada ? "1" : "0");
  actualizarControlMusica();
  if (musicaActivada) iniciarMusicaConcentracion();
  else detenerMusicaConcentracion();
}

function actualizarControlMusica() {
  const boton = document.getElementById("btn-musica");
  if (!boton) return;
  boton.textContent = musicaActivada ? "🎵 Música activada" : "🎵 Música desactivada";
  boton.setAttribute("aria-pressed", String(musicaActivada));
}

function actualizarVolumenAudio(valor) {
  volumenAudio = Math.min(1, Math.max(0, Number(valor) / 100));
  localStorage.setItem("stop_volumen_audio", String(volumenAudio));
  if (gananciaMusica && audioContext) {
    gananciaMusica.gain.setTargetAtTime(volumenAudio * 0.12, audioContext.currentTime, 0.12);
  }
}

function iniciarMusicaConcentracion() {
  if (!musicaActivada || osciladoresMusica.length) return;
  if (!window.AudioContext && !window.webkitAudioContext) {
    musicaActivada = false;
    localStorage.setItem("stop_musica", "0");
    actualizarControlMusica();
    mostrarToast("Este navegador no admite música Web Audio.", "error");
    return;
  }
  const ctx = obtenerAudioContext();
  if (!ctx) {
    musicaActivada = false;
    localStorage.setItem("stop_musica", "0");
    actualizarControlMusica();
    mostrarToast("No se pudo activar la música.", "error");
    return;
  }

  gananciaMusica = ctx.createGain();
  gananciaMusica.gain.setValueAtTime(0, ctx.currentTime);
  gananciaMusica.gain.setTargetAtTime(volumenAudio * 0.12, ctx.currentTime, 0.8);
  gananciaMusica.connect(ctx.destination);
  osciladoresMusica = [0, 1, 2].map(() => {
    const oscilador = ctx.createOscillator();
    const ganancia = ctx.createGain();
    oscilador.type = "sine";
    ganancia.gain.value = 0.035;
    oscilador.connect(ganancia).connect(gananciaMusica);
    oscilador.start();
    return oscilador;
  });

  const acordes = [
    [130.81, 164.81, 196],
    [110, 130.81, 164.81],
    [98, 123.47, 146.83],
    [123.47, 146.83, 185]
  ];
  let indiceAcorde = 0;
  const aplicarAcorde = () => {
    acordes[indiceAcorde].forEach((frecuencia, indice) => {
      osciladoresMusica[indice].frequency.setTargetAtTime(frecuencia, ctx.currentTime, 1.5);
    });
    indiceAcorde = (indiceAcorde + 1) % acordes.length;
  };
  aplicarAcorde();
  intervaloMusica = window.setInterval(aplicarAcorde, 6000);
}

function detenerMusicaConcentracion() {
  if (intervaloMusica) window.clearInterval(intervaloMusica);
  intervaloMusica = null;
  osciladoresMusica.forEach((oscilador) => {
    oscilador.stop();
    oscilador.disconnect();
  });
  osciladoresMusica = [];
  if (gananciaMusica) gananciaMusica.disconnect();
  gananciaMusica = null;
}

function mostrarEfectoJuego(emoji, titulo, subtitulo, clase = "") {
  const overlay = document.getElementById("efecto-juego");
  const emojiEl = document.getElementById("efecto-emoji");
  const tituloEl = document.getElementById("efecto-titulo");
  const subtituloEl = document.getElementById("efecto-subtitulo");
  if (!overlay) return;
  overlay.className = `efecto-juego ${clase}`.trim();
  emojiEl.textContent = emoji;
  tituloEl.textContent = titulo;
  subtituloEl.textContent = subtitulo || "";
  void overlay.offsetWidth;
  overlay.classList.add("visible");
  clearTimeout(overlay._timer);
  overlay._timer = setTimeout(() => overlay.classList.remove("visible"), clase.includes("stop") ? 1500 : 1800);
}

function mostrarEfectoStop(nombre, jugadorId, ronda) {
  const claveRonda = `${ronda}:${nombre}`;
  if (rondaConEfectoStop === claveRonda) return;
  rondaConEfectoStop = claveRonda;
  reproducirSonido("alerta");
  window.setTimeout(() => reproducirSonido("impacto"), 100);
  const avatar = document.querySelector(`.avatar-animado[data-player-id="${Number(jugadorId)}"]`);
  if (avatar) {
    avatar.classList.remove("avatar-stop-salto");
    void avatar.offsetWidth;
    avatar.classList.add("avatar-stop-salto");
    window.setTimeout(() => avatar.classList.remove("avatar-stop-salto"), 900);
  }
  mostrarEfectoJuego("💥", "💥 STOP 💥", `😂 ¡${nombre.toLocaleUpperCase("es-CO")} DIJO STOP!`, "efecto-stop");
}

function mostrarEfectoRonda(msg) {
  rondaConEfectoStop = null;
  const letra = msg.letra || "?";
  mostrarEfectoJuego("✋", `¡LETRA ${letra}!`, "Prepárate... comienza la ronda", "efecto-ronda");
}

function lanzarConfeti(claveEvento = "celebracion") {
  if (eventosConfeti.has(claveEvento)) return;
  eventosConfeti.add(claveEvento);
  const contenedor = document.createElement("div");
  contenedor.className = "confeti-contenedor";
  for (let i = 0; i < 42; i += 1) {
    const pieza = document.createElement("span");
    pieza.textContent = ["🎉", "✨", "⭐", "🏆"][i % 4];
    pieza.style.setProperty("--x", `${Math.round(Math.random() * 100)}vw`);
    pieza.style.setProperty("--delay", `${(Math.random() * 0.45).toFixed(2)}s`);
    pieza.style.setProperty("--duracion", `${(1.5 + Math.random() * 1.8).toFixed(2)}s`);
    contenedor.appendChild(pieza);
  }
  document.body.appendChild(contenedor);
  setTimeout(() => contenedor.remove(), 3600);
}

function animarPuntos() {
  document.querySelectorAll(".pts-ronda-badge[data-player-id]").forEach((el, indice) => {
    setTimeout(() => {
      const puntos = Number(el.dataset.puntos);
      if (!Number.isFinite(puntos) || puntos <= 0) return;
      el.classList.add("puntos-entra");
      const jugadorId = Number(el.dataset.playerId);
      const destino = Number.isInteger(jugadorId)
        ? document.querySelector(`.item-clasificacion[data-player-id="${jugadorId}"] .pts-total-badge`)
        : null;
      if (puntos > 0 && destino) animarPuntosAlMarcador(el, destino, puntos);
      reproducirSonido("punto");
    }, indice * 100);
  });
}

function animarPuntosAlMarcador(origen, destino, puntos) {
  const inicio = origen.getBoundingClientRect();
  const final = destino.getBoundingClientRect();
  if (!inicio.width || !final.width) return;

  const vuelo = document.createElement("span");
  vuelo.className = "puntos-volando";
  vuelo.textContent = `⬆️ +${puntos}`;
  vuelo.setAttribute("aria-hidden", "true");
  vuelo.style.left = `${inicio.left + inicio.width / 2}px`;
  vuelo.style.top = `${inicio.top + inicio.height / 2}px`;
  document.body.appendChild(vuelo);

  window.requestAnimationFrame(() => {
    vuelo.style.transform = `translate(${final.left + final.width / 2 - inicio.left - inicio.width / 2}px, ${final.top + final.height / 2 - inicio.top - inicio.height / 2}px) scale(.55)`;
    vuelo.style.opacity = "0";
    destino.classList.add("puntos-recibe");
  });
  window.setTimeout(() => {
    vuelo.remove();
    destino.classList.remove("puntos-recibe");
  }, 780);
}

// ==================== TRANSICIÓN DE PANTALLAS ====================
function cambiarPantalla(nuevaPantalla) {
  estadoJuego = nuevaPantalla;
  const pantallas = ["LOGIN", "SALA", "JUEGO", "VOTACION", "RESULTADOS"];

  pantallas.forEach((p) => {
    const el = document.getElementById(`pantalla-${p.toLowerCase()}`);
    if (el) {
      if (p === nuevaPantalla) {
        el.classList.add("activa");
      } else {
        el.classList.remove("activa");
      }
    }
  });

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ==================== ACCIONES DEL USUARIO ====================
function entrarAlJuego() {
  const input = document.getElementById("input-nombre");
  const nombre = input.value.trim();
  const accionSala = document.getElementById("accion-sala")?.value || "crear";
  const codigoSala = document.getElementById("input-codigo-sala")?.value.trim().toUpperCase() || "";

  if (!nombre) {
    mostrarToast("El nombre es obligatorio.", "error");
    return;
  }

  if (accionSala === "unir" && !/^[A-HJ-NP-Z2-9]{4}$/.test(codigoSala)) {
    mostrarToast("Ingresa un código de sala válido de 4 caracteres.", "error");
    return;
  }

  const tokenParaSala = accionSala === "unir"
    && codigoSala === localStorage.getItem("stop_codigo_sala")
    ? tokenSesion
    : "";
  enviarMensaje({
    tipo: "conexion",
    nombre,
    avatar: avatarSeleccionado,
    accion_sala: accionSala,
    codigo_sala: accionSala === "unir" ? codigoSala : "",
    ...(tokenParaSala ? { token: tokenParaSala } : {}),
  });
}

function actualizarCamposCodigoSala() {
  const selector = document.getElementById("accion-sala");
  const campo = document.getElementById("campo-codigo-sala");
  const codigo = document.getElementById("input-codigo-sala");
  const unirse = selector?.value === "unir";
  campo?.classList.toggle("hidden", !unirse);
  if (codigo) codigo.required = !!unirse;
}

function alternarCamposCodigoSala() {
  const selector = document.getElementById("accion-sala");
  selector?.addEventListener("change", actualizarCamposCodigoSala);
  actualizarCamposCodigoSala();
}

function seleccionarAvatar(avatarId) {
  if (!AVATARES.some((avatar) => avatar.id === avatarId)) return;
  avatarSeleccionado = avatarId;
  localStorage.setItem("stop_avatar", avatarId);
  document.querySelectorAll(".opcion-avatar").forEach((boton) => {
    boton.setAttribute("aria-pressed", String(boton.dataset.avatar === avatarSeleccionado));
  });
  actualizarInfoUsuario();
}

function renderizarAvatar(emoji, clase = "avatar-jugador", jugadorId = null) {
  const avatar = AVATARES.find((opcion) => opcion.emoji === emoji) || AVATARES[0];
  const atributoJugador = Number.isInteger(jugadorId) ? ` data-player-id="${jugadorId}"` : "";
  return `<span class="${clase} avatar-animado" data-avatar="${avatar.id}"${atributoJugador} aria-hidden="true">${avatar.emoji}</span>`;
}

function renderizarEmocion(emocion) {
  const emocionesPermitidas = new Set(["😎", "🤔", "😱", "🥳", "😭", "🔥", "🏆", "😴", "🔄", "👀"]);
  if (!emocionesPermitidas.has(emocion)) return "";
  return `<span class="emocion-automatica" aria-label="Emoción ${emocion}">${emocion}</span>`;
}

function renderizarSelectorAvatares() {
  const contenedor = document.getElementById("opciones-avatares");
  if (!contenedor) return;
  if (!AVATARES.some((avatar) => avatar.id === avatarSeleccionado)) avatarSeleccionado = "oso";
  contenedor.replaceChildren();
  AVATARES.forEach((avatar) => {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "opcion-avatar";
    boton.dataset.avatar = avatar.id;
    boton.textContent = avatar.emoji;
    boton.title = avatar.nombre;
    boton.setAttribute("aria-label", avatar.nombre);
    boton.setAttribute("aria-pressed", String(avatar.id === avatarSeleccionado));
    boton.addEventListener("click", () => seleccionarAvatar(avatar.id));
    contenedor.appendChild(boton);
  });
}

function renderizarReacciones() {
  const contenedor = document.getElementById("botones-reacciones");
  if (!contenedor) return;
  contenedor.replaceChildren();
  REACCIONES.forEach((reaccion) => {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "boton-reaccion";
    boton.dataset.reaccion = reaccion.id;
    boton.textContent = reaccion.texto;
    boton.addEventListener("click", () => enviarReaccion(reaccion.id));
    contenedor.appendChild(boton);
  });
}

function enviarReaccion(reaccion) {
  if (!REACCIONES.some((opcion) => opcion.id === reaccion)) return;
  enviarMensaje({ tipo: "reaccion", reaccion });
}

function mostrarReaccion(mensaje) {
  const contenedor = document.getElementById("reacciones-flotantes");
  if (!contenedor || !REACCIONES.some((opcion) => opcion.id === mensaje.reaccion)) return;
  const reaccion = REACCIONES.find((opcion) => opcion.id === mensaje.reaccion);
  const burbuja = document.createElement("div");
  burbuja.className = "reaccion-flotante";
  burbuja.textContent = `${mensaje.avatar || "🐻"} ${mensaje.nombre || "Jugador"}: ${reaccion.texto}`;
  contenedor.appendChild(burbuja);
  while (contenedor.children.length > 5) contenedor.firstElementChild.remove();
  window.setTimeout(() => {
    burbuja.classList.add("saliendo");
    window.setTimeout(() => burbuja.remove(), 220);
  }, 3000);
}

function iniciarRonda() {
  if (esEspectador) {
    mostrarToast("Los espectadores no pueden iniciar una ronda.", "error");
    return;
  }
  if (!esAnfitrion) {
    mostrarToast("Debes esperar al anfitrión.", "error");
    return;
  }
  enviarMensaje({ tipo: "iniciar_ronda" });
}

function accionResultados() {
  if (document.getElementById("btn-nueva-ronda")?.dataset.nuevaPartida === "true") {
    enviarMensaje({ tipo: "nueva_partida" });
  } else {
    iniciarRonda();
  }
}

function recolectarRespuestas() {
  const respuestas = {};
  categoriasActivas.forEach((cat) => {
    const input = document.getElementById(`cat-${cat}`);
    respuestas[cat] = input ? input.value.trim() : "";
  });
  return respuestas;
}

function enviarRespuestasTiempoReal() {
  clearTimeout(debounceRespuestasTimer);
  debounceRespuestasTimer = setTimeout(() => {
    if (estadoJuego === "JUEGO") {
      const resp = recolectarRespuestas();
      enviarMensaje({
        tipo: "respuestas",
        respuestas: resp
      });
    }
  }, 350);
}

function enviarStop() {
  if (estadoJuego !== "JUEGO") return;
  document.getElementById("confirm-stop-modal").classList.remove("hidden");
}

function cancelarStop() {
  document.getElementById("confirm-stop-modal").classList.add("hidden");
}

function confirmarStop() {
  cancelarStop();
  const resp = recolectarRespuestas();
  enviarMensaje({
    tipo: "stop",
    respuestas: resp
  });
}

// ==================== ACTUALIZACIONES DE UI ====================
function actualizarInfoUsuario() {
  const labelNombre = document.getElementById("label-mi-nombre");
  const labelRol = document.getElementById("label-mi-rol");
  const avatar = document.getElementById("avatar-mi-usuario");

  if (labelNombre) labelNombre.textContent = miNombre;
  if (labelRol) labelRol.textContent = esEspectador ? "👀 ESPECTADOR" : esAnfitrion ? "👑 Anfitrión" : "Jugador";
  if (avatar) {
    const seleccionado = AVATARES.find((opcion) => opcion.id === avatarSeleccionado);
    avatar.textContent = seleccionado ? seleccionado.emoji : "🐻";
    avatar.setAttribute("aria-label", seleccionado ? seleccionado.nombre : "Oso");
    avatar.dataset.avatar = seleccionado ? seleccionado.id : "oso";
    avatar.classList.add("avatar-animado");
  }
  const badgeEspectador = document.getElementById("badge-espectador");
  if (badgeEspectador) badgeEspectador.classList.toggle("hidden", !esEspectador);
}

function actualizarSala(msg) {
  const jugadores = msg.jugadores || [];
  const anfitrionId = msg.anfitrion_id;

  // Actualizar mi estado de anfitrión por si hubo traspaso
  const miJugador = jugadores.find((j) => j.id === miId);
  if (miJugador) {
    esAnfitrion = !!miJugador.es_anfitrion;
    actualizarInfoUsuario();
  }
  aplicarConfiguracionSala(msg.configuracion || { rondas: 4, categorias: CATEGORIAS, min_categorias: 3 }, msg.estado);

  // Contador
  const contador = document.getElementById("contador-jugadores");
  if (contador) contador.textContent = jugadores.length;

  // Lista en Sala
  const listaSala = document.getElementById("lista-jugadores-sala");
  if (listaSala) {
    listaSala.innerHTML = "";
    jugadores.forEach((j) => {
      const li = document.createElement("li");
      li.className = `item-jugador ${j.id === miId ? "es-yo" : ""}`;
      li.innerHTML = `
        <div class="jugador-info-izq">
          <span class="${j.conectado === false ? "dot-desconectado" : "dot-verde"}">●</span>
          ${renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id)}
          ${renderizarEmocion(j.emocion)}
          <span>${escaparHtml(j.nombre)} ${j.id === miId ? "(TÚ)" : ""} · ${escaparHtml(j.estado_presencia || (j.conectado === false ? "🔴 Desconectado" : "🟢 Conectado"))}</span>
          ${j.es_anfitrion ? '<span class="badge-host">👑 Anfitrión</span>' : ""}
        </div>
        <div class="pts-total-badge">${j.total || 0} pts</div>
      `;
      listaSala.appendChild(li);
    });
  }

  // Nombre anfitrión
  const hostObj = jugadores.find((j) => j.id === anfitrionId);
  const nombreHostEl = document.getElementById("nombre-anfitrion");
  if (nombreHostEl) {
    nombreHostEl.textContent = hostObj ? hostObj.nombre : "Esperando...";
  }

  // Botón iniciar vs aviso
  const btnIniciar = document.getElementById("btn-iniciar-ronda");
  const msgEspera = document.getElementById("msg-espera-host");
  if (btnIniciar && msgEspera) {
    if (esAnfitrion) {
      btnIniciar.style.display = "block";
      msgEspera.classList.add("hidden");
    } else {
      btnIniciar.style.display = "none";
      msgEspera.classList.remove("hidden");
    }
  }

  // Si estábamos en resultados y el servidor pasó a SALA
  if (msg.estado === "SALA") {
    cambiarPantalla("SALA");
  }
}

function aplicarConfiguracionSala(config, estado) {
  const selector = document.getElementById("config-rondas");
  const checks = [...document.querySelectorAll("#config-categorias input[type=checkbox]")];
  if (!selector || !checks.length) return;
  categoriasActivas = config.categorias || [...CATEGORIAS];
  selector.value = String(config.rondas || 4);
  const editable = esAnfitrion && estado === "SALA";
  selector.disabled = !editable;
  checks.forEach((check) => {
    check.checked = categoriasActivas.includes(check.value);
    check.disabled = !editable;
  });
  const boton = document.getElementById("btn-guardar-configuracion");
  if (boton) boton.disabled = !editable;
  const resumen = document.getElementById("resumen-configuracion");
  if (resumen) resumen.textContent = `${config.rondas || 4} rondas · ${categoriasActivas.map((c) => c[0].toUpperCase() + c.slice(1)).join(", ")}`;
  actualizarVisibilidadCategorias();
}

function guardarConfiguracion() {
  const rondas = Number(document.getElementById("config-rondas")?.value);
  const categorias = [...document.querySelectorAll("#config-categorias input:checked")].map((check) => check.value);
  const error = document.getElementById("error-config-rondas");
  error.classList.add("hidden");
  if (!Number.isInteger(rondas) || rondas < 4 || rondas > 10) {
    error.textContent = "La cantidad de rondas debe estar entre 4 y 10.";
    error.classList.remove("hidden");
    return;
  }
  if (categorias.length < 3) {
    error.textContent = "Activa al menos 3 categorías para iniciar.";
    error.classList.remove("hidden");
    return;
  }
  enviarMensaje({ tipo: "configuracion", rondas, categorias });
}

function actualizarVisibilidadCategorias() {
  CATEGORIAS.forEach((categoria) => {
    const campo = document.getElementById(`cat-${categoria}`)?.closest(".campo-categoria");
    if (campo) campo.classList.toggle("hidden", !categoriasActivas.includes(categoria));
    document.querySelectorAll(`[data-cat="${categoria}"]`).forEach((celda) => {
      celda.style.display = categoriasActivas.includes(categoria) ? "" : "none";
    });
  });
}

function actualizarJugadoresEnPartida(jugadores, espectadores = []) {
  const lista = document.getElementById("lista-jugadores-juego");
  if (!lista) return;

  lista.innerHTML = "";
  jugadores.forEach((j) => {
    const li = document.createElement("li");
    li.className = "item-jugador-simple";
    const etiquetaYo = j.id === miId ? " (TÚ)" : "";
    const host = j.es_anfitrion ? " 👑" : "";
    const estado = j.estado_presencia || j.estado || `${j.total || 0} pts`;
    const desconectado = j.conectado === false;
    li.innerHTML = `
      <span>${renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id)}${renderizarEmocion(j.emocion)}${escaparHtml(j.nombre)}${etiquetaYo}${host}${desconectado ? " · Desconectado" : ""}</span>
      <strong class="${desconectado ? "texto-muted" : "puntos-verde"}">${escaparHtml(estado)}</strong>
    `;
    lista.appendChild(li);
  });
  espectadores.forEach((e) => {
    const li = document.createElement("li");
    li.className = "item-jugador-simple";
    li.innerHTML = `<span>👀 ${renderizarAvatar(e.avatar || "🐻", "avatar-jugador", e.id)}${renderizarEmocion(e.emocion)}${escaparHtml(e.nombre)}</span><strong class="texto-muted">${escaparHtml(e.estado_presencia || "👀 Espectador")}</strong>`;
    lista.appendChild(li);
  });
}

function iniciarPantallaJuego(msg) {
  const yaEstabaEnJuego = estadoJuego === "JUEGO";
  if (msg.categorias) categoriasActivas = msg.categorias;
  actualizarVisibilidadCategorias();
  const letra = msg.letra || "?";
  const numRonda = msg.ronda || 1;

  document.getElementById("letra-ronda").textContent = "?";
  document.getElementById("badge-ronda-actual").textContent = `Ronda ${numRonda}`;
  if (msg.anfitrion_id !== undefined) esAnfitrion = msg.anfitrion_id === miId;
  if (msg.espectador !== undefined) esEspectador = !!msg.espectador;
  actualizarInfoUsuario();
  iniciarTemporizadorVisual(msg.vence_en, msg.servidor_ahora);
  bloquearCamposRonda(esEspectador);

  // Limpiar campos de texto
  CATEGORIAS.forEach((cat) => {
    const input = document.getElementById(`cat-${cat}`);
    if (input) {
      input.value = "";
    }
  });

  if (!esEspectador && msg.mis_respuestas) {
    CATEGORIAS.forEach((cat) => {
      const input = document.getElementById(`cat-${cat}`);
      if (input) input.value = msg.mis_respuestas[cat] || "";
    });
  }

  cambiarPantalla("JUEGO");

  // Poner foco en el primer input
  const primerInput = document.getElementById("cat-nombre");
  if (primerInput) {
    if (!esEspectador) setTimeout(() => primerInput.focus(), 150);
  }
  const claveAnimacion = `${numRonda}:${letra}`;
  if (!yaEstabaEnJuego || ultimaAnimacionLetra !== claveAnimacion) {
    ultimaAnimacionLetra = claveAnimacion;
    animarLetraRonda(letra, numRonda, () => mostrarEfectoRonda(msg));
  }
}

function cancelarAnimacionLetra() {
  animacionLetraId += 1;
  if (temporizadorAnimacionLetra) clearTimeout(temporizadorAnimacionLetra);
  temporizadorAnimacionLetra = null;
  document.getElementById("letra-ronda")?.classList.remove("letra-animando");
}

function animarLetraRonda(letra, ronda, alFinalizar) {
  cancelarAnimacionLetra();
  const idAnimacion = animacionLetraId;
  const etiqueta = document.getElementById("letra-ronda");
  const letraFinal = String(letra || "?").toLocaleUpperCase("es-CO");
  const alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const secuencia = Array.from({ length: 4 }, () => alfabeto[Math.floor(Math.random() * alfabeto.length)]);
  secuencia.push(letraFinal);
  let indice = 0;

  const avanzar = () => {
    if (idAnimacion !== animacionLetraId) return;
    if (etiqueta) {
      etiqueta.textContent = secuencia[indice];
      if (indice === secuencia.length - 1) etiqueta.setAttribute("aria-label", `Letra ${letraFinal} de la ronda ${ronda}`);
      etiqueta.classList.remove("letra-animando");
      void etiqueta.offsetWidth;
      etiqueta.classList.add("letra-animando");
    }
    indice += 1;
    if (indice < secuencia.length) {
      temporizadorAnimacionLetra = setTimeout(avanzar, 65);
      return;
    }
    temporizadorAnimacionLetra = null;
    setTimeout(() => etiqueta?.classList.remove("letra-animando"), 160);
    if (idAnimacion === animacionLetraId) alFinalizar();
  };

  temporizadorAnimacionLetra = setTimeout(avanzar, 45);
}

function iniciarTemporizadorVisual(venceEn, servidorAhora) {
  detenerTemporizadorVisual();
  tiempoAgotadoNotificado = false;
  const etiqueta = document.getElementById("temporizador-ronda");
  const aviso = document.getElementById("aviso-temporizador");
  const cuentaRegresiva = document.getElementById("cuenta-regresiva");
  const diferenciaReloj = Number(servidorAhora) * 1000 - Date.now();
  let ultimoSegundo = null;
  const actualizar = () => {
    const segundos = Math.max(0, Math.ceil((Number(venceEn) * 1000 - (Date.now() + diferenciaReloj)) / 1000));
    if (etiqueta) {
      etiqueta.textContent = `${String(Math.floor(segundos / 60)).padStart(2, "0")}:${String(segundos % 60).padStart(2, "0")}`;
      etiqueta.classList.toggle("tiempo-agotado", segundos === 0);
      etiqueta.classList.toggle("tiempo-critico", segundos <= 10 && segundos > 0);
    }
    if (aviso) {
      aviso.textContent = segundos <= 10 && segundos > 0 ? "⚠️" : "";
      aviso.classList.toggle("hidden", segundos > 10 || segundos === 0);
    }
    if (cuentaRegresiva) {
      cuentaRegresiva.textContent = segundos <= 5 && segundos > 0 ? String(segundos) : "";
      cuentaRegresiva.classList.toggle("hidden", segundos > 5 || segundos === 0);
    }
    if (segundos !== ultimoSegundo && segundos <= 5 && segundos > 0) reproducirSonido("suspenso");
    if (segundos === 0 && !tiempoAgotadoNotificado) {
      tiempoAgotadoNotificado = true;
      if (aviso) aviso.classList.add("hidden");
      if (cuentaRegresiva) cuentaRegresiva.classList.add("hidden");
      reproducirSonido("tiempo");
      mostrarEfectoJuego("💥", "💥 ¡TIEMPO!", "", "efecto-tiempo");
    }
    ultimoSegundo = segundos;
  };
  actualizar();
  temporizadorVisual = setInterval(actualizar, 250);
}

function detenerTemporizadorVisual() {
  if (temporizadorVisual) clearInterval(temporizadorVisual);
  temporizadorVisual = null;
}

function bloquearCamposRonda(bloquear = true) {
  CATEGORIAS.forEach((cat) => {
    const input = document.getElementById(`cat-${cat}`);
    if (input) input.disabled = bloquear;
  });
  const boton = document.getElementById("btn-stop");
  if (boton) boton.disabled = bloquear;
}

function etiquetaResultadoRespuesta(detalle, puntos) {
  if (["valida_repetida", "votada_repetida"].includes(detalle.estado)) {
    return `⚠️ Repetida +${puntos}`;
  }
  if (puntos > 0) return `✅ Correcta +${puntos}`;
  return "❌ No válida +0";
}

function mostrarPantallaVotacion(msg) {
  const contenedor = document.getElementById("contenedor-votaciones");
  const badge = document.getElementById("badge-ronda-votacion");
  const banner = document.getElementById("banner-stop-votacion");
  if (!contenedor) return;

  if (badge) badge.textContent = `Ronda ${msg.ronda || 1} (Letra: ${msg.letra || ""})`;
  if (banner) banner.textContent = msg.motivo_cierre === "tiempo"
    ? "⏰ ¡TIEMPO TERMINADO!"
    : `🛑 ${msg.quien_stop || "Un jugador"} HA HECHO STOP`;
  actualizarJugadoresEnVotacion(msg.jugadores || [], msg.espectadores || []);

  contenedor.innerHTML = "";
  const candidatos = msg.candidatos || [];

  if (candidatos.length === 0) {
    contenedor.innerHTML = '<p class="texto-muted">No hay respuestas pendientes de votación.</p>';
    cambiarPantalla("VOTACION");
    return;
  }

  candidatos.forEach((candidato) => {
    const card = document.createElement("div");
    card.className = "card tarjeta-votacion";
    const autores = (candidato.autores || []).map(escaparHtml).join(", ");
    const puedeVotar = !!candidato.puede_votar;
    const total = candidato.total_votantes || 0;
    const votos = `SÍ: ${candidato.votos_si || 0} · NO: ${candidato.votos_no || 0} · ${total} votantes`;

    card.innerHTML = `
      <div class="votacion-cabecera">
        <div>
          <span class="badge-categoria-votacion">${ETIQUETAS_CATEGORIA[candidato.categoria] || candidato.categoria}</span>
          <h2>"${escaparHtml(candidato.respuesta)}"</h2>
          <p class="texto-muted">¿Aceptar esta respuesta? · De: ${autores}</p>
        </div>
        <div class="contador-votos">🗳️ ${votos}</div>
      </div>
      <div class="votacion-acciones">
        ${candidato.cerrada
          ? `<div class="aviso-no-vota">${candidato.aprobada ? "✅ Aprobada por votación" : "❌ Rechazada por votación"}</div>`
          : candidato.ya_voto
          ? `<div class="aviso-no-vota">Tu voto: ${candidato.mi_voto ? "SÍ" : "NO"}. Espera a los demás jugadores.</div>`
          : puedeVotar
          ? `<button class="btn btn-voto btn-voto-si" data-voto="si">👍 SÍ, ES VÁLIDA</button>
             <button class="btn btn-voto btn-voto-no" data-voto="no">👎 NO, NO ES VÁLIDA</button>`
          : esEspectador
          ? '<div class="aviso-no-vota">👀 ESPECTADOR: puedes ver la votación, pero no participar.</div>'
          : '<div class="aviso-no-vota">👀 Esta respuesta es tuya. Espera la decisión de los demás jugadores.</div>'}
      </div>
    `;
    contenedor.appendChild(card);
    if (puedeVotar) {
      card.querySelectorAll("button[data-voto]").forEach((boton) => {
        boton.addEventListener("click", () => votarRespuesta(candidato.clave, boton.dataset.voto === "si", card));
      });
    }
  });

  cambiarPantalla("VOTACION");
}

function actualizarJugadoresEnVotacion(jugadores, espectadores) {
  const lista = document.getElementById("lista-jugadores-votacion");
  if (!lista) return;
  lista.innerHTML = "";
  jugadores.forEach((j) => {
    const li = document.createElement("li");
    li.className = "item-jugador-simple";
    const host = j.es_anfitrion ? " 👑" : "";
    const disconnected = j.conectado === false;
    const presencia = j.estado_presencia || (disconnected ? "🔴 Desconectado" : "🟢 Conectado");
    const estado = disconnected ? presencia : `${presencia} · ${j.estado || "En votación"}`;
    li.innerHTML = `<span>${renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id)}${renderizarEmocion(j.emocion)}${escaparHtml(j.nombre)}${host}${j.id === miId ? " (TÚ)" : ""}</span><strong class="${disconnected ? "texto-muted" : "puntos-verde"}">${escaparHtml(estado)}</strong>`;
    lista.appendChild(li);
  });
  espectadores.forEach((e) => {
    const li = document.createElement("li");
    li.className = "item-jugador-simple";
    li.innerHTML = `<span>👀 ${renderizarAvatar(e.avatar || "🐻", "avatar-jugador", e.id)}${renderizarEmocion(e.emocion)}${escaparHtml(e.nombre)}${e.id === miId ? " (TÚ)" : ""}</span><strong class="texto-muted">${escaparHtml(e.estado_presencia || "👀 Espectador")}</strong>`;
    lista.appendChild(li);
  });
}

function votarRespuesta(clave, voto, card) {
  if (card) card.querySelectorAll("button[data-voto]").forEach((b) => b.disabled = true);
  enviarMensaje({ tipo: "voto", clave, voto });
}

function animarResultadosProgresivamente(animar) {
  temporizadoresResultado.forEach((temporizador) => clearTimeout(temporizador));
  temporizadoresResultado = [];
  document.querySelectorAll(".resultado-progresivo").forEach((etiqueta, indice) => {
    const puntos = Number(etiqueta.dataset.puntos);
    const textoFinal = etiquetaResultadoRespuesta({ estado: etiqueta.dataset.estado }, puntos);
    if (!animar) {
      etiqueta.textContent = textoFinal;
      return;
    }

    etiqueta.textContent = "⏳ Calculando...";
    const retraso = indice * 20;
    temporizadoresResultado.push(setTimeout(() => {
      etiqueta.textContent = puntos > 0 ? "✅ Respuesta aceptada" : "❌ Respuesta no válida";
      etiqueta.classList.add("resultado-actualizando");
    }, 260 + retraso));
    temporizadoresResultado.push(setTimeout(() => {
      etiqueta.textContent = textoFinal;
      etiqueta.classList.remove("resultado-actualizando");
    }, 520 + retraso));
  });
}

function mostrarPantallaResultados(msg, animar = true) {
  if (msg.categorias) categoriasActivas = msg.categorias;
  actualizarVisibilidadCategorias();
  const letra = msg.letra || "";
  const numRonda = msg.ronda || 1;
  const quienStop = msg.quien_stop || "Un jugador";
  const jugadores = msg.jugadores || [];
  const historialGlobal = msg.historial_global || [];

  // Actualizar rol anfitrión
  const miJugador = jugadores.find((j) => j.id === miId);
  if (miJugador) {
    esAnfitrion = !!miJugador.es_anfitrion;
    document.getElementById("label-mi-total-resultados").textContent = `${miJugador.total} pts`;
    document.getElementById("total-jugador-juego").textContent = `${miJugador.total} pts`;
  }

  // Banner STOP
  const bannerStop = document.getElementById("banner-quien-stop");
  if (bannerStop) {
    bannerStop.textContent = msg.motivo_cierre === "tiempo"
      ? "⏰ ¡TIEMPO TERMINADO!"
      : `🛑 ${quienStop} HA HECHO STOP`;
  }

  document.getElementById("badge-ronda-resultados").textContent = `Ronda ${numRonda} (Letra: ${letra})`;

  // Renderizar tabla
  const tbody = document.getElementById("tbody-resultados");
  if (tbody) {
    tbody.innerHTML = "";
    jugadores.forEach((j) => {
      const tr = document.createElement("tr");
      if (j.id === miId) tr.className = "fila-yo";

      const r = j.respuestas || {};
      const detalle = j.detalle_respuestas || {};
      const celdaRespuesta = (cat) => {
        const d = detalle[cat] || {};
        const respuesta = d.respuesta || r[cat] || "-";
        const puntos = Number(d.puntos || 0);
        let clase = "detalle-puntos detalle-cero";
        if (puntos === 10) clase = "detalle-puntos detalle-diez";
        else if (puntos === 5) clase = "detalle-puntos detalle-cinco";
        const etiqueta = etiquetaResultadoRespuesta(d, puntos);
        return `<div>${escaparHtml(respuesta)}</div><small class="${clase} resultado-progresivo" data-estado="${escaparHtml(d.estado || "")}" data-puntos="${puntos}">${etiqueta}</small>`;
      };

      tr.innerHTML = `
        <td><strong>${renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id)}${renderizarEmocion(j.emocion)}${escaparHtml(j.nombre)} ${j.id === miId ? "(TÚ)" : ""}</strong><small class="texto-muted">${escaparHtml(j.estado_presencia || (j.conectado === false ? "🔴 Desconectado" : "🟢 Conectado"))}</small></td>
        <td data-cat="nombre">${celdaRespuesta("nombre")}</td>
        <td data-cat="apellido">${celdaRespuesta("apellido")}</td>
        <td data-cat="ciudad">${celdaRespuesta("ciudad")}</td>
        <td data-cat="fruta">${celdaRespuesta("fruta")}</td>
        <td data-cat="animal">${celdaRespuesta("animal")}</td>
        <td data-cat="cosa">${celdaRespuesta("cosa")}</td>
        <td>
          <span class="pts-ronda-badge" data-player-id="${Number(j.id)}" data-puntos="${Number(j.puntos_ronda) || 0}">+${j.puntos_ronda || 0}</span>
          <small class="${j.bonus_ronda ? "bonus-ronda-label" : ""}">${j.puntos_categorias ?? j.puntos_ronda ?? 0} puntos de categorías${j.bonus_ronda ? ` · 🔥 RONDA PERFECTA · +${j.bonus_ronda} BONUS` : ""}</small>
        </td>
        <td><span class="pts-total-badge">${j.total || 0}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Renderizar clasificación acumulada
  const contClasificacion = document.getElementById("contenedor-clasificacion");
  if (contClasificacion) {
    contClasificacion.innerHTML = "";
    const ranking = msg.clasificacion?.map((puesto) => jugadores.find((j) => j.id === puesto.id)).filter(Boolean)
      || [...jugadores].sort((a, b) => (b.total || 0) - (a.total || 0));
    ranking.forEach((j, indice) => {
      const item = document.createElement("div");
      item.className = `item-clasificacion ${j.id === miId ? "clasificacion-yo" : ""}`;
      item.dataset.playerId = String(j.id);
      const medalla = indice === 0 ? "🥇" : indice === 1 ? "🥈" : indice === 2 ? "🥉" : `${indice + 1}.`;
      item.innerHTML = `
        <span>${medalla} ${renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id)}${renderizarEmocion(j.emocion)}${escaparHtml(j.nombre)}${j.id === miId ? " (TÚ)" : ""}</span>
        <strong class="pts-total-badge">${j.total || 0} pts</strong>
      `;
      contClasificacion.appendChild(item);
    });
    renderizarPodio(ranking, !!msg.partida_terminada);
  }

  // Renderizar Historial Global
  const contHistorial = document.getElementById("contenedor-historial-completo");
  if (contHistorial) {
    contHistorial.innerHTML = "";
    if (historialGlobal.length === 0) {
      contHistorial.innerHTML = '<p class="texto-muted">Sin historial previo.</p>';
    } else {
    historialGlobal.forEach((item) => {
      const card = document.createElement("div");
      card.className = "card-ronda-historial";
        let jugadoresHtml = "";
        (item.jugadores || []).forEach((jugador) => {
          const respuestasHtml = Object.entries(jugador.resultados || {}).map(([categoria, resultado]) => {
            const respuesta = resultado.respuesta || jugador.respuestas?.[categoria] || "—";
            const estado = (resultado.estado || "").replaceAll("_", " ");
            return `<li>${escaparHtml(categoria)} — ${escaparHtml(respuesta)} — ${escaparHtml(estado)} — ${resultado.puntos || 0} pts</li>`;
          }).join("");
          jugadoresHtml += `<div><strong>${renderizarAvatar(jugador.avatar || "🐻", "avatar-jugador", jugador.id)}${escaparHtml(jugador.nombre)}: ${jugador.puntos_categorias ?? jugador.puntos_obtenidos ?? 0} puntos de categorías${jugador.bonus ? ` + ${jugador.bonus} bonus 🔥 ¡RONDA PERFECTA!` : ""} · total ronda ${jugador.puntos_obtenidos ?? item.puntuaciones?.[jugador.nombre] ?? 0} · acumulado ${jugador.puntuacion_acumulada ?? "—"}</strong><ul>${respuestasHtml}</ul></div>`;
        });
        if (!jugadoresHtml) {
          jugadoresHtml = Object.entries(item.puntuaciones || {}).map(([nombre, pts]) => `<span>${escaparHtml(nombre)}: <strong>+${pts} pts</strong></span>`).join(" ");
        }
        card.innerHTML = `
          <div class="card-ronda-header">
            <span>RONDA ${item.ronda} (Letra ${item.letra})</span>
          </div>
          <div class="card-ronda-cuerpo" style="display:flex; flex-wrap:wrap; gap:12px; font-size:0.88rem;">
            ${jugadoresHtml}
          </div>
        `;
        contHistorial.appendChild(card);
      });
    }
  }

  // Controles de Nueva Ronda
  const btnNueva = document.getElementById("btn-nueva-ronda");
  const msgEsperaNueva = document.getElementById("msg-espera-host-nueva");
  const partidaTerminada = !!msg.partida_terminada;
  const titulo = document.getElementById("titulo-resultados");
  const tituloAccion = document.getElementById("titulo-accion-resultados");
  const estadisticas = document.getElementById("estadisticas-partida");
  if (titulo) titulo.textContent = partidaTerminada ? "🏁 PARTIDA TERMINADA" : "RESULTADOS DE LA RONDA";
  if (tituloAccion) tituloAccion.textContent = partidaTerminada ? "Partida finalizada" : "Próxima Ronda";
  if (estadisticas) {
    estadisticas.classList.toggle("hidden", !partidaTerminada);
    if (partidaTerminada) {
      renderizarEstadisticas(msg.estadisticas || {});
    }
  }
  if (btnNueva && msgEsperaNueva) {
    if (esAnfitrion) {
      btnNueva.style.display = "block";
      btnNueva.dataset.nuevaPartida = String(partidaTerminada);
      btnNueva.querySelector("span").textContent = partidaTerminada ? "🔄 NUEVA PARTIDA" : "INICIAR SIGUIENTE RONDA";
      msgEsperaNueva.classList.add("hidden");
    } else {
      btnNueva.style.display = "none";
      btnNueva.dataset.nuevaPartida = String(partidaTerminada);
      msgEsperaNueva.classList.remove("hidden");
      msgEsperaNueva.textContent = partidaTerminada ? "Esperando a que el anfitrión inicie una nueva partida..." : "Esperando a que el anfitrión inicie la siguiente ronda...";
    }
  }

  cambiarPantalla("RESULTADOS");
  animarResultadosProgresivamente(animar);
  const clavePuntaje = JSON.stringify([
    numRonda,
    !!msg.partida_terminada,
    ...jugadores.map((jugador) => [jugador.id, jugador.puntos_ronda, jugador.total])
  ]);
  if (clavePuntaje !== ultimaAnimacionPuntaje) {
    ultimaAnimacionPuntaje = clavePuntaje;
    setTimeout(animarPuntos, 120);
  }
  const jugadoresRondaPerfecta = jugadores.filter((jugador) => jugador.bonus_ronda > 0);
  if (jugadoresRondaPerfecta.length) {
    const participantes = jugadoresRondaPerfecta.map((jugador) => jugador.id).sort((a, b) => a - b);
    lanzarConfeti(`ronda-perfecta:${numRonda}:${participantes.join(",")}`);
  }
  if (msg.partida_terminada) {
    const ganoPartida = miJugador?.emocion === "🏆";
    if (miJugador) reproducirSonido(ganoPartida ? "ganador" : "derrota");
    if (ganoPartida) lanzarConfeti(`victoria:${numRonda}:${miJugador.id}:${miJugador.total}`);
  }
  renderizarPerfil(msg);
  if (msg.partida_terminada) limpiarPerfilesTemporales();
}

function renderizarPodio(ranking, partidaTerminada) {
  const podio = document.getElementById("podio-final");
  if (!podio) return;
  podio.replaceChildren();
  podio.classList.toggle("hidden", !partidaTerminada || ranking.length === 0);
  if (!partidaTerminada) return;

  const puestos = [
    { lugar: 1, medalla: "🥇", etiqueta: "Primer lugar", clase: "podio-puesto-1" },
    { lugar: 2, medalla: "🥈", etiqueta: "Segundo lugar", clase: "podio-puesto-2" },
    { lugar: 3, medalla: "🥉", etiqueta: "Tercer lugar", clase: "podio-puesto-3" },
  ];
  puestos.forEach((puesto) => {
    const jugador = ranking[puesto.lugar - 1];
    if (!jugador) return;
    const tarjeta = document.createElement("div");
    tarjeta.className = `podio-puesto ${puesto.clase}${puesto.lugar === 1 ? " podio-ganador" : ""}`;
    tarjeta.setAttribute("aria-label", `${puesto.etiqueta}: ${jugador.nombre}, ${jugador.total || 0} puntos`);
    tarjeta.innerHTML = `
      <span class="podio-medalla">${puesto.medalla}</span>
      ${puesto.lugar === 1 ? '<span class="podio-corona" aria-label="Ganador">👑 Ganador</span>' : ""}
      <span class="podio-personaje">${renderizarAvatar(jugador.avatar || "🐻", "avatar-podio", jugador.id)}</span>
      <strong>${escaparHtml(jugador.nombre)}</strong>
      <span class="podio-puntos">${Number(jugador.total || 0).toLocaleString("es-CO")} pts</span>
    `;
    podio.appendChild(tarjeta);
  });
}

function notificarLogrosNuevos(logros) {
  const claveLogros = `stop_logros_vistos_${tokenSesion || miId}`;
  const logrosPrevios = new Set((localStorage.getItem(claveLogros) || "").split(",").filter(Boolean));
  const nuevos = logros.filter((logro) => logro.id && !logrosPrevios.has(logro.id));
  if (!nuevos.length) return;

  localStorage.setItem(claveLogros, [...logrosPrevios, ...nuevos.map((logro) => logro.id)].join(","));
  window.setTimeout(() => {
    reproducirSonido("logro");
    lanzarConfeti(`logros:${tokenSesion || miId}:${nuevos.map((logro) => logro.id).sort().join(",")}`);
    mostrarEfectoJuego(
      "🔓",
      "✨ LOGRO DESBLOQUEADO ✨",
      nuevos.map((logro) => `${logro.icono} ${logro.nombre}`).join(" · "),
      "efecto-logro"
    );
  }, 1600);
}

function renderizarPerfil(msg) {
  const contenedor = document.getElementById("perfil-mi-jugador");
  if (!contenedor) return;
  const miJugador = (msg.jugadores || []).find((jugador) => jugador.id === miId);
  const perfil = (msg.perfiles || {})[String(miId)] || miJugador?.perfil;
  if (!perfil) { contenedor.innerHTML = ""; return; }
  notificarLogrosNuevos(perfil.logros || []);
  contenedor.innerHTML = contenidoPerfil(perfil, miJugador);
}

function renderizarPerfilTemporal(msg) {
  const contenedor = document.getElementById("perfil-mi-jugador-ronda");
  if (!contenedor) return;
  const miJugador = (msg.jugadores || []).find((jugador) => jugador.id === miId);
  if (!miJugador?.perfil) {
    contenedor.innerHTML = "";
    return;
  }
  contenedor.innerHTML = contenidoPerfil(miJugador.perfil, miJugador);
}

function contenidoPerfil(perfil, miJugador) {
  const logros = (perfil.logros || []).map((logro) => `<span class="chip-logro" title="${escaparHtml(logro.descripcion || "")}">${logro.icono} ${escaparHtml(logro.nombre)}</span>`).join("");
  return `
    ${renderizarAvatar(miJugador?.avatar || AVATARES.find((opcion) => opcion.id === avatarSeleccionado)?.emoji || "🐻", "perfil-avatar", miId)}
    <div class="perfil-contenido">
      <div class="perfil-titulo"><span>👤 ${escaparHtml(perfil.nombre)}</span><strong>${Number(perfil.puntos || 0).toLocaleString("es-CO")} pts</strong></div>
      <div class="perfil-metricas">
        <span>🏆 ${perfil.victorias || 0} victorias de partida</span>
        <span>⭐ ${perfil.rondas_ganadas || 0} rondas ganadas</span>
        <span>🛑 ${perfil.stops || 0} STOP</span>
      </div>
      <div class="perfil-logros">${logros || '<span class="texto-muted">Tus logros aparecerán aquí.</span>'}</div>
    </div>`;
}

function limpiarPerfilesTemporales() {
  ["perfil-mi-jugador", "perfil-mi-jugador-ronda"].forEach((id) => {
    const contenedor = document.getElementById(id);
    if (contenedor) contenedor.innerHTML = "";
  });
}

function renderizarEstadisticas(stats) {
  const generales = document.getElementById("estadisticas-generales");
  const porJugador = document.getElementById("estadisticas-jugadores");
  if (!generales || !porJugador) return;
  const tarjetaRey = document.getElementById("rey-del-stop");
  if (tarjetaRey) {
    const rey = stats.rey_del_stop;
    tarjetaRey.replaceChildren();
    tarjetaRey.classList.toggle("hidden", !rey);
    if (rey) {
      tarjetaRey.innerHTML = `
        <span class="rey-stop-personaje">${renderizarAvatar(rey.avatar || "🐻", "avatar-rey-stop", rey.id)}</span>
        <span class="rey-stop-texto">
          <strong>👑 REY DEL STOP · MVP</strong>
          <span>${escaparHtml(rey.nombre)} · ${rey.cantidad_stop} STOP</span>
        </span>
      `;
    }
  }
  const lineas = [
    ["Rondas", stats.rondas_completadas],
    ["Jugadores", stats.jugadores],
    ["Palabras válidas", stats.respuestas_validas],
    ["STOP realizados", stats.cantidad_stop],
    ["Mejor jugador", stats.mejor_jugador || (stats.ganadores || []).join(", ") || "—"],
    ["Mayor puntuación", Number(stats.mayor_puntuacion || 0).toLocaleString("es-CO")],
    ["Respuestas totales", stats.respuestas_totales],
    ["Respuestas inválidas", stats.respuestas_invalidas],
    ["Validadas por votación", stats.respuestas_validadas_votacion],
    ["Rechazadas por votación", stats.respuestas_rechazadas_votacion],
    ["Rondas perfectas", stats.rondas_perfectas],
    ["Letras utilizadas", (stats.letras_utilizadas || []).join(", ") || "—"],
  ];
  generales.replaceChildren();
  const listaGeneral = document.createElement("ul");
  lineas.forEach(([etiqueta, valor]) => {
    const li = document.createElement("li");
    li.textContent = `${etiqueta}: ${valor ?? 0}`;
    listaGeneral.appendChild(li);
  });
  generales.appendChild(listaGeneral);

  porJugador.replaceChildren();
  (stats.por_jugador || []).forEach((jugador) => {
    const card = document.createElement("section");
    card.className = "card estadistica-jugador";
    const titulo = document.createElement("h4");
    titulo.textContent = `${jugador.nombre} — ${jugador.puntos_totales} pts`;
    const puntosRonda = (jugador.puntos_por_ronda || []).map((r) =>
      `R${r.ronda}: ${r.total} (${r.puntos_categorias} categorías + ${r.bonus} bonus)`
    ).join(" · ") || "Sin rondas jugadas";
    const logrosHtml = (jugador.logros || []).map((logro) => `<span class="chip-logro">${logro.icono} ${escaparHtml(logro.nombre)}</span>`).join("");
    const resumen = [
      `Puntos por ronda: ${puntosRonda}`,
      `Victorias de partida: ${jugador.victorias} · Rondas ganadas: ${jugador.rondas_ganadas}`,
      `Promedio por ronda: ${Number(jugador.promedio_puntos_por_ronda || 0).toLocaleString("es-CO")} pts · Mejor ronda: ${jugador.mejor_ronda ? `R${jugador.mejor_ronda.ronda} (${jugador.mejor_ronda.puntos} pts)` : "—"}`,
      `Válidas: ${jugador.respuestas_correctas} · No válidas: ${jugador.respuestas_incorrectas} · Repetidas: ${jugador.respuestas_repetidas}`,
      `Validadas por votación: ${jugador.validadas_por_votacion} · Rechazadas: ${jugador.rechazadas_por_votacion}`,
      `STOP: ${jugador.cantidad_stop} · Rondas perfectas: ${jugador.rondas_perfectas}`,
      `Enviadas: ${jugador.respuestas_enviadas}/${jugador.respuestas_posibles} · Participación: ${jugador.participacion}% (${jugador.rondas_participadas} rondas con respuestas)`,
    ];
    const lista = document.createElement("ul");
    resumen.forEach((texto) => {
      const li = document.createElement("li");
      li.textContent = texto;
      lista.appendChild(li);
    });
    const logros = document.createElement("div");
    logros.className = "perfil-logros estadisticas-logros";
    logros.innerHTML = logrosHtml || '<span class="texto-muted">Sin logros todavía.</span>';
    card.append(titulo, lista, logros);
    porJugador.appendChild(card);
  });
}

// ==================== UTILIDADES ====================
function mostrarToast(mensaje, tipo = "error") {
  if (!toastEl) return;
  clearTimeout(toastTimeout);
  toastEl.textContent = mensaje;
  toastEl.className = `toast ${tipo === "success" ? "toast-success" : tipo === "info" ? "toast-info" : ""}`;
  toastTimeout = setTimeout(() => {
    toastEl.classList.add("hidden");
  }, 3500);
}

function mostrarNotificacionJugador(mensaje) {
  if (!toastEl) return;
  const evento = ["entrada", "salida", "reconexion"].includes(mensaje.evento)
    ? mensaje.evento
    : "entrada";
  clearTimeout(toastTimeout);
  toastEl.textContent = mensaje.mensaje || "Actualización de jugadores.";
  toastEl.className = `toast toast-info toast-notificacion-jugador toast-${evento}`;
  toastTimeout = setTimeout(() => {
    toastEl.classList.add("hidden");
  }, 3500);
}

function escaparHtml(texto) {
  if (!texto) return "";
  const div = document.createElement("div");
  div.textContent = texto;
  return div.innerHTML;
}

// Escuchar escritura en los inputs para sincronizar
window.addEventListener("DOMContentLoaded", () => {
  renderizarSelectorAvatares();
  renderizarReacciones();
  alternarCamposCodigoSala();
  actualizarInfoUsuario();
  const botonSonido = document.getElementById("btn-sonido");
  if (botonSonido) {
    botonSonido.textContent = sonidoActivado ? "🔊 Sonidos activados" : "🔇 Sonidos desactivados";
    botonSonido.setAttribute("aria-pressed", String(sonidoActivado));
  }
  actualizarControlMusica();
  const controlVolumen = document.getElementById("volumen-audio");
  if (controlVolumen) {
    controlVolumen.value = String(Math.round(volumenAudio * 100));
    controlVolumen.addEventListener("input", () => actualizarVolumenAudio(controlVolumen.value));
  }
  window.addEventListener("click", () => {
    if (musicaActivada) iniciarMusicaConcentracion();
  }, { once: true });
  CATEGORIAS.forEach((cat) => {
    const input = document.getElementById(`cat-${cat}`);
    if (input) {
      input.addEventListener("input", enviarRespuestasTiempoReal);
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          enviarStop();
        }
      });
    }
  });

  inicializarWebSocket();
});
