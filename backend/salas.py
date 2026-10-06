import asyncio
import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from backend.servidor import GestorJuego

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEFAULT_ROOM = "DEMO"
ROOM_IDLE_SECONDS = 15 * 60
RECONNECT_WINDOW_SECONDS = 10 * 60


def normalizar_codigo(codigo: str) -> str:
    return "".join(ch for ch in str(codigo or "").upper() if ch in ROOM_ALPHABET)[:8]


def generar_codigo(existentes) -> str:
    for _ in range(100):
        codigo = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(4))
        if codigo not in existentes:
            return codigo
    raise RuntimeError("No fue posible generar un código de sala único.")


@dataclass
class Sala:
    codigo: str
    gestor: GestorJuego = field(default_factory=GestorJuego)
    creada_en: float = field(default_factory=time.time)
    ultima_actividad: float = field(default_factory=time.time)
    abandonada_desde: Optional[float] = None

    def tocar(self):
        self.ultima_actividad = time.time()
        if self.conectados():
            self.abandonada_desde = None

    def conectados(self) -> int:
        return len(self.gestor.sesiones_conectadas())

    def recuperable(self) -> bool:
        if self.conectados():
            return True
        if self.abandonada_desde is None:
            return True
        return time.time() - self.abandonada_desde < RECONNECT_WINDOW_SECONDS

    def marcar_desconexion(self):
        self.ultima_actividad = time.time()
        if self.conectados() == 0 and self.abandonada_desde is None:
            self.abandonada_desde = time.time()


class GestorSalas:
    def __init__(self):
        self.salas: Dict[str, Sala] = {}
        self.lock = asyncio.Lock()

    async def obtener_o_crear(self, codigo: Optional[str] = None):
        async with self.lock:
            codigo = normalizar_codigo(codigo or "")
            if not codigo:
                codigo = generar_codigo(self.salas)
            sala = self.salas.get(codigo)
            if sala is None:
                sala = Sala(codigo=codigo)
                self.salas[codigo] = sala
            sala.tocar()
            return sala

    async def obtener(self, codigo: str):
        async with self.lock:
            sala = self.salas.get(normalizar_codigo(codigo))
            if sala:
                sala.tocar()
            return sala

    async def limpiar(self):
        ahora = time.time()
        eliminadas = []
        async with self.lock:
            for codigo, sala in list(self.salas.items()):
                if sala.conectados():
                    continue
                if sala.abandonada_desde is None:
                    sala.abandonada_desde = ahora
                limite = RECONNECT_WINDOW_SECONDS if not sala.gestor.partida_terminada else ROOM_IDLE_SECONDS
                if ahora - sala.abandonada_desde >= limite:
                    eliminadas.append(codigo)
                    del self.salas[codigo]
        return eliminadas

    async def resumen(self):
        async with self.lock:
            return {
                codigo: {
                    "conectados": sala.conectados(),
                    "estado": sala.gestor.estado_juego,
                    "ronda": sala.gestor.ronda_actual,
                    "recuperable": sala.recuperable(),
                }
                for codigo, sala in self.salas.items()
            }
