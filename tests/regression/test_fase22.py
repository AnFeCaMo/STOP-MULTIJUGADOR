from pathlib import Path


def test_podio_final_muestra_tres_puestos_solo_al_finalizar():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'id="podio-final"' in html
    assert "function renderizarPodio(ranking, partidaTerminada)" in js
    assert 'podio.classList.toggle("hidden", !partidaTerminada || ranking.length === 0);' in js
    for etiqueta in (
        "Primer lugar",
        "Segundo lugar",
        "Tercer lugar",
    ):
        assert etiqueta in js
    assert 'class="podio-medalla" aria-hidden="true">👑</span>' in js
    assert 'content: "PRIMER PUESTO · GANADOR"' in css
    assert 'content: "SEGUNDO PUESTO"' in css
    assert 'content: "TERCER PUESTO"' in css
    assert ".podio-personaje" in css
    assert ".podio-celebracion { animation: salto-podio" in css
