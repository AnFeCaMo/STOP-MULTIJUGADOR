import asyncio
from pathlib import Path

from backend.web_server import seleccionar_sala
from backend.servidor import GestorJuego


class FakeWebSocket:
    pass


def test_reconexion_recupera_sala_ronda_respuestas_avatar_y_puntuacion():
    async def caso():
        codigo, gestor, error = seleccionar_sala("crear")
        assert error is None
        ws_original = FakeWebSocket()
        sesion, error = await gestor.conectar_sesion(
            ws_original, "Ana", avatar="panda"
        )
        assert error is None
        jugador_id = sesion["id"]
        assert (await gestor.iniciar_ronda(jugador_id))[0]
        gestor.letra_actual = "A"
        gestor.jugadores[jugador_id]["total"] = 35
        await gestor.actualizar_respuestas(jugador_id, {"nombre": "Ana"})
        assert await gestor.desconectar(ws_original) == "Ana"

        codigo_recuperado, sala_recuperada, error = seleccionar_sala(
            "unir", codigo.lower()
        )
        assert error is None
        assert codigo_recuperado == codigo
        assert sala_recuperada is gestor

        ws_recuperado = FakeWebSocket()
        reconexion, error = await sala_recuperada.conectar_sesion(
            ws_recuperado, "Nombre ignorado", sesion["token"]
        )
        assert error is None and reconexion["reconectado"]
        assert reconexion["id"] == jugador_id
        assert len(gestor.jugadores) == 1
        assert gestor.jugadores[jugador_id]["avatar"] == "panda"
        assert gestor.jugadores[jugador_id]["total"] == 35
        estado = gestor.serializar_estado_para(jugador_id)
        assert estado["tipo"] == "ronda"
        assert estado["letra"] == "A"
        assert estado["mis_respuestas"]["nombre"] == "Ana"
        await gestor.desconectar(ws_recuperado)
        gestor._cancelar_reinicio_sala()

    asyncio.run(caso())


def test_banner_de_reconexion_permanece_hasta_confirmar_bienvenida():
    js = Path("frontend/app.js").read_text()
    html = Path("frontend/index.html").read_text()
    apertura = js.split("socket.onopen = () => {", 1)[1].split(
        "socket.onmessage =", 1
    )[0]
    bienvenida = js.split('case "bienvenida":', 1)[1].split(
        'case "sala":', 1
    )[0]

    apertura_sin_sesion = apertura.split("} else {", 1)[1]
    assert "bannerReconnect.classList.add(\"hidden\")" not in apertura.split(
        "if (tokenSesion && nombreGuardado)", 1
    )[1].split("} else {", 1)[0]
    assert "bannerReconnect.classList.add(\"hidden\")" in apertura_sin_sesion
    assert "bannerReconnect.classList.add(\"hidden\")" in bienvenida
    assert 'mostrarToast("✅ Conexión recuperada", "success")' in bienvenida
    assert 'role="status" aria-live="polite"' in html
