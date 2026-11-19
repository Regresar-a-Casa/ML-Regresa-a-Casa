"""Ventana principal de GEODETEC: encabezado, pestañas y barra de estado."""
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from ..sistema import Geodetec
from . import estilo
from .pestanas import PESTANAS

ESCALA_PRESENTACION = 1.3


class AppGeodetec:
    def __init__(self, g):
        self.g = g
        self.listo = False
        self._presentacion = False
        self._ocupado = 0

        self.root = root = tk.Tk()
        root.title("GEODETEC – Estado de México")
        root.geometry("1280x800")
        root.minsize(1000, 640)
        estilo.aplicar(root)
        if sys.platform == "win32":
            try:
                root.state("zoomed")          # maximizada en Windows
            except tk.TclError:
                pass

        self._crear_encabezado()
        self._crear_barra_estado()     # antes que las pestañas: así nunca se queda sin espacio
        self._crear_pestanas()
        self._atajos()

        self.estado("Preparando el sistema: simulando datos de entrenamiento y cargando los "
                    "datos reales…")
        self.ocupado(True)
        root.after(300, self.preparar_sistema)

    # ------------------------------------------------------------------ construcción
    def _crear_encabezado(self):
        enc = ttk.Frame(self.root, style="Encabezado.TFrame", padding=(20, 10))
        enc.pack(side="top", fill="x")
        ttk.Label(enc, text="GEODETEC", style="Marca.TLabel").pack(side="left")
        ttk.Label(enc, text="Análisis territorial inteligente · Estado de México · "
                            "INEGI 2020 · RNPDNO · Random Forest",
                  style="EncabezadoTexto.TLabel").pack(side="left", padx=(16, 0), pady=(6, 0))
        self._boton_presentacion = ttk.Button(enc, text="Modo presentación (F11)",
                                              style="Encabezado.TButton",
                                              command=self.alternar_presentacion)
        self._boton_presentacion.pack(side="right")

    def _crear_pestanas(self):
        self.cuaderno = ttk.Notebook(self.root)
        self.cuaderno.pack(side="top", fill="both", expand=True, padx=10, pady=(8, 0))
        self.pestanas = []
        for texto, clase in PESTANAS:
            p = clase(self.cuaderno, self)
            self.cuaderno.add(p, text=texto, state="normal" if not p.requiere_sistema
                              else "disabled")
            self.pestanas.append(p)
        self.inicio = self.pestanas[0]
        self.cuaderno.bind("<<NotebookTabChanged>>", lambda _: self._pestana_actual().al_mostrar())

    def _crear_barra_estado(self):
        barra = ttk.Frame(self.root, style="Tarjeta.TFrame", padding=(12, 4))
        barra.pack(side="bottom", fill="x")
        self._progreso = ttk.Progressbar(barra, mode="indeterminate", length=120)
        self._progreso.pack(side="right")
        self._texto_estado = ttk.Label(barra, text="", style="Estado.TLabel")
        self._texto_estado.pack(side="left", fill="x", expand=True)

    def _atajos(self):
        r = self.root
        for i in range(len(self.pestanas)):
            r.bind_all(f"<Control-Key-{i + 1}>", lambda _, n=i: self.ir_a(n))
        r.bind_all("<F11>", lambda _: self.alternar_presentacion())
        r.bind_all("<Escape>", lambda _: self.salir_presentacion())

    def ejecutar(self):
        self.root.mainloop()

    # ------------------------------------------------------------------ utilidades
    def _pestana_actual(self):
        return self.pestanas[self.cuaderno.index("current")]

    def ir_a(self, indice):
        if 0 <= indice < len(self.pestanas) and \
                self.cuaderno.tab(indice, "state") != "disabled":
            self.cuaderno.select(indice)

    def estado(self, texto):
        self._texto_estado.configure(text=texto)
        self.root.update_idletasks()

    def ocupado(self, activo):
        """Cursor de espera y barra de progreso mientras se calcula algo (admite anidamiento)."""
        self._ocupado = max(0, self._ocupado + (1 if activo else -1))
        if self._ocupado:
            self.root.configure(cursor="watch")
            self._progreso.start(12)
        else:
            self.root.configure(cursor="")
            self._progreso.stop()
        self.root.update_idletasks()

    def requiere(self, attr):
        if getattr(self.g, attr) is None:
            messagebox.showwarning("GEODETEC", "Primero completa los pasos anteriores.")
            return False
        return True

    # ------------------------------------------------------------------ modo presentación
    def alternar_presentacion(self):
        self._presentacion = not self._presentacion
        self.root.attributes("-fullscreen", self._presentacion)
        estilo.escalar(ESCALA_PRESENTACION if self._presentacion else 1.0)
        self._boton_presentacion.configure(
            text="Salir de presentación (Esc)" if self._presentacion else "Modo presentación (F11)")

    def salir_presentacion(self):
        if self._presentacion:
            self.alternar_presentacion()

    # ------------------------------------------------------------------ arranque
    def preparar_sistema(self):
        g = self.g
        try:
            g.paso_generar()
            self.estado("Entrenando el modelo con los municipios simulados…")
            self.inicio.estado("Entrenando el modelo con los municipios simulados…")
            g.paso_entrenar()
            self.listo = True
            for i, p in enumerate(self.pestanas):
                self.cuaderno.tab(i, state="normal")
                p.sistema_listo()
            self.estado(f"Sistema listo · {len(g.train)} municipios simulados para entrenar · "
                        f"{len(g.test)} municipios reales evaluados · accuracy en datos reales: "
                        f"{g.metricas['accuracy']:.1%}")
            self._pestana_actual().al_mostrar()
        except Exception as e:
            self.estado("No se pudo preparar el sistema.")
            self.inicio.estado(f"No se pudo preparar el sistema: {e}")
            messagebox.showerror("Error al iniciar", str(e))
        finally:
            self.ocupado(False)


def modo_gui():
    try:
        g = Geodetec()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("GEODETEC", str(e))
        return
    AppGeodetec(g).ejecutar()
