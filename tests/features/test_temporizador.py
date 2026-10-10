from pathlib import Path


def test_temporizador_muestra_aviso_cuenta_regresiva_y_fin_una_sola_vez():
    js = Path("frontend/app.js").read_text()
    html = Path("frontend/index.html").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'iniciarTemporizadorVisual(msg.vence_en, msg.servidor_ahora)' in js
    assert 'segundos <= 10 && segundos > 0 ? "⚠️" : ""' in js
    assert 'segundos <= 5 && segundos > 0 ? String(segundos) : ""' in js
    assert 'reproducirSonido("suspenso")' in js
    assert 'segundos === 0 && !tiempoAgotadoNotificado' in js
    assert 'mostrarEfectoJuego("💥", "💥 ¡TIEMPO!"' in js
    assert 'id="aviso-temporizador"' in html
    assert 'id="cuenta-regresiva"' in html
    assert ".cuenta-regresiva" in css


def test_temporizador_no_duplica_el_audio_entre_fin_visual_y_servidor():
    js = Path("frontend/app.js").read_text()

    assert 'else if (!tiempoAgotadoNotificado) reproducirSonido("tiempo")' in js
    assert "tiempoAgotadoNotificado = false" in js
