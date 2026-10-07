import asyncio

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_estadisticas_finales_calculan_victorias_promedio_y_mejor_ronda():
    async def caso():
        gestor = GestorJuego()
        andres, _ = await gestor.conectar(FakeWebSocket(), "Andres")
        ana, _ = await gestor.conectar(FakeWebSocket(), "Ana")
        gestor.jugadores[andres]["total"] = 30
        gestor.jugadores[ana]["total"] = 15
        gestor.partida_terminada = True
        gestor._logros_jugador = lambda _jugador_id: []
        gestor.historial_global = [
            {
                "ronda": 1,
                "letra": "A",
                "categorias": ["nombre"],
                "puntuaciones": {"Andres": 10, "Ana": 10},
                "jugadores": [
                    {
                        "id": andres,
                        "nombre": "Andres",
                        "respuestas": {"nombre": "Andres"},
                        "resultados": {"nombre": {"estado": "valida_unica"}},
                        "puntos_categorias": 10,
                        "puntos_obtenidos": 10,
                        "puntuacion_acumulada": 10,
                    },
                    {
                        "id": ana,
                        "nombre": "Ana",
                        "respuestas": {"nombre": "Ana"},
                        "resultados": {"nombre": {"estado": "valida_unica"}},
                        "puntos_categorias": 10,
                        "puntos_obtenidos": 10,
                        "puntuacion_acumulada": 10,
                    },
                ],
            },
            {
                "ronda": 2,
                "letra": "B",
                "categorias": ["nombre"],
                "puntuaciones": {"Andres": 20, "Ana": 5},
                "jugadores": [
                    {
                        "id": andres,
                        "nombre": "Andres",
                        "respuestas": {"nombre": "Bernardo"},
                        "resultados": {"nombre": {"estado": "valida_unica"}},
                        "puntos_categorias": 20,
                        "puntos_obtenidos": 20,
                        "puntuacion_acumulada": 30,
                    },
                    {
                        "id": ana,
                        "nombre": "Ana",
                        "respuestas": {"nombre": "Beatriz"},
                        "resultados": {"nombre": {"estado": "votacion_rechazada"}},
                        "puntos_categorias": 5,
                        "puntos_obtenidos": 5,
                        "puntuacion_acumulada": 15,
                    },
                ],
            },
        ]

        stats = gestor._estadisticas_partida()
        por_id = {jugador["id"]: jugador for jugador in stats["por_jugador"]}

        assert stats["rondas_completadas"] == 2
        assert stats["jugadores"] == 2
        assert stats["respuestas_totales"] == 4
        assert stats["respuestas_validas"] == 3
        assert stats["respuestas_invalidas"] == 1
        assert por_id[andres]["victorias"] == 1
        assert por_id[andres]["rondas_ganadas"] == 2
        assert por_id[andres]["promedio_puntos_por_ronda"] == 15
        assert por_id[andres]["mejor_ronda"] == {"ronda": 2, "puntos": 20}
        assert por_id[ana]["victorias"] == 0
        assert por_id[ana]["rondas_ganadas"] == 1
        assert por_id[ana]["promedio_puntos_por_ronda"] == 7.5
        assert por_id[ana]["mejor_ronda"] == {"ronda": 1, "puntos": 10}

    asyncio.run(caso())
