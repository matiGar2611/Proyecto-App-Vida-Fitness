"""Preparación de la aplicación al iniciar: base de datos, migración,
cuenta del dueño y respaldos automáticos."""

import asyncio
import logging

from . import db
from .datos import usuarios
from .servicios import migracion, respaldos

log = logging.getLogger(__name__)

_tareas = set()  # referencia a las tareas en segundo plano (si no, Python las puede descartar)


def preparar():
    """Deja todo listo para atender pedidos. Se llama una vez, antes de ui.run()."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    db.inicializar()
    migracion.migrar_si_corresponde()
    usuarios.asegurar_cuenta_dueño()
    usuarios.endurecer_admin_de_fabrica()


async def _bucle_respaldos(cada_segundos=3600):
    while True:
        try:
            ruta = await asyncio.to_thread(respaldos.respaldo_diario_si_falta)
            if ruta:
                log.info("Respaldo diario creado: %s", ruta)
        except Exception:
            log.exception("Falló el respaldo diario")
        await asyncio.sleep(cada_segundos)


def iniciar_respaldos_automaticos(app):
    """Hace una copia por día mientras la app esté corriendo (revisa cada hora)."""
    async def arrancar():
        tarea = asyncio.create_task(_bucle_respaldos())
        _tareas.add(tarea)
        tarea.add_done_callback(_tareas.discard)

    app.on_startup(arrancar)
