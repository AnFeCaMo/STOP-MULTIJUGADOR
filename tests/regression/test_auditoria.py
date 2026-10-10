"""Casos de escala de la auditoría final, sin añadir lógica de juego."""

import asyncio

from backend.servidor import CATEGORIAS, GestorJuego


class FakeWebSocket:
    pass


def test_sala_y_ronda_con_2_5_y_10_jugadores_sin_duplicados():
    async def caso(cantidad):
        gestor = GestorJuego()
        sesiones = []
        for indice in range(cantidad):
            sesion, error = await gestor.conectar_sesion(FakeWebSocket(), f"Jugador {indice + 1}")
            assert error is None
            sesiones.append(sesion)
        ids = [sesion["id"] for sesion in sesiones]
        assert len(set(ids)) == cantidad
        assert len(gestor.serializar_sala()["jugadores"]) == cantidad
        assert await gestor.actualizar_configuracion(ids[0], 4, CATEGORIAS) == (True, None)
        assert (await gestor.iniciar_ronda(ids[0]))[0]
        ronda = gestor.serializar_ronda()
        assert len(ronda["jugadores"]) == cantidad
        assert all(
            gestor.serializar_estado_para(jugador_id)["letra"] == ronda["letra"]
            for jugador_id in ids
        )
    for cantidad in (2, 5, 10):
        asyncio.run(caso(cantidad))


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Los casos de escala de la auditoría pasaron.")
