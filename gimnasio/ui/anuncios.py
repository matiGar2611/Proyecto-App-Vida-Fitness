"""Página para publicar y borrar anuncios (solo dueño)."""

from nicegui import ui

from ..datos.ajustes import agregar_anuncio, cargar_anuncios, eliminar_anuncio
from ..tiempo import formatear_fecha
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, registrar_actividad, requerir_autenticacion


@ui.page('/anuncios')
def pagina_anuncios():
    """Página para publicar y borrar anuncios (solo dueño). Los
    anuncios se muestran a los clientes en su portal y al personal
    en la página de Clientes."""
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

            ui.label('Anuncios').classes('page-title')
            ui.label('Lo que publiques acá lo ven los clientes al entrar a su '
                      'cuenta, y también el personal en la página de Clientes.') \
                .classes('page-subtitle')

            with ui.column().classes('glass-card w-full p-6'):
                ui.label('Nuevo anuncio').classes('text-lg font-bold mb-2')
                texto_nuevo = ui.textarea(placeholder='Escribí el anuncio...') \
                    .props('outlined rows=3').classes('w-full')

                def publicar():
                    if not texto_nuevo.value.strip():
                        ui.notify('Escribí un texto antes de publicar.', type='negative')
                        return
                    agregar_anuncio(texto_nuevo.value.strip())
                    registrar_actividad('Anuncio publicado')
                    texto_nuevo.value = ''
                    ui.notify('Anuncio publicado.', type='positive')
                    refrescar()

                ui.button('Publicar', icon='campaign', on_click=publicar) \
                    .props('unelevated color=primary').classes('mt-2')

            ui.label('Anuncios publicados').classes('text-lg font-bold mt-4')
            contenedor_lista = ui.column().classes('w-full')

            def refrescar():
                contenedor_lista.clear()
                with contenedor_lista:
                    anuncios = cargar_anuncios()
                    if not anuncios:
                        ui.label('Todavía no publicaste ningún anuncio.').classes('text-gray-500')
                    for anuncio in anuncios:
                        with ui.row().classes('anuncio-item w-full items-center justify-between'):
                            with ui.column().classes('gap-0'):
                                ui.label(formatear_fecha(anuncio['fecha'])).classes('anuncio-fecha')
                                ui.label(anuncio['texto'])

                            def eliminar(anuncio_id=anuncio['id']):
                                eliminar_anuncio(anuncio_id)
                                registrar_actividad('Anuncio eliminado')
                                ui.notify('Anuncio eliminado.', type='positive')
                                refrescar()

                            ui.button(icon='delete', on_click=eliminar).props('flat round color=negative')

            refrescar()

        construir_footer()
