"""Pasa los datos de la versión anterior (archivos JSON + usuarios.db) a la base nueva.

Se ejecuta sola, una vez, al arrancar: si en DATA_DIR hay archivos de la versión
anterior y la base nueva todavía está vacía. Los archivos viejos NO se borran
ni se modifican; una vez que verifiques que todo se pasó bien, archivalos o
borralos (tienen datos personales, y los viejos podían guardar contraseñas en
texto plano, que acá NO se copian).
"""

import json
import logging
import os
import sqlite3

from .. import config, db, seguridad, tiempo

log = logging.getLogger(__name__)

CLAVE_MIGRADO = 'migracion_datos_anteriores'


def _leer_json(nombre, defecto):
    ruta = config.ruta_datos(nombre)
    if not os.path.exists(ruta):
        return defecto
    try:
        with open(ruta, 'r', encoding='utf-8') as archivo:
            return json.load(archivo)
    except (json.JSONDecodeError, OSError):
        log.exception("No se pudo leer %s; se omite.", nombre)
        return defecto


def _usuarios_anteriores():
    ruta = config.ruta_datos('usuarios.db')
    if not os.path.exists(ruta):
        return []
    try:
        conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        try:
            return conn.execute(
                "SELECT id, username, password_hash, salt, nombre, rol FROM usuarios"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        log.exception("No se pudo leer el usuarios.db anterior; se omite.")
        return []


def hay_datos_anteriores():
    nombres = ['usuarios.db', 'Clientes.json', 'precios.json', 'informacion.json',
               'anuncios.json', 'contabilidad.json']
    return any(os.path.exists(config.ruta_datos(n)) for n in nombres)


def migrar_si_corresponde():
    """Importa los datos anteriores si corresponde. Devuelve un resumen
    ({'usuarios': n, 'clientes': n, ...}) o None si no hizo nada."""
    with db.lectura() as conn:
        ya_hecho = conn.execute("SELECT 1 FROM ajustes WHERE clave = ?", (CLAVE_MIGRADO,)).fetchone()
        hay_datos = conn.execute(
            "SELECT (SELECT COUNT(*) FROM usuarios) + (SELECT COUNT(*) FROM clientes)"
        ).fetchone()[0]
    if ya_hecho or hay_datos or not hay_datos_anteriores():
        return None

    usuarios = _usuarios_anteriores()
    clientes = _leer_json('Clientes.json', [])
    precios = _leer_json('precios.json', {})
    informacion = _leer_json('informacion.json', {})
    anuncios = _leer_json('anuncios.json', [])
    movimientos = _leer_json('contabilidad.json', [])

    resumen = {'usuarios': 0, 'clientes': 0, 'pagos': 0, 'anuncios': 0, 'movimientos': 0}
    with db.escritura() as conn:
        for u in usuarios:
            if u[5] not in config.ROLES:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO usuarios (id, username, password_hash, salt, nombre, rol) "
                "VALUES (?, ?, ?, ?, ?, ?)", tuple(u),
            )
            resumen['usuarios'] += 1

        for c in clientes:
            dni = str(c.get('DNI', '')).strip()
            if not dni or conn.execute("SELECT 1 FROM clientes WHERE dni = ?", (dni,)).fetchone():
                continue
            if c.get('Password Hash') and c.get('Password Salt'):
                hash_val, salt = c['Password Hash'], c['Password Salt']
                debe_cambiar = c.get('Debe cambiar password')
                if debe_cambiar is None:
                    debe_cambiar = seguridad.verificar_password(dni, salt, hash_val)
            else:
                # Ficha muy vieja sin contraseña: entraba con su DNI.
                salt, hash_val = seguridad.hash_password(dni)
                debe_cambiar = True
            conn.execute(
                "INSERT INTO clientes (dni, nombre, telefono, plan, fecha_nacimiento, fecha_inicio, "
                "fecha_vencimiento, fecha_ultimo_pago, activo, rutina, password_hash, password_salt, "
                "debe_cambiar_password, saldo_pendiente) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (dni, c.get('Nombre y  Apellido', ''), c.get('Telefono', ''), c.get('Plan', ''),
                 c.get('Fecha de nacimiento'), c.get('Fecha de inicio') or str(tiempo.hoy()),
                 c.get('Fecha de vencimiento') or str(tiempo.hoy()),
                 c.get('Fecha ultimo pago') or str(tiempo.hoy()),
                 1 if c.get('Cliente Activo', True) else 0, seguridad.sanitizar_html(c.get('Rutina', '')),
                 hash_val, salt, 1 if debe_cambiar else 0, c.get('Saldo pendiente', 0) or 0),
            )
            resumen['clientes'] += 1
            for p in c.get('Historial de pagos', []):
                conn.execute(
                    "INSERT INTO pagos (dni, fecha, monto, vencimiento, saldo_pendiente_tras_pago) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (dni, p.get('fecha', ''), p.get('monto', 0), p.get('vencimiento', ''),
                     p.get('saldo_pendiente_tras_pago', 0)),
                )
                resumen['pagos'] += 1

        for plan, precio in precios.items():
            conn.execute("INSERT OR REPLACE INTO precios (plan, precio) VALUES (?, ?)", (plan, precio))
        if informacion.get('texto'):
            conn.execute("INSERT OR REPLACE INTO ajustes (clave, valor) VALUES ('informacion', ?)",
                         (informacion['texto'],))

        for a in sorted(anuncios, key=lambda x: x.get('id', 0)):
            conn.execute("INSERT INTO anuncios (id, fecha, texto) VALUES (?, ?, ?)",
                         (a.get('id'), a.get('fecha', ''), a.get('texto', '')))
            resumen['anuncios'] += 1

        for m in sorted(movimientos, key=lambda x: x.get('id', 0)):
            conn.execute(
                "INSERT INTO movimientos (id, fecha, tipo, categoria, descripcion, monto, dni_cliente) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (m.get('id'), m.get('fecha', ''), m.get('tipo', 'ingreso'), m.get('categoria', ''),
                 m.get('descripcion', ''), m.get('monto', 0), m.get('dni_cliente')),
            )
            resumen['movimientos'] += 1

        conn.execute("INSERT INTO ajustes (clave, valor) VALUES (?, ?)",
                     (CLAVE_MIGRADO, str(tiempo.hoy())))

    log.warning("Datos de la versión anterior importados: %s", resumen)
    return resumen
