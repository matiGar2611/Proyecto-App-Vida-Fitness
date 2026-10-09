import unittest

from gimnasio import seguridad
from gimnasio.datos import ajustes, clientes, contabilidad
from tests.base import BaseConDatos


class TestClientes(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.fijar_hoy(2026, 10, 8)

    def test_alta_con_valores_iniciales(self):
        dni = self.nuevo_cliente()
        c = clientes.buscar_cliente_por_dni(dni)
        self.assertEqual(c['nombre'], 'Ana Pérez')
        self.assertEqual(c['fecha_inicio'], '2026-10-08')
        self.assertEqual(c['fecha_vencimiento'], '2026-11-07')  # a 30 días
        self.assertEqual(c['fecha_ultimo_pago'], '2026-10-08')
        self.assertTrue(c['activo'])
        self.assertEqual(c['rutina'], '')
        self.assertEqual(c['saldo_pendiente'], 0)

    def test_alta_registra_el_primer_pago_en_el_historial(self):
        self.nuevo_cliente(plan='Todos los días')
        historial = clientes.buscar_cliente_por_dni('12345678')['historial']
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]['monto'], 22000)
        self.assertEqual(historial[0]['vencimiento'], '2026-11-07')

    def test_el_primer_pago_usa_el_precio_vigente(self):
        ajustes.guardar_precios({'Todos los días': 30000})
        self.nuevo_cliente()
        self.assertEqual(clientes.buscar_cliente_por_dni('12345678')['historial'][0]['monto'], 30000)

    def test_alta_registra_el_primer_pago_tambien_en_la_contabilidad(self):
        dni = self.nuevo_cliente()
        mov = contabilidad.cargar_movimientos()
        self.assertEqual(len(mov), 1)
        self.assertEqual((mov[0]['tipo'], mov[0]['categoria'], mov[0]['monto'], mov[0]['dni_cliente']),
                         ('ingreso', 'Cuota', 22000, dni))
        self.assertIn('Ana Pérez', mov[0]['descripcion'])
        self.assertEqual(mov[0]['fecha'], '2026-10-08')

    def test_alta_con_pago_parcial_deja_saldo_pendiente(self):
        self.assertTrue(clientes.agregar_cliente('12345678', 'Ana', '2615551234', 'Todos los días', '1990-01-01',
                                                 monto_abonado=10000))
        c = clientes.buscar_cliente_por_dni('12345678')
        self.assertEqual(c['saldo_pendiente'], 12000)
        self.assertEqual((c['historial'][0]['monto'], c['historial'][0]['saldo_pendiente_tras_pago']), (10000, 12000))
        self.assertEqual(contabilidad.cargar_movimientos()[0]['monto'], 10000)

    def test_alta_pagando_de_mas_no_genera_deuda(self):
        clientes.agregar_cliente('12345678', 'Ana', '2615551234', 'Todos los días', '1990-01-01', monto_abonado=30000)
        self.assertEqual(clientes.buscar_cliente_por_dni('12345678')['saldo_pendiente'], 0)

    def test_alta_con_monto_invalido_no_guarda_nada(self):
        for monto in (0, -5):
            with self.assertRaises(ValueError):
                clientes.agregar_cliente('12345678', 'Ana', '2615551234', 'Todos los días', '1990-01-01',
                                         monto_abonado=monto)
        self.assertEqual(clientes.cargar_clientes(), [])
        self.assertEqual(contabilidad.cargar_movimientos(), [])

    def test_alta_con_dni_repetido_no_duplica_el_asiento(self):
        self.nuevo_cliente()
        self.assertFalse(clientes.agregar_cliente('12345678', 'Otra', '2615550000', 'Todos los días', '2000-01-01'))
        self.assertEqual(len(contabilidad.cargar_movimientos()), 1)

    def test_el_alta_es_una_sola_transaccion(self):
        from unittest import mock
        with mock.patch.object(contabilidad, 'registrar_movimiento', side_effect=RuntimeError('falla')):
            with self.assertRaises(RuntimeError):
                clientes.agregar_cliente('12345678', 'Ana', '2615551234', 'Todos los días', '1990-01-01')
        self.assertEqual(clientes.cargar_clientes(), [])  # ni el cliente ni su pago quedaron guardados

    def test_lo_cobrado_coincide_con_la_contabilidad(self):
        from gimnasio.datos import pagos
        from gimnasio.servicios import estadisticas
        self.nuevo_cliente('11111111')
        self.nuevo_cliente('22222222', plan='2 veces por semana')
        pagos.registrar_pago('11111111', '2026-12-08', 15000)
        pagos.abonar_deuda('11111111', 2000)
        cuotas = sum(m['monto'] for m in contabilidad.cargar_movimientos() if m['categoria'].startswith('Cuota'))
        # "Cobrado este mes" suma los pagos; el abono de saldo no es un pago nuevo del historial.
        self.assertEqual(estadisticas.ingresos_cobrados_mes_actual() + 2000, cuotas)

    def test_contrasena_inicial_es_el_dni_y_debe_cambiarse(self):
        self.nuevo_cliente(dni='11112222')
        c = clientes.buscar_cliente_por_dni('11112222')
        self.assertTrue(c['debe_cambiar_password'])
        self.assertTrue(clientes.verificar_password_cliente(c, '11112222'))
        self.assertFalse(clientes.verificar_password_cliente(c, 'otra'))
        self.assertNotIn('11112222', c['password_hash'])

    def test_dni_duplicado_no_se_agrega(self):
        self.nuevo_cliente()
        self.assertFalse(clientes.agregar_cliente('12345678', 'Otra', '2615550000', 'Todos los días', '2000-01-01'))
        self.assertEqual(len(clientes.cargar_clientes()), 1)
        self.assertTrue(clientes.dni_existe('12345678'))
        self.assertFalse(clientes.dni_existe('00000000'))

    def test_buscar_inexistente(self):
        self.assertIsNone(clientes.buscar_cliente_por_dni('99999999'))

    def test_actualizar_datos(self):
        dni = self.nuevo_cliente()
        self.assertTrue(clientes.actualizar_cliente(dni, 'Ana Gómez', '2619999999', '2 veces por semana', '1991-01-01'))
        c = clientes.buscar_cliente_por_dni(dni)
        self.assertEqual((c['nombre'], c['telefono'], c['plan'], c['fecha_nacimiento']),
                         ('Ana Gómez', '2619999999', '2 veces por semana', '1991-01-01'))
        self.assertEqual(c['fecha_vencimiento'], '2026-11-07')  # no toca las fechas de pago
        self.assertFalse(clientes.actualizar_cliente('00000000', 'x', 'x', 'x', 'x'))

    def test_eliminar_borra_tambien_el_historial(self):
        dni = self.nuevo_cliente()
        self.assertTrue(clientes.eliminar_cliente(dni))
        self.assertIsNone(clientes.buscar_cliente_por_dni(dni))
        from gimnasio import db
        with db.lectura() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM pagos").fetchone()[0], 0)
        self.assertFalse(clientes.eliminar_cliente(dni))

    def test_rutina_se_guarda_limpia(self):
        dni = self.nuevo_cliente()
        clientes.actualizar_rutina(dni, '<b>Piernas</b><script>alert(1)</script><div onclick="x()">3x10</div>')
        rutina = clientes.buscar_cliente_por_dni(dni)['rutina']
        self.assertEqual(rutina, '<b>Piernas</b><div>3x10</div>')

    def test_cambiar_contrasena(self):
        dni = self.nuevo_cliente()
        self.assertTrue(clientes.cambiar_password_cliente(dni, 'nueva-clave'))
        c = clientes.buscar_cliente_por_dni(dni)
        self.assertFalse(c['debe_cambiar_password'])
        self.assertTrue(clientes.verificar_password_cliente(c, 'nueva-clave'))
        self.assertFalse(clientes.verificar_password_cliente(c, dni))

    def test_restablecer_contrasena(self):
        dni = self.nuevo_cliente()
        clientes.cambiar_password_cliente(dni, 'nueva-clave')
        self.assertTrue(clientes.restablecer_password_cliente(dni))
        c = clientes.buscar_cliente_por_dni(dni)
        self.assertTrue(c['debe_cambiar_password'])
        self.assertTrue(clientes.verificar_password_cliente(c, dni))
        self.assertFalse(clientes.cambiar_password_cliente('00000000', 'x'))

    def test_cargar_clientes_con_y_sin_historial(self):
        self.nuevo_cliente('11111111')
        self.nuevo_cliente('22222222')
        self.assertEqual([c['dni'] for c in clientes.cargar_clientes()], ['11111111', '22222222'])
        self.assertNotIn('historial', clientes.cargar_clientes()[0])
        self.assertEqual(len(clientes.cargar_clientes(con_historial=True)[1]['historial']), 1)

    def test_formato_viejo_de_hash_se_actualiza(self):
        import hashlib
        from gimnasio import db
        dni = self.nuevo_cliente()
        viejo = hashlib.sha256(('sal' + 'miclave').encode()).hexdigest()
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET password_hash = ?, password_salt = 'sal' WHERE dni = ?", (viejo, dni))
        c = clientes.buscar_cliente_por_dni(dni)
        self.assertTrue(clientes.verificar_password_cliente(c, 'miclave'))
        self.assertTrue(seguridad.necesita_rehash(c['password_hash']))


if __name__ == '__main__':
    unittest.main()
