import asyncio

from backend import web_server
from backend.servidor import CATEGORIAS, LETRAS_DISPONIBLES, GestorJuego


class FakeWebSocket:
    async def send_text(self, _):
        pass


def test_sala_sigue_viva_mientras_un_jugador_permanezca_conectado():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.04)
        ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
        a, _ = await gestor.conectar_sesion(ws_a, "Andres")
        b, _ = await gestor.conectar_sesion(ws_b, "Jose")
        await gestor.iniciar_ronda(a["id"])

        await gestor.desconectar(ws_a)
        assert gestor._tarea_reinicio_sala is None
        await asyncio.sleep(0.06)
        assert gestor.ronda_actual == 1
        assert gestor.jugadores[b["id"]]["ws"] is ws_b

        espectador, error = await gestor.conectar_sesion(FakeWebSocket(), "Eva")
        assert error is None and espectador["es_espectador"]

    asyncio.run(caso())


def test_reconexion_con_token_en_ventana_conserva_partida():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.12)
        ws = FakeWebSocket()
        sesion, _ = await gestor.conectar_sesion(ws, "Andres")
        await gestor.iniciar_ronda(sesion["id"])
        await gestor.desconectar(ws)
        await asyncio.sleep(0.03)

        nueva_conexion, error = await gestor.conectar_sesion(
            FakeWebSocket(), "Andres", sesion["token"]
        )
        assert error is None and nueva_conexion["reconectado"]
        await asyncio.sleep(0.14)
        assert nueva_conexion["id"] in gestor.jugadores
        assert gestor.ronda_actual == 1

    asyncio.run(caso())


def test_expiracion_limpia_estado_y_token_antiguo_crea_partida_nueva():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.04)
        sockets = [FakeWebSocket(), FakeWebSocket()]
        a, _ = await gestor.conectar_sesion(sockets[0], "Andres")
        b, _ = await gestor.conectar_sesion(sockets[1], "Jose")
        await gestor.iniciar_ronda(a["id"])
        gestor.jugadores[a["id"]]["respuestas_ronda"][CATEGORIAS[0]] = "Respuesta"
        gestor.historial_global.append({"anterior": True})
        gestor.votaciones["temporal"] = {
            "votantes": [], "autores": [], "votos_si": [], "votos_no": []
        }
        gestor._detalles_votacion_final = [{"anterior": True}]

        await gestor.desconectar(sockets[0])
        await gestor.desconectar(sockets[1])
        await asyncio.sleep(0.07)

        assert gestor.jugadores == {}
        assert gestor.espectadores == {}
        assert gestor.espectadores_registrados == set()
        assert gestor.id_counter == 1
        assert gestor.anfitrion_id is None
        assert gestor.estado_juego == "SALA"
        assert gestor.letra_actual == ""
        assert gestor.ronda_actual == 0 and gestor.rondas_totales == 4
        assert gestor.categorias_activas == CATEGORIAS
        assert gestor.letras_disponibles == list(LETRAS_DISPONIBLES)
        assert gestor.letras_utilizadas == []
        assert not gestor.partida_terminada and gestor.quien_stop == ""
        assert gestor.historial_global == [] and gestor.votaciones == {}
        assert gestor._detalles_votacion_final == []
        assert gestor.vence_en == 0 and gestor.vence_en_monotonic == 0
        assert gestor.ronda_iniciada_monotonic == 0

        nueva, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres", a["token"])
        assert error is None
        assert not nueva["reconectado"] and nueva["es_anfitrion"]
        assert nueva["id"] == 1 and nueva["token"] != a["token"]

    asyncio.run(caso())


def test_token_desconocido_no_conserva_ni_extiende_sala_abandonada():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.1)
        ws = FakeWebSocket()
        anterior, _ = await gestor.conectar_sesion(ws, "Andres")
        await gestor.iniciar_ronda(anterior["id"])
        await gestor.desconectar(ws)

        nueva, error = await gestor.conectar_sesion(
            FakeWebSocket(), "Carlos", "token-invalido"
        )
        assert error is None and not nueva["reconectado"]
        assert nueva["id"] == 1 and nueva["es_anfitrion"]
        assert gestor.estado_juego == "SALA" and gestor.ronda_actual == 0
        assert gestor.jugadores[1]["nombre"] == "Carlos"
        assert gestor.jugadores[1]["token"] != anterior["token"]
        assert gestor._tarea_reinicio_sala is None

    asyncio.run(caso())


def test_limpieza_de_sala_predeterminada_cancela_temporizador_web():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.02)
        sesion, _ = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        await gestor.desconectar(gestor.jugadores[sesion["id"]]["ws"])
        ronda = asyncio.create_task(asyncio.sleep(10))
        web_server.temporizadores_ronda[id(gestor)] = ronda

        limpieza = asyncio.create_task(web_server.limpiar_sala_abandonada("7K4P", gestor))
        web_server.tareas_limpieza_sala["7K4P"] = limpieza
        await limpieza

        assert ronda.cancelled()
        assert id(gestor) not in web_server.temporizadores_ronda
        assert "7K4P" not in web_server.tareas_limpieza_sala
        assert gestor.jugadores == {}

    asyncio.run(caso())
