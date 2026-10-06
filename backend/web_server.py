import json
import os
import asyncio

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from backend.servidor import GestorJuego

app = FastAPI(title="STOP Multijugador Web")
gestor = GestorJuego()
temporizador_ronda = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


async def broadcast(mensaje: dict):
    for _, sesion, es_espectador in gestor.sesiones_conectadas():
        try:
            personalizado = dict(mensaje, espectador=es_espectador)
            await sesion["ws"].send_text(json.dumps(personalizado, ensure_ascii=False))
        except Exception:
            pass


async def broadcast_votacion():
    for sesion_id, sesion, es_espectador in gestor.sesiones_conectadas():
        try:
            mensaje = gestor.serializar_votacion_para(sesion_id, es_espectador)
            mensaje["espectador"] = es_espectador
            await sesion["ws"].send_text(
                json.dumps(mensaje, ensure_ascii=False)
            )
        except Exception:
            pass


async def esperar_fin_ronda(numero_ronda: int):
    await asyncio.sleep(gestor.duracion_ronda)
    cerrada = await gestor.finalizar_por_tiempo(numero_ronda)
    if not cerrada:
        return
    await broadcast_fase_cerrada()


async def broadcast_fase_cerrada():
    if gestor.estado_juego == "VOTACION":
        await broadcast_votacion()
    elif gestor.estado_juego == "RESULTADOS":
        await broadcast(gestor.serializar_resultados())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    sesion_id = None
    es_espectador = False

    try:
        while True:
            datos_raw = await websocket.receive_text()
            try:
                mensaje = json.loads(datos_raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "tipo": "error",
                    "mensaje": "Mensaje inválido: debe ser JSON válido."
                }))
                continue

            if not isinstance(mensaje, dict):
                await websocket.send_text(json.dumps({
                    "tipo": "error",
                    "mensaje": "El mensaje debe ser un objeto JSON."
                }))
                continue

            tipo = mensaje.get("tipo")

            # Los espectadores pasan a jugadores al cerrar la ronda; actualizar el rol
            # asociado a esta conexión antes de validar la siguiente acción.
            if sesion_id is not None:
                if sesion_id in gestor.jugadores:
                    es_espectador = False
                elif sesion_id in gestor.espectadores:
                    es_espectador = True

            if tipo == "conexion":
                if sesion_id is not None:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "Esta conexión ya tiene un jugador registrado."
                    }))
                    continue

                nombre = mensaje.get("nombre", "")
                token = mensaje.get("token")
                if not isinstance(nombre, str):
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "El nombre debe ser texto."
                    }))
                    continue
                if token is not None and not isinstance(token, str):
                    await websocket.send_text(json.dumps({"tipo": "error", "mensaje": "La sesión no es válida."}))
                    continue

                sesion, error = await gestor.conectar_sesion(websocket, nombre, token)
                if error:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                    continue

                sesion_id = sesion["id"]
                es_espectador = sesion["es_espectador"]
                socket_anterior = sesion.get("socket_anterior")
                if socket_anterior is not None:
                    try:
                        await socket_anterior.close(code=4001, reason="Sesión reemplazada")
                    except Exception:
                        pass
                await websocket.send_text(json.dumps({
                    "tipo": "bienvenida",
                    "id": sesion_id,
                    "token": sesion["token"],
                    "nombre": sesion["nombre"],
                    "es_anfitrion": sesion["es_anfitrion"],
                    "es_espectador": es_espectador,
                    "reconectado": sesion["reconectado"],
                    "estado": gestor.estado_juego,
                }, ensure_ascii=False))
                await websocket.send_text(json.dumps(
                    gestor.serializar_estado_para(sesion_id, es_espectador), ensure_ascii=False
                ))
                if gestor.estado_juego == "SALA":
                    await broadcast(gestor.serializar_sala())
                elif gestor.estado_juego == "JUEGO":
                    presencia = gestor.serializar_ronda()
                    presencia["tipo"] = "jugadores"
                    await broadcast(presencia)
                elif gestor.estado_juego == "VOTACION":
                    await broadcast_votacion()
                else:
                    await broadcast(gestor.serializar_resultados())

            elif sesion_id is None:
                await websocket.send_text(json.dumps({
                    "tipo": "error",
                    "mensaje": "Primero debes entrar a la sala."
                }))

            elif not gestor.conexion_autorizada(websocket, sesion_id, es_espectador):
                await websocket.send_text(json.dumps({
                    "tipo": "error",
                    "mensaje": "Esta sesión se conectó desde otro dispositivo."
                }, ensure_ascii=False))
                await websocket.close()
                break

            elif es_espectador and tipo in {"iniciar_ronda", "respuestas", "stop", "voto", "configuracion"}:
                await websocket.send_text(json.dumps({
                    "tipo": "error",
                    "mensaje": "Los espectadores no pueden realizar acciones de juego."
                }, ensure_ascii=False))

            elif tipo == "iniciar_ronda":
                ok, error = await gestor.iniciar_ronda(sesion_id)
                if not ok:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                else:
                    global temporizador_ronda
                    if temporizador_ronda and not temporizador_ronda.done():
                        temporizador_ronda.cancel()
                    temporizador_ronda = asyncio.create_task(esperar_fin_ronda(gestor.ronda_actual))
                    await broadcast(gestor.serializar_ronda())

            elif tipo == "configuracion":
                ok, error = await gestor.actualizar_configuracion(
                    sesion_id, mensaje.get("rondas"), mensaje.get("categorias")
                )
                if not ok:
                    await websocket.send_text(json.dumps({
                        "tipo": "error", "mensaje": error
                    }, ensure_ascii=False))
                else:
                    await broadcast(gestor.serializar_sala())

            elif tipo == "nueva_partida":
                ok, error = await gestor.iniciar_nueva_partida(sesion_id)
                if not ok:
                    await websocket.send_text(json.dumps({
                        "tipo": "error", "mensaje": error
                    }, ensure_ascii=False))
                else:
                    if temporizador_ronda and not temporizador_ronda.done():
                        temporizador_ronda.cancel()
                    await broadcast(gestor.serializar_sala())

            elif tipo == "respuestas":
                respuestas = mensaje.get("respuestas")
                if not isinstance(respuestas, dict):
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "Las respuestas deben enviarse como objeto."
                    }))
                    continue
                cerrada_por_tiempo = await gestor.actualizar_respuestas(sesion_id, respuestas)
                if cerrada_por_tiempo:
                    if temporizador_ronda and not temporizador_ronda.done():
                        temporizador_ronda.cancel()
                    await broadcast_fase_cerrada()
                elif gestor.estado_juego == "JUEGO":
                    presencia = gestor.serializar_ronda()
                    presencia["tipo"] = "jugadores"
                    await broadcast(presencia)

            elif tipo == "stop":
                respuestas_finales = mensaje.get("respuestas")
                if respuestas_finales is not None and not isinstance(respuestas_finales, dict):
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "Las respuestas de STOP deben ser un objeto."
                    }))
                    continue

                ok, error = await gestor.procesar_stop(sesion_id, respuestas_finales)
                if not ok:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                    if gestor.estado_juego != "JUEGO":
                        if temporizador_ronda and not temporizador_ronda.done():
                            temporizador_ronda.cancel()
                        await broadcast_fase_cerrada()
                    continue

                if temporizador_ronda and not temporizador_ronda.done():
                    temporizador_ronda.cancel()

                if gestor.estado_juego == "VOTACION":
                    await broadcast_votacion()
                else:
                    await broadcast(gestor.serializar_resultados())

            elif tipo == "voto":
                clave = mensaje.get("clave")
                voto = mensaje.get("voto")
                if not isinstance(clave, str) or not isinstance(voto, bool):
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": "El voto debe incluir una clave y un valor sí/no."
                    }))
                    continue

                ok, error = gestor.registrar_voto(sesion_id, clave, voto)
                if not ok:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                    continue

                if gestor.estado_juego == "RESULTADOS":
                    await broadcast(gestor.serializar_resultados())
                else:
                    await broadcast_votacion()

            else:
                await websocket.send_text(json.dumps({
                    "tipo": "error",
                    "mensaje": f"Tipo de mensaje no reconocido: {tipo!r}"
                }, ensure_ascii=False))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"Excepción en websocket: {exc}")
    finally:
        nombre_desconectado = await gestor.desconectar(websocket)
        if nombre_desconectado:
            print(f"Jugador desconectado: {nombre_desconectado}")
            if gestor.estado_juego == "VOTACION":
                await broadcast_votacion()
            elif gestor.estado_juego == "RESULTADOS":
                await broadcast(gestor.serializar_resultados())
            elif gestor.estado_juego == "SALA":
                await broadcast(gestor.serializar_sala())
            else:
                actualizacion = gestor.serializar_ronda()
                actualizacion["tipo"] = "jugadores"
                await broadcast(actualizacion)


if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


def iniciar():
    uvicorn.run("backend.web_server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    iniciar()
