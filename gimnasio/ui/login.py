"""Pantalla de ingreso: Profesor (usuario y contraseña) o Cliente (DNI y contraseña)."""

from nicegui import app, ui

from ..datos.clientes import buscar_cliente_por_dni, guardar_password_cliente, verificar_password_cliente
from ..datos.usuarios import actualizar_usuario, obtener_usuario
from ..seguridad import (gastar_tiempo_de_verificacion, limpiar_fallos, necesita_rehash, registrar_fallo,
                         segundos_de_bloqueo, texto_bloqueo, verificar_password)
from .estilos import HEAD_COMUN
from .logo import LOGO_DATA_URI
from .sesion import es_cliente_rol, registrar_actividad, verificar_autenticacion


@ui.page('/login')
def pagina_login():
    """Pantalla de inicio de sesión: 'Profesor' (usuario y contraseña, para dueño o profe) o 'Cliente' (solo DNI)."""
    if verificar_autenticacion():
        ui.navigate.to('/mi-cuenta' if es_cliente_rol() else '/')
        return

    ui.add_head_html(HEAD_COMUN)

    with ui.element('div').classes('login-page w-full'):
        with ui.element('div').classes('login-card'):
            with ui.column().classes('items-center gap-4 mb-4 w-full'):
                with ui.element('div').classes('logo-icon-grande'):
                    ui.image(LOGO_DATA_URI)
                ui.label('Gimnasio Vida Fitness').classes('login-title')
                ui.label('¿Cómo querés ingresar?').classes('login-subtitle')

            selector = ui.column().classes('w-full')
            contenedor_admin = ui.column().classes('w-full')
            contenedor_cliente = ui.column().classes('w-full')
            contenedor_admin.visible = False
            contenedor_cliente.visible = False

            with selector:
                with ui.row().classes('w-full gap-2'):
                    def elegir_admin():
                        selector.visible = False
                        contenedor_admin.visible = True

                    def elegir_cliente():
                        selector.visible = False
                        contenedor_cliente.visible = True

                    ui.button('Profesor', icon='badge',
                              on_click=elegir_admin).props('unelevated color=primary').classes('flex-1')
                    ui.button('Cliente', icon='person',
                              on_click=elegir_cliente).props('outline color=primary').classes('flex-1')

            # ---- Formulario Administrador / Profe ----
            with contenedor_admin:
                error_admin = ui.column().classes('w-full')
                username_input = ui.input('Usuario').props('outlined autocomplete=username').classes('w-full')
                password_input = ui.input(
                    'Contraseña', password=True, password_toggle_button=True
                ).props('outlined autocomplete=current-password').classes('w-full')

                def intentar_login_admin():
                    error_admin.clear()
                    usuario = username_input.value.strip()
                    clave = password_input.value

                    if not usuario or not clave:
                        with error_admin:
                            ui.label('Completá usuario y contraseña').classes('login-error w-full')
                        return

                    clave_intentos = f"admin:{usuario.lower()}"
                    espera = segundos_de_bloqueo(clave_intentos)
                    if espera:
                        with error_admin:
                            ui.label(texto_bloqueo(espera)).classes('login-error w-full')
                        return

                    registro = obtener_usuario(usuario)
                    if registro is None:
                        gastar_tiempo_de_verificacion(clave)  # igualar tiempos de respuesta
                        credenciales_ok = False
                    else:
                        credenciales_ok = verificar_password(clave, registro[3], registro[2])

                    if not credenciales_ok:
                        registrar_fallo(clave_intentos)
                        with error_admin:
                            ui.label('Usuario o contraseña incorrectos').classes('login-error w-full')
                        return

                    limpiar_fallos(clave_intentos)
                    if necesita_rehash(registro[2]):
                        # Cuenta con hash viejo: se pasa al formato nuevo ahora que sabemos la clave.
                        actualizar_usuario(registro[0], registro[1], registro[4], registro[5], clave)

                    app.storage.user['id'] = registro[0]
                    app.storage.user['username'] = registro[1]
                    app.storage.user['nombre'] = registro[4]
                    app.storage.user['rol'] = registro[5]
                    registrar_actividad('Inicio de sesión')

                    ui.notify(f'Bienvenido, {registro[4]}', type='positive')
                    ui.navigate.to('/')

                ui.button('Ingresar', icon='login', on_click=intentar_login_admin) \
                    .props('unelevated color=primary').classes('w-full mt-2')
                username_input.on('keydown.enter', lambda e: intentar_login_admin())
                password_input.on('keydown.enter', lambda e: intentar_login_admin())

                def volver_admin():
                    contenedor_admin.visible = False
                    selector.visible = True

                ui.button('Volver', icon='arrow_back', on_click=volver_admin) \
                    .props('flat').classes('w-full mt-2')

            # ---- Formulario Cliente (DNI como usuario y contraseña) ----
            with contenedor_cliente:
                error_cliente = ui.column().classes('w-full')
                dni_input = ui.input('Tu DNI (usuario)').props('outlined inputmode=numeric autocomplete=username').classes('w-full')
                password_cliente_input = ui.input(
                    'Contraseña', password=True, password_toggle_button=True,
                    placeholder='La primera vez es tu propio DNI'
                ).props('outlined autocomplete=current-password').classes('w-full')

                def intentar_login_cliente():
                    error_cliente.clear()
                    dni = dni_input.value.strip()
                    clave = password_cliente_input.value

                    if not dni or not clave:
                        with error_cliente:
                            ui.label('Ingresá tu DNI y tu contraseña.').classes('login-error w-full')
                        return

                    clave_intentos = f"cliente:{dni}"
                    espera = segundos_de_bloqueo(clave_intentos)
                    if espera:
                        with error_cliente:
                            ui.label(texto_bloqueo(espera)).classes('login-error w-full')
                        return

                    cliente = buscar_cliente_por_dni(dni)
                    if cliente is None:
                        gastar_tiempo_de_verificacion(clave)  # igualar tiempos de respuesta
                        credenciales_ok = False
                    else:
                        credenciales_ok = verificar_password_cliente(cliente, clave)

                    if not credenciales_ok:
                        registrar_fallo(clave_intentos)
                        with error_cliente:
                            ui.label('DNI o contraseña incorrectos. Si no podés ingresar, consultá con recepción.') \
                                .classes('login-error w-full')
                        return

                    limpiar_fallos(clave_intentos)

                    # Si tiene un hash del formato viejo, se lo actualiza al nuevo.
                    if necesita_rehash(cliente['password_hash']):
                        guardar_password_cliente(dni, clave, cliente['debe_cambiar_password'])

                    app.storage.user['rol'] = 'cliente'
                    app.storage.user['dni'] = dni
                    app.storage.user['nombre'] = cliente['nombre']

                    ui.notify(f"Bienvenido, {cliente['nombre']}", type='positive')
                    ui.navigate.to('/mi-cuenta')

                ui.button('Ingresar', icon='login', on_click=intentar_login_cliente) \
                    .props('unelevated color=primary').classes('w-full mt-2')
                dni_input.on('keydown.enter', lambda e: intentar_login_cliente())
                password_cliente_input.on('keydown.enter', lambda e: intentar_login_cliente())

                def volver_cliente():
                    contenedor_cliente.visible = False
                    selector.visible = True

                ui.button('Volver', icon='arrow_back', on_click=volver_cliente) \
                    .props('flat').classes('w-full mt-2')
