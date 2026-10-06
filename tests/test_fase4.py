"""Pruebas de configuración de partida (fase 4)."""

import asyncio
from pathlib import Path

from backend.servidor import CATEGORIAS, GestorJuego


class FakeWebSocket:
    pass


async def sala():
    gestor = GestorJuego()
    sesiones = []
    for nombre in ("Andres", "Ana"):
        sesion, error = await gestor.conectar_sesion(FakeWebSocket(), nombre)
        assert error is None
        sesiones.append(sesion)
    return gestor, [s["id"] for s in sesiones]


def test_rondas_minimo_medio_y_maximo_validos():
    async def caso():
        gestor, ids = await sala()
        for cantidad in (4, 5, 10):
            assert await gestor.actualizar_configuracion(ids[0], cantidad, CATEGORIAS) == (True, None)
            assert gestor.serializar_sala()["configuracion"]["rondas"] == cantidad
    asyncio.run(caso())


def test_rechaza_rondas_fuera_del_rango():
    async def caso():
        gestor, ids = await sala()
        for cantidad in (0, 1, 2, 3, 11, 99):
            ok, error = await gestor.actualizar_configuracion(ids[0], cantidad, CATEGORIAS)
            assert not ok and "entre 4 y 10" in error
    asyncio.run(caso())


def test_configuracion_de_categorias_y_minimo():
    async def caso():
        gestor, ids = await sala()
        activas = ["nombre", "ciudad", "animal"]
        assert await gestor.actualizar_configuracion(ids[0], 5, activas) == (True, None)
        assert gestor.categorias_activas == activas
        ok, error = await gestor.actualizar_configuracion(ids[0], 5, ["nombre", "ciudad"])
        assert not ok and "al menos 3" in error
        ok, error = await gestor.actualizar_configuracion(ids[0], 5, ["nombre", "nombre", "ciudad"])
        assert not ok and "inválidas" in error
    asyncio.run(caso())


def test_solo_anfitrion_configura_y_se_bloquea_al_iniciar():
    async def caso():
        gestor, ids = await sala()
        ok, error = await gestor.actualizar_configuracion(ids[1], 6, CATEGORIAS)
        assert not ok and "anfitrión" in error
        assert (await gestor.actualizar_configuracion(ids[0], 6, CATEGORIAS))[0]
        assert (await gestor.iniciar_ronda(ids[0]))[0]
        ok, error = await gestor.actualizar_configuracion(ids[0], 7, CATEGORIAS)
        assert not ok and "bloqueada" in error
    asyncio.run(caso())


def test_nueva_partida_reinicia_configuracion_por_defecto():
    async def caso():
        gestor, ids = await sala()
        await gestor.actualizar_configuracion(ids[0], 8, ["nombre", "ciudad", "animal"])
        gestor.partida_terminada = True
        gestor.estado_juego = "RESULTADOS"
        assert (await gestor.iniciar_nueva_partida(ids[0]))[0]
        assert gestor.rondas_totales == 4
        assert gestor.categorias_activas == CATEGORIAS
        config = gestor.serializar_sala()["configuracion"]
        assert config["rondas"] == 4 and config["categorias"] == CATEGORIAS
    asyncio.run(caso())


def test_interfaz_muestra_configuracion_solo_editable_por_host():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    assert all(f"<option>{n}</option>" in html for n in range(4, 11))
    assert 'value="nombre" checked' in html and 'value="cosa" checked' in html
    assert "guardarConfiguracion" in js and 'tipo: "configuracion"' in js
    assert "selector.disabled = !editable" in js


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Todas las pruebas de la fase 4 pasaron.")
