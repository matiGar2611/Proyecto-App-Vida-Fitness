import unittest
from datetime import timedelta
from unittest import mock

from gimnasio import config, tiempo


class TestTiempo(unittest.TestCase):
    def test_ahora_usa_hora_de_argentina(self):
        self.assertEqual(tiempo.ahora().utcoffset(), timedelta(hours=-3))

    def test_sin_base_de_zonas_usa_utc_menos_3(self):
        tiempo._zona.cache_clear()
        self.addCleanup(tiempo._zona.cache_clear)
        with mock.patch.object(config, 'ZONA_HORARIA', 'Zona/Inexistente'):
            self.assertEqual(tiempo.ahora().utcoffset(), timedelta(hours=-3))

    def test_parsear_fecha(self):
        self.assertEqual(str(tiempo.parsear_fecha('2026-10-08')), '2026-10-08')
        for malo in (None, '', 'hola', '2026-13-45', 5):
            self.assertIsNone(tiempo.parsear_fecha(malo))

    def test_formatear_fecha(self):
        self.assertEqual(tiempo.formatear_fecha('2026-10-08'), '08/10/2026')
        self.assertEqual(tiempo.formatear_fecha(None), '(sin fecha)')

    def test_formatear_moneda(self):
        self.assertEqual(tiempo.formatear_moneda(15000), '$15.000')
        self.assertEqual(tiempo.formatear_moneda(1234567.4), '$1.234.567')
        self.assertEqual(tiempo.formatear_moneda(0), '$0')


if __name__ == '__main__':
    unittest.main()
