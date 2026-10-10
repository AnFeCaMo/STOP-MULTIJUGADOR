"""Pruebas de selección y persistencia de personajes locales (fase 6)."""

import asyncio
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi.testclient import TestClient

from backend.web_server import app
from backend.servidor import (
    AVATARES,
    AVATAR_PERSONA_A_LEGADO,
    AVATAR_PREDETERMINADO,
    GestorJuego,
    normalizar_avatar_id,
)


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


def test_id_nuevo_y_referencias_anteriores_se_normalizan_sin_perder_compatibilidad():
    assert normalizar_avatar_id("persona-03") == "gato"
    assert normalizar_avatar_id("gato") == "gato"
    assert normalizar_avatar_id("🐱") == "gato"
    assert normalizar_avatar_id("desconocido") is None


def test_websocket_acepta_id_estable_y_publica_la_persona_en_el_lobby():
    with TestClient(app) as cliente:
        with cliente.websocket_connect("/ws") as socket:
            socket.send_json({
                "tipo": "conexion",
                "nombre": "AvatarPersona",
                "avatar": "oso",
                "avatar_id": "persona-03",
                "accion_sala": "crear",
                "codigo_sala": "",
            })
            bienvenida = socket.receive_json()
            assert bienvenida["tipo"] == "bienvenida"
            assert bienvenida["avatar"] == "gato"
            socket.receive_json()  # Estado inicial de la sala.
            sala = socket.receive_json()
            assert sala["tipo"] == "sala"
            assert sala["jugadores"][0]["avatar"] == "🐱"


def test_avatar_persona_se_reconecta_sin_duplicar_jugador_ni_perder_progreso():
    async def caso():
        gestor = GestorJuego()
        ws = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(ws, "Andres", avatar="persona-03")
        assert error is None and sesion["avatar"] == "gato"
        jugador_id = sesion["id"]
        jugador = gestor.jugadores[jugador_id]
        jugador["total"] = 145
        jugador["historial"] = [45, 50, 50]
        jugador["cantidad_stop"] = 3
        gestor.historial_global = [
            {
                "ronda": indice,
                "puntuaciones": {"Andres": puntos},
                "stopper_id": jugador_id,
                "duracion_segundos": 10,
                "jugadores": [{"id": jugador_id, "puntos_obtenidos": puntos}],
            }
            for indice, puntos in enumerate((45, 50, 50), start=1)
        ]

        await gestor.desconectar(ws)
        recuperada, error = await gestor.conectar_sesion(
            FakeWebSocket(), "Nombre ignorado", sesion["token"]
        )
        assert error is None and recuperada["reconectado"]
        assert recuperada["id"] == jugador_id
        assert len(gestor.jugadores) == 1
        assert recuperada["avatar"] == "gato"
        assert jugador["total"] == 145
        assert jugador["historial"] == [45, 50, 50]
        assert jugador["cantidad_stop"] == 3
        perfil = gestor._perfil_jugador(jugador_id)
        assert perfil["puntos"] == 145
        assert perfil["rondas_ganadas"] == 3
        assert {logro["id"] for logro in perfil["logros"]} >= {"racha_tres", "rey_stop"}

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
    assert "...camposAvatarConexion()" in js
    assert "actualizarPrevisualizacionAvatar" not in js
    assert "previsualizacion-avatar" not in html
    assert ".previsualizacion-avatar" not in css
    assert ".opcion-avatar" in css
    assert 'clase = "avatar-jugador"' in js


def test_catalogo_de_20_avatares_locales_es_accesible_y_tiene_fallback():
    raiz = Path(__file__).resolve().parents[2]
    catalogo = (raiz / "frontend/avatar-catalog.js").read_text(encoding="utf-8")
    html = (raiz / "frontend/index.html").read_text(encoding="utf-8")
    js = (raiz / "frontend/app.js").read_text(encoding="utf-8")
    ids = re.findall(r'\{ id: "(persona-\d{2})", nombre: "([^"]+)",[^}]*?ruta: "([^"]+)"', catalogo)

    assert len(ids) == 20
    assert len({avatar_id for avatar_id, _, _ in ids}) == 20
    assert 'src="avatar-catalog.js?' in html
    assert 'id="opciones-avatares"' in html
    assert 'El avatar seleccionado se confirma al entrar a la sala.' in html
    assert "AVATAR_FALLBACK_DATA_URI" in js

    for avatar_id, nombre, ruta in ids:
        archivo = raiz / "frontend" / ruta.lstrip("/")
        assert archivo.is_file(), f"Falta el SVG de {avatar_id}"
        assert nombre.strip()
        raiz_svg = ET.parse(archivo).getroot()
        assert raiz_svg.tag.endswith("svg")
        assert raiz_svg.attrib.get("viewBox") == "0 0 256 256"
        contenido = archivo.read_text(encoding="utf-8")
        assert not re.search(r'(?:xlink:)?href=["\']https?://', contenido)
        assert "<image" not in contenido
        assert "<path" in contenido and "<ellipse" in contenido
        assert AVATAR_PERSONA_A_LEGADO[avatar_id] in catalogo

    with TestClient(app) as cliente:
        for avatar_id, _, ruta in ids:
            respuesta = cliente.get(ruta)
            assert respuesta.status_code == 200
        for avatar_id, _, _ in ids:
            for emocion in ("normal", "feliz", "muy_feliz", "triste", "frustrado", "sorprendido", "concentrado", "nervioso", "pensativo", "competitivo", "suspenso", "orgulloso"):
                ruta_emocion = f"/assets/avatars/expresiones/{avatar_id}/{emocion}.svg"
                respuesta = cliente.get(ruta_emocion)
                assert respuesta.status_code == 200, ruta_emocion
                assert respuesta.headers["content-type"].startswith("image/svg+xml")


def test_catalogo_dragon_ball_usa_tabla_local_y_conserva_identificadores():
    raiz = Path(__file__).resolve().parents[2]
    catalogo = (raiz / "frontend/avatar-catalog.js").read_text(encoding="utf-8")
    nombres = (
        "Goku", "Vegeta", "Gohan", "Piccolo", "Trunks", "Goten", "Krilin",
        "Bulma", "Androide 18", "Androide 17", "Freezer", "Cell", "Majin Buu",
        "Broly", "Yamcha", "Ten Shin Han", "Bills", "Whis", "Videl", "Bardock",
    )
    entradas = re.findall(
        r'\{ id: "(persona-\d{2})", nombre: "([^"]+)", personajeId: "([^"]+)", '
        r'permisoUsoDeclarado: true, ruta: "([^"]+)", legacyId: "([^"]+)"',
        catalogo,
    )

    assert [nombre for _, nombre, _, _, _ in entradas] == list(nombres)
    assert len({avatar_id for avatar_id, *_ in entradas}) == 20
    assert len({personaje_id for _, _, personaje_id, *_ in entradas}) == 20
    assert len({legacy_id for *_, legacy_id in entradas}) == 20
    assert "tabla local proporcionada" in (raiz / "frontend/index.html").read_text(encoding="utf-8")
    licencia = (raiz / "frontend/assets/avatars/LICENCIA.md").read_text(encoding="utf-8")
    assert "declaró que cuenta con permiso" in licencia
    assert "Tabla de Emociones Dragon Ball.png" in licencia
