"""Página de contabilidad (solo dueño): resumen mensual y carga de ingresos y gastos."""

from nicegui import ui

from ..datos.contabilidad import eliminar_movimiento, registrar_movimiento, resumen_mensual, ultimos_movimientos
from ..tiempo import formatear_fecha, formatear_moneda
from .estilos import HEAD_COMUN
from .navbar import construir_footer, construir_navbar
from .sesion import es_dueño, registrar_actividad, requerir_autenticacion


@ui.page('/contabilidad')
def pagina_contabilidad():
    """Página de contabilidad (solo dueño).

    Muestra el resumen mes a mes de ingresos, egresos y neto, y
    permite cargar a mano otros ingresos (bebidas, etc.) y gastos.
    Los cobros de cuotas aparecen solos, registrados automáticamente
    al cargar un pago desde la página de Clientes."""
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

            ui.label('Contabilidad').classes('page-title')
            ui.label('Ingresos y gastos del gimnasio, mes a mes. Las cuotas se '
                      'registran solas cuando cargás un pago; acá podés sumar '
                      'otros ingresos (bebidas, etc.) o restar gastos.') \
                .classes('page-subtitle')

            # --- Formulario de carga manual ---
            with ui.column().classes('glass-card w-full p-6 gap-3'):
                ui.label('Registrar movimiento').classes('text-lg font-bold')

                with ui.row().classes('w-full items-center gap-3'):
                    tipo_select = ui.select(
                        {'ingreso': 'Ingreso (suma)', 'egreso': 'Gasto (resta)'},
                        value='ingreso', label='Tipo'
                    ).props('outlined dense').classes('w-48')
                    categoria_input = ui.input('Categoría (ej: Bebidas, Luz, Limpieza)') \
                        .props('outlined dense').classes('w-72')
                    monto_input = ui.number(label='Monto', min=0, step=500, prefix='$') \
                        .props('outlined dense').classes('w-40')

                descripcion_input = ui.input('Descripción (opcional)') \
                    .props('outlined dense').classes('w-full')

                def registrar():
                    monto = monto_input.value or 0
                    categoria = categoria_input.value.strip()
                    if monto <= 0:
                        ui.notify('El monto tiene que ser mayor a cero.', type='negative')
                        return
                    if not categoria:
                        ui.notify('Poné una categoría (ej: Bebidas, Luz...).', type='negative')
                        return

                    registrar_movimiento(
                        tipo_select.value, categoria,
                        descripcion_input.value.strip() or categoria, monto,
                    )
                    registrar_actividad('Movimiento contable registrado',
                                        f'{tipo_select.value}: {categoria} {formatear_moneda(monto)}')
                    categoria_input.value = ''
                    descripcion_input.value = ''
                    monto_input.value = None
                    ui.notify('Movimiento registrado.', type='positive')
                    refrescar()

                ui.button('Registrar', icon='add', on_click=registrar) \
                    .props('unelevated color=primary').classes('self-start')

            # --- Resumen mes a mes ---
            ui.label('Resumen mensual').classes('text-lg font-bold mt-2')
            with ui.column().classes('table-container w-full p-4'):
                columnas_resumen = [
                    {'name': 'mes', 'label': 'Mes', 'field': 'mes', 'align': 'left'},
                    {'name': 'ingresos', 'label': 'Ingresos', 'field': 'ingresos', 'align': 'left'},
                    {'name': 'egresos', 'label': 'Gastos', 'field': 'egresos', 'align': 'left'},
                    {'name': 'neto', 'label': 'Neto', 'field': 'neto', 'align': 'left'},
                ]
                tabla_resumen = ui.table(columns=columnas_resumen, rows=[], row_key='mes') \
                    .classes('w-full')

            # --- Últimos movimientos ---
            ui.label('Últimos movimientos').classes('text-lg font-bold mt-2')
            with ui.column().classes('table-container w-full p-4'):
                columnas_mov = [
                    {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left'},
                    {'name': 'tipo', 'label': 'Tipo', 'field': 'tipo', 'align': 'left'},
                    {'name': 'categoria', 'label': 'Categoría', 'field': 'categoria', 'align': 'left'},
                    {'name': 'descripcion', 'label': 'Descripción', 'field': 'descripcion', 'align': 'left'},
                    {'name': 'monto', 'label': 'Monto', 'field': 'monto', 'align': 'left'},
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'right'},
                ]
                tabla_mov = ui.table(columns=columnas_mov, rows=[], row_key='id').classes('w-full')

                tabla_mov.add_slot('body-cell-acciones', '''
                    <q-td :props="props">
                        <q-btn flat round dense icon="delete" color="negative"
                               @click="$parent.$emit('eliminar', props.row)">
                            <q-tooltip>Eliminar movimiento</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')

                def on_eliminar_movimiento(e):
                    eliminar_movimiento(e.args['id'])
                    registrar_actividad('Movimiento contable eliminado', f"id {e.args['id']}")
                    ui.notify('Movimiento eliminado.', type='positive')
                    refrescar()

                tabla_mov.on('eliminar', on_eliminar_movimiento)

            def refrescar():
                tabla_resumen.rows = [{
                    'mes': fila['mes'],
                    'ingresos': formatear_moneda(fila['ingresos']),
                    'egresos': formatear_moneda(fila['egresos']),
                    'neto': formatear_moneda(fila['neto']),
                } for fila in resumen_mensual()]

                movimientos = ultimos_movimientos(50)
                tabla_mov.rows = [{
                    'id': m['id'],
                    'fecha': formatear_fecha(m['fecha']),
                    'tipo': 'Ingreso' if m['tipo'] == 'ingreso' else 'Gasto',
                    'categoria': m['categoria'],
                    'descripcion': m['descripcion'],
                    'monto': formatear_moneda(m['monto']),
                } for m in movimientos]

            refrescar()

        construir_footer()
