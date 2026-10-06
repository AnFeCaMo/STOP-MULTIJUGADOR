import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_resultados_se_recuperan_con_los_mismos_puntajes_tras_reconexion():
    async def caso():
        gestor = GestorJuego()
        ws = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(ws, "Andres")
        assert error is None
        jugador_id = sesion["id"]
        assert (await gestor.iniciar_ronda(jugador_id))[0]
        gestor.letra_actual = "A"
        respuestas = {
            "nombre": "Andres",
            "apellido": "Acosta",
            "ciudad": "Armenia",
            "fruta": "Arandano",
            "animal": "Aguila",
            "cosa": "Anillo",
        }
        await gestor.actualizar_respuestas(jugador_id, respuestas)
        assert (await gestor.procesar_stop(jugador_id))[0]
        assert gestor.estado_juego == "RESULTADOS"
        antes = gestor.serializar_estado_para(jugador_id)
        assert antes["tipo"] == "resultados"

        assert await gestor.desconectar(ws) == "Andres"
        ws_reconectado = FakeWebSocket()
        reconexion, error = await gestor.conectar_sesion(
            ws_reconectado, "Andres", sesion["token"]
        )
        assert error is None and reconexion["reconectado"]
        despues = gestor.serializar_estado_para(jugador_id)
        assert despues["tipo"] == "resultados"
        assert despues["jugadores"][0]["detalle_respuestas"] == antes["jugadores"][0]["detalle_respuestas"]
        assert despues["jugadores"][0]["total"] == antes["jugadores"][0]["total"]

    asyncio.run(caso())


def test_interfaz_presenta_resultados_en_etapas_sin_reemplazar_datos_oficiales():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert "function animarResultadosProgresivamente(animar)" in js
    assert '"⏳ Calculando..."' in js
    assert '"✅ Respuesta aceptada"' in js
    assert '"❌ Respuesta no válida"' in js
    assert 'data-estado="${escaparHtml(d.estado || "")}" data-puntos="${puntos}"' in js
    assert 'mostrarPantallaResultados(msg, estadoJuego !== "RESULTADOS")' in js
    assert "if (!animar)" in js
    assert ".resultado-actualizando" in css
