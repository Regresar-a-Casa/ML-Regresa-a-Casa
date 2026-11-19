"""Primitivas de dibujo compartidas por todas las figuras (mapas coropléticos y leyendas)."""
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

LATITUD_REFERENCIA = 19.4   # corrige la deformación lon/lat a la latitud del Edomex


def dibujar_mapa(ax, geoms, cves, valores, cmap, norm, borde="#555555", ancho=0.3):
    """Pinta cada municipio con su valor y ajusta los ejes a la extensión del estado."""
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
