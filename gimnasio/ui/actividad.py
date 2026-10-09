"""Registro de actividad (solo dueño): quién hizo qué y cuándo."""

from datetime import datetime

from nicegui import ui

from ..datos import auditoria
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, requerir_autenticacion


def _formatear(fecha_hora):
    try:
        return datetime.fromisoformat(fecha_hora).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return fecha_hora


@ui.page('/actividad')
def pagina_actividad():
    """Las últimas 200 acciones registradas (pagos, altas, bajas, cambios de precios...)."""
    if not requerir_autenticacion():
        return

    if not es_dueño():
        ui.notify('No tenés permisos para acceder a esta página.', type='negative')
        ui.navigate.to('/')
        return

    ui.add_head_html(HEAD_COMUN)
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-5xl mx-auto p-8 gap-6'):

            ui.label('Actividad').classes('page-title')
            ui.label('Quién hizo qué y cuándo. Se ven las últimas 200 acciones.') \
                .classes('page-subtitle')

            with ui.column().classes('table-container w-full p-4'):
                columnas = [
                    {'name': 'fecha', 'label': 'Fecha y hora', 'field': 'fecha', 'align': 'left'},
                    {'name': 'actor', 'label': 'Quién', 'field': 'actor', 'align': 'left'},
                    {'name': 'accion', 'label': 'Acción', 'field': 'accion', 'align': 'left'},
                    {'name': 'detalle', 'label': 'Detalle', 'field': 'detalle', 'align': 'left'},
                ]
                filas = [{
                    'id': a['id'],
                    'fecha': _formatear(a['fecha_hora']),
                    'actor': a['actor'],
                    'accion': a['accion'],
                    'detalle': a['detalle'],
                } for a in auditoria.ultimas(200)]
                ui.table(columns=columnas, rows=filas, row_key='id').classes('w-full')

        construir_footer()
