"""Pruebas de extremo a extremo del STOP Multijugador Web."""

import asyncio
import json
import os
import subprocess
import sys

import websockets

from backend.validaciones import DICCIONARIO_CATEGORIAS

HOST = "127.0.0.1"
PORT = 8765
URL = f"ws://{HOST}:{PORT}/ws"


def respuesta_conocida(categoria: str, letra: str, indice: int = 0) -> str:
    opciones = DICCIONARIO_CATEGORIAS.get(categoria, {}).get(letra, [])
    if opciones:
        return opciones[min(indice, len(opciones) - 1)]
    return f"{letra}respuesta{indice}"


async def recibir_tipo(ws, tipo, timeout=4):
    while True:
        mensaje = json.loads(await asyncio.wait_for(ws.recv(), timeout))
        if mensaje.get("tipo") == tipo:
            return mensaje


async def iniciar_servidor():
    env = os.environ.copy()
    rutas_python = [os.getcwd(), env.get("PYTHONPATH", "")]
    env["PYTHONPATH"] = os.pathsep.join(ruta for ruta in rutas_python if ruta)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.web_server:app", "--host", HOST, "--port", str(PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    for _ in range(30):
        try:
            ws = await websockets.connect(URL)
            return proc, ws
        except Exception:
            await asyncio.sleep(0.2)
    proc.terminate()
    raise RuntimeError("No se pudo iniciar el servidor de pruebas")


async def test_completo():
    servidor_proc, primera_ws = await iniciar_servidor()
    websockets_abiertos = [primera_ws]
    try:
        ws1 = primera_ws
        ws2 = await websockets.connect(URL)
        ws3 = await websockets.connect(URL)
        websockets_abiertos.extend([ws2, ws3])

        print("[1] Conectando 3 jugadores...")
        await ws1.send(json.dumps({"tipo": "conexion", "nombre": "Andres"}))
        b1 = await recibir_tipo(ws1, "bienvenida")
        id1 = b1["id"]
        await recibir_tipo(ws1, "sala")

        await ws2.send(json.dumps({"tipo": "conexion", "nombre": "Carlos"}))
        b2 = await recibir_tipo(ws2, "bienvenida")
        id2 = b2["id"]
        await recibir_tipo(ws2, "sala")
        await recibir_tipo(ws1, "sala")

        await ws3.send(json.dumps({"tipo": "conexion", "nombre": "Maria"}))
        b3 = await recibir_tipo(ws3, "bienvenida")
        id3 = b3["id"]
        await recibir_tipo(ws3, "sala")
        await recibir_tipo(ws1, "sala")
        await recibir_tipo(ws2, "sala")
        assert b1["es_anfitrion"] is True
        assert b2["es_anfitrion"] is False
        assert b3["es_anfitrion"] is False
        print(" -> Anfitrión e IDs confirmados.")

        print("[2] Iniciando ronda...")
        await ws1.send(json.dumps({"tipo": "iniciar_ronda"}))
        r1 = await recibir_tipo(ws1, "ronda")
        await recibir_tipo(ws2, "ronda")
        await recibir_tipo(ws3, "ronda")
        letra = r1["letra"]
        print(f" -> Letra: {letra}")

        # Nombres conocidos: validación automática. Nombres no reconocidos y otras respuestas desconocidas: votación.
        respuestas1 = {
            "nombre": f"{letra}NombreAndres",
            "apellido": respuesta_conocida("apellido", letra, 0),
            "ciudad": respuesta_conocida("ciudad", letra, 0),
            "fruta": respuesta_conocida("fruta", letra, 0),
            "animal": f"{letra}AjoloteInventado",
            "cosa": respuesta_conocida("cosa", letra, 0),
        }
        respuestas2 = {
            "nombre": f"{letra}NombreCarlos",
            "apellido": respuesta_conocida("apellido", letra, 0),
            "ciudad": respuesta_conocida("ciudad", letra, 0),
            "fruta": respuesta_conocida("fruta", letra, 0),
            "animal": f"{letra}AnimalInventado",
            "cosa": respuesta_conocida("cosa", letra, 1),
        }
        respuestas3 = {
            "nombre": f"{letra}NombreMaria",
            "apellido": respuesta_conocida("apellido", letra, 1),
            "ciudad": respuesta_conocida("ciudad", letra, 1),
            "fruta": respuesta_conocida("fruta", letra, 1),
            "animal": f"{letra}AnimalMaria",
            "cosa": respuesta_conocida("cosa", letra, 2),
        }

        await ws1.send(json.dumps({"tipo": "respuestas", "respuestas": respuestas1}))
        await ws2.send(json.dumps({"tipo": "respuestas", "respuestas": respuestas2}))
        await ws3.send(json.dumps({"tipo": "respuestas", "respuestas": respuestas3}))
        await asyncio.sleep(0.15)

        print("[3] Presionando STOP y entrando a votación...")
        await ws1.send(json.dumps({"tipo": "stop", "respuestas": respuestas1}))
        v1 = await recibir_tipo(ws1, "votacion")
        v2 = await recibir_tipo(ws2, "votacion")
        v3 = await recibir_tipo(ws3, "votacion")
        assert v1["candidatos"]
        assert v2["candidatos"]
        assert v3["candidatos"]
        print(f" -> {len(v1['candidatos'])} respuestas pendientes de validación.")

        # Cada jugador vota SÍ por todas las respuestas que puede votar.
        print("[4] Votando todas las respuestas pendientes...")
        for ws, voto_msg in [(ws1, v1), (ws2, v2), (ws3, v3)]:
            for candidato in voto_msg["candidatos"]:
                if candidato["puede_votar"]:
                    await ws.send(json.dumps({
                        "tipo": "voto",
                        "clave": candidato["clave"],
                        "voto": True,
                    }))
                    await asyncio.sleep(0.03)

        # El último voto produce resultados; cada cliente puede recibir primero actualizaciones de votación.
        resultados = []
        for ws in [ws1, ws2, ws3]:
            resultados.append(await recibir_tipo(ws, "resultados", timeout=6))
        final = resultados[0]
        assert final["tipo"] == "resultados"
        assert len(final["jugadores"]) == 3

        jugador_andres = next(j for j in final["jugadores"] if j["nombre"] == "Andres")
        assert set(jugador_andres["desglose"].keys()) == {
            "nombre", "apellido", "ciudad", "fruta", "animal", "cosa"
        }
        assert all("puntos" in d for d in jugador_andres["detalle_respuestas"].values())
        print(" -> Votación, desglose por categoría y total confirmados.")

        print("[5] Verificando rechazo por mayoría NO...")
        # No reiniciamos la partida aquí: comprobamos la regla directamente con una instancia aparte.
        from backend.servidor import GestorJuego

        gestor = GestorJuego()
        class WS: pass
        sockets = [WS(), WS(), WS()]
        ids = []
        for nombre, ws in zip(["A", "B", "C"], sockets):
            j_id, error = await gestor.conectar(ws, nombre)
            assert error is None
            ids.append(j_id)
        ok, error = await gestor.iniciar_ronda(ids[0])
        assert ok and error is None
        gestor.letra_actual = "A"
        for j_id, nombre in zip(ids, ["A", "B", "C"]):
            await gestor.actualizar_respuestas(j_id, {
                "nombre": f"A{nombre}", "apellido": "Acosta", "ciudad": "Armenia",
                "fruta": "Arazá", "animal": "Ajolote", "cosa": "Anillo"
            })
        await gestor.procesar_stop(ids[0])
        claves_nombre = [k for k in gestor.votaciones if k.startswith("nombre:")]
        # Todos los nombres reciben mayoría NO.
        for clave in claves_nombre:
            for voter in list(gestor.votaciones[clave]["votantes"]):
                gestor.registrar_voto(voter, clave, False)
        assert gestor.estado_juego == "RESULTADOS"
        assert all(j["detalle_respuestas"]["nombre"]["puntos"] == 0 for j in gestor.jugadores.values())
        print(" -> Mayoría NO produce 0 puntos correctamente.")

        print("\n==================================================")
        print(" TODAS LAS PRUEBAS PASARON EXITOSAMENTE (100%)")
        print("==================================================")
    finally:
        for ws in websockets_abiertos:
            try:
                await ws.close()
            except Exception:
                pass
        servidor_proc.terminate()
        try:
            servidor_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            servidor_proc.kill()


if __name__ == "__main__":
    asyncio.run(test_completo())
