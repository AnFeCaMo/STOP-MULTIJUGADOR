import asyncio

from backend.servidor import GestorJuego
from backend.validaciones import evaluar_palabra


def test_nombres_conocidos_se_validan_automaticamente():
    conocidos = [
        ("Andrés", "A"), ("Pablo", "P"), ("Juan", "J"),
        ("Michael", "M"), ("Lina", "L"), ("Román", "R"),
        ("Wilfrido", "W"),
    ]
    for nombre, letra in conocidos:
        assert evaluar_palabra("nombre", nombre, letra) == "valida"


def test_nombre_desconocido_pero_con_letra_pasa_a_votacion():
    assert evaluar_palabra("nombre", "Xandrius", "X") == "votacion"


def test_nombre_con_letra_incorrecta_no_pasa_a_votacion():
    assert evaluar_palabra("nombre", "Pedro", "A") == "invalida"


def test_categoria_desconocida_con_letra_pasa_a_votacion():
    assert evaluar_palabra("animal", "Ajolote", "A") == "votacion"


def test_categoria_conocida_se_valida_automaticamente():
    assert evaluar_palabra("ciudad", "Armenia", "A") == "valida"


def test_entrada_no_texto_no_rompe_validaciones():
    assert evaluar_palabra("animal", None, "A") == "invalida"
    assert evaluar_palabra("animal", 123, "A") == "invalida"
    assert evaluar_palabra("nombre", "Ana", 7) == "invalida"


def test_conexion_rechaza_nombres_y_tokens_invalidos():
    async def caso():
        gestor = GestorJuego()
        class WS: pass
        sesion, error = await gestor.conectar_sesion(WS(), None)
        assert sesion is None and error == "El nombre debe ser texto."
        sesion, error = await gestor.conectar_sesion(WS(), "Ana", 123)
        assert sesion is None and error == "La sesión no es válida."
    asyncio.run(caso())


def test_seguridad_del_juego_rechaza_acciones_no_permitidas():
    async def caso():
        gestor = GestorJuego()

        class WS:
            pass

        ws1, ws2, ws3 = WS(), WS(), WS()
        id1, err = await gestor.conectar(ws1, "Andres")
        id2, err = await gestor.conectar(ws2, "Ana")
        id3, err = await gestor.conectar(ws3, "Carlos")
        assert err is None
        ok, err = await gestor.iniciar_ronda(id1)
        assert ok and err is None
        gestor.letra_actual = "A"

        respuestas = {
            "nombre": "Andres",
            "apellido": "Acosta",
            "ciudad": "Armenia",
            "fruta": "Aguacate",
            "animal": "Aguila",
            "cosa": "Anillo",
        }
        await gestor.actualizar_respuestas(id1, {**respuestas, "fruta": "Arazá"})
        await gestor.actualizar_respuestas(id2, {**respuestas, "nombre": "Ana", "fruta": "Aguacate"})
        await gestor.actualizar_respuestas(id3, {**respuestas, "nombre": "Carlos", "fruta": "Aguacate"})

        ok, err = await gestor.procesar_stop(id1, {**respuestas, "fruta": "Arazá"})
        assert ok and err is None
        assert gestor.estado_juego == "VOTACION"

        clave = "fruta:ARAZA"
        assert clave in gestor.votaciones
        assert gestor.registrar_voto(id1, clave, True) == (False, "No puedes votar tu propia respuesta.")
        assert gestor.registrar_voto(id2, clave, True) == (True, None)
        assert gestor.registrar_voto(id2, clave, True) == (False, "Ya votaste por esta respuesta.")

        assert await gestor.actualizar_respuestas(id2, {**respuestas, "fruta": "Almendra"}) is False
        assert await gestor.iniciar_ronda(id2) == (False, "Solamente el anfitrión puede iniciar la ronda.")
        assert await gestor.actualizar_configuracion(id2, 5, ["nombre", "apellido", "ciudad"]) == (
            False,
            "Solamente el anfitrión puede cambiar la configuración.",
        )

        # Un nombre duplicado no puede crear otra sesión.
        dup, error = await gestor.conectar_sesion(WS(), "Andres")
        assert dup is None and error == "Ya existe un jugador con el nombre 'Andres'."

    asyncio.run(caso())


async def _prueba_gestor_nombre_conocido_y_desconocido():
    gestor = GestorJuego()

    class WS: pass
    ws1, ws2 = WS(), WS()
    id1, err = await gestor.conectar(ws1, "Andres")
    assert err is None
    id2, err = await gestor.conectar(ws2, "Carlos")
    assert err is None
    ok, err = await gestor.iniciar_ronda(id1)
    assert ok and err is None
    gestor.letra_actual = "A"

    await gestor.actualizar_respuestas(id1, {
        "nombre": "Andrés", "apellido": "Acosta", "ciudad": "Armenia",
        "fruta": "Arándano", "animal": "Águila", "cosa": "Anillo"
    })
    await gestor.actualizar_respuestas(id2, {
        "nombre": "Aurelianox", "apellido": "Acosta", "ciudad": "Armenia",
        "fruta": "Arándano", "animal": "Águila", "cosa": "Anillo"
    })
    await gestor.procesar_stop(id1)

    # El nombre conocido no debe aparecer como candidato de votación.
    claves = set(gestor.votaciones.keys())
    assert "nombre:ANDRES" not in claves
    assert "nombre:AURELIANOX" in claves


def test_flujo_gestor():
    asyncio.run(_prueba_gestor_nombre_conocido_y_desconocido())


if __name__ == "__main__":
    test_nombres_conocidos_se_validan_automaticamente()
    test_nombre_desconocido_pero_con_letra_pasa_a_votacion()
    test_nombre_con_letra_incorrecta_no_pasa_a_votacion()
    test_categoria_desconocida_con_letra_pasa_a_votacion()
    test_categoria_conocida_se_valida_automaticamente()
    test_flujo_gestor()
    print("Todas las pruebas de reglas pasaron.")
