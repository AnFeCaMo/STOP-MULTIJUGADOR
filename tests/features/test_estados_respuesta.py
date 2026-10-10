from pathlib import Path


def test_resultados_muestran_etiqueta_coherente_con_puntaje_y_estado():
    js = Path("frontend/app.js").read_text()

    assert "function etiquetaResultadoRespuesta(detalle, puntos)" in js
    assert '["valida_repetida", "votada_repetida"].includes(detalle.estado)' in js
    assert "`⚠️ Repetida +${puntos}`" in js
    assert "`✅ Correcta +${puntos}`" in js
    assert '"❌ Rechazada por votación +0"' in js
    assert '"❌ No empieza con la letra +0"' in js
    assert '"⚪ Sin respuesta +0"' in js
    assert "const etiqueta = etiquetaResultadoRespuesta(d, puntos)" in js


def test_interfaz_explicita_que_respuestas_desconocidas_pasan_a_votacion():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()

    assert "el sistema nunca la rechaza por no conocerla" in html
    assert "el sistema no la rechaza por desconocerla" in html
    assert "pasa a votación y no se rechaza automáticamente" in js


def test_estado_de_escritura_y_completado_se_muestra_en_la_lista_de_jugadores():
    js = Path("frontend/app.js").read_text()
    pruebas_presencia = Path("tests/features/test_estados_jugadores.py").read_text()

    assert 'j.estado_presencia || j.estado || `${j.total || 0} pts`' in js
    assert '"✍️ Escribiendo"' in pruebas_presencia
    assert '"✅ Completó"' in pruebas_presencia
