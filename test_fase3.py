"""Pruebas de clasificación, historial y nueva partida (fase 3)."""

import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def respuestas(nombre):
    return {
        "nombre": nombre, "apellido": "Acosta", "ciudad": "Armenia",
        "fruta": "Arandano", "animal": "Aguila", "cosa": "Anillo",
    }


async def preparar_partida(rondas=2):
    gestor = GestorJuego()
    sesiones = []
    for nombre in ("Andres", "Ana"):
        sesion, error = await gestor.conectar_sesion(FakeWebSocket(), nombre)
        assert error is None
        sesiones.append(sesion)
    gestor.rondas_totales = rondas
    return gestor, [s["id"] for s in sesiones]


async def cerrar_ronda(gestor, ids):
    assert (await gestor.iniciar_ronda(ids[0]))[0]
    gestor.letra_actual = "A"
    for jugador_id, nombre in zip(ids, ("Andres", "Ana")):
        await gestor.actualizar_respuestas(jugador_id, respuestas(nombre))
    assert (await gestor.procesar_stop(ids[0]))[0]


def test_clasificacion_despues_de_ronda_y_orden_acumulado():
    async def caso():
        gestor, ids = await preparar_partida()
        await cerrar_ronda(gestor, ids)
        resultado = gestor.serializar_resultados()
        assert resultado["clasificacion"][0]["puntos"] >= resultado["clasificacion"][1]["puntos"]
        gestor.jugadores[ids[1]]["total"] += 100
        assert gestor._clasificacion()[0]["id"] == ids[1]
    asyncio.run(caso())


def test_historial_guarda_jugadores_respuestas_resultados_y_totales():
    async def caso():
        gestor, ids = await preparar_partida()
        await cerrar_ronda(gestor, ids)
        ronda = gestor.serializar_resultados()["historial_global"][0]
        assert ronda["ronda"] == 1 and ronda["letra"] == "A"
        jugador = next(j for j in ronda["jugadores"] if j["id"] == ids[0])
        assert jugador["respuestas"]["nombre"] == "Andres"
        assert jugador["resultados"]["nombre"]["estado"] == "valida_unica"
        assert jugador["puntos_obtenidos"] > 0
        assert jugador["puntuacion_acumulada"] == jugador["puntos_obtenidos"]
    asyncio.run(caso())


def test_final_de_partida_clasificacion_y_estadisticas():
    async def caso():
        gestor, ids = await preparar_partida(rondas=1)
        await cerrar_ronda(gestor, ids)
        resultado = gestor.serializar_resultados()
        assert resultado["partida_terminada"] is True
        assert resultado["estadisticas"]["rondas_completadas"] == 1
        assert resultado["estadisticas"]["jugadores"] == 2
        assert resultado["estadisticas"]["puntos_distribuidos"] > 0
        assert resultado["clasificacion"]
    asyncio.run(caso())


def test_nueva_partida_reinicia_y_conserva_jugadores_y_anfitrion():
    async def caso():
        gestor, ids = await preparar_partida(rondas=1)
        await cerrar_ronda(gestor, ids)
        gestor.jugadores[ids[0]]["total"] = 125
        assert await gestor.iniciar_nueva_partida(ids[1]) == (False, "Solamente el anfitrión puede iniciar una nueva partida.")
        assert (await gestor.iniciar_nueva_partida(ids[0])) == (True, None)
        assert gestor.estado_juego == "SALA" and gestor.ronda_actual == 0
        assert gestor.historial_global == [] and gestor.letras_utilizadas == []
        assert not gestor.partida_terminada
        assert set(gestor.jugadores) == set(ids) and len(gestor.jugadores) == len(ids)
        assert all(j["total"] == 0 and j["historial"] == [] for j in gestor.jugadores.values())
        assert gestor.anfitrion_id == ids[0]
        assert gestor.serializar_sala()["jugadores"]
    asyncio.run(caso())


def test_frontend_presenta_partida_terminada_y_nueva_partida():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    assert "🏁 PARTIDA TERMINADA" in js
    assert "🔄 NUEVA PARTIDA" in js
    assert 'tipo: "nueva_partida"' in js
    assert 'tipo == "nueva_partida"' in Path("backend/web_server.py").read_text()


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Todas las pruebas de la fase 3 pasaron.")
