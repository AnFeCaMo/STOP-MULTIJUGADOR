import asyncio
import json

from backend import web_server
from backend.servidor import GestorJuego


class FakeWebSocket:
    def __init__(self):
        self.enviados = []

    async def send_text(self, contenido):
        await asyncio.sleep(0)
        self.enviados.append(contenido)


def test_broadcast_serializa_por_rol_y_envia_a_todos_los_jugadores():
    async def caso():
        gestor = GestorJuego()
        sockets = [FakeWebSocket() for _ in range(3)]
        await gestor.conectar_sesion(sockets[0], "Ana")
        await gestor.conectar_sesion(sockets[1], "Luis")
        gestor.estado_juego = "JUEGO"
        await gestor.conectar_sesion(sockets[2], "Eva")

        web_server.gestor_contexto.set(gestor)
        web_server.codigo_sala_contexto.set("TEST")
        await web_server.broadcast({"tipo": "prueba", "valor": 42})

        mensajes = [json.loads(socket.enviados[0]) for socket in sockets]
        assert all(mensaje["tipo"] == "prueba" for mensaje in mensajes)
        assert all(mensaje["valor"] == 42 for mensaje in mensajes)
        assert all(mensaje["codigo_sala"] == "TEST" for mensaje in mensajes)
        assert [mensaje["espectador"] for mensaje in mensajes] == [False, False, True]

        for socket in sockets:
            socket.enviados.clear()
        await web_server.broadcast_votacion()
        assert all(json.loads(socket.enviados[0])["tipo"] == "votacion" for socket in sockets)

    asyncio.run(caso())
