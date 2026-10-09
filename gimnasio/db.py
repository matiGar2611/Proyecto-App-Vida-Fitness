"""Base de datos SQLite: un único archivo (gimnasio.db) dentro de DATA_DIR.

Uso:
    with db.lectura() as conn:      # solo consultas
        ...
    with db.escritura() as conn:    # una transacción: o se guarda todo, o nada
        ...
"""

import sqlite3
from contextlib import contextmanager

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    nombre        TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('dueño', 'profe'))
);

CREATE TABLE IF NOT EXISTS clientes (
    dni                    TEXT PRIMARY KEY,
    nombre                 TEXT NOT NULL,
    telefono               TEXT NOT NULL DEFAULT '',
    plan                   TEXT NOT NULL,
    fecha_nacimiento       TEXT,
    fecha_inicio           TEXT NOT NULL,
    fecha_vencimiento      TEXT NOT NULL,
    fecha_ultimo_pago      TEXT NOT NULL,
    activo                 INTEGER NOT NULL DEFAULT 1,
    rutina                 TEXT NOT NULL DEFAULT '',
    password_hash          TEXT NOT NULL,
    password_salt          TEXT NOT NULL,
    debe_cambiar_password  INTEGER NOT NULL DEFAULT 1,
    saldo_pendiente        REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pagos (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    dni                        TEXT NOT NULL REFERENCES clientes(dni) ON DELETE CASCADE,
    fecha                      TEXT NOT NULL,
    monto                      REAL NOT NULL,
    vencimiento                TEXT NOT NULL,
    saldo_pendiente_tras_pago  REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_pagos_dni ON pagos(dni);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha);

CREATE TABLE IF NOT EXISTS precios (
    plan    TEXT PRIMARY KEY,
    precio  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ajustes (
    clave  TEXT PRIMARY KEY,
    valor  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anuncios (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha  TEXT NOT NULL,
    texto  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS movimientos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha        TEXT NOT NULL,
    tipo         TEXT NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
    categoria    TEXT NOT NULL,
    descripcion  TEXT NOT NULL,
    monto        REAL NOT NULL,
    dni_cliente  TEXT
);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha);

CREATE TABLE IF NOT EXISTS auditoria (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora  TEXT NOT NULL,
    actor       TEXT NOT NULL,
    accion      TEXT NOT NULL,
    detalle     TEXT NOT NULL DEFAULT ''
);
"""

TABLAS_ESPERADAS = {
    'usuarios', 'clientes', 'pagos', 'precios', 'ajustes',
    'anuncios', 'movimientos', 'auditoria',
}


def ruta_db():
    """Ruta completa del archivo de la base de datos."""
    return config.ruta_datos(config.NOMBRE_DB)


def conectar():
    """Abre una conexión nueva. 'isolation_level=None' deja las transacciones
    en nuestras manos (ver escritura()); 'timeout' hace que, si dos operaciones
    escriben a la vez, la segunda espere hasta 10 segundos en vez de fallar."""
    conn = sqlite3.connect(ruta_db(), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def lectura():
    """Conexión para consultas."""
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def escritura():
    """Transacción de escritura. Toma el bloqueo de escritura al principio
    (BEGIN IMMEDIATE), así las secuencias 'leer -> calcular -> guardar' no se
    pisan con otra operación simultánea. Si algo falla, se deshace todo."""
    conn = conectar()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        conn.close()


def inicializar():
    """Crea las tablas que falten. Es seguro llamarla en cada arranque."""
    conn = conectar()
    try:
        conn.executescript(ESQUEMA)
    finally:
        conn.close()
