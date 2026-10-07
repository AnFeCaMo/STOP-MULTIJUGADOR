import asyncio
import random
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from backend.validaciones import evaluar_palabra, normalizar

CATEGORIAS = ["nombre", "apellido", "ciudad", "fruta", "animal", "cosa"]
LETRAS_DISPONIBLES = "ABCDEFGLMPRSTV"
TIEMPO_PARA_MARCAR_AUSENTE = 300
UMBRAL_PUNTOS_EXPERTO = 200
TIEMPO_STOP_RELAMPAGO = 5
AVATARES = {
    "oso": "🐻",
    "gallina": "🐔",
    "gato": "🐱",
    "perro": "🐶",
    "mono": "🐵",
    "zorro": "🦊",
    "rana": "🐸",
    "panda": "🐼",
    "koala": "🐨",
    "tigre": "🐯",
    "leon": "🦁",
    "conejo": "🐰",
    "cerdo": "🐷",
    "vaca": "🐮",
    "pinguino": "🐧",
    "unicornio": "🦄",
    "robot": "🤖",
    "alien": "👽",
    "videojuego": "👾",
    "fantasma": "👻",
    "calabaza": "🎃",
}
AVATAR_PREDETERMINADO = "oso"
ERROR_SESION_EXPIRADA = "La sesión guardada ya expiró. Ingresa tu nombre para empezar de nuevo."
REACCIONES = {
    "jaja": "😂 JAJA",
    "facil": "😎 Fácil",
    "te_gane": "😏 Te gané",
    "vamos": "🔥 ¡Vamos!",
    "bien_jugado": "👏 Bien jugado",
    "que_paso": "😱 ¿Qué pasó?",
    "no_puede_ser": "😭 No puede ser",
    "pensando": "🤔 Estoy pensando",
    "ganamos": "🥳 ¡Ganamos!",
    "buena_partida": "❤️ Buena partida",
}


class GestorJuego:
    def __init__(self, duracion_ronda: int = 60, ventana_reconexion: float = 8.0):
        self.lock = asyncio.Lock()
        self.jugadores: Dict[int, Dict[str, Any]] = {}
        self.espectadores: Dict[int, Dict[str, Any]] = {}
        self.espectadores_registrados = set()
        self.id_counter = 1
        self.anfitrion_id: Optional[int] = None
        self.estado_juego = "SALA"  # SALA, JUEGO, VOTACION, RESULTADOS
        self.letra_actual = ""
        self.ronda_actual = 0
        self.rondas_totales = 4
        self.categorias_activas = list(CATEGORIAS)
        self.letras_disponibles = list(LETRAS_DISPONIBLES)
        self.letras_utilizadas: List[str] = []
        self.partida_terminada = False
        self.quien_stop = ""
        self.historial_global: List[Dict[str, Any]] = []
        self.votaciones: Dict[str, Dict[str, Any]] = {}
        self._detalles_votacion_final: List[Dict[str, Any]] = []
        self.duracion_ronda = duracion_ronda
        self.vence_en = 0.0
        self.vence_en_monotonic = 0.0
        self.ronda_iniciada_monotonic = 0.0
        # Si todos los clientes desaparecen, damos una pequeña ventana para que
        # una reconexión legítima pueda recuperar la partida. Si nadie vuelve,
        # la sala se limpia automáticamente para no resucitar partidas viejas.
        self.ventana_reconexion = ventana_reconexion
        self._tarea_reinicio_sala = None

    def buscar_jugador_por_ws(self, ws: WebSocket) -> Optional[int]:
        for j_id, data in self.jugadores.items():
            if data["ws"] == ws:
                return j_id
        return None

    def _buscar_sesion(self, token: Optional[str]):
        if not token:
            return None, None
        for coleccion, es_espectador in ((self.jugadores, False), (self.espectadores, True)):
            for jugador_id, datos in coleccion.items():
                if datos.get("token") == token:
                    return (jugador_id, datos), es_espectador
        return None, None

    def _crear_registro_jugador(
        self, jugador_id: int, nombre: str, ws, token: str, es_anfitrion: bool,
        avatar: str = AVATAR_PREDETERMINADO,
    ):
        return {
            "id": jugador_id,
            "nombre": nombre,
            "avatar": avatar,
            "ws": ws,
            "token": token,
            "reconectando": False,
            "desconectado_en": None,
            "ultima_reaccion": 0.0,
            "es_anfitrion": es_anfitrion,
            "respuestas_ronda": {cat: "" for cat in self.categorias_activas},
            "puntos_ronda": 0,
            "puntos_categorias": 0,
            "bonus_ronda": 0,
            "desglose_ronda": {cat: 0 for cat in self.categorias_activas},
            "detalle_respuestas": {cat: {} for cat in self.categorias_activas},
            "total": 0,
            "historial": [],
            "rondas_perfectas": 0,
            "cantidad_stop": 0,
        }

    def _hay_sesiones_conectadas(self):
        return any(datos.get("ws") is not None for datos in self.jugadores.values()) or any(
            datos.get("ws") is not None for datos in self.espectadores.values()
        )

    def _cancelar_reinicio_sala(self):
        tarea = self._tarea_reinicio_sala
        if tarea is not None and not tarea.done():
            tarea.cancel()
        self._tarea_reinicio_sala = None

    def _reiniciar_sala_vacia_locked(self):
        """Elimina por completo una partida cuando ya no queda nadie conectado."""
        self.jugadores.clear()
        self.espectadores.clear()
        self.espectadores_registrados.clear()
        self.id_counter = 1
        self.anfitrion_id = None
        self.estado_juego = "SALA"
        self.letra_actual = ""
        self.ronda_actual = 0
        self.rondas_totales = 4
        self.categorias_activas = list(CATEGORIAS)
        self.letras_disponibles = list(LETRAS_DISPONIBLES)
        self.letras_utilizadas = []
        self.partida_terminada = False
        self.quien_stop = ""
        self.historial_global = []
        self.votaciones = {}
        self.vence_en = 0.0
        self.vence_en_monotonic = 0.0
        self.ronda_iniciada_monotonic = 0.0
        self._detalles_votacion_final = []

    async def _esperar_reinicio_por_sala_vacia(self):
        try:
            await asyncio.sleep(self.ventana_reconexion)
            async with self.lock:
                if self._hay_sesiones_conectadas():
                    return
                self._reiniciar_sala_vacia_locked()
        except asyncio.CancelledError:
            return
        finally:
            if asyncio.current_task() is self._tarea_reinicio_sala:
                self._tarea_reinicio_sala = None

    def _programar_reinicio_si_sala_vacia(self):
        if self._hay_sesiones_conectadas():
            return
        self._cancelar_reinicio_sala()
        self._tarea_reinicio_sala = asyncio.create_task(self._esperar_reinicio_por_sala_vacia())

    async def conectar_sesion(
        self, ws: WebSocket, nombre: str, token: Optional[str] = None, avatar: Optional[str] = None
    ):
        async with self.lock:
            if not isinstance(nombre, str):
                return None, "El nombre debe ser texto."
            if token is not None and not isinstance(token, str):
                return None, "La sesión no es válida."
            if avatar is not None and (not isinstance(avatar, str) or avatar not in AVATARES):
                return None, "El avatar seleccionado no es válido."
            avatar_seleccionado = avatar or AVATAR_PREDETERMINADO
            nombre_limpio = nombre.strip()
            if not nombre_limpio:
                return None, "El nombre es obligatorio."

            sesion, era_espectador = self._buscar_sesion(token)
            if sesion:
                # Solo un token que aún pertenece a esta sala puede cancelar
                # la ventana de expiración y recuperar la partida.
                self._cancelar_reinicio_sala()
                jugador_id, datos = sesion
                anterior = datos.get("ws")
                datos["ws"] = ws
                datos["reconectando"] = False
                datos["desconectado_en"] = None
                if avatar is not None:
                    datos["avatar"] = avatar
                if not era_espectador and anterior is None:
                    self._reactivar_votante(jugador_id)
                return {
                    "id": jugador_id,
                    "token": datos["token"],
                    "nombre": datos["nombre"],
                    "avatar": datos["avatar"],
                    "es_espectador": era_espectador,
                    "es_anfitrion": not era_espectador and jugador_id == self.anfitrion_id,
                    "reconectado": True,
                    "socket_anterior": anterior if anterior is not ws else None,
                }, None

            if token is not None and (self.jugadores or self.espectadores):
                # Un token desconocido nunca crea una sesión silenciosamente:
                # la interfaz debe pedir al usuario que vuelva a identificarse.
                return None, ERROR_SESION_EXPIRADA

            # Sin sockets activos, un token inválido o una entrada nueva no
            # puede conservar la partida abandonada ni entrar como espectador.
            if not self._hay_sesiones_conectadas() and (self.jugadores or self.espectadores):
                self._cancelar_reinicio_sala()
                self._reiniciar_sala_vacia_locked()

            for data in list(self.jugadores.values()) + list(self.espectadores.values()):
                if data["nombre"].casefold() == nombre_limpio.casefold():
                    return None, f"Ya existe un jugador con el nombre '{nombre_limpio}'."

            # Errores de validación o tokens no válidos no deben cancelar el timer.
            self._cancelar_reinicio_sala()

            j_id = self.id_counter
            self.id_counter += 1
            nuevo_token = secrets.token_urlsafe(32)
            es_espectador = self.estado_juego in {"JUEGO", "VOTACION"}
            es_anfitrion = self.anfitrion_id is None or not any(d.get("ws") for d in self.jugadores.values())
            if es_anfitrion and not es_espectador:
                self.anfitrion_id = j_id
            if es_espectador:
                self.espectadores_registrados.add(j_id)
                self.espectadores[j_id] = {
                    "id": j_id, "nombre": nombre_limpio, "ws": ws,
                    "token": nuevo_token, "es_espectador": True,
                    "avatar": avatar_seleccionado,
                    "reconectando": False, "desconectado_en": None,
                    "ultima_reaccion": 0.0,
                }
            else:
                self.jugadores[j_id] = self._crear_registro_jugador(
                    j_id, nombre_limpio, ws, nuevo_token, es_anfitrion, avatar_seleccionado
                )
                self._sincronizar_anfitrion()
            return {
                "id": j_id,
                "token": nuevo_token,
                "nombre": nombre_limpio,
                "avatar": avatar_seleccionado,
                "es_espectador": es_espectador,
                "es_anfitrion": not es_espectador and j_id == self.anfitrion_id,
                "reconectado": False,
            }, None

    async def conectar(self, ws: WebSocket, nombre: str):
        """Compatibilidad con las pruebas y llamadas internas previas."""
        sesion, error = await self.conectar_sesion(ws, nombre)
        return (sesion["id"] if sesion else None), error

    def _sincronizar_anfitrion(self):
        for jugador_id, jugador in self.jugadores.items():
            jugador["es_anfitrion"] = jugador_id == self.anfitrion_id

    def _estado_presencia(self, sesion: Dict[str, Any], estado_ronda: Optional[str] = None) -> str:
        if sesion.get("ws") is None:
            if sesion.get("reconectando"):
                return "🔄 Reconectando"
            desconectado_en = sesion.get("desconectado_en")
            if desconectado_en is not None and time.time() - desconectado_en >= TIEMPO_PARA_MARCAR_AUSENTE:
                return "😴 Ausente"
            return "🔴 Desconectado"
        if estado_ronda == "completó":
            return "✅ Completó"
        if estado_ronda == "escribiendo":
            return "✍️ Escribiendo"
        return "🟢 Conectado"

    def _emocion_por_presencia(self, sesion: Dict[str, Any], estado_ronda: Optional[str] = None) -> str:
        if sesion.get("ws") is None:
            if sesion.get("reconectando"):
                return "🔄"
            desconectado_en = sesion.get("desconectado_en")
            if desconectado_en is not None and time.time() - desconectado_en >= TIEMPO_PARA_MARCAR_AUSENTE:
                return "😴"
            return "😴"
        if estado_ronda == "escribiendo":
            return "🤔"
        if sesion.get("es_espectador"):
            return "👀"
        return "😎"

    def marcar_reconectando(self, token: str):
        registro, es_espectador = self._buscar_sesion(token)
        if registro is None:
            return None
        jugador_id, sesion = registro
        if sesion.get("ws") is not None:
            return None
        sesion["reconectando"] = True
        return {
            "id": jugador_id,
            "nombre": sesion["nombre"],
            "es_espectador": es_espectador,
        }

    def crear_mensaje_reaccion(self, sesion_id: int, reaccion: Any):
        if not isinstance(reaccion, str) or reaccion not in REACCIONES:
            return None, "La reacción seleccionada no es válida."
        for coleccion in (self.jugadores, self.espectadores):
            sesion = coleccion.get(sesion_id)
            if sesion is not None and sesion.get("ws") is not None:
                ahora = time.monotonic()
                if ahora - sesion.get("ultima_reaccion", 0.0) < 0.8:
                    return None, "Espera un momento antes de enviar otra reacción."
                sesion["ultima_reaccion"] = ahora
                return {
                    "tipo": "reaccion",
                    "jugador_id": sesion_id,
                    "nombre": sesion["nombre"],
                    "avatar": AVATARES.get(sesion.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                    "reaccion": reaccion,
                    "texto": REACCIONES[reaccion],
                }, None
        return None, "La sesión no está conectada."

    def _reactivar_votante(self, jugador_id: int):
        if self.estado_juego != "VOTACION":
            return
        for candidato in self.votaciones.values():
            if "resultado" in candidato or jugador_id in candidato["autores"]:
                continue
            if jugador_id not in candidato["votos_si"] and jugador_id not in candidato["votos_no"]:
                if jugador_id not in candidato["votantes"]:
                    candidato["votantes"].append(jugador_id)

    async def desconectar(self, ws: WebSocket):
        async with self.lock:
            j_id = self.buscar_jugador_por_ws(ws)
            if j_id is not None:
                jugador = self.jugadores[j_id]
                jugador["ws"] = None
                jugador["reconectando"] = False
                jugador["desconectado_en"] = time.time()
                self._actualizar_votaciones_por_desconexion(j_id)
                if self.anfitrion_id == j_id:
                    conectados = [pid for pid, p in self.jugadores.items() if p.get("ws") is not None]
                    if conectados:
                        self.anfitrion_id = conectados[0]
                        self._sincronizar_anfitrion()
                if not self._hay_sesiones_conectadas():
                    self._programar_reinicio_si_sala_vacia()
                return jugador["nombre"]

            for espectador in self.espectadores.values():
                if espectador.get("ws") == ws:
                    espectador["ws"] = None
                    espectador["reconectando"] = False
                    espectador["desconectado_en"] = time.time()
                    if not self._hay_sesiones_conectadas():
                        self._programar_reinicio_si_sala_vacia()
                    return espectador["nombre"]
            return None

    def _promover_espectadores(self):
        if not self.espectadores:
            return
        para_promover = list(self.espectadores.items())
        self.espectadores.clear()
        for jugador_id, espectador in para_promover:
            es_anfitrion = self.anfitrion_id is None
            self.jugadores[jugador_id] = self._crear_registro_jugador(
                jugador_id, espectador["nombre"], espectador.get("ws"), espectador["token"],
                es_anfitrion, espectador.get("avatar", AVATAR_PREDETERMINADO),
            )
            if es_anfitrion:
                self.anfitrion_id = jugador_id
        if self.anfitrion_id not in self.jugadores or self.jugadores[self.anfitrion_id].get("ws") is None:
            conectados = [pid for pid, jugador in self.jugadores.items() if jugador.get("ws") is not None]
            if conectados:
                self.anfitrion_id = conectados[0]
        self._sincronizar_anfitrion()

    def sesiones_conectadas(self):
        return [
            (jugador_id, jugador, False)
            for jugador_id, jugador in self.jugadores.items() if jugador.get("ws") is not None
        ] + [
            (sesion_id, sesion, True)
            for sesion_id, sesion in self.espectadores.items() if sesion.get("ws") is not None
        ]

    def conexion_autorizada(self, ws: WebSocket, sesion_id: int, es_espectador: bool):
        coleccion = self.espectadores if es_espectador else self.jugadores
        sesion = coleccion.get(sesion_id)
        return sesion is not None and sesion.get("ws") is ws

    async def iniciar_ronda(self, jugador_id: int):
        async with self.lock:
            if jugador_id != self.anfitrion_id:
                return False, "Solamente el anfitrión puede iniciar la ronda."

            if self.estado_juego not in ["SALA", "RESULTADOS"]:
                return False, "La ronda ya está en curso."
            if self.partida_terminada or self.ronda_actual >= self.rondas_totales:
                return False, "La partida ha terminado. Inicia una nueva partida."

            letras_restantes = [letra for letra in self.letras_disponibles if letra not in self.letras_utilizadas]
            if not letras_restantes:
                return False, "No quedan letras disponibles sin repetir para esta partida."

            self.ronda_actual += 1
            self.letra_actual = random.choice(letras_restantes)
            self.letras_utilizadas.append(self.letra_actual)
            self.quien_stop = ""
            self.vence_en = time.time() + self.duracion_ronda
            self.vence_en_monotonic = asyncio.get_running_loop().time() + self.duracion_ronda
            self.ronda_iniciada_monotonic = asyncio.get_running_loop().time()
            self.estado_juego = "JUEGO"
            self.votaciones = {}

            for jugador in self.jugadores.values():
                jugador["respuestas_ronda"] = {cat: "" for cat in self.categorias_activas}
                jugador["puntos_ronda"] = 0
                jugador["puntos_categorias"] = 0
                jugador["bonus_ronda"] = 0
                jugador["desglose_ronda"] = {cat: 0 for cat in self.categorias_activas}
                jugador["detalle_respuestas"] = {cat: {} for cat in self.categorias_activas}

            return True, None

    async def actualizar_configuracion(self, jugador_id: int, rondas: Any, categorias: Any):
        async with self.lock:
            if jugador_id != self.anfitrion_id:
                return False, "Solamente el anfitrión puede cambiar la configuración."
            if self.estado_juego != "SALA" or self.ronda_actual != 0:
                return False, "La configuración queda bloqueada cuando inicia la partida."
            if isinstance(rondas, bool) or not isinstance(rondas, int) or not 4 <= rondas <= 10:
                return False, "La cantidad de rondas debe estar entre 4 y 10."
            if not isinstance(categorias, list) or any(not isinstance(c, str) for c in categorias):
                return False, "Selecciona categorías válidas."
            if len(set(categorias)) != len(categorias) or any(c not in CATEGORIAS for c in categorias):
                return False, "La selección contiene categorías inválidas."
            if len(categorias) < 3:
                return False, "Debes activar al menos 3 categorías."
            if rondas > len(self.letras_disponibles):
                return False, f"Solo hay {len(self.letras_disponibles)} letras disponibles para evitar repeticiones."
            self.rondas_totales = rondas
            self.categorias_activas = [cat for cat in CATEGORIAS if cat in categorias]
            return True, None

    async def actualizar_respuestas(self, jugador_id: int, respuestas: Dict[str, str]):
        async with self.lock:
            if self.estado_juego == "JUEGO" and asyncio.get_running_loop().time() >= self.vence_en_monotonic:
                self.quien_stop = ""
                self.vence_en = 0.0
                self.vence_en_monotonic = 0.0
                self._preparar_resultado_o_votacion()
                return True
            if self.estado_juego == "JUEGO" and jugador_id in self.jugadores and isinstance(respuestas, dict):
                self.jugadores[jugador_id]["respuestas_ronda"] = {
                    cat: str(respuestas.get(cat, "")).strip()[:80] for cat in self.categorias_activas
                }
            return False

    def _crear_clave_votacion(self, categoria: str, respuesta: str) -> str:
        return f"{categoria}:{normalizar(respuesta)}"

    def _preparar_votaciones(self) -> List[Dict[str, Any]]:
        candidatos: Dict[str, Dict[str, Any]] = {}

        for jugador_id, jugador in self.jugadores.items():
            for categoria in self.categorias_activas:
                respuesta = jugador["respuestas_ronda"].get(categoria, "")
                estado = evaluar_palabra(categoria, respuesta, self.letra_actual)
                if estado != "votacion":
                    continue

                clave = self._crear_clave_votacion(categoria, respuesta)
                if clave not in candidatos:
                    candidatos[clave] = {
                        "clave": clave,
                        "categoria": categoria,
                        "respuesta": respuesta,
                        "respuesta_normalizada": normalizar(respuesta),
                        "autores": [],
                        "votos_si": set(),
                        "votos_no": set(),
                    }
                candidatos[clave]["autores"].append(jugador_id)

        resultado = []
        for candidato in candidatos.values():
            autores = candidato["autores"]
            votantes = [
                j_id for j_id, jugador in self.jugadores.items()
                if jugador.get("ws") is not None and j_id not in autores
            ]
            resultado.append({
                **candidato,
                "votantes": votantes,
            })

        return resultado

    async def procesar_stop(self, jugador_id: int, respuestas_finales: Optional[Dict[str, str]] = None):
        return await self._cerrar_ronda(jugador_id, respuestas_finales, motivo="stop")

    async def finalizar_por_tiempo(self, ronda: int):
        """Cierra solo la ronda cuyo temporizador venció; llamadas tardías son inofensivas."""
        async with self.lock:
            if (ronda != self.ronda_actual or self.estado_juego != "JUEGO"
                    or asyncio.get_running_loop().time() < self.vence_en_monotonic):
                return False
            self.quien_stop = ""
            self.vence_en = 0.0
            self.vence_en_monotonic = 0.0
            self._preparar_resultado_o_votacion()
            return True

    async def _cerrar_ronda(self, jugador_id: Optional[int], respuestas_finales: Optional[Dict[str, str]], motivo: str):
        async with self.lock:
            if self.estado_juego != "JUEGO":
                return False, "La ronda ya ha finalizado."
            if asyncio.get_running_loop().time() >= self.vence_en_monotonic:
                self.quien_stop = ""
                self.vence_en = 0.0
                self.vence_en_monotonic = 0.0
                self._preparar_resultado_o_votacion()
                return False, "El tiempo de la ronda terminó."
            if motivo == "stop" and jugador_id not in self.jugadores:
                return False, "Jugador no encontrado."

            if respuestas_finales is not None:
                if not isinstance(respuestas_finales, dict):
                    return False, "Las respuestas deben enviarse como objeto."
                self.jugadores[jugador_id]["respuestas_ronda"] = {
                    cat: str(respuestas_finales.get(cat, "")).strip()[:80] for cat in self.categorias_activas
                }

            self.quien_stop = self.jugadores[jugador_id]["nombre"] if motivo == "stop" else ""
            if motivo == "stop":
                self.jugadores[jugador_id]["cantidad_stop"] += 1
            self.vence_en = 0.0
            self.vence_en_monotonic = 0.0
            self._preparar_resultado_o_votacion()
            return True, None

    def _preparar_resultado_o_votacion(self):
        candidatos = self._preparar_votaciones()
        self.votaciones = {c["clave"]: c for c in candidatos}
        self.estado_juego = "VOTACION" if candidatos else "RESULTADOS"
        if not candidatos:
            self._calcular_resultados()
            self._promover_espectadores()
            return
        for candidato in self.votaciones.values():
            if not candidato["votantes"]:
                candidato["resultado"] = False
        self._limpiar_votaciones_completadas()

    def registrar_voto(self, jugador_id: int, clave: str, voto: bool):
        if self.estado_juego != "VOTACION":
            return False, "La fase de votación ya terminó."
        if jugador_id not in self.jugadores:
            return False, "Jugador no encontrado."
        if not isinstance(clave, str) or clave not in self.votaciones:
            return False, "La respuesta a votar no existe."
        if not isinstance(voto, bool):
            return False, "El voto debe ser sí o no."

        candidato = self.votaciones[clave]
        if jugador_id not in candidato["votantes"]:
            return False, "No puedes votar tu propia respuesta."

        if jugador_id in candidato["votos_si"] or jugador_id in candidato["votos_no"]:
            return False, "Ya votaste por esta respuesta."

        (candidato["votos_si"] if voto else candidato["votos_no"]).add(jugador_id)

        if set(candidato["votantes"]) <= candidato["votos_si"] | candidato["votos_no"]:
            candidato["resultado"] = len(candidato["votos_si"]) > len(candidato["votos_no"])

        self._limpiar_votaciones_completadas()
        return True, None

    def _limpiar_votaciones_completadas(self):
        if self.votaciones and all("resultado" in c for c in self.votaciones.values()):
            self.estado_juego = "RESULTADOS"
            self._calcular_resultados()
            self.votaciones.clear()
            self._promover_espectadores()

    def _actualizar_votaciones_por_desconexion(self, jugador_id: int):
        if not self.votaciones:
            return

        for candidato in self.votaciones.values():
            if jugador_id in candidato["votantes"]:
                candidato["votantes"].remove(jugador_id)
            if not candidato["votantes"]:
                candidato["resultado"] = False
            elif set(candidato["votantes"]) <= candidato["votos_si"] | candidato["votos_no"]:
                candidato["resultado"] = len(candidato["votos_si"]) > len(candidato["votos_no"])

        if self.estado_juego == "VOTACION":
            self._limpiar_votaciones_completadas()

    def _resultado_candidato(self, categoria: str, respuesta: str) -> Optional[bool]:
        clave = self._crear_clave_votacion(categoria, respuesta)
        candidato = self.votaciones.get(clave)
        if candidato is None:
            return None
        return candidato.get("resultado", False)

    def _calcular_resultados(self):
        ahora_monotonic = asyncio.get_running_loop().time()
        duracion_ronda_real = round(max(0.0, ahora_monotonic - self.ronda_iniciada_monotonic), 1)
        respuestas_validas_cat: Dict[str, List[str]] = {cat: [] for cat in self.categorias_activas}
        estados_por_jugador: Dict[int, Dict[str, str]] = {}
        normas_por_jugador: Dict[int, Dict[str, Optional[str]]] = {}

        for j_id, jugador in self.jugadores.items():
            estados_por_jugador[j_id] = {}
            normas_por_jugador[j_id] = {}
            for categoria in self.categorias_activas:
                respuesta = jugador["respuestas_ronda"].get(categoria, "")
                estado = evaluar_palabra(categoria, respuesta, self.letra_actual)
                norm = normalizar(respuesta)
                aprobado = estado == "valida"

                if estado == "votacion":
                    aprobado = self._resultado_candidato(categoria, respuesta) is True

                if aprobado:
                    respuestas_validas_cat[categoria].append(norm)
                    estados_por_jugador[j_id][categoria] = "votada" if estado == "votacion" else "valida"
                    normas_por_jugador[j_id][categoria] = norm
                elif estado == "votacion":
                    estados_por_jugador[j_id][categoria] = "rechazada"
                    normas_por_jugador[j_id][categoria] = None
                else:
                    estados_por_jugador[j_id][categoria] = "invalida"
                    normas_por_jugador[j_id][categoria] = None

        detalles_globales = []
        for categoria in self.categorias_activas:
            for jugador in self.jugadores.values():
                respuesta = jugador["respuestas_ronda"].get(categoria, "")
                if evaluar_palabra(categoria, respuesta, self.letra_actual) != "votacion":
                    continue
                candidato = self.votaciones.get(self._crear_clave_votacion(categoria, respuesta))
                if candidato is not None:
                    detalles_globales.append({
                        "clave": candidato["clave"],
                        "categoria": categoria,
                        "respuesta": candidato["respuesta"],
                        "autores": [self.jugadores[a]["nombre"] for a in candidato["autores"] if a in self.jugadores],
                        "votos_si": len(candidato["votos_si"]),
                        "votos_no": len(candidato["votos_no"]),
                        "aprobada": bool(candidato.get("resultado", False)),
                    })

        for j_id, jugador in self.jugadores.items():
            puntos_ronda = 0
            desglose = {}
            detalle_respuestas = {}

            for categoria in self.categorias_activas:
                respuesta = jugador["respuestas_ronda"].get(categoria, "")
                estado = estados_por_jugador[j_id][categoria]
                norm = normas_por_jugador[j_id][categoria]

                if estado == "valida" and norm:
                    repeticiones = respuestas_validas_cat[categoria].count(norm)
                    puntos = 10 if repeticiones == 1 else 5
                    detalle = {
                        "respuesta": respuesta,
                        "estado": "valida_unica" if puntos == 10 else "valida_repetida",
                        "puntos": puntos,
                    }
                elif evaluar_palabra(categoria, respuesta, self.letra_actual) == "votacion":
                    candidato = self.votaciones.get(self._crear_clave_votacion(categoria, respuesta))
                    aprobada = bool(candidato and candidato.get("resultado", False))
                    if aprobada and norm:
                        repeticiones = respuestas_validas_cat[categoria].count(norm)
                        puntos = 10 if repeticiones == 1 else 5
                        estado_detalle = "votada_unica" if puntos == 10 else "votada_repetida"
                    else:
                        puntos = 0
                        estado_detalle = "votacion_rechazada"
                    detalle = {
                        "respuesta": respuesta,
                        "estado": estado_detalle,
                        "puntos": puntos,
                        "votos_si": len(candidato["votos_si"]) if candidato else 0,
                        "votos_no": len(candidato["votos_no"]) if candidato else 0,
                    }
                else:
                    puntos = 0
                    detalle = {
                        "respuesta": respuesta,
                        "estado": "vacia" if not respuesta.strip() else "letra_incorrecta",
                        "puntos": 0,
                    }

                desglose[categoria] = puntos
                detalle_respuestas[categoria] = detalle
                puntos_ronda += puntos

            jugador["puntos_ronda"] = puntos_ronda
            jugador["puntos_categorias"] = puntos_ronda
            jugador["bonus_ronda"] = 0
            jugador["desglose_ronda"] = desglose
            jugador["detalle_respuestas"] = detalle_respuestas
            ronda_perfecta = bool(self.categorias_activas) and all(
                detalle_respuestas[categoria]["puntos"] == 10
                for categoria in self.categorias_activas
            )
            if ronda_perfecta:
                jugador["bonus_ronda"] = 10
                jugador["rondas_perfectas"] += 1
                jugador["puntos_ronda"] += 10
            jugador["total"] += jugador["puntos_ronda"]
            jugador["historial"].append(jugador["puntos_ronda"])

        puntuaciones = {
            jugador["nombre"]: jugador["puntos_ronda"]
            for jugador in self.jugadores.values()
        }
        self.historial_global.append({
            "ronda": self.ronda_actual,
            "letra": self.letra_actual,
            "categorias": list(self.categorias_activas),
            "motivo_cierre": "stop" if self.quien_stop else "tiempo",
            "quien_stop": self.quien_stop,
            "stopper_id": next((pid for pid, player in self.jugadores.items() if player["nombre"] == self.quien_stop), None),
            "duracion_segundos": duracion_ronda_real,
            "puntuaciones": puntuaciones,
            "jugadores": [
                {
                    "id": j_id,
                    "nombre": jugador["nombre"],
                    "avatar": AVATARES.get(jugador.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                    "respuestas": dict(jugador["respuestas_ronda"]),
                    "resultados": {cat: dict(detalle) for cat, detalle in jugador["detalle_respuestas"].items()},
                    "puntos_obtenidos": jugador["puntos_ronda"],
                    "puntos_categorias": jugador["puntos_categorias"],
                    "bonus": jugador["bonus_ronda"],
                    "ronda_perfecta": jugador["bonus_ronda"] > 0,
                    "puntuacion_acumulada": jugador["total"],
                }
                for j_id, jugador in self.jugadores.items()
            ],
        })
        self._detalles_votacion_final = detalles_globales
        self.partida_terminada = self.ronda_actual >= self.rondas_totales

    def _clasificacion(self):
        return [
            {
                "id": jugador["id"],
                "nombre": jugador["nombre"],
                "avatar": AVATARES.get(jugador.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                "puntos": jugador["total"],
            }
            for jugador in sorted(
                self.jugadores.values(),
                key=lambda item: (-item["total"], item["nombre"].casefold(), item["id"]),
            )
        ]

    def _stopper_id(self) -> Optional[int]:
        return next(
            (jugador_id for jugador_id, jugador in self.jugadores.items()
             if jugador["nombre"] == self.quien_stop),
            None,
        )

    def _logros_jugador(self, jugador_id: int) -> List[Dict[str, str]]:
        jugador = self.jugadores.get(jugador_id)
        if not jugador:
            return []
        rondas = [
            item for item in self.historial_global
            for item in item.get("jugadores", [])
            if item.get("id") == jugador_id
        ]
        logros = []
        for ronda in self.historial_global:
            puntuaciones = ronda.get("puntuaciones", {})
            if puntuaciones and jugador["nombre"] in puntuaciones and puntuaciones[jugador["nombre"]] == max(puntuaciones.values()):
                logros.append({"id": "primera_victoria", "icono": "🏆", "nombre": "Primera victoria", "descripcion": "Ganaste al menos una ronda."})
                break
        if any(
            ronda.get("duracion_segundos", 999) <= 20
            and all(
                str(item.get("respuestas", {}).get(cat, "")).strip()
                for cat in ronda.get("categorias", [])
            )
            for ronda in self.historial_global
            for item in ronda.get("jugadores", [])
            if item.get("id") == jugador_id
        ):
            logros.append({"id": "respuesta_rapida", "icono": "⚡", "nombre": "Respuesta rápida", "descripcion": "Completaste todas las categorías en 20 segundos o menos."})
        consecutivas = 0
        max_consecutivas = 0
        for item in sorted(rondas, key=lambda x: x.get("ronda", 0)):
            if item.get("puntos_obtenidos", 0) > 0:
                consecutivas += 1
                max_consecutivas = max(max_consecutivas, consecutivas)
            else:
                consecutivas = 0
        if max_consecutivas >= 3:
            logros.append({"id": "racha_tres", "icono": "🔥", "nombre": "3 rondas consecutivas", "descripcion": "Conseguiste puntos en tres rondas seguidas."})
        estados_validos = {"valida_unica", "valida_repetida", "votada_unica", "votada_repetida"}
        if any(
            ronda.get("categorias")
            and any(
                item.get("id") == jugador_id
                and len(item.get("resultados", {})) >= len(ronda.get("categorias", []))
                and all(detalle.get("estado") in estados_validos for detalle in item.get("resultados", {}).values())
                for item in ronda.get("jugadores", [])
            )
            for ronda in self.historial_global
        ):
            logros.append({"id": "todas_validas", "icono": "🎯", "nombre": "Todas las respuestas válidas", "descripcion": "Completaste una ronda con todas tus respuestas válidas."})
        if jugador.get("cantidad_stop", 0) >= 1:
            max_stops = max((sum(1 for r in self.historial_global if r.get("stopper_id") == pid) for pid in self.jugadores), default=0)
            if jugador.get("cantidad_stop", 0) == max_stops:
                logros.append({"id": "rey_stop", "icono": "😂", "nombre": "Rey del STOP", "descripcion": "Eres quien más veces ha presionado STOP."})
        if (
            self.partida_terminada
            and jugador["total"] > 0
            and jugador["total"] == max((j["total"] for j in self.jugadores.values()), default=0)
        ):
            logros.append({"id": "campeon", "icono": "👑", "nombre": "Campeón", "descripcion": "Terminaste la partida en primer lugar."})
        if jugador["total"] >= UMBRAL_PUNTOS_EXPERTO:
            logros.append({"id": "experto", "icono": "🧠", "nombre": "Experto", "descripcion": f"Acumulaste {UMBRAL_PUNTOS_EXPERTO} puntos en la partida."})
        if any(
            ronda.get("stopper_id") == jugador_id
            and ronda.get("duracion_segundos", float("inf")) <= TIEMPO_STOP_RELAMPAGO
            for ronda in self.historial_global
        ):
            logros.append({"id": "stop_relampago", "icono": "🚀", "nombre": "STOP relámpago", "descripcion": f"Presionaste STOP en {TIEMPO_STOP_RELAMPAGO} segundos o menos."})
        return logros

    def _estadisticas_partida(self):
        clasificacion = self._clasificacion()
        lideres = []
        if clasificacion:
            maximo = clasificacion[0]["puntos"]
            lideres = [j["nombre"] for j in clasificacion if j["puntos"] == maximo]
        stats_jugadores = {
            jugador_id: {
                "id": jugador_id,
                "nombre": jugador["nombre"],
                "avatar": AVATARES.get(jugador.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                "puntos_totales": jugador["total"],
                "puntos_por_ronda": [],
                "rondas_ganadas": 0,
                "mejor_ronda": None,
                "respuestas_correctas": 0,
                "respuestas_incorrectas": 0,
                "respuestas_repetidas": 0,
                "validadas_por_votacion": 0,
                "rechazadas_por_votacion": 0,
                "cantidad_stop": 0,
                "rondas_perfectas": 0,
                "respuestas_enviadas": 0,
                "respuestas_posibles": 0,
                "rondas_participadas": 0,
                "logros": [],
            }
            for jugador_id, jugador in self.jugadores.items()
        }
        general = {
            "respuestas_totales": 0,
            "respuestas_validas": 0,
            "respuestas_invalidas": 0,
            "respuestas_validadas_votacion": 0,
            "respuestas_rechazadas_votacion": 0,
            "cantidad_stop": 0,
            "rondas_perfectas": 0,
            "mejor_jugador": lideres[0] if lideres else "—",
            "mayor_puntuacion": clasificacion[0]["puntos"] if clasificacion else 0,
        }
        puntos_distribuidos = 0
        for ronda in self.historial_global:
            hubo_ronda_perfecta = False
            if ronda.get("stopper_id") in stats_jugadores:
                stats_jugadores[ronda["stopper_id"]]["cantidad_stop"] += 1
            if ronda.get("quien_stop"):
                general["cantidad_stop"] += 1
            jugadores_ronda = ronda.get("jugadores", [])
            maximo_ronda = max(
                (item.get("puntos_obtenidos", 0) for item in jugadores_ronda),
                default=None,
            )
            for item in jugadores_ronda:
                jugador_stats = stats_jugadores.get(item.get("id"))
                if jugador_stats is None:
                    jugador_stats = {
                        "id": item.get("id"), "nombre": item.get("nombre", ""),
                        "avatar": item.get("avatar", AVATARES[AVATAR_PREDETERMINADO]),
                        "puntos_totales": item.get("puntuacion_acumulada", 0), "puntos_por_ronda": [],
                        "rondas_ganadas": 0, "mejor_ronda": None,
                        "respuestas_correctas": 0, "respuestas_incorrectas": 0,
                        "respuestas_repetidas": 0, "validadas_por_votacion": 0,
                        "rechazadas_por_votacion": 0, "cantidad_stop": 0,
                        "rondas_perfectas": 0, "respuestas_enviadas": 0,
                        "respuestas_posibles": 0, "rondas_participadas": 0,
                    }
                    stats_jugadores[item.get("id")] = jugador_stats
                jugador_stats["puntos_totales"] = item.get("puntuacion_acumulada", jugador_stats["puntos_totales"])
                jugador_stats["puntos_por_ronda"].append({
                    "ronda": ronda.get("ronda"),
                    "puntos_categorias": item.get("puntos_categorias", item.get("puntos_obtenidos", 0)),
                    "bonus": item.get("bonus", 0),
                    "total": item.get("puntos_obtenidos", 0),
                })
                puntos_ronda = item.get("puntos_obtenidos", 0)
                if maximo_ronda is not None and puntos_ronda == maximo_ronda:
                    jugador_stats["rondas_ganadas"] += 1
                if jugador_stats["mejor_ronda"] is None or puntos_ronda > jugador_stats["mejor_ronda"]["puntos"]:
                    jugador_stats["mejor_ronda"] = {
                        "ronda": ronda.get("ronda"),
                        "puntos": puntos_ronda,
                    }
                enviados_esta_ronda = 0
                if item.get("ronda_perfecta"):
                    jugador_stats["rondas_perfectas"] += 1
                    hubo_ronda_perfecta = True
                for categoria, detalle in item.get("resultados", {}).items():
                    respuesta = item.get("respuestas", {}).get(categoria, "")
                    if not respuesta:
                        continue
                    enviados_esta_ronda += 1
                    general["respuestas_totales"] += 1
                    jugador_stats["respuestas_enviadas"] += 1
                    estado = detalle.get("estado")
                    if estado in {"valida_unica", "valida_repetida", "votada_unica", "votada_repetida"}:
                        general["respuestas_validas"] += 1
                        jugador_stats["respuestas_correctas"] += 1
                    else:
                        general["respuestas_invalidas"] += 1
                        jugador_stats["respuestas_incorrectas"] += 1
                    if estado in {"valida_repetida", "votada_repetida"}:
                        jugador_stats["respuestas_repetidas"] += 1
                    if estado in {"votada_unica", "votada_repetida"}:
                        general["respuestas_validadas_votacion"] += 1
                        jugador_stats["validadas_por_votacion"] += 1
                    if estado == "votacion_rechazada":
                        general["respuestas_rechazadas_votacion"] += 1
                        jugador_stats["rechazadas_por_votacion"] += 1
                categorias_ronda = ronda.get("categorias", list(item.get("respuestas", {})))
                posibles_esta_ronda = len(categorias_ronda)
                jugador_stats["respuestas_posibles"] += posibles_esta_ronda
                if enviados_esta_ronda:
                    jugador_stats["rondas_participadas"] += 1
                puntos_distribuidos += item.get("puntos_obtenidos", 0)
            if hubo_ronda_perfecta:
                general["rondas_perfectas"] += 1
        for stats in stats_jugadores.values():
            posibles = stats["respuestas_posibles"]
            stats["participacion"] = round(100 * stats["respuestas_enviadas"] / posibles, 1) if posibles else 0.0
            stats["participacion_porcentaje"] = stats["participacion"]
            stats["logros"] = self._logros_jugador(stats["id"])
            rondas_jugadas = len(stats["puntos_por_ronda"])
            stats["promedio_puntos_por_ronda"] = round(
                sum(ronda["total"] for ronda in stats["puntos_por_ronda"]) / rondas_jugadas,
                1,
            ) if rondas_jugadas else 0.0
            stats["victorias"] = int(
                self.partida_terminada
                and stats["puntos_totales"] == (clasificacion[0]["puntos"] if clasificacion else 0)
                and stats["puntos_totales"] > 0
            )
        candidatos_rey = [stats for stats in stats_jugadores.values() if stats["cantidad_stop"] > 0]
        rey_del_stop = min(
            candidatos_rey,
            key=lambda stats: (
                -stats["cantidad_stop"],
                -stats["puntos_totales"],
                stats["nombre"].casefold(),
                stats["id"],
            ),
            default=None,
        )
        return {
            "rondas_completadas": len(self.historial_global),
            "jugadores": len(self.jugadores),
            "espectadores": len(self.espectadores_registrados),
            **general,
            "rey_del_stop": (
                {
                    "id": rey_del_stop["id"],
                    "nombre": rey_del_stop["nombre"],
                    "avatar": rey_del_stop["avatar"],
                    "cantidad_stop": rey_del_stop["cantidad_stop"],
                }
                if rey_del_stop else None
            ),
            "letras_utilizadas": [ronda["letra"] for ronda in self.historial_global],
            "puntos_distribuidos": puntos_distribuidos,
            "ganadores": lideres,
            "por_jugador": list(stats_jugadores.values()),
        }

    async def iniciar_nueva_partida(self, jugador_id: int):
        async with self.lock:
            if jugador_id != self.anfitrion_id:
                return False, "Solamente el anfitrión puede iniciar una nueva partida."
            if self.estado_juego != "RESULTADOS" or not self.partida_terminada:
                return False, "La partida actual todavía no ha terminado."
            self.ronda_actual = 0
            self.letra_actual = ""
            self.quien_stop = ""
            self.historial_global = []
            self.espectadores_registrados = set()
            self.votaciones = {}
            self.letras_utilizadas = []
            self.letras_disponibles = list(LETRAS_DISPONIBLES)
            self.partida_terminada = False
            self.rondas_totales = 4
            self.categorias_activas = list(CATEGORIAS)
            self.vence_en = 0.0
            self.vence_en_monotonic = 0.0
            self.ronda_iniciada_monotonic = 0.0
            self._detalles_votacion_final = []
            for jugador in self.jugadores.values():
                jugador["total"] = 0
                jugador["historial"] = []
                jugador["respuestas_ronda"] = {cat: "" for cat in self.categorias_activas}
                jugador["puntos_ronda"] = 0
                jugador["puntos_categorias"] = 0
                jugador["bonus_ronda"] = 0
                jugador["desglose_ronda"] = {cat: 0 for cat in self.categorias_activas}
                jugador["detalle_respuestas"] = {cat: {} for cat in self.categorias_activas}
                jugador["rondas_perfectas"] = 0
                jugador["cantidad_stop"] = 0
            self.estado_juego = "SALA"
            self._sincronizar_anfitrion()
            return True, None

    def serializar_sala(self):
        return {
            "tipo": "sala",
            "jugadores": [
                {
                    "id": d["id"],
                    "nombre": d["nombre"],
                    "avatar": AVATARES.get(d.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                    "es_anfitrion": d["es_anfitrion"],
                    "total": d["total"],
                    "conectado": d.get("ws") is not None,
                    "estado_presencia": self._estado_presencia(d),
                    "emocion": self._emocion_por_presencia(d),
                }
                for d in self.jugadores.values()
            ],
            "anfitrion_id": self.anfitrion_id,
            "estado": self.estado_juego,
            "configuracion": {"rondas": self.rondas_totales, "categorias": list(self.categorias_activas), "min_categorias": 3},
        }

    def serializar_ronda(self):
        jugadores = []
        for jugador in self.jugadores.values():
            estado_respuesta = (
                "completó"
                if all(
                    str(jugador["respuestas_ronda"].get(categoria, "")).strip()
                    for categoria in self.categorias_activas
                )
                else "escribiendo"
            )
            jugadores.append({
                "id": jugador["id"],
                "nombre": jugador["nombre"],
                "avatar": AVATARES.get(
                    jugador.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]
                ),
                "es_anfitrion": jugador["es_anfitrion"],
                "total": jugador["total"],
                "perfil": self._perfil_jugador(jugador["id"]),
                "conectado": jugador.get("ws") is not None,
                "estado_presencia": self._estado_presencia(jugador, estado_respuesta),
                "emocion": self._emocion_por_presencia(jugador, estado_respuesta),
                "estado": estado_respuesta,
            })
        return {
            "tipo": "ronda",
            "ronda": self.ronda_actual,
            "letra": self.letra_actual,
            "vence_en": self.vence_en,
            "servidor_ahora": time.time(),
            "anfitrion_id": self.anfitrion_id,
            "categorias": list(self.categorias_activas),
            "jugadores": jugadores,
            "espectadores": [
                {
                    "id": d["id"],
                    "nombre": d["nombre"],
                    "avatar": AVATARES.get(d.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                    "estado": "observando",
                    "emocion": self._emocion_por_presencia(d),
                    "estado_presencia": (
                        "👀 Espectador" if d.get("ws") is not None else self._estado_presencia(d)
                    ),
                }
                for d in self.espectadores.values()
            ],
        }

    def serializar_votacion_para(self, jugador_id: int, es_espectador: bool = False):
        pendientes = []
        for candidato in self.votaciones.values():
            cerrada = "resultado" in candidato
            mi_voto = True if jugador_id in candidato["votos_si"] else False if jugador_id in candidato["votos_no"] else None
            ya_voto = mi_voto is not None
            puede_votar = not es_espectador and jugador_id in candidato["votantes"] and not cerrada and not ya_voto
            if (not es_espectador and jugador_id not in candidato["votantes"]
                    and jugador_id not in candidato["autores"] and not ya_voto):
                continue
            pendientes.append({
                "clave": candidato["clave"],
                "categoria": candidato["categoria"],
                "respuesta": candidato["respuesta"],
                "autores": [self.jugadores[a]["nombre"] for a in candidato["autores"] if a in self.jugadores],
                "puede_votar": puede_votar,
                "votos_si": len(candidato["votos_si"]),
                "votos_no": len(candidato["votos_no"]),
                "total_votantes": len(candidato["votantes"]),
                "cerrada": cerrada,
                "aprobada": candidato.get("resultado"),
                "ya_voto": ya_voto,
                "mi_voto": mi_voto,
            })
        jugadores_votacion = []
        for jugador_id_actual, jugador in self.jugadores.items():
            conectada = jugador.get("ws") is not None
            voto_si = any(jugador_id_actual in c["votos_si"] for c in self.votaciones.values())
            voto_no = any(jugador_id_actual in c["votos_no"] for c in self.votaciones.values())
            es_autor = any(jugador_id_actual in c["autores"] for c in self.votaciones.values())
            pendiente = any(
                "resultado" not in c and jugador_id_actual in c["votantes"]
                and jugador_id_actual not in c["votos_si"] and jugador_id_actual not in c["votos_no"]
                for c in self.votaciones.values()
            )
            estado = "Desconectado" if not conectada else (
                "Votó SÍ" if voto_si else "Votó NO" if voto_no else
                "Respuesta por validar" if es_autor else "Pendiente de votar" if pendiente else "En votación"
            )
            jugadores_votacion.append({
                "id": jugador_id_actual,
                "nombre": jugador["nombre"],
                "avatar": AVATARES.get(jugador.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                "es_anfitrion": jugador["es_anfitrion"],
                "conectado": conectada,
                "estado_presencia": self._estado_presencia(jugador),
                "emocion": (
                    "😱" if self.quien_stop == jugador["nombre"]
                    else self._emocion_por_presencia(jugador)
                ),
                "total": jugador["total"],
                "estado": estado,
            })
        return {
            "tipo": "votacion",
            "ronda": self.ronda_actual,
            "letra": self.letra_actual,
            "quien_stop": self.quien_stop,
            "stopper_id": self._stopper_id(),
            "motivo_cierre": "stop" if self.quien_stop else "tiempo",
            "jugadores": jugadores_votacion,
            "espectadores": [
                {
                    "id": d["id"],
                    "nombre": d["nombre"],
                    "avatar": AVATARES.get(d.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                    "estado": "observando",
                    "emocion": self._emocion_por_presencia(d),
                    "estado_presencia": (
                        "👀 Espectador" if d.get("ws") is not None else self._estado_presencia(d)
                    ),
                }
                for d in self.espectadores.values()
            ],
            "candidatos": pendientes,
        }

    def serializar_estado_para(self, sesion_id: int, es_espectador: bool = False):
        if self.estado_juego == "SALA":
            mensaje = self.serializar_sala()
        elif self.estado_juego == "JUEGO":
            mensaje = self.serializar_ronda()
            if not es_espectador and sesion_id in self.jugadores:
                mensaje["mis_respuestas"] = dict(self.jugadores[sesion_id]["respuestas_ronda"])
        elif self.estado_juego == "VOTACION":
            mensaje = self.serializar_votacion_para(sesion_id, es_espectador)
        else:
            mensaje = self.serializar_resultados()
        mensaje["espectador"] = es_espectador
        return mensaje

    def _perfil_jugador(self, jugador_id: int) -> Dict[str, Any]:
        jugador = self.jugadores.get(jugador_id)
        if not jugador:
            return {"nombre": "", "victorias": 0, "puntos": 0, "rondas_ganadas": 0, "logros": []}
        victorias = 0
        rondas_ganadas = 0
        for ronda in self.historial_global:
            puntuaciones = ronda.get("puntuaciones", {})
            if not puntuaciones or jugador["nombre"] not in puntuaciones:
                continue
            maximo = max(puntuaciones.values())
            if puntuaciones[jugador["nombre"]] == maximo:
                victorias += 1
                rondas_ganadas += 1
        max_total = max((j["total"] for j in self.jugadores.values()), default=0)
        victoria_partida = 1 if self.partida_terminada and jugador["total"] == max_total and max_total > 0 else 0
        return {
            "nombre": jugador["nombre"],
            "victorias": victoria_partida,
            "puntos": jugador["total"],
            "rondas_ganadas": rondas_ganadas,
            "logros": self._logros_jugador(jugador_id),
            "stops": jugador.get("cantidad_stop", 0),
        }

    def serializar_resultados(self):
        resultados = []
        maximo_ronda = max(
            (jugador["puntos_ronda"] for jugador in self.jugadores.values()),
            default=0,
        )
        maximo_total = max((jugador["total"] for jugador in self.jugadores.values()), default=0)
        for d in self.jugadores.values():
            if self.partida_terminada:
                emocion = "🏆" if d["total"] == maximo_total and maximo_total > 0 else "😭"
            elif d.get("bonus_ronda", 0) > 0:
                emocion = "🔥"
            elif d["puntos_ronda"] == maximo_ronda and maximo_ronda > 0:
                emocion = "🥳"
            else:
                emocion = "😭"
            resultados.append({
                "id": d["id"],
                "nombre": d["nombre"],
                "avatar": AVATARES.get(d.get("avatar"), AVATARES[AVATAR_PREDETERMINADO]),
                "emocion": emocion,
                "es_anfitrion": d["es_anfitrion"],
                "conectado": d.get("ws") is not None,
                "estado_presencia": self._estado_presencia(d),
                "respuestas": d["respuestas_ronda"],
                "puntos_ronda": d["puntos_ronda"],
                "puntos_categorias": d.get("puntos_categorias", d["puntos_ronda"]),
                "bonus_ronda": d.get("bonus_ronda", 0),
                "desglose": d["desglose_ronda"],
                "detalle_respuestas": d["detalle_respuestas"],
                "total": d["total"],
                "historial": d["historial"],
                "perfil": self._perfil_jugador(d["id"]),
            })
        return {
            "tipo": "resultados",
            "ronda": self.ronda_actual,
            "categorias": list(self.categorias_activas),
            "letras_utilizadas": list(self.letras_utilizadas),
            "letra": self.letra_actual,
            "quien_stop": self.quien_stop,
            "stopper_id": self._stopper_id(),
            "motivo_cierre": "stop" if self.quien_stop else "tiempo",
            "jugadores": resultados,
            "historial_global": self.historial_global,
            "clasificacion": self._clasificacion(),
            "rondas_totales": self.rondas_totales,
            "partida_terminada": self.partida_terminada,
            "estadisticas": self._estadisticas_partida() if self.partida_terminada else None,
            "votaciones_finales": getattr(self, "_detalles_votacion_final", []),
            "anfitrion_id": self.anfitrion_id,
            "perfiles": {str(j["id"]): self._perfil_jugador(j["id"]) for j in self.jugadores.values()},
        }
