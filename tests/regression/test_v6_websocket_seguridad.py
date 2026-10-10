"""Pruebas V6 para conexiones WebSocket que se cierran antes de entrar a una sala."""

from starlette.testclient import TestClient

from backend.web_server import app


def test_websocket_puede_desconectarse_antes_de_registrarse():
    """Cerrar una conexión recién aceptada no debe provocar una excepción de servidor."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws"):
            pass
