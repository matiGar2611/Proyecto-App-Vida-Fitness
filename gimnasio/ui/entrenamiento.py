"""Cronómetro y contador de rondas del portal del cliente (funciona en el navegador, sin usar el servidor)."""

from nicegui import ui


# Funciona 100% en el navegador del cliente: no usa el servidor, sigue
# contando aunque se bloquee la pantalla, y recuerda el estado en ese
# dispositivo (localStorage), separado por DNI.

JS_ENTRENAMIENTO = r"""
(function () {
  var CLAVE = '__CLAVE__';
  var est = { acum: 0, inicio: null, rondas: 0 };
  var wakeLock = null;

  try {
    var g = JSON.parse(localStorage.getItem(CLAVE));
    if (g && typeof g === 'object') {
      est.acum = Math.max(0, Number(g.acum) || 0);
      est.inicio = g.inicio ? Number(g.inicio) || null : null;
      est.rondas = Math.min(999, Math.max(0, parseInt(g.rondas, 10) || 0));
    }
  } catch (e) {}

  function guardar() {
    try { localStorage.setItem(CLAVE, JSON.stringify(est)); } catch (e) {}
  }
  function transcurrido() {
    return est.acum + (est.inicio ? Math.max(0, Date.now() - est.inicio) : 0);
  }
  function p2(n) { return (n < 10 ? '0' : '') + n; }
  function formatear(ms) {
    var d = Math.floor(ms / 100) % 10;
    var s = Math.floor(ms / 1000);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var seg = s % 60;
    return (h ? h + ':' + p2(m) : p2(m)) + ':' + p2(seg) + '.' + d;
  }

  function pantallaActiva(activar) {
    try {
      if (activar && navigator.wakeLock && !wakeLock) {
        navigator.wakeLock.request('screen').then(function (w) {
          wakeLock = w;
          w.addEventListener('release', function () { wakeLock = null; });
        }).catch(function () {});
      } else if (!activar && wakeLock) {
        wakeLock.release();
        wakeLock = null;
      }
    } catch (e) {}
  }

  function pintar() {
    var corriendo = !!est.inicio;
    var t = formatear(transcurrido());
    var a = document.querySelectorAll('.vf-tiempo');
    for (var i = 0; i < a.length; i++) { if (a[i].textContent !== t) a[i].textContent = t; }
    var r = String(est.rondas);
    var b = document.querySelectorAll('.vf-rondas');
    for (var j = 0; j < b.length; j++) { if (b[j].textContent !== r) b[j].textContent = r; }
    var ini = document.querySelectorAll('[data-vf="iniciar"]');
    for (var k = 0; k < ini.length; k++) ini[k].style.display = corriendo ? 'none' : 'inline-flex';
    var pau = document.querySelectorAll('[data-vf="pausar"]');
    for (var l = 0; l < pau.length; l++) pau[l].style.display = corriendo ? 'inline-flex' : 'none';
  }

  function vibrar(ms) {
    try { if (navigator.vibrate) navigator.vibrate(ms); } catch (e) {}
  }

  function accion(nombre) {
    if (nombre === 'iniciar') {
      if (!est.inicio) { est.inicio = Date.now(); pantallaActiva(true); }
    } else if (nombre === 'pausar') {
      if (est.inicio) { est.acum = transcurrido(); est.inicio = null; pantallaActiva(false); }
    } else if (nombre === 'reiniciar-tiempo') {
      est.acum = 0; est.inicio = null; pantallaActiva(false);
    } else if (nombre === 'rondas-mas') {
      est.rondas = Math.min(999, est.rondas + 1);
    } else if (nombre === 'rondas-menos') {
      est.rondas = Math.max(0, est.rondas - 1);
    } else if (nombre === 'rondas-reset') {
      est.rondas = 0;
    } else {
      return;
    }
    vibrar(nombre === 'rondas-mas' ? 40 : 20);
    guardar();
    pintar();
  }

  document.addEventListener('click', function (e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-vf]') : null;
    if (el) accion(el.getAttribute('data-vf'));
  });
  document.addEventListener('visibilitychange', function () {
    pintar();
    if (!document.hidden && est.inicio) pantallaActiva(true);
  });
  setInterval(pintar, 100);
  pintar();

  window.__vfEntrenamiento = { accion: accion, estado: function () { return est; }, formatear: formatear };
})();
"""


def agregar_entrenamiento(dni):
    """Dibuja el cronómetro y el contador de rondas y carga su código JS.
    Se llama dentro de la página 'Mi cuenta'."""
    clave = 'vf_entrenamiento_' + ''.join(c for c in str(dni) if c.isalnum())
    ui.add_body_html('<script>' + JS_ENTRENAMIENTO.replace('__CLAVE__', clave) + '</script>')

    ui.label('Cronómetro y rondas').classes('text-lg font-bold mt-5 mb-1')
    with ui.column().classes('entrenamiento w-full items-center gap-2'):
        ui.label('00:00.0').classes('vf-tiempo vf-numero')
        with ui.row().classes('gap-2 justify-center'):
            ui.button('Iniciar', icon='play_arrow').props('unelevated color=primary data-vf=iniciar')
            ui.button('Pausar', icon='pause').props('unelevated color=primary data-vf=pausar')
            ui.button('Reiniciar', icon='restart_alt').props('outline color=primary data-vf=reiniciar-tiempo')

        ui.separator().classes('w-full my-1')

        ui.label('Rondas').classes('vf-subtitulo')
        ui.label('0').classes('vf-rondas vf-numero')
        with ui.row().classes('gap-2 justify-center items-center'):
            ui.button(icon='remove').props('round outline color=primary data-vf=rondas-menos')
            ui.button('Ronda', icon='add').props('unelevated color=primary data-vf=rondas-mas')
            ui.button(icon='restart_alt').props('round flat color=primary data-vf=rondas-reset')
