"""Primitivas de dibujo compartidas por todas las figuras (mapas coropléticos y leyendas)."""
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

from ..config import CENTROS

LATITUD_REFERENCIA = 19.4   # corrige la deformación lon/lat a la latitud del Edomex
ATRIBUTO_INFO = "_geodetec_info"   # datos que la GUI usa para los recuadros al pasar el ratón


def _formatear(valor, formato):
    if callable(formato):
        return formato(valor)
    try:
        return formato.format(valor)
    except (TypeError, ValueError):
        return str(valor)


def registrar_info(ax, geoms, lineas):
    """Asocia a un mapa la función ``lineas(cve) -> list[str]`` con la información de cada
    municipio. La interfaz la muestra en un recuadro al pasar el ratón; no cambia el dibujo."""
    setattr(ax, ATRIBUTO_INFO, {"geoms": geoms, "lineas": lineas})


def info_mapa(ax):
    """Información registrada con ``registrar_info`` (o ``None`` si el eje no es un mapa)."""
    return getattr(ax, ATRIBUTO_INFO, None)


def dibujar_mapa(ax, geoms, cves, valores, cmap, norm, borde="#555555", ancho=0.3,
                 etiqueta=None, formato="{:.2f}", valores_info=None):
    """Pinta cada municipio con su valor y ajusta los ejes a la extensión del estado.

    ``etiqueta``/``formato``/``valores_info`` solo sirven para el recuadro informativo de la GUI
    (``valores_info`` permite mostrar el valor original cuando se pinta uno transformado).
    """
    if etiqueta is not None:
        mostrados = dict(zip(cves, valores if valores_info is None else valores_info))
        registrar_info(ax, geoms, lambda c: [f"{etiqueta}: {_formatear(mostrados[c], formato)}"]
                       if c in mostrados else [])
    polys, vals = [], []
    for cve, v in zip(cves, valores):
        for anillo in geoms[cve]:
            polys.append(anillo)
            vals.append(v)
    pc = PolyCollection(polys, array=np.array(vals, dtype=float), cmap=cmap, norm=norm,
                        edgecolor=borde, linewidth=ancho)
    ax.add_collection(pc)
    todos = np.vstack([a for c in geoms for a in geoms[c]])
    ax.set_xlim(todos[:, 0].min() - 0.03, todos[:, 0].max() + 0.03)
    ax.set_ylim(todos[:, 1].min() - 0.03, todos[:, 1].max() + 0.03)
    ax.set_aspect(1 / np.cos(np.radians(LATITUD_REFERENCIA)))
    ax.set_xticks([])
    ax.set_yticks([])
    return pc


def contorno(ax, geoms, cves, color="blue", ancho=2.0):
    """Dibuja solo el borde de un conjunto de municipios."""
    polys = [a for c in cves for a in geoms[c]]
    ax.add_collection(PolyCollection(polys, facecolor="none", edgecolor=color, linewidth=ancho))


def marcador_leyenda(color, marker, label):
    """Elemento de leyenda con un marcador suelto (sin línea)."""
    return Line2D([], [], color=color, marker=marker, markersize=12, markeredgecolor="black",
                  linestyle="none", label=label)


def marcar_referencias(ax, tamano=6, texto=True):
    """Marca los puntos de referencia de ``config.CENTROS`` (CDMX y Toluca) para orientarse."""
    for nombre, (lon, lat) in CENTROS.items():
        ax.plot(lon, lat, marker="s", color="white", markersize=tamano, markeredgecolor="black",
                markeredgewidth=1, linestyle="none", zorder=5)
        if texto:
            ax.annotate(nombre.split(" (")[0], (lon, lat), xytext=(5, 4),
                        textcoords="offset points", fontsize=7.5, zorder=5,
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
