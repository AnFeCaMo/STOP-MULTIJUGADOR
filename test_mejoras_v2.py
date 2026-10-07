"""Pruebas de las mejoras visuales y de gamificación V2."""

import asyncio

from backend.servidor import GestorJuego


class WS:
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


def test_duracion_por_defecto_es_un_minuto():
    gestor = GestorJuego()
    assert gestor.duracion_ronda == 60


def test_perfil_logros_y_estadisticas_finales():
    async def caso():
        gestor = GestorJuego(duracion_ronda=60)
        a, _ = await gestor.conectar(WS(), "Andres")
        b, _ = await gestor.conectar(WS(), "Ana")
        gestor.rondas_totales = 4

        for ronda in range(1, 4):
            ok, error = await gestor.iniciar_ronda(a)
            assert ok and error is None
            gestor.letra_actual = "A"
            await gestor.actualizar_respuestas(a, respuestas_completas())
            await gestor.actualizar_respuestas(b, {**respuestas_completas(), "nombre": "Ana"})
            ok, error = await gestor.procesar_stop(a, respuestas_completas())
            assert ok and error is None
            assert gestor.estado_juego == "RESULTADOS"

        perfil = gestor._perfil_jugador(a)
        assert perfil["nombre"] == "Andres"
        assert perfil["rondas_ganadas"] >= 1
        ids_logros = {x["id"] for x in perfil["logros"]}
        assert "primera_victoria" in ids_logros
        assert "respuesta_rapida" in ids_logros
        assert "todas_validas" in ids_logros
        assert "racha_tres" in ids_logros
        assert perfil["stops"] == 3

        stats = gestor._estadisticas_partida()
        assert stats["rondas_completadas"] == 3
        assert stats["cantidad_stop"] == 3
        assert "mejor_jugador" in stats
        assert "mayor_puntuacion" in stats

    asyncio.run(caso())


def test_estado_de_jugador_cambia_a_completo():
    async def caso():
        gestor = GestorJuego()
        a, _ = await gestor.conectar(WS(), "Andres")
        ok, _ = await gestor.iniciar_ronda(a)
        assert ok
        gestor.letra_actual = "A"
        await gestor.actualizar_respuestas(a, {"nombre": "Andres"})
        ronda = gestor.serializar_ronda()
        jugador = next(j for j in ronda["jugadores"] if j["id"] == a)
        assert jugador["estado"] == "escribiendo"
        await gestor.actualizar_respuestas(a, respuestas_completas())
        ronda = gestor.serializar_ronda()
        jugador = next(j for j in ronda["jugadores"] if j["id"] == a)
        assert jugador["estado"] == "completó"

    asyncio.run(caso())
