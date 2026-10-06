"""Pruebas de estados de presencia y avisos de jugadores (fase 5)."""

import asyncio
import time
from pathlib import Path

from backend import web_server
from backend.servidor import GestorJuego, TIEMPO_PARA_MARCAR_AUSENTE


class FakeWebSocket:
    pass


def test_estado_de_conexion_y_ausencia_en_la_sala():
    async def caso():
        gestor = GestorJuego()
        ws = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(ws, "Andres")
        assert error is None
        jugador_id = sesion["id"]
        assert gestor.serializar_sala()["jugadores"][0]["estado_presencia"] == "🟢 Conectado"

        assert await gestor.desconectar(ws) == "Andres"
        assert gestor.serializar_sala()["jugadores"][0]["estado_presencia"] == "🔴 Desconectado"

        jugador = gestor.jugadores[jugador_id]
        jugador["desconectado_en"] = time.time() - TIEMPO_PARA_MARCAR_AUSENTE - 1
        assert gestor.serializar_sala()["jugadores"][0]["estado_presencia"] == "😴 Ausente"

    asyncio.run(caso())


def test_estado_de_reconexion_se_muestra_y_se_limpia_al_recuperar_sesion():
    async def caso():
        gestor = GestorJuego()
        ws_anterior = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(ws_anterior, "Ana")
        assert error is None
        assert await gestor.desconectar(ws_anterior) == "Ana"

        reconectando = gestor.marcar_reconectando(sesion["token"])
        assert reconectando == {
            "id": sesion["id"],
            "nombre": "Ana",
            "es_espectador": False,
        }
        assert gestor.serializar_sala()["jugadores"][0]["estado_presencia"] == "🔄 Reconectando"

        ws_nuevo = FakeWebSocket()
        recuperada, error = await gestor.conectar_sesion(ws_nuevo, "Ana", sesion["token"])
        assert error is None and recuperada["reconectado"]
        assert gestor.serializar_sala()["jugadores"][0]["estado_presencia"] == "🟢 Conectado"

    asyncio.run(caso())


def test_estado_escribiendo_completado_y_espectador_en_ronda():
    async def caso():
        gestor = GestorJuego()
        sesion, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None
        host_id = sesion["id"]
        assert (await gestor.iniciar_ronda(host_id))[0]

        ronda = gestor.serializar_ronda()
        assert ronda["jugadores"][0]["estado_presencia"] == "✍️ Escribiendo"

        gestor.jugadores[host_id]["respuestas_ronda"] = {
            categoria: "A" for categoria in gestor.categorias_activas
        }
        assert gestor.serializar_ronda()["jugadores"][0]["estado_presencia"] == "✅ Completó"

        espectador, error = await gestor.conectar_sesion(FakeWebSocket(), "Observador")
        assert error is None and espectador["es_espectador"]
        datos_espectador = gestor.serializar_ronda()["espectadores"][0]
        assert datos_espectador["estado"] == "observando"
        assert datos_espectador["estado_presencia"] == "👀 Espectador"

    asyncio.run(caso())


def test_interfaz_y_servidor_publican_avisos_de_cambios_de_presencia():
    js = Path("frontend/app.js").read_text()
    servidor = Path("backend/web_server.py").read_text()

    assert 'tipo: "estado_reconexion"' in js
    assert 'case "notificacion"' in js
    assert "se ha unido!" in servidor
    assert "se reconectó!" in servidor
    assert "abandonó la partida." in servidor


def test_servidor_actualiza_estado_a_ausente_sin_polling(monkeypatch):
    async def caso():
        gestor = GestorJuego()
        ws_desconectado = FakeWebSocket()
        _, error = await gestor.conectar_sesion(ws_desconectado, "Andres")
        assert error is None
        _, error = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        assert error is None
        assert await gestor.desconectar(ws_desconectado) == "Andres"

        actualizaciones = []

        async def registrar_actualizacion():
            actualizaciones.append(True)

        monkeypatch.setattr(web_server, "gestor", gestor)
        monkeypatch.setattr(web_server, "TIEMPO_PARA_MARCAR_AUSENTE", 0.01)
        monkeypatch.setattr(web_server, "broadcast_estado_actual", registrar_actualizacion)
        await web_server.esperar_ausencia("Andres")
        assert actualizaciones == [True]

    asyncio.run(caso())
