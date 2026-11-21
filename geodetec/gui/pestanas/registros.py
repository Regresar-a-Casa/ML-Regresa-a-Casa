"""Pestaña de análisis de registros cargados desde un archivo CSV.

El archivo se lee y se analiza solo en memoria (no se guarda en la base de datos). Para cada
registro se calcula su zona de búsqueda con el mismo índice de la pestaña Zona de búsqueda y luego
se analizan las zonas en conjunto (municipios compartidos, registros cercanos).
"""
import os
from datetime import date
from tkinter import filedialog, messagebox, ttk

from matplotlib.figure import Figure

from ...figuras import color_registro, fig_conjunto, fig_registros
from ...registros import (EJEMPLO_PATH, ErrorRegistros, analizar_registros, leer_csv,
                          texto_analisis, validar_registros)
from ...reportes import generar_reporte_registros
from ..componentes import (SelectorVistas, TextoSoloLectura, etiqueta_ajustable,
                           panel_ancho_fijo, seguro)
from .base import Pestana

ANCHO_PANEL = 380
CLASES = ["Baja", "Media", "Alta"]
FORMATO = ("Columnas: id y fecha_desaparicion (obligatorias), y municipio o lat/lon. "
           "Opcionales: nombre, edad, sexo, descripcion. Separador , o ; · UTF-8 o ANSI.")


def _figura_vacia():
    fig = Figure(figsize=(8, 5))
    fig.text(0.5, 0.5, "Carga un archivo CSV o usa el ejemplo para ver el análisis.",
             ha="center", va="center", fontsize=12, color="#5f6b7a")
    return fig


class PestanaRegistros(Pestana):
    titulo = "Registros (CSV)"
    descripcion = ("Carga un archivo CSV con registros de última ubicación conocida. El sistema "
                   "valida cada renglón, ubica el municipio, calcula la zona de búsqueda de cada "
                   "registro y analiza las zonas en conjunto. Los datos solo se usan en memoria: "
                   "no se guardan. Con «Generar reporte PDF» obtienes un documento con cada gráfica "
                   "explicada e interpretada. El archivo de ejemplo tiene 3 registros ficticios.")

    def construir(self):
        self.an = self.avisos = None
        self.archivo = None
        c = self.contenido
        c.columnconfigure(0, weight=0, minsize=ANCHO_PANEL)
        c.columnconfigure(1, weight=1)
        c.rowconfigure(0, weight=1)

        izq = panel_ancho_fijo(c, ANCHO_PANEL)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        tarjeta = ttk.Frame(izq, style="Tarjeta.TFrame", padding=12)
        tarjeta.pack(fill="x")
        ttk.Label(tarjeta, text="Archivo", style="TarjetaTitulo.TLabel").pack(anchor="w")
        botones = ttk.Frame(tarjeta, style="Tarjeta.TFrame")
        botones.pack(fill="x", pady=(8, 0))
        botones.columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(botones, text="Cargar CSV…", command=self.cargar).grid(
            row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(botones, text="Usar ejemplo", command=self.usar_ejemplo).grid(
            row=0, column=1, sticky="ew", padx=(3, 0))
        self.b_exportar = ttk.Button(botones, text="Generar reporte PDF…",
                                     command=self.exportar, state="disabled")
        self.b_exportar.grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=(6, 0))
        self.b_limpiar = ttk.Button(botones, text="Limpiar", command=self.limpiar,
                                    state="disabled")
        self.b_limpiar.grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=(6, 0))
        self.lbl_archivo = etiqueta_ajustable(tarjeta, "Ningún archivo cargado.", "Tarjeta.TLabel")
        self.lbl_archivo.pack(anchor="w", fill="x", pady=(8, 0))
        self.lbl_error = etiqueta_ajustable(tarjeta, "", "TarjetaError.TLabel")
        self.lbl_error.pack(anchor="w", fill="x")
        etiqueta_ajustable(tarjeta, FORMATO, "Pista.TLabel").pack(anchor="w", fill="x",
                                                                  pady=(6, 0))

        ttk.Label(izq, text="Registros (doble clic: ver en Zona de búsqueda)",
                  style="Subtitulo.TLabel").pack(anchor="w", pady=(12, 4))
        columnas = (("n", "#", 30), ("id", "Id", 70), ("municipio", "Municipio", 150),
                    ("prioridad", "Prioridad", 70), ("dias", "Días", 50))
        self.tabla = ttk.Treeview(izq, columns=[k for k, _, _ in columnas], show="headings",
                                  height=4, selectmode="browse")
        for k, titulo, ancho in columnas:
            self.tabla.heading(k, text=titulo)
            self.tabla.column(k, width=ancho, anchor="w", stretch=k == "municipio")
        self.tabla.pack(fill="x")
        self.tabla.bind("<Double-1>", lambda _: self.ver_en_busqueda())

        ttk.Label(izq, text="Reporte", style="Subtitulo.TLabel").pack(anchor="w", pady=(12, 4))
        self.reporte = TextoSoloLectura(izq, alto=10, ajustar=True)
        self.reporte.pack(fill="both", expand=True)

        self.selector = SelectorVistas(c, self.app, [
            {"nombre": "Mapa de registros",
             "ayuda": "cada color es un registro: el círculo numerado es su última ubicación y "
                      "el área sombreada su zona de búsqueda. La línea punteada negra marca los "
                      "municipios que están en la zona de 2 o más registros.",
             "fabrica": lambda: (fig_registros(self.an, self.g.mapa_pred, self.g.geoms)
                                 if self.an else _figura_vacia())},
            {"nombre": "Municipios a revisar primero",
             "ayuda": "suma del índice de búsqueda de todos los registros. Arriba quedan los "
                      "municipios que convienen a varios registros a la vez; a la derecha de "
                      "cada barra, los registros en cuya zona aparece.",
             "fabrica": lambda: fig_conjunto(self.an) if self.an else _figura_vacia()},
        ])
        self.selector.grid(row=0, column=1, sticky="nsew")
        self.selector.panel.aviso("Carga un archivo CSV o usa el ejemplo para ver el análisis.")

    def renderizar(self):
        if self.an is not None:            # el modelo cambió: recalcular con lo ya cargado
            self._analizar(self.archivo)

    # ------------------------------------------------------------------ acciones
    def cargar(self):
        ruta = filedialog.askopenfilename(
            parent=self, title="Selecciona el archivo CSV de registros",
            filetypes=[("Archivos CSV", "*.csv"), ("Texto", "*.txt"), ("Todos", "*.*")])
        if ruta:
            self._analizar(ruta)

    def usar_ejemplo(self):
        self._analizar(EJEMPLO_PATH)

    @seguro
    def _analizar(self, ruta):
        if not self.app.listo:
            return
        self.app.ocupado(True)
        try:
            avisos = []
            try:
                df = leer_csv(ruta)
                regs, avisos = validar_registros(df, self.g.mun, self.g.geoms)
                an = analizar_registros(regs, self.g.mapa_pred, self.g.mun)
            except (ErrorRegistros, OSError) as e:
                self.lbl_error.configure(text=str(e))
                self.reporte.poner("\n".join(f"renglón {r} [{n}]: {m}" for r, n, m in avisos))
                return
            self.archivo, self.an, self.avisos = ruta, an, avisos
            self.lbl_error.configure(text="")
            errores = sum(1 for a in avisos if a[1] == "error")
            self.lbl_archivo.configure(
                text=f"{os.path.basename(ruta)} · {len(regs)} registros válidos"
                     + (f" · {errores} descartados" if errores else "")
                     + (f" · {len(avisos) - errores} avisos" if len(avisos) > errores else ""))
            self._llenar_tabla()
            self.reporte.poner(texto_analisis(an, avisos))
            self.b_exportar.configure(state="normal")
            self.b_limpiar.configure(state="normal")
            self.selector.refrescar()
            self.app.estado(f"Análisis de registros listo · {len(regs)} registros.")
        finally:
            self.app.ocupado(False)

    def _llenar_tabla(self):
        self.tabla.delete(*self.tabla.get_children())
        regs = self.an["registros"]
        self.tabla.configure(height=min(max(len(regs), 3), 8))
        for i, r in enumerate(regs):
            tag = f"r{i}"
            self.tabla.insert("", "end", iid=str(i), tags=(tag,), values=(
                i + 1, r["id"], r["municipio"], CLASES[r["prioridad"]], r["dias"]))
            self.tabla.tag_configure(tag, background=color_registro(i), foreground="white")

    def limpiar(self):
        self.an = self.avisos = self.archivo = None
        self.tabla.delete(*self.tabla.get_children())
        self.reporte.poner("")
        self.lbl_archivo.configure(text="Ningún archivo cargado.")
        self.lbl_error.configure(text="")
        self.b_exportar.configure(state="disabled")
        self.b_limpiar.configure(state="disabled")
        self.selector.panel.aviso("Carga un archivo CSV o usa el ejemplo para ver el análisis.")
        self.app.estado("Registros descartados de la memoria.")

    @seguro
    def exportar(self, ruta=None):
        """Genera el reporte PDF (gráficas con su explicación e interpretación)."""
        if self.an is None:
            return
        ruta = ruta or filedialog.asksaveasfilename(
            parent=self, title="Guardar reporte PDF", defaultextension=".pdf",
            initialfile=f"reporte_registros_{date.today():%Y%m%d}.pdf",
            filetypes=[("Documento PDF", "*.pdf")])
        if not ruta:
            return
        self.app.ocupado(True)
        self.app.estado("Generando reporte PDF…")
        try:
            paginas = generar_reporte_registros(
                self.an, self.avisos, self.g.mapa_pred, self.g.geoms, self.g.metricas, ruta,
                self.archivo, es_ejemplo=os.path.abspath(self.archivo) == os.path.abspath(
                    EJEMPLO_PATH))
        finally:
            self.app.ocupado(False)
        self.app.estado(f"Reporte PDF de {paginas} páginas guardado en {ruta}")
        if hasattr(os, "startfile") and messagebox.askyesno(
                "Reporte listo", f"Se guardó el reporte ({paginas} páginas).\n\n"
                                 "¿Quieres abrirlo ahora?", parent=self):
            os.startfile(ruta)

    def ver_en_busqueda(self):
        sel = self.tabla.selection()
        if not sel or self.an is None:
            return
        from .busqueda import PestanaBusqueda
        r = self.an["registros"][int(sel[0])]
        for i, p in enumerate(self.app.pestanas):
            if isinstance(p, PestanaBusqueda):
                p.origen_punto(r["lon"], r["lat"], f"registro {r['id']}")
                self.app.ir_a(i)
                break
