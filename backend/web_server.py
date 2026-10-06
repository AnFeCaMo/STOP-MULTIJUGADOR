import json
import os
import asyncio
import secrets
import string
import time
from contextvars import ContextVar

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from backend.servidor import AVATARES, GestorJuego, TIEMPO_PARA_MARCAR_AUSENTE

app = FastAPI(title="STOP Multijugador Web")
gestor_principal = GestorJuego()
gestor_contexto: ContextVar[GestorJuego] = ContextVar("gestor_contexto", default=gestor_principal)
codigo_sala_contexto: ContextVar[str] = ContextVar("codigo_sala_contexto", default="7K4P")
gestores_por_codigo = {"7K4P": gestor_principal}
temporizadores_ronda = {}
tareas_ausencia = {}
tareas_limpieza_sala = {}
ALFABETO_CODIGO_SALA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class GestorContextual:
    def __getattr__(self, nombre):
        return getattr(gestor_contexto.get(), nombre)

    def __setattr__(self, nombre, valor):
        setattr(gestor_contexto.get(), nombre, valor)

    def actual(self):
        return gestor_contexto.get()


gestor = GestorContextual()


def gestor_actual():
    if isinstance(gestor, GestorContextual):
        return gestor.actual()
    return gestor


def seleccionar_sala(accion: str, codigo: str = ""):
    if accion == "crear":
        while True:
            nuevo_codigo = "".join(secrets.choice(ALFABETO_CODIGO_SALA) for _ in range(4))
            if nuevo_codigo not in gestores_por_codigo:
                break
        nuevo_gestor = GestorJuego()
        gestores_por_codigo[nuevo_codigo] = nuevo_gestor
        return nuevo_codigo, nuevo_gestor, None
    if accion == "unir":
        codigo = codigo.strip().upper()
        if len(codigo) != 4 or any(caracter not in ALFABETO_CODIGO_SALA for caracter in codigo):
            return "", None, "El código debe tener 4 caracteres válidos."
        sala = gestores_por_codigo.get(codigo)
        if sala is None:
            return "", None, "No existe una sala con ese código."
        return codigo, sala, None
    return "", None, "La acción de sala no es válida."


def cancelar_temporizador_actual():
    temporizador = temporizadores_ronda.pop(id(gestor_actual()), None)
    if temporizador and not temporizador.done():
        temporizador.cancel()


def cancelar_limpieza_sala(codigo_sala: str):
    tarea = tareas_limpieza_sala.pop(codigo_sala, None)
    if tarea is not None and not tarea.done():
        tarea.cancel()


async def limpiar_sala_abandonada(codigo_sala: str, gestor_sala: GestorJuego):
    tarea_actual = asyncio.current_task()
    try:
        await asyncio.sleep(gestor_sala.ventana_reconexion)
        if (
            codigo_sala != "7K4P"
            and gestores_por_codigo.get(codigo_sala) is gestor_sala
            and not gestor_sala.sesiones_conectadas()
        ):
            temporizador = temporizadores_ronda.pop(id(gestor_sala), None)
            if temporizador is not None and not temporizador.done():
                temporizador.cancel()
            for clave, tarea in list(tareas_ausencia.items()):
                if clave[0] == id(gestor_sala):
                    tareas_ausencia.pop(clave, None)
                    if not tarea.done():
                        tarea.cancel()
            gestores_por_codigo.pop(codigo_sala, None)
    finally:
        if tareas_limpieza_sala.get(codigo_sala) is tarea_actual:
            tareas_limpieza_sala.pop(codigo_sala, None)


def programar_limpieza_sala(codigo_sala: str, gestor_sala: GestorJuego):
    if codigo_sala == "7K4P":
        return
    cancelar_limpieza_sala(codigo_sala)
    tareas_limpieza_sala[codigo_sala] = asyncio.create_task(
        limpiar_sala_abandonada(codigo_sala, gestor_sala)
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


async def broadcast(mensaje: dict):
    codigo_sala = codigo_sala_contexto.get()
    sesiones = gestor.sesiones_conectadas()
    payloads = {
        espectador: json.dumps(
            dict(mensaje, espectador=espectador, codigo_sala=codigo_sala),
            ensure_ascii=False,
        )
        for espectador in {es_espectador for _, _, es_espectador in sesiones}
    }
    await asyncio.gather(*(
        _enviar_texto(sesion["ws"], payloads[es_espectador])
        for _, sesion, es_espectador in sesiones
    ))


async def broadcast_votacion():
    sesiones = gestor.sesiones_conectadas()
    codigo_sala = codigo_sala_contexto.get()
    mensajes = (
        _enviar_texto(
            sesion["ws"],
            json.dumps(
                dict(
                    gestor.serializar_votacion_para(sesion_id, es_espectador),
                    espectador=es_espectador,
                    codigo_sala=codigo_sala,
                ),
                ensure_ascii=False,
            ),
        )
        for sesion_id, sesion, es_espectador in sesiones
    )
    await asyncio.gather(*mensajes)


async def _enviar_texto(websocket, contenido: str):
    try:
        await websocket.send_text(contenido)
    except Exception:
        pass


async def broadcast_estado_actual():
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


def cancelar_aviso_ausencia(nombre: str):
    clave = (id(gestor_actual()), nombre)
    tarea = tareas_ausencia.pop(clave, None)
    if tarea is not None and not tarea.done():
        tarea.cancel()


async def esperar_ausencia(nombre: str):
    tarea_actual = asyncio.current_task()
    try:
        await asyncio.sleep(TIEMPO_PARA_MARCAR_AUSENTE)
        sesiones = list(gestor.jugadores.values()) + list(gestor.espectadores.values())
        if any(
            sesion.get("nombre") == nombre
            and sesion.get("ws") is None
            and sesion.get("desconectado_en") is not None
            and time.time() - sesion["desconectado_en"] >= TIEMPO_PARA_MARCAR_AUSENTE
            for sesion in sesiones
        ):
            await broadcast_estado_actual()
    finally:
        clave = (id(gestor_actual()), nombre)
        if tareas_ausencia.get(clave) is tarea_actual:
            tareas_ausencia.pop(clave, None)


async def esperar_fin_ronda(numero_ronda: int):
    tarea_actual = asyncio.current_task()
    clave = id(gestor_actual())
    try:
        await asyncio.sleep(gestor.duracion_ronda)
        cerrada = await gestor.finalizar_por_tiempo(numero_ronda)
        if not cerrada:
            return
        await broadcast_fase_cerrada()
    finally:
        if temporizadores_ronda.get(clave) is tarea_actual:
            temporizadores_ronda.pop(clave, None)


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
    codigo_sala = "7K4P"
    gestor_contexto.set(gestores_por_codigo[codigo_sala])
    codigo_sala_contexto.set(codigo_sala)

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

            if tipo == "estado_reconexion" and sesion_id is None:
                token = mensaje.get("token")
                codigo_reconexion = mensaje.get("codigo_sala", "7K4P")
                if isinstance(codigo_reconexion, str):
                    codigo_reconexion = codigo_reconexion.strip().upper()
                    sala_reconexion = gestores_por_codigo.get(codigo_reconexion)
                    if sala_reconexion is not None:
                        codigo_sala = codigo_reconexion
                        gestor_contexto.set(sala_reconexion)
                        codigo_sala_contexto.set(codigo_sala)
                if isinstance(token, str):
                    sesion_reconectando = gestor.marcar_reconectando(token)
                    if sesion_reconectando:
                        await broadcast_estado_actual()
                continue

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
                avatar = mensaje.get("avatar")
                if avatar is not None and (not isinstance(avatar, str) or avatar not in AVATARES):
                    await websocket.send_text(json.dumps({
                        "tipo": "error", "mensaje": "El avatar seleccionado no es válido."
                    }, ensure_ascii=False))
                    continue
                accion_sala = mensaje.get("accion_sala")
                codigo_solicitado = mensaje.get("codigo_sala", "")
                if accion_sala is None and not codigo_solicitado:
                    codigo_sala, sala_seleccionada, error_sala = (
                        "7K4P", gestores_por_codigo["7K4P"], None
                    )
                elif accion_sala == "unir" and isinstance(codigo_solicitado, str):
                    codigo_sala, sala_seleccionada, error_sala = seleccionar_sala(
                        accion_sala, codigo_solicitado.strip().upper()
                    )
                elif accion_sala == "crear" and isinstance(codigo_solicitado, str):
                    codigo_sala, sala_seleccionada, error_sala = seleccionar_sala(
                        accion_sala, codigo_solicitado
                    )
                else:
                    codigo_sala, sala_seleccionada, error_sala = (
                        "", None, "La acción de sala o el código no son válidos."
                    )
                if error_sala:
                    await websocket.send_text(json.dumps({
                        "tipo": "error", "mensaje": error_sala
                    }, ensure_ascii=False))
                    continue
                gestor_contexto.set(sala_seleccionada)
                codigo_sala_contexto.set(codigo_sala)
                cancelar_limpieza_sala(codigo_sala)

                sesion, error = await gestor.conectar_sesion(websocket, nombre, token, avatar)
                if error:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                    if not gestor.sesiones_conectadas():
                        programar_limpieza_sala(codigo_sala, gestor_actual())
                    continue

                sesion_id = sesion["id"]
                es_espectador = sesion["es_espectador"]
                cancelar_aviso_ausencia(sesion["nombre"])
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
                    "avatar": sesion["avatar"],
                    "es_anfitrion": sesion["es_anfitrion"],
                    "es_espectador": es_espectador,
                    "reconectado": sesion["reconectado"],
                    "estado": gestor.estado_juego,
                    "codigo_sala": codigo_sala,
                }, ensure_ascii=False))
                estado_inicial = gestor.serializar_estado_para(sesion_id, es_espectador)
                estado_inicial["codigo_sala"] = codigo_sala
                await websocket.send_text(json.dumps(estado_inicial, ensure_ascii=False))
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
                if sesion["reconectado"]:
                    evento = "reconexion"
                    texto = f"🔄 ¡{sesion['nombre']} se reconectó!"
                else:
                    evento = "entrada"
                    texto = f"✨ 👋 ¡{sesion['nombre']} se ha unido!"
                await broadcast({
                    "tipo": "notificacion",
                    "evento": evento,
                    "mensaje": texto,
                    "estado": "success",
                })

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

            elif tipo == "reaccion":
                mensaje_reaccion, error = gestor.crear_mensaje_reaccion(
                    sesion_id, mensaje.get("reaccion")
                )
                if error:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                    continue
                await broadcast(mensaje_reaccion)

            elif tipo == "iniciar_ronda":
                ok, error = await gestor.iniciar_ronda(sesion_id)
                if not ok:
                    await websocket.send_text(json.dumps({
                        "tipo": "error",
                        "mensaje": error
                    }, ensure_ascii=False))
                else:
                    cancelar_temporizador_actual()
                    temporizadores_ronda[id(gestor_actual())] = asyncio.create_task(
                        esperar_fin_ronda(gestor.ronda_actual)
                    )
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
                    cancelar_temporizador_actual()
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
                    cancelar_temporizador_actual()
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
                        cancelar_temporizador_actual()
                        await broadcast_fase_cerrada()
                    continue

                cancelar_temporizador_actual()

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
            if gestor.sesiones_conectadas():
                cancelar_limpieza_sala(codigo_sala)
                cancelar_aviso_ausencia(nombre_desconectado)
                clave_ausencia = (id(gestor_actual()), nombre_desconectado)
                tareas_ausencia[clave_ausencia] = asyncio.create_task(
                    esperar_ausencia(nombre_desconectado)
                )
            else:
                programar_limpieza_sala(codigo_sala, gestor_actual())
                for sala_id, nombre in list(tareas_ausencia):
                    if sala_id == id(gestor_actual()):
                        cancelar_aviso_ausencia(nombre)
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
            await broadcast({
                "tipo": "notificacion",
                "evento": "salida",
                "mensaje": f"👋 {nombre_desconectado} abandonó la partida.",
                "estado": "info",
            })


if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


def iniciar():
    uvicorn.run("backend.web_server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    iniciar()
