"""Pruebas de espectadores y reconexión (fase 2)."""

import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


async def crear_sesion(gestor, nombre):
    ws = FakeWebSocket()
    sesion, error = await gestor.conectar_sesion(ws, nombre)
    assert error is None
    return ws, sesion


async def crear_ronda(nombres=("Andres", "Ana"), duracion=60):
    gestor = GestorJuego(duracion_ronda=duracion)
    sesiones = [await crear_sesion(gestor, nombre) for nombre in nombres]
    ids = [sesion["id"] for _, sesion in sesiones]
    assert (await gestor.iniciar_ronda(ids[0]))[0]
    gestor.letra_actual = "A"
    return gestor, sesiones, ids


def respuestas(nombre, fruta="Arandano"):
    return {
        "nombre": nombre,
        "apellido": "Acosta",
        "ciudad": "Armenia",
        "fruta": fruta,
        "animal": "Aguila",
        "cosa": "Anillo",
    }


def test_jugador_que_entra_antes_de_partida_es_jugador():
    async def caso():
        gestor = GestorJuego()
        _, sesion = await crear_sesion(gestor, "Andres")
        assert not sesion["es_espectador"]
        assert sesion["id"] in gestor.jugadores
        assert sesion["id"] not in gestor.espectadores
        assert sesion["es_anfitrion"]
    asyncio.run(caso())


def test_frontend_muestra_rol_y_estado_de_reconexion():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    assert "👀 ESPECTADOR" in html
    assert "🔄 Reconectando..." in html and "✅ Conexión recuperada" in js
    assert 'localStorage.setItem("stop_token"' in js


def test_entrada_durante_ronda_espectador_no_actua_y_promueve_al_cerrar():
    async def caso():
        gestor, _, ids = await crear_ronda()
        _, espectador = await crear_sesion(gestor, "Observador")
        eid = espectador["id"]
        assert espectador["es_espectador"] and eid in gestor.espectadores
        estado = gestor.serializar_estado_para(eid, True)
        assert estado["tipo"] == "ronda" and estado["letra"] == "A"
        assert estado["jugadores"] and estado["espectador"] is True
        assert "mis_respuestas" not in estado
        assert await gestor.actualizar_respuestas(eid, respuestas("Elena")) is False
        ok, error = await gestor.procesar_stop(eid, respuestas("Elena"))
        assert not ok and error == "Jugador no encontrado."
        assert gestor.quien_stop == ""
        assert eid not in gestor.jugadores
        for jugador_id, nombre in zip(ids, ("Andres", "Ana")):
            await gestor.actualizar_respuestas(jugador_id, respuestas(nombre))
        assert (await gestor.procesar_stop(ids[0]))[0]
        assert gestor.estado_juego == "RESULTADOS"
        assert eid in gestor.jugadores and eid not in gestor.espectadores
        assert gestor.jugadores[eid]["total"] == 0
    asyncio.run(caso())


def test_espectador_en_votacion_ve_candidatos_no_vota_y_se_promueve_al_final():
    async def caso():
        gestor, _, ids = await crear_ronda(nombres=("Andres", "Ana", "Alberto"))
        await gestor.actualizar_respuestas(ids[0], respuestas("Andres", fruta="Arazá"))
        await gestor.actualizar_respuestas(ids[1], respuestas("Ana"))
        await gestor.actualizar_respuestas(ids[2], respuestas("Alberto"))
        assert (await gestor.procesar_stop(ids[0]))[0]
        assert gestor.estado_juego == "VOTACION"
        _, espectador = await crear_sesion(gestor, "Observador")
        eid = espectador["id"]
        assert espectador["es_espectador"]
        voto = gestor.serializar_estado_para(eid, True)
        assert voto["tipo"] == "votacion" and voto["candidatos"]
        assert voto["jugadores"] and voto["quien_stop"] == "Andres"
        assert next(j for j in voto["jugadores"] if j["id"] == ids[1])["estado"] == "Pendiente de votar"
        assert all(not candidato["puede_votar"] for candidato in voto["candidatos"])
        clave = "fruta:ARAZA"
        assert gestor.registrar_voto(eid, clave, True) == (False, "Jugador no encontrado.")
        assert eid in gestor.espectadores and eid not in gestor.jugadores
        for jugador_id in list(gestor.votaciones[clave]["votantes"]):
            assert gestor.registrar_voto(jugador_id, clave, True)[0]
        assert gestor.estado_juego == "RESULTADOS"
        assert eid in gestor.jugadores and eid not in gestor.espectadores
    asyncio.run(caso())


def test_reconexion_conserva_identidad_puntuacion_historial_y_respuestas():
    async def caso():
        gestor, sesiones, ids = await crear_ronda()
        ws_anterior, sesion = sesiones[0]
        await gestor.actualizar_respuestas(ids[0], respuestas("Andres"))
        jugador = gestor.jugadores[ids[0]]
        jugador["total"] = 45
        jugador["historial"] = [20, 25]
        assert await gestor.desconectar(ws_anterior) == "Andres"
        ws_nuevo = FakeWebSocket()
        reconexion, error = await gestor.conectar_sesion(ws_nuevo, "Nombre ignorado", sesion["token"])
        assert error is None and reconexion["reconectado"]
        assert reconexion["id"] == ids[0] and reconexion["nombre"] == "Andres"
        assert not reconexion["es_anfitrion"]
        assert gestor.jugadores[ids[1]]["es_anfitrion"]
        assert gestor.jugadores[ids[0]]["total"] == 45
        assert gestor.jugadores[ids[0]]["historial"] == [20, 25]
        estado = gestor.serializar_estado_para(ids[0])
        assert estado["tipo"] == "ronda"
        assert estado["mis_respuestas"]["nombre"] == "Andres"
    asyncio.run(caso())


def test_reconexion_durante_votacion_recupera_su_elegibilidad():
    async def caso():
        gestor, sesiones, ids = await crear_ronda(nombres=("Andres", "Ana", "Alberto"))
        await gestor.actualizar_respuestas(ids[0], respuestas("Andres", fruta="Arazá"))
        await gestor.actualizar_respuestas(ids[1], respuestas("Ana"))
        await gestor.actualizar_respuestas(ids[2], respuestas("Alberto"))
        assert (await gestor.procesar_stop(ids[0]))[0]
        ws, sesion = sesiones[1]
        assert ids[1] in gestor.votaciones["fruta:ARAZA"]["votantes"]
        await gestor.desconectar(ws)
        assert ids[1] not in gestor.votaciones["fruta:ARAZA"]["votantes"]
        ws_nuevo = FakeWebSocket()
        reconexion, error = await gestor.conectar_sesion(ws_nuevo, "Ana", sesion["token"])
        assert error is None and reconexion["id"] == ids[1]
        estado = gestor.serializar_estado_para(ids[1])
        candidato = next(c for c in estado["candidatos"] if c["clave"] == "fruta:ARAZA")
        assert candidato["puede_votar"]
        assert gestor.registrar_voto(ids[1], "fruta:ARAZA", True)[0]
        await gestor.desconectar(ws_nuevo)
        ws_recuperado = FakeWebSocket()
        assert (await gestor.conectar_sesion(ws_recuperado, "Ana", sesion["token"]))[1] is None
        candidato = next(
            c for c in gestor.serializar_estado_para(ids[1])["candidatos"]
            if c["clave"] == "fruta:ARAZA"
        )
        assert candidato["ya_voto"] and not candidato["puede_votar"]
        assert gestor.registrar_voto(ids[2], "fruta:ARAZA", True)[0]
    asyncio.run(caso())


def test_reconexion_de_anfitrion_y_transferencia_automatica():
    async def caso():
        gestor = GestorJuego()
        ws_host, host = await crear_sesion(gestor, "Andres")
        _, otro = await crear_sesion(gestor, "Ana")
        assert await gestor.desconectar(ws_host) == "Andres"
        assert gestor.anfitrion_id == otro["id"]
        ws_host_nuevo = FakeWebSocket()
        reconexion, error = await gestor.conectar_sesion(ws_host_nuevo, "Andres", host["token"])
        assert error is None and reconexion["id"] == host["id"]
        assert not reconexion["es_anfitrion"]
        assert gestor.anfitrion_id == otro["id"]
        assert gestor.jugadores[otro["id"]]["es_anfitrion"]

        solo = GestorJuego()
        ws_solo, anfitrion = await crear_sesion(solo, "Solo")
        await solo.desconectar(ws_solo)
        recuperado, error = await solo.conectar_sesion(FakeWebSocket(), "Solo", anfitrion["token"])
        assert error is None and recuperado["es_anfitrion"]
        assert solo.anfitrion_id == anfitrion["id"]
    asyncio.run(caso())


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Todas las pruebas de la fase 2 pasaron.")
