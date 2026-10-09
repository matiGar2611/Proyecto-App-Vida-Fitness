import hashlib
import io
import os
import unittest
from unittest import mock

from gimnasio import config, seguridad
from tests.base import BaseConDatos


class TestContrasenas(BaseConDatos):
    def test_hash_y_verificacion(self):
        salt, hash_val = seguridad.hash_password('clave-larga-1')
        self.assertTrue(hash_val.startswith('pbkdf2_sha256$'))
        self.assertTrue(seguridad.verificar_password('clave-larga-1', salt, hash_val))
        self.assertFalse(seguridad.verificar_password('otra', salt, hash_val))

    def test_el_salt_hace_distintos_los_hashes(self):
        self.assertNotEqual(seguridad.hash_password('igual')[1], seguridad.hash_password('igual')[1])

    def test_acepta_el_formato_viejo_sha256(self):
        viejo = hashlib.sha256(('sal' + 'miclave').encode()).hexdigest()
        self.assertTrue(seguridad.verificar_password('miclave', 'sal', viejo))
        self.assertFalse(seguridad.verificar_password('otra', 'sal', viejo))
        self.assertTrue(seguridad.necesita_rehash(viejo))

    def test_rehash_segun_iteraciones(self):
        _, hash_val = seguridad.hash_password('x')
        self.assertFalse(seguridad.necesita_rehash(hash_val))
        with mock.patch.object(seguridad, 'PBKDF2_ITERACIONES', 5000):
            self.assertTrue(seguridad.necesita_rehash(hash_val))

    def test_datos_corruptos_no_rompen(self):
        self.assertFalse(seguridad.verificar_password('x', 'sal', 'pbkdf2_sha256$basura'))
        self.assertFalse(seguridad.verificar_password('x', 'sal', 'pbkdf2_sha256$abc$def'))
        self.assertFalse(seguridad.verificar_password(None, 'sal', 'hash'))
        self.assertTrue(seguridad.necesita_rehash(None))

    def test_gastar_tiempo_no_falla(self):
        seguridad.gastar_tiempo_de_verificacion('lo que sea')


class TestLimiteDeIntentos(BaseConDatos):
    def test_bloquea_tras_los_intentos_maximos(self):
        for _ in range(config.MAX_INTENTOS_LOGIN - 1):
            seguridad.registrar_fallo('cliente:1')
        self.assertEqual(seguridad.segundos_de_bloqueo('cliente:1'), 0)
        seguridad.registrar_fallo('cliente:1')
        espera = seguridad.segundos_de_bloqueo('cliente:1')
        self.assertTrue(0 < espera <= config.SEGUNDOS_BLOQUEO_LOGIN + 1)

    def test_otra_cuenta_no_se_bloquea(self):
        for _ in range(config.MAX_INTENTOS_LOGIN):
            seguridad.registrar_fallo('cliente:1')
        self.assertEqual(seguridad.segundos_de_bloqueo('cliente:2'), 0)

    def test_se_desbloquea_con_login_correcto(self):
        for _ in range(config.MAX_INTENTOS_LOGIN):
            seguridad.registrar_fallo('admin:x')
        seguridad.limpiar_fallos('admin:x')
        self.assertEqual(seguridad.segundos_de_bloqueo('admin:x'), 0)

    def test_los_fallos_viejos_expiran(self):
        with mock.patch('time.time', return_value=1000.0):
            for _ in range(config.MAX_INTENTOS_LOGIN):
                seguridad.registrar_fallo('admin:y')
            self.assertGreater(seguridad.segundos_de_bloqueo('admin:y'), 0)
        with mock.patch('time.time', return_value=1000.0 + config.SEGUNDOS_BLOQUEO_LOGIN + 1):
            self.assertEqual(seguridad.segundos_de_bloqueo('admin:y'), 0)

    def test_texto_de_bloqueo(self):
        self.assertIn('2 minuto', seguridad.texto_bloqueo(61))


class TestSanitizarHtml(unittest.TestCase):
    def test_deja_el_formato_simple(self):
        self.assertEqual(seguridad.sanitizar_html('<b>Hola</b> <i>mundo</i>'), '<b>Hola</b> <i>mundo</i>')
        self.assertEqual(seguridad.sanitizar_html('<ul><li>a</li><li>b</li></ul>'),
                         '<ul><li>a</li><li>b</li></ul>')

    def test_elimina_scripts_y_eventos(self):
        sucio = '<b>Hola</b><script>alert(1)</script><img src=x onerror=alert(2)><div onclick="x()">ok</div>'
        limpio = seguridad.sanitizar_html(sucio)
        for peligroso in ('script', 'alert', 'onerror', 'onclick', '<img'):
            self.assertNotIn(peligroso, limpio)
        self.assertIn('<b>Hola</b>', limpio)
        self.assertIn('<div>ok</div>', limpio)

    def test_quita_links_y_atributos(self):
        self.assertEqual(
            seguridad.sanitizar_html('<a href="javascript:alert(1)">link</a><p style="x">ok</p>'),
            'link<p>ok</p>')

    def test_descarta_contenido_de_iframe_style_svg(self):
        for etiqueta in ('iframe', 'style', 'svg', 'object', 'embed'):
            self.assertEqual(seguridad.sanitizar_html(f'a<{etiqueta}>peligro</{etiqueta}>b'), 'ab')

    def test_cierra_etiquetas_abiertas(self):
        self.assertEqual(seguridad.sanitizar_html('<ul><li>a</li><li>b'), '<ul><li>a</li><li>b</li></ul>')

    def test_escapa_texto_suelto(self):
        self.assertEqual(seguridad.sanitizar_html('a < b & c'), 'a &lt; b &amp; c')

    def test_vacio(self):
        self.assertEqual(seguridad.sanitizar_html(''), '')
        self.assertEqual(seguridad.sanitizar_html(None), '')


class TestCsvSeguro(unittest.TestCase):
    def test_neutraliza_formulas(self):
        self.assertEqual(seguridad.celda_csv('=SUMA(A1)'), "'=SUMA(A1)")
        for inicio in ('+', '-', '@'):
            self.assertTrue(seguridad.celda_csv(inicio + 'x').startswith("'"))
        self.assertEqual(seguridad.celda_csv('Ana'), 'Ana')
        self.assertEqual(seguridad.celda_csv(15), 15)

    def test_escritor(self):
        buffer = io.StringIO()
        seguridad.EscritorCSVSeguro(buffer).writerow(['=x', 'ok', 3])
        self.assertEqual(buffer.getvalue().strip(), "'=x;ok;3")


class TestStorageSecret(BaseConDatos):
    def test_usa_la_variable_de_entorno(self):
        os.environ['STORAGE_SECRET'] = 'x' * 20
        self.assertEqual(seguridad.obtener_storage_secret(), 'x' * 20)

    def test_ignora_una_variable_demasiado_corta(self):
        os.environ['STORAGE_SECRET'] = 'corta'
        self.assertGreaterEqual(len(seguridad.obtener_storage_secret()), 32)

    def test_genera_y_persiste_si_no_hay_variable(self):
        primera = seguridad.obtener_storage_secret()
        self.assertGreaterEqual(len(primera), 32)
        self.assertEqual(primera, seguridad.obtener_storage_secret())
        ruta = os.path.join(self.carpeta, '.storage_secret')
        if os.name != 'nt':  # Windows no maneja permisos tipo Linux
            self.assertEqual(oct(os.stat(ruta).st_mode)[-3:], '600')


if __name__ == '__main__':
    unittest.main()
