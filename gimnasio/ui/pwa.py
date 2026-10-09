"""App instalable en Android (manifest y service worker), cabeceras de seguridad y chequeo de salud."""

import os

from nicegui import app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .. import db


class _CabecerasSeguridad(BaseHTTPMiddleware):
    """Agrega cabeceras de seguridad básicas a todas las respuestas
    (evita que la app se embeba en otro sitio, etc.)."""

    async def dispatch(self, request, call_next):
        respuesta = await call_next(request)
        respuesta.headers.setdefault('X-Content-Type-Options', 'nosniff')
        respuesta.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        respuesta.headers.setdefault('Referrer-Policy', 'same-origin')
        return respuesta


app.add_middleware(_CabecerasSeguridad)


# ---- App instalable en Android (PWA) ----

def datos_manifest():
    """Contenido del manifiesto que le dice a Android cómo instalar la app."""
    return {
        "name": "Gimnasio Vida Fitness",
        "short_name": "Vida Fitness",
        "description": "Tu cuenta, tu rutina, cronómetro y rondas.",
        "lang": "es-AR",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ecfdf5",
        "theme_color": "#16a34a",
        "icons": [
            {"src": "/static-vf/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static-vf/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }


# Service worker mínimo: hace que Chrome ofrezca instalar la app. No
# guarda nada en caché ni intercepta pedidos: todo sigue yendo al servidor.
SW_JS = """self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function () {});
"""

_carpeta_static = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'static')
if os.path.isdir(_carpeta_static):
    app.add_static_files('/static-vf', _carpeta_static)


@app.get('/manifest.webmanifest')
def ruta_manifest():
    return JSONResponse(datos_manifest(), media_type='application/manifest+json')


@app.get('/sw.js')
def ruta_service_worker():
    return Response(SW_JS, media_type='application/javascript', headers={'Cache-Control': 'no-cache'})


def estado_salud():
    """True si la base de datos responde."""
    try:
        with db.lectura() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False


@app.get('/health')
def ruta_salud():
    """Para que un monitor externo (ej. UptimeRobot) compruebe que la app está viva."""
    if estado_salud():
        return JSONResponse({'estado': 'ok'})
    return JSONResponse({'estado': 'error'}, status_code=503)
