from pathlib import Path


def test_puntos_se_mueven_desde_la_ronda_hasta_el_marcador_del_jugador():
    js = Path("frontend/app.js").read_text()
    css = Path("frontend/style.css").read_text()

    assert 'class="pts-ronda-badge" data-player-id="${Number(j.id)}"' in js
    assert 'data-puntos="${Number(j.puntos_ronda) || 0}"' in js
    assert 'item.dataset.playerId = String(j.id)' in js
    assert 'class="pts-total-badge">${j.total || 0} pts' in js
    assert 'function animarPuntosAlMarcador(origen, destino, puntos)' in js
    assert "document.querySelector(`.item-clasificacion[data-player-id=\"${jugadorId}\"] .pts-total-badge`)" in js
    assert "vuelo.textContent = `⬆️ +${puntos}`" in js
    assert 'vuelo.setAttribute("aria-hidden", "true")' in js
    assert ".puntos-volando" in css
    assert ".puntos-recibe" in css


def test_animacion_omite_puntaje_cero_y_no_repite_el_mismo_resultado():
    js = Path("frontend/app.js").read_text()

    assert "if (!Number.isFinite(puntos) || puntos <= 0) return" in js
    assert "if (clavePuntaje !== ultimaAnimacionPuntaje)" in js
    assert "ultimaAnimacionPuntaje = clavePuntaje" in js
