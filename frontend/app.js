// ==================== CONFIGURACIÓN Y ESTADO ====================
const CATEGORIAS = ["nombre", "apellido", "ciudad", "fruta", "animal", "cosa"];
let categoriasActivas = [...CATEGORIAS];
const ETIQUETAS_CATEGORIA = { nombre: "Nombre", apellido: "Apellido", ciudad: "Ciudad", fruta: "Fruta", animal: "Animal", cosa: "Cosa" };

let socket = null;
let reconectarInterval = null;
let tokenSesion = localStorage.getItem("stop_token") || "";
let nombreGuardado = localStorage.getItem("stop_nombre") || "";
let reconectando = false;
let sesionReemplazada = false;
let miId = null;
let miNombre = "";
let esAnfitrion = false;
let esEspectador = false;
let estadoJuego = "LOGIN"; // LOGIN, SALA, JUEGO, VOTACION, RESULTADOS
let debounceRespuestasTimer = null;
let temporizadorVisual = null;
let sonidoActivado = localStorage.getItem("stop_sonido") !== "0";
let audioContext = null;

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
    bannerReconnect.classList.add("hidden");

    if (reconectarInterval) {
      clearInterval(reconectarInterval);
      reconectarInterval = null;
    }

    if (tokenSesion && nombreGuardado) {
      enviarMensaje({ tipo: "conexion", nombre: nombreGuardado, token: tokenSesion });
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

// ==================== MANEJO DE MENSAJES DEL SERVIDOR ====================
function manejarMensajeServidor(msg) {
  const tipo = msg.tipo;
  if (Object.prototype.hasOwnProperty.call(msg, "espectador")) {
    esEspectador = !!msg.espectador;
    actualizarInfoUsuario();
  }

  switch (tipo) {
    case "error":
      mostrarToast(msg.mensaje || "Ocurrió un error", "error");
      break;

    case "bienvenida":
      miId = msg.id;
      miNombre = msg.nombre;
      tokenSesion = msg.token || tokenSesion;
      nombreGuardado = miNombre;
      localStorage.setItem("stop_token", tokenSesion);
      localStorage.setItem("stop_nombre", nombreGuardado);
      esAnfitrion = !!msg.es_anfitrion;
      esEspectador = !!msg.es_espectador;
      actualizarInfoUsuario();
      if (msg.reconectado || reconectando) {
        if (textoConexion) textoConexion.textContent = "✅ Conexión recuperada";
        mostrarToast("✅ Conexión recuperada", "success");
      }
      reconectando = false;
      break;

    case "sala":
      actualizarSala(msg);
      break;

    case "ronda":
      reproducirSonido("ronda");
      mostrarEfectoRonda(msg);
      iniciarPantallaJuego(msg);
      actualizarJugadoresEnPartida(msg.jugadores || [], msg.espectadores || []);
      break;

    case "jugadores":
      actualizarJugadoresEnPartida(msg.jugadores || [], msg.espectadores || []);
      break;

    case "votacion":
      detenerTemporizadorVisual();
      bloquearCamposRonda();
      if (msg.motivo_cierre === "stop") mostrarEfectoStop(msg.quien_stop || "Un jugador");
      else reproducirSonido("tiempo");
      mostrarPantallaVotacion(msg);
      break;

    case "resultados":
      detenerTemporizadorVisual();
      bloquearCamposRonda();
      if (msg.motivo_cierre === "stop") mostrarEfectoStop(msg.quien_stop || "Un jugador");
      else reproducirSonido("tiempo");
      mostrarPantallaResultados(msg);
      break;

    default:
      console.log("Mensaje no reconocido:", msg);
  }
}

// ==================== ANIMACIONES Y SONIDO ====================
function obtenerAudioContext() {
  if (!sonidoActivado) return null;
  try {
    if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === "suspended") audioContext.resume();
    return audioContext;
  } catch (_) { return null; }
}

function reproducirSonido(tipo) {
  const ctx = obtenerAudioContext();
  if (!ctx) return;
  const patrones = {
    tic: [[620, 0.04, 0.035]],
    ronda: [[440, 0.07, 0.06], [660, 0.08, 0.07], [880, 0.12, 0.08]],
    stop: [[220, 0.08, 0.08], [110, 0.16, 0.12]],
    tiempo: [[180, 0.16, 0.1], [120, 0.2, 0.12]],
    ganador: [[523, 0.08, 0.07], [659, 0.08, 0.07], [784, 0.16, 0.1], [1047, 0.25, 0.12]],
    punto: [[740, 0.07, 0.04]]
  };
  let retraso = 0;
  (patrones[tipo] || []).forEach(([frecuencia, duracion, volumen]) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = tipo === "stop" ? "sawtooth" : "sine";
    osc.frequency.value = frecuencia;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime + retraso);
    gain.gain.exponentialRampToValueAtTime(volumen, ctx.currentTime + retraso + 0.01);
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

function mostrarEfectoStop(nombre) {
  reproducirSonido("stop");
  mostrarEfectoJuego("😂", "¡STOP!", `${nombre} ha terminado la ronda`, "efecto-stop");
}

function mostrarEfectoRonda(msg) {
  const letra = msg.letra || "?";
  mostrarEfectoJuego("✋", `¡LETRA ${letra}!`, "Prepárate... comienza la ronda", "efecto-ronda");
}

function lanzarConfeti() {
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
  document.querySelectorAll(".pts-ronda-badge").forEach((el, indice) => {
    setTimeout(() => {
      el.classList.add("puntos-entra");
      reproducirSonido("punto");
    }, indice * 100);
  });
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

  if (!nombre) {
    mostrarToast("El nombre es obligatorio.", "error");
    return;
  }

  enviarMensaje({
    tipo: "conexion",
    nombre,
    ...(tokenSesion ? { token: tokenSesion } : {}),
  });
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
  if (avatar) avatar.textContent = miNombre.charAt(0).toUpperCase();
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
          <span>${escaparHtml(j.nombre)} ${j.id === miId ? "(TÚ)" : ""}${j.conectado === false ? " · Desconectado" : ""}</span>
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
    const estado = j.estado || `${j.total || 0} pts`;
    const desconectado = j.conectado === false;
    li.innerHTML = `
      <span>${escaparHtml(j.nombre)}${etiquetaYo}${host}${desconectado ? " · Desconectado" : ""}</span>
      <strong class="${desconectado ? "texto-muted" : "puntos-verde"}">${escaparHtml(estado)}</strong>
    `;
    lista.appendChild(li);
  });
  espectadores.forEach((e) => {
    const li = document.createElement("li");
    li.className = "item-jugador-simple";
    li.innerHTML = `<span>👀 ${escaparHtml(e.nombre)}</span><strong class="texto-muted">Espectador</strong>`;
    lista.appendChild(li);
  });
}

function iniciarPantallaJuego(msg) {
  if (msg.categorias) categoriasActivas = msg.categorias;
  actualizarVisibilidadCategorias();
  const letra = msg.letra || "?";
  const numRonda = msg.ronda || 1;

  document.getElementById("letra-ronda").textContent = letra;
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
}

function iniciarTemporizadorVisual(venceEn, servidorAhora) {
  detenerTemporizadorVisual();
  const etiqueta = document.getElementById("temporizador-ronda");
  const diferenciaReloj = Number(servidorAhora) * 1000 - Date.now();
  let ultimoSegundo = null;
  const actualizar = () => {
    const segundos = Math.max(0, Math.ceil((Number(venceEn) * 1000 - (Date.now() + diferenciaReloj)) / 1000));
    if (etiqueta) {
      etiqueta.textContent = `${String(Math.floor(segundos / 60)).padStart(2, "0")}:${String(segundos % 60).padStart(2, "0")}`;
      etiqueta.classList.toggle("tiempo-agotado", segundos === 0);
      etiqueta.classList.toggle("tiempo-critico", segundos <= 10 && segundos > 0);
    }
    if (segundos !== ultimoSegundo && segundos <= 5 && segundos > 0) reproducirSonido("tic");
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
    const votos = `${candidato.votos_si || 0} SÍ · ${candidato.votos_no || 0} NO · ${total} votantes`;

    card.innerHTML = `
      <div class="votacion-cabecera">
        <div>
          <span class="badge-categoria-votacion">${ETIQUETAS_CATEGORIA[candidato.categoria] || candidato.categoria}</span>
          <h2>"${escaparHtml(candidato.respuesta)}"</h2>
          <p class="texto-muted">Respuesta de: ${autores}</p>
        </div>
        <div class="contador-votos">${votos}</div>
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
    li.innerHTML = `<span>${escaparHtml(j.nombre)}${host}${j.id === miId ? " (TÚ)" : ""}</span><strong class="${disconnected ? "texto-muted" : "puntos-verde"}">${escaparHtml(j.estado || "En votación")}</strong>`;
    lista.appendChild(li);
  });
  espectadores.forEach((e) => {
    const li = document.createElement("li");
    li.className = "item-jugador-simple";
    li.innerHTML = `<span>👀 ${escaparHtml(e.nombre)}${e.id === miId ? " (TÚ)" : ""}</span><strong class="texto-muted">Espectador</strong>`;
    lista.appendChild(li);
  });
}

function votarRespuesta(clave, voto, card) {
  if (card) card.querySelectorAll("button[data-voto]").forEach((b) => b.disabled = true);
  enviarMensaje({ tipo: "voto", clave, voto });
}

function mostrarPantallaResultados(msg) {
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
        let etiqueta = puntos > 0 ? `+${puntos} pts` : "0 pts";
        if (d.estado === "votacion_rechazada") etiqueta = `❌ Rechazada por votación · ${etiqueta}`;
        if (d.estado === "votada_unica" || d.estado === "votada_repetida") etiqueta = `🗳️ Validada por votación · ${etiqueta}`;
        if (d.estado === "valida_unica") etiqueta = `✅ Automática · ${etiqueta}`;
        if (d.estado === "valida_repetida") etiqueta = `🔁 Repetida · ${etiqueta}`;
        if (d.estado === "letra_incorrecta") etiqueta = `❌ Letra incorrecta · ${etiqueta}`;
        if (d.estado === "vacia") etiqueta = `⚪ Vacía · ${etiqueta}`;
        return `<div>${escaparHtml(respuesta)}</div><small class="${clase}">${etiqueta}</small>`;
      };

      tr.innerHTML = `
        <td><strong>${escaparHtml(j.nombre)} ${j.id === miId ? "(TÚ)" : ""}</strong></td>
        <td data-cat="nombre">${celdaRespuesta("nombre")}</td>
        <td data-cat="apellido">${celdaRespuesta("apellido")}</td>
        <td data-cat="ciudad">${celdaRespuesta("ciudad")}</td>
        <td data-cat="fruta">${celdaRespuesta("fruta")}</td>
        <td data-cat="animal">${celdaRespuesta("animal")}</td>
        <td data-cat="cosa">${celdaRespuesta("cosa")}</td>
        <td>
          <span class="pts-ronda-badge">+${j.puntos_ronda || 0}</span>
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
      const medalla = indice === 0 ? "🥇" : indice === 1 ? "🥈" : indice === 2 ? "🥉" : `${indice + 1}.`;
      item.innerHTML = `
        <span>${medalla} ${escaparHtml(j.nombre)}${j.id === miId ? " (TÚ)" : ""}</span>
        <strong>${j.total || 0} pts</strong>
      `;
      contClasificacion.appendChild(item);
    });
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
          jugadoresHtml += `<div><strong>${escaparHtml(jugador.nombre)}: ${jugador.puntos_categorias ?? jugador.puntos_obtenidos ?? 0} puntos de categorías${jugador.bonus ? ` + ${jugador.bonus} bonus 🔥 ¡RONDA PERFECTA!` : ""} · total ronda ${jugador.puntos_obtenidos ?? item.puntuaciones?.[jugador.nombre] ?? 0} · acumulado ${jugador.puntuacion_acumulada ?? "—"}</strong><ul>${respuestasHtml}</ul></div>`;
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
  setTimeout(animarPuntos, 120);
  if (msg.partida_terminada) {
    reproducirSonido("ganador");
    lanzarConfeti();
  }
  renderizarPerfil(msg);
}

function renderizarPerfil(msg) {
  const contenedor = document.getElementById("perfil-mi-jugador");
  if (!contenedor) return;
  const perfil = (msg.perfiles || {})[String(miId)] || jugadores.find((j) => j.id === miId)?.perfil;
  if (!perfil) { contenedor.innerHTML = ""; return; }
  const logros = (perfil.logros || []).map((logro) => `<span class="chip-logro" title="${escaparHtml(logro.descripcion || "")}">${logro.icono} ${escaparHtml(logro.nombre)}</span>`).join("");
  contenedor.innerHTML = `
    <div class="perfil-avatar">${escaparHtml((perfil.nombre || "?").charAt(0).toUpperCase())}</div>
    <div class="perfil-contenido">
      <div class="perfil-titulo"><span>👤 ${escaparHtml(perfil.nombre)}</span><strong>${Number(perfil.puntos || 0).toLocaleString("es-CO")} pts</strong></div>
      <div class="perfil-metricas">
        <span>🏆 ${perfil.victorias || 0} victorias</span>
        <span>⭐ ${perfil.rondas_ganadas || 0} rondas ganadas</span>
        <span>🛑 ${perfil.stops || 0} STOP</span>
      </div>
      <div class="perfil-logros">${logros || '<span class="texto-muted">Tus logros aparecerán aquí.</span>'}</div>
    </div>`;
}

function renderizarEstadisticas(stats) {
  const generales = document.getElementById("estadisticas-generales");
  const porJugador = document.getElementById("estadisticas-jugadores");
  if (!generales || !porJugador) return;
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
      `Correctas: ${jugador.respuestas_correctas} · Incorrectas: ${jugador.respuestas_incorrectas} · Repetidas: ${jugador.respuestas_repetidas}`,
      `Validadas por votación: ${jugador.validadas_por_votacion} · Rechazadas: ${jugador.rechazadas_por_votacion}`,
      `STOP: ${jugador.cantidad_stop} · Rondas perfectas: ${jugador.rondas_perfectas}`,
      `Participación: ${jugador.participacion}% (${jugador.respuestas_enviadas}/${jugador.respuestas_posibles} respuestas posibles; ${jugador.rondas_participadas} rondas con respuestas)`,
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
  toastEl.textContent = mensaje;
  toastEl.className = `toast ${tipo === "success" ? "toast-success" : tipo === "info" ? "toast-info" : ""}`;
  setTimeout(() => {
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
  const botonSonido = document.getElementById("btn-sonido");
  if (botonSonido) {
    botonSonido.textContent = sonidoActivado ? "🔊 Sonidos activados" : "🔇 Sonidos desactivados";
    botonSonido.setAttribute("aria-pressed", String(sonidoActivado));
  }
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
