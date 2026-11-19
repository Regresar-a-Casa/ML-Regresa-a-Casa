"""Carga de municipios reales, construcción de variables, regla de prioridad y datos simulados."""
import json
import os

import numpy as np
import pandas as pd

from .config import CARPETA_DATOS, GEOJSON_PATH, N_TRAIN, RUIDO_ETIQUETA, SEMILLA_TRAIN


def cargar_municipios(ruta=GEOJSON_PATH):
    """Lee el GeoJSON de municipios.

    Devuelve ``(mun, geoms)``: un DataFrame con las propiedades de cada municipio (ordenado por
    ``cvegeo``) y un diccionario ``cvegeo -> [arreglos (n, 2) con el anillo exterior]``.
    """
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró {os.path.basename(ruta)}. Debe estar en la carpeta de "
            f"datos del proyecto:\n{CARPETA_DATOS}")
    with open(ruta, encoding="utf-8") as f:
        gj = json.load(f)
    filas, geoms = [], {}
    for feat in gj["features"]:
        p = feat["properties"]
        filas.append(p)
        g = feat["geometry"]
        poligonos = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        geoms[p["cvegeo"]] = [np.array(poly[0]) for poly in poligonos]
    mun = pd.DataFrame(filas)
    if "registros_rnpdno" not in mun.columns:
        raise ValueError("El archivo edomex_municipios.geojson es de una versión anterior: "
                         "usa el que acompaña a esta versión del programa.")
    mun["population_density"] = (mun["poblacion_2020"] / mun["area_km2"]).round(2)
    return mun.sort_values("cvegeo").reset_index(drop=True), geoms


def variables_reales(mun):
    """Construye las 6 variables del modelo a partir de las columnas del GeoJSON."""
    df = mun[["cvegeo", "municipio", "zona_metropolitana"]].copy()
    df["terrain_index"] = np.clip(mun["altitud_desv_m"] / 500, 0, 1).round(4)
    df["vegetation_index"] = mun["prop_localidades_rurales"].round(4)
    df["population_density"] = mun["population_density"]
    df["accessibility_index"] = (1 - np.clip(mun["dist_centro_km"] / 110, 0, 1)).round(4)
    df["historical_record_count"] = mun["registros_rnpdno"].astype(int)
    df["report_frequency"] = mun["tasa_anual_100k_2020_2025"].round(2)
    return df


def puntaje_prioridad(df):
    """Regla determinista (0 a 1) con la que se etiquetan tanto simulados como reales."""
    urb = np.clip((np.log10(df["population_density"]) - 1) / 3.3, 0, 1)
    hist = np.clip(np.log1p(df["historical_record_count"]) / np.log1p(1000), 0, 1)
    rep = np.clip(df["report_frequency"] / 15, 0, 1)
    veg = df["vegetation_index"]
    acc = 1 - np.abs(df["accessibility_index"] - 0.5) * 2
    ter = df["terrain_index"]
    return (0.30 * hist + 0.20 * rep + 0.20 * veg + 0.15 * (1 - urb)
            + 0.10 * acc + 0.05 * ter)


def etiquetar(puntaje, umbrales):
    """0 = Baja, 1 = Media, 2 = Alta según los dos umbrales."""
    return np.digitize(puntaje, umbrales)


def simular_entrenamiento(n=N_TRAIN, semilla=SEMILLA_TRAIN):
    """Genera ``n`` municipios sintéticos etiquetados; los umbrales son sus terciles."""
    rng = np.random.default_rng(semilla)
    urb = rng.beta(1.3, 2.0, n)
    densidad = 10 ** (1.3 + urb * 3.0 + rng.normal(0, 0.12, n))
    area = np.exp(rng.normal(4.67, 1.1, n))
    poblacion = densidad * area
    vegetacion = np.clip(0.97 - 0.55 * urb ** 2 + rng.normal(0, 0.07, n), 0, 1)
    desv_alt = rng.gamma(1.5, 85, n) * (1.25 - 0.8 * urb)
    distancia = np.clip(rng.normal(62 - 45 * urb, 14, n), 1, 110)
    tasa = np.exp(rng.normal(np.log(4.8), 0.5, n)) * (0.8 + 0.5 * urb)
    anios_acumulados = np.exp(rng.normal(np.log(8.8), 0.3, n))
    historicos = rng.poisson(tasa * poblacion / 1e5 * anios_acumulados)

    df = pd.DataFrame({
        "cvegeo": [f"SIM-{i:04d}" for i in range(n)],
        "municipio": [f"Municipio sintético {i}" for i in range(n)],
        "zona_metropolitana": "Simulado",
        "terrain_index": np.clip(desv_alt / 500, 0, 1).round(4),
        "vegetation_index": vegetacion.round(4),
        "population_density": densidad.round(2),
        "accessibility_index": (1 - distancia / 110).round(4),
        "historical_record_count": historicos,
        "report_frequency": tasa.round(2),
    })
    puntaje = puntaje_prioridad(df) + rng.normal(0, RUIDO_ETIQUETA, n)
    umbrales = np.quantile(puntaje, [1 / 3, 2 / 3])
    df["puntaje"] = puntaje.round(4)
    df["prioridad"] = etiquetar(puntaje, umbrales)
    return df, umbrales


def preparar_prueba_real(mun, umbrales):
    """Etiqueta los municipios reales con la misma regla y los umbrales del entrenamiento."""
    df = variables_reales(mun)
    df["puntaje"] = puntaje_prioridad(df).round(4)
    df["prioridad"] = etiquetar(df["puntaje"], umbrales)
    return df
