from pathlib import Path


def test_controles_de_musica_y_volumen_persisten_y_controlan_web_audio():
    js = Path("frontend/app.js").read_text()
    html = Path("frontend/index.html").read_text()

    assert 'id="btn-musica"' in html
    assert 'onclick="alternarMusica()"' in html
    assert 'id="volumen-audio"' in html
    assert 'function alternarMusica()' in js
    assert 'function iniciarMusicaConcentracion()' in js
    assert 'function detenerMusicaConcentracion()' in js
    assert 'localStorage.setItem("stop_musica"' in js
    assert 'localStorage.setItem("stop_volumen_audio"' in js
    assert "gananciaMusica.gain.setTargetAtTime" in js
    assert 'ctx.createOscillator()' in js


def test_efectos_cubren_votacion_resultados_victoria_derrota_y_logros():
    js = Path("frontend/app.js").read_text()
    html = Path("frontend/index.html").read_text()

    for sonido in ('votacion:', 'resultados:', 'ganador:', 'derrota:', 'logro:'):
        assert sonido in js
    assert 'reproducirSonido("votacion")' in js
    assert 'reproducirSonido("resultados")' in js
    assert 'reproducirSonido(ganoPartida ? "ganador" : "derrota")' in js
    assert 'reproducirSonido("logro")' in js
    assert 'reproducirSonido("alerta")' in js
    assert 'reproducirSonido("impacto")' in js
    assert 'reproducirSonido("suspenso")' in js
    assert 'aria-pressed="false"' in html
