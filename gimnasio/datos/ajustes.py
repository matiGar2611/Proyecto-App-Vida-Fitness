"""Precios por plan, texto de 'Información importante' y anuncios del dueño."""

from .. import config, db, tiempo

CLAVE_INFORMACION = 'informacion'


# ---- Precios ----

def cargar_precios():
    """Devuelve {plan: precio}. Los planes sin precio guardado usan el valor por defecto."""
    precios = dict(config.PRECIOS_POR_DEFECTO)
    with db.lectura() as conn:
        for fila in conn.execute("SELECT plan, precio FROM precios"):
            precios[fila['plan']] = fila['precio']
    return precios


def guardar_precios(precios):
    """Guarda el precio de cada plan ({plan: precio})."""
    with db.escritura() as conn:
        for plan, precio in precios.items():
            conn.execute(
                "INSERT INTO precios (plan, precio) VALUES (?, ?) "
                "ON CONFLICT(plan) DO UPDATE SET precio = excluded.precio",
                (plan, precio),
            )


def precio_de_plan(plan, conn=None):
    """Precio vigente de un plan (0 si el plan no existe). Se puede pasar una
    conexión abierta para leer dentro de una transacción en curso."""
    if conn is None:
        return cargar_precios().get(plan, 0)
    fila = conn.execute("SELECT precio FROM precios WHERE plan = ?", (plan,)).fetchone()
    if fila is not None:
        return fila['precio']
    return config.PRECIOS_POR_DEFECTO.get(plan, 0)


# ---- Información importante ----

def cargar_informacion():
    """Texto que ven los clientes en 'Información importante'."""
    with db.lectura() as conn:
        fila = conn.execute(
            "SELECT valor FROM ajustes WHERE clave = ?", (CLAVE_INFORMACION,)
        ).fetchone()
    return fila['valor'] if fila else config.INFO_IMPORTANTE_POR_DEFECTO


def guardar_informacion(texto):
    with db.escritura() as conn:
        conn.execute(
            "INSERT INTO ajustes (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (CLAVE_INFORMACION, texto),
        )


# ---- Anuncios ----

def cargar_anuncios():
    """Lista de anuncios, del más nuevo al más viejo: [{'id', 'fecha', 'texto'}]."""
    with db.lectura() as conn:
        filas = conn.execute("SELECT id, fecha, texto FROM anuncios ORDER BY id DESC").fetchall()
    return [dict(f) for f in filas]


def agregar_anuncio(texto):
    with db.escritura() as conn:
        conn.execute(
            "INSERT INTO anuncios (fecha, texto) VALUES (?, ?)", (str(tiempo.hoy()), texto)
        )


def eliminar_anuncio(anuncio_id):
    with db.escritura() as conn:
        conn.execute("DELETE FROM anuncios WHERE id = ?", (anuncio_id,))
