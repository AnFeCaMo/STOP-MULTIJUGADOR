"""Pruebas de selección y persistencia de personajes locales (fase 6)."""

import asyncio
from pathlib import Path

from backend.servidor import AVATARES, AVATAR_PREDETERMINADO, GestorJuego


class FakeWebSocket:
    pass


def test_catalogo_completo_y_seleccion_de_avatar():
    assert len(AVATARES) == 21
    assert AVATARES["oso"] == "🐻"
    assert AVATARES["calabaza"] == "🎃"
    assert AVATAR_PREDETERMINADO in AVATARES


def test_avatar_seleccionado_se_conserva_al_reconectar_y_se_publica():
    async def caso():
        gestor = GestorJuego()
        ws = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(ws, "Andres", avatar="gato")
        assert error is None
        jugador_id = sesion["id"]
        assert sesion["avatar"] == "gato"
        assert gestor.serializar_sala()["jugadores"][0]["avatar"] == "🐱"

        await gestor.desconectar(ws)
        recuperada, error = await gestor.conectar_sesion(
            FakeWebSocket(), "Nombre ignorado", sesion["token"]
        )
        assert error is None and recuperada["reconectado"]
        assert recuperada["avatar"] == "gato"
        assert gestor.serializar_sala()["jugadores"][0]["avatar"] == "🐱"
        assert gestor.jugadores[jugador_id]["avatar"] == "gato"

    asyncio.run(caso())


def test_avatar_se_mantiene_con_jugador_promovido_y_espectador():
    async def caso():
        gestor = GestorJuego()
        jugador, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres", avatar="robot")
        assert error is None
        nuevo, error = await gestor.conectar_sesion(FakeWebSocket(), "Ana", avatar="panda")
        assert error is None
        assert gestor.serializar_sala()["jugadores"][1]["avatar"] == "🐼"

        assert (await gestor.iniciar_ronda(jugador["id"]))[0]
        espectador, error = await gestor.conectar_sesion(
            FakeWebSocket(), "Observador", avatar="fantasma"
        )
        assert error is None and espectador["es_espectador"]
        espectador_serializado = gestor.serializar_ronda()["espectadores"][0]
        assert espectador_serializado["avatar"] == "👻"

        assert (await gestor.procesar_stop(jugador["id"], {}))[0]
        assert gestor.jugadores[espectador["id"]]["avatar"] == "fantasma"
        assert gestor.jugadores[nuevo["id"]]["avatar"] == "panda"

    asyncio.run(caso())


def test_avatar_invalido_se_rechaza_sin_crear_sesion():
    async def caso():
        gestor = GestorJuego()
        sesion, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres", avatar="<img>")
        assert sesion is None
        assert error == "El avatar seleccionado no es válido."
        assert gestor.jugadores == {}

    asyncio.run(caso())


def test_avatares_de_salas_y_jugadores_son_independientes():
    async def caso():
        sala_a = GestorJuego()
        sala_b = GestorJuego()
        jugador_a, error = await sala_a.conectar_sesion(FakeWebSocket(), "Andres", avatar="leon")
        assert error is None
        jugador_b, error = await sala_b.conectar_sesion(FakeWebSocket(), "Ana", avatar="koala")
        assert error is None

        assert sala_a.serializar_sala()["jugadores"][0]["avatar"] == "🦁"
        assert sala_b.serializar_sala()["jugadores"][0]["avatar"] == "🐨"
        assert sala_a.jugadores[jugador_a["id"]]["avatar"] == "leon"
        assert sala_b.jugadores[jugador_b["id"]]["avatar"] == "koala"

    asyncio.run(caso())


def test_selector_guarda_preferencia_local_y_la_envia_al_servidor():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'id="opciones-avatares"' in html
    assert 'localStorage.getItem("stop_avatar")' in js
    assert 'localStorage.setItem("stop_avatar", avatarId)' in js
    assert "avatar: avatarSeleccionado" in js
    assert ".opcion-avatar" in css
    assert 'clase = "avatar-jugador"' in js
