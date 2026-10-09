"""Libro contable: ingresos (cuotas, bebidas...) y egresos (gastos)."""

from contextlib import contextmanager

from .. import config, db, tiempo


@contextmanager
def _conexion(conn):
    """Usa la conexión recibida (dentro de una transacción en curso) o abre una de escritura."""
    if conn is not None:
        yield conn
    else:
        with db.escritura() as nueva:
            yield nueva


def registrar_movimiento(tipo, categoria, descripcion, monto, dni_cliente=None, conn=None):
    """Agrega un movimiento. 'tipo' es 'ingreso' o 'egreso'.

    Si se pasa 'conn', se registra dentro de esa transacción (así un pago y su
    asiento contable se guardan juntos o no se guardan)."""
    with _conexion(conn) as c:
        c.execute(
            "INSERT INTO movimientos (fecha, tipo, categoria, descripcion, monto, dni_cliente) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(tiempo.hoy()), tipo, categoria, descripcion, monto, dni_cliente),
        )


def eliminar_movimiento(movimiento_id):
    with db.escritura() as conn:
        conn.execute("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))


def cargar_movimientos():
    """Todos los movimientos, del más viejo al más nuevo."""
    with db.lectura() as conn:
        filas = conn.execute("SELECT * FROM movimientos ORDER BY id").fetchall()
    return [dict(f) for f in filas]


def ultimos_movimientos(limite=50):
    """Los más recientes primero (por fecha y luego por id)."""
    with db.lectura() as conn:
        filas = conn.execute(
            "SELECT * FROM movimientos ORDER BY fecha DESC, id DESC LIMIT ?", (limite,)
        ).fetchall()
    return [dict(f) for f in filas]


def resumen_mensual():
    """Ingresos, egresos y neto de cada mes, del más reciente al más viejo."""
    with db.lectura() as conn:
        filas = conn.execute(
            "SELECT substr(fecha, 1, 7) AS mes, "
            "       SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE 0 END) AS ingresos, "
            "       SUM(CASE WHEN tipo = 'egreso'  THEN monto ELSE 0 END) AS egresos "
            "FROM movimientos WHERE length(fecha) >= 7 GROUP BY mes ORDER BY mes DESC"
        ).fetchall()
    resultado = []
    for fila in filas:
        try:
            anio, mes = fila['mes'].split('-')
            nombre_mes = f"{config.MESES_ES[int(mes)]} {anio}"
        except (ValueError, IndexError):
            continue
        resultado.append({
            "mes": nombre_mes,
            "ingresos": fila['ingresos'],
            "egresos": fila['egresos'],
            "neto": fila['ingresos'] - fila['egresos'],
        })
    return resultado
