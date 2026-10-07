import asyncio
from pathlib import Path

from backend.servidor import GestorJuego
from backend.web_server import (
    MAX_JUGADORES_POR_SALA,
    MAX_MENSAJE_BYTES,
    MAX_NOMBRE,
    GestorSalas,
    app,
)


class FakeWebSocket:
    pass


def test_v5_arranca_sin_salas_y_healthcheck_esta_registrado():
    manager = GestorSalas()
    assert manager.salas == {}
    rutas = {getattr(route, "path", None): getattr(route, "methods", set()) for route in app.routes}
    assert "/health" in rutas
    assert "GET" in rutas["/health"]


def test_v5_gestor_de_salas_es_unico_y_elimina_salas_vacias():
    manager = GestorSalas()
    codigo, sala, error = manager.crear()
    assert error is None
    assert manager.obtener(codigo) is sala
    manager.eliminar(codigo, sala)
    assert manager.obtener(codigo) is None
    assert manager.salas == {}


def test_v5_backend_rechaza_nombre_mayor_al_limite():
    async def caso():
        sala = GestorJuego()
        sesion, error = await sala.conectar_sesion(FakeWebSocket(), "A" * (MAX_NOMBRE + 1))
        assert sesion is None
        assert error == f"El nombre no puede superar {MAX_NOMBRE} caracteres."
        assert sala.jugadores == {}

    asyncio.run(caso())


def test_v5_limite_de_jugadores_se_puede_configurar_en_servidor():
    assert MAX_JUGADORES_POR_SALA >= 2
    assert MAX_MENSAJE_BYTES >= 64 * 1024


def test_v5_no_hay_referencias_a_sala_predeterminada_ni_motor_duplicado():
    root = Path(__file__).parents[1]
    textos = []
    for path in [root / "backend/web_server.py", root / "frontend/app.js", root / "frontend/index.html"]:
        textos.append(path.read_text(encoding="utf-8"))
    assert "7K4P" not in "\n".join(textos)
    assert not (root / "backend/v4_game.py").exists()


def test_v5_musica_de_fondo_es_local_y_no_requiere_servicio_de_pago():
    js = (Path(__file__).parents[1] / "frontend/app.js").read_text(encoding="utf-8")
    assert 'localStorage.getItem("stop_musica") !== "0"' in js
    assert "function iniciarMusicaConcentracion()" in js
    assert "ctx.createOscillator()" in js
    assert "window.AudioContext" in js
