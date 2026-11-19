"""Configuración central de GEODETEC: rutas, constantes del modelo y variables de entorno.

Los valores sensibles (la contraseña inicial del registro de personas) NO viven en el código:
se leen del archivo ``.env`` en la raíz del proyecto (ver ``.env.example``).
"""
import os

# --------------------------------------------------------------------------- rutas
CARPETA_PAQUETE = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.dirname(CARPETA_PAQUETE)          # raíz del proyecto
CARPETA_DATOS = os.path.join(CARPETA, "datos")

GEOJSON_PATH = os.path.join(CARPETA_DATOS, "edomex_municipios.geojson")
FOSAS_PATH = os.path.join(CARPETA_DATOS, "fosas_edomex.enc")
DB_PATH = os.path.join(CARPETA, "geodetec_edomex.db")
CARPETA_SALIDAS = os.path.join(CARPETA, "salidas_edomex")
ENV_PATH = os.path.join(CARPETA, ".env")


# --------------------------------------------------------------------------- .env
def cargar_env(ruta=ENV_PATH):
    """Carga pares CLAVE=valor de un archivo .env en ``os.environ``.

    Las variables ya definidas en el entorno tienen prioridad sobre el archivo.
    Admite comentarios (#), líneas vacías, ``export`` opcional y valores entre comillas.
    """
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8-sig") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            if linea.startswith("export "):
                linea = linea[len("export "):]
            clave, valor = linea.split("=", 1)
            clave, valor = clave.strip(), valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                valor = valor[1:-1]
            os.environ.setdefault(clave, valor)


cargar_env()


def contrasena_inicial():
    """Contraseña con la que se cifra el registro de personas la primera vez que se crea."""
    valor = os.environ.get("GEODETEC_CONTRASENA_INICIAL", "")
    if not valor:
        raise RuntimeError(
            "Falta la variable GEODETEC_CONTRASENA_INICIAL.\n"
            "Copia el archivo .env.example como .env en la carpeta del proyecto y define "
            f"la contraseña inicial:\n{CARPETA}")
    return valor


# --------------------------------------------------------------------------- modelo de prioridad
N_TRAIN = 500
SEMILLA_TRAIN = 2024
RUIDO_ETIQUETA = 0.025

VARIABLES = [
    "terrain_index",
    "vegetation_index",
    "population_density",
    "accessibility_index",
    "historical_record_count",
    "report_frequency",
]

TITULOS_VARIABLES = {
    "terrain_index": "Terreno (variación de altitud)",
    "vegetation_index": "Vegetación (prop. localidades rurales)",
    "population_density": "Densidad log10(hab/km²)",
    "accessibility_index": "Accesibilidad a centro metropolitano",
    "historical_record_count": "Registros RNPDNO log10(1+n)",
    "report_frequency": "Registros por 100 mil hab/año 2020-25",
}

CLASES = ["Baja", "Media", "Alta"]
COLORES_CLASES = ["#2ecc71", "#f1c40f", "#e74c3c"]

CENTROS = {"CDMX (Zócalo)": (-99.1332, 19.4326), "Toluca (centro)": (-99.6557, 19.2925)}

# --------------------------------------------------------------------------- zona de búsqueda
SIGMA_KM = 30.0
PISO_MODELO = 0.25
PORCENTAJE_ZONA = 0.10

# --------------------------------------------------------------------------- registro de personas
N_PERSONAS = 5
SEMILLA_PERSONAS = 2026
COLORES_PERSONAS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4"]
MIN_LONGITUD_CONTRASENA = 8

# --------------------------------------------------------------------------- criptografía
ITERACIONES_KDF = 390_000
VERIFICADOR = b"GEODETEC-OK"

# --------------------------------------------------------------------------- modelo de fosas
VARIABLES_FOSAS = VARIABLES + ["tasa_homicidios_100k", "homicidios_2019_2024"]
REPETICIONES_FOSAS = 5
