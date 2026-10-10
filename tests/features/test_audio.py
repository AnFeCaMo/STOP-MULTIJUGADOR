from pathlib import Path

from fastapi.testclient import TestClient

from backend.web_server import app


ROOT = Path(__file__).parents[2]


def test_cancion_local_es_la_musica_de_fondo_en_bucle():
    js = (ROOT / "frontend/app.js").read_text()
    html = (ROOT / "frontend/index.html").read_text()
    server = (ROOT / "backend/web_server.py").read_text()

    assert 'id="musica-fondo" src="/audio/background.mp3" loop' in html
    assert '"/audio/background.mp3"' in server
    assert '"assets", "audio", "background.mp3"' in server
    assert 'reproductorMusica.play()' in js
    assert 'reproductorMusica?.pause()' in js
    assert 'reproductorMusica.volume = volumenMusica' in js


def test_servidor_entrega_la_cancion_local():
    cancion = ROOT / "frontend/assets/audio/background.mp3"
    respuesta = TestClient(app).get("/audio/background.mp3")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "audio/mpeg"
    assert len(respuesta.content) == cancion.stat().st_size


def test_controles_de_musica_y_volumen_persisten():
    js = (ROOT / "frontend/app.js").read_text()
    html = (ROOT / "frontend/index.html").read_text()
    css = (ROOT / "frontend/style.css").read_text()

    assert 'id="btn-musica"' in html
    assert 'onclick="alternarMusica()"' in html
    assert 'id="btn-sonido"' in html
    assert 'id="volumen-musica"' in html
    assert 'id="volumen-sonido"' in html
    assert 'class="controles-audio-globales"' in html
    assert 'href="style.css?' in html
    assert "#controles-audio-globales" in css
    assert "position: fixed" in css
    assert 'function alternarMusica()' in js
    assert 'function alternarSonido()' in js
    assert 'function iniciarMusicaFondo()' in js
    assert 'function detenerMusicaFondo()' in js
    assert 'localStorage.setItem("stop_musica"' in js
    assert 'localStorage.setItem("stop_volumen_musica"' in js
    assert 'localStorage.setItem("stop_volumen_sonido"' in js
    assert 'mostrarControlVolumen("musica")' in js
    assert 'mostrarControlVolumen("sonido")' in js
    assert 'setTimeout(() => ocultarControlVolumen(opcion), 3000)' in js
    assert 'programarOcultarControlVolumen("musica")' in js
    assert 'programarOcultarControlVolumen("sonido")' in js


def test_efectos_de_juego_siguen_separados_con_web_audio():
    js = (ROOT / "frontend/app.js").read_text()
    html = (ROOT / "frontend/index.html").read_text()

    for sonido in ('votacion:', 'resultados:', 'ganador:', 'derrota:', 'logro:'):
        assert sonido in js
    assert 'reproducirSonido("votacion")' in js
    assert 'reproducirSonido("resultados")' in js
    assert 'reproducirSonido(ganoPartida ? "ganador" : "derrota")' in js
    assert 'reproducirSonido("logro")' in js
    assert 'reproducirSonido("alerta")' in js
    assert 'reproducirSonido("impacto")' in js
    assert 'ctx.createOscillator()' in js
    assert 'aria-pressed="true"' in html


def test_audio_se_inicia_tras_interaccion_y_persiste_preferencias():
    js = (ROOT / "frontend/app.js").read_text()
    assert 'function desbloquearAudio()' in js
    assert 'ctx.resume()' in js
    assert '"pointerdown", "touchstart", "keydown"' in js
    assert 'localStorage.setItem("stop_musica"' in js
    assert 'localStorage.setItem("stop_sonido"' in js
    assert 'document.addEventListener("visibilitychange"' in js


def test_audio_tiene_volumen_independiente_para_musica_y_efectos():
    js = (ROOT / "frontend/app.js").read_text()
    assert 'let gananciaEfectos = null;' in js
    assert 'gananciaEfectos.connect(audioContext.destination)' in js
    assert 'gananciaEfectos.gain.setTargetAtTime(volumenSonido * 0.8' in js
    assert 'reproductorMusica.volume = volumenMusica' in js


def test_efecto_stop_mantiene_alerta_e_impacto():
    js = (ROOT / "frontend/app.js").read_text()
    assert 'reproducirSonido("alerta")' in js
    assert 'reproducirSonido("impacto")' in js
    assert 'class="efecto-stop"' in js or '"efecto-stop"' in js
