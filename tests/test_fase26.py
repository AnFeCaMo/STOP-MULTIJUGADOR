import asyncio

from backend import web_server
from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_dos_salones_conservan_independientemente_estado_y_temporizador(monkeypatch):
    async def caso():
        codigo_a, gestor_a, error_a = web_server.seleccionar_sala("crear")
        codigo_b, gestor_b, error_b = web_server.seleccionar_sala("crear")
        assert error_a is None and error_b is None
        assert codigo_a != codigo_b

        jugador_a, error = await gestor_a.conectar_sesion(FakeWebSocket(), "Ana")
        assert error is None
        jugador_b, error = await gestor_b.conectar_sesion(FakeWebSocket(), "Ana")
        assert error is None
        id_a, id_b = jugador_a["id"], jugador_b["id"]
        assert gestor_a.anfitrion_id == id_a
        assert gestor_b.anfitrion_id == id_b

        gestor_a.duracion_ronda = 0.03
        gestor_b.duracion_ronda = 0.2
        assert (await gestor_a.iniciar_ronda(id_a)) == (True, None)
        assert (await gestor_b.iniciar_ronda(id_b)) == (True, None)
        gestor_a.letra_actual = "A"
        gestor_b.letra_actual = "B"
        await gestor_a.actualizar_respuestas(id_a, {"nombre": "Ana"})
        await gestor_b.actualizar_respuestas(id_b, {"nombre": "Beatriz"})
        gestor_a.jugadores[id_a]["total"] = 30
        gestor_b.jugadores[id_b]["total"] = 80
        gestor_a.votaciones = {"A": {"votos_si": {id_a}, "votos_no": set()}}
        gestor_b.votaciones = {"B": {"votos_si": set(), "votos_no": {id_b}}}
        gestor_a.historial_global.append({"ronda": 1, "letra": "A", "puntuaciones": {"Ana": 30}})
        gestor_b.historial_global.append({"ronda": 1, "letra": "B", "puntuaciones": {"Ana": 80}})

        async def no_broadcast():
            return None

        monkeypatch.setattr(web_server, "broadcast_fase_cerrada", no_broadcast)
        web_server.gestor_contexto.set(gestor_a)
        web_server.codigo_sala_contexto.set(codigo_a)
        temporizador_a = asyncio.create_task(web_server.esperar_fin_ronda(1))
        web_server.gestor_contexto.set(gestor_b)
        web_server.codigo_sala_contexto.set(codigo_b)
        temporizador_b = asyncio.create_task(web_server.esperar_fin_ronda(1))

        assert gestor_a.votaciones["A"]["votos_si"] == {id_a}
        assert gestor_b.votaciones["B"]["votos_no"] == {id_b}
        await temporizador_a
        assert gestor_a.estado_juego != "JUEGO"
        assert gestor_b.estado_juego == "JUEGO"
        assert gestor_a.jugadores[id_a]["respuestas_ronda"]["nombre"] == "Ana"
        assert gestor_b.jugadores[id_b]["respuestas_ronda"]["nombre"] == "Beatriz"
        assert gestor_a.letra_actual == "A" and gestor_b.letra_actual == "B"
        assert gestor_a.jugadores[id_a]["total"] == 40
        assert gestor_b.jugadores[id_b]["total"] == 80
        assert gestor_a.historial_global[0]["letra"] == "A"
        assert gestor_b.historial_global[0]["letra"] == "B"
        await temporizador_b
        assert gestor_b.estado_juego != "JUEGO"
        assert gestor_b.jugadores[id_b]["total"] == 90

    asyncio.run(caso())


def test_serializacion_contextual_no_cruza_datos_entre_salones():
    async def caso():
        _, gestor_a, _ = web_server.seleccionar_sala("crear")
        _, gestor_b, _ = web_server.seleccionar_sala("crear")
        await gestor_a.conectar_sesion(FakeWebSocket(), "Jugador A")
        await gestor_b.conectar_sesion(FakeWebSocket(), "Jugador B")

        async def serializar(gestor):
            web_server.gestor_contexto.set(gestor)
            return web_server.gestor.serializar_sala()

        sala_a, sala_b = await asyncio.gather(serializar(gestor_a), serializar(gestor_b))
        assert [j["nombre"] for j in sala_a["jugadores"]] == ["Jugador A"]
        assert [j["nombre"] for j in sala_b["jugadores"]] == ["Jugador B"]

    asyncio.run(caso())
