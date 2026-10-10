"""Pruebas para animaciones ligeras de personajes (fase 7)."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from backend.servidor import AVATARES


def test_animaciones_ligeras_se_activan_por_evento_y_sin_bucle():
    css = Path("frontend/style.css").read_text()

    for keyframe in (
        "avatarFeliz",
        "avatarCelebrar",
        "avatarTriste",
        "avatarFrustrado",
        "avatarSorpresa",
        "avatarNervioso",
        "avatarCompetitivo",
        "avatarSuspenso",
    ):
        assert f"@keyframes {keyframe}" in css
    assert ".avatar-animado[data-avatar=" not in css
    assert "infinite" not in css[css.index(".avatar-evento[data-emocion="):css.index(".estado-conexion {")]
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_avatares_animados_se_renderizan_para_varios_jugadores_y_cambios():
    js = Path("frontend/app.js").read_text()

    assert "function renderizarAvatar(referencia" in js
    assert 'data-avatar-legado="${avatar.legacyId}"' in js
    assert "window.STOP_AVATAR_CATALOG" in js
    assert 'classList.add("avatar-animado")' in js
    assert "eventosEmocionAnimados.has(claveEvento)" in js
    assert "function iniciarSorpresaTemporal" in js
    assert "function rutaAvatarEmocion" in js
    assert 'renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id, j.emocion, j.emocion_evento)' in js
    assert 'renderizarAvatar(e.avatar || "🐻", "avatar-jugador", e.id, e.emocion, e.emocion_evento)' in js
    assert len(AVATARES) == 21


def test_animaciones_usen_solo_transform_y_opacidad_para_bajo_costo():
    css = Path("frontend/style.css").read_text()
    inicio = css.index(".avatar-animado {")
    fin = css.index(".estado-conexion {", inicio)
    estilos_avatar = css[inicio:fin]

    assert "filter:" not in estilos_avatar
    assert "box-shadow:" not in estilos_avatar
    assert "transform:" in estilos_avatar


def test_cada_avatar_tiene_las_12_expresiones_locales_validas_y_estado_normal():
    raiz = Path("frontend/assets/avatars")
    emociones = (
        "normal", "feliz", "muy_feliz", "triste", "frustrado", "sorprendido",
        "concentrado", "nervioso", "pensativo", "competitivo", "suspenso", "orgulloso",
    )
    expresiones_normales = []
    for numero in range(1, 21):
        avatar_id = f"persona-{numero:02}"
        base = (raiz / f"{avatar_id}.svg").read_text(encoding="utf-8")
        contenido_por_emocion = []
        for emocion in emociones:
            ruta = raiz / "expresiones" / avatar_id / f"{emocion}.svg"
            assert ruta.is_file(), f"Falta {avatar_id}/{emocion}"
            raiz_svg = ET.parse(ruta).getroot()
            assert raiz_svg.tag.endswith("svg")
            assert raiz_svg.attrib.get("viewBox") == "0 0 256 256"
            assert raiz_svg.find("{http://www.w3.org/2000/svg}image") is None
            assert emocion.replace("_", " ") in raiz_svg.find("{http://www.w3.org/2000/svg}title").text
            contenido = ruta.read_text(encoding="utf-8")
            assert "<path" in contenido and "<svg" in contenido
            contenido_por_emocion.append(contenido)
        assert len(set(contenido_por_emocion)) == len(emociones), f"Estados repetidos en {avatar_id}"
        assert base == (raiz / "expresiones" / avatar_id / "normal.svg").read_text(encoding="utf-8")
        expresiones_normales.append(contenido_por_emocion[0])
    assert len(set(expresiones_normales)) == 20
