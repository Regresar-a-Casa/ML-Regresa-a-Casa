"""Figuras del análisis de registros cargados desde CSV."""
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from .base import contorno, dibujar_mapa, marcar_referencias, registrar_info

PALETA = ["#e6194b", "#4363d8", "#3cb44b", "#f58231", "#911eb4", "#42d4f4", "#f032e6",
          "#9a6324", "#469990", "#800000"]
CLASES = ["Baja", "Media", "Alta"]
MAX_FICHAS = 8      # fichas detalladas que caben en el panel de texto


def color_registro(i):
    return PALETA[i % len(PALETA)]


def fig_registros(an, mapa_pred, geoms, panel=True):
    """Mapa con la última ubicación y la zona de búsqueda de cada registro.

    Con ``panel=False`` solo se dibuja el mapa (para el reporte PDF)."""
    fig = Figure(figsize=(13, 6.6) if panel else (7.5, 7))
    ax = fig.add_axes([0.01, 0.06, 0.55, 0.86] if panel else [0.02, 0.02, 0.96, 0.92])
    dibujar_mapa(ax, geoms, mapa_pred["cvegeo"], mapa_pred["prob_alta"], "Greys",
                 Normalize(0, 2.4), borde="#9a9a9a", ancho=0.3)
    regs = an["registros"]
    for i, r in enumerate(regs):
        cves = r["zona"].loc[r["zona"]["en_zona"], "cvegeo"]
        polys = [a for c in cves for a in geoms[c]]
        ax.add_collection(PolyCollection(polys, facecolor=color_registro(i), alpha=0.2,
                                         edgecolor="none"))
        contorno(ax, geoms, cves, color=color_registro(i), ancho=2)
    conj = an["conjunto"]
    compartidos = conj.loc[conj["n_registros"] > 1, "cvegeo"]
    if len(compartidos):
        polys = [a for c in compartidos for a in geoms[c]]
        ax.add_collection(PolyCollection(polys, facecolor="none", edgecolor="black",
                                         linewidths=1.6, linestyles="--", zorder=4))
    marcar_referencias(ax, texto=False)
    for i, r in enumerate(regs):
        ax.plot(r["lon"], r["lat"], marker="o", color=color_registro(i), markersize=15,
                markeredgecolor="black", markeredgewidth=1.5, linestyle="none", zorder=7)
        ax.text(r["lon"], r["lat"], str(i + 1), ha="center", va="center", color="white",
                fontsize=8, fontweight="bold", zorder=8)
    ax.set_title("Registros del CSV – última ubicación y zona de búsqueda")
    leyenda = [Line2D([], [], marker="o", color="w", markerfacecolor="#777777",
                      markeredgecolor="black", markersize=10, label="Última ubicación (n.º)")]
    if len(compartidos):
        leyenda.append(mpatches.Patch(facecolor="none", edgecolor="black", linestyle="--",
                                      label="En la zona de 2 o más registros"))
    ax.legend(handles=leyenda, loc="lower left", fontsize=8)

    filas = conj.set_index("cvegeo")
    pred = mapa_pred.set_index("cvegeo")
    ubicados = {}
    for r in regs:
        ubicados.setdefault(r["cvegeo"], []).append(r["id"])

    def lineas(cve):
        if cve not in pred.index:
            return []
        t = [f"P(alta): {pred.loc[cve, 'prob_alta']:.2f}"]
        if cve in ubicados:
            t.append("Última ubicación de: " + ", ".join(ubicados[cve]))
        if cve in filas.index:
            t.append("En la zona de: " + ", ".join(filas.loc[cve, "ids"]))
        else:
            t.append("Fuera de las zonas de búsqueda")
        return t
    registrar_info(ax, geoms, lineas)
    if not panel:
        return fig

    axt = fig.add_axes([0.60, 0.06, 0.39, 0.86])
    axt.axis("off")
    axt.text(0, 1.0, "Registros cargados desde CSV\nEjercicio académico · no se guardan",
             va="top", fontsize=10, fontweight="bold", color="#1f3a5f")
    y = 0.88
    paso = min(0.11, 0.80 / max(1, min(len(regs), MAX_FICHAS)))
    for i, r in enumerate(regs[:MAX_FICHAS]):
        axt.add_patch(mpatches.Rectangle((0, y - paso * 0.85), 0.025, paso * 0.85,
                                         color=color_registro(i), transform=axt.transAxes))
        nombre = f" · {r['nombre']}" if r["nombre"] else ""
        txt = (f"{i + 1}. {r['id']}{nombre}\n"
               f"{r['municipio']} · {r['fecha'].isoformat()} (hace {r['dias']} días)\n"
               f"Prioridad {CLASES[r['prioridad']]} · P(alta) {r['prob_alta']:.2f} · "
               f"zona hasta {r['alcance_km']:.0f} km")
        axt.text(0.04, y, txt, va="top", fontsize=8, family="monospace")
        y -= paso
    if len(regs) > MAX_FICHAS:
        axt.text(0.04, y, f"… y {len(regs) - MAX_FICHAS} registros más (ver reporte)",
                 va="top", fontsize=8)
        y -= 0.05
    s = an["resumen"]
    axt.text(0, max(y - 0.02, 0.02),
             f"{s['municipios_en_zonas']} municipios en alguna zona · "
             f"{s['compartidos']} en zonas de 2+ registros\n"
             "Coincidir en una zona no implica relación entre casos.",
             va="top", fontsize=8, color="#555555")
    return fig


def fig_conjunto(an, maximo=15):
    """Municipios a revisar primero: suma del índice de búsqueda de todos los registros."""
    conj = an["conjunto"].sort_values("indice_total", ascending=False).head(maximo)[::-1]
    fig = Figure(figsize=(8, 5.5))
    ax = fig.add_subplot(111)
    n_max = max(2, int(an["conjunto"]["n_registros"].max()))
    colores = ["#9ecae1", "#3182bd", "#08519c", "#08306b"]
    barras = ax.barh(conj["municipio"], conj["indice_total"],
                     color=[colores[min(n, len(colores)) - 1] for n in conj["n_registros"]])
    for b, ids in zip(barras, conj["ids"]):
        ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2, ", ".join(ids),
                va="center", fontsize=8, color="#444444")
    ax.set_xlim(0, conj["indice_total"].max() * 1.35)
    ax.set_xlabel("Índice de búsqueda sumado de todos los registros")
    ax.set_title(f"Municipios a revisar primero (top {len(conj)})")
    ax.legend(handles=[mpatches.Patch(color=colores[min(n, len(colores)) - 1],
                                      label=f"En {n} zona{'s' if n > 1 else ''}")
                       for n in range(1, n_max + 1) if n <= len(colores)],
              loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


def fig_zona_registro(r, i, geoms):
    """Acercamiento a la zona de búsqueda de un registro, con el lugar de cada municipio."""
    zona = r["zona"]
    fig = Figure(figsize=(7.5, 5.6))
    ax = fig.add_axes([0.02, 0.03, 0.80, 0.90])
    pc = dibujar_mapa(ax, geoms, zona["cvegeo"], zona["indice_busqueda"], "YlOrRd",
                      Normalize(0, max(zona["indice_busqueda"].max(), 1e-6)), borde="#8a8a8a", ancho=0.4)
    sel = zona[zona["en_zona"]]
    contorno(ax, geoms, sel["cvegeo"], color=color_registro(i), ancho=2.6)
    puntos = np.vstack([a for c in sel["cvegeo"] for a in geoms[c]] + [[[r["lon"], r["lat"]]]])
    (x0, y0), (x1, y1) = puntos.min(0), puntos.max(0)
    mx, my = (x1 - x0) * 0.12 + 0.05, (y1 - y0) * 0.12 + 0.05
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)
    for k, f in enumerate(sel.itertuples(), 1):
        anillo = max(geoms[f.cvegeo], key=len)
        cx, cy = anillo[:, 0].mean(), anillo[:, 1].mean()
        ax.text(cx, cy, str(k), ha="center", va="center", fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec=color_registro(i), lw=1),
                zorder=6)
    ax.plot(r["lon"], r["lat"], marker="*", color=color_registro(i), markersize=20,
            markeredgecolor="black", linestyle="none", zorder=7)
    ax.set_title(f"Zona de búsqueda – {r['id']} (origen: {r['municipio']})", fontsize=11)
    cax = fig.add_axes([0.85, 0.12, 0.03, 0.72])
    fig.colorbar(pc, cax=cax, label="Índice de búsqueda")
    ax.legend(handles=[Line2D([], [], marker="*", color="w", markerfacecolor=color_registro(i),
                              markeredgecolor="black", markersize=14,
                              label="Última ubicación conocida"),
                       mpatches.Patch(facecolor="none", edgecolor=color_registro(i), linewidth=2,
                                      label="Zona prioritaria (n.º = orden)")],
              loc="lower left", fontsize=8)
    return fig
