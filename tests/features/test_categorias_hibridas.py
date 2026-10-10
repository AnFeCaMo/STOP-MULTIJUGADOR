"""Pruebas de catálogos JSON, validación híbrida y categorías personalizadas."""
import asyncio
import json
from pathlib import Path

from backend.servidor import CATEGORIAS, GestorJuego
from backend.validaciones import evaluar_palabra


class FakeWebSocket:
    pass


def test_catalogos_json_existen_y_se_cargan():
    base = Path("backend/data")
    esperados = {
        "nombres.json", "apellidos.json", "ciudades.json", "frutas.json",
        "animales.json", "cosas.json", "colores.json", "paises.json",
        "capitales.json", "departamentos.json", "continentes.json",
        "tuberculos.json", "plantas.json",
    }
    assert esperados <= {p.name for p in base.glob("*.json")}
    for nombre in esperados:
        datos = json.loads((base / nombre).read_text(encoding="utf-8"))
        assert isinstance(datos, list) and datos


def test_ciudad_acepta_geografia_amplia_y_si_falta_va_a_votacion():
    assert evaluar_palabra("ciudad", "Colombia", "C") == "valida"
    assert evaluar_palabra("ciudad", "Cundinamarca", "C") == "valida"
    assert evaluar_palabra("ciudad", "Europa", "E") == "valida"
    assert evaluar_palabra("ciudad", "Bogotá", "B") == "valida"
    assert evaluar_palabra("ciudad", "CapitalInventada", "C") == "votacion"
    assert evaluar_palabra("ciudad", "Colombia", "A") == "invalida"


def test_geografia_se_ofrece_solo_dentro_de_ciudad():
    async def caso():
        gestor = GestorJuego()
        disponibles = {item["id"] for item in gestor.categorias_disponibles()}
        assert "ciudad" in disponibles
        assert not {"pais", "capital", "departamento", "continente"} & disponibles

    asyncio.run(caso())


def test_fruta_acepta_frutas_tuberculos_y_plantas_en_una_categoria():
    assert evaluar_palabra("fruta", "Fresa", "F") == "valida"
    assert evaluar_palabra("fruta", "Papa", "P") == "valida"
    assert evaluar_palabra("fruta", "Albahaca", "A") == "valida"
    assert evaluar_palabra("fruta", "Orquídea", "O") == "valida"
    assert evaluar_palabra("fruta", "PlantaInventada", "P") == "votacion"


def test_respuesta_desconocida_no_se_rechaza_si_no_hay_otro_votante():
    async def caso():
        gestor = GestorJuego()
        jugador, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None
        gestor.categorias_activas = ["fruta"]
        gestor.letra_actual = "F"
        gestor.jugadores[jugador["id"]]["respuestas_ronda"] = {"fruta": "FrutaInventada"}

        candidato = gestor._preparar_votaciones()[0]
        assert candidato["votantes"] == [jugador["id"]]

    asyncio.run(caso())


def test_catalogos_adicionales_se_validan_automaticamente():
    assert evaluar_palabra("color", "Azul", "A") == "valida"
    assert evaluar_palabra("pais", "Colombia", "C") == "valida"
    assert evaluar_palabra("capital", "Bogotá", "B") == "valida"
    assert evaluar_palabra("departamento", "Antioquia", "A") == "valida"
    assert evaluar_palabra("continente", "Europa", "E") == "valida"


def test_categoria_personalizada_se_crea_y_pasa_a_votacion():
    async def caso():
        gestor = GestorJuego()
        host, error = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        assert error is None
        other, error2 = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        assert error2 is None
        ok, error = await gestor.agregar_categoria_personalizada(host["id"], "Superhéroe")
        assert ok and error is None
        categoria = next(c for c, n in gestor.categorias_personalizadas.items() if n == "Superhéroe")
        assert categoria.startswith("personalizada:")
        assert await gestor.actualizar_configuracion(
            host["id"], 4, ["nombre", "ciudad", categoria]
        ) == (True, None)
        assert categoria in gestor.categorias_activas
        assert (await gestor.iniciar_ronda(host["id"]))[0]
        gestor.letra_actual = "S"
        await gestor.actualizar_respuestas(host["id"], {
            "nombre": "Sofia",
            "ciudad": "Santa Marta",
            categoria: "Superman",
        })
        await gestor.procesar_stop(host["id"])
        assert gestor.estado_juego == "VOTACION"
        clave = f"{categoria}:SUPERMAN"
        assert clave in gestor.votaciones

    asyncio.run(caso())


def test_categoria_personalizada_no_se_puede_crear_por_jugador_normal():
    async def caso():
        gestor = GestorJuego()
        host, _ = await gestor.conectar_sesion(FakeWebSocket(), "Andres")
        jugador, _ = await gestor.conectar_sesion(FakeWebSocket(), "Ana")
        ok, error = await gestor.agregar_categoria_personalizada(jugador["id"], "Película")
        assert not ok and "anfitrión" in error
        assert await gestor.agregar_categoria_personalizada(host["id"], "Película") == (True, None)
        ok, error = await gestor.agregar_categoria_personalizada(host["id"], "pelicula")
        assert not ok and "ya existe" in error

    asyncio.run(caso())
