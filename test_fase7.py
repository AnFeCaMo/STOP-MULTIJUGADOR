"""Comprobaciones estructurales de UX/UI (fase 7)."""

from pathlib import Path


def test_pantallas_y_controles_principales_estan_presentes():
    html = Path("frontend/index.html").read_text()
    for pantalla in ("login", "sala", "juego", "votacion", "resultados"):
        assert f'id="pantalla-{pantalla}"' in html
    assert 'href="favicon.svg"' in html and Path("frontend/favicon.svg").is_file()
    for control in (
        "btn-iniciar-ronda", "btn-stop", "confirm-stop-modal", "contenedor-votaciones",
        "tbody-resultados", "contenedor-clasificacion", "contenedor-historial-completo",
        "estadisticas-generales", "estadisticas-jugadores", "btn-nueva-ronda",
    ):
        assert f'id="{control}"' in html


def test_accesibilidad_y_estilos_adaptables():
    html = Path("frontend/index.html").read_text()
    css = Path("frontend/style.css").read_text()
    js = Path("frontend/app.js").read_text()
    assert 'role="dialog"' in html and 'aria-live="polite"' in html
    assert "Completa las categorías activas" in html
    assert "focus-visible" in css
    assert ".hidden {\n  display: none !important;" in css
    assert "max-width: 860px" in css and "max-width: 560px" in css
    assert "prefers-reduced-motion" in css
    assert ".config-categorias" in css and ".estadistica-jugador" in css
    assert 'if (msg.estado === "SALA")' in js


if __name__ == "__main__":
    for nombre, prueba in sorted(globals().items()):
        if nombre.startswith("test_") and callable(prueba):
            prueba()
    print("Las comprobaciones de UX/UI pasaron.")
