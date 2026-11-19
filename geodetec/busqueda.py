"""Zona de búsqueda prioritaria: combina P(alta) del modelo con la cercanía al punto de origen.

    índice = (PISO_MODELO + (1 - PISO_MODELO) · P(alta)) · exp(-d² / 2·SIGMA_KM²)

La zona prioritaria es el ``PORCENTAJE_ZONA`` de municipios con mayor índice. Los tres
parámetros (σ, piso y porcentaje) se pueden cambiar en cada llamada; por omisión se usan los de
``config``.
"""
import numpy as np
from matplotlib.path import Path

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


def zona_busqueda_punto(mapa_pred, mun, lon0, lat0, sigma_km=SIGMA_KM, piso=PISO_MODELO,
                        porcentaje=PORCENTAJE_ZONA):
    """Calcula ``indice_busqueda`` y ``en_zona`` para cada municipio, ordenados de mayor a menor.

    - ``sigma_km``: qué tan rápido decae la cercanía con la distancia.
    - ``piso``: peso mínimo del modelo (0 = solo cuenta P(alta); 1 = solo cuenta la cercanía).
    - ``porcentaje``: fracción de municipios que forman la zona prioritaria (al menos uno).
    """
    if sigma_km <= 0:
        raise ValueError("sigma_km debe ser mayor que 0.")
    if not 0 <= piso <= 1:
        raise ValueError("piso debe estar entre 0 y 1.")
    if not 0 < porcentaje <= 1:
        raise ValueError("porcentaje debe estar entre 0 (excluido) y 1.")
    df = mapa_pred.merge(mun[["cvegeo", "lon", "lat"]], on="cvegeo")
    df["distancia_km"] = distancia_km(lon0, lat0, df["lon"], df["lat"])
    cercania = np.exp(-df["distancia_km"] ** 2 / (2 * sigma_km ** 2))
    df["indice_busqueda"] = (piso + (1 - piso) * df["prob_alta"]) * cercania
    n = max(1, int(np.ceil(porcentaje * len(df))))
    df = df.sort_values("indice_busqueda", ascending=False).reset_index(drop=True)
    df["en_zona"] = df.index < n
    return df


class LocalizadorMunicipios:
    """Encuentra el municipio que contiene un punto (lon, lat).

    Precalcula un ``Path`` y una caja envolvente por anillo, así cada consulta solo prueba los
    pocos polígonos cuya caja contiene el punto (es lo bastante rápido para seguir al ratón).
    """

    def __init__(self, geoms):
        self._anillos = []
        for cve, anillos in geoms.items():
            for a in anillos:
                a = np.asarray(a)
                caja = (a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max())
                self._anillos.append((cve, caja, Path(a)))

    def buscar(self, lon, lat):
        """Clave ``cvegeo`` del municipio que contiene el punto, o ``None`` si cae fuera."""
        if lon is None or lat is None:
            return None
        for cve, (x0, x1, y0, y1), ruta in self._anillos:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and ruta.contains_point((lon, lat)):
                return cve
        return None


_LOCALIZADORES = {}


def localizador(geoms):
    """``LocalizadorMunicipios`` reutilizable para un mismo diccionario de geometrías."""
    clave = id(geoms)
    if clave not in _LOCALIZADORES:
        _LOCALIZADORES.clear()          # solo hay un juego de geometrías a la vez
        _LOCALIZADORES[clave] = (geoms, LocalizadorMunicipios(geoms))
    return _LOCALIZADORES[clave][1]
