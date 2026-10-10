"""Estilos (CSS) y etiquetas comunes del <head> de todas las páginas."""


# ============================================================
# ESTILOS GLASSMORPHISM -- gama de verdes
# ============================================================

CSS = """
:root {
    --glass-bg: rgba(255, 255, 255, 0.62);
    --glass-border: rgba(255, 255, 255, 0.75);
    --primary: #16a34a;
    --secondary: #22c55e;
    --text-primary: #10241a;
    --shadow: 0 20px 50px rgba(21, 128, 61, 0.12);
}

html, body { min-height: 100%; margin: 0; }

body {
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    color: var(--text-primary);
    background:
        radial-gradient(circle at 10% 10%, rgba(34, 197, 94, 0.22), transparent 28%),
        radial-gradient(circle at 90% 15%, rgba(16, 185, 129, 0.20), transparent 25%),
        radial-gradient(circle at 50% 100%, rgba(74, 222, 128, 0.16), transparent 35%),
        linear-gradient(135deg, #ecfdf5 0%, #f7fefb 45%, #ecfdf5 100%);
    background-attachment: fixed;
}

.app-header {
    height: 70px;
    background: rgba(255, 255, 255, 0.58);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.7);
    box-shadow: 0 10px 30px rgba(21, 128, 61, 0.06);
}

.logo-container { display: flex; align-items: center; gap: 11px; }

.logo-icon {
    width: 40px; height: 40px; border-radius: 13px;
    background: linear-gradient(135deg, #16a34a, #4ade80);
    display: flex; align-items: center; justify-content: center;
    color: white; box-shadow: 0 10px 25px rgba(22, 163, 74, 0.28);
    flex-shrink: 0;
    overflow: hidden;
}
.logo-icon img { width: 100%; height: 100%; object-fit: cover; }

.logo-icon-grande {
    width: 64px; height: 64px; border-radius: 18px;
    background: linear-gradient(135deg, #16a34a, #4ade80);
    display: flex; align-items: center; justify-content: center;
    color: white; box-shadow: 0 10px 25px rgba(22, 163, 74, 0.28);
    flex-shrink: 0;
    overflow: hidden;
    margin: 0 auto;
}
.logo-icon-grande img { width: 100%; height: 100%; object-fit: cover; }

.logo-text { font-size: 19px; font-weight: 800; color: #10241a; letter-spacing: -0.5px; }
.logo-text span {
    background: linear-gradient(90deg, #16a34a, #4ade80);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.nav-button { color: #4b5c53 !important; font-weight: 650; border-radius: 12px; transition: all .2s ease; }
.nav-button:hover { color: #16a34a !important; background: rgba(22, 163, 74, 0.08); transform: translateY(-1px); }

.page-title { font-size: 32px; font-weight: 850; letter-spacing: -1px; color: #10241a; }
.page-subtitle { color: #5c6b62; font-size: 14px; line-height: 1.6; }

.glass-card {
    background: var(--glass-bg);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid var(--glass-border); border-radius: 22px;
    box-shadow: var(--shadow);
}

.stat-card {
    position: relative; overflow: hidden;
    background: rgba(255, 255, 255, 0.58);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255, 255, 255, 0.78); border-radius: 20px;
    padding: 21px; box-shadow: 0 15px 40px rgba(21, 128, 61, 0.08);
    transition: all .25s ease;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 20px 45px rgba(21, 128, 61, 0.16); }
.stat-label { color: #5c6b62; font-size: 13px; font-weight: 600; }
.stat-value { font-size: 31px; font-weight: 850; color: #10241a; margin-top: 5px; }

.table-container {
    background: rgba(255, 255, 255, 0.60);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255, 255, 255, 0.78); border-radius: 22px;
    overflow: hidden; box-shadow: 0 20px 50px rgba(21, 128, 61, 0.09);
}

.q-field--outlined .q-field__control { border-radius: 13px; background: rgba(255, 255, 255, 0.50); }
.q-btn { border-radius: 12px; font-weight: 650; text-transform: none; }
.q-btn.bg-primary {
    background: linear-gradient(135deg, #16a34a, #4ade80) !important;
    box-shadow: 0 8px 20px rgba(22, 163, 74, 0.28);
}

.q-table { background: transparent !important; color: #26332c; }
.q-table thead tr { background: rgba(22, 163, 74, 0.05); }
.q-table thead th { color: #5c6b62; font-size: 11px; font-weight: 800; letter-spacing: .7px; }
.q-table tbody tr:hover { background: rgba(22, 163, 74, 0.06); }

.q-dialog__inner > .q-card {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(25px); -webkit-backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.9); border-radius: 24px;
    box-shadow: 0 30px 80px rgba(21, 128, 61, 0.20);
}

.app-footer {
    width: 100%; padding: 24px 32px;
    border-top: 1px solid rgba(255, 255, 255, 0.7);
    background: rgba(255, 255, 255, 0.40);
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
}
.footer-text { font-size: 12px; color: #6d7c74; }

.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
.login-card {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.82); border-radius: 28px;
    box-shadow: 0 30px 80px rgba(21, 128, 61, 0.15);
    padding: 40px; width: 420px; max-width: 95vw;
}
.login-title { font-size: 26px; font-weight: 850; color: #10241a; text-align: center; letter-spacing: -.5px; }
.login-subtitle { color: #5c6b62; font-size: 14px; text-align: center; line-height: 1.6; }
.login-hint {
    background: rgba(22, 163, 74, 0.07); border: 1px solid rgba(22, 163, 74, 0.14);
    border-radius: 14px; padding: 12px 16px; margin-top: 16px;
}
.login-hint-label { color: #16a34a; font-size: 11px; font-weight: 750; text-transform: uppercase; }
.login-hint-text { color: #5c6b62; font-size: 13px; margin-top: 2px; }
.login-error {
    background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.18);
    border-radius: 12px; padding: 10px 14px; color: #dc2626; font-size: 13px; font-weight: 600;
}

.user-avatar {
    width: 36px; height: 36px; min-width: 36px; border-radius: 12px;
    background: linear-gradient(135deg, #16a34a, #4ade80); color: white;
    display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px;
}
.user-info-name { font-size: 13px; font-weight: 700; color: #1c2e24; }
.user-info-role { font-size: 11px; color: #5c6b62; font-weight: 600; text-transform: uppercase; }

.cumple-fila {
    padding: 10px 14px; border-radius: 12px;
    background: rgba(255, 255, 255, 0.45);
    margin-bottom: 6px;
}
.cumple-hoy {
    padding: 10px 14px; border-radius: 12px;
    background: linear-gradient(135deg, rgba(74, 222, 128, 0.35), rgba(250, 204, 21, 0.30));
    border: 1px solid rgba(22, 163, 74, 0.4);
    margin-bottom: 6px;
    font-weight: 700;
}

.mi-cuenta-card {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
    border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 24px;
    box-shadow: 0 25px 60px rgba(21, 128, 61, 0.14);
    padding: 32px; width: 560px; max-width: 95vw;
}
.dato-fila { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.06); }
.dato-label { color: #5c6b62; font-weight: 600; }
.dato-valor { color: #10241a; font-weight: 700; }

.venc-ok {
    background: rgba(74, 222, 128, 0.25); border: 1px solid rgba(22, 163, 74, 0.35);
    border-radius: 14px; padding: 16px 20px; font-weight: 700; color: #14532d;
}
.venc-vencido {
    background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 14px; padding: 16px 20px; font-weight: 700; color: #991b1b;
}

.info-importante {
    background: rgba(250, 204, 21, 0.14); border: 1px solid rgba(202, 138, 4, 0.3);
    border-radius: 14px; padding: 16px 20px; color: #713f12; font-size: 14px; line-height: 1.7;
    white-space: pre-line;
}

.rutina-cliente {
    background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(37, 99, 235, 0.3);
    border-radius: 14px; padding: 16px 20px; color: #1e3a8a; font-size: 14px; line-height: 1.7;
}
.rutina-cliente ul, .rutina-cliente ol { padding-left: 22px; margin: 8px 0; }
.rutina-cliente p { margin: 6px 0; }
.rutina-cliente h1, .rutina-cliente h2, .rutina-cliente h3 { margin: 10px 0 6px 0; }

.anuncio-item {
    background: linear-gradient(135deg, rgba(22, 163, 74, 0.14), rgba(74, 222, 128, 0.10));
    border: 1px solid rgba(22, 163, 74, 0.35);
    border-radius: 14px; padding: 14px 18px; margin-bottom: 10px;
    color: #14532d;
}
.anuncio-fecha { font-size: 11px; color: #16803d; font-weight: 700; text-transform: uppercase; }

.deuda-aviso {
    background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(217, 119, 6, 0.4);
    border-radius: 12px; padding: 10px 14px; color: #92400e; font-size: 14px; font-weight: 700;
}

.entrenamiento {
    background: rgba(255, 255, 255, 0.55); border: 1px solid rgba(22, 163, 74, 0.25);
    border-radius: 14px; padding: 18px 20px;
}
.vf-numero {
    font-size: 52px; font-weight: 850; color: #10241a; line-height: 1.1;
    font-variant-numeric: tabular-nums; letter-spacing: -1px;
}
.vf-subtitulo { color: #5c6b62; font-size: 13px; font-weight: 700; text-transform: uppercase; }
[data-vf="pausar"] { display: none; }

.q-btn { touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
.entrenamiento { user-select: none; -webkit-user-select: none; }

@media (max-width: 700px) {
    .p-8 { padding: 14px !important; }
    .page-title { font-size: 25px; }
    .app-header { height: auto !important; min-height: 64px; padding: 6px 10px !important; }
    .app-header .q-separator--vertical { display: none; }
    .logo-text { display: none; }
    .user-info-name, .user-info-role { display: none; }
    /* Los enlaces del personal pasan a una segunda fila que se desliza con el dedo */
    .nav-links-staff { order: 10; flex: 0 0 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; padding-bottom: 2px; }
    .nav-links-staff .nav-button { flex-shrink: 0; min-width: auto; padding: 0 10px; font-size: 13px; }
    .nav-links-staff .nav-button .q-icon { font-size: 18px; }
    .mi-cuenta-card { padding: 18px; }
    .login-card { padding: 26px 20px; }
    .grid-stats { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
    .grid-paneles { grid-template-columns: minmax(0, 1fr) !important; }
    .stat-value { font-size: 24px; }
    .app-footer { padding: 16px; }
    .vf-numero { font-size: 60px; }
    .entrenamiento { padding: 14px 10px; }
    .entrenamiento .q-btn { min-height: 52px; }
}

.btn-whatsapp {
    background: #25D366 !important; color: white !important;
    box-shadow: 0 8px 20px rgba(37, 211, 102, 0.35);
}
"""


# Etiquetas que se agregan al <head> de TODAS las páginas: permiten
# instalar la app en Android ("Agregar a la pantalla de inicio"), tiñen
# la barra del navegador de verde y cargan los estilos.
HEAD_COMUN = (
    '<link rel="manifest" href="/manifest.webmanifest">'
    '<meta name="theme-color" content="#16a34a">'
    '<meta name="mobile-web-app-capable" content="yes">'
    '<link rel="apple-touch-icon" href="/static-vf/icon-192.png">'
    "<script>if ('serviceWorker' in navigator) { window.addEventListener('load', function () {"
    " navigator.serviceWorker.register('/sw.js').catch(function () {}); }); }</script>"
    + f'<style>{CSS}</style>'
)
