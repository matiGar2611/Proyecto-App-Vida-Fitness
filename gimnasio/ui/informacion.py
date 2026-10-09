"""Página para editar el texto de 'Información importante' que ven los clientes (solo dueño)."""

from nicegui import ui

from ..datos.ajustes import cargar_informacion, guardar_informacion
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, registrar_actividad, requerir_autenticacion


@ui.page('/informacion')
def pagina_informacion():
    """Página para editar el texto de 'Información importante' que ven los clientes (solo dueño)."""
    if not requerir_autenticacion():
        return

    if not es_dueño():
        ui.notify('No tenés permisos para acceder a esta página.', type='negative')
        ui.navigate.to('/')
        return

    ui.add_head_html(HEAD_COMUN)
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-3xl mx-auto p-8 gap-6'):

            ui.label('Información importante').classes('page-title')
            ui.label('Este texto es el que ven todos los clientes en su portal '
                      '(horarios, uso de toallas, cómo avisar si van a dejar de '
                      'asistir, etc.). Editalo y guardá los cambios.') \
                .classes('page-subtitle')

            with ui.column().classes('glass-card w-full p-6'):
                texto = ui.textarea(value=cargar_informacion()) \
                    .props('outlined rows=10').classes('w-full')

                def guardar():
                    guardar_informacion(texto.value.strip())
                    registrar_actividad('Información para clientes actualizada')
                    ui.notify('Información actualizada. Ya la ven los clientes.', type='positive')

                ui.button('Guardar cambios', icon='save', on_click=guardar) \
                    .props('unelevated color=primary').classes('mt-3')

        construir_footer()
