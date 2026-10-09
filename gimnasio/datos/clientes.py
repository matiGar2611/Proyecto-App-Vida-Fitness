"""Fichas de los socios.

Cada cliente se devuelve como un diccionario con estas claves:
    dni, nombre, telefono, plan, fecha_nacimiento, fecha_inicio,
    fecha_vencimiento, fecha_ultimo_pago, activo (bool), rutina,
    saldo_pendiente, debe_cambiar_password (bool), password_hash, password_salt
y, si se pide, 'historial': lista de pagos [{fecha, monto, vencimiento,
saldo_pendiente_tras_pago}] del más viejo al más nuevo.
"""

from datetime import timedelta

from .. import db, seguridad, tiempo
from . import ajustes, contabilidad


def _a_cliente(fila):
    cliente = dict(fila)
    cliente['activo'] = bool(cliente['activo'])
    cliente['debe_cambiar_password'] = bool(cliente['debe_cambiar_password'])
    return cliente


def _adjuntar_historial(conn, clientes):
    por_dni = {c['dni']: [] for c in clientes}
    for pago in conn.execute(
        "SELECT dni, fecha, monto, vencimiento, saldo_pendiente_tras_pago FROM pagos ORDER BY id"
    ):
        if pago['dni'] in por_dni:
            por_dni[pago['dni']].append({
                'fecha': pago['fecha'],
                'monto': pago['monto'],
                'vencimiento': pago['vencimiento'],
                'saldo_pendiente_tras_pago': pago['saldo_pendiente_tras_pago'],
            })
    for cliente in clientes:
        cliente['historial'] = por_dni[cliente['dni']]


def cargar_clientes(con_historial=False):
    """Todos los clientes, en el orden en que se dieron de alta."""
    with db.lectura() as conn:
        clientes = [_a_cliente(f) for f in conn.execute("SELECT * FROM clientes ORDER BY rowid")]
        if con_historial:
            _adjuntar_historial(conn, clientes)
    return clientes


def buscar_cliente_por_dni(dni):
    """El cliente (con su historial de pagos) o None si no existe."""
    with db.lectura() as conn:
        fila = conn.execute("SELECT * FROM clientes WHERE dni = ?", (dni,)).fetchone()
        if fila is None:
            return None
        cliente = _a_cliente(fila)
        _adjuntar_historial(conn, [cliente])
    return cliente


def dni_existe(dni):
    with db.lectura() as conn:
        return conn.execute("SELECT 1 FROM clientes WHERE dni = ?", (dni,)).fetchone() is not None


def agregar_cliente(dni, nombre, telefono, plan, fecha_nacimiento, monto_abonado=None):
    """Da de alta un cliente nuevo y registra su primer pago.

    El primer pago (por defecto, el precio del plan) se anota en el historial y
    en la contabilidad, todo en una sola transacción. Si abona menos que el precio
    del plan, la diferencia queda como saldo pendiente. La cuota vence a 30 días y
    la contraseña inicial es el DNI (la tiene que cambiar al entrar).

    Devuelve True si se agregó, o False si ese DNI ya existía.
    Lanza ValueError si el monto del primer pago no es mayor a cero."""
    if monto_abonado is not None and monto_abonado <= 0:
        raise ValueError("El monto del primer pago tiene que ser mayor a cero.")

    hoy = tiempo.hoy()
    vencimiento = str(hoy + timedelta(days=30))
    salt, hash_val = seguridad.hash_password(dni)

    with db.escritura() as conn:
        if conn.execute("SELECT 1 FROM clientes WHERE dni = ?", (dni,)).fetchone():
            return False
        precio = ajustes.precio_de_plan(plan, conn=conn)
        monto = precio if monto_abonado is None else monto_abonado
        saldo = max(0, precio - monto)

        conn.execute(
            "INSERT INTO clientes (dni, nombre, telefono, plan, fecha_nacimiento, fecha_inicio, "
            "fecha_vencimiento, fecha_ultimo_pago, activo, rutina, password_hash, password_salt, "
            "debe_cambiar_password, saldo_pendiente) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '', ?, ?, 1, ?)",
            (dni, nombre, telefono, plan, fecha_nacimiento, str(hoy), vencimiento, str(hoy),
             hash_val, salt, saldo),
        )
        conn.execute(
            "INSERT INTO pagos (dni, fecha, monto, vencimiento, saldo_pendiente_tras_pago) "
            "VALUES (?, ?, ?, ?, ?)",
            (dni, str(hoy), monto, vencimiento, saldo),
        )
        contabilidad.registrar_movimiento(
            "ingreso", "Cuota", f"Pago de cuota (alta) - {nombre} (DNI {dni})", monto, dni, conn=conn,
        )
    return True


def actualizar_cliente(dni, nombre, telefono, plan, fecha_nacimiento):
    """Modifica nombre, teléfono, plan y fecha de nacimiento (el DNI y las fechas de pago no se tocan)."""
    with db.escritura() as conn:
        cursor = conn.execute(
            "UPDATE clientes SET nombre = ?, telefono = ?, plan = ?, fecha_nacimiento = ? WHERE dni = ?",
            (nombre, telefono, plan, fecha_nacimiento, dni),
        )
        return cursor.rowcount > 0


def eliminar_cliente(dni):
    """Elimina al cliente y su historial de pagos. (Sus asientos contables se conservan.)"""
    with db.escritura() as conn:
        return conn.execute("DELETE FROM clientes WHERE dni = ?", (dni,)).rowcount > 0


def actualizar_rutina(dni, texto_rutina):
    """Guarda la rutina de un cliente. El HTML se limpia antes de guardarlo."""
    limpio = seguridad.sanitizar_html(texto_rutina)
    with db.escritura() as conn:
        return conn.execute(
            "UPDATE clientes SET rutina = ? WHERE dni = ?", (limpio, dni)
        ).rowcount > 0


# ---- Contraseña del cliente ----

def verificar_password_cliente(cliente, password_ingresada):
    """True si la contraseña ingresada es la del cliente."""
    return seguridad.verificar_password(
        password_ingresada, cliente['password_salt'], cliente['password_hash']
    )


def guardar_password_cliente(dni, nueva_password, debe_cambiar):
    """Guarda el hash de una contraseña y marca si el cliente todavía tiene que cambiarla."""
    salt, hash_val = seguridad.hash_password(nueva_password)
    with db.escritura() as conn:
        return conn.execute(
            "UPDATE clientes SET password_hash = ?, password_salt = ?, debe_cambiar_password = ? "
            "WHERE dni = ?",
            (hash_val, salt, 1 if debe_cambiar else 0, dni),
        ).rowcount > 0


def cambiar_password_cliente(dni, nueva_password):
    """El cliente elige una contraseña propia: queda como definitiva."""
    return guardar_password_cliente(dni, nueva_password, False)


def restablecer_password_cliente(dni):
    """Vuelve la contraseña a su DNI y lo obliga a cambiarla al entrar."""
    return guardar_password_cliente(dni, dni, True)
