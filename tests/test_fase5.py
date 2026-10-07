"""Pruebas de letras sin repetición y ronda perfecta (fase 5)."""

import asyncio

from backend.servidor import CATEGORIAS, LETRAS_DISPONIBLES, GestorJuego


class FakeWebSocket:
    pass


RESPUESTAS_A = {
    "nombre": "Andres", "apellido": "Acosta", "ciudad": "Armenia",
    "fruta": "Arandano", "animal": "Aguila", "cosa": "Anillo",
}


async def gestor_con_host():
    gestor = GestorJuego()
    sesion, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
    assert error is None
    return gestor, sesion["id"]


def test_letras_unicas_en_partidas_de_4_y_10_rondas():
    async def caso(total):
        gestor, host = await gestor_con_host()
        gestor.rondas_totales = total
        seleccionadas = []
        for _ in range(total):
            assert (await gestor.iniciar_ronda(host))[0]
            seleccionadas.append(gestor.letra_actual)
            gestor.estado_juego = "RESULTADOS"
        assert len(seleccionadas) == len(set(seleccionadas)) == total
        assert gestor.letras_utilizadas == seleccionadas
    asyncio.run(caso(4))
    asyncio.run(caso(10))


def test_no_repite_y_falla_claramente_si_no_quedan_letras():
    async def caso():
        gestor, host = await gestor_con_host()
        gestor.letras_disponibles = ["A"]
        gestor.rondas_totales = 4
        assert (await gestor.iniciar_ronda(host))[0]
        gestor.estado_juego = "RESULTADOS"
        ok, error = await gestor.iniciar_ronda(host)
        assert not ok and "No quedan letras" in error
        assert gestor.letras_utilizadas == ["A"]
    asyncio.run(caso())


def test_nueva_partida_reinicia_letras_utilizadas():
    async def caso():
        gestor, host = await gestor_con_host()
        gestor.rondas_totales = 1
        assert (await gestor.iniciar_ronda(host))[0]
        gestor.estado_juego = "RESULTADOS"
        gestor.partida_terminada = True
        assert (await gestor.iniciar_nueva_partida(host))[0]
        assert gestor.letras_utilizadas == []
        assert gestor.letras_disponibles == list(LETRAS_DISPONIBLES)
    asyncio.run(caso())


def test_ronda_perfecta_separa_subtotal_bonus_y_acumulado():
    async def caso():
        gestor, host = await gestor_con_host()
        assert (await gestor.iniciar_ronda(host))[0]
        gestor.letra_actual = "A"
        gestor.jugadores[host]["respuestas_ronda"] = dict(RESPUESTAS_A)
        assert (await gestor.procesar_stop(host))[0]
        jugador = gestor.jugadores[host]
        assert jugador["puntos_categorias"] == 60
        assert jugador["bonus_ronda"] == 10
        assert jugador["puntos_ronda"] == 70
        assert jugador["total"] == 70
        ronda = gestor.historial_global[-1]["jugadores"][0]
        assert ronda["ronda_perfecta"] is True and ronda["bonus"] == 10
        publicado = gestor.serializar_resultados()["jugadores"][0]
        assert publicado["puntos_categorias"] == 60 and publicado["bonus_ronda"] == 10
    asyncio.run(caso())


def test_ronda_no_perfecta_no_recibe_bonus():
    async def caso():
        gestor, host = await gestor_con_host()
        assert (await gestor.iniciar_ronda(host))[0]
        gestor.letra_actual = "A"
        respuestas = dict(RESPUESTAS_A, cosa="Pedro")
        gestor.jugadores[host]["respuestas_ronda"] = respuestas
        assert (await gestor.procesar_stop(host))[0]
        jugador = gestor.jugadores[host]
        assert jugador["bonus_ronda"] == 0
        assert jugador["puntos_ronda"] == jugador["puntos_categorias"] < 60
        assert gestor.historial_global[-1]["jugadores"][0]["ronda_perfecta"] is False
    asyncio.run(caso())


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Todas las pruebas de la fase 5 pasaron.")
