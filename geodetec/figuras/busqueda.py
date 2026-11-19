"""Figura de la zona de búsqueda prioritaria."""
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from .base import contorno, dibujar_mapa, marcador_leyenda


def fig_busqueda(zona, geoms, lon0, lat0, origen, color_zona="blue", color_punto="cyan",
                 cmap="YlOrRd"):
    fig = Figure(figsize=(12, 6.2))
    ax = fig.add_axes([0.01, 0.08, 0.56, 0.84])
    pc = dibujar_mapa(ax, geoms, zona["cvegeo"], zona["indice_busqueda"], cmap, Normalize())
    contorno(ax, geoms, zona.loc[zona["en_zona"], "cvegeo"], color=color_zona, ancho=2.5)
    ax.plot(lon0, lat0, marker="*", color=color_punto, markersize=22,
            markeredgecolor="black", linestyle="none")
    fig.colorbar(pc, ax=ax, fraction=0.035, label="Índice de prioridad de búsqueda")
    ax.set_title(f"Zona de búsqueda prioritaria – origen: {origen}")
    ax.legend(handles=[marcador_leyenda(color_punto, "*", "Última ubicación conocida (ficticia)"),
                       mpatches.Patch(facecolor="none", edgecolor=color_zona, linewidth=2,
                                      label="Zona prioritaria (10%)")],
              loc="lower left", fontsize=8)

    axt = fig.add_axes([0.71, 0.08, 0.28, 0.84])
    axt.axis("off")
    sel = zona[zona["en_zona"]]
    texto = "Municipios en la zona prioritaria\n(orden de prioridad)\n\n"
    for i, r in enumerate(sel.itertuples(), 1):
        texto += f"{i:2d}. {r.municipio[:26]:26s} {r.distancia_km:5.0f} km\n"
    texto += ("\nÍndice = (0.25 + 0.75·P(alta)) · cercanía\n"
              "cercanía = exp(-d² / 2·30²)\n\nP(alta): modelo aplicado a datos reales\n"
              "Ejercicio académico")
    axt.text(0, 1, texto, va="top", family="monospace", fontsize=8.5)
    return fig
