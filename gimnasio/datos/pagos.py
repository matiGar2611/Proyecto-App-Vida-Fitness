"""Pagos de cuotas y abonos de saldo pendiente.

Cada operación guarda el cambio en el cliente, su historial y el asiento
contable dentro de UNA sola transacción: o se guarda todo, o nada.
"""

from .. import db, tiempo
from . import ajustes, contabilidad


def registrar_pago(dni, nueva_fecha_vencimiento, monto_abonado):
    """Registra el pago de una cuota (total o parcial).

    Actualiza el último pago y el vencimiento, reactiva al cliente, ajusta su
    saldo pendiente (si pagó menos que el precio del plan, la diferencia queda
    como deuda; si pagó de más, se descuenta de deuda anterior), agrega el pago
    al historial y lo anota como ingreso. Devuelve False si el cliente no existe."""
    with db.escritura() as conn:
        cliente = conn.execute(
            "SELECT nombre, plan, saldo_pendiente FROM clientes WHERE dni = ?", (dni,)
        ).fetchone()
        if cliente is None:
            return False

        precio_plan = ajustes.precio_de_plan(cliente['plan'], conn=conn)
        nueva_deuda = max(0, cliente['saldo_pendiente'] + (precio_plan - monto_abonado))
        hoy = str(tiempo.hoy())

        conn.execute(
            "UPDATE clientes SET saldo_pendiente = ?, fecha_ultimo_pago = ?, "
            "fecha_vencimiento = ?, activo = 1 WHERE dni = ?",
            (nueva_deuda, hoy, nueva_fecha_vencimiento, dni),
        )
        conn.execute(
            "INSERT INTO pagos (dni, fecha, monto, vencimiento, saldo_pendiente_tras_pago) "
            "VALUES (?, ?, ?, ?, ?)",
            (dni, hoy, monto_abonado, nueva_fecha_vencimiento, nueva_deuda),
        )
        contabilidad.registrar_movimiento(
            "ingreso", "Cuota", f"Pago de cuota - {cliente['nombre']} (DNI {dni})",
            monto_abonado, dni, conn=conn,
        )
    return True


def abonar_deuda(dni, monto):
    """Abona contra el saldo pendiente, sin tocar el vencimiento.

    Solo se aplica (y se anota como ingreso) hasta el monto de la deuda real.
    Devuelve True si se aplicó algún abono, False si no había nada para aplicar."""
    with db.escritura() as conn:
        cliente = conn.execute(
            "SELECT nombre, saldo_pendiente FROM clientes WHERE dni = ?", (dni,)
        ).fetchone()
        if cliente is None:
            return False

        aplicado = min(monto, cliente['saldo_pendiente'])
        if aplicado <= 0:
            return False

        conn.execute(
            "UPDATE clientes SET saldo_pendiente = ? WHERE dni = ?",
            (cliente['saldo_pendiente'] - aplicado, dni),
        )
        contabilidad.registrar_movimiento(
            "ingreso", "Cuota (saldo)",
            f"Abono de saldo pendiente - {cliente['nombre']} (DNI {dni})",
            aplicado, dni, conn=conn,
        )
    return True
