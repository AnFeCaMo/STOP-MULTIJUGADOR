"""Pruebas de reacciones predefinidas en tiempo real (fase 8)."""

import asyncio
from pathlib import Path

from backend.servidor import GestorJuego, REACCIONES


class FakeWebSocket:
    pass


def test_reacciones_predefinidas_sin_mensajes_libres():
    assert REACCIONES == {
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


def test_reaccion_se_envia_y_se_asocia_a_la_sesion_correcta():
    async def caso():
        gestor = GestorJuego()
        ws_andres, ws_ana = FakeWebSocket(), FakeWebSocket()
        andres, error = await gestor.conectar_sesion(ws_andres, "Andres", avatar="gato")
        assert error is None
        ana, error = await gestor.conectar_sesion(ws_ana, "Ana", avatar="panda")
        assert error is None

        msg_andres, error = gestor.crear_mensaje_reaccion(andres["id"], "jaja")
        assert error is None
        assert msg_andres == {
            "tipo": "reaccion",
            "jugador_id": andres["id"],
            "nombre": "Andres",
            "avatar": "🐱",
            "reaccion": "jaja",
            "texto": "😂 JAJA",
        }

        msg_ana, error = gestor.crear_mensaje_reaccion(ana["id"], "vamos")
        assert error is None
        assert msg_ana["jugador_id"] == ana["id"]
        assert msg_ana["nombre"] == "Ana"
        assert msg_ana["avatar"] == "🐼"

    asyncio.run(caso())


def test_rechaza_reacciones_invalidas_y_sesiones_no_conectadas():
    async def caso():
        gestor = GestorJuego()
        sesion, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None

        mensaje, error = gestor.crear_mensaje_reaccion(sesion["id"], "mensaje libre")
        assert mensaje is None
        assert error == "La reacción seleccionada no es válida."

        assert await gestor.desconectar(gestor.jugadores[sesion["id"]]["ws"]) == "Andres"
        mensaje, error = gestor.crear_mensaje_reaccion(sesion["id"], "jaja")
        assert mensaje is None
        assert error == "La sesión no está conectada."

    asyncio.run(caso())


def test_reaccion_limita_frecuencia_por_jugador():
    async def caso():
        gestor = GestorJuego()
        sesion, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None
        assert gestor.crear_mensaje_reaccion(sesion["id"], "jaja")[0]
        mensaje, error = gestor.crear_mensaje_reaccion(sesion["id"], "vamos")
        assert mensaje is None
        assert error == "Espera un momento antes de enviar otra reacción."

    asyncio.run(caso())


def test_interfaz_renderiza_reacciones_con_expiracion_y_limite_visual():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()
    servidor = Path("backend/web_server.py").read_text()
    gestor = Path("backend/servidor.py").read_text()

    assert 'id="botones-reacciones"' in html
    assert 'id="reacciones-flotantes"' in html
    assert "function enviarReaccion(reaccion)" in js
    assert "function mostrarReaccion(mensaje)" in js
    assert "window.setTimeout" in js and "}, 3000);" in js
    assert "contenedor.children.length > 5" in js
    assert "mensaje_reaccion, error = gestor.crear_mensaje_reaccion" in servidor
    assert ".reaccion-flotante" in css
    assert "La reacción seleccionada no es válida." in gestor
