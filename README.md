# 🏋️ Gestor de Gimnasio Vida Fitness

Aplicación web hecha con [NiceGUI](https://nicegui.io/) para administrar los socios de un gimnasio: altas, bajas, pagos, vencimientos, precios por plan, rutinas de entrenamiento, contabilidad y un portal propio para que cada cliente consulte su situación.

Todo el programa vive en un solo archivo (`gimnasio_completo.py`) y guarda los datos en archivos locales, sin necesidad de un motor de base de datos externo.

---

## ✨ Funcionalidades

### Gestión de clientes
- Alta, edición y baja de socios (DNI de 8 dígitos, teléfono de 10 dígitos, fecha de nacimiento).
- Planes: **2 veces por semana**, **3 veces por semana** y **Todos los días**.
- Buscador por nombre o DNI, filtro por plan y filtro de "solo vencidos".
- Exportación de la lista filtrada a **CSV** (separador `;`, compatible con Excel en configuración regional argentina).
- Rutina de entrenamiento por cliente, con editor de texto con formato (negrita, títulos, viñetas).

### Pagos y vencimientos
- Registro de pagos **totales o parciales**: si el cliente paga menos que el precio del plan, la diferencia queda como saldo pendiente.
- Abono posterior de saldo pendiente, sin modificar el vencimiento.
- Historial de pagos por cliente.
- Panel de **próximos vencimientos** (7 días) y **próximos cumpleaños** (30 días).
- Estadísticas: clientes activos, cuotas vencidas, ingresos esperados del mes y cobrado del mes.

### Contabilidad (solo dueño)
- Los cobros de cuotas se registran solos como ingresos.
- Carga manual de otros ingresos (bebidas, etc.) y gastos (luz, limpieza, etc.).
- Resumen mensual de ingresos, gastos y neto, y listado de los últimos movimientos.

### Portal del cliente
Cada cliente entra con su DNI y ve únicamente su propia ficha:
- Fecha de vencimiento y días restantes de cuota.
- Saldo pendiente (si tiene).
- Sus datos, su rutina y la información importante del gimnasio.
- Anuncios del gimnasio.
- Botón de consulta por **WhatsApp** y link a una **encuesta anónima** de sugerencias.
- Cambio de contraseña propio.

### Comunicación
- **Anuncios**: el dueño publica avisos que ven los clientes en su portal y el personal en la página de Clientes.
- **Información importante**: texto editable (horarios, normas, etc.) que se muestra a los clientes.

---

## 👥 Roles y permisos

| Acción | Dueño | Profe | Cliente |
|---|:---:|:---:|:---:|
| Ver y buscar clientes | ✅ | ✅ | ❌ |
| Alta / edición de clientes | ✅ | ✅ | ❌ |
| Registrar pagos y abonos | ✅ | ✅ | ❌ |
| Cargar / editar rutinas | ✅ | ✅ | ❌ |
| Eliminar clientes | ✅ | ❌ | ❌ |
| Administrar usuarios (dueño / profe) | ✅ | ❌ | ❌ |
| Precios, Información, Anuncios | ✅ | ❌ | ❌ |
| Contabilidad | ✅ | ❌ | ❌ |
| Ver su propia ficha | — | — | ✅ |

---

## 🚀 Instalación y ejecución

**Requisitos:** Python 3.9 o superior.

```bash
# 1. (Opcional) crear un entorno virtual
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 2. Instalar la dependencia
pip install nicegui

# 3. Ejecutar
python gimnasio_completo.py
```

Después abrí en el navegador: <http://localhost:8080>

El puerto se puede cambiar con la variable de entorno `PORT`:

```bash
PORT=9000 python gimnasio_completo.py
```

### Primer ingreso

La primera vez que se ejecuta, se crea la cuenta del dueño con usuario `admin`:

- Si definiste la variable de entorno `ADMIN_PASSWORD` (mínimo 8 caracteres), esa es la contraseña.
- Si no, se genera una **al azar y se muestra una sola vez en la consola (en Render, en la pestaña *Logs*)**. Guardala y cambiala desde la app (candado de la barra superior).

Los clientes nuevos reciben como contraseña inicial su propio DNI, y la app les **obliga a cambiarla** la primera vez que entran.

### Variables de entorno

| Variable | Para qué sirve |
|---|---|
| `ADMIN_PASSWORD` | Contraseña inicial de `admin` (mín. 8 caracteres). Si la cuenta todavía tiene la contraseña de fábrica `admin123`, se reemplaza por esta al arrancar |
| `STORAGE_SECRET` | Clave larga y aleatoria (mín. 16 caracteres) que firma las sesiones. Si no está, se genera una y se guarda en `DATA_DIR` |
| `DATA_DIR` | Carpeta donde se guardan todos los datos (por defecto, la carpeta actual) |
| `PORT` | Puerto del servidor |

Para generar un valor aleatorio largo: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

---

## ⚙️ Configuración

Todas las constantes están al principio de `gimnasio_completo.py`:

| Constante | Qué es |
|---|---|
| `NUMERO_WHATSAPP_GIMNASIO` | Número de WhatsApp del gimnasio (código de país + número, sin `+`, espacios ni guiones). Ej.: `5492615551234` |
| `LINK_ENCUESTA` | Link de la encuesta anónima de satisfacción |
| `LOGO_DATA_URI` | Logo del gimnasio incrustado en base64 (el `.py` queda autocontenido) |
| `PRECIOS_POR_DEFECTO` | Precios iniciales de cada plan (después se editan desde la página **Precios**) |
| `INFO_IMPORTANTE_POR_DEFECTO` | Texto inicial de "Información importante" |

---

## 🗂️ Almacenamiento de datos

Los datos se guardan en archivos locales, dentro de la carpeta `DATA_DIR` (por defecto, la carpeta desde donde se ejecuta el programa):

| Archivo | Formato | Contenido |
|---|---|---|
| `usuarios.db` | SQLite | Cuentas de dueño y profe |
| `Clientes.json` | JSON | Ficha de cada socio (datos, pagos, rutina, saldo) |
| `precios.json` | JSON | Precio vigente de cada plan |
| `informacion.json` | JSON | Texto que ven los clientes |
| `anuncios.json` | JSON | Anuncios publicados |
| `contabilidad.json` | JSON | Libro de ingresos y gastos |

Medidas de robustez incluidas:
- **Escritura atómica**: los JSON se escriben primero en un archivo temporal y luego se renombran, para que un corte de luz no deje un archivo a medio escribir.
- **Lectura tolerante**: si un archivo está corrupto, la app arranca igual con un valor por defecto en vez de caerse.
- **Locks** (`threading.Lock`) en las operaciones de leer-modificar-guardar, para que dos acciones simultáneas no se pisen.

> 💾 **Hacé copias de seguridad periódicas** de estos archivos, especialmente `Clientes.json`, `contabilidad.json` y `usuarios.db`.

### Despliegue en Render

- **Comando de build:** `pip install -r requirements.txt`
- **Comando de inicio:** `python gimnasio_completo.py`
- **Variables de entorno:** `ADMIN_PASSWORD`, `STORAGE_SECRET` y `DATA_DIR`.
- ⚠️ **Disco persistente:** en Render el disco del servicio es *efímero*: se borra en cada reinicio o deploy, y con él todos los clientes, pagos y la contabilidad. Para conservarlos, agregá un **Disk** al servicio (sección *Disks*), montalo en una carpeta (por ejemplo `/data`) y definí `DATA_DIR=/data`.

---

## 🔒 Seguridad

La app maneja datos personales de los socios (DNI, teléfono, fecha de nacimiento) y de pagos. Medidas implementadas:

- **Contraseñas solo como hash**: PBKDF2-SHA256 con 600.000 iteraciones y salt aleatorio por cuenta, con comparación en tiempo constante. **No se guarda ninguna copia legible** de las contraseñas ni se muestra en pantalla. Las cuentas con el hash viejo siguen entrando y se migran solas en su próximo ingreso.
- **Restablecer contraseña**: en lugar de ver la contraseña de un cliente, recepción puede restablecerla (vuelve a ser su DNI y el cliente debe cambiarla al entrar).
- **Cambio obligatorio** de la contraseña inicial de los clientes (que es su DNI).
- **Límite de intentos de login**: 5 intentos fallidos bloquean esa cuenta por 5 minutos, y los mensajes de error no revelan si el usuario o el DNI existen.
- **Sin cuenta de fábrica conocida**: la contraseña de `admin` viene de `ADMIN_PASSWORD` o se genera al azar.
- **Sesiones firmadas con una clave propia** (`STORAGE_SECRET`), no escrita en el código. Si se borra o cambia de rol a un usuario, su sesión abierta deja de funcionar.
- **Rutinas saneadas**: el texto con formato se limpia (se permite solo negrita, listas, títulos, etc.), para que nadie pueda inyectar código que se ejecute en el navegador de los clientes.
- **CSV seguro** contra inyección de fórmulas en Excel.
- **Protecciones de cuentas**: no se puede borrar la cuenta propia, ni a `admin`, ni dejar el sistema sin ningún dueño. Contraseñas de mínimo 8 caracteres para el personal y 6 para clientes.
- **Cabeceras HTTP de seguridad** (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`).

Recomendaciones que quedan de tu lado:

1. Usá **HTTPS** (Render lo incluye en su dominio `onrender.com`).
2. **No subas los datos a GitHub**: usá el `.gitignore` incluido.
3. Elegí contraseñas largas para el dueño y los profes, y no las compartas entre personas.
4. Hacé copias de seguridad y configurá el disco persistente (ver "Despliegue en Render").
5. Los datos de clientes están protegidos por contraseñas y roles, pero los archivos en el servidor **no están cifrados**: quien tenga acceso al servidor puede leerlos.

---

## 📁 Estructura del proyecto

```
.
├── gimnasio_completo.py   # Toda la aplicación
├── requirements.txt
├── README.md
├── .gitignore
│
│   # Se generan solos al usar la app:
├── usuarios.db
├── Clientes.json
├── precios.json
├── informacion.json
├── anuncios.json
└── contabilidad.json
```

### Páginas de la app

| Ruta | Quién accede | Descripción |
|---|---|---|
| `/login` | Todos | Ingreso como Profesor (usuario + contraseña) o Cliente (DNI + contraseña) |
| `/` | Dueño, Profe | Clientes: estadísticas, paneles, tabla y acciones |
| `/mi-cuenta` | Cliente | Portal personal del cliente |
| `/usuarios` | Dueño | Alta, edición y baja de cuentas |
| `/precios` | Dueño | Precio de cada plan |
| `/informacion` | Dueño | Texto de información para clientes |
| `/anuncios` | Dueño | Publicar y borrar anuncios |
| `/contabilidad` | Dueño | Ingresos, gastos y resumen mensual |

---

## 🛠️ Tecnologías

- **Python 3**
- **NiceGUI** (interfaz web; usa Quasar/Vue por debajo)
- **SQLite** (módulo `sqlite3` de la biblioteca estándar)
- **JSON** para el resto de los datos
- Estilo visual *glassmorphism* en gama de verdes

---

## 🧭 Ideas para próximas versiones

- Migrar los JSON a SQLite para tener consultas más eficientes y transacciones.
- Copias de seguridad automáticas.
- Recordatorios de vencimiento por WhatsApp.
- Dividir el código en módulos (datos, vistas, utilidades).

---

## 📄 Licencia

Proyecto de uso interno del gimnasio. Definí acá la licencia que corresponda si decidís publicarlo.
