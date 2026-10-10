import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_rey_del_stop_resuelve_empates_por_puntos_nombre_y_id():
    async def caso():
        gestor = GestorJuego()
        ids = {}
        for nombre, puntos in (("Andres", 80), ("Carlos", 30), ("Ana", 30), ("Bruno", 100)):
            jugador_id, error = await gestor.conectar(FakeWebSocket(), nombre)
            assert error is None
            gestor.jugadores[jugador_id]["total"] = puntos
            ids[nombre] = jugador_id

        gestor.partida_terminada = True
        gestor._logros_jugador = lambda _jugador_id: []
        gestor.historial_global = [
            {"ronda": 1, "letra": "A", "stopper_id": ids["Carlos"], "jugadores": []},
            {"ronda": 2, "letra": "B", "stopper_id": ids["Ana"], "jugadores": []},
            {"ronda": 3, "letra": "C", "stopper_id": ids["Carlos"], "jugadores": []},
            {"ronda": 4, "letra": "D", "stopper_id": ids["Ana"], "jugadores": []},
            {"ronda": 5, "letra": "E", "stopper_id": ids["Andres"], "jugadores": []},
        ]

        rey = gestor._estadisticas_partida()["rey_del_stop"]
        assert rey["nombre"] == "Ana"
        assert rey["id"] == ids["Ana"]
        assert rey["cantidad_stop"] == 2
        assert rey["avatar"]

        gestor.historial_global = [{"ronda": 1, "letra": "A", "jugadores": []}]
        assert gestor._estadisticas_partida()["rey_del_stop"] is None

    asyncio.run(caso())


def test_rey_del_stop_tiene_presentacion_de_corona_y_celebracion():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'id="rey-del-stop"' in html
    assert 'const rey = stats.rey_del_stop;' in js
    assert "👑 REY DEL STOP · MVP" in js
    assert ".rey-stop-personaje" in css
    assert "@keyframes rey-stop-resplandor" in css
