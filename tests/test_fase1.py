"""Pruebas de la experiencia completa de una ronda (fase 1)."""

import asyncio
from pathlib import Path

from backend.servidor import CATEGORIAS, GestorJuego


class FakeWebSocket:
    pass


async def crear_partida(nombres=("Andres", "Ana"), duracion=60):
    gestor = GestorJuego(duracion_ronda=duracion)
    ids = []
    for nombre in nombres:
        jugador_id, error = await gestor.conectar(FakeWebSocket(), nombre)
        assert error is None
        ids.append(jugador_id)
    ok, error = await gestor.iniciar_ronda(ids[0])
    assert ok and error is None
    gestor.letra_actual = "A"
    return gestor, ids


def respuestas(nombre, **overrides):
    resultado = {
        "nombre": nombre,
        "apellido": "Acosta",
        "ciudad": "Armenia",
        "fruta": "Arandano",
        "animal": "Aguila",
        "cosa": "Anillo",
    }
    resultado.update(overrides)
    return resultado


def test_temporizador_dura_60_segundos_y_se_serializa():
    async def caso():
        gestor, ids = await crear_partida(duracion=60)
        assert round(gestor.vence_en - __import__("time").time()) in (59, 60)
        assert gestor.serializar_ronda()["vence_en"] == gestor.vence_en
    asyncio.run(caso())


def test_finalizacion_automatica_por_tiempo_y_respuestas_bloqueadas():
    async def caso():
        gestor, ids = await crear_partida(duracion=0.02)
        await gestor.actualizar_respuestas(ids[0], respuestas("Andres"))
        await asyncio.sleep(0.03)
        assert await gestor.finalizar_por_tiempo(gestor.ronda_actual)
        estado_final = gestor.jugadores[ids[0]]["respuestas_ronda"].copy()
        await gestor.actualizar_respuestas(ids[0], respuestas("Alberto"))
        assert gestor.jugadores[ids[0]]["respuestas_ronda"] == estado_final
        ok, error = await gestor.procesar_stop(ids[0], respuestas("Ana"))
        assert not ok and error
        assert gestor.estado_juego == "RESULTADOS"
        assert gestor.serializar_resultados()["motivo_cierre"] == "tiempo"
    asyncio.run(caso())


def test_respuesta_que_llega_despues_del_plazo_cierra_la_ronda():
    async def caso():
        gestor, ids = await crear_partida(duracion=0.02)
        await asyncio.sleep(0.03)
        assert await gestor.actualizar_respuestas(ids[0], respuestas("Andres")) is True
        assert gestor.estado_juego == "RESULTADOS"
        assert await gestor.finalizar_por_tiempo(gestor.ronda_actual) is False
    asyncio.run(caso())


def test_stop_cierra_una_sola_vez_e_incluye_anuncio():
    async def caso():
        gestor, ids = await crear_partida()
        for jugador_id, nombre in zip(ids, ("Andres", "Ana")):
            await gestor.actualizar_respuestas(jugador_id, respuestas(nombre))
        ok, error = await gestor.procesar_stop(ids[0], respuestas("Andres"))
        assert ok and error is None
        assert gestor.quien_stop == "Andres"
        assert gestor.serializar_resultados()["motivo_cierre"] == "stop"
        assert gestor.serializar_resultados()["stopper_id"] == ids[0]
        ok, _ = await gestor.procesar_stop(ids[1], respuestas("Ana"))
        assert not ok
    asyncio.run(caso())


def test_confirmacion_stop_presente_en_interfaz():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    assert "¿Seguro que quieres terminar la ronda?" in html
    assert "CANCELAR" in html and "CONFIRMAR STOP" in html
    assert "function confirmarStop()" in js and "function cancelarStop()" in js


def test_respuesta_conocida_auto_y_desconocida_a_votacion_con_resultados_individuales():
    async def caso():
        gestor, ids = await crear_partida(nombres=("Andres", "Ana", "Alberto"))
        await gestor.actualizar_respuestas(ids[0], respuestas("Andres", fruta="Arazá"))
        await gestor.actualizar_respuestas(ids[1], respuestas("Ana"))
        await gestor.actualizar_respuestas(ids[2], respuestas("Alberto", fruta="Aguacate"))
        ok, _ = await gestor.procesar_stop(ids[0])
        assert ok and gestor.estado_juego == "VOTACION"
        clave = "fruta:ARAZA"
        candidato = gestor.votaciones[clave]
        assert ids[0] not in candidato["votantes"]
        assert ids[1] in candidato["votantes"]
        assert gestor.registrar_voto(ids[0], clave, True) == (False, "No puedes votar tu propia respuesta.")
        assert gestor.registrar_voto(ids[1], clave, True) == (True, None)
        voto_propio = gestor.serializar_votacion_para(ids[1])["candidatos"]
        assert next(c for c in voto_propio if c["clave"] == clave)["ya_voto"] is True
        assert gestor.registrar_voto(ids[1], clave, False) == (False, "Ya votaste por esta respuesta.")
        assert gestor.registrar_voto(ids[2], clave, True) == (True, None)
        assert gestor.estado_juego == "RESULTADOS"
        detalle = gestor.jugadores[ids[0]]["detalle_respuestas"]
        assert detalle["nombre"]["estado"] == "valida_unica"
        assert gestor.jugadores[ids[1]]["detalle_respuestas"]["fruta"]["estado"] == "valida_unica"
        assert detalle["fruta"]["estado"] == "votada_unica"
        assert detalle["fruta"]["puntos"] == 10
        assert detalle["apellido"]["estado"] == "valida_repetida"
        assert detalle["apellido"]["puntos"] == 5
        assert gestor.jugadores[ids[0]]["total"] == gestor.jugadores[ids[0]]["puntos_ronda"]
        assert set(detalle) == set(CATEGORIAS)
        total_primera = gestor.jugadores[ids[0]]["total"]
        assert (await gestor.iniciar_ronda(ids[0]))[0]
        gestor.letra_actual = "A"
        for jugador_id, nombre in zip(ids, ("Andres", "Ana")):
            await gestor.actualizar_respuestas(jugador_id, respuestas(nombre))
        assert (await gestor.procesar_stop(ids[0]))[0]
        assert gestor.jugadores[ids[0]]["total"] == total_primera + gestor.jugadores[ids[0]]["puntos_ronda"]
    asyncio.run(caso())


def test_votacion_no_y_empate_rechazan_resposta():
    async def caso(votos):
        gestor, ids = await crear_partida(nombres=("Andres", "Ana", "Alberto"))
        await gestor.actualizar_respuestas(ids[0], respuestas("Andres", fruta="Arazá"))
        await gestor.actualizar_respuestas(ids[1], respuestas("Ana"))
        await gestor.actualizar_respuestas(ids[2], respuestas("Alberto"))
        await gestor.procesar_stop(ids[0])
        clave = "fruta:ARAZA"
        assert ids[0] not in gestor.votaciones[clave]["votantes"]
        for voter_id, voto in zip(gestor.votaciones[clave]["votantes"], votos):
            assert gestor.registrar_voto(voter_id, clave, voto)[0]
        assert gestor.estado_juego == "RESULTADOS"
        assert gestor.jugadores[ids[0]]["detalle_respuestas"]["fruta"]["puntos"] == 0
        assert gestor.votaciones == {}
        detalle_votacion = next(
            detalle for detalle in gestor._detalles_votacion_final
            if detalle["clave"] == clave
        )
        assert detalle_votacion["aprobada"] is False

    asyncio.run(caso([False, False]))
    asyncio.run(caso([True, False]))


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Todas las pruebas de la fase 1 pasaron.")
