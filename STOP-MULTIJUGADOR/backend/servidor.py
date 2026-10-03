import asyncio
import random
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from backend.validaciones import evaluar_palabra, normalizar

CATEGORIAS = ["nombre", "apellido", "ciudad", "fruta", "animal", "cosa"]
LETRAS_DISPONIBLES = "ABCDEFGLMPRSTV"


class GestorJuego:
    def __init__(self, duracion_ronda: int = 90):
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
        self.duracion_ronda = duracion_ronda
        self.vence_en = 0.0
        self.vence_en_monotonic = 0.0

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

    def _crear_registro_jugador(self, jugador_id: int, nombre: str, ws, token: str, es_anfitrion: bool):
        return {
            "id": jugador_id,
            "nombre": nombre,
            "ws": ws,
            "token": token,
            "es_anfitrion": es_anfitrion,
            "respuestas_ronda": {cat: "" for cat in self.categorias_activas},
            "puntos_ronda": 0,
            "puntos_categorias": 0,
            "bonus_ronda": 0,
            "desglose_ronda": {cat: 0 for cat in self.categorias_activas},
            "detalle_respuestas": {cat: {} for cat in self.categorias_activas},
            "total": 0,
            "historial": [],
        }

    async def conectar_sesion(self, ws: WebSocket, nombre: str, token: Optional[str] = None):
        async with self.lock:
            nombre_limpio = nombre.strip()
            if not nombre_limpio:
                return None, "El nombre es obligatorio."

            sesion, era_espectador = self._buscar_sesion(token)
            if sesion:
                jugador_id, datos = sesion
                anterior = datos.get("ws")
                datos["ws"] = ws
                if not era_espectador and anterior is None:
                    self._reactivar_votante(jugador_id)
                return {
                    "id": jugador_id,
                    "token": datos["token"],
                    "nombre": datos["nombre"],
                    "es_espectador": era_espectador,
                    "es_anfitrion": not era_espectador and jugador_id == self.anfitrion_id,
                    "reconectado": True,
                    "socket_anterior": anterior if anterior is not ws else None,
                }, None

            for data in list(self.jugadores.values()) + list(self.espectadores.values()):
                if data["nombre"].casefold() == nombre_limpio.casefold():
                    return None, f"Ya existe un jugador con el nombre '{nombre_limpio}'."

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
                }
            else:
                self.jugadores[j_id] = self._crear_registro_jugador(
                    j_id, nombre_limpio, ws, nuevo_token, es_anfitrion
                )
                self._sincronizar_anfitrion()
            return {
                "id": j_id,
                "token": nuevo_token,
                "nombre": nombre_limpio,
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
                self._actualizar_votaciones_por_desconexion(j_id)
                if self.anfitrion_id == j_id:
                    conectados = [pid for pid, p in self.jugadores.items() if p.get("ws") is not None]
                    if conectados:
                        self.anfitrion_id = conectados[0]
                        self._sincronizar_anfitrion()
                return jugador["nombre"]

            for espectador in self.espectadores.values():
                if espectador.get("ws") == ws:
                    espectador["ws"] = None
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
                jugador_id, espectador["nombre"], espectador.get("ws"), espectador["token"], es_anfitrion
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
        completadas = [
            clave for clave, candidato in self.votaciones.items()
            if "resultado" in candidato
        ]
        for clave in completadas:
            # Se conserva temporalmente el resultado para calcular los puntos.
            pass

        # Solo cerramos la fase cuando todas las votaciones ya tienen resultado.
        if self.votaciones and all("resultado" in c for c in self.votaciones.values()):
            self.estado_juego = "RESULTADOS"
            self._calcular_resultados()
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
            "puntuaciones": puntuaciones,
            "jugadores": [
                {
                    "id": j_id,
                    "nombre": jugador["nombre"],
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
            {"id": jugador["id"], "nombre": jugador["nombre"], "puntos": jugador["total"]}
            for jugador in sorted(
                self.jugadores.values(),
                key=lambda item: (-item["total"], item["nombre"].casefold(), item["id"]),
            )
        ]

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
                "puntos_totales": jugador["total"],
                "puntos_por_ronda": [],
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
        }
        puntos_distribuidos = 0
        for ronda in self.historial_global:
            hubo_ronda_perfecta = False
            if ronda.get("stopper_id") in stats_jugadores:
                stats_jugadores[ronda["stopper_id"]]["cantidad_stop"] += 1
            if ronda.get("quien_stop"):
                general["cantidad_stop"] += 1
            for item in ronda.get("jugadores", []):
                jugador_stats = stats_jugadores.get(item.get("id"))
                if jugador_stats is None:
                    jugador_stats = {
                        "id": item.get("id"), "nombre": item.get("nombre", ""),
                        "puntos_totales": item.get("puntuacion_acumulada", 0), "puntos_por_ronda": [],
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
        return {
            "rondas_completadas": len(self.historial_global),
            "jugadores": len(self.jugadores),
            "espectadores": len(self.espectadores_registrados),
            **general,
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
                    "es_anfitrion": d["es_anfitrion"],
                    "total": d["total"],
                    "conectado": d.get("ws") is not None,
                }
                for d in self.jugadores.values()
            ],
            "anfitrion_id": self.anfitrion_id,
            "estado": self.estado_juego,
            "configuracion": {"rondas": self.rondas_totales, "categorias": list(self.categorias_activas), "min_categorias": 3},
        }

    def serializar_ronda(self):
        return {
            "tipo": "ronda",
            "ronda": self.ronda_actual,
            "letra": self.letra_actual,
            "vence_en": self.vence_en,
            "servidor_ahora": time.time(),
            "anfitrion_id": self.anfitrion_id,
            "categorias": list(self.categorias_activas),
            "jugadores": [
                {
                    "id": d["id"],
                    "nombre": d["nombre"],
                    "es_anfitrion": d["es_anfitrion"],
                    "total": d["total"],
                    "conectado": d.get("ws") is not None,
                    "estado": "jugando",
                }
                for d in self.jugadores.values()
            ],
            "espectadores": [
                {"id": d["id"], "nombre": d["nombre"], "estado": "observando"}
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
                "es_anfitrion": jugador["es_anfitrion"],
                "conectado": conectada,
                "total": jugador["total"],
                "estado": estado,
            })
        return {
            "tipo": "votacion",
            "ronda": self.ronda_actual,
            "letra": self.letra_actual,
            "quien_stop": self.quien_stop,
            "motivo_cierre": "stop" if self.quien_stop else "tiempo",
            "jugadores": jugadores_votacion,
            "espectadores": [
                {"id": d["id"], "nombre": d["nombre"], "estado": "observando"}
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

    def serializar_resultados(self):
        resultados = []
        for d in self.jugadores.values():
            resultados.append({
                "id": d["id"],
                "nombre": d["nombre"],
                "es_anfitrion": d["es_anfitrion"],
                "conectado": d.get("ws") is not None,
                "respuestas": d["respuestas_ronda"],
                "puntos_ronda": d["puntos_ronda"],
                "puntos_categorias": d.get("puntos_categorias", d["puntos_ronda"]),
                "bonus_ronda": d.get("bonus_ronda", 0),
                "desglose": d["desglose_ronda"],
                "detalle_respuestas": d["detalle_respuestas"],
                "total": d["total"],
                "historial": d["historial"],
            })
        return {
            "tipo": "resultados",
            "ronda": self.ronda_actual,
            "categorias": list(self.categorias_activas),
            "letras_utilizadas": list(self.letras_utilizadas),
            "letra": self.letra_actual,
            "quien_stop": self.quien_stop,
            "motivo_cierre": "stop" if self.quien_stop else "tiempo",
            "jugadores": resultados,
            "historial_global": self.historial_global,
            "clasificacion": self._clasificacion(),
            "rondas_totales": self.rondas_totales,
            "partida_terminada": self.partida_terminada,
            "estadisticas": self._estadisticas_partida() if self.partida_terminada else None,
            "votaciones_finales": getattr(self, "_detalles_votacion_final", []),
            "anfitrion_id": self.anfitrion_id,
        }
