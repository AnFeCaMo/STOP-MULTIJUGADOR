from pathlib import Path


def test_podio_final_muestra_tres_puestos_solo_al_finalizar():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'id="podio-final"' in html
    assert "function renderizarPodio(ranking, partidaTerminada)" in js
    assert 'podio.classList.toggle("hidden", !partidaTerminada || ranking.length === 0);' in js
    for medalla, etiqueta in (
        ("🥇", "Primer lugar"),
        ("🥈", "Segundo lugar"),
        ("🥉", "Tercer lugar"),
    ):
        assert medalla in js
        assert etiqueta in js
    assert "👑 Ganador" in js
    assert ".podio-personaje" in css
    assert "@keyframes salto-podio" in css
