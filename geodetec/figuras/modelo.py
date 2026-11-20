"""Figuras del modelo de prioridad: variables, evaluación, importancia, distribuciones y mapa."""
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.figure import Figure

from ..config import CLASES, COLORES_CLASES, TITULOS_VARIABLES, VARIABLES

# Cómo mostrar el valor original de cada variable en el recuadro informativo de la GUI
ETIQUETAS_INFO = {
    "terrain_index": ("Índice de terreno", "{:.2f}"),
    "vegetation_index": ("Índice de vegetación", "{:.2f}"),
    "population_density": ("Densidad", "{:,.0f} hab/km²"),
    "accessibility_index": ("Accesibilidad", "{:.2f}"),
    "historical_record_count": ("Registros RNPDNO", "{:,.0f}"),
    "report_frequency": ("Registros por 100 mil hab/año", "{:.1f}"),
}


def _clase(valor):
    return CLASES[int(valor)]
from .base import dibujar_mapa, marcar_referencias


def _transformar(var, serie):
    """Escala logarítmica para las variables muy sesgadas."""
    if var == "population_density":
        return np.log10(serie)
    if var == "historical_record_count":
        return np.log10(1 + serie)
    return serie


def fig_variables_reales(test, geoms):
    fig = Figure(figsize=(14, 8.5))
    for k, var in enumerate(VARIABLES, 1):
        ax = fig.add_subplot(2, 3, k)
        etiqueta, formato = ETIQUETAS_INFO[var]
        pc = dibujar_mapa(ax, geoms, test["cvegeo"], _transformar(var, test[var]),
                          "viridis", Normalize(), ancho=0.2, etiqueta=etiqueta, formato=formato,
                          valores_info=test[var])
        fig.colorbar(pc, ax=ax, fraction=0.04)
        ax.set_title(TITULOS_VARIABLES[var], fontsize=10)
    fig.suptitle("Datos REALES del conjunto de prueba – 125 municipios del Estado de México\n"
                 "Fuentes: INEGI (Censo 2020, catálogo de localidades) y RNPDNO (corte 30/11/2025)")
    fig.tight_layout()
    return fig


def fig_matriz_confusion(m):
    fig = Figure(figsize=(5.5, 4.5))
    ax = fig.add_subplot(111)
    M = m["matriz"]
    im = ax.imshow(M, cmap="Blues")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, M[i, j], ha="center", va="center", fontsize=13,
                    color="white" if M[i, j] > M.max() / 2 else "black")
    ax.set_xticks(range(3), CLASES)
    ax.set_yticks(range(3), CLASES)
    ax.set_xlabel("Predicción del modelo")
    ax.set_ylabel("Etiqueta según la regla (datos reales)")
    ax.set_title(f"Matriz de confusión – {M.sum()} municipios reales")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    return fig


def fig_importancia(metricas):
    """Importancia por permutación: caída del accuracy en los reales al desordenar cada variable."""
    imp = pd.Series(metricas["importancia"]).reindex(VARIABLES).sort_values()
    desv = pd.Series(metricas["importancia_desv"]).reindex(imp.index)
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    ax.barh(imp.index, imp.values, xerr=desv.values, color="#3498db", ecolor="#555555",
            capsize=3)
    for i, (v, d) in enumerate(zip(imp.values, desv.values)):
        ax.text(max(v, 0) + d + 0.006, i, f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlim(min(0, imp.min() * 1.2), (imp + desv).max() * 1.25)
    ax.set_xlabel("Caída del accuracy al desordenar la variable (municipios reales)")
    ax.set_title("Importancia por permutación – red neuronal")
    fig.tight_layout()
    return fig


def fig_curva_aprendizaje(modelo):
    """Pérdida (entropía cruzada) en cada época de retropropagación."""
    red = modelo.named_steps["red"]
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    ax.plot(range(1, len(red.loss_curve_) + 1), red.loss_curve_, color="#3498db", lw=2)
    ax.axhline(red.loss_curve_[-1], color="#999999", ls="--", lw=1)
    ax.annotate(f"pérdida final {red.loss_curve_[-1]:.3f}",
                (len(red.loss_curve_), red.loss_curve_[-1]), xytext=(0, 12),
                textcoords="offset points", ha="right", fontsize=9, color="#555555")
    ax.set_xlabel("Época (pasadas completas por los 500 municipios simulados)")
    ax.set_ylabel("Pérdida (entropía cruzada + L2)")
    ax.set_title(f"Entrenamiento de la red – {red.n_iter_} épocas de retropropagación")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def fig_distribuciones(train, test):
    fig = Figure(figsize=(11, 6.5))
    for k, var in enumerate(VARIABLES, 1):
        ax = fig.add_subplot(2, 3, k)
        a, b = _transformar(var, train[var]), _transformar(var, test[var])
        bins = np.histogram_bin_edges(np.concatenate([a, b]), bins=18)
        ax.hist(a, bins=bins, alpha=0.55, density=True, label="Entrenamiento (simulado)",
                color="#3498db")
        ax.hist(b, bins=bins, alpha=0.55, density=True, label="Prueba (real)", color="#e67e22")
        ax.set_title(TITULOS_VARIABLES[var], fontsize=9)
        ax.tick_params(labelsize=7)
    fig.axes[0].legend(fontsize=7)
    fig.suptitle("Distribuciones: datos simulados de entrenamiento vs datos reales de prueba")
    fig.tight_layout()
    return fig


def fig_mapa(mapa_pred, geoms):
    cmap = ListedColormap(COLORES_CLASES)
    fig = Figure(figsize=(15, 5.6))
    cves = mapa_pred["cvegeo"]
    ax1 = fig.add_subplot(131)
    dibujar_mapa(ax1, geoms, cves, mapa_pred["prioridad"], cmap, Normalize(0, 2),
                 etiqueta="Prioridad (regla)", formato=_clase)
    ax1.set_title("Prioridad según la regla (datos reales)")
    ax2 = fig.add_subplot(132)
    dibujar_mapa(ax2, geoms, cves, mapa_pred["prediccion"], cmap, Normalize(0, 2),
                 etiqueta="Prioridad (modelo)", formato=_clase)
    ax2.set_title("Prioridad predicha por el modelo")
    ax3 = fig.add_subplot(133)
    pc = dibujar_mapa(ax3, geoms, cves, mapa_pred["prob_alta"], "inferno", Normalize(0, 1),
                      etiqueta="P(alta)")
    for ax in (ax1, ax2, ax3):
        marcar_referencias(ax, tamano=5, texto=ax is ax1)
    fig.colorbar(pc, ax=ax3, fraction=0.04)
    ax3.set_title("Mapa de calor: P(prioridad alta)")
    fig.legend(handles=[mpatches.Patch(color=c, label=l) for c, l in zip(COLORES_CLASES, CLASES)],
               loc="lower center", ncol=3)
    acierto = (mapa_pred["prioridad"] == mapa_pred["prediccion"]).mean()
    fig.suptitle("Estado de México – modelo entrenado con simulados aplicado a datos reales – "
                 f"coincidencia {acierto:.1%}")
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    return fig
