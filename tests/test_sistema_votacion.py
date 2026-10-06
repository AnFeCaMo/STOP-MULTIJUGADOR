import asyncio
from pathlib import Path

from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_votacion_cuenta_votos_bloquea_autor_duplicado_y_cierre():
    async def caso():
        gestor = GestorJuego()
        sesiones = []
        for nombre in ("Andres", "Ana", "Alberto"):
            sesion, error = await gestor.conectar_sesion(FakeWebSocket(), nombre)
            assert error is None
            sesiones.append(sesion["id"])

        assert (await gestor.iniciar_ronda(sesiones[0]))[0]
        gestor.letra_actual = "A"
        respuestas = {
            sesiones[0]: {"nombre": "Andres", "fruta": "Arazá"},
            sesiones[1]: {"nombre": "Ana", "fruta": "Arandano"},
            sesiones[2]: {"nombre": "Alberto", "fruta": "Aguacate"},
        }
        for jugador_id, valores in respuestas.items():
            await gestor.actualizar_respuestas(jugador_id, valores)
        assert (await gestor.procesar_stop(sesiones[0]))[0]
        assert gestor.estado_juego == "VOTACION"

        clave = "fruta:ARAZA"
        candidato_ana = next(
            item for item in gestor.serializar_votacion_para(sesiones[1])["candidatos"]
            if item["clave"] == clave
        )
        assert candidato_ana["votos_si"] == 0
        assert candidato_ana["votos_no"] == 0
        assert candidato_ana["puede_votar"] is True

        candidato_autor = next(
            item for item in gestor.serializar_votacion_para(sesiones[0])["candidatos"]
            if item["clave"] == clave
        )
        assert candidato_autor["puede_votar"] is False
        assert gestor.registrar_voto(sesiones[0], clave, True) == (
            False, "No puedes votar tu propia respuesta."
        )

        assert gestor.registrar_voto(sesiones[1], clave, True) == (True, None)
        assert gestor.registrar_voto(sesiones[1], clave, False) == (
            False, "Ya votaste por esta respuesta."
        )
        voto_ana = next(
            item for item in gestor.serializar_votacion_para(sesiones[1])["candidatos"]
            if item["clave"] == clave
        )
        assert voto_ana["votos_si"] == 1
        assert voto_ana["votos_no"] == 0
        assert voto_ana["ya_voto"] is True
        assert voto_ana["puede_votar"] is False

        assert gestor.registrar_voto(sesiones[2], clave, True) == (True, None)
        assert gestor.estado_juego == "RESULTADOS"
        assert gestor.registrar_voto(sesiones[1], clave, False) == (
            False, "La fase de votación ya terminó."
        )

    asyncio.run(caso())


def test_interfaz_muestra_votos_y_bloquea_interaccion_duplicada_o_del_autor():
    js = Path("frontend/app.js").read_text()
    html = Path("frontend/index.html").read_text()

    assert 'const votos = `SÍ: ${candidato.votos_si || 0} · NO: ${candidato.votos_no || 0}' in js
    assert "¿Aceptar esta respuesta?" in js
    assert 'if (card) card.querySelectorAll("button[data-voto]").forEach((b) => b.disabled = true)' in js
    assert "candidato.ya_voto" in js
    assert "candidato.autores" in js
    assert 'class="titulo-seccion">🗳️ VOTACIÓN' in html
