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
