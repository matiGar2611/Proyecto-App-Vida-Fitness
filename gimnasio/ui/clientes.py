"""Página principal (clientes) y sus diálogos: alta, edición, pagos, historial, rutina."""

from datetime import timedelta

from nicegui import ui

from .. import tiempo
from ..datos.ajustes import cargar_anuncios, precio_de_plan
from ..datos.clientes import (actualizar_cliente, actualizar_rutina, agregar_cliente, buscar_cliente_por_dni,
                              eliminar_cliente, restablecer_password_cliente)
from ..datos.pagos import abonar_deuda, registrar_pago
from ..servicios.estadisticas import (contadores, exportar_clientes_csv, ingresos_cobrados_mes_actual,
                                      ingresos_esperados_mensuales, obtener_filas, proximos_cumpleanos,
                                      proximos_vencimientos)
from ..tiempo import formatear_fecha, formatear_moneda
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_cliente_rol, es_dueño, registrar_actividad, requerir_autenticacion


def abrir_formulario_cliente(al_guardar):
    """Diálogo para dar de alta un cliente nuevo."""
    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Nuevo cliente').classes('text-2xl font-bold')

            dni = ui.input('DNI (8 caracteres)').props('outlined').classes('w-full')
            nombre = ui.input('Nombre y Apellido').props('outlined').classes('w-full')
            telefono = ui.input('Teléfono (10 caracteres)').props('outlined').classes('w-full')
            plan = ui.select(
                ['2 veces por semana', '3 veces por semana', 'Todos los días'],
                value='2 veces por semana', label='Plan'
            ).props('outlined').classes('w-full')

            monto = ui.number(
                label='Monto que abona ahora (primer pago)', value=precio_de_plan(plan.value),
                min=0, step=500, prefix='$'
            ).props('outlined').classes('w-full')

            def al_cambiar_plan():
                monto.value = precio_de_plan(plan.value)

            plan.on_value_change(al_cambiar_plan)

            ui.label('Fecha de nacimiento').classes('text-sm text-gray-600 mt-2')
            nacimiento = ui.date().props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    dni_ingresado = dni.value.strip()
                    telefono_ingresado = telefono.value.strip()

                    if len(dni_ingresado) != 8 or not dni_ingresado.isdigit():
                        ui.notify('El DNI debe tener 8 dígitos numéricos.', type='negative')
                        return
                    if len(telefono_ingresado) != 10 or not telefono_ingresado.isdigit():
                        ui.notify('El teléfono debe tener 10 dígitos numéricos.', type='negative')
                        return
                    if not nacimiento.value:
                        ui.notify('Elegí la fecha de nacimiento.', type='negative')
                        return
                    primer_pago = monto.value or 0
                    if primer_pago <= 0:
                        ui.notify('El monto del primer pago tiene que ser mayor a cero.', type='negative')
                        return

                    if not agregar_cliente(dni_ingresado, nombre.value.strip(), telefono_ingresado,
                                           plan.value, nacimiento.value, primer_pago):
                        ui.notify('Este DNI ya está registrado.', type='negative')
                        return

                    registrar_actividad(
                        'Cliente creado',
                        f'{nombre.value.strip()} (DNI {dni_ingresado}): primer pago {formatear_moneda(primer_pago)}')
                    ui.notify('Cliente agregado correctamente.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Guardar', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


def abrir_formulario_editar_cliente(dni_original, al_guardar):
    """Diálogo para editar los datos de un cliente existente (el DNI no se puede cambiar)."""
    cliente = buscar_cliente_por_dni(dni_original)
    if cliente is None:
        ui.notify('No se encontró el cliente.', type='negative')
        return

    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Editar cliente').classes('text-2xl font-bold')
            ui.label(f'DNI: {dni_original} (no editable)').classes('text-sm text-gray-500 mb-2')

            nombre = ui.input('Nombre y Apellido', value=cliente['nombre']) \
                .props('outlined').classes('w-full')
            telefono = ui.input('Teléfono (10 caracteres)', value=cliente['telefono']) \
                .props('outlined').classes('w-full')
            plan = ui.select(
                ['2 veces por semana', '3 veces por semana', 'Todos los días'],
                value=cliente['plan'], label='Plan'
            ).props('outlined').classes('w-full')

            ui.label('Fecha de nacimiento').classes('text-sm text-gray-600 mt-2')
            nacimiento = ui.date(value=cliente['fecha_nacimiento']).props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    telefono_ingresado = telefono.value.strip()
                    if len(telefono_ingresado) != 10 or not telefono_ingresado.isdigit():
                        ui.notify('El teléfono debe tener 10 dígitos numéricos.', type='negative')
                        return
                    if not nacimiento.value:
                        ui.notify('Elegí la fecha de nacimiento.', type='negative')
                        return

                    actualizar_cliente(dni_original, nombre.value.strip(),
                                       telefono_ingresado, plan.value, nacimiento.value)
                    registrar_actividad('Cliente editado', f'{nombre.value.strip()} (DNI {dni_original})')
                    ui.notify('Cliente actualizado.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Guardar cambios', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


def abrir_dialogo_pago(dni, nombre, al_registrar):
    """Diálogo para registrar un pago (total o parcial).

    Se elige con un calendario hasta qué fecha queda cubierta la
    cuota y cuánto abona el cliente ahora. Si abona menos que el
    precio del plan, la diferencia queda como saldo pendiente."""
    cliente = buscar_cliente_por_dni(dni)
    precio_plan = precio_de_plan(cliente['plan']) if cliente else 0
    saldo_actual = cliente['saldo_pendiente'] if cliente else 0

    with ui.dialog() as dialog:
        with ui.card().classes('w-[420px] max-w-[95vw] p-7'):
            ui.label('Registrar pago').classes('text-xl font-bold')
            ui.label(f'Cliente: {nombre}').classes('text-gray-600')
            ui.label(f'Precio del plan: {formatear_moneda(precio_plan)}').classes('text-sm text-gray-600 mb-2')

            if saldo_actual > 0:
                ui.label(f'Saldo pendiente actual: {formatear_moneda(saldo_actual)}') \
                    .classes('deuda-aviso w-full mb-2')

            monto_abonado = ui.number(
                label='Monto que abona ahora', value=precio_plan, min=0, step=500, prefix='$'
            ).props('outlined').classes('w-full')

            sugerencia = str(tiempo.hoy() + timedelta(days=30))
            ui.label('Cuota paga hasta:').classes('text-sm text-gray-600 mt-2')
            calendario = ui.date(value=sugerencia).props('outlined')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def confirmar():
                    if not calendario.value:
                        ui.notify('Elegí una fecha en el calendario.', type='negative')
                        return
                    monto = monto_abonado.value or 0
                    if monto <= 0:
                        ui.notify('El monto abonado tiene que ser mayor a cero.', type='negative')
                        return

                    registrar_pago(dni, calendario.value, monto)
                    registrar_actividad('Pago registrado', f'{nombre} (DNI {dni}): {formatear_moneda(monto)}')
                    ui.notify('Pago registrado, vencimiento actualizado.', type='positive')
                    dialog.close()
                    al_registrar()

                ui.button('Confirmar pago', icon='payments', on_click=confirmar) \
                    .props('unelevated color=primary')

    dialog.open()


def abrir_dialogo_abonar_deuda(dni, nombre, al_registrar):
    """Diálogo para que un cliente complete un saldo pendiente, sin
    tocar su fecha de vencimiento."""
    cliente = buscar_cliente_por_dni(dni)
    saldo_actual = cliente['saldo_pendiente'] if cliente else 0

    with ui.dialog() as dialog:
        with ui.card().classes('w-[400px] max-w-[95vw] p-7'):
            ui.label('Abonar saldo pendiente').classes('text-xl font-bold')
            ui.label(f'Cliente: {nombre}').classes('text-gray-600 mb-2')

            if saldo_actual <= 0:
                ui.label('Este cliente no tiene saldo pendiente.').classes('text-sm text-gray-600')
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Cerrar', on_click=dialog.close).props('flat')
            else:
                ui.label(f'Debe: {formatear_moneda(saldo_actual)}').classes('deuda-aviso w-full mb-2')

                monto_abono = ui.number(
                    label='Monto que abona', value=saldo_actual, min=0, max=saldo_actual,
                    step=500, prefix='$'
                ).props('outlined').classes('w-full')

                with ui.row().classes('w-full justify-end gap-2 mt-5'):
                    ui.button('Cancelar', on_click=dialog.close).props('flat')

                    def confirmar():
                        monto = monto_abono.value or 0
                        if monto <= 0:
                            ui.notify('El monto tiene que ser mayor a cero.', type='negative')
                            return
                        abonar_deuda(dni, monto)
                        registrar_actividad('Abono de saldo', f'{nombre} (DNI {dni}): {formatear_moneda(monto)}')
                        ui.notify('Abono registrado.', type='positive')
                        dialog.close()
                        al_registrar()

                    ui.button('Registrar abono', icon='payments', on_click=confirmar) \
                        .props('unelevated color=primary')

    dialog.open()


def abrir_dialogo_rutina(dni, nombre, al_cambiar=None):
    """El profe o el dueño escriben (o borran) la rutina de un cliente
    puntual, con formato (negrita, títulos, viñetas), guardada como
    HTML en su ficha."""
    cliente = buscar_cliente_por_dni(dni)
    texto_actual = cliente['rutina'] if cliente else ''

    with ui.dialog() as dialog:
        with ui.card().classes('w-[560px] max-w-[95vw] p-7'):
            ui.label('Rutina de entrenamiento').classes('text-xl font-bold')
            ui.label(f'Cliente: {nombre}').classes('text-gray-600 mb-3')

            editor_rutina = ui.editor(value=texto_actual, placeholder='Escribí acá la rutina...') \
                .classes('w-full').style('min-height: 220px')

            with ui.row().classes('w-full justify-between gap-2 mt-4'):
                def borrar():
                    editor_rutina.value = ''

                ui.button('Vaciar', icon='delete', on_click=borrar).props('outline color=negative')

                with ui.row().classes('gap-2'):
                    ui.button('Cerrar', on_click=dialog.close).props('flat')

                    def guardar():
                        actualizar_rutina(dni, editor_rutina.value.strip())
                        registrar_actividad('Rutina actualizada', f'{nombre} (DNI {dni})')
                        ui.notify('Rutina guardada en el perfil del cliente.', type='positive')
                        dialog.close()
                        if al_cambiar:
                            al_cambiar()

                    ui.button('Guardar rutina', icon='save', on_click=guardar) \
                        .props('unelevated color=primary')

    dialog.open()


def abrir_dialogo_historial(dni, nombre):
    """Diálogo de solo lectura con todos los pagos registrados de un cliente, del más reciente al más viejo."""
    cliente = buscar_cliente_por_dni(dni)
    historial = list(reversed(cliente['historial'])) if cliente else []

    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Historial de pagos').classes('text-xl font-bold')
            ui.label(f'Cliente: {nombre}').classes('text-gray-600 mb-3')

            if not historial:
                ui.label('Todavía no hay pagos registrados.').classes('text-sm text-gray-600')
            else:
                columnas = [
                    {'name': 'fecha', 'label': 'Fecha de pago', 'field': 'fecha', 'align': 'left'},
                    {'name': 'monto', 'label': 'Monto abonado', 'field': 'monto', 'align': 'left'},
                    {'name': 'vencimiento', 'label': 'Dejó pago hasta', 'field': 'vencimiento', 'align': 'left'},
                    {'name': 'saldo', 'label': 'Saldo tras el pago', 'field': 'saldo', 'align': 'left'},
                ]
                filas = [{
                    'fecha': formatear_fecha(pago['fecha']),
                    'monto': formatear_moneda(pago.get('monto', 0)),
                    'vencimiento': formatear_fecha(pago['vencimiento']),
                    'saldo': formatear_moneda(pago.get('saldo_pendiente_tras_pago', 0)),
                } for indice, pago in enumerate(historial)]
                for indice, fila in enumerate(filas):
                    fila['indice'] = indice
                ui.table(columns=columnas, rows=filas, row_key='indice').classes('w-full')

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cerrar', on_click=dialog.close).props('flat')

    dialog.open()


def confirmar_eliminacion(dni, nombre, al_eliminar):
    """Diálogo de confirmación antes de eliminar un cliente."""
    with ui.dialog() as dialog:
        with ui.card().classes('p-7 w-[400px] max-w-[95vw]'):
            ui.label('Eliminar cliente').classes('text-xl font-bold')
            ui.label(f'¿Seguro que querés eliminar a {nombre}?').classes('text-gray-600 mt-3')
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def eliminar():
                    eliminar_cliente(dni)
                    registrar_actividad('Cliente eliminado', f'{nombre} (DNI {dni})')
                    dialog.close()
                    ui.notify('Cliente eliminado', type='positive')
                    al_eliminar()

                ui.button('Eliminar', icon='delete', on_click=eliminar).props('unelevated color=negative')

    dialog.open()


def confirmar_reset_password(dni, nombre):
    """Diálogo de confirmación para volver la contraseña de un cliente a su DNI."""
    with ui.dialog() as dialog:
        with ui.card().classes('p-7 w-[420px] max-w-[95vw]'):
            ui.label('Restablecer contraseña').classes('text-xl font-bold')
            ui.label(f'La contraseña de {nombre} va a volver a ser su DNI, y tendrá que '
                     f'cambiarla la próxima vez que entre. ¿Continuar?').classes('text-gray-600 mt-3')
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def restablecer():
                    restablecer_password_cliente(dni)
                    registrar_actividad('Contraseña de cliente restablecida', f'{nombre} (DNI {dni})')
                    dialog.close()
                    ui.notify('Contraseña restablecida: ahora es el DNI del cliente.', type='positive')

                ui.button('Restablecer', icon='lock_reset', on_click=restablecer) \
                    .props('unelevated color=primary')

    dialog.open()


@ui.page('/')
def pagina_principal():
    """Página de Clientes, para dueño y profe.

    Incluye las estadísticas del mes, los paneles de próximos
    cumpleaños y próximos vencimientos, el buscador, los filtros,
    la exportación a CSV y la tabla con todas las acciones sobre
    cada cliente."""
    if not requerir_autenticacion():
        return

    if es_cliente_rol():
        ui.navigate.to('/mi-cuenta')
        return

    ui.add_head_html(HEAD_COMUN)
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-6xl mx-auto p-8 gap-6'):

            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label('Clientes').classes('page-title')
                    ui.label('Gestioná los socios del gimnasio.').classes('page-subtitle')
                with ui.row().classes('gap-2'):
                    ui.button('Exportar CSV', icon='download', on_click=lambda: exportar_csv_click()) \
                        .props('outline color=primary')
                    ui.button('Nuevo cliente', icon='add',
                              on_click=lambda: abrir_formulario_cliente(refrescar)) \
                        .props('unelevated color=primary').classes('px-5')

            with ui.grid(columns=4).classes('w-full gap-4 grid-stats'):
                with ui.card().classes('stat-card'):
                    ui.label('Clientes activos').classes('stat-label')
                    etiqueta_activos = ui.label('0').classes('stat-value')
                with ui.card().classes('stat-card'):
                    ui.label('Cuotas vencidas').classes('stat-label')
                    etiqueta_vencidos = ui.label('0').classes('stat-value')
                with ui.card().classes('stat-card'):
                    ui.label('Ingresos esperados (mes)').classes('stat-label')
                    etiqueta_ingresos_esperados = ui.label('$0').classes('stat-value')
                with ui.card().classes('stat-card'):
                    ui.label('Cobrado este mes').classes('stat-label')
                    etiqueta_ingresos_cobrados = ui.label('$0').classes('stat-value')

            with ui.grid(columns=2).classes('w-full gap-4 grid-paneles'):
                # Panel de cumpleaños: siempre visible.
                with ui.column().classes('glass-card w-full p-5'):
                    ui.label('🎂 Próximos cumpleaños (30 días)').classes('text-lg font-bold mb-2')
                    contenedor_cumples = ui.column().classes('w-full')

                # Panel de próximos vencimientos: siempre visible.
                with ui.column().classes('glass-card w-full p-5'):
                    ui.label('⏰ Próximos a vencer (7 días)').classes('text-lg font-bold mb-2')
                    contenedor_vencimientos = ui.column().classes('w-full')

            # Anuncios del dueño: visibles también para el personal.
            anuncios_actuales = cargar_anuncios()
            if anuncios_actuales:
                with ui.column().classes('glass-card w-full p-5'):
                    ui.label('📢 Anuncios').classes('text-lg font-bold mb-2')
                    for anuncio in anuncios_actuales[:5]:
                        with ui.column().classes('anuncio-item w-full'):
                            ui.label(formatear_fecha(anuncio['fecha'])).classes('anuncio-fecha')
                            ui.label(anuncio['texto'])

            with ui.column().classes('table-container w-full p-4 gap-3'):
                with ui.row().classes('items-center gap-3'):
                    busqueda_input = ui.input(placeholder='Buscar por nombre o DNI...') \
                        .props('outlined dense clearable').classes('w-64')
                    checkbox_vencidos = ui.checkbox('Solo vencidos')
                    select_plan = ui.select(
                        ['Todos', '2 veces por semana', '3 veces por semana', 'Todos los días'],
                        value='Todos', label='Filtrar por plan'
                    ).props('outlined dense').classes('w-64')
                    ui.space()
                    ui.button(icon='refresh', on_click=lambda: refrescar()).props('flat round')

                columnas = [
                    {'name': 'dni', 'label': 'DNI', 'field': 'dni', 'align': 'left'},
                    {'name': 'nombre', 'label': 'Nombre y Apellido', 'field': 'nombre', 'align': 'left'},
                    {'name': 'telefono', 'label': 'Teléfono', 'field': 'telefono', 'align': 'left'},
                    {'name': 'plan', 'label': 'Plan', 'field': 'plan', 'align': 'left'},
                    {'name': 'nacimiento', 'label': 'Cumpleaños', 'field': 'nacimiento', 'align': 'left'},
                    {'name': 'vencimiento', 'label': 'Vencimiento', 'field': 'vencimiento', 'align': 'left'},
                    {'name': 'activo', 'label': 'Activo', 'field': 'activo', 'align': 'left'},
                    {'name': 'debe', 'label': 'Debe', 'field': 'debe', 'align': 'left'},
                ]
                columnas.append({'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'right'})

                tabla = ui.table(columns=columnas, rows=[], row_key='dni').classes('w-full')

                boton_eliminar_html = '''
                        <q-btn flat round dense icon="delete" color="negative"
                               @click="$parent.$emit('eliminar', props.row)">
                            <q-tooltip>Eliminar</q-tooltip>
                        </q-btn>
                ''' if es_dueño() else ''

                tabla.add_slot('body-cell-acciones', f'''
                    <q-td :props="props">
                        <q-btn flat round dense icon="edit" color="primary"
                               @click="$parent.$emit('editar', props.row)">
                            <q-tooltip>Editar</q-tooltip>
                        </q-btn>
                        <q-btn flat round dense icon="payments" color="primary"
                               @click="$parent.$emit('pagar', props.row)">
                            <q-tooltip>Registrar pago</q-tooltip>
                        </q-btn>
                        <q-btn flat round dense icon="account_balance_wallet" color="primary"
                               @click="$parent.$emit('abonar', props.row)">
                            <q-tooltip>Abonar saldo pendiente</q-tooltip>
                        </q-btn>
                        <q-btn flat round dense icon="history" color="primary"
                               @click="$parent.$emit('historial', props.row)">
                            <q-tooltip>Historial de pagos</q-tooltip>
                        </q-btn>
                        <q-btn flat round dense icon="edit_note" color="primary"
                               @click="$parent.$emit('rutina', props.row)">
                            <q-tooltip>Rutina (texto)</q-tooltip>
                        </q-btn>
                        <q-btn flat round dense icon="lock_reset" color="primary"
                               @click="$parent.$emit('resetear', props.row)">
                            <q-tooltip>Restablecer contraseña</q-tooltip>
                        </q-btn>
                        {boton_eliminar_html}
                    </q-td>
                ''')

                def on_editar(e):
                    abrir_formulario_editar_cliente(e.args['dni'], refrescar)

                def on_pagar(e):
                    abrir_dialogo_pago(e.args['dni'], e.args['nombre'], refrescar)

                def on_abonar(e):
                    abrir_dialogo_abonar_deuda(e.args['dni'], e.args['nombre'], refrescar)

                def on_historial(e):
                    abrir_dialogo_historial(e.args['dni'], e.args['nombre'])

                def on_rutina(e):
                    abrir_dialogo_rutina(e.args['dni'], e.args['nombre'], al_cambiar=refrescar)

                def on_eliminar(e):
                    if not es_dueño():
                        ui.notify('No tenés permisos para eliminar clientes.', type='negative')
                        return
                    confirmar_eliminacion(e.args['dni'], e.args['nombre'], refrescar)

                tabla.on('editar', on_editar)
                tabla.on('pagar', on_pagar)
                tabla.on('abonar', on_abonar)
                tabla.on('historial', on_historial)
                tabla.on('rutina', on_rutina)

                def on_resetear(e):
                    confirmar_reset_password(e.args['dni'], e.args['nombre'])

                tabla.on('resetear', on_resetear)
                tabla.on('eliminar', on_eliminar)

            def exportar_csv_click():
                contenido = exportar_clientes_csv(
                    solo_vencidos=checkbox_vencidos.value,
                    plan_filtro=select_plan.value,
                    busqueda=busqueda_input.value or "",
                )
                ui.download(contenido.encode('utf-8-sig'), 'clientes.csv')

            def refrescar():
                tabla.rows = obtener_filas(
                    solo_vencidos=checkbox_vencidos.value,
                    plan_filtro=select_plan.value,
                    busqueda=busqueda_input.value or "",
                )
                activos, vencidos = contadores()
                etiqueta_activos.set_text(str(activos))
                etiqueta_vencidos.set_text(str(vencidos))
                etiqueta_ingresos_esperados.set_text(formatear_moneda(ingresos_esperados_mensuales()))
                etiqueta_ingresos_cobrados.set_text(formatear_moneda(ingresos_cobrados_mes_actual()))

                contenedor_cumples.clear()
                with contenedor_cumples:
                    cumples = proximos_cumpleanos(30)
                    if not cumples:
                        ui.label('No hay cumpleaños en los próximos 30 días.').classes('text-gray-500')
                    else:
                        for c in cumples:
                            clase = 'cumple-hoy' if c['es_hoy'] else 'cumple-fila'
                            with ui.row().classes(f'{clase} w-full items-center justify-between'):
                                ui.label(f"{c['nombre']} ({c['dni']})")
                                if c['es_hoy']:
                                    ui.label('🎉 ¡Hoy!')
                                else:
                                    ui.label(f"{c['fecha']} · en {c['dias_faltantes']} días")

                contenedor_vencimientos.clear()
                with contenedor_vencimientos:
                    vencimientos = proximos_vencimientos(7)
                    if not vencimientos:
                        ui.label('No hay cuotas por vencer en los próximos 7 días.').classes('text-gray-500')
                    else:
                        for v in vencimientos:
                            clase = 'cumple-hoy' if v['vence_hoy'] else 'cumple-fila'
                            with ui.row().classes(f'{clase} w-full items-center justify-between'):
                                ui.label(f"{v['nombre']} ({v['dni']})")
                                if v['vence_hoy']:
                                    ui.label('⚠️ ¡Vence hoy!')
                                else:
                                    ui.label(f"{v['fecha']} · en {v['dias']} días")

            busqueda_input.on_value_change(refrescar)
            checkbox_vencidos.on_value_change(refrescar)
            select_plan.on_value_change(refrescar)

            refrescar()

        construir_footer()
