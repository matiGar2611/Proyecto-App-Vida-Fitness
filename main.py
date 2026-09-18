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

ROLES = ['dueño', 'profe']  # el rol 'cliente' no vive en esta tabla: se entra solo con el DNI

ARCHIVO_INFORMACION = 'informacion.json'

INFO_IMPORTANTE_POR_DEFECTO = """
- El gimnasio abre de lunes a sábado de 7:00 a 22:00 hs.
- Traé una toalla propia para usar las máquinas.
- Avisá con anticipación si vas a dejar de asistir, para no acumular
  atraso en el vencimiento.
- Cualquier consulta sobre tu cuota, hablá con recepción.
""".strip()


# ============================================================
# BASE DE DATOS DE USUARIOS (dueño / profe)
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
            rol TEXT NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("PRAGMA table_info(usuarios)")
    columnas_existentes = {fila[1] for fila in cursor.fetchall()}
    if "rol" not in columnas_existentes:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'dueño'")
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
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        salt, hash_val = hash_password('admin123')
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, salt, nombre, rol) VALUES (?, ?, ?, ?, ?)",
            ('admin', hash_val, salt, 'Dueño del gimnasio', 'dueño')
        )
        conn.commit()
    conn.close()


def obtener_usuario(username):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, salt, nombre, rol FROM usuarios WHERE username = ?",
        (username,)
    )
    usuario = cursor.fetchone()
    conn.close()
    return usuario


def obtener_usuario_por_id(user_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password_hash, salt, nombre, rol FROM usuarios WHERE id = ?",
        (user_id,)
    )
    usuario = cursor.fetchone()
    conn.close()
    return usuario


def obtener_todos_usuarios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nombre, rol FROM usuarios ORDER BY rol, nombre")
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios


def crear_usuario(username, password, nombre, rol):
    conn = conectar_db()
    cursor = conn.cursor()
    salt, hash_val = hash_password(password)
    cursor.execute(
        "INSERT INTO usuarios (username, password_hash, salt, nombre, rol) VALUES (?, ?, ?, ?, ?)",
        (username, hash_val, salt, nombre, rol)
    )
    conn.commit()
    conn.close()


def actualizar_usuario(user_id, username, nombre, rol, nueva_password=None):
    conn = conectar_db()
    cursor = conn.cursor()
    if nueva_password:
        salt, hash_val = hash_password(nueva_password)
        cursor.execute(
            "UPDATE usuarios SET username = ?, nombre = ?, rol = ?, password_hash = ?, salt = ? WHERE id = ?",
            (username, nombre, rol, hash_val, salt, user_id)
        )
    else:
        cursor.execute(
            "UPDATE usuarios SET username = ?, nombre = ?, rol = ? WHERE id = ?",
            (username, nombre, rol, user_id)
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
# El rol 'cliente' NO vive en usuarios.db: se arma en el momento del
# login por DNI (ver pagina_login) y se guarda solo en app.storage.user.

def verificar_autenticacion():
    return 'rol' in app.storage.user


def rol_actual():
    return app.storage.user.get('rol')


def dni_actual():
    return app.storage.user.get('dni')


def es_dueño():
    return rol_actual() == 'dueño'


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
        "Rutina": "",
    }


def actualizar_cliente(dni, nombre_y_apellido, telefono, plan, fecha_nacimiento):
    lista_clientes = cargar_clientes()
    for cliente in lista_clientes:
        if cliente["DNI"] == dni:
            cliente["Nombre y  Apellido"] = nombre_y_apellido
            cliente["Telefono"] = telefono
            cliente["Plan"] = plan
            cliente["Fecha de nacimiento"] = fecha_nacimiento
            guardar_clientes(lista_clientes)
            return True
    return False


def registrar_pago(dni, nueva_fecha_vencimiento):
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


def dias_para_vencimiento(cliente):
    """Positivo: días que faltan para vencer. Negativo: días desde que venció."""
    fecha_vencimiento = datetime.strptime(cliente["Fecha de vencimiento"], "%Y-%m-%d").date()
    return (fecha_vencimiento - date.today()).days


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


def proximos_cumpleanos(dias_rango=30):
    hoy = date.today()
    resultados = []

    for cliente in cargar_clientes():
        fecha_nac_texto = cliente.get("Fecha de nacimiento")
        if not fecha_nac_texto:
            continue

        fecha_nac = datetime.strptime(fecha_nac_texto, "%Y-%m-%d").date()

        try:
            proximo = fecha_nac.replace(year=hoy.year)
        except ValueError:
            proximo = fecha_nac.replace(year=hoy.year, day=28)

        if proximo < hoy:
            try:
                proximo = proximo.replace(year=hoy.year + 1)
            except ValueError:
                proximo = proximo.replace(year=hoy.year + 1, day=28)

        dias_faltantes = (proximo - hoy).days
        if dias_faltantes <= dias_rango:
            resultados.append({
                "nombre": cliente["Nombre y  Apellido"],
                "dni": cliente["DNI"],
                "fecha": proximo.strftime("%d/%m"),
                "dias_faltantes": dias_faltantes,
                "es_hoy": dias_faltantes == 0,
            })

    resultados.sort(key=lambda r: r["dias_faltantes"])
    return resultados


# ============================================================
# RUTINA DE CADA CLIENTE (texto simple, guardado dentro de Clientes.json)
# ============================================================

def actualizar_rutina(dni, texto_rutina):
    lista_clientes = cargar_clientes()
    for cliente in lista_clientes:
        if cliente["DNI"] == dni:
            cliente["Rutina"] = texto_rutina
            guardar_clientes(lista_clientes)
            return True
    return False


# ============================================================
# INFORMACIÓN PARA CLIENTES (editable por el dueño)
# ============================================================

def cargar_informacion():
    """Texto que ven los clientes en 'Información importante'. Si
    todavía no se guardó nada, usa el texto por defecto."""
    if os.path.exists(ARCHIVO_INFORMACION):
        with open(ARCHIVO_INFORMACION, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            return datos.get("texto", INFO_IMPORTANTE_POR_DEFECTO)
    return INFO_IMPORTANTE_POR_DEFECTO


def guardar_informacion(texto):
    with open(ARCHIVO_INFORMACION, "w", encoding="utf-8") as archivo:
        json.dump({"texto": texto}, archivo, ensure_ascii=False, indent=4)


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

.cumple-fila {
    padding: 10px 14px; border-radius: 12px;
    background: rgba(255, 255, 255, 0.45);
    margin-bottom: 6px;
}
.cumple-hoy {
    padding: 10px 14px; border-radius: 12px;
    background: linear-gradient(135deg, rgba(74, 222, 128, 0.35), rgba(250, 204, 21, 0.30));
    border: 1px solid rgba(22, 163, 74, 0.4);
    margin-bottom: 6px;
    font-weight: 700;
}

.mi-cuenta-card {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
    border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 24px;
    box-shadow: 0 25px 60px rgba(21, 128, 61, 0.14);
    padding: 32px; width: 560px; max-width: 95vw;
}
.dato-fila { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.06); }
.dato-label { color: #5c6b62; font-weight: 600; }
.dato-valor { color: #10241a; font-weight: 700; }

.venc-ok {
    background: rgba(74, 222, 128, 0.25); border: 1px solid rgba(22, 163, 74, 0.35);
    border-radius: 14px; padding: 16px 20px; font-weight: 700; color: #14532d;
}
.venc-vencido {
    background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 14px; padding: 16px 20px; font-weight: 700; color: #991b1b;
}

.info-importante {
    background: rgba(250, 204, 21, 0.14); border: 1px solid rgba(202, 138, 4, 0.3);
    border-radius: 14px; padding: 16px 20px; color: #713f12; font-size: 14px; line-height: 1.7;
    white-space: pre-line;
}

.rutina-cliente {
    background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(37, 99, 235, 0.3);
    border-radius: 14px; padding: 16px 20px; color: #1e3a8a; font-size: 14px; line-height: 1.7;
    white-space: pre-line;
}
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
                    ui.button('Información', icon='info',
                              on_click=lambda: ui.navigate.to('/informacion')) \
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
# PÁGINA: LOGIN (elige Administrador o Cliente)
# ============================================================

@ui.page('/login')
def pagina_login():
    if verificar_autenticacion():
        ui.navigate.to('/mi-cuenta' if es_cliente_rol() else '/')
        return

    ui.add_head_html(f'<style>{CSS}</style>')

    with ui.element('div').classes('login-page w-full'):
        with ui.element('div').classes('login-card'):
            with ui.column().classes('items-center gap-4 mb-4 w-full'):
                with ui.element('div').classes('logo-icon'):
                    ui.icon('fitness_center').classes('text-3xl')
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
                username_input = ui.input('Usuario').props('outlined').classes('w-full')
                password_input = ui.input(
                    'Contraseña', password=True, password_toggle_button=True
                ).props('outlined').classes('w-full')

                def intentar_login_admin():
                    error_admin.clear()
                    usuario = username_input.value.strip()
                    clave = password_input.value

                    if not usuario or not clave:
                        with error_admin:
                            ui.label('Completá usuario y contraseña').classes('login-error w-full')
                        return

                    registro = obtener_usuario(usuario)
                    if registro is None:
                        with error_admin:
                            ui.label('Usuario no encontrado').classes('login-error w-full')
                        return

                    if not verificar_password(clave, registro[3], registro[2]):
                        with error_admin:
                            ui.label('Contraseña incorrecta').classes('login-error w-full')
                        return

                    app.storage.user['id'] = registro[0]
                    app.storage.user['username'] = registro[1]
                    app.storage.user['nombre'] = registro[4]
                    app.storage.user['rol'] = registro[5]

                    ui.notify(f'Bienvenido, {registro[4]}', type='positive')
                    ui.navigate.to('/')

                ui.button('Ingresar', icon='login', on_click=intentar_login_admin) \
                    .props('unelevated color=primary').classes('w-full mt-2')
                username_input.on('keydown.enter', lambda e: intentar_login_admin())
                password_input.on('keydown.enter', lambda e: intentar_login_admin())

                with ui.element('div').classes('login-hint'):
                    ui.label('Cuenta por defecto (dueño)').classes('login-hint-label')
                    ui.label('Usuario: admin · Contraseña: admin123').classes('login-hint-text')

                def volver_admin():
                    contenedor_admin.visible = False
                    selector.visible = True

                ui.button('Volver', icon='arrow_back', on_click=volver_admin) \
                    .props('flat').classes('w-full mt-2')

            # ---- Formulario Cliente (solo DNI) ----
            with contenedor_cliente:
                error_cliente = ui.column().classes('w-full')
                dni_input = ui.input('Tu DNI').props('outlined').classes('w-full')

                def intentar_login_cliente():
                    error_cliente.clear()
                    dni = dni_input.value.strip()

                    if not dni:
                        with error_cliente:
                            ui.label('Ingresá tu DNI').classes('login-error w-full')
                        return

                    cliente = buscar_cliente_por_dni(dni)
                    if cliente is None:
                        with error_cliente:
                            ui.label('No encontramos ese DNI. Consultá con recepción.') \
                                .classes('login-error w-full')
                        return

                    app.storage.user['rol'] = 'cliente'
                    app.storage.user['dni'] = dni
                    app.storage.user['nombre'] = cliente['Nombre y  Apellido']

                    ui.notify(f"Bienvenido, {cliente['Nombre y  Apellido']}", type='positive')
                    ui.navigate.to('/mi-cuenta')

                ui.button('Ingresar', icon='login', on_click=intentar_login_cliente) \
                    .props('unelevated color=primary').classes('w-full mt-2')
                dni_input.on('keydown.enter', lambda e: intentar_login_cliente())

                def volver_cliente():
                    contenedor_cliente.visible = False
                    selector.visible = True

                ui.button('Volver', icon='arrow_back', on_click=volver_cliente) \
                    .props('flat').classes('w-full mt-2')


# ============================================================
# PÁGINA: MI CUENTA (cliente)
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

    dni = dni_actual()
    cliente = buscar_cliente_por_dni(dni) if dni else None

    with ui.column().classes('w-full min-h-screen items-center justify-center py-8'):
        with ui.element('div').classes('mi-cuenta-card'):
            if cliente is None:
                ui.label('No pudimos encontrar tu ficha. Consultá con recepción.') \
                    .classes('login-error w-full')
            else:
                ui.label(f"¡Hola, {cliente['Nombre y  Apellido']}!").classes('page-title')
                ui.label('Este es tu resumen en el gimnasio.').classes('page-subtitle mb-4')

                # --- Vencimiento y días restantes ---
                dias = dias_para_vencimiento(cliente)
                vencido = esta_vencido(cliente)

                with ui.column().classes(('venc-vencido' if vencido else 'venc-ok') + ' w-full mb-4'):
                    ui.label(f"Próximo vencimiento: {formatear_fecha(cliente['Fecha de vencimiento'])}")
                    if vencido:
                        ui.label(f"Tu cuota está vencida hace {abs(dias)} día(s).")
                    else:
                        ui.label(f"Te quedan {dias} día(s) de cuota vigente.")

                # --- Tus datos ---
                ui.label('Tus datos').classes('text-lg font-bold mt-2 mb-1')
                datos = [
                    ('DNI', cliente['DNI']),
                    ('Teléfono', cliente['Telefono']),
                    ('Plan', cliente['Plan']),
                    ('Fecha de nacimiento',
                        formatear_fecha(cliente['Fecha de nacimiento'])
                        if cliente.get('Fecha de nacimiento') else '-'),
                    ('Último pago', formatear_fecha(cliente['Fecha ultimo pago'])),
                    ('Estado', 'Activo' if cliente['Cliente Activo'] else 'Inactivo'),
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
                texto_rutina = cliente.get('Rutina', '').strip()
                with ui.column().classes('rutina-cliente w-full'):
                    if texto_rutina:
                        ui.label(texto_rutina)
                    else:
                        ui.label('Todavía no tenés una rutina cargada. Consultá con tu profe.')

        construir_footer()


# ============================================================
# DIÁLOGOS: cliente (agregar / editar / pagar / rutina / eliminar)
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


def abrir_formulario_editar_cliente(dni_original, al_guardar):
    cliente = buscar_cliente_por_dni(dni_original)
    if cliente is None:
        ui.notify('No se encontró el cliente.', type='negative')
        return

    with ui.dialog() as dialog:
        with ui.card().classes('w-[480px] max-w-[95vw] p-7'):
            ui.label('Editar cliente').classes('text-2xl font-bold')
            ui.label(f'DNI: {dni_original} (no editable)').classes('text-sm text-gray-500 mb-2')

            nombre = ui.input('Nombre y Apellido', value=cliente['Nombre y  Apellido']) \
                .props('outlined').classes('w-full')
            telefono = ui.input('Teléfono (10 caracteres)', value=cliente['Telefono']) \
                .props('outlined').classes('w-full')
            plan = ui.select(
                ['2 veces por semana', '3 veces por semana', 'Todos los días'],
                value=cliente['Plan'], label='Plan'
            ).props('outlined').classes('w-full')

            ui.label('Fecha de nacimiento').classes('text-sm text-gray-600 mt-2')
            nacimiento = ui.date(value=cliente.get('Fecha de nacimiento')).props('outlined').classes('w-full')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                def guardar():
                    if len(telefono.value.strip()) != 10:
                        ui.notify('El teléfono debe tener 10 caracteres.', type='negative')
                        return
                    if not nacimiento.value:
                        ui.notify('Elegí la fecha de nacimiento.', type='negative')
                        return

                    actualizar_cliente(dni_original, nombre.value.strip(),
                                       telefono.value.strip(), plan.value, nacimiento.value)
                    ui.notify('Cliente actualizado.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Guardar cambios', icon='save', on_click=guardar).props('unelevated color=primary')

    dialog.open()


def abrir_dialogo_pago(dni, nombre, al_registrar):
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


def abrir_dialogo_rutina(dni, nombre, al_cambiar=None):
    """El profe o el dueño escriben (o borran) la rutina de un cliente
    puntual, como texto simple guardado en su ficha (Clientes.json)."""
    cliente = buscar_cliente_por_dni(dni)
    texto_actual = cliente.get('Rutina', '') if cliente else ''

    with ui.dialog() as dialog:
        with ui.card().classes('w-[520px] max-w-[95vw] p-7'):
            ui.label('Rutina de entrenamiento').classes('text-xl font-bold')
            ui.label(f'Cliente: {nombre}').classes('text-gray-600 mb-3')

            area_rutina = ui.textarea(value=texto_actual, placeholder='Escribí acá la rutina...') \
                .props('outlined rows=8').classes('w-full')

            with ui.row().classes('w-full justify-between gap-2 mt-4'):
                def borrar():
                    area_rutina.value = ''

                ui.button('Vaciar', icon='delete', on_click=borrar).props('outline color=negative')

                with ui.row().classes('gap-2'):
                    ui.button('Cerrar', on_click=dialog.close).props('flat')

                    def guardar():
                        actualizar_rutina(dni, area_rutina.value.strip())
                        ui.notify('Rutina guardada en el perfil del cliente.', type='positive')
                        dialog.close()
                        if al_cambiar:
                            al_cambiar()

                    ui.button('Guardar rutina', icon='save', on_click=guardar) \
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
# PÁGINA PRINCIPAL (dueño / profe)
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

            # Panel de cumpleaños: siempre visible.
            with ui.column().classes('glass-card w-full p-5'):
                ui.label('🎂 Próximos cumpleaños (30 días)').classes('text-lg font-bold mb-2')
                contenedor_cumples = ui.column().classes('w-full')

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

                boton_eliminar_html = '''
                        <q-btn flat round dense icon="delete" color="negative"
                               @click="$parent.$emit('eliminar', props.row)">
                            <q-tooltip>Eliminar</q-tooltip>
                        </q-btn>
                ''' if es_dueño() else ''

                # El ícono de PDF (asignar rutina) lo pueden usar dueño y profe.
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
                        <q-btn flat round dense icon="edit_note" color="primary"
                               @click="$parent.$emit('rutina', props.row)">
                            <q-tooltip>Rutina (texto)</q-tooltip>
                        </q-btn>
                        {boton_eliminar_html}
                    </q-td>
                ''')

                def on_editar(e):
                    abrir_formulario_editar_cliente(e.args['dni'], refrescar)

                def on_pagar(e):
                    abrir_dialogo_pago(e.args['dni'], e.args['nombre'], refrescar)

                def on_rutina(e):
                    abrir_dialogo_rutina(e.args['dni'], e.args['nombre'], al_cambiar=refrescar)

                def on_eliminar(e):
                    if not es_dueño():
                        ui.notify('No tenés permisos para eliminar clientes.', type='negative')
                        return
                    confirmar_eliminacion(e.args['dni'], e.args['nombre'], refrescar)

                tabla.on('editar', on_editar)
                tabla.on('pagar', on_pagar)
                tabla.on('rutina', on_rutina)
                tabla.on('eliminar', on_eliminar)

            def refrescar():
                tabla.rows = obtener_filas(
                    solo_vencidos=checkbox_vencidos.value,
                    plan_filtro=select_plan.value,
                )
                lista_clientes = cargar_clientes()
                etiqueta_activos.set_text(str(sum(1 for c in lista_clientes if c["Cliente Activo"])))
                etiqueta_vencidos.set_text(str(sum(1 for c in lista_clientes if esta_vencido(c))))

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

            checkbox_vencidos.on_value_change(refrescar)
            select_plan.on_value_change(refrescar)

            refrescar()

        construir_footer()


# ============================================================
# PÁGINA: USUARIOS (solo dueño) -- cuentas de dueño y profe
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

                    crear_usuario(username.value.strip(), password.value, nombre.value.strip(), rol.value)
                    ui.notify('Usuario creado correctamente.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Crear usuario', icon='person_add', on_click=guardar) \
                    .props('unelevated color=primary')

    dialog.open()


def abrir_formulario_editar_usuario(user_id, al_guardar):
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
            rol = ui.select(ROLES, value=rol_actual_valor, label='Rol').props('outlined').classes('w-full')
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
                    if password.value and len(password.value) < 4:
                        ui.notify('La contraseña debe tener al menos 4 caracteres.', type='negative')
                        return

                    otro = obtener_usuario(nuevo_username)
                    if otro and otro[0] != user_id:
                        ui.notify('Ese nombre de usuario ya lo usa otra cuenta.', type='negative')
                        return

                    actualizar_usuario(user_id, nuevo_username, nombre.value.strip(),
                                       rol.value, password.value or None)
                    ui.notify('Usuario actualizado.', type='positive')
                    dialog.close()
                    al_guardar()

                ui.button('Guardar cambios', icon='save', on_click=guardar).props('unelevated color=primary')

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
                    eliminar_usuario(e.args['id'])
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


# ============================================================
# PÁGINA: INFORMACIÓN (solo dueño) -- edita lo que ve el cliente
# ============================================================

@ui.page('/informacion')
def pagina_informacion():
    if not requerir_autenticacion():
        return

    if not es_dueño():
        ui.notify('No tenés permisos para acceder a esta página.', type='negative')
        ui.navigate.to('/')
        return

    ui.add_head_html(f'<style>{CSS}</style>')
    construir_navbar()

    with ui.column().classes('w-full min-h-screen'):
        with ui.column().classes('w-full max-w-3xl mx-auto p-8 gap-6'):

            ui.label('Información importante').classes('page-title')
            ui.label('Este texto es el que ven todos los clientes en su portal '
                      '(horarios, uso de toallas, cómo avisar si van a dejar de '
                      'asistir, etc.). Editalo y guardá los cambios.') \
                .classes('page-subtitle')

            with ui.column().classes('glass-card w-full p-6'):
                texto = ui.textarea(value=cargar_informacion()) \
                    .props('outlined rows=10').classes('w-full')

                def guardar():
                    guardar_informacion(texto.value.strip())
                    ui.notify('Información actualizada. Ya la ven los clientes.', type='positive')

                ui.button('Guardar cambios', icon='save', on_click=guardar) \
                    .props('unelevated color=primary').classes('mt-3')

        construir_footer()


# ============================================================
# INICIO
# ============================================================

inicializar_db()

ui.run(
    title='Gimnasio Vida Fitness',
    favicon='🏋️',
    reload=False,
    storage_secret='gimnasio_vida_fitness_secret',
)

ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
)