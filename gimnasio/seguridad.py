"""Seguridad: contraseñas, límite de intentos de login, HTML y CSV seguros.

No depende de NiceGUI ni de la base de datos.
"""

import csv
import hashlib
import hmac
import html as html_lib
import os
import secrets
import threading
import time
from functools import lru_cache
from html.parser import HTMLParser

from . import config

# ------------------------------------------------------------
# Contraseñas
# ------------------------------------------------------------

PBKDF2_ITERACIONES = 600_000
PREFIJO_HASH = 'pbkdf2_sha256$'


def hash_password(password, salt=None):
    """Genera el hash PBKDF2-SHA256 de una contraseña combinada con un salt.

    Si no se pasa 'salt', genera uno nuevo aleatorio (alta de cuenta).
    Devuelve (salt, hash) donde el hash guarda también la cantidad de
    iteraciones usadas: 'pbkdf2_sha256$<iteraciones>$<hash>'."""
    if salt is None:
        salt = secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'), PBKDF2_ITERACIONES
    )
    return salt, f"{PREFIJO_HASH}{PBKDF2_ITERACIONES}${derivado.hex()}"


def verificar_password(password, salt, hash_val):
    """Compara una contraseña ingresada contra el hash guardado.

    Entiende el formato nuevo (PBKDF2) y también el viejo (SHA-256
    simple), para que las cuentas creadas antes sigan pudiendo entrar;
    después de un login correcto se las pasa al formato nuevo."""
    if not isinstance(password, str) or not isinstance(salt, str) or not isinstance(hash_val, str):
        return False
    if hash_val.startswith(PREFIJO_HASH):
        try:
            _, iteraciones, esperado = hash_val.split('$')
            derivado = hashlib.pbkdf2_hmac(
                'sha256', password.encode('utf-8'), salt.encode('utf-8'), int(iteraciones)
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(derivado.hex().encode('utf-8'), esperado.encode('utf-8'))
    viejo = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return hmac.compare_digest(viejo.encode('utf-8'), hash_val.encode('utf-8'))


def necesita_rehash(hash_val):
    """True si el hash guardado es del formato viejo o usa menos iteraciones que las actuales."""
    if not isinstance(hash_val, str) or not hash_val.startswith(PREFIJO_HASH):
        return True
    try:
        return int(hash_val.split('$')[1]) < PBKDF2_ITERACIONES
    except (IndexError, ValueError):
        return True


@lru_cache(maxsize=1)
def _hash_de_relleno():
    return hash_password(secrets.token_hex(8))


def gastar_tiempo_de_verificacion(password):
    """Hace el mismo trabajo que verificar una contraseña real. Se usa cuando el
    usuario o DNI no existe, para que tarde lo mismo en responder y no se pueda
    adivinar cuáles existen."""
    salt, hash_val = _hash_de_relleno()
    verificar_password(password, salt, hash_val)


# ------------------------------------------------------------
# Límite de intentos de login
# ------------------------------------------------------------

_intentos_fallidos = {}
_lock_intentos = threading.Lock()


def segundos_de_bloqueo(clave):
    """Si 'clave' (ej. 'cliente:12345678') acumuló demasiados intentos
    fallidos recientes, devuelve cuántos segundos faltan para poder
    reintentar. Si no está bloqueada, devuelve 0."""
    ahora = time.time()
    with _lock_intentos:
        recientes = [t for t in _intentos_fallidos.get(clave, [])
                     if ahora - t < config.SEGUNDOS_BLOQUEO_LOGIN]
        if recientes:
            _intentos_fallidos[clave] = recientes
        else:
            _intentos_fallidos.pop(clave, None)
        if len(recientes) >= config.MAX_INTENTOS_LOGIN:
            return int(config.SEGUNDOS_BLOQUEO_LOGIN - (ahora - recientes[-config.MAX_INTENTOS_LOGIN])) + 1
        return 0


def registrar_fallo(clave):
    """Anota un intento de login fallido para 'clave'."""
    ahora = time.time()
    with _lock_intentos:
        _intentos_fallidos.setdefault(clave, []).append(ahora)
        if len(_intentos_fallidos) > 5000:
            # Limpieza para que alguien probando miles de DNI al azar no llene la memoria.
            for k in list(_intentos_fallidos):
                if all(ahora - t >= config.SEGUNDOS_BLOQUEO_LOGIN for t in _intentos_fallidos[k]):
                    del _intentos_fallidos[k]


def limpiar_fallos(clave):
    """Borra los intentos fallidos de 'clave' (se llama tras un login correcto)."""
    with _lock_intentos:
        _intentos_fallidos.pop(clave, None)


def texto_bloqueo(segundos):
    """Mensaje para mostrar cuando un login está temporalmente bloqueado."""
    minutos = segundos // 60 + 1
    return f'Demasiados intentos fallidos. Probá de nuevo en {minutos} minuto(s).'


class _SaneadorHTML(HTMLParser):
    """Deja pasar solo etiquetas de formato simple (negrita, listas,
    títulos...) y descarta TODO lo demás: atributos, scripts, estilos,
    imágenes, links, eventos como onclick, etc. Es lo que se usa para
    mostrar la rutina, que se guarda como HTML."""

    PERMITIDAS = {
        'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'br', 'p', 'div', 'span',
        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'pre', 'code',
    }
    SIN_CIERRE = {'br'}
    DESCARTAR_CONTENIDO = {'script', 'style', 'iframe', 'object', 'embed', 'template', 'svg', 'math'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.pila = []
        self._descartando = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DESCARTAR_CONTENIDO:
            self._descartando += 1
            return
        if self._descartando or tag not in self.PERMITIDAS:
            return
        self.partes.append(f'<{tag}>')
        if tag not in self.SIN_CIERRE:
            self.pila.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in self.DESCARTAR_CONTENIDO or self._descartando:
            return
        if tag in self.PERMITIDAS and tag in self.SIN_CIERRE:
            self.partes.append(f'<{tag}>')

    def handle_endtag(self, tag):
        if tag in self.DESCARTAR_CONTENIDO:
            self._descartando = max(0, self._descartando - 1)
            return
        if self._descartando or tag not in self.PERMITIDAS or tag in self.SIN_CIERRE:
            return
        if tag in self.pila:
            while self.pila:
                abierta = self.pila.pop()
                self.partes.append(f'</{abierta}>')
                if abierta == tag:
                    break

    def handle_data(self, data):
        if not self._descartando:
            self.partes.append(html_lib.escape(data))

    def resultado(self):
        while self.pila:
            self.partes.append(f'</{self.pila.pop()}>')
        return ''.join(self.partes)


def sanitizar_html(texto):
    """Devuelve 'texto' limpio para mostrarlo como HTML sin riesgo de
    que ejecute código en el navegador de quien lo mira."""
    if not texto:
        return ''
    try:
        saneador = _SaneadorHTML()
        saneador.feed(texto)
        saneador.close()
        return saneador.resultado()
    except Exception:
        return html_lib.escape(texto)


# ------------------------------------------------------------
# HTML, CSV y clave de sesión
# ------------------------------------------------------------

def celda_csv(valor):
    """Evita la 'inyección de fórmulas' en Excel: si un texto empieza con
    =, +, - o @, Excel puede interpretarlo como una fórmula al abrir el CSV."""
    if isinstance(valor, str) and valor[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + valor
    return valor


class EscritorCSVSeguro:
    """Envuelve csv.writer aplicando celda_csv a cada celda."""

    def __init__(self, buffer, delimiter=';'):
        self._escritor = csv.writer(buffer, delimiter=delimiter)

    def writerow(self, fila):
        self._escritor.writerow([celda_csv(celda) for celda in fila])


def obtener_storage_secret():
    """Clave que firma las sesiones del navegador. Sale de la variable
    de entorno STORAGE_SECRET; si no está, se genera una al azar y se
    guarda en DATA_DIR (así las sesiones sobreviven a un reinicio)."""
    desde_entorno = os.environ.get('STORAGE_SECRET', '').strip()
    if len(desde_entorno) >= 16:
        return desde_entorno
    if desde_entorno:
        print("AVISO: STORAGE_SECRET es demasiado corta (mínimo 16 caracteres); se ignora.", flush=True)

    ruta = config.ruta_datos('.storage_secret')
    try:
        with open(ruta, 'r', encoding='utf-8') as archivo:
            guardada = archivo.read().strip()
        if len(guardada) >= 32:
            return guardada
    except OSError:
        pass

    nueva = secrets.token_urlsafe(48)
    try:
        descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as archivo:
            archivo.write(nueva)
    except OSError:
        pass
    return nueva
