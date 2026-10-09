import unittest

from gimnasio import config
from gimnasio.datos import ajustes, auditoria, contabilidad
from tests.base import BaseConDatos


class TestContabilidad(BaseConDatos):
    def test_registrar_y_eliminar(self):
        self.fijar_hoy(2026, 10, 8)
        contabilidad.registrar_movimiento('ingreso', 'Bebidas', 'Venta', 1500)
        contabilidad.registrar_movimiento('egreso', 'Luz', 'Factura', 4000)
        mov = contabilidad.cargar_movimientos()
        self.assertEqual([m['categoria'] for m in mov], ['Bebidas', 'Luz'])
        self.assertEqual(mov[0]['fecha'], '2026-10-08')
        contabilidad.eliminar_movimiento(mov[0]['id'])
        self.assertEqual([m['categoria'] for m in contabilidad.cargar_movimientos()], ['Luz'])

    def test_tipo_invalido_se_rechaza(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            contabilidad.registrar_movimiento('regalo', 'x', 'x', 1)

    def test_resumen_mensual(self):
        for fecha, tipo, monto in [('2026-09-10', 'ingreso', 1000), ('2026-10-01', 'ingreso', 5000),
                                   ('2026-10-15', 'egreso', 2000), ('2026-10-20', 'ingreso', 500)]:
            self.fijar_hoy(*map(int, fecha.split('-')))
            contabilidad.registrar_movimiento(tipo, 'x', 'x', monto)
        resumen = contabilidad.resumen_mensual()
        self.assertEqual([r['mes'] for r in resumen], ['Octubre 2026', 'Septiembre 2026'])
        self.assertEqual((resumen[0]['ingresos'], resumen[0]['egresos'], resumen[0]['neto']), (5500, 2000, 3500))
        self.assertEqual(resumen[1]['neto'], 1000)

    def test_resumen_vacio(self):
        self.assertEqual(contabilidad.resumen_mensual(), [])

    def test_ultimos_movimientos_mas_nuevos_primero_y_con_limite(self):
        for dia in (1, 2, 3):
            self.fijar_hoy(2026, 10, dia)
            contabilidad.registrar_movimiento('ingreso', f'dia{dia}', 'x', 1)
        self.assertEqual([m['categoria'] for m in contabilidad.ultimos_movimientos(2)], ['dia3', 'dia2'])


class TestAjustes(BaseConDatos):
    def test_precios_por_defecto(self):
        self.assertEqual(ajustes.cargar_precios(), config.PRECIOS_POR_DEFECTO)
        self.assertEqual(ajustes.precio_de_plan('Todos los días'), 22000)
        self.assertEqual(ajustes.precio_de_plan('plan que no existe'), 0)

    def test_guardar_precios_y_completar_con_defecto(self):
        ajustes.guardar_precios({'Todos los días': 25000})
        precios = ajustes.cargar_precios()
        self.assertEqual(precios['Todos los días'], 25000)
        self.assertEqual(precios['2 veces por semana'], 15000)
        ajustes.guardar_precios({'Todos los días': 26000})  # vuelve a guardar sin duplicar
        self.assertEqual(ajustes.precio_de_plan('Todos los días'), 26000)

    def test_informacion(self):
        self.assertEqual(ajustes.cargar_informacion(), config.INFO_IMPORTANTE_POR_DEFECTO)
        ajustes.guardar_informacion('Abrimos a las 8')
        self.assertEqual(ajustes.cargar_informacion(), 'Abrimos a las 8')
        ajustes.guardar_informacion('Abrimos a las 9')
        self.assertEqual(ajustes.cargar_informacion(), 'Abrimos a las 9')

    def test_anuncios_del_mas_nuevo_al_mas_viejo(self):
        self.fijar_hoy(2026, 10, 8)
        ajustes.agregar_anuncio('Primero')
        ajustes.agregar_anuncio('Segundo')
        anuncios = ajustes.cargar_anuncios()
        self.assertEqual([a['texto'] for a in anuncios], ['Segundo', 'Primero'])
        self.assertEqual(anuncios[0]['fecha'], '2026-10-08')
        ajustes.eliminar_anuncio(anuncios[0]['id'])
        self.assertEqual([a['texto'] for a in ajustes.cargar_anuncios()], ['Primero'])


class TestAuditoria(BaseConDatos):
    def test_registrar_y_listar(self):
        auditoria.registrar('Ana', 'Pago registrado', 'DNI 123')
        auditoria.registrar('Luis', 'Cliente eliminado')
        ultimas = auditoria.ultimas()
        self.assertEqual([a['accion'] for a in ultimas], ['Cliente eliminado', 'Pago registrado'])
        self.assertEqual(ultimas[1]['actor'], 'Ana')
        self.assertIn('-03:00', ultimas[0]['fecha_hora'])  # hora de Argentina
        self.assertEqual(len(auditoria.ultimas(1)), 1)

    def test_sin_actor(self):
        auditoria.registrar('', 'Algo')
        self.assertEqual(auditoria.ultimas()[0]['actor'], '(desconocido)')

    def test_un_fallo_no_rompe_la_accion(self):
        from unittest import mock
        from gimnasio import db
        with mock.patch.object(db, 'escritura', side_effect=RuntimeError('base caída')):
            auditoria.registrar('Ana', 'Algo')  # no debe lanzar


if __name__ == '__main__':
    unittest.main()
