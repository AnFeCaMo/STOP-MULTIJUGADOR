import asyncio
from pathlib import Path

from backend.servidor import GestorJuego, TIEMPO_STOP_RELAMPAGO, UMBRAL_PUNTOS_EXPERTO


class FakeWebSocket:
    pass


def test_catalogo_completo_y_condiciones_de_nuevos_logros():
    async def caso():
        gestor = GestorJuego()
        host, _ = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        otro, _ = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        host_id, otro_id = host["id"], otro["id"]
        gestor.jugadores[host_id]["total"] = UMBRAL_PUNTOS_EXPERTO
        gestor.jugadores[host_id]["cantidad_stop"] = 3
        gestor.jugadores[otro_id]["total"] = 100
        gestor.partida_terminada = True
        gestor.historial_global = [
            {
                "ronda": ronda,
                "duracion_segundos": TIEMPO_STOP_RELAMPAGO,
                "stopper_id": host_id,
                "categorias": ["nombre"],
                "puntuaciones": {"Andres": 10, "Ana": 5},
                "jugadores": [
                    {
                        "id": host_id,
                        "respuestas": {"nombre": "Andres"},
                        "resultados": {"nombre": {"estado": "valida_unica"}},
                        "puntos_obtenidos": 10,
                    },
                    {
                        "id": otro_id,
                        "respuestas": {"nombre": "Ana"},
                        "resultados": {"nombre": {"estado": "valida_unica"}},
                        "puntos_obtenidos": 5,
                    },
                ],
            }
            for ronda in range(1, 4)
        ]

        ids_logros = {logro["id"] for logro in gestor._logros_jugador(host_id)}
        assert ids_logros == {
            "primera_victoria",
            "respuesta_rapida",
            "racha_tres",
            "todas_validas",
            "rey_stop",
            "campeon",
            "experto",
            "stop_relampago",
        }

        gestor.partida_terminada = False
        gestor.jugadores[host_id]["total"] = UMBRAL_PUNTOS_EXPERTO - 1
        for ronda in gestor.historial_global:
            ronda["duracion_segundos"] = TIEMPO_STOP_RELAMPAGO + 1
        ids_logros = {logro["id"] for logro in gestor._logros_jugador(host_id)}
        assert "campeon" not in ids_logros
        assert "experto" not in ids_logros
        assert "stop_relampago" not in ids_logros

    asyncio.run(caso())


def test_logro_nuevo_muestra_animacion_y_se_registra_para_evitar_repeticiones():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert "function notificarLogrosNuevos(logros)" in js
    assert "logros.filter((logro) => logro.id && !logrosPrevios.has(logro.id))" in js
    assert "localStorage.setItem(claveLogros," in js
    assert '"🔓"' in js
    assert '"✨ LOGRO DESBLOQUEADO ✨"' in js
    assert 'nuevos.map((logro) => `${logro.icono} ${logro.nombre}`).join(" · ")' in js
    assert 'mostrarEfectoJuego(' in js
    assert ".efecto-logro .efecto-titulo" in css
