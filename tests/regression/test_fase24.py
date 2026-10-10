from pathlib import Path


def test_confeti_es_ligero_deduplicado_y_respeta_eventos_de_celebracion():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()
    readme = Path("README.md").read_text()

    assert "const eventosConfeti = new Set();" in js
    assert "function lanzarConfeti(claveEvento = \"celebracion\")" in js
    assert "if (eventosConfeti.has(claveEvento)) return;" in js
    assert "eventosConfeti.clear();" in js
    assert 'lanzarConfeti(`victoria:${numRonda}:${miJugador.id}:${miJugador.total}`)' in js
    assert 'lanzarConfeti(`ronda-perfecta:${numRonda}:${participantes.join(",")}`)' in js
    assert 'lanzarConfeti(`logros:${tokenSesion || miId}:' in js
    assert "i < 42" in js
    assert "setTimeout(() => contenedor.remove(), 3600)" in js
    assert ".confeti-contenedor { display: none; }" in css
    assert "confeti" in readme.lower()
