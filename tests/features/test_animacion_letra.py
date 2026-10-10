from pathlib import Path


def test_animacion_revela_al_final_la_letra_autoritativa_de_la_ronda():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'document.getElementById("letra-ronda").textContent = "?"' in js
    assert "const letraFinal = String(letra || \"?\").toLocaleUpperCase(\"es-CO\")" in js
    assert "secuencia.push(letraFinal)" in js
    assert "etiqueta.textContent = secuencia[indice]" in js
    assert "temporizadorAnimacionLetra = setTimeout(avanzar, 65)" in js
    assert '() => mostrarEfectoRonda(msg)' in js
    assert ".letra-valor.letra-animando" in css
    assert "@keyframes giroLetra" in css


def test_animacion_no_se_repite_en_una_ronda_activa_y_se_cancela_al_cerrar():
    js = Path("frontend/app.js").read_text()

    assert "if (!yaEstabaEnJuego || ultimaAnimacionLetra !== claveAnimacion)" in js
    assert "function cancelarAnimacionLetra()" in js
    assert "cancelarAnimacionLetra();" in js
    assert "if (idAnimacion !== animacionLetraId) return" in js
    assert 'etiqueta.setAttribute("aria-label", `Letra ${letraFinal} de la ronda ${ronda}`)' in js
