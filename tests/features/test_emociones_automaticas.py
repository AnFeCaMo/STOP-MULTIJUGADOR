"""Pruebas de emociones automáticas de presencia y juego (fase 9)."""

import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


RESPUESTAS_PERFECTAS_A = {
    "nombre": "Andres",
    "apellido": "Acosta",
    "ciudad": "Armenia",
    "fruta": "Arandano",
    "animal": "Aguila",
    "cosa": "Anillo",
    "color": "Amarillo",
}


def test_emociones_de_espera_escritura_desconexion_y_reconexion():
    async def caso():
        gestor = GestorJuego()
        ws = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(ws, "Andres")
        assert error is None
        assert gestor.serializar_sala()["jugadores"][0]["emocion"] == "normal"

        assert (await gestor.iniciar_ronda(sesion["id"]))[0]
        assert gestor.serializar_ronda()["jugadores"][0]["emocion"] == "competitivo"
        gestor.ronda_iniciada_monotonic = asyncio.get_running_loop().time() - 4
        assert gestor.serializar_ronda()["jugadores"][0]["emocion"] == "pensativo"
        gestor.ronda_iniciada_monotonic = asyncio.get_running_loop().time()
        gestor.vence_en_monotonic = asyncio.get_running_loop().time() + 9
        assert gestor.serializar_ronda()["jugadores"][0]["emocion"] == "nervioso"
        gestor.vence_en_monotonic = asyncio.get_running_loop().time() + 60
        gestor.jugadores[sesion["id"]]["respuestas_ronda"] = {
            categoria: "A" for categoria in gestor.categorias_activas
        }
        assert gestor.serializar_ronda()["jugadores"][0]["emocion"] == "concentrado"

        await gestor.desconectar(ws)
        assert gestor.serializar_ronda()["jugadores"][0]["emocion"] == "normal"
        gestor.marcar_reconectando(sesion["token"])
        assert gestor.serializar_ronda()["jugadores"][0]["emocion"] == "normal"

    asyncio.run(caso())


def test_stop_tiene_emocion_automatica_de_sorpresa():
    async def caso():
        gestor = GestorJuego()
        sesiones = []
        for nombre in ("Andres", "Ana", "Carlos"):
            sesion, error = await gestor.conectar_sesion(FakeWebSocket(), nombre)
            assert error is None
            sesiones.append(sesion)
        ids = [sesion["id"] for sesion in sesiones]
        assert (await gestor.iniciar_ronda(ids[0]))[0]
        gestor.letra_actual = "A"
        for jugador_id, nombre in zip(ids, ("Andres", "Ana", "Carlos")):
            respuestas = {"fruta": "Arazá"} if jugador_id == ids[0] else {}
            await gestor.actualizar_respuestas(jugador_id, respuestas)
        assert (await gestor.procesar_stop(ids[0]))[0]
        mensaje = gestor.serializar_votacion_para(ids[1])
        stopper = next(j for j in mensaje["jugadores"] if j["id"] == ids[0])
        otro = next(j for j in mensaje["jugadores"] if j["id"] == ids[1])
        assert stopper["emocion"] == "sorprendido"
        assert otro["emocion"] == "suspenso"
        assert stopper["emocion_evento"].startswith("stop:")

    asyncio.run(caso())


def test_emociones_de_ganando_perdiendo_perfecta_y_victoria():
    async def caso():
        gestor = GestorJuego()
        host, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None
        otro, error = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        assert error is None
        assert (await gestor.iniciar_ronda(host["id"]))[0]
        gestor.letra_actual = "A"
        gestor.jugadores[host["id"]]["respuestas_ronda"] = {
            **RESPUESTAS_PERFECTAS_A,
            "fruta": "",
        }
        assert (await gestor.procesar_stop(host["id"]))[0]
        resultado = gestor.serializar_resultados()
        emociones = {j["id"]: j["emocion"] for j in resultado["jugadores"]}
        assert emociones[host["id"]] == "feliz"
        assert emociones[otro["id"]] == "triste"

        assert (await gestor.iniciar_ronda(host["id"]))[0]
        gestor.letra_actual = "A"
        gestor.jugadores[host["id"]]["respuestas_ronda"] = dict(RESPUESTAS_PERFECTAS_A)
        assert (await gestor.procesar_stop(host["id"]))[0]
        resultado = gestor.serializar_resultados()
        assert next(j for j in resultado["jugadores"] if j["id"] == host["id"])["emocion"] == "orgulloso"

        gestor.partida_terminada = True
        resultado = gestor.serializar_resultados()
        assert next(j for j in resultado["jugadores"] if j["id"] == host["id"])["emocion"] == "muy_feliz"

    asyncio.run(caso())


def test_respuesta_rechazada_activa_frustracion_solo_en_su_autor():
    async def caso():
        gestor = GestorJuego()
        sesiones = []
        for nombre in ("Andres", "Ana", "Carlos"):
            sesion, error = await gestor.conectar_sesion(FakeWebSocket(), nombre)
            assert error is None
            sesiones.append(sesion["id"])
        assert (await gestor.iniciar_ronda(sesiones[0]))[0]
        gestor.letra_actual = "A"
        for jugador_id, respuesta in ((sesiones[0], "Arazá"), (sesiones[1], "Arandano"), (sesiones[2], "Aguacate")):
            await gestor.actualizar_respuestas(jugador_id, {"fruta": respuesta})
        assert (await gestor.procesar_stop(sesiones[0]))[0]
        clave = "fruta:ARAZA"
        assert gestor.registrar_voto(sesiones[1], clave, False) == (True, None)
        assert gestor.registrar_voto(sesiones[2], clave, False) == (True, None)
        emociones = {j["id"]: j["emocion"] for j in gestor.serializar_resultados()["jugadores"]}
        assert emociones[sesiones[0]] == "frustrado"
        assert emociones[sesiones[1]] == "feliz"
        assert emociones[sesiones[2]] == "feliz"

    asyncio.run(caso())


def test_ui_muestra_emociones_publicadas_por_servidor():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert "function rutaAvatarEmocion(avatar, emocion)" in js
    assert "data-emocion=\"${estado}\"" in js
    assert "function renderizarAvatar(referencia, clase = \"avatar-jugador\", jugadorId = null, emocion = \"normal\", evento = \"\")" in js
    assert "emocion_evento" in js
    assert "def _emocion_por_presencia" in Path("backend/servidor.py").read_text()
    assert ".avatar-evento[data-emocion=\"feliz\"]" in css
    assert "emocion-automatica" not in js + css
