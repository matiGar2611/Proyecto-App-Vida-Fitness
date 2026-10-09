"""Arranque de la aplicación Gestor de Gimnasio Vida Fitness.

Se ejecuta con:  python main.py
Variables de entorno: ver gimnasio/config.py (DATA_DIR, ADMIN_PASSWORD, STORAGE_SECRET, PORT).
"""

import os

from nicegui import app, ui

from gimnasio import arranque, seguridad

arranque.preparar()                        # base de datos, migración de datos viejos y cuenta del dueño
import gimnasio.ui  # noqa: E402,F401      # registra todas las páginas
arranque.iniciar_respaldos_automaticos(app)

ui.run(
    title='Gimnasio Vida Fitness',
    favicon='🏋️',
    reload=False,
    storage_secret=seguridad.obtener_storage_secret(),
)

# Si la variable de entorno PORT viene con un valor que no es un
# número (por ejemplo, mal configurada en el panel del hosting),
# usamos 8080 en vez de que el programa se caiga al arrancar.
try:
    _puerto = int(os.environ.get('PORT', 8080))
except (TypeError, ValueError):
    _puerto = 8080

ui.run(
    host='0.0.0.0',
    port=_puerto,
)
