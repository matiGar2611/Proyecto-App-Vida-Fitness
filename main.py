from nicegui import app, ui
import sqlite3
import hashlib
import secrets
import json
import os
from datetime import date, timedelta, datetime


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_USUARIOS = 'usuarios.db'
ARCHIVO_CLIENTES = 'Clientes.json'

ROLES = ['dueño', 'profe', 'cliente']


# ============================================================
# BASE DE DATOS DE USUARIOS (login + roles)
# ============================================================

def conectar_db():
    return sqlite3.connect(DB_USUARIOS)


def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL,
            dni_asociado TEXT
        )
    """)
    conn.commit()

    # Migración: si usuarios.db ya existía de una versión anterior sin
    # columnas de rol, se las agregamos ahora (CREATE TABLE IF NOT EXISTS
    # no modifica una tabla que ya existe).
    cursor.execute("PRAGMA table_info(usuarios)")
    columnas_existentes = {fila[1] for fila in cursor.fetchall()}
    if "rol" not in columnas_existentes:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'dueño'")
    if "dni_asociado" not in columnas_existentes:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN dni_asociado TEXT")
    conn.commit()
    conn.close()
    crear_usuario_dueño()


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hash_val = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return salt, hash_val


def verificar_password(password, salt, hash_val):
    _, nuevo_hash = hash_password(password, salt)
    return nuevo_hash == hash_val


def crear_usuario_dueño():
    """El primer usuario que existe siempre es el dueño, con permisos totales."""
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        salt, hash_val = hash_password('admin123')
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, salt, nombre, rol, dni_asociado) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ('admin', hash_val, salt, 'Dueño del gimnasio', 'dueño', None)
        )
        conn.commit()
    conn.close()


def obtener_usuario(username):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, salt, nombre, rol, dni_asociado "
        "FROM usuarios WHERE username = ?",
        (username,)
    )
    usuario = cursor.fetchone()
    conn.close()
    return usuario


def obtener_todos_usuarios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, rol, dni_asociado FROM usuarios ORDER BY rol, nombre")
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios


def crear_usuario(username, password, nombre, rol, dni_asociado=None):
    conn = conectar_db()
    cursor = conn.cursor()
    salt, hash_val = hash_password(password)
    cursor.execute(
        "INSERT INTO usuarios (username, password_hash, salt, nombre, rol, dni_asociado) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, hash_val, salt, nombre, rol, dni_asociado)
    )
    conn.commit()
    conn.close()


def eliminar_usuario(user_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# ---- Sesión y permisos ----

def verificar_autenticacion():
    return 'username' in app.storage.user


def rol_actual():
    return app.storage.user.get('rol')


def es_dueño():
    return rol_actual() == 'dueño'


def es_profe():
    return rol_actual() == 'profe'


def es_cliente_rol():
    return rol_actual() == 'cliente'


def requerir_autenticacion():
    if not verificar_autenticacion():
        ui.navigate.to('/login')
        return False
    return True


def cerrar_sesion():
    app.storage.user.clear()
    ui.notify('Sesión cerrada', type='info')
    ui.navigate.to('/login')


# ============================================================
# DATOS DE CLIENTES (JSON)
# ============================================================

def cargar_clientes():
    if os.path.exists(ARCHIVO_CLIENTES):
        with open(ARCHIVO_CLIENTES, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    return []


def guardar_clientes(lista_clientes):
    with open(ARCHIVO_CLIENTES, "w", encoding="utf-8") as archivo:
        json.dump(lista_clientes, archivo, ensure_ascii=False, indent=4)


def dni_existe(lista_clientes, dni):
    return any(cliente["DNI"] == dni for cliente in lista_clientes)


def buscar_cliente_por_dni(dni):
    for cliente in cargar_clientes():
        if cliente["DNI"] == dni:
            return cliente
    return None


def crear_cliente(dni, nombre_y_apellido, telefono, plan, fecha_nacimiento):
    hoy = date.today()
    return {
        "DNI": dni,
        "Nombre y  Apellido": nombre_y_apellido,
        "Telefono": telefono,
        "Plan": plan,
        "Fecha de nacimiento": fecha_nacimiento,
        "Fecha de inicio": str(hoy),
        "Fecha de vencimiento": str(hoy + timedelta(days=30)),
        "Fecha ultimo pago": str(hoy),
        "Cliente Activo": True,
    }


def registrar_pago(dni, nueva_fecha_vencimiento):
    """A diferencia de antes, la fecha de vencimiento ya no se calcula
    sola (+30 días) -- se elige a mano en el calendario del diálogo de pago."""
    lista_clientes = cargar_clientes()
    for cliente in lista_clientes:
        if cliente["DNI"] == dni:
            cliente["Fecha ultimo pago"] = str(date.today())
            cliente["Fecha de vencimiento"] = nueva_fecha_vencimiento
            cliente["Cliente Activo"] = True
            guardar_clientes(lista_clientes)
            return True
    return False


def eliminar_cliente(dni):
    lista_clientes = cargar_clientes()
    for cliente in lista_clientes:
        if cliente["DNI"] == dni:
            lista_clientes.remove(cliente)
            guardar_clientes(lista_clientes)
            return True
    return False


def dar_baja_automatica():
    lista_clientes = cargar_clientes()
    cambios = False
    for cliente in lista_clientes:
        fecha_ultimo_pago = datetime.strptime(cliente["Fecha ultimo pago"], "%Y-%m-%d").date()
        if (date.today() - fecha_ultimo_pago).days > 90 and cliente["Cliente Activo"]:
            cliente["Cliente Activo"] = False
            cambios = True
    if cambios:
        guardar_clientes(lista_clientes)


def formatear_fecha(fecha_texto):
    return datetime.strptime(fecha_texto, "%Y-%m-%d").date().strftime("%d/%m/%Y")


def esta_vencido(cliente):
    fecha_vencimiento = datetime.strptime(cliente["Fecha de vencimiento"], "%Y-%m-%d").date()
    return fecha_vencimiento < date.today()


def obtener_filas(solo_vencidos=False, plan_filtro="Todos"):
    filas = []
    for cliente in cargar_clientes():
        if solo_vencidos and not esta_vencido(cliente):
            continue
        if plan_filtro != "Todos" and cliente["Plan"] != plan_filtro:
            continue
        filas.append({
            "dni": cliente["DNI"],
            "nombre": cliente["Nombre y  Apellido"],
            "telefono": cliente["Telefono"],
            "plan": cliente["Plan"],
            "nacimiento": formatear_fecha(cliente["Fecha de nacimiento"])
                          if cliente.get("Fecha de nacimiento") else "-",
            "vencimiento": formatear_fecha(cliente["Fecha de vencimiento"]),
            "activo": "Sí" if cliente["Cliente Activo"] else "No",
        })
    return filas


# ============================================================
# ESTILOS GLASSMORPHISM -- gama de verdes
# ============================================================

CSS = """
:root {
    --glass-bg: rgba(255, 255, 255, 0.62);
    --glass-border: rgba(255, 255, 255, 0.75);
    --primary: #16a34a;
    --secondary: #22c55e;
    --text-primary: #10241a;
    --shadow: 0 20px 50px rgba(21, 128, 61, 0.12);
}

html, body { min-height: 100%; margin: 0; }

body {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    color: var(--text-primary);
    background:
        radial-gradient(circle at 10% 10%, rgba(34, 197, 94, 0.22), transparent 28%),
        radial-gradient(circle at 90% 15%, rgba(16, 185, 129, 0.20), transparent 25%),
        radial-gradient(circle at 50% 100%, rgba(74, 222, 128, 0.16), transparent 35%),
        linear-gradient(135deg, #ecfdf5 0%, #f7fefb 45%, #ecfdf5 100%);
    background-attachment: fixed;
}

.app-header {
    height: 70px;
    background: rgba(255, 255, 255, 0.58);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.7);
    box-shadow: 0 10px 30px rgba(21, 128, 61, 0.06);
}

.logo-container { display: flex; align-items: center; gap: 11px; }

.logo-icon {
    width: 40px; height: 40px; border-radius: 13px;
    background: linear-gradient(135deg, #16a34a, #4ade80);
    display: flex; align-items: center; justify-content: center;
    color: white; box-shadow: 0 10px 25px rgba(22, 163, 74, 0.28);
    flex-shrink: 0;
}

.logo-text { font-size: 19px; font-weight: 800; color: #10241a; letter-spacing: -0.5px; }
.logo-text span {
    background: linear-gradient(90deg, #16a34a, #4ade80);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.nav-button { color: #4b5c53 !important; font-weight: 650; border-radius: 12px; transition: all .2s ease; }
.nav-button:hover { color: #16a34a !important; background: rgba(22, 163, 74, 0.08); transform: translateY(-1px); }

.page-title { font-size: 32px; font-weight: 850; letter-spacing: -1px; color: #10241a; }
.page-subtitle { color: #5c6b62; font-size: 14px; line-height: 1.6; }

.glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid var(--glass-border); border-radius: 22px;
    box-shadow: var(--shadow);
}

.stat-card {
    position: relative; overflow: hidden;
    background: rgba(255, 255, 255, 0.58);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255, 255, 255, 0.78); border-radius: 20px;
    padding: 21px; box-shadow: 0 15px 40px rgba(21, 128, 61, 0.08);
    transition: all .25s ease;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 20px 45px rgba(21, 128, 61, 0.16); }
.stat-label { color: #5c6b62; font-size: 13px; font-weight: 600; }
.stat-value { font-size: 31px; font-weight: 850; color: #10241a; margin-top: 5px; }

.table-container {
    background: rgba(255, 255, 255, 0.60);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255, 255, 255, 0.78); border-radius: 22px;
    overflow: hidden; box-shadow: 0 20px 50px rgba(21, 128, 61, 0.09);
}

.q-field--outlined .q-field__control { border-radius: 13px; background: rgba(255, 255, 255, 0.50); }
.q-btn { border-radius: 12px; font-weight: 650; text-transform: none; }
.q-btn.bg-primary {
    background: linear-gradient(135deg, #16a34a, #4ade80) !important;
    box-shadow: 0 8px 20px rgba(22, 163, 74, 0.28);
}

.q-table { background: transparent !important; color: #26332c; }
.q-table thead tr { background: rgba(22, 163, 74, 0.05); }
.q-table thead th { color: #5c6b62; font-size: 11px; font-weight: 800; letter-spacing: .7px; }
.q-table tbody tr:hover { background: rgba(22, 163, 74, 0.06); }

.q-dialog__inner > .q-card {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.9); border-radius: 24px;
    box-shadow: 0 30px 80px rgba(21, 128, 61, 0.20);
}

.app-footer {
    width: 100%; padding: 24px 32px;
    border-top: 1px solid rgba(255, 255, 255, 0.7);
    background: rgba(255, 255, 255, 0.40);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
}
.footer-text { font-size: 12px; color: #6d7c74; }

.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
.login-card {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.82); border-radius: 28px;
    box-shadow: 0 30px 80px rgba(21, 128, 61, 0.15);
    padding: 40px; width: 420px; max-width: 95vw;
}
.login-title { font-size: 26px; font-weight: 850; color: #10241a; text-align: center; letter-spacing: -.5px; }
.login-subtitle { color: #5c6b62; font-size: 14px; text-align: center; line-height: 1.6; }
.login-hint {
    background: rgba(22, 163, 74, 0.07); border: 1px solid rgba(22, 163, 74, 0.14);
    border-radius: 14px; padding: 12px 16px; margin-top: 16px;
}
.login-hint-label { color: #16a34a; font-size: 11px; font-weight: 750; text-transform: uppercase; }
.login-hint-text { color: #5c6b62; font-size: 13px; margin-top: 2px; }
.login-error {
    background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.18);
    border-radius: 12px; padding: 10px 14px; color: #dc2626; font-size: 13px; font-weight: 600;
}

.user-avatar {
    width: 36px; height: 36px; min-width: 36px; border-radius: 12px;
    background: linear-gradient(135deg, #16a34a, #4ade80); color: white;
    display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px;
}
.user-info-name { font-size: 13px; font-weight: 700; color: #1c2e24; }
.user-info-role { font-size: 11px; color: #5c6b62; font-weight: 600; text-transform: uppercase; }

.mi-cuenta-card {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
    border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 24px;
    box-shadow: 0 25px 60px rgba(21, 128, 61, 0.14);
    padding: 32px; width: 480px; max-width: 95vw;
}
.dato-fila { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.06); }
.dato-label { color: #5c6b62; font-weight: 600; }
.dato-valor { color: #10241a; font-weight: 700; }
"""


# ============================================================
# NAVBAR / FOOTER
# ============================================================

def construir_navbar():
    with ui.header().classes('app-header px-6'):
        with ui.row().classes('w-full items-center'):
            with ui.row().classes('logo-container'):
                with ui.element('div').classes('logo-icon'):
                    ui.icon('fitness_center')
                with ui.element('div').classes('logo-text'):
                    ui.html('Vida<span>Fitness</span>')

            ui.space()

            if es_dueño() or es_profe():
                ui.button('Clientes', icon='groups', on_click=lambda: ui.navigate.to('/')) \
                    .props('flat').classes('nav-button')

            if es_dueño():
                ui.button('Usuarios', icon='manage_accounts', on_click=lambda: ui.navigate.to('/usuarios')) \
                    .props('flat').classes('nav-button')

            if es_cliente_rol():
                ui.button('Mi cuenta', icon='person', on_click=lambda: ui.navigate.to('/mi-cuenta')) \
                    .props('flat').classes('nav-button')

            ui.separator().props('vertical').classes('mx-2').style('height: 28px;')

            with ui.row().classes('items-center gap-2'):
                with ui.element('div').classes('user-avatar'):
                    ui.label(app.storage.user.get('nombre', '?')[0].upper())
                with ui.column().classes('gap-0'):
                    ui.label(app.storage.user.get('nombre', '')).classes('user-info-name')
                    ui.label(rol_actual() or '').classes('user-info-role')

            ui.button(icon='logout', on_click=cerrar_sesion).props('flat round').classes('nav-button')


def construir_footer():
    with ui.element('footer').classes('app-footer'):
        with ui.row().classes('items-center justify-center'):
            ui.label('Gimnasio Vida Fitness · gestor interno').classes('footer-text')


# ============================================================
# PÁGINA: LOGIN
# ============================================================

@ui.page('/login')
def pagina_login():
    if verificar_autenticacion():
        ui.navigate.to('/mi-cuenta' if es_cliente_rol() else '/')
        return

    ui.add_head_html(f'<style>{CSS}</style>')

    with ui.element('div').classes('login-page w-full'):
        with ui.element('div').classes('login-card'):
            with ui.column().classes('items-center gap-4 mb-6 w-full'):
                with ui.element('div').classes('logo-icon'):
                    ui.icon('fitness_center').classes('text-3xl')
                ui.label('Gimnasio Vida Fitness').classes('login-title')
                ui.label('Ingresá tu usuario y contraseña.').classes('login-subtitle')

            error_container = ui.column().classes('w-full')

            username_input = ui.input('Usuario').props('outlined').classes('w-full')
            password_input = ui.input(
                'Contraseña', password=True, password_toggle_button=True
            ).props('outlined').classes('w-full')

            def intentar_login():
                error_container.clear()
                usuario = username_input.value.strip()
                clave = password_input.value

                if not usuario or not clave:
                    with error_container:
                        ui.label('Completá usuario y contraseña').classes('login-error w-full')
                    return

                registro = obtener_usuario(usuario)
                if registro is None:
                    with error_container:
                        ui.label('Usuario no encontrado').classes('login-error w-full')
                    return

                if not verificar_password(clave, registro[3], registro[2]):
                    with error_container:
                        ui.label('Contraseña incorrecta').classes('login-error w-full')
                    return

                app.storage.user['id'] = registro[0]
                app.storage.user['username'] = registro[1]
                app.storage.user['nombre'] = registro[4]
                app.storage.user['rol'] = registro[5]
                app.storage.user['dni_asociado'] = registro[6]

                ui.notify(f'Bienvenido, {registro[4]}', type='positive')
                ui.navigate.to('/mi-cuenta' if registro[5] == 'cliente' else '/')

            ui.button('Ingresar', icon='login', on_click=intentar_login) \
                .props('unelevated color=primary').classes('w-full mt-2')

            username_input.on('keydown.enter', lambda e: intentar_login())
            password_input.on('keydown.enter', lambda e: intentar_login())

            with ui.element('div').classes('login-hint'):
                ui.label('Cuenta por defecto (dueño)').classes('login-hint-label')
                ui.label('Usuario: admin · Contraseña: admin123').classes('login-hint-text')


# ============================================================
# DIÁLOGOS: cliente
# ============================================================

def abrir_formulario_cliente(al_guardar):
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

            ui.label('Fecha de nacimiento').classes('text-sm text-gray-600 mt-2')
            nacimiento = ui.date().props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    if len(dni.value.strip()) != 8:
                        ui.notify('El DNI debe tener 8 caracteres.', type='negative')
                        return
                    if len(telefono.value.strip()) != 10:
                        ui.notify('El teléfono debe tener 10 caracteres.', type='negative')
                        return
                    if not nacimiento.value:
                        ui.notify('Elegí la fecha de nacimiento.', type='negative')
                        return
                    if dni_existe(cargar_clientes(), dni.value.strip()):
                        ui.notify('Este DNI ya está registrado.', type='negative')
                        return

                    lista_clientes = cargar_clientes()
                    lista_clientes.append(
                        crear_cliente(dni.value.strip(), nombre.value.strip(),
                                      telefono.value.strip(), plan.value, nacimiento.value)
                    )
                    guardar_clientes(lista_clientes)
                    ui.notify('Cliente agregado correctamente.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Guardar', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


def abrir_dialogo_pago(dni, nombre, al_registrar):
    """Al registrar un pago, se elige con un calendario hasta cuándo
    queda pagada la cuota (en vez de calcularlo solo con +30 días)."""
    with ui.dialog() as dialog:
        with ui.card().classes('w-[400px] max-w-[95vw] p-7'):
            ui.label('Registrar pago').classes('text-xl font-bold')
            ui.label(f'Cliente: {nombre}').classes('text-gray-600 mb-3')

            sugerencia = str(date.today() + timedelta(days=30))
            ui.label('Cuota paga hasta:').classes('text-sm text-gray-600')
            calendario = ui.date(value=sugerencia).props('outlined')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def confirmar():
                    if not calendario.value:
                        ui.notify('Elegí una fecha en el calendario.', type='negative')
                        return
                    registrar_pago(dni, calendario.value)
                    ui.notify('Pago registrado, vencimiento actualizado.', type='positive')
                    dialog.close()
                    al_registrar()

                ui.button('Confirmar pago', icon='payments', on_click=confirmar) \
                    .props('unelevated color=primary')

    dialog.open()


def confirmar_eliminacion(dni, nombre, al_eliminar):
    with ui.dialog() as dialog:
        with ui.card().classes('p-7 w-[400px] max-w-[95vw]'):
            ui.label('Eliminar cliente').classes('text-xl font-bold')
            ui.label(f'¿Seguro que querés eliminar a {nombre}?').classes('text-gray-600 mt-3')
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def eliminar():
                    eliminar_cliente(dni)
                    dialog.close()
                    ui.notify('Cliente eliminado', type='positive')
                    al_eliminar()

                ui.button('Eliminar', icon='delete', on_click=eliminar).props('unelevated color=negative')

    dialog.open()


# ============================================================
# PÁGINA PRINCIPAL (dueño y profe)
# ============================================================

@ui.page('/')
def pagina_principal():
    if not requerir_autenticacion():
        return

    if es_cliente_rol():
        ui.navigate.to('/mi-cuenta')
        return

    dar_baja_automatica()
    ui.add_head_html(f'<style>{CSS}</style>')
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-6xl mx-auto p-8 gap-6'):

            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label('Clientes').classes('page-title')
                    ui.label('Gestioná los socios del gimnasio.').classes('page-subtitle')
                ui.button('Nuevo cliente', icon='add',
                          on_click=lambda: abrir_formulario_cliente(refrescar)) \
                    .props('unelevated color=primary').classes('px-5')

            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.card().classes('stat-card'):
                    ui.label('Clientes activos').classes('stat-label')
                    etiqueta_activos = ui.label('0').classes('stat-value')
                with ui.card().classes('stat-card'):
                    ui.label('Cuotas vencidas').classes('stat-label')
                    etiqueta_vencidos = ui.label('0').classes('stat-value')

            with ui.column().classes('table-container w-full p-4 gap-3'):
                with ui.row().classes('items-center gap-3'):
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
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'right'},
                ]

                tabla = ui.table(columns=columnas, rows=[], row_key='dni').classes('w-full')

                # El botón de eliminar solo se dibuja para el dueño.
                boton_eliminar_html = '''
                        <q-btn flat round dense icon="delete" color="negative"
                               @click="$parent.$emit('eliminar', props.row)">
                            <q-tooltip>Eliminar</q-tooltip>
                        </q-btn>
                ''' if es_dueño() else ''

                tabla.add_slot('body-cell-acciones', f'''
                    <q-td :props="props">
                        <q-btn flat round dense icon="payments" color="primary"
                               @click="$parent.$emit('pagar', props.row)">
                            <q-tooltip>Registrar pago</q-tooltip>
                        </q-btn>
                        {boton_eliminar_html}
                    </q-td>
                ''')

                def on_pagar(e):
                    abrir_dialogo_pago(e.args['dni'], e.args['nombre'], refrescar)

                def on_eliminar(e):
                    if not es_dueño():
                        ui.notify('No tenés permisos para eliminar clientes.', type='negative')
                        return
                    confirmar_eliminacion(e.args['dni'], e.args['nombre'], refrescar)

                tabla.on('pagar', on_pagar)
                tabla.on('eliminar', on_eliminar)

            def refrescar():
                tabla.rows = obtener_filas(
                    solo_vencidos=checkbox_vencidos.value,
                    plan_filtro=select_plan.value,
                )
                lista_clientes = cargar_clientes()
                etiqueta_activos.set_text(str(sum(1 for c in lista_clientes if c["Cliente Activo"])))
                etiqueta_vencidos.set_text(str(sum(1 for c in lista_clientes if esta_vencido(c))))

            checkbox_vencidos.on_value_change(refrescar)
            select_plan.on_value_change(refrescar)

            refrescar()

        construir_footer()


# ============================================================
# PÁGINA: MI CUENTA (solo rol cliente)
# ============================================================

@ui.page('/mi-cuenta')
def pagina_mi_cuenta():
    if not requerir_autenticacion():
        return

    if not es_cliente_rol():
        ui.navigate.to('/')
        return

    ui.add_head_html(f'<style>{CSS}</style>')
    construir_navbar()

    dni_asociado = app.storage.user.get('dni_asociado')
    cliente = buscar_cliente_por_dni(dni_asociado) if dni_asociado else None

    with ui.column().classes('w-full min-h-screen items-center justify-center'):
        with ui.element('div').classes('mi-cuenta-card'):
            ui.label('Mi situación en el gimnasio').classes('page-title')
            ui.label('Datos de tu plan y tu cuota.').classes('page-subtitle mb-4')

            if cliente is None:
                ui.label('Tu usuario todavía no está vinculado a una ficha de socio. '
                         'Consultá con recepción.').classes('login-error w-full mt-4')
            else:
                datos = [
                    ('Nombre y Apellido', cliente['Nombre y  Apellido']),
                    ('DNI', cliente['DNI']),
                    ('Teléfono', cliente['Telefono']),
                    ('Plan', cliente['Plan']),
                    ('Fecha de nacimiento',
                        formatear_fecha(cliente['Fecha de nacimiento'])
                        if cliente.get('Fecha de nacimiento') else '-'),
                    ('Fecha de inicio', formatear_fecha(cliente['Fecha de inicio'])),
                    ('Fecha de vencimiento', formatear_fecha(cliente['Fecha de vencimiento'])),
                    ('Último pago', formatear_fecha(cliente['Fecha ultimo pago'])),
                    ('Estado', 'Activo' if cliente['Cliente Activo'] else 'Inactivo'),
                    ('Cuota', 'Vencida' if esta_vencido(cliente) else 'Al día'),
                ]
                for etiqueta, valor in datos:
                    with ui.row().classes('dato-fila w-full'):
                        ui.label(etiqueta).classes('dato-label')
                        ui.label(str(valor)).classes('dato-valor')

        construir_footer()


# ============================================================
# PÁGINA: USUARIOS (solo dueño)
# ============================================================

def abrir_formulario_usuario(al_guardar):
    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Nuevo usuario').classes('text-2xl font-bold mb-2')

            username = ui.input('Usuario').props('outlined').classes('w-full')
            nombre = ui.input('Nombre completo').props('outlined').classes('w-full')
            password = ui.input('Contraseña', password=True, password_toggle_button=True) \
                .props('outlined').classes('w-full')
            rol = ui.select(ROLES, value='profe', label='Rol').props('outlined').classes('w-full')

            select_dni = ui.select({}, label='Vincular a socio (DNI)').props('outlined').classes('w-full')
            select_dni.visible = False

            def actualizar_campo_dni():
                if rol.value == 'cliente':
                    opciones_dni = {c['DNI']: f"{c['DNI']} - {c['Nombre y  Apellido']}"
                                    for c in cargar_clientes()}
                    select_dni.options = opciones_dni
                    select_dni.update()
                    select_dni.visible = True
                else:
                    select_dni.visible = False

            rol.on_value_change(actualizar_campo_dni)
            actualizar_campo_dni()

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    if not username.value.strip() or not nombre.value.strip():
                        ui.notify('Usuario y nombre son obligatorios.', type='negative')
                        return
                    if not password.value or len(password.value) < 4:
                        ui.notify('La contraseña debe tener al menos 4 caracteres.', type='negative')
                        return
                    if obtener_usuario(username.value.strip()):
                        ui.notify('Ese nombre de usuario ya existe.', type='negative')
                        return
                    dni_asociado = select_dni.value if rol.value == 'cliente' else None
                    if rol.value == 'cliente' and not dni_asociado:
                        ui.notify('Elegí a qué socio se vincula esta cuenta.', type='negative')
                        return

                    crear_usuario(username.value.strip(), password.value, nombre.value.strip(),
                                  rol.value, dni_asociado)
                    ui.notify('Usuario creado correctamente.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Crear usuario', icon='person_add', on_click=guardar) \
                    .props('unelevated color=primary')

    dialog.open()


@ui.page('/usuarios')
def pagina_usuarios():
    if not requerir_autenticacion():
        return

    if not es_dueño():
        ui.notify('No tenés permisos para acceder a esta página.', type='negative')
        ui.navigate.to('/')
        return

    ui.add_head_html(f'<style>{CSS}</style>')
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-6'):

            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-0'):
                    ui.label('Usuarios').classes('page-title')
                    ui.label('Cuentas de acceso: dueño, profes y clientes.').classes('page-subtitle')
                ui.button('Nuevo usuario', icon='person_add',
                          on_click=lambda: abrir_formulario_usuario(refrescar)) \
                    .props('unelevated color=primary').classes('px-5')

            with ui.column().classes('table-container w-full'):
                columnas = [
                    {'name': 'username', 'label': 'USUARIO', 'field': 'username', 'align': 'left'},
                    {'name': 'nombre', 'label': 'NOMBRE', 'field': 'nombre', 'align': 'left'},
                    {'name': 'rol', 'label': 'ROL', 'field': 'rol', 'align': 'left'},
                    {'name': 'dni_asociado', 'label': 'DNI VINCULADO', 'field': 'dni_asociado', 'align': 'left'},
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'right'},
                ]
                tabla = ui.table(columns=columnas, rows=[], row_key='id').classes('w-full')

                tabla.add_slot('body-cell-acciones', '''
                    <q-td :props="props">
                        <q-btn v-if="props.row.username !== 'admin'" flat round dense icon="delete"
                               color="negative" @click="$parent.$emit('eliminar', props.row)">
                            <q-tooltip>Eliminar usuario</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')

                def on_eliminar(e):
                    eliminar_usuario(e.args['id'])
                    ui.notify('Usuario eliminado.', type='positive')
                    refrescar()

                tabla.on('eliminar', on_eliminar)

                def refrescar():
                    tabla.rows = [
                        {'id': u[0], 'username': u[1], 'nombre': u[2],
                         'rol': u[3], 'dni_asociado': u[4] or '-'}
                        for u in obtener_todos_usuarios()
                    ]

                refrescar()

        construir_footer()


# ============================================================
# INICIO
# ============================================================

inicializar_db()

# Un solo ui.run(): si está la variable de entorno PORT (típico en
# servicios de hosting como Render/Railway) se usa esa, si no, 8080.
ui.run(
    title='Gimnasio Vida Fitness',
    favicon='🏋️',
    reload=False,
    storage_secret='gimnasio_vida_fitness_secret',
    ),
)
ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
)