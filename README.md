# 🏋️ Gestor de Gimnasio Vida Fitness

Aplicación web hecha con [NiceGUI](https://nicegui.io/) para administrar los socios de un gimnasio: altas, bajas, pagos, vencimientos, precios por plan, rutinas, contabilidad y un portal para que cada cliente consulte su situación. Se puede instalar en el celular como una app.

---

## ✨ Funcionalidades

**Clientes (dueño y profe)**
- Alta, edición y baja de socios (DNI de 8 dígitos, teléfono de 10 dígitos).
- El alta registra el **primer pago** (por defecto, el precio del plan; se puede cambiar): queda en el historial del cliente y en la contabilidad. Si abona menos, la diferencia queda como saldo pendiente.
- Planes: 2 veces por semana, 3 veces por semana y Todos los días.
- Buscador, filtro por plan y por cuotas vencidas, y exportación a CSV.
- Pagos totales o parciales (la diferencia queda como saldo pendiente) y abonos posteriores. Cada pago queda en el historial y en la contabilidad.
- Rutina de entrenamiento por cliente, con formato (negrita, títulos, listas).
- Paneles de próximos vencimientos (7 días) y cumpleaños (30 días).
- Restablecer la contraseña de un cliente.

**Solo dueño**
- Cuentas del personal, precios por plan, texto de información para clientes y anuncios.
- Contabilidad: ingresos, gastos y resumen mensual.
- **Respaldos**: copia automática diaria, copia manual y descarga de un `.zip`.
- **Actividad**: registro de quién hizo qué y cuándo (pagos, altas, bajas, cambios de precio...).

**Portal del cliente** (entra con su DNI)
- Vencimiento y días restantes, saldo pendiente, sus datos, su rutina, anuncios e información.
- Botón de consulta por WhatsApp y link a una encuesta anónima.
- **Cronómetro y contador de rondas** (funciona en el teléfono, sigue contando con la pantalla bloqueada).

### Roles y permisos

| Acción | Dueño | Profe | Cliente |
|---|:---:|:---:|:---:|
| Ver, buscar y editar clientes | ✅ | ✅ | ❌ |
| Registrar pagos, abonos y rutinas | ✅ | ✅ | ❌ |
| Restablecer la clave de un cliente | ✅ | ✅ | ❌ |
| Eliminar clientes | ✅ | ❌ | ❌ |
| Cuentas, precios, información, anuncios | ✅ | ❌ | ❌ |
| Contabilidad, respaldos, actividad | ✅ | ❌ | ❌ |
| Ver su propia ficha | — | — | ✅ |

---

## 🚀 Instalación y ejecución

Requiere Python 3.9 o superior.

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install nicegui
python main.py
```

Abrí <http://localhost:8080>.

### Primer ingreso

La primera vez se crea la cuenta `admin` (dueño):

- Si definiste `ADMIN_PASSWORD` (mínimo 8 caracteres), esa es la contraseña.
- Si no, se genera una al azar y se muestra **una sola vez en la consola** (en Render: pestaña *Logs*). Guardala y cambiala desde la app.

Los clientes nuevos entran con su DNI como contraseña y **tienen que cambiarla** en el primer ingreso.

### Si te olvidás la contraseña

Desde la consola, con la misma `DATA_DIR` que usa la app:

```bash
python -m gimnasio.cambiar_clave admin
```

Pide la contraseña nueva (mínimo 8 caracteres) y la guarda. En Render se corre desde la pestaña **Shell** del servicio (planes pagos). Ojo: `ADMIN_PASSWORD` solo se usa cuando la cuenta `admin` se crea por primera vez; cambiarla después en Render no cambia la de una cuenta que ya existe.

### Variables de entorno

| Variable | Para qué sirve |
|---|---|
| `ADMIN_PASSWORD` | Contraseña inicial de `admin` (mín. 8). Si `admin` todavía tiene la contraseña de fábrica `admin123` de versiones viejas, se reemplaza por esta al arrancar |
| `STORAGE_SECRET` | Clave larga y aleatoria (mín. 16) que firma las sesiones |
| `DATA_DIR` | Carpeta donde se guarda todo (por defecto, la carpeta actual). **En Render: el punto de montaje del disco persistente** |
| `PORT` | Puerto del servidor (por defecto 8080) |

Para generar una clave aleatoria: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## 🗂️ Estructura del proyecto

```
main.py                   # Arranque (mismo comando de inicio de siempre: python main.py)
gimnasio/
├── config.py             # Constantes y variables de entorno
├── tiempo.py             # Fechas y formatos (hora de Argentina)
├── seguridad.py          # Contraseñas, límite de intentos, HTML y CSV seguros
├── db.py                 # Base SQLite: esquema y transacciones
├── arranque.py           # Preparación al iniciar y tarea de respaldos
├── restaurar.py          # Restaurar una copia: python -m gimnasio.restaurar
├── cambiar_clave.py      # Recuperar una contraseña olvidada: python -m gimnasio.cambiar_clave USUARIO
├── datos/                # Acceso a los datos (sin NiceGUI)
│   ├── usuarios.py       #   cuentas del personal
│   ├── clientes.py       #   fichas y contraseñas de clientes
│   ├── pagos.py          #   pagos y abonos
│   ├── contabilidad.py   #   ingresos y gastos
│   ├── ajustes.py        #   precios, información y anuncios
│   └── auditoria.py      #   registro de actividad
├── servicios/            # Lógica (sin NiceGUI)
│   ├── estadisticas.py   #   vencimientos, cumpleaños, ingresos, filtros, CSV
│   ├── respaldos.py      #   copias de seguridad
│   └── migracion.py      #   importa los datos de la versión anterior
└── ui/                   # Pantallas (NiceGUI)
    ├── login.py, mi_cuenta.py, clientes.py, usuarios.py, precios.py,
    │   informacion.py, anuncios.py, contabilidad.py, respaldos.py, actividad.py
    ├── navbar.py, sesion.py, componentes.py, estilos.py, logo.py
    ├── entrenamiento.py  #   cronómetro y rondas
    └── pwa.py            #   app instalable, cabeceras de seguridad y /health
static/                   # Íconos de la app instalable
tests/                    # Pruebas automáticas
```

**Regla de oro:** todo lo que no está en `ui/` funciona sin NiceGUI. Por eso se puede probar solo, y por eso al agregar una función nueva conviene ponerla en `datos/` o `servicios/`, con su test, y que la pantalla solo la llame.

---

## 💾 Datos y respaldos

Todo vive en **un solo archivo**: `DATA_DIR/gimnasio.db` (SQLite). Los respaldos quedan en `DATA_DIR/respaldos/`.

- **Copia automática**: una por día mientras la app esté corriendo; se conservan las últimas 14.
- **Copia manual y descarga**: página **Respaldos** (solo dueño). Bajá el `.zip` de vez en cuando a tu compu o a tu Google Drive: es lo que te protege si pasa algo con el servidor.
- **Restaurar** (con la app sin uso):
  ```bash
  python -m gimnasio.restaurar RUTA/gimnasio-20261008-120000.db
  ```
  Antes de restaurar se guarda una copia `-previo` de lo que había, por si hay que deshacer.

### Si venís de la versión anterior (archivos JSON)

Al arrancar, si en `DATA_DIR` hay `Clientes.json`, `usuarios.db`, etc. y la base nueva está vacía, **se importan solos, una única vez**. Las contraseñas en texto plano de la versión vieja no se copian. Los archivos viejos no se tocan: cuando verifiques que todo se pasó bien, archivalos o borralos (tienen datos personales).

---

## ☁️ Despliegue en Render

- **Build:** `pip install -r requirements.txt` · **Inicio:** `python main.py`
- **Variables:** `ADMIN_PASSWORD`, `STORAGE_SECRET`, `DATA_DIR` y `PORT`.
- ⚠️ **Disco persistente**: en el plan gratuito el disco se borra en cada reinicio o deploy, y con él todos los datos. Para conservarlos hace falta una instancia paga con un **Disk** (sección *Disks*) montado en, por ejemplo, `/data`, y definir `DATA_DIR=/data`.
- **Monitoreo** (opcional): `GET /health` responde `{"estado": "ok"}` si la base está viva. Sirve para servicios como UptimeRobot.
- Recomendado: agregar `tzdata` al `requirements.txt` (la app igual funciona sin él, usando UTC-3).

Los archivos de `static/` tienen que estar en el repositorio para que la app sea instalable.

### Uso en celulares (Android)

Diseño adaptable, teclado numérico para el DNI, autocompletado de contraseña y vibración en el cronómetro. En Chrome: menú ⋮ → **Instalar app**.

---

## 🧪 Pruebas

```bash
python -m unittest discover -s tests -t .
```

No hace falta instalar nada extra (usa `unittest`, que viene con Python). Cubren contraseñas, permisos, pagos, deudas, contabilidad, vencimientos y cumpleaños, respaldos y restauración, migración de datos, el arranque y todas las pantallas (con un NiceGUI de mentira: `tests/stub_nicegui.py`).

Las pruebas de pantallas detectan errores de código y de permisos, pero **no reemplazan mirar la app en un navegador**. Después de cada cambio importante, revisá a mano:

1. El login del personal y del cliente, y que el logo se vea.
2. La tabla de clientes y que carguen el alta, un pago y la rutina.
3. El portal de un cliente (en el celular): vencimiento, rutina y cronómetro.
4. Respaldos: crear una copia y descargar el `.zip`.

---

## 🔒 Seguridad

- Contraseñas solo como hash (PBKDF2-SHA256, 600.000 iteraciones, salt propio); nunca en texto plano ni visibles en pantalla. Las cuentas con hash viejo se actualizan solas al ingresar.
- Cambio obligatorio de la contraseña inicial de los clientes (su DNI) y botón para restablecerla.
- Límite de intentos de login (5 fallos bloquean la cuenta 5 minutos) y mensajes que no revelan si el usuario existe.
- Sesiones firmadas con clave propia; si se borra un usuario o cambia su rol, su sesión abierta deja de valer.
- Rutinas saneadas (sin scripts) y CSV protegido contra fórmulas de Excel.
- No se puede borrar la propia cuenta, ni `admin`, ni dejar el sistema sin dueño.
- Cabeceras de seguridad HTTP y registro de actividad.
- Pago y asiento contable se guardan en una sola transacción: o se guardan los dos, o ninguno.

Del lado tuyo: usá HTTPS (Render lo incluye), no subas `gimnasio.db` ni los respaldos a GitHub (el `.gitignore` ya los excluye), guardá copias fuera del servidor y elegí contraseñas largas. Los archivos del servidor no están cifrados.

---

## 🧭 Ideas para más adelante

- Tiempos parciales por ronda en el cronómetro y aviso sonoro.
- Envío automático de los respaldos a Google Drive o a un bucket.
- Recordatorios de vencimiento por WhatsApp.
- Unificar los dos `ui.run()` de `main.py` en uno solo (hoy se mantienen tal cual funcionan en Render).
