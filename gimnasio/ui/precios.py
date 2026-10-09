"""Página de precios por plan (solo dueño)."""

from nicegui import ui

from .. import config
from ..datos.ajustes import cargar_precios, guardar_precios
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, registrar_actividad, requerir_autenticacion


@ui.page('/precios')
def pagina_precios():
    """Página para editar el precio de cada plan (solo dueño)."""
    if not requerir_autenticacion():
        return

    if not es_dueño():
        ui.notify('No tenés permisos para acceder a esta página.', type='negative')
        ui.navigate.to('/')
        return

    ui.add_head_html(HEAD_COMUN)
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-2xl mx-auto p-8 gap-6'):

            ui.label('Precios por plan').classes('page-title')
            ui.label('Estos son los valores que se usan para calcular los ingresos '
                      'esperados y lo cobrado del mes. Actualizalos cuando cambien.') \
                .classes('page-subtitle')

            with ui.column().classes('glass-card w-full p-6 gap-3'):
                precios_actuales = cargar_precios()
                campos = {}
                for plan in config.PLANES:
                    campos[plan] = ui.number(
                        label=plan, value=precios_actuales.get(plan, 0), min=0, step=500, prefix='$'
                    ).props('outlined').classes('w-full')

                def guardar():
                    nuevos_precios = {plan: (campo.value or 0) for plan, campo in campos.items()}
                    guardar_precios(nuevos_precios)
                    registrar_actividad('Precios actualizados', ', '.join(f'{p}: {v:g}' for p, v in nuevos_precios.items()))
                    ui.notify('Precios actualizados.', type='positive')

                ui.button('Guardar precios', icon='save', on_click=guardar) \
                    .props('unelevated color=primary').classes('mt-2')

        construir_footer()
