"""Cuentas del personal (dueño y profes).

Las filas se devuelven como sqlite3.Row: se accede por posición o por nombre,
en este orden: id, username, password_hash, salt, nombre, rol.
Los clientes NO viven acá: tienen su propia contraseña en datos/clientes.py.
"""

import logging
import os
import secrets

from .. import config, db, seguridad

log = logging.getLogger(__name__)

_COLUMNAS = "id, username, password_hash, salt, nombre, rol"


def obtener_usuario(username):
    """Busca una cuenta por nombre de usuario. None si no existe."""
    with db.lectura() as conn:
        return conn.execute(
            f"SELECT {_COLUMNAS} FROM usuarios WHERE username = ?", (username,)
        ).fetchone()


def obtener_usuario_por_id(user_id):
    """Busca una cuenta por su id. None si no existe."""
    if user_id is None:
        return None
    with db.lectura() as conn:
        return conn.execute(
            f"SELECT {_COLUMNAS} FROM usuarios WHERE id = ?", (user_id,)
        ).fetchone()


def obtener_todos_usuarios():
    """Todas las cuentas (sin contraseñas): id, username, nombre, rol; ordenadas por rol y nombre."""
    with db.lectura() as conn:
        return conn.execute(
            "SELECT id, username, nombre, rol FROM usuarios ORDER BY rol, nombre"
        ).fetchall()


def contar_dueños():
    """Cantidad de cuentas con rol 'dueño' (para no quedarse nunca sin ninguna)."""
    with db.lectura() as conn:
        return conn.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'dueño'").fetchone()[0]


def contar_usuarios():
    with db.lectura() as conn:
        return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]


def crear_usuario(username, password, nombre, rol):
    """Da de alta una cuenta (solo se guarda el hash de la contraseña).
    Lanza sqlite3.IntegrityError si el usuario ya existe o el rol no es válido."""
    salt, hash_val = seguridad.hash_password(password)
    with db.escritura() as conn:
        conn.execute(
            "INSERT INTO usuarios (username, password_hash, salt, nombre, rol) VALUES (?, ?, ?, ?, ?)",
            (username, hash_val, salt, nombre, rol),
        )


def actualizar_usuario(user_id, username, nombre, rol, nueva_password=None):
    """Actualiza una cuenta. Si se pasa 'nueva_password' cambia también la
    contraseña; si no, queda como estaba."""
    with db.escritura() as conn:
        if nueva_password:
            salt, hash_val = seguridad.hash_password(nueva_password)
            conn.execute(
                "UPDATE usuarios SET username = ?, nombre = ?, rol = ?, password_hash = ?, salt = ? "
                "WHERE id = ?",
                (username, nombre, rol, hash_val, salt, user_id),
            )
        else:
            conn.execute(
                "UPDATE usuarios SET username = ?, nombre = ?, rol = ? WHERE id = ?",
                (username, nombre, rol, user_id),
            )


def eliminar_usuario(user_id):
    with db.escritura() as conn:
        conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))


def asegurar_cuenta_dueño():
    """Si no hay ninguna cuenta, crea la del dueño ('admin').

    La contraseña sale de ADMIN_PASSWORD. Si no está (o es muy corta), se
    genera una al azar y se muestra UNA vez en la consola / logs.
    Devuelve la contraseña generada, o None si no hizo falta generar ninguna."""
    if contar_usuarios() > 0:
        return None

    clave = os.environ.get('ADMIN_PASSWORD', '')
    generada = None
    if len(clave) < config.MIN_PASSWORD_PERSONAL:
        clave = generada = secrets.token_urlsafe(12)
    crear_usuario('admin', clave, 'Dueño del gimnasio', 'dueño')

    if generada:
        print(
            "=" * 60 + "\n"
            "CUENTA DEL DUEÑO CREADA\n"
            "  Usuario:    admin\n"
            f"  Contraseña: {generada}\n"
            "Guardala ahora y cambiala desde la app (candado arriba a la derecha).\n"
            "Para elegir la tuya, definí ADMIN_PASSWORD (mínimo 8 caracteres).\n"
            + "=" * 60,
            flush=True,
        )
    return generada


def endurecer_admin_de_fabrica():
    """Si 'admin' todavía tiene la contraseña de fábrica (admin123, de versiones
    viejas), la reemplaza por ADMIN_PASSWORD si está definida; si no, avisa en el log.
    Devuelve True si la cambió."""
    registro = obtener_usuario('admin')
    if registro is None or not seguridad.verificar_password('admin123', registro['salt'], registro['password_hash']):
        return False

    nueva = os.environ.get('ADMIN_PASSWORD', '')
    if len(nueva) >= config.MIN_PASSWORD_PERSONAL and nueva != 'admin123':
        actualizar_usuario(registro['id'], registro['username'], registro['nombre'], registro['rol'], nueva)
        log.warning("La cuenta 'admin' tenía la contraseña de fábrica: se reemplazó por ADMIN_PASSWORD.")
        return True

    log.warning(
        "ATENCIÓN: la cuenta 'admin' todavía usa la contraseña de fábrica (admin123). "
        "Cambiala ya, o definí ADMIN_PASSWORD (mínimo 8 caracteres) y reiniciá."
    )
    return False
