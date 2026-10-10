"""Pruebas de estadísticas generales y por jugador (fase 6)."""

import asyncio

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_estadisticas_generales_y_detalle_por_jugador():
    async def caso():
        gestor = GestorJuego()
        host, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        ana, error2 = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        assert error is None and error2 is None
        host_id, ana_id = host["id"], ana["id"]
        assert (await gestor.actualizar_configuracion(host_id, 4, ["nombre", "ciudad", "animal"]))[0]
        assert (await gestor.iniciar_ronda(host_id))[0]
        gestor.letra_actual = "A"
        observador, err = await gestor.conectar_sesion(FakeWebSocket(), "Observador")
        assert err is None and observador["es_espectador"]
        await gestor.actualizar_respuestas(host_id, {
            "nombre": "Andres", "ciudad": "Armenia", "animal": "Aguila",
        })
        await gestor.actualizar_respuestas(ana_id, {
            "nombre": "Aurelianox", "ciudad": "Armenia", "animal": "Aardwolfx",
        })
        assert (await gestor.procesar_stop(host_id))[0]
        assert gestor.estado_juego == "VOTACION"
        assert gestor.registrar_voto(host_id, "nombre:AURELIANOX", True) == (True, None)
        assert gestor.registrar_voto(host_id, "animal:AARDWOLFX", False) == (True, None)
        assert gestor.estado_juego == "RESULTADOS"

        stats = gestor._estadisticas_partida()
        assert stats["rondas_completadas"] == 1
        assert stats["jugadores"] == 3  # El espectador se promueve al terminar la ronda.
        assert stats["espectadores"] == 1
        assert stats["respuestas_totales"] == 6
        assert stats["respuestas_validas"] == 5
        assert stats["respuestas_invalidas"] == 1
        assert stats["respuestas_validadas_votacion"] == 1
        assert stats["respuestas_rechazadas_votacion"] == 1
        assert stats["cantidad_stop"] == 1
        assert stats["letras_utilizadas"] == ["A"]
        andres = next(j for j in stats["por_jugador"] if j["id"] == host_id)
        ana_stats = next(j for j in stats["por_jugador"] if j["id"] == ana_id)
        assert andres["puntos_totales"] == gestor.jugadores[host_id]["total"]
        assert andres["puntos_por_ronda"][0]["ronda"] == 1
        assert andres["respuestas_correctas"] == 3
        assert andres["respuestas_repetidas"] == 1
        assert andres["cantidad_stop"] == 1
        # Color permanece activo aunque el anfitrión solo configure tres categorías.
        assert andres["participacion"] == 75.0
        assert ana_stats["validadas_por_votacion"] == 1
        assert ana_stats["rechazadas_por_votacion"] == 1
        assert ana_stats["respuestas_incorrectas"] == 1

        gestor.partida_terminada = True
        publicado = gestor.serializar_resultados()["estadisticas"]
        assert publicado["respuestas_totales"] == 6
        assert len(publicado["por_jugador"]) == 3
    asyncio.run(caso())


def test_frontend_incluye_panel_estadistico_general_y_por_jugador():
    from pathlib import Path

    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    assert "estadisticas-generales" in html and "estadisticas-jugadores" in html
    for etiqueta in (
        "Respuestas totales", "Letras utilizadas", "Victorias de partida",
        "Rondas ganadas", "Promedio por ronda", "Mejor ronda", "Participación",
    ):
        assert etiqueta in js


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Todas las pruebas de la fase 6 pasaron.")
