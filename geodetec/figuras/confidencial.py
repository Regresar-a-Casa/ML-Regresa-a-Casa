"""Figuras de las secciones de acceso restringido: personas (ficticias) y fosas (datos reales)."""
import matplotlib.patches as mpatches
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.figure import Figure

from ..busqueda import zona_busqueda_punto
from .base import contorno, dibujar_mapa


def fig_fosas(res, metricas, geoms):
    fig = Figure(figsize=(13, 6.8))
    ax = fig.add_axes([0.01, 0.06, 0.55, 0.86])
    pc = dibujar_mapa(ax, geoms, res["cvegeo"], res["prob_fosa"], "magma_r",
                      Normalize(0, max(0.5, res["prob_fosa"].max())), ancho=0.25)
    contorno(ax, geoms, res.loc[res["con_fosa"] == 1, "cvegeo"], color="#00bcd4", ancho=2.2)
    fig.colorbar(pc, ax=ax, fraction=0.035, label="Probabilidad estimada de fosa (fuera de muestra)")
    ax.set_title("Fosas clandestinas – probabilidad por municipio (datos reales)")
    ax.legend(handles=[mpatches.Patch(facecolor="none", edgecolor="#00bcd4", linewidth=2,
                                      label="Fosa registrada (CNB, 2018-2023)")],
              loc="lower left", fontsize=8)
    axt = fig.add_axes([0.62, 0.06, 0.37, 0.86])
    axt.axis("off")
    t = "ACCESO AUTORIZADO – sección confidencial\n\n"
    t += "Municipios con mayor probabilidad\n"
    t += f"{'#':>2}  {'Municipio':24s} {'Prob.':>5}  Fosa reg.\n"
    for i, r in enumerate(res.head(20).itertuples(), 1):
        t += f"{i:2d}. {r.municipio[:24]:24s} {r.prob_fosa:5.2f}  {'sí' if r.con_fosa else '—'}\n"
    t += (f"\nAUC Random Forest: {metricas['auc_rf']:.2f} · logística: {metricas['auc_logistica']:.2f}\n"
          f"Fosas registradas en el top 20: {metricas['aciertos_top20']} de {metricas['positivos']}\n"
          "'—' = sin fosa registrada: candidato a revisión,\nno un hallazgo.")
    axt.text(0, 1, t, va="top", family="monospace", fontsize=8.3)
    return fig


def fig_personas(personas, mapa_pred, mun, geoms):
    fig = Figure(figsize=(13, 6.6))
    ax = fig.add_axes([0.01, 0.06, 0.55, 0.86])
    dibujar_mapa(ax, geoms, mapa_pred["cvegeo"], mapa_pred["prob_alta"], "Greys",
                 Normalize(0, 1.6), borde="#9a9a9a", ancho=0.3)
    for p in personas:
        zona = zona_busqueda_punto(mapa_pred, mun, p["lon"], p["lat"])
        cves = zona.loc[zona["en_zona"], "cvegeo"]
        polys = [a for c in cves for a in geoms[c]]
        ax.add_collection(PolyCollection(polys, facecolor=p["color"], alpha=0.22, edgecolor="none"))
        contorno(ax, geoms, cves, color=p["color"], ancho=2.2)
    for p in personas:
        ax.plot(p["lon"], p["lat"], marker="o", color=p["color"], markersize=15,
                markeredgecolor="black", markeredgewidth=1.5, linestyle="none")
        ax.text(p["lon"], p["lat"], p["id"][-1], ha="center", va="center",
                color="white", fontsize=8, fontweight="bold")
    ax.set_title("Última ubicación conocida y zona de búsqueda por persona")

    axt = fig.add_axes([0.59, 0.06, 0.40, 0.86])
    axt.axis("off")
    axt.text(0, 1.0, "REGISTRO CONFIDENCIAL – acceso autorizado\nDatos 100% ficticios",
             va="top", fontsize=10, fontweight="bold", color="#8b0000")
    y = 0.88
    for p in personas:
        axt.add_patch(mpatches.Rectangle((0, y - 0.115), 0.025, 0.125, color=p["color"],
                                         transform=axt.transAxes))
        txt = (f"{p['id']}  ·  Folio {p['folio']}\n"
               f"{p['nombre']}, {p['edad']} años, {p['sexo']}\n"
               f"Desaparición: {p['fecha_desaparicion']}\n"
               f"Última ubicación: {p['municipio']}\n"
               f"({p['lat']:.4f}, {p['lon']:.4f})")
        axt.text(0.04, y, txt, va="top", fontsize=8.3, family="monospace")
        y -= 0.175
    return fig
