"""Pruebas de avisos animados de entrada, salida y reconexión (fase 10)."""

from pathlib import Path


def test_servidor_emite_mensajes_y_tipos_de_evento_especificos():
    servidor = Path("backend/web_server.py").read_text()

    assert 'evento = "entrada"' in servidor
    assert 'evento = "reconexion"' in servidor
    assert 'evento": "salida"' in servidor
    assert 'f"✨ 👋 ¡{sesion[\'nombre\']} se ha unido!"' in servidor
    assert 'f"🔄 ¡{sesion[\'nombre\']} se reconectó!"' in servidor
    assert 'f"👋 {nombre_desconectado} abandonó la partida."' in servidor


def test_frontend_muestra_avisos_animados_de_jugador_y_limpia_timer_anterior():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert "function mostrarNotificacionJugador(mensaje)" in js
    assert "toastTimeout = setTimeout" in js
    assert "clearTimeout(toastTimeout)" in js
    assert 'toast-notificacion-jugador toast-${evento}' in js
    assert "@keyframes avisoEntradaJugador" in css
    assert "@keyframes avisoSalidaJugador" in css
    assert ".toast-reconexion" in css


def test_readme_documenta_notificaciones_de_presencia():
    readme = Path("README.md").read_text()

    assert "se ha unido" in readme
    assert "abandonó la partida" in readme
    assert "se reconectó" in readme
