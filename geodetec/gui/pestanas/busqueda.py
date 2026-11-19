"""Pestaña de zona de búsqueda a partir de la última ubicación conocida.

El origen se elige de tres formas: un municipio de la lista (su centroide), un punto de
referencia (CDMX o Toluca) o un clic en cualquier punto del mapa. Los tres parámetros del índice
(σ, piso del modelo y tamaño de la zona) se ajustan con deslizadores y el mapa se recalcula solo.
"""
import math
from tkinter import ttk

from ...busqueda import localizador, zona_busqueda_punto
from ...config import CENTROS, PISO_MODELO, PORCENTAJE_ZONA, SIGMA_KM
from ...figuras import fig_busqueda
from ..componentes import (Deslizador, MarcoDesplazable, PanelFigura, etiqueta_ajustable,
                           nombre_municipio, panel_ancho_fijo, seguro)
from .base import Pestana

MUNICIPIO_INICIAL = "Toluca"
ANCHO_PANEL = 350

# (desde, hasta, paso) de cada deslizador
RANGO_SIGMA = (10, 80, 5)
RANGO_PISO = (0.0, 1.0, 0.05)
RANGO_PORCENTAJE = (0.05, 0.30, 0.01)


class PestanaBusqueda(Pestana):
    titulo = "Zona de búsqueda"
    descripcion = ("Elige la última ubicación conocida: un municipio de la lista, un punto de "
                   "referencia o un clic en el mapa. El sistema combina la probabilidad de "
                   "prioridad alta del modelo con la cercanía a ese punto y marca como zona "
                   "prioritaria los municipios con mayor índice. Mueve los deslizadores para ver "
                   "cómo cambia la zona.")

    def construir(self):
        self.origen = None          # {"lon", "lat", "nombre"}
        c = self.contenido
        c.columnconfigure(0, weight=0, minsize=ANCHO_PANEL)
        c.columnconfigure(1, weight=1)
        c.rowconfigure(0, weight=1)

        tarjeta = panel_ancho_fijo(c, ANCHO_PANEL, style="Tarjeta.TFrame", padding=2)
        tarjeta.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        desplazable = MarcoDesplazable(tarjeta, fondo="#ffffff", estilo_interior="Plano.TFrame")
        desplazable.pack(fill="both", expand=True)
        izq = ttk.Frame(desplazable.interior, style="Plano.TFrame", padding=14)
        izq.pack(fill="both", expand=True)

        # ---- origen
        ttk.Label(izq, text="Última ubicación conocida", style="TarjetaTitulo.TLabel").pack(anchor="w")
        ttk.Label(izq, text="Municipio (centroide)", style="TarjetaSuave.TLabel").pack(
            anchor="w", pady=(8, 2))
        self.combo = ttk.Combobox(izq, state="readonly", width=32)
        self.combo.pack(fill="x")
        self.combo.bind("<<ComboboxSelected>>", lambda _: self.origen_municipio())

        ttk.Label(izq, text="Puntos de referencia", style="TarjetaSuave.TLabel").pack(
            anchor="w", pady=(10, 2))
        fila = ttk.Frame(izq, style="Plano.TFrame")
        fila.pack(fill="x")
        for i, (nombre, (lon, lat)) in enumerate(CENTROS.items()):
            ttk.Button(fila, text=nombre.split(" (")[0],
                       command=lambda n=nombre, x=lon, y=lat: self.origen_punto(x, y, n)).grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            fila.columnconfigure(i, weight=1)
        etiqueta_ajustable(izq, "También puedes hacer clic en cualquier punto del mapa para "
                                "colocar ahí el origen.", "Pista.TLabel").pack(
            anchor="w", fill="x", pady=(8, 0))
        self.lbl_origen = etiqueta_ajustable(izq, "Origen: —", "Tarjeta.TLabel")
        self.lbl_origen.pack(anchor="w", fill="x", pady=(6, 0))

        # ---- parámetros
        ttk.Separator(izq).pack(fill="x", pady=12)
        ttk.Label(izq, text="Parámetros del índice", style="TarjetaTitulo.TLabel").pack(anchor="w")
        self.d_sigma = Deslizador(izq, "Alcance σ", *RANGO_SIGMA, SIGMA_KM, "{:.0f} km",
                                  al_cambiar=self._parametro,
                                  ayuda="Qué tan rápido pierde peso un municipio al alejarse.")
        self.d_sigma.pack(fill="x", pady=(8, 0))
        self.d_piso = Deslizador(izq, "Piso", *RANGO_PISO, PISO_MODELO, "{:.2f}",
                                 al_cambiar=self._parametro,
                                 ayuda="Peso de la cercanía aunque el modelo dé poca probabilidad.")
        self.d_piso.pack(fill="x", pady=(8, 0))
        self.d_porcentaje = Deslizador(izq, "Tamaño", *RANGO_PORCENTAJE,
                                       PORCENTAJE_ZONA, self._texto_porcentaje,
                                       al_cambiar=self._parametro,
                                       ayuda="Porcentaje de los 125 municipios que forman la zona.")
        self.d_porcentaje.pack(fill="x", pady=(8, 0))
        ttk.Button(izq, text="Restablecer valores originales",
                   command=self.restablecer).pack(fill="x", pady=(10, 0))

        # ---- explicación y resultado
        ttk.Separator(izq).pack(fill="x", pady=12)
        ttk.Label(izq, text="Resultado", style="TarjetaTitulo.TLabel").pack(anchor="w")
        self.resumen = etiqueta_ajustable(izq, "—", "TarjetaSuave.TLabel")
        self.resumen.pack(anchor="w", fill="x", pady=(4, 0))
        ttk.Separator(izq).pack(fill="x", pady=12)
        ttk.Label(izq, text="¿Cómo se calcula?", style="TarjetaTitulo.TLabel").pack(anchor="w")
        self.lbl_formula = etiqueta_ajustable(izq, "", "TarjetaSuave.TLabel")
        self.lbl_formula.pack(anchor="w", fill="x", pady=(4, 0))
        self._actualizar_formula()

        self.panel = PanelFigura(c, self.app)
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.panel.aviso("Elige un municipio para calcular la zona de búsqueda.")

    # ------------------------------------------------------------------ parámetros
    @property
    def parametros(self):
        return {"sigma_km": self.d_sigma.valor, "piso": self.d_piso.valor,
                "porcentaje": self.d_porcentaje.valor}

    def _texto_porcentaje(self, p):
        total = len(self.g.mun) if self.app.listo and self.g.mun is not None else 125
        return f"{p:.0%} ({max(1, math.ceil(round(p * total, 6)))} mun.)"

    def _parametro(self, _valor):
        self._actualizar_formula()
        self.calcular()

    def restablecer(self):
        self.d_sigma.poner(SIGMA_KM)
        self.d_piso.poner(PISO_MODELO)
        self.d_porcentaje.poner(PORCENTAJE_ZONA)
        self._parametro(None)

    def _actualizar_formula(self):
        p = self.parametros
        s, piso = p["sigma_km"], p["piso"]
        self.lbl_formula.configure(text=(
            f"índice = ({piso:.2f} + {1 - piso:.2f} · P(alta)) · cercanía\n\n"
            f"cercanía = exp(−d² / 2·{s:.0f}²), donde d es la distancia en km al origen. Vale 1 "
            f"en el origen, ≈0.61 a {s:.0f} km y ≈0.14 a {2 * s:.0f} km. Un σ mayor amplía la "
            "búsqueda; uno menor la concentra cerca del origen.\n\n"
            f"El piso ({piso:.2f}) es el peso que conserva un municipio cercano aunque el modelo "
            "le asigne poca probabilidad: con 0 solo cuenta P(alta); con 1 solo cuenta la "
            "distancia."))

    # ------------------------------------------------------------------ origen
    def renderizar(self):
        nombres = sorted(self.g.mun["municipio"].tolist())
        self.combo.configure(values=nombres)
        self.d_porcentaje.poner(self.d_porcentaje.valor)     # actualiza "n municipios"
        if self.origen is None:
            self.combo.set(MUNICIPIO_INICIAL if MUNICIPIO_INICIAL in nombres else nombres[0])
            self.origen_municipio()
        else:
            self.calcular()

    def origen_municipio(self):
        if not self.app.listo or self.combo.get() not in self.combo.cget("values"):
            return
        o = self.g.municipio_por_nombre(self.combo.get())
        self.origen = {"lon": float(o["lon"]), "lat": float(o["lat"]),
                       "nombre": o["municipio"], "detalle": "centroide del municipio"}
        self.calcular()

    def origen_punto(self, lon, lat, nombre=None):
        """Origen en un punto libre (clic en el mapa o punto de referencia)."""
        if not self.app.listo:
            return
        cve = localizador(self.g.geoms).buscar(lon, lat)
        dentro = nombre_municipio(self.app, cve) if cve else None
        if nombre is None:                       # clic en el mapa
            nombre = f"punto en {dentro}" if dentro else "punto fuera del Estado de México"
            detalle = ""
        else:                                    # punto de referencia
            detalle = f"dentro de {dentro}" if dentro else "fuera del Estado de México"
        self.combo.set("(punto de referencia)" if detalle else "(punto elegido en el mapa)")
        self.origen = {"lon": float(lon), "lat": float(lat), "nombre": nombre, "detalle": detalle}
        self.calcular()

    # ------------------------------------------------------------------ cálculo
    @seguro
    def calcular(self):
        if not self.app.listo or self.origen is None:
            return
        g, o, p = self.g, self.origen, self.parametros
        detalle = f" ({o['detalle']})" if o.get("detalle") else ""
        self.lbl_origen.configure(
            text=f"Origen: {o['nombre']}{detalle}\n{o['lat']:.4f}, {o['lon']:.4f}")
        zona = zona_busqueda_punto(g.mapa_pred, g.mun, o["lon"], o["lat"], **p)
        sel = zona[zona["en_zona"]]
        self.resumen.configure(
            text=f"{len(sel)} municipios en la zona prioritaria. El más lejano está a "
                 f"{sel['distancia_km'].max():.0f} km del origen; P(alta) promedio en la zona: "
                 f"{sel['prob_alta'].mean():.2f}. Más cercano al origen: "
                 f"{zona.sort_values('distancia_km').iloc[0]['municipio']}.")
        titulo = o["nombre"][0].upper() + o["nombre"][1:]
        self.app.ocupado(True)
        try:
            self.panel.mostrar(
                lambda: fig_busqueda(zona, g.geoms, o["lon"], o["lat"], titulo, **p),
                f"Zona de búsqueda – {titulo}", al_clic=self.origen_punto)
        finally:
            self.app.ocupado(False)
