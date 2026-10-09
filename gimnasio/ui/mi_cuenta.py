"""Portal del cliente: vencimiento, rutina, anuncios, datos y cronómetro."""

from urllib.parse import quote

from nicegui import ui

from .. import config
from ..datos.ajustes import cargar_anuncios, cargar_informacion
from ..datos.clientes import buscar_cliente_por_dni, cambiar_password_cliente, verificar_password_cliente
from ..seguridad import sanitizar_html
from ..servicios.estadisticas import dias_para_vencimiento, esta_vencido
from ..tiempo import formatear_fecha, formatear_moneda
from .componentes import html_confiable
from .entrenamiento import agregar_entrenamiento
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import dni_actual, es_cliente_rol, registrar_actividad, requerir_autenticacion


def abrir_dialogo_cambiar_password_cliente(dni, obligatorio=False):
    """El cliente cambia su propia contraseña (la que usa para entrar con su DNI).

    Con obligatorio=True (primer ingreso, o después de que recepción se
    la restableció) el diálogo no se puede cerrar sin elegir una nueva."""
    cliente = buscar_cliente_por_dni(dni)
    if cliente is None:
        ui.notify('No se pudo identificar tu cuenta.', type='negative')
        return

    with ui.dialog() as dialog:
        if obligatorio:
            dialog.props('persistent')
        with ui.card().classes('w-[420px] max-w-[95vw] p-7'):
            ui.label('Elegí tu nueva contraseña' if obligatorio else 'Cambiar mi contraseña') \
                .classes('text-xl font-bold mb-3')
            if obligatorio:
                ui.label('Por seguridad, tenés que cambiar tu contraseña inicial (tu DNI) '
                         'antes de seguir. En "contraseña actual" poné tu DNI.') \
                    .classes('text-sm text-gray-600 mb-2')

            actual = ui.input('Contraseña actual', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')
            nueva = ui.input('Nueva contraseña', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')
            confirmar = ui.input('Confirmar nueva contraseña', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                if not obligatorio:
                    ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    cliente_actualizado = buscar_cliente_por_dni(dni)
                    if cliente_actualizado is None or not verificar_password_cliente(cliente_actualizado, actual.value):
                        ui.notify('La contraseña actual no es correcta.', type='negative')
                        return
                    if not nueva.value or len(nueva.value) < config.MIN_PASSWORD_CLIENTE:
                        ui.notify(f'La nueva contraseña debe tener al menos {config.MIN_PASSWORD_CLIENTE} caracteres.', type='negative')
                        return
                    if nueva.value == dni:
                        ui.notify('La nueva contraseña no puede ser tu DNI.', type='negative')
                        return
                    if nueva.value != confirmar.value:
                        ui.notify('Las contraseñas nuevas no coinciden.', type='negative')
                        return

                    cambiar_password_cliente(dni, nueva.value)
                    registrar_actividad('Cambió su contraseña')
                    ui.notify('Contraseña actualizada correctamente.', type='positive')
                    dialog.close()
                    if obligatorio:
                        ui.navigate.to('/mi-cuenta')

                ui.button('Guardar', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


@ui.page('/mi-cuenta')
def pagina_mi_cuenta():
    """Portal del cliente.

    Muestra el saludo, los anuncios del gimnasio, el vencimiento con
    los días restantes, los botones de WhatsApp y de la encuesta
    anónima, sus datos, la información importante y su rutina."""
    if not requerir_autenticacion():
        return

    if not es_cliente_rol():
        ui.navigate.to('/')
        return

    ui.add_head_html(HEAD_COMUN)
    construir_navbar()

    dni = dni_actual()
    cliente = buscar_cliente_por_dni(dni) if dni else None

    with ui.column().classes('w-full min-h-screen items-center justify-center py-8'):
        with ui.element('div').classes('mi-cuenta-card'):
            if cliente is None:
                ui.label('No pudimos encontrar tu ficha. Consultá con recepción.') \
                    .classes('login-error w-full')
            else:
                if cliente['debe_cambiar_password']:
                    abrir_dialogo_cambiar_password_cliente(dni, obligatorio=True)

                ui.label(f"¡Hola, {cliente['nombre']}!").classes('page-title')
                ui.label('Este es tu resumen en el gimnasio.').classes('page-subtitle mb-4')

                # --- Anuncios del gimnasio ---
                anuncios = cargar_anuncios()
                if anuncios:
                    ui.label('📢 Anuncios').classes('text-lg font-bold mb-1')
                    for anuncio in anuncios[:5]:
                        with ui.column().classes('anuncio-item w-full'):
                            ui.label(formatear_fecha(anuncio['fecha'])).classes('anuncio-fecha')
                            ui.label(anuncio['texto'])

                # --- Botones de consulta: WhatsApp y encuesta anónima ---
                mensaje = quote(
                    f"Hola! Soy {cliente['nombre']} (DNI {cliente['dni']}), "
                    f"quería hacer una consulta."
                )
                link_whatsapp = f"https://wa.me/{config.NUMERO_WHATSAPP_GIMNASIO}?text={mensaje}"
                with ui.row().classes('w-full gap-2 mb-4'):
                    ui.button('Consultar por WhatsApp', icon='chat',
                              on_click=lambda: ui.navigate.to(link_whatsapp, new_tab=True)) \
                        .props('unelevated').classes('btn-whatsapp flex-1')
                    ui.button('Encuesta / Sugerencias', icon='feedback',
                              on_click=lambda: ui.navigate.to(config.LINK_ENCUESTA, new_tab=True)) \
                        .props('outline color=primary').classes('flex-1')

                # --- Vencimiento y días restantes ---
                dias = dias_para_vencimiento(cliente)
                vencido = esta_vencido(cliente)

                with ui.column().classes(('venc-vencido' if vencido else 'venc-ok') + ' w-full mb-4'):
                    ui.label(f"Próximo vencimiento: {formatear_fecha(cliente['fecha_vencimiento'])}")
                    if vencido:
                        ui.label(f"Tu cuota está vencida hace {abs(dias)} día(s).")
                    else:
                        ui.label(f"Te quedan {dias} día(s) de cuota vigente.")

                # --- Saldo pendiente (solo si tiene deuda) ---
                saldo_pendiente = cliente['saldo_pendiente']
                if saldo_pendiente > 0:
                    ui.label(f"Tenés un saldo pendiente de {formatear_moneda(saldo_pendiente)}. "
                             f"Acercate a completarlo cuando puedas.") \
                        .classes('deuda-aviso w-full mb-4')

                # --- Tus datos ---
                with ui.row().classes('w-full items-center justify-between mt-2 mb-1'):
                    ui.label('Tus datos').classes('text-lg font-bold')
                    ui.button('Cambiar mi contraseña', icon='lock',
                              on_click=lambda: abrir_dialogo_cambiar_password_cliente(dni)) \
                        .props('flat dense color=primary')

                datos = [
                    ('DNI', cliente['dni']),
                    ('Teléfono', cliente['telefono']),
                    ('Plan', cliente['plan']),
                    ('Fecha de nacimiento',
                        formatear_fecha(cliente['fecha_nacimiento'])
                        if cliente['fecha_nacimiento'] else '-'),
                    ('Último pago', formatear_fecha(cliente['fecha_ultimo_pago'])),
                    ('Estado', 'Activo' if cliente['activo'] else 'Inactivo'),
                ]
                for etiqueta, valor in datos:
                    with ui.row().classes('dato-fila w-full'):
                        ui.label(etiqueta).classes('dato-label')
                        ui.label(str(valor)).classes('dato-valor')

                # --- Información importante ---
                ui.label('Información importante').classes('text-lg font-bold mt-5 mb-1')
                with ui.column().classes('info-importante w-full'):
                    ui.label(cargar_informacion())

                # --- Rutina ---
                ui.label('Mi rutina').classes('text-lg font-bold mt-5 mb-1')
                texto_rutina = cliente['rutina'].strip()
                with ui.column().classes('rutina-cliente w-full'):
                    if texto_rutina:
                        html_confiable(sanitizar_html(texto_rutina))
                    else:
                        ui.label('Todavía no tenés una rutina cargada. Consultá con tu profe.')

                # --- Cronómetro y contador de rondas ---
                agregar_entrenamiento(dni)

        construir_footer()
