import unittest

from gimnasio import db
from gimnasio.datos import ajustes, clientes, pagos
from gimnasio.servicios import estadisticas
from tests.base import BaseConDatos


def poner_vencimiento(dni, fecha):
    with db.escritura() as conn:
        conn.execute("UPDATE clientes SET fecha_vencimiento = ? WHERE dni = ?", (fecha, dni))


class TestVencimientos(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.fijar_hoy(2026, 10, 8)

    def test_esta_vencido_y_dias(self):
        self.assertFalse(estadisticas.esta_vencido({'fecha_vencimiento': '2026-10-08'}))  # hoy no está vencido
        self.assertTrue(estadisticas.esta_vencido({'fecha_vencimiento': '2026-10-07'}))
        self.assertFalse(estadisticas.esta_vencido({'fecha_vencimiento': None}))
        self.assertEqual(estadisticas.dias_para_vencimiento({'fecha_vencimiento': '2026-10-12'}), 4)
        self.assertEqual(estadisticas.dias_para_vencimiento({'fecha_vencimiento': '2026-10-05'}), -3)
        self.assertEqual(estadisticas.dias_para_vencimiento({'fecha_vencimiento': 'mal'}), 0)

    def test_proximos_vencimientos(self):
        for dni, fecha in [('1', '2026-10-08'), ('2', '2026-10-12'), ('3', '2026-10-15'),
                           ('4', '2026-10-16'), ('5', '2026-10-01')]:
            self.nuevo_cliente(dni, f'Cliente {dni}')
            poner_vencimiento(dni, fecha)
        resultado = estadisticas.proximos_vencimientos(7)
        self.assertEqual([r['dni'] for r in resultado], ['1', '2', '3'])  # ni el vencido ni el lejano
        self.assertTrue(resultado[0]['vence_hoy'])
        self.assertEqual(resultado[1]['dias'], 4)
        self.assertEqual(resultado[1]['fecha'], '12/10/2026')

    def test_contadores(self):
        self.nuevo_cliente('1')
        self.nuevo_cliente('2')
        poner_vencimiento('2', '2026-09-01')
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET activo = 0 WHERE dni = '1'")
        self.assertEqual(estadisticas.contadores(), (1, 1))


class TestCumpleanos(BaseConDatos):
    def test_proximos_cumpleanos(self):
        self.fijar_hoy(2026, 10, 8)
        for dni, nac in [('1', '1990-10-08'), ('2', '1985-10-20'), ('3', '2000-11-07'),
                         ('4', '1999-11-08'), ('5', '1970-10-07')]:
            self.nuevo_cliente(dni, f'C{dni}', nacimiento=nac)
        r = estadisticas.proximos_cumpleanos(30)
        self.assertEqual([x['dni'] for x in r], ['1', '2', '3'])  # 4 está a 31 días; 5 ya pasó este año
        self.assertTrue(r[0]['es_hoy'])
        self.assertEqual(r[1]['fecha'], '20/10')
        self.assertEqual(r[1]['dias_faltantes'], 12)

    def test_cumpleanos_que_cruza_el_anio(self):
        self.fijar_hoy(2026, 12, 20)
        self.nuevo_cliente('1', nacimiento='1990-01-05')
        self.assertEqual(estadisticas.proximos_cumpleanos(30)[0]['dias_faltantes'], 16)

    def test_29_de_febrero_en_anio_no_bisiesto(self):
        self.fijar_hoy(2027, 2, 20)
        self.nuevo_cliente('1', nacimiento='2000-02-29')
        r = estadisticas.proximos_cumpleanos(30)
        self.assertEqual((r[0]['fecha'], r[0]['dias_faltantes']), ('28/02', 8))

    def test_sin_fecha_de_nacimiento_se_ignora(self):
        self.fijar_hoy(2026, 10, 8)
        self.nuevo_cliente('1', nacimiento=None)
        self.assertEqual(estadisticas.proximos_cumpleanos(30), [])


class TestIngresos(BaseConDatos):
    def test_esperados_suman_el_plan_de_los_activos(self):
        self.fijar_hoy(2026, 10, 8)
        self.nuevo_cliente('1', plan='Todos los días')         # 22.000
        self.nuevo_cliente('2', plan='2 veces por semana')     # 15.000
        self.nuevo_cliente('3', plan='3 veces por semana')     # 18.000 (inactivo)
        with db.escritura() as conn:
            conn.execute("UPDATE clientes SET activo = 0 WHERE dni = '3'")
        self.assertEqual(estadisticas.ingresos_esperados_mensuales(), 37000)
        ajustes.guardar_precios({'Todos los días': 30000})
        self.assertEqual(estadisticas.ingresos_esperados_mensuales(), 45000)

    def test_cobrado_en_el_mes_actual(self):
        self.fijar_hoy(2026, 9, 30)
        self.nuevo_cliente('1', plan='Todos los días')   # alta en septiembre: $22.000
        self.fijar_hoy(2026, 10, 1)
        pagos.registrar_pago('1', '2026-11-01', 20000)
        self.fijar_hoy(2026, 10, 31)
        pagos.registrar_pago('1', '2026-12-01', 5000)
        self.assertEqual(estadisticas.ingresos_cobrados_mes_actual(), 25000)

    def test_cobrado_en_diciembre_cruza_de_anio(self):
        self.fijar_hoy(2026, 12, 15)
        self.nuevo_cliente('1')
        self.assertEqual(estadisticas.ingresos_cobrados_mes_actual(), 22000)
        self.fijar_hoy(2027, 1, 1)
        self.assertEqual(estadisticas.ingresos_cobrados_mes_actual(), 0)


class TestTablaYCsv(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.fijar_hoy(2026, 10, 8)
        self.nuevo_cliente('11111111', 'Ana Pérez', plan='Todos los días')
        self.nuevo_cliente('22222222', 'Luis Gómez', plan='2 veces por semana')
        self.nuevo_cliente('33333333', '=Peligro', plan='Todos los días')
        poner_vencimiento('22222222', '2026-09-01')

    def test_filtros(self):
        self.assertEqual(len(estadisticas.filtrar_clientes()), 3)
        self.assertEqual([c['dni'] for c in estadisticas.filtrar_clientes(solo_vencidos=True)], ['22222222'])
        self.assertEqual(len(estadisticas.filtrar_clientes(plan_filtro='Todos los días')), 2)
        self.assertEqual([c['dni'] for c in estadisticas.filtrar_clientes(busqueda='gómez')], ['22222222'])
        self.assertEqual([c['dni'] for c in estadisticas.filtrar_clientes(busqueda=' 1111 ')], ['11111111'])
        self.assertEqual(estadisticas.filtrar_clientes(busqueda='zzz'), [])

    def test_filas_formateadas_y_sin_contrasenas(self):
        pagos.registrar_pago('11111111', '2026-12-01', 10000)
        fila = [f for f in estadisticas.obtener_filas() if f['dni'] == '11111111'][0]
        self.assertEqual(fila['vencimiento'], '01/12/2026')
        self.assertEqual(fila['debe'], '$12.000')
        self.assertEqual(fila['activo'], 'Sí')
        self.assertEqual(fila['nacimiento'], '10/05/1990')
        self.assertEqual(estadisticas.obtener_filas(busqueda='Luis')[0]['debe'], '-')
        for fila in estadisticas.obtener_filas():
            self.assertFalse([k for k in fila if 'pass' in k.lower() or 'hash' in k.lower()])

    def test_csv(self):
        texto = estadisticas.exportar_clientes_csv()
        lineas = texto.strip().splitlines()
        self.assertEqual(len(lineas), 4)
        self.assertTrue(lineas[0].startswith('DNI;Nombre y Apellido'))
        self.assertIn("'=Peligro", texto)  # fórmula neutralizada
        self.assertNotIn('password', texto.lower())
        self.assertEqual(len(estadisticas.exportar_clientes_csv(solo_vencidos=True).strip().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
