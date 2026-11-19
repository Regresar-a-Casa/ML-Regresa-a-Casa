"""Figura de la zona de búsqueda prioritaria."""
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from ..config import PISO_MODELO, PORCENTAJE_ZONA, SIGMA_KM
from .base import contorno, dibujar_mapa, marcador_leyenda, marcar_referencias, registrar_info

MAX_LISTA = 22   # renglones que caben en el panel de texto


def fig_busqueda(zona, geoms, lon0, lat0, origen, color_zona="blue", color_punto="cyan",
                 cmap="YlOrRd", sigma_km=SIGMA_KM, piso=PISO_MODELO, porcentaje=PORCENTAJE_ZONA,
                 referencias=True):
    """Mapa del índice de búsqueda con la zona prioritaria y la lista de sus municipios.

    ``sigma_km``, ``piso`` y ``porcentaje`` deben ser los mismos con los que se calculó ``zona``
    (solo se usan para los textos).
    """
    fig = Figure(figsize=(12, 6.2))
    ax = fig.add_axes([0.01, 0.08, 0.56, 0.84])
    pc = dibujar_mapa(ax, geoms, zona["cvegeo"], zona["indice_busqueda"], cmap, Normalize())
    contorno(ax, geoms, zona.loc[zona["en_zona"], "cvegeo"], color=color_zona, ancho=2.5)
    if referencias:
        marcar_referencias(ax)
    ax.plot(lon0, lat0, marker="*", color=color_punto, markersize=22,
            markeredgecolor="black", linestyle="none", zorder=6)
    fig.colorbar(pc, ax=ax, fraction=0.035, label="Índice de prioridad de búsqueda")
    ax.set_title(f"Zona de búsqueda prioritaria – origen: {origen}")
    ax.legend(handles=[marcador_leyenda(color_punto, "*", "Última ubicación conocida (ficticia)"),
                       mpatches.Patch(facecolor="none", edgecolor=color_zona, linewidth=2,
                                      label=f"Zona prioritaria ({porcentaje:.0%})")],
              loc="lower left", fontsize=8)

    filas = zona.set_index("cvegeo")
    posicion = {c: i for i, c in enumerate(zona["cvegeo"], 1)}

    def lineas(cve):
        if cve not in filas.index:
            return []
        r = filas.loc[cve]
        return [f"Índice: {r['indice_busqueda']:.3f}  (lugar {posicion[cve]} de {len(zona)})",
                f"P(alta): {r['prob_alta']:.2f} · distancia: {r['distancia_km']:.0f} km",
                "En la zona prioritaria" if r["en_zona"] else "Fuera de la zona prioritaria"]
    registrar_info(ax, geoms, lineas)

    axt = fig.add_axes([0.71, 0.08, 0.28, 0.84])
    axt.axis("off")
    sel = zona[zona["en_zona"]]
    texto = "Municipios en la zona prioritaria\n(orden de prioridad)\n\n"
    for i, r in enumerate(sel.head(MAX_LISTA).itertuples(), 1):
        texto += f"{i:2d}. {r.municipio[:26]:26s} {r.distancia_km:5.0f} km\n"
    if len(sel) > MAX_LISTA:
        texto += f"    … y {len(sel) - MAX_LISTA} municipios más\n"
    texto += (f"\nÍndice = ({piso:.2f} + {1 - piso:.2f}·P(alta)) · cercanía\n"
              f"cercanía = exp(-d² / 2·{sigma_km:g}²)\n\nP(alta): modelo aplicado a datos reales\n"
              "Ejercicio académico")
    axt.text(0, 1, texto, va="top", family="monospace", fontsize=8.5)
    return fig
