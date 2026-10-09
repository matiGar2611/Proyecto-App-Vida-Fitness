"""Página de respaldos (solo dueño): copias de seguridad de la base de datos."""

from nicegui import ui

from ..servicios import respaldos
from ..tiempo import ahora
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, registrar_actividad, requerir_autenticacion


def _tamano(bytes_):
    return f"{bytes_ / 1024:.0f} KB" if bytes_ < 1024 * 1024 else f"{bytes_ / 1024 / 1024:.1f} MB"


@ui.page('/respaldos')
def pagina_respaldos():
    """Descargar una copia, crear una copia ahora y ver las copias automáticas."""
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

            ui.label('Respaldos').classes('page-title')
            ui.label('La app hace una copia automática por día y guarda las últimas '
                     '14. Además podés bajar una copia a tu compu o a tu Google Drive: '
                     'es la mejor protección si algo le pasa al servidor.') \
                .classes('page-subtitle')

            with ui.column().classes('glass-card w-full p-6 gap-3'):
                ui.label('Descargar copia ahora').classes('text-lg font-bold')
                ui.label('Se descarga un archivo .zip con todos los datos (clientes, pagos, '
                         'contabilidad y cuentas). Contiene datos personales de los socios: '
                         'guardalo en un lugar seguro.').classes('text-sm text-gray-600')

                def descargar():
                    nombre = f"vida-fitness-{ahora():%Y%m%d-%H%M}.zip"
                    ui.download(respaldos.zip_de_respaldo(), nombre)
                    registrar_actividad('Copia de seguridad descargada')

                ui.button('Descargar copia (.zip)', icon='download', on_click=descargar) \
                    .props('unelevated color=primary').classes('self-start')

            ui.label('Copias automáticas en el servidor').classes('text-lg font-bold mt-2')
            with ui.column().classes('table-container w-full p-4 gap-3'):
                with ui.row().classes('items-center gap-3'):
                    def crear_ahora():
                        respaldos.crear_respaldo()
                        registrar_actividad('Copia de seguridad creada')
                        ui.notify('Copia creada.', type='positive')
                        refrescar()

                    ui.button('Crear una copia ahora', icon='backup', on_click=crear_ahora) \
                        .props('outline color=primary')

                columnas = [
                    {'name': 'nombre', 'label': 'Archivo', 'field': 'nombre', 'align': 'left'},
                    {'name': 'tamano', 'label': 'Tamaño', 'field': 'tamano', 'align': 'left'},
                ]
                tabla = ui.table(columns=columnas, rows=[], row_key='nombre').classes('w-full')

                ui.label('Para restaurar una copia: python -m gimnasio.restaurar archivo.db '
                         '(con la app sin uso; antes guarda una copia de lo actual).') \
                    .classes('text-xs text-gray-500')

            def refrescar():
                tabla.rows = [{'nombre': r['nombre'], 'tamano': _tamano(r['bytes'])}
                              for r in respaldos.listar_respaldos()]

            refrescar()

        construir_footer()
