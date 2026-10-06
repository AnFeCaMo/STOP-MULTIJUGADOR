import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def respuestas_completas():
    return {
        "nombre": "Andres",
        "apellido": "Acosta",
        "ciudad": "Armenia",
        "fruta": "Arandano",
        "animal": "Aguila",
        "cosa": "Anillo",
    }


def test_perfil_temporal_se_actualiza_con_el_estado_de_la_partida():
    async def caso():
        gestor = GestorJuego()
        jugador_id, _ = await gestor.conectar(FakeWebSocket(), "Andres")
        otro_id, _ = await gestor.conectar(FakeWebSocket(), "Ana")

        ok, error = await gestor.iniciar_ronda(jugador_id)
        assert ok and error is None
        gestor.letra_actual = "A"
        await gestor.actualizar_respuestas(jugador_id, respuestas_completas())
        await gestor.actualizar_respuestas(otro_id, {**respuestas_completas(), "nombre": "Ana"})
        ok, error = await gestor.procesar_stop(jugador_id, respuestas_completas())
        assert ok and error is None

        ok, error = await gestor.iniciar_ronda(jugador_id)
        assert ok and error is None
        ronda = gestor.serializar_ronda()
        jugador = next(j for j in ronda["jugadores"] if j["id"] == jugador_id)

        assert jugador["perfil"]["nombre"] == "Andres"
        assert jugador["perfil"]["puntos"] == jugador["total"]
        assert jugador["perfil"]["rondas_ganadas"] >= 1
        assert jugador["perfil"]["stops"] == 1

    asyncio.run(caso())


def test_perfil_temporal_se_muestra_durante_el_juego_y_se_limpia_al_finalizar():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()

    sidebar = html[html.index('<aside class="card sidebar-juego">'):html.index("</aside>", html.index('<aside class="card sidebar-juego">'))]
    assert 'id="perfil-mi-jugador-ronda"' in sidebar
    assert "function renderizarPerfilTemporal(msg)" in js
    assert "function limpiarPerfilesTemporales()" in js
    assert 'if (msg.partida_terminada) limpiarPerfilesTemporales();' in js
