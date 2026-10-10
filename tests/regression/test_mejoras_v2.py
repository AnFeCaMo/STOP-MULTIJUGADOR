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
        "color": "Amarillo",
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


def test_partida_se_conserva_si_alguien_sigue_conectado():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.05)
        a, _ = await gestor.conectar(WS(), "Andres")
        b, _ = await gestor.conectar(WS(), "Ana")
        ok, _ = await gestor.iniciar_ronda(a)
        assert ok
        ws_a = gestor.jugadores[a]["ws"]
        await gestor.desconectar(ws_a)
        assert gestor.jugadores[a]["ws"] is None
        assert gestor.jugadores[b]["ws"] is not None
        await asyncio.sleep(0.08)
        assert b in gestor.jugadores
        assert gestor.ronda_actual == 1
        assert gestor.estado_juego == "JUEGO"
    asyncio.run(caso())


def test_sala_se_reinicia_si_todos_se_desconectan():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.05)
        ws_a = WS()
        a, _ = await gestor.conectar(ws_a, "Andres")
        ok, _ = await gestor.iniciar_ronda(a)
        assert ok
        await gestor.desconectar(ws_a)
        await asyncio.sleep(0.08)
        assert gestor.jugadores == {}
        assert gestor.espectadores == {}
        assert gestor.anfitrion_id is None
        assert gestor.estado_juego == "SALA"
        assert gestor.ronda_actual == 0
        assert gestor.historial_global == []
        assert gestor.letras_utilizadas == []
    asyncio.run(caso())


def test_reconexion_con_token_recupera_partida_durante_la_ventana():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.12)
        ws_a = WS()
        sesion_a, _ = await gestor.conectar_sesion(ws_a, "Andres")
        a = sesion_a["id"]
        token = gestor.jugadores[a]["token"]
        ok, _ = await gestor.iniciar_ronda(a)
        assert ok
        await gestor.desconectar(ws_a)
        await asyncio.sleep(0.03)
        ws_b = WS()
        sesion, error = await gestor.conectar_sesion(ws_b, "Andres", token)
        assert error is None
        assert sesion["id"] == a
        assert sesion["reconectado"] is True
        await asyncio.sleep(0.15)
        assert a in gestor.jugadores
        assert gestor.jugadores[a]["ws"] is ws_b
        assert gestor.ronda_actual == 1
    asyncio.run(caso())


def test_usuario_nuevo_no_hereda_partida_abandonada():
    async def caso():
        gestor = GestorJuego(ventana_reconexion=0.2)
        ws_a = WS()
        a, _ = await gestor.conectar(ws_a, "Andres")
        ok, _ = await gestor.iniciar_ronda(a)
        assert ok
        await gestor.desconectar(ws_a)
        ws_nuevo = WS()
        nuevo, error = await gestor.conectar_sesion(ws_nuevo, "Carlos")
        assert error is None
        assert nuevo["reconectado"] is False
        assert gestor.ronda_actual == 0
        assert gestor.estado_juego == "SALA"
        assert list(gestor.jugadores) == [nuevo["id"]]
        assert gestor.jugadores[nuevo["id"]]["nombre"] == "Carlos"
    asyncio.run(caso())
