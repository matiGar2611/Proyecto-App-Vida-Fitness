import unittest

from gimnasio import db
from gimnasio.datos import ajustes, clientes, contabilidad, pagos
from tests.base import BaseConDatos


class TestPagos(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.fijar_hoy(2026, 10, 8)
        self.dni = self.nuevo_cliente(plan='Todos los días')  # $22.000

    def cliente(self):
        return clientes.buscar_cliente_por_dni(self.dni)

    def test_pago_completo(self):
        self.assertTrue(pagos.registrar_pago(self.dni, '2026-12-08', 22000))
        c = self.cliente()
        self.assertEqual(c['saldo_pendiente'], 0)
        self.assertEqual(c['fecha_vencimiento'], '2026-12-08')
        self.assertEqual(c['fecha_ultimo_pago'], '2026-10-08')
        self.assertEqual(len(c['historial']), 2)
        self.assertEqual(c['historial'][-1]['monto'], 22000)

    def test_pago_parcial_deja_deuda(self):
        pagos.registrar_pago(self.dni, '2026-12-08', 15000)
        c = self.cliente()
        self.assertEqual(c['saldo_pendiente'], 7000)
        self.assertEqual(c['historial'][-1]['saldo_pendiente_tras_pago'], 7000)

    def test_la_deuda_se_acumula_y_se_compensa_pagando_de_mas(self):
        pagos.registrar_pago(self.dni, '2026-12-08', 20000)   # debe 2.000
        pagos.registrar_pago(self.dni, '2027-01-08', 20000)   # debe 4.000
        self.assertEqual(self.cliente()['saldo_pendiente'], 4000)
        pagos.registrar_pago(self.dni, '2027-02-08', 30000)   # paga 8.000 de más -> 0
        self.assertEqual(self.cliente()['saldo_pendiente'], 0)

    def test_el_pago_reactiva_al_cliente(self):
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET activo = 0 WHERE dni = ?", (self.dni,))
        pagos.registrar_pago(self.dni, '2026-12-08', 22000)
        self.assertTrue(self.cliente()['activo'])

    def test_el_pago_se_anota_como_ingreso(self):
        pagos.registrar_pago(self.dni, '2026-12-08', 22000)
        mov = contabilidad.cargar_movimientos()
        self.assertEqual(len(mov), 2)  # el del alta y este pago
        self.assertEqual((mov[1]['tipo'], mov[1]['categoria'], mov[1]['monto'], mov[1]['dni_cliente']),
                         ('ingreso', 'Cuota', 22000, self.dni))
        self.assertIn('Ana Pérez', mov[1]['descripcion'])

    def test_cliente_inexistente(self):
        self.assertFalse(pagos.registrar_pago('00000000', '2026-12-08', 1000))
        self.assertEqual(len(contabilidad.cargar_movimientos()), 1)  # solo el del alta

    def test_usa_el_precio_vigente_del_plan(self):
        ajustes.guardar_precios({'Todos los días': 30000})
        pagos.registrar_pago(self.dni, '2026-12-08', 22000)
        self.assertEqual(self.cliente()['saldo_pendiente'], 8000)

    def test_abonar_deuda(self):
        pagos.registrar_pago(self.dni, '2026-12-08', 15000)  # debe 7.000
        self.assertTrue(pagos.abonar_deuda(self.dni, 3000))
        c = self.cliente()
        self.assertEqual(c['saldo_pendiente'], 4000)
        self.assertEqual(c['fecha_vencimiento'], '2026-12-08')  # no toca el vencimiento
        mov = contabilidad.cargar_movimientos()[-1]
        self.assertEqual((mov['categoria'], mov['monto']), ('Cuota (saldo)', 3000))

    def test_abonar_de_mas_solo_aplica_lo_que_se_debe(self):
        pagos.registrar_pago(self.dni, '2026-12-08', 15000)  # debe 7.000
        self.assertTrue(pagos.abonar_deuda(self.dni, 50000))
        self.assertEqual(self.cliente()['saldo_pendiente'], 0)
        self.assertEqual(contabilidad.cargar_movimientos()[-1]['monto'], 7000)

    def test_abonar_sin_deuda_no_hace_nada(self):
        antes = len(contabilidad.cargar_movimientos())
        self.assertFalse(pagos.abonar_deuda(self.dni, 1000))
        self.assertFalse(pagos.abonar_deuda('00000000', 1000))
        self.assertEqual(len(contabilidad.cargar_movimientos()), antes)

    def test_si_algo_falla_no_se_guarda_nada(self):
        """El pago y su asiento contable son una sola transacción."""
        from unittest import mock
        with mock.patch.object(contabilidad, 'registrar_movimiento', side_effect=RuntimeError('falla')):
            with self.assertRaises(RuntimeError):
                pagos.registrar_pago(self.dni, '2026-12-08', 15000)
        c = self.cliente()
        self.assertEqual(c['saldo_pendiente'], 0)
        self.assertEqual(c['fecha_vencimiento'], '2026-11-07')
        self.assertEqual(len(c['historial']), 1)


if __name__ == '__main__':
    unittest.main()
