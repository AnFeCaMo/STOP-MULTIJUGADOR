import asyncio
from pathlib import Path

from backend.web_server import ALFABETO_CODIGO_SALA, seleccionar_sala


class FakeWebSocket:
    pass


def test_crear_unir_validar_codigo_y_aislar_salas():
    codigo_a, gestor_a, error = seleccionar_sala("crear")
    assert error is None
    assert len(codigo_a) == 4
    assert all(caracter in ALFABETO_CODIGO_SALA for caracter in codigo_a)

    codigo_b, gestor_b, error = seleccionar_sala("crear")
    assert error is None
    assert codigo_b != codigo_a
    assert gestor_b is not gestor_a

    codigo_unido, gestor_unido, error = seleccionar_sala("unir", codigo_a.lower())
    assert error is None
    assert codigo_unido == codigo_a
    assert gestor_unido is gestor_a

    _, _, error = seleccionar_sala("unir", "A0!?")
    assert error == "El código debe tener 4 caracteres válidos."
    _, _, error = seleccionar_sala("unir", "ZZZZ")
    assert error == "No existe una sala con ese código."

    async def caso():
        _, error_a = await gestor_a.conectar_sesion(FakeWebSocket(), "Andres")
        _, error_b = await gestor_b.conectar_sesion(FakeWebSocket(), "Ana")
        assert error_a is None and error_b is None
        assert [j["nombre"] for j in gestor_a.serializar_sala()["jugadores"]] == ["Andres"]
        assert [j["nombre"] for j in gestor_b.serializar_sala()["jugadores"]] == ["Ana"]

    asyncio.run(caso())


def test_interfaz_permite_crear_unirse_y_reconectar_a_la_sala():
    html = Path("frontend/index.html").read_text()
    js = Path("frontend/app.js").read_text()
    backend = Path("backend/web_server.py").read_text()

    assert 'id="accion-sala"' in html
    assert 'value="crear"' in html and 'value="unir"' in html
    assert 'id="input-codigo-sala"' in html
    assert 'id="codigo-sala-activo"' in html
    assert 'accion_sala: accionSala' in js
    assert 'codigo_sala: codigoSalaGuardado' in js
    assert 'localStorage.setItem("stop_codigo_sala", msg.codigo_sala)' in js
    assert 'def seleccionar_sala(accion: str, codigo: str = ""):' in backend
