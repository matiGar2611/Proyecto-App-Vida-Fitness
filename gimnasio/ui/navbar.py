"""Barra superior y pie de página, iguales en todas las pantallas."""

from nicegui import app, ui

from .. import config
from ..datos.usuarios import actualizar_usuario, obtener_usuario
from ..seguridad import verificar_password
from .componentes import html_confiable
from .logo import LOGO_DATA_URI
from .sesion import cerrar_sesion, es_cliente_rol, es_dueño, registrar_actividad, rol_actual


def abrir_dialogo_cambiar_mi_password():
    """Cualquier usuario logueado (dueño o profe) puede cambiar su
    propia contraseña, sin pasar por la página de Usuarios (esa es
    solo para que el dueño administre las cuentas de los demás)."""
    username_actual = app.storage.user.get('username')
    registro = obtener_usuario(username_actual)
    if registro is None:
        ui.notify('No se pudo identificar tu cuenta.', type='negative')
        return
    user_id, username, password_hash, salt, nombre, rol = registro[0], registro[1], registro[2], registro[3], registro[4], registro[5]

    with ui.dialog() as dialog:
        with ui.card().classes('w-[420px] max-w-[95vw] p-7'):
            ui.label('Cambiar mi contraseña').classes('text-xl font-bold mb-3')

            actual = ui.input('Contraseña actual', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')
            nueva = ui.input('Nueva contraseña', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')
            confirmar = ui.input('Confirmar nueva contraseña', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    if not verificar_password(actual.value, salt, password_hash):
                        ui.notify('La contraseña actual no es correcta.', type='negative')
                        return
                    if not nueva.value or len(nueva.value) < config.MIN_PASSWORD_PERSONAL:
                        ui.notify(f'La nueva contraseña debe tener al menos {config.MIN_PASSWORD_PERSONAL} caracteres.', type='negative')
                        return
                    if nueva.value != confirmar.value:
                        ui.notify('Las contraseñas nuevas no coinciden.', type='negative')
                        return

                    actualizar_usuario(user_id, username, nombre, rol, nueva.value)
                    registrar_actividad('Cambió su contraseña')
                    ui.notify('Contraseña actualizada correctamente.', type='positive')
                    dialog.close()

                ui.button('Guardar', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


def construir_navbar():
    """Dibuja la barra superior de navegación, con las opciones que corresponden según el rol de la sesión activa."""
    with ui.header().classes('app-header px-6'):
        with ui.row().classes('w-full items-center'):
            with ui.row().classes('logo-container'):
                with ui.element('div').classes('logo-icon'):
                    ui.image(LOGO_DATA_URI)
                with ui.element('div').classes('logo-text'):
                    html_confiable('Vida<span>Fitness</span>')

            ui.space()

            # Los enlaces van juntos: en el celular el CSS los pasa a una segunda fila que se desliza.
            with ui.row().classes('nav-links items-center no-wrap' + ('' if es_cliente_rol() else ' nav-links-staff')):
                if es_cliente_rol():
                    ui.button('Mi cuenta', icon='person', on_click=lambda: ui.navigate.to('/mi-cuenta')) \
                        .props('flat').classes('nav-button')
                else:
                    ui.button('Clientes', icon='groups', on_click=lambda: ui.navigate.to('/')) \
                        .props('flat').classes('nav-button')
                    if es_dueño():
                        ui.button('Usuarios', icon='manage_accounts',
                                  on_click=lambda: ui.navigate.to('/usuarios')) \
                            .props('flat').classes('nav-button')
                        ui.button('Contabilidad', icon='account_balance',
                                  on_click=lambda: ui.navigate.to('/contabilidad')) \
                            .props('flat').classes('nav-button')
                        ui.button('Precios', icon='sell',
                                  on_click=lambda: ui.navigate.to('/precios')) \
                            .props('flat').classes('nav-button')
                        ui.button('Información', icon='info',
                                  on_click=lambda: ui.navigate.to('/informacion')) \
                            .props('flat').classes('nav-button')
                        ui.button('Anuncios', icon='campaign',
                                  on_click=lambda: ui.navigate.to('/anuncios')) \
                            .props('flat').classes('nav-button')
                        ui.button('Respaldos', icon='backup',
                                  on_click=lambda: ui.navigate.to('/respaldos')) \
                            .props('flat').classes('nav-button')
                        ui.button('Actividad', icon='history',
                                  on_click=lambda: ui.navigate.to('/actividad')) \
                            .props('flat').classes('nav-button')
                    ui.button(icon='lock', on_click=abrir_dialogo_cambiar_mi_password) \
                        .props('flat round').classes('nav-button').tooltip('Cambiar mi contraseña')

            ui.separator().props('vertical').classes('mx-2').style('height: 28px;')

            with ui.row().classes('items-center gap-2'):
                with ui.element('div').classes('user-avatar'):
                    ui.label(app.storage.user.get('nombre', '?')[0].upper())
                with ui.column().classes('gap-0'):
                    ui.label(app.storage.user.get('nombre', '')).classes('user-info-name')
                    ui.label(rol_actual() or '').classes('user-info-role')

            ui.button(icon='logout', on_click=cerrar_sesion).props('flat round').classes('nav-button')


def construir_footer():
    """Dibuja el pie de página, igual en todas las pantallas."""
    with ui.element('footer').classes('app-footer'):
        with ui.row().classes('items-center justify-center'):
            ui.label('Gimnasio Vida Fitness · gestor interno').classes('footer-text')
