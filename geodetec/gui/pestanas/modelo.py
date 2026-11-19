"""Pestaña del modelo: métricas, matriz de confusión e importancia de variables."""
from tkinter import ttk

from ...config import CLASES
from ...figuras import fig_importancia, fig_matriz_confusion
from ...modelo import texto_metricas
from ..componentes import SelectorVistas, Tarjeta, TextoSoloLectura, panel_ancho_fijo
from .base import Pestana

ANCHO_PANEL = 380


class PestanaModelo(Pestana):
    titulo = "Modelo"
    descripcion = ("Random Forest de 300 árboles. Las etiquetas (Baja, Media, Alta) vienen de una "
                   "regla ponderada; el modelo aprende esa regla con municipios simulados y aquí "
                   "se mide qué tan bien la reproduce en los municipios reales.")

    def construir(self):
        c = self.contenido
        c.columnconfigure(0, weight=0, minsize=ANCHO_PANEL)
        c.columnconfigure(1, weight=1)
        c.rowconfigure(0, weight=1)

        izq = panel_ancho_fijo(c, ANCHO_PANEL)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        rejilla = ttk.Frame(izq)
        rejilla.pack(fill="x")
        rejilla.columnconfigure((0, 1), weight=1, uniform="t")
        self.t_acc = Tarjeta(rejilla, "Accuracy (reales)")
        self.t_cv = Tarjeta(rejilla, "Val. cruzada (simulados)")
        self.t_prec = Tarjeta(rejilla, "Precisión macro")
        self.t_rec = Tarjeta(rejilla, "Recall macro")
        for k, t in enumerate((self.t_acc, self.t_cv, self.t_prec, self.t_rec)):
            t.grid(row=k // 2, column=k % 2, sticky="nsew", padx=3, pady=3)

        ttk.Label(izq, text="Reporte completo", style="Subtitulo.TLabel").pack(
            anchor="w", pady=(12, 4))
        self.reporte = TextoSoloLectura(izq, alto=14)
        self.reporte.pack(fill="both", expand=True)

        self.selector = SelectorVistas(c, self.app, [
            {"nombre": "Matriz de confusión",
             "ayuda": "filas = prioridad según la regla; columnas = lo que predijo el modelo. La "
                      "diagonal son aciertos; fuera de ella, los errores (p. ej. municipios de "
                      "prioridad Media clasificados como Alta).",
             "fabrica": lambda: fig_matriz_confusion(self.g.metricas)},
            {"nombre": "Importancia de variables",
             "ayuda": "cuánto ayuda cada variable a separar las clases dentro del Random Forest. "
                      "Valores más altos = la variable pesa más en la decisión del modelo.",
             "fabrica": lambda: fig_importancia(self.g.modelo)},
        ])
        self.selector.grid(row=0, column=1, sticky="nsew")

    def renderizar(self):
        g, m = self.g, self.g.metricas
        self.t_cv.actualizar(f"{m['cv_media']:.1%}", f"± {m['cv_desv']:.1%}")
        self.t_prec.actualizar(f"{m['precision']:.3f}")
        self.t_rec.actualizar(f"{m['recall']:.3f}")
        reales = g.test["prioridad"].value_counts().reindex([0, 1, 2], fill_value=0)
        self.t_acc.actualizar(f"{m['accuracy']:.1%}", " · ".join(
            f"{c}: {n}" for c, n in zip(CLASES, reales)))
        self.reporte.poner(texto_metricas(m, g.train, g.test, g.umbrales))
        self.selector.refrescar()
