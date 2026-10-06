import asyncio
import json
from pathlib import Path

from backend.servidor import CATEGORIAS, AVATARES, REACCIONES, GestorJuego


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(text)


def test_bateria_fases_30_34_backend_completa_y_regresion():
    async def caso():
        gestor = GestorJuego(duracion_ronda=60)
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        s1, e1 = await gestor.conectar_sesion(ws1, "Andrés", avatar="oso")
        s2, e2 = await gestor.conectar_sesion(ws2, "Yulesi", avatar="gato")
        assert e1 is None and e2 is None
        assert len(gestor.jugadores) == 2

        assert await gestor.actualizar_configuracion(s1["id"], 4, CATEGORIAS) == (True, None)
        assert (await gestor.iniciar_ronda(s1["id"]))[0]
        assert 0 < gestor.duracion_ronda <= 60
        gestor.letra_actual = "A"

        # Respuestas, estados y puntuación.
        await gestor.actualizar_respuestas(s1["id"], {
            "nombre": "Ana", "apellido": "Alonso", "ciudad": "Armenia",
            "fruta": "Arándano", "animal": "Águila", "cosa": "Anillo",
        })
        await gestor.actualizar_respuestas(s2["id"], {
            "nombre": "Ana", "apellido": "Acosta", "ciudad": "Armenia",
            "fruta": "Aguacate", "animal": "Ardilla", "cosa": "Avión",
        })
        assert all(
            gestor.jugadores[s1["id"]]["respuestas_ronda"][cat]
            for cat in CATEGORIAS
        )

        # STOP único y cierre; una segunda ejecución no debe reabrir la ronda.
        ok, error = await gestor.procesar_stop(s1["id"])
        assert ok is True and error is None
        assert gestor.estado_juego in {"RESULTADOS", "VOTACION"}
        estado_cerrado = gestor.estado_juego
        ok2, _ = await gestor.procesar_stop(s2["id"])
        assert ok2 is False
        assert gestor.estado_juego == estado_cerrado

        # Si hubiera votación, completar con votos válidos; no se puede votar
        # la propia respuesta ni repetir un voto.
        if gestor.estado_juego == "VOTACION":
            pendientes = list(gestor.votaciones.values())
            for candidato in pendientes:
                clave = candidato["clave"]
                autor = next(iter(candidato["autores"]))
                votante = s2["id"] if autor == s1["id"] else s1["id"]
                assert gestor.registrar_voto(autor, clave, True)[0] is False
                assert gestor.registrar_voto(votante, clave, True)[0] is True
                assert gestor.registrar_voto(votante, clave, True)[0] is False
            assert gestor.estado_juego == "RESULTADOS"

        resultados = gestor.serializar_resultados()
        assert resultados["tipo"] == "resultados"
        assert "clasificacion" in resultados
        assert "historial_global" in resultados

        # Limpieza de estado temporal y nueva partida.
        gestor.partida_terminada = True
        gestor.estado_juego = "RESULTADOS"
        ok, error = await gestor.iniciar_nueva_partida(s1["id"])
        assert ok and error is None
        assert gestor.estado_juego == "SALA"
        assert gestor.ronda_actual == 0
        assert gestor.letras_utilizadas == []
        assert all(j["total"] == 0 for j in gestor.jugadores.values())

    asyncio.run(caso())


def test_auditoria_final_frontend_recursos_locales_y_seguridad():
    root = Path(__file__).resolve().parents[1]
    js = (root / "frontend/app.js").read_text(encoding="utf-8")
    html = (root / "frontend/index.html").read_text(encoding="utf-8")
    css = (root / "frontend/style.css").read_text(encoding="utf-8")
    backend = (root / "backend/servidor.py").read_text(encoding="utf-8")
    web = (root / "backend/web_server.py").read_text(encoding="utf-8")

    for texto in [
        "localStorage", "WebSocket", "AudioContext", "animarLetraRonda",
        "lanzarConfeti", "mostrarEfectoStop", "REACCIONES", "AVATARES",
        "temporizador", "codigo_sala", "accion_sala", "podio", "rey-del-stop",
    ]:
        assert texto in (js + html + css + backend + web)

    assert 'TIEMPO_PARA_MARCAR_AUSENTE = 300' in backend
    assert 'TIEMPO_STOP_RELAMPAGO = 5' in backend
    assert 'duracion_ronda: int = 60' in backend
    assert 'secrets.token_urlsafe(32)' in backend
    assert 'if jugador_id != self.anfitrion_id' in backend
    assert "pythonpath = ." in (root / "pytest.ini").read_text()
