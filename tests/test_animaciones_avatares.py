"""Pruebas para animaciones ligeras de personajes (fase 7)."""

from pathlib import Path

from backend.servidor import AVATARES


def test_animaciones_ligeras_estan_asociadas_a_personajes():
    css = Path("frontend/style.css").read_text()

    for avatar in ("oso", "gallina", "gato", "perro", "rana", "conejo", "pinguino", "fantasma", "robot"):
        assert f'data-avatar="{avatar}"' in css
    for keyframe in (
        "avatarSalto",
        "avatarAlas",
        "avatarCola",
        "avatarOrejas",
        "avatarBalanceo",
        "avatarFlotacion",
        "avatarRobot",
    ):
        assert f"@keyframes {keyframe}" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_avatares_animados_se_renderizan_para_varios_jugadores_y_cambios():
    js = Path("frontend/app.js").read_text()

    assert "function renderizarAvatar(emoji" in js
    assert "avatar.dataset.avatar = seleccionado ? seleccionado.id : \"oso\"" in js
    assert 'classList.add("avatar-animado")' in js
    assert 'renderizarAvatar(j.avatar || "🐻", "avatar-jugador", j.id)' in js
    assert 'renderizarAvatar(e.avatar || "🐻", "avatar-jugador", e.id)' in js
    assert len(AVATARES) == 21


def test_animaciones_usen_solo_transform_y_opacidad_para_bajo_costo():
    css = Path("frontend/style.css").read_text()
    inicio = css.index(".avatar-animado {")
    fin = css.index(".estado-conexion {", inicio)
    estilos_avatar = css[inicio:fin]

    assert "filter:" not in estilos_avatar
    assert "box-shadow:" not in estilos_avatar
    assert "transform:" in estilos_avatar
