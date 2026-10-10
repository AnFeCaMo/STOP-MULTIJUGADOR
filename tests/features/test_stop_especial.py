"""Pruebas para el anuncio y cierre especial de STOP (fase 11)."""

import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_stop_publica_identidad_del_jugador_que_cierra_la_ronda():
    async def caso():
        gestor = GestorJuego()
        host, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None
        otro, error = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        assert error is None
        assert (await gestor.iniciar_ronda(host["id"]))[0]
        respuestas = {"nombre": "Andres"}
        await gestor.actualizar_respuestas(host["id"], respuestas)

        ok, error = await gestor.procesar_stop(host["id"], respuestas)
        assert ok and error is None
        assert gestor.serializar_resultados()["stopper_id"] == host["id"]
        assert gestor.serializar_votacion_para(otro["id"])["stopper_id"] == host["id"]
        assert (await gestor.procesar_stop(otro["id"], {"nombre": "Ana"}))[0] is False
        assert gestor.historial_global[-1]["stopper_id"] == host["id"]

    asyncio.run(caso())


def test_efecto_stop_anuncia_nombre_anima_avatar_y_suena_con_audio_local():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert '"💥 STOP 💥"' in js
    assert "DIJO STOP!" in js
    assert 'reproducirSonido("alerta")' in js
    assert 'reproducirSonido("impacto")' in js
    assert 'data-player-id="${jugadorId}"' in js
    assert '.avatar-evento[data-emocion="sorprendido"]' in css
    assert "@keyframes avatarSorpresa" in css
    assert "rondaConEfectoStop === claveRonda" in js
