"""NiceGUI de mentira para probar las pantallas sin navegador.

Cada elemento que la interfaz "dibuja" (labels, botones, inputs, tablas...) se
guarda en REGISTRO, así los tests pueden buscarlo, escribir en un campo, tocar
un botón y comprobar el resultado. No reemplaza probar la app en un navegador
real, pero detecta errores de código (nombres mal escritos, datos que faltan,
permisos mal puestos) en todas las pantallas.
"""

import sys
import types

REGISTRO = []          # todos los elementos creados
NOTIFICACIONES = []    # (texto, tipo)
NAVEGACIONES = []      # destinos de ui.navigate.to
DESCARGAS = []         # (contenido, nombre)
HEAD_Y_BODY = []       # html agregado al <head>/<body>
LLAMADAS_A_RUN = []    # argumentos de cada ui.run(...)
PAGINAS = {}           # ruta -> función de la página
RUTAS = {}             # ruta -> función de un @app.get


class Elemento:
    def __init__(self, tipo, *args, **kwargs):
        self.tipo = tipo
        self.args = args
        self.kwargs = kwargs
        self.texto = args[0] if args and isinstance(args[0], str) else kwargs.get('label', kwargs.get('text'))
        por_defecto = '' if tipo in ('input', 'textarea', 'editor') else (False if tipo == 'checkbox' else None)
        self.value = kwargs.get('value', por_defecto)
        self.on_click = kwargs.get('on_click')
        self.manejadores = {}
        self.propiedades = []
        self.clases = []
        self.rows = kwargs.get('rows')
        self.abierto = False
        REGISTRO.append(self)

    # contexto: with ui.card(): ...
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    # encadenado: .props().classes().style().tooltip()...
    def props(self, texto=''):
        self.propiedades.append(texto)
        return self

    def classes(self, texto=''):
        self.clases.append(texto)
        return self

    def style(self, *a, **k):
        return self

    def tooltip(self, *a, **k):
        return self

    def add_slot(self, *a, **k):
        return self

    def on(self, evento, manejador=None, **k):
        self.manejadores[evento] = manejador
        return self

    def on_value_change(self, manejador):
        self.manejadores['value_change'] = manejador
        return self

    def set_text(self, texto):
        self.texto = texto

    def clear(self):
        pass

    def open(self):
        self.abierto = True

    def close(self):
        self.abierto = False

    def __getattr__(self, nombre):  # cualquier otro método de NiceGUI: no hace nada
        if nombre.startswith('__'):
            raise AttributeError(nombre)
        return lambda *a, **k: self


class _Navigate:
    def to(self, destino, new_tab=False):
        NAVEGACIONES.append(destino)

    def reload(self):
        NAVEGACIONES.append('(recargar)')


class _Ui:
    navigate = _Navigate()

    def page(self, ruta, **k):
        def decorador(funcion):
            PAGINAS[ruta] = funcion
            return funcion
        return decorador

    def notify(self, texto, type=None, **k):
        NOTIFICACIONES.append((texto, type))

    def download(self, contenido, nombre=None, *a, **k):
        DESCARGAS.append((contenido, nombre))

    def add_head_html(self, codigo, *a, **k):
        HEAD_Y_BODY.append(('head', codigo))

    def add_body_html(self, codigo, *a, **k):
        HEAD_Y_BODY.append(('body', codigo))

    def run(self, *a, **k):
        LLAMADAS_A_RUN.append(k)

    def __getattr__(self, tipo):
        if tipo.startswith('__'):
            raise AttributeError(tipo)
        return lambda *a, **k: Elemento(tipo, *a, **k)


class _Almacen:
    def __init__(self):
        self.user = {}


class _App:
    def __init__(self):
        self.storage = _Almacen()
        self.middlewares = []
        self.estaticos = []
        self.al_iniciar = []

    def get(self, ruta):
        def decorador(funcion):
            RUTAS[ruta] = funcion
            return funcion
        return decorador

    def add_middleware(self, clase, *a, **k):
        self.middlewares.append(clase)

    def add_static_files(self, url, carpeta):
        self.estaticos.append((url, carpeta))

    def on_startup(self, funcion):
        self.al_iniciar.append(funcion)


ui = _Ui()
app = _App()


def reiniciar():
    for lista in (REGISTRO, NOTIFICACIONES, NAVEGACIONES, DESCARGAS, HEAD_Y_BODY, LLAMADAS_A_RUN):
        lista.clear()
    app.storage.user.clear()


def buscar(tipo, texto):
    """Todos los elementos de ese tipo cuyo texto/etiqueta sea 'texto'."""
    return [e for e in REGISTRO if e.tipo == tipo and e.texto == texto]


def textos(tipo='label'):
    return [str(e.texto) for e in REGISTRO if e.tipo == tipo]


def instalar():
    """Hace que 'import nicegui' (y starlette, si no está instalado) use las versiones de mentira."""
    modulo = types.ModuleType('nicegui')
    modulo.ui = ui
    modulo.app = app
    sys.modules['nicegui'] = modulo
    for nombre in [n for n in sys.modules if n == 'gimnasio.ui' or n.startswith('gimnasio.ui.')]:
        del sys.modules[nombre]

    try:
        import starlette.middleware.base  # noqa: F401
        import starlette.responses  # noqa: F401
    except ImportError:
        base = types.ModuleType('starlette.middleware.base')

        class BaseHTTPMiddleware:
            def __init__(self, app=None, **k):
                self.app = app

        base.BaseHTTPMiddleware = BaseHTTPMiddleware
        respuestas = types.ModuleType('starlette.responses')

        class Response:
            def __init__(self, content=None, status_code=200, headers=None, media_type=None):
                self.status_code, self.media_type = status_code, media_type
                self.headers = dict(headers or {})
                self.body = self._a_bytes(content)

            @staticmethod
            def _a_bytes(content):
                return content if isinstance(content, bytes) else str(content).encode('utf-8')

        class JSONResponse(Response):
            @staticmethod
            def _a_bytes(content):
                import json
                return json.dumps(content).encode('utf-8')

        respuestas.Response, respuestas.JSONResponse = Response, JSONResponse
        sys.modules['starlette'] = types.ModuleType('starlette')
        sys.modules['starlette.middleware'] = types.ModuleType('starlette.middleware')
        sys.modules['starlette.middleware.base'] = base
        sys.modules['starlette.responses'] = respuestas
