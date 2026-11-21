# GEODETEC – ML Regresa a Casa

Análisis territorial con Machine Learning para **priorizar la búsqueda de personas
desaparecidas en los 125 municipios del Estado de México**. Proyecto académico (UNAM).

> ⚠️ Ejercicio académico. Las personas del registro son **100 % ficticias**. Una probabilidad
> alta en el modelo de fosas es un *candidato a revisión*, no un hallazgo.

## ¿Qué hace?
| Módulo | Descripción |
|---|---|
| **Mapa de prioridad** | Red neuronal (perceptrón multicapa 6 → 16 → 3, retropropagación) que clasifica en Baja / Media / Alta, entrenada con 500 municipios *simulados* y evaluado con los 125 municipios *reales* (INEGI 2020 + RNPDNO). |
| **Zona de búsqueda** | Combina `P(alta)` con la cercanía al último punto conocido: `índice = (0.25 + 0.75·P(alta)) · exp(-d² / 2·30²)`; marca el 10 % de municipios con mayor índice. En la GUI los tres parámetros se ajustan con deslizadores. |
| **Registros (CSV)** | Carga un CSV con registros de última ubicación, valida cada renglón, calcula la zona de búsqueda de cada uno y analiza las zonas en conjunto (municipios compartidos, registros cercanos). Solo en memoria. Genera un **reporte PDF** con cada gráfica explicada e interpretada. Ejemplo ficticio en `datos/registros_ejemplo.csv`. |
| **Registro de personas** | 5 fichas ficticias cifradas (Fernet + PBKDF2) en SQLite, protegidas con contraseña. |
| **Fosas clandestinas** | Modelo con datos reales cifrados (CNB 2018-2023, homicidios 2019-2024). Random Forest vs regresión logística con validación cruzada repetida. Se desbloquea con un folio. |

## Guía de instalación

### Requisitos previos
| Requisito | Versión | Cómo verificar |
|---|---|---|
| Python | 3.10 o superior (probado con 3.13) | `python --version` |
| pip | incluido con Python | `python -m pip --version` |
| Tkinter | incluido con Python en Windows y macOS | `python -m tkinter` (abre una ventanita) |
| Git | cualquiera (opcional) | `git --version` |

> **Windows:** al instalar Python desde [python.org](https://www.python.org/downloads/) marca
> la casilla **"Add python.exe to PATH"**.
> **Linux:** Tkinter se instala aparte, por ejemplo `sudo apt install python3-tk`.
> En macOS/Linux usa `python3` en lugar de `python` si `python` no existe.

### Paso 1 · Obtener el proyecto
```bash
git clone https://github.com/Regresar-a-Casa/ML-Regresa-a-Casa.git
cd ML-Regresa-a-Casa
```
También puedes descargar el ZIP desde GitHub (*Code → Download ZIP*), descomprimirlo y abrir una
terminal dentro de la carpeta.

### Paso 2 · (Recomendado) Crear un entorno virtual
Así las librerías del proyecto no se mezclan con las de otros proyectos.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
> Si PowerShell bloquea el script, ejecuta una vez
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Sabrás que está activo porque la terminal muestra `(.venv)` al inicio. Hay que activarlo cada
vez que abras una terminal nueva.

### Paso 3 · Instalar las dependencias
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
Esto instala numpy, pandas, matplotlib, scikit-learn y cryptography.

### Paso 4 · Configurar el archivo `.env`
El archivo `.env` guarda la contraseña inicial del registro de personas. **No se sube a git**,
así que cada computadora necesita el suyo.

**Windows:**
```powershell
copy .env.example .env
```
**macOS / Linux:**
```bash
cp .env.example .env
```
Abre `.env` con cualquier editor de texto y reemplaza el valor:
```
GEODETEC_CONTRASENA_INICIAL=la_contraseña_del_equipo
```
(Pide la contraseña al equipo. Debe tener al menos 8 caracteres.)

### Paso 5 · Verificar la instalación (opcional)
```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```
Debe terminar con `22 passed`.

## Guía de ejecución

Todos los comandos se ejecutan **desde la carpeta raíz del proyecto** (donde está `main.py`) y
con el entorno virtual activado si creaste uno.

### Opción A · Interfaz gráfica (recomendada para la exposición)
```bash
python main.py
```
1. Se abre la ventana **GEODETEC** (maximizada). Durante unos segundos solo está disponible la
   pestaña **Inicio**, mientras el sistema simula los datos y entrena el modelo.
2. Cuando la barra inferior dice **"Sistema listo · ... accuracy en datos reales: XX %"**, se
   habilitan las demás pestañas.
3. Pestañas, en el orden sugerido para una exposición:

| Pestaña | Qué muestra | Requiere |
|---|---|---|
| **Inicio** | Qué es el sistema, recorrido sugerido, las 6 variables explicadas y tarjetas con las métricas principales. | — |
| **Datos** | Mapas de las 6 variables reales y comparación de distribuciones simulados vs. reales. | — |
| **Modelo** | Métricas, reporte completo, matriz de confusión, importancia de variables (por permutación) y curva de entrenamiento de la red. | — |
| **Mapa de prioridad** | Prioridad según la regla, la predicha por el modelo y el mapa de calor de P(alta). | — |
| **Zona de búsqueda** | Eliges la última ubicación conocida (municipio, CDMX/Toluca o **clic en cualquier punto del mapa**) y se calcula la zona prioritaria. Con deslizadores ajustas σ, el piso del modelo y el tamaño de la zona; el mapa se recalcula solo. | — |
| **Registros (CSV)** | Cargas un CSV (o el ejemplo) y ves el reporte, el mapa con la zona de cada registro, los municipios a revisar primero y generas un reporte PDF. Doble clic en un registro lo abre en Zona de búsqueda. | Un archivo CSV |
| **Confidencial → Registro de personas** | Tabla de personas ficticias con ficha completa, mapa de ubicaciones, zona por persona y cambio de contraseña. | Contraseña |
| **Confidencial → Fosas clandestinas** | Entrena el modelo de fosas con datos reales y muestra el mapa de probabilidad y sus métricas (tarda unos segundos). | Folio de una persona |

- Cada vista incluye un texto **"Cómo leer"** que explica la gráfica.
- **Pasa el ratón sobre cualquier municipio** de un mapa para ver su nombre y sus valores
  (variable, prioridad, P(alta), índice de búsqueda, distancia, etc.).
- Los mapas marcan **CDMX** y **Toluca** como referencia para orientarse.
- Las gráficas tienen una barra de herramientas para hacer zoom, desplazarse y **guardar la
  imagen** (ícono del disquete), y un botón **"Abrir en ventana"** para verlas aparte.
- Las secciones confidenciales se desbloquean dentro de la pestaña y se vuelven a cerrar con
  **Bloquear**.

**Atajos de teclado**

| Tecla | Acción |
|---|---|
| `Ctrl+1` … `Ctrl+7` | Cambiar de pestaña |
| `F11` | Modo presentación: pantalla completa y letra más grande |
| `Esc` | Salir del modo presentación |

### Opción B · Modo consola (sin interfaz)
```bash
python main.py --consola
```
1. Imprime en la terminal el reporte de métricas del modelo.
2. Pide la **contraseña** del registro de personas → escríbela (no se muestra) o pulsa
   **Enter** para omitir esa sección.
3. Pide el **folio** para la sección de fosas → escríbelo o pulsa **Enter** para omitir.
4. Guarda todas las gráficas como PNG en la carpeta `salidas_edomex/`.

Útil para generar imágenes de respaldo para la presentación.

### Otras formas de ejecutar
```bash
python -m geodetec              # equivalente a python main.py
python -m geodetec --consola    # equivalente a python main.py --consola
```

### Qué se genera al ejecutar
| Archivo | Contenido |
|---|---|
| `geodetec_edomex.db` | Base SQLite: datos, predicciones, historial de métricas y registros cifrados. |
| `salidas_edomex/*.png` | Gráficas (solo en modo consola). |

- La **primera ejecución** crea la base y cifra el registro de personas con la contraseña del
  `.env`. En las siguientes ejecuciones el registro se conserva.
- La contraseña se puede cambiar desde *Personas → Cambiar contraseña*. A partir de ahí, la
  válida es la nueva, no la del `.env`.
- Para **empezar de cero** (por ejemplo, si olvidaste la contraseña), cierra el programa y
  borra `geodetec_edomex.db`. Se volverá a crear con la contraseña del `.env`.

## Solución de problemas
| Mensaje / síntoma | Solución |
|---|---|
| `'python' no se reconoce como un comando` | Reinstala Python marcando *Add to PATH*, o usa `py` en lugar de `python`. |
| `ModuleNotFoundError: No module named ...` | Falta instalar dependencias: `python -m pip install -r requirements.txt` (con el entorno virtual activado). |
| `Falta la librería 'cryptography'` | `python -m pip install cryptography` |
| `Falta la variable GEODETEC_CONTRASENA_INICIAL` | No existe el `.env` o está vacío: repite el Paso 4. |
| `Contraseña incorrecta. Acceso denegado.` | La contraseña cambió desde la GUI, o la base se creó con otro `.env`. Borra `geodetec_edomex.db` para reiniciar. |
| `Folio no válido. Acceso denegado.` | El folio debe ser el de una persona del registro (formato `GD-AAAA-00N`). |
| `No se encontró edomex_municipios.geojson` | Ejecuta desde la raíz del proyecto y verifica que la carpeta `datos/` esté completa. |
| La ventana dice "No responde" unos segundos | Es normal mientras entrena (al iniciar y en Fosas); espera a que termine. |
| El clic en el mapa no mueve el origen | Desactiva la lupa o la flecha de desplazamiento de la barra de herramientas (vuelve a pulsar el ícono activo). |
| Las pestañas aparecen en gris | El sistema todavía se está preparando; espera el mensaje "Sistema listo". |
| `No module named '_tkinter'` (Linux) | `sudo apt install python3-tk` |
| Acentos raros en la consola de Windows | Ejecuta antes `set PYTHONIOENCODING=utf-8` (cmd) o `$env:PYTHONIOENCODING="utf-8"` (PowerShell). |

## Formato del CSV de registros
| Columna | Obligatoria | Notas |
|---|---|---|
| `id` | sí | Identificador único del registro |
| `fecha_desaparicion` | sí | `AAAA-MM-DD` o `DD/MM/AAAA`; no puede ser futura |
| `municipio` | * | Se toleran acentos, mayúsculas, erratas leves y nombres cortos (`Ecatepec`) |
| `lat`, `lon` | * | Coordenadas decimales; si vienen junto con el municipio, mandan las coordenadas |
| `nombre`, `edad`, `sexo`, `descripcion` | no | Informativas |

\* Se necesita `municipio` o el par `lat`/`lon`. Se aceptan separadores `,` `;` tabulador o `|`,
codificación UTF-8 o ANSI (lo que guarda Excel en español) y sinónimos en los encabezados
(`Fecha de desaparición`, `Latitud`, `Longitud`, `folio`…). Los renglones con errores se descartan
y se explican en el reporte; el resto se analiza. Máximo 30 registros por archivo.

## Reportes PDF
Todos los reportes usan la misma plantilla (`geodetec/reportes/plantilla.py`): portada con los
datos del documento y un aviso, encabezado y pie con número de página en cada hoja, y un bloque
estándar por gráfica: **título → gráfica → "Qué muestra" → "Interpretación"**. La interpretación
se redacta a partir de los datos del análisis.

El reporte de registros (botón **Generar reporte PDF…**) incluye: resumen, tabla de registros, mapa
general, municipios a revisar primero, una página por registro (zona, interpretación y orden de
revisión), calidad de los datos, metodología con sus límites y a dónde acudir. Está escrito para
que lo pueda leer una familia o un colectivo: deja claro que la zona **ordena** municipios para
revisar, no indica dónde está una persona, y que las pistas concretas del caso tienen prioridad.

Para un reporte nuevo: crea un módulo en `geodetec/reportes/` que use `Reporte` (`portada`,
`seccion`, `parrafo`, `vinetas`, `recuadro`, `grafica`, `tabla`, `guardar`).

## Estructura
```
main.py                  lanzador
geodetec/
├── config.py            rutas, constantes y lectura de .env
├── datos.py             municipios reales, variables, regla de prioridad, simulación
├── db.py                persistencia SQLite
├── modelo.py            red neuronal de prioridad
├── busqueda.py          zona de búsqueda prioritaria
├── cripto.py            derivación de claves y Fernet
├── personas.py          registro confidencial (ficticio)
├── fosas.py             modelo de fosas clandestinas
├── registros.py         lectura, validación y análisis de registros desde CSV
├── reportes/            reportes PDF: plantilla común (plantilla.py) y reporte de registros
├── sistema.py           orquestador (clase Geodetec)
├── consola.py           modo consola
├── figuras/             mapas y gráficas (matplotlib)
└── gui/                 interfaz Tkinter
    ├── app.py           ventana principal, pestañas, modo presentación
    ├── estilo.py        paleta, tipografías y tema
    ├── componentes.py   figuras incrustadas, tarjetas, selector de vistas, diálogos
    └── pestanas/        una pestaña por archivo (inicio, datos, modelo, ...)
datos/
├── edomex_municipios.geojson
├── fosas_edomex.enc     (cifrado)
└── registros_ejemplo.csv  3 registros ficticios de ejemplo
tests/                   pruebas con pytest
```

## Fuentes de datos
- Límites municipales: CONABIO / INEGI, Marco Geoestadístico 2020.
- Población: INEGI, Censo 2020. Localidades y altitud: catálogo de localidades INEGI.
- Personas desaparecidas: RNPDNO, Consulta Pública (corte 30/11/2025).
- Fosas clandestinas: Comisión Nacional de Búsqueda (2018-2023). Homicidios 2019-2024.
