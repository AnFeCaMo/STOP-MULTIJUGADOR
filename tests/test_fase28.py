import asyncio

from backend import web_server
from backend.servidor import GestorJuego


def test_limpieza_de_sala_abandonada_libera_registros_y_tareas():
    async def caso():
        codigo, gestor, error = web_server.seleccionar_sala("crear")
        assert error is None
        gestor.ventana_reconexion = 0.01
        tarea_temporizador = asyncio.create_task(asyncio.sleep(10))
        tarea_ausencia = asyncio.create_task(asyncio.sleep(10))
        web_server.temporizadores_ronda[id(gestor)] = tarea_temporizador
        clave_ausencia = (id(gestor), "Ana")
        web_server.tareas_ausencia[clave_ausencia] = tarea_ausencia

        tarea_limpieza = asyncio.create_task(
            web_server.limpiar_sala_abandonada(codigo, gestor)
        )
        web_server.tareas_limpieza_sala[codigo] = tarea_limpieza
        await tarea_limpieza
        await asyncio.gather(
            tarea_temporizador, tarea_ausencia, return_exceptions=True
        )

        assert codigo not in web_server.gestores_por_codigo
        assert codigo not in web_server.tareas_limpieza_sala
        assert id(gestor) not in web_server.temporizadores_ronda
        assert clave_ausencia not in web_server.tareas_ausencia
        assert tarea_temporizador.cancelled()
        assert tarea_ausencia.cancelled()

    asyncio.run(caso())


def test_cancelar_limpieza_preserva_sala_durante_reconexion():
    async def caso():
        codigo, gestor, error = web_server.seleccionar_sala("crear")
        assert error is None
        gestor.ventana_reconexion = 0.01

        tarea_limpieza = asyncio.create_task(
            web_server.limpiar_sala_abandonada(codigo, gestor)
        )
        web_server.tareas_limpieza_sala[codigo] = tarea_limpieza
        web_server.cancelar_limpieza_sala(codigo)

        _, error = await gestor.conectar_sesion(object(), "Ana")
        assert error is None
        await asyncio.sleep(0.02)

        assert web_server.gestores_por_codigo[codigo] is gestor
        assert codigo not in web_server.tareas_limpieza_sala
        web_server.gestores_por_codigo.pop(codigo, None)

    asyncio.run(caso())


def test_temporizador_de_ronda_se_quita_del_registro_al_terminar(monkeypatch):
    async def caso():
        gestor = GestorJuego(duracion_ronda=0)
        web_server.gestor_contexto.set(gestor)
        web_server.codigo_sala_contexto.set("TEST")

        async def no_broadcast():
            return None

        async def finalizar(numero_ronda):
            return False

        monkeypatch.setattr(web_server, "broadcast_fase_cerrada", no_broadcast)
        monkeypatch.setattr(gestor, "finalizar_por_tiempo", finalizar)
        tarea = asyncio.create_task(web_server.esperar_fin_ronda(1))
        web_server.temporizadores_ronda[id(gestor)] = tarea
        await tarea

        assert id(gestor) not in web_server.temporizadores_ronda

    asyncio.run(caso())
