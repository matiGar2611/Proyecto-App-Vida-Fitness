"""Página de cuentas del personal (solo dueño): alta, edición y baja de dueños y profes."""

from nicegui import app, ui

from .. import config
from ..datos.usuarios import (actualizar_usuario, contar_dueños, crear_usuario, eliminar_usuario, obtener_todos_usuarios,
                              obtener_usuario, obtener_usuario_por_id)
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, registrar_actividad, requerir_autenticacion


def abrir_formulario_usuario(al_guardar):
    """Diálogo para crear una cuenta nueva de dueño o profe."""
    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Nuevo usuario').classes('text-2xl font-bold mb-2')

            username = ui.input('Usuario').props('outlined').classes('w-full')
            nombre = ui.input('Nombre completo').props('outlined').classes('w-full')
            password = ui.input('Contraseña', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')
            rol = ui.select(config.ROLES, value='profe', label='Rol').props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    if not username.value.strip() or not nombre.value.strip():
                        ui.notify('Usuario y nombre son obligatorios.', type='negative')
                        return
                    if not password.value or len(password.value) < config.MIN_PASSWORD_PERSONAL:
                        ui.notify(f'La contraseña debe tener al menos {config.MIN_PASSWORD_PERSONAL} caracteres.', type='negative')
                        return
                    if obtener_usuario(username.value.strip()):
                        ui.notify('Ese nombre de usuario ya existe.', type='negative')
                        return

                    crear_usuario(username.value.strip(), password.value, nombre.value.strip(), rol.value)
                    registrar_actividad('Usuario creado', f'{username.value.strip()} ({rol.value})')
                    ui.notify('Usuario creado correctamente.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Crear usuario', icon='person_add', on_click=guardar) \
                    .props('unelevated color=primary')

    dialog.open()


def abrir_formulario_editar_usuario(user_id, al_guardar):
    """Diálogo para editar una cuenta existente, incluyendo un cambio de contraseña opcional."""
    usuario = obtener_usuario_por_id(user_id)
    if usuario is None:
        ui.notify('No se encontró el usuario.', type='negative')
        return
    _, username_actual, _, _, nombre_actual, rol_actual_valor = usuario

    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Editar usuario').classes('text-2xl font-bold mb-2')

            username = ui.input('Usuario', value=username_actual).props('outlined').classes('w-full')
            nombre = ui.input('Nombre completo', value=nombre_actual).props('outlined').classes('w-full')
            rol = ui.select(config.ROLES, value=rol_actual_valor, label='Rol').props('outlined').classes('w-full')
            password = ui.input(
                'Nueva contraseña (opcional)', password=True, password_toggle_button=True,
                placeholder='Dejar en blanco para no cambiarla'
            ).props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    nuevo_username = username.value.strip()
                    if not nuevo_username or not nombre.value.strip():
                        ui.notify('Usuario y nombre son obligatorios.', type='negative')
                        return
                    if password.value and len(password.value) < config.MIN_PASSWORD_PERSONAL:
                        ui.notify(f'La contraseña debe tener al menos {config.MIN_PASSWORD_PERSONAL} caracteres.', type='negative')
                        return

                    otro = obtener_usuario(nuevo_username)
                    if otro and otro[0] != user_id:
                        ui.notify('Ese nombre de usuario ya lo usa otra cuenta.', type='negative')
                        return

                    if rol_actual_valor == 'dueño' and rol.value != 'dueño' and contar_dueños() <= 1:
                        ui.notify('Tiene que quedar al menos una cuenta de dueño.', type='negative')
                        return

                    actualizar_usuario(user_id, nuevo_username, nombre.value.strip(),
                                       rol.value, password.value or None)
                    registrar_actividad('Usuario editado', f'{nuevo_username} ({rol.value})')
                    if user_id == app.storage.user.get('id'):
                        app.storage.user['username'] = nuevo_username
                        app.storage.user['nombre'] = nombre.value.strip()
                        app.storage.user['rol'] = rol.value
                    ui.notify('Usuario actualizado.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Guardar cambios', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


@ui.page('/usuarios')
def pagina_usuarios():
    """Página de administración de cuentas (solo dueño): alta, edición y borrado de usuarios."""
    if not requerir_autenticacion():
        return

    if not es_dueño():
        ui.notify('No tenés permisos para acceder a esta página.', type='negative')
        ui.navigate.to('/')
        return

    ui.add_head_html(HEAD_COMUN)
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-6'):

            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label('Usuarios').classes('page-title')
                    ui.label('Cuentas de acceso: dueño y profes.').classes('page-subtitle')
                ui.button('Nuevo usuario', icon='person_add',
                          on_click=lambda: abrir_formulario_usuario(refrescar)) \
                    .props('unelevated color=primary').classes('px-5')

            with ui.column().classes('table-container w-full'):
                columnas = [
                    {'name': 'username', 'label': 'USUARIO', 'field': 'username', 'align': 'left'},
                    {'name': 'nombre', 'label': 'NOMBRE', 'field': 'nombre', 'align': 'left'},
                    {'name': 'rol', 'label': 'ROL', 'field': 'rol', 'align': 'left'},
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'right'},
                ]
                tabla = ui.table(columns=columnas, rows=[], row_key='id').classes('w-full')

                tabla.add_slot('body-cell-acciones', '''
                    <q-td :props="props">
                        <q-btn flat round dense icon="edit" color="primary"
                               @click="$parent.$emit('editar', props.row)">
                            <q-tooltip>Editar usuario</q-tooltip>
                        </q-btn>
                        <q-btn v-if="props.row.username !== 'admin'" flat round dense icon="delete"
                               color="negative" @click="$parent.$emit('eliminar', props.row)">
                            <q-tooltip>Eliminar usuario</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')

                def on_editar(e):
                    abrir_formulario_editar_usuario(e.args['id'], refrescar)

                def on_eliminar(e):
                    if not es_dueño():
                        ui.notify('No tenés permisos para eliminar usuarios.', type='negative')
                        return
                    objetivo = obtener_usuario_por_id(e.args['id'])
                    if objetivo is None:
                        refrescar()
                        return
                    if objetivo[0] == app.storage.user.get('id'):
                        ui.notify('No podés eliminar tu propia cuenta.', type='negative')
                        return
                    if objetivo[1] == 'admin' or (objetivo[5] == 'dueño' and contar_dueños() <= 1):
                        ui.notify('Esta cuenta no se puede eliminar.', type='negative')
                        return
                    eliminar_usuario(objetivo[0])
                    registrar_actividad('Usuario eliminado', f'{objetivo[1]} ({objetivo[5]})')
                    ui.notify('Usuario eliminado.', type='positive')
                    refrescar()

                tabla.on('editar', on_editar)
                tabla.on('eliminar', on_eliminar)

                def refrescar():
                    tabla.rows = [
                        {'id': u[0], 'username': u[1], 'nombre': u[2], 'rol': u[3]}
                        for u in obtener_todos_usuarios()
                    ]

                refrescar()

        construir_footer()
