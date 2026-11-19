"""Zona de búsqueda prioritaria: combina P(alta) del modelo con la cercanía al punto de origen.

    índice = (PISO_MODELO + (1 - PISO_MODELO) · P(alta)) · exp(-d² / 2·SIGMA_KM²)

La zona prioritaria es el ``PORCENTAJE_ZONA`` de municipios con mayor índice.
"""
import numpy as np

from .config import PISO_MODELO, PORCENTAJE_ZONA, SIGMA_KM


def distancia_km(lon1, lat1, lon2, lat2):
    """Distancia de gran círculo (haversine) en kilómetros."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def zona_busqueda(mapa_pred, mun, cve_origen):
    """Zona de búsqueda tomando como origen el centroide del municipio ``cve_origen``."""
    o = mun[mun["cvegeo"] == cve_origen].iloc[0]
    return zona_busqueda_punto(mapa_pred, mun, o["lon"], o["lat"])


def zona_busqueda_punto(mapa_pred, mun, lon0, lat0):
    """Calcula ``indice_busqueda`` y ``en_zona`` para cada municipio, ordenados de mayor a menor."""
    df = mapa_pred.merge(mun[["cvegeo", "lon", "lat"]], on="cvegeo")
    df["distancia_km"] = distancia_km(lon0, lat0, df["lon"], df["lat"])
    cercania = np.exp(-df["distancia_km"] ** 2 / (2 * SIGMA_KM ** 2))
    df["indice_busqueda"] = (PISO_MODELO + (1 - PISO_MODELO) * df["prob_alta"]) * cercania
    n = int(np.ceil(PORCENTAJE_ZONA * len(df)))
    df = df.sort_values("indice_busqueda", ascending=False).reset_index(drop=True)
    df["en_zona"] = df.index < n
    return df
