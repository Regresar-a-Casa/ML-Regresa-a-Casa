"""Ventana principal de GEODETEC (Tkinter)."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..busqueda import zona_busqueda_punto
from ..figuras import (fig_busqueda, fig_distribuciones, fig_fosas, fig_importancia, fig_mapa,
                       fig_matriz_confusion, fig_variables_reales)
from ..fosas import abrir_datos_fosas, entrenar_fosas, guardar_resultados_fosas, preparar_fosas, texto_fosas
from ..modelo import texto_metricas
from ..personas import abrir_registro_personas
from ..sistema import Geodetec
from .comun import pedir_contrasena, seguro, ventana_figura, ventana_texto
from .ventana_personas import VentanaPersonas

COLOR_FONDO = "#f0f0f0"
MUNICIPIO_INICIAL_BUSQUEDA = "Toluca"


class AppGeodetec:
    def __init__(self, g):
        self.g = g
        self.root = root = tk.Tk()
        root.title("GEODETEC – Estado de México")
        root.geometry("640x460")
        root.config(bg=COLOR_FONDO)
        self._crear_encabezado()
        self._crear_botones()
        self.estado = tk.Label(root, text="Preparando el sistema: simulando datos de entrenamiento "
                                          "y cargando los datos reales...", bg=COLOR_FONDO,
                               fg="#555", font=("Helvetica", 9), wraplength=620)
        self.estado.pack(pady=10)
        root.config(cursor="watch")
        root.after(300, self.preparar_sistema)

    # ------------------------------------------------------------------ construcción
    def _crear_encabezado(self):
        tk.Label(self.root, text="GEODETEC", font=("Helvetica", 28, "bold"),
                 fg="#1e3d59", bg=COLOR_FONDO).pack(pady=(16, 2))
        tk.Label(self.root, text="Análisis territorial inteligente – Estado de México\n"
                                 "Entrena con municipios simulados · prueba con los 125 municipios reales\n"
                                 "INEGI 2020 · RNPDNO · Random Forest",
                 font=("Helvetica", 11), bg=COLOR_FONDO).pack(pady=(0, 10))

    def _crear_botones(self):
        botones = [
            ("Mapa de prioridad por municipio", self.mapa, "#c0392b"),
            ("Zona de búsqueda por municipio", self.busqueda, "#c0392b"),
            ("Personas desaparecidas (acceso restringido)", self.personas, "#6c1d45"),
            ("Fosas clandestinas (acceso restringido)", self.fosas, "#2c2c2c"),
        ]
        self.lista_botones = []
        for texto, cmd, color in botones:
            b = tk.Button(self.root, text=texto, command=cmd, font=("Helvetica", 12), bg=color,
                          fg="white", width=36, pady=3, state="disabled")
            b.pack(pady=3)
            self.lista_botones.append(b)

    def ejecutar(self):
        self.root.mainloop()

    # ------------------------------------------------------------------ utilidades
    def requiere(self, attr):
        if getattr(self.g, attr) is None:
            messagebox.showwarning("GEODETEC", "Primero completa los pasos anteriores.")
            return False
        return True

    def preparar_sistema(self):
        g, root = self.g, self.root
        try:
            g.paso_generar()
            self.estado.config(text="Entrenando el modelo con los municipios simulados...")
            root.update_idletasks()
            g.paso_entrenar()
            self.estado.config(
                text=f"Sistema listo · {len(g.train)} municipios simulados para entrenar · "
                     f"{len(g.test)} municipios reales evaluados · accuracy en datos reales: "
                     f"{g.metricas['accuracy']:.1%}")
            for b in self.lista_botones:
                b.config(state="normal")
        except Exception as e:
            self.estado.config(text="No se pudo preparar el sistema.", fg="#c0392b")
            messagebox.showerror("Error al iniciar", str(e))
        finally:
            root.config(cursor="")

    # ------------------------------------------------------------------ vistas del modelo
    # metricas, division, matriz, importancia y distribuciones aún no tienen botón en la
    # ventana principal (igual que en la versión original); se conectarán en la siguiente fase.
    @seguro
    def metricas(self):
        if self.requiere("metricas"):
            g = self.g
            ventana_texto(self.root, "Métricas",
                          texto_metricas(g.metricas, g.train, g.test, g.umbrales), "600x540")

    @seguro
    def division(self):
        if self.requiere("train"):
            ventana_figura(self.root, "Variables reales por municipio",
                           fig_variables_reales(self.g.test, self.g.geoms))

    @seguro
    def matriz(self):
        if self.requiere("metricas"):
            ventana_figura(self.root, "Matriz de confusión", fig_matriz_confusion(self.g.metricas))

    @seguro
    def importancia(self):
        if self.requiere("modelo"):
            ventana_figura(self.root, "Importancia de variables", fig_importancia(self.g.modelo))

    @seguro
    def distribuciones(self):
        if self.requiere("train"):
            ventana_figura(self.root, "Distribuciones", fig_distribuciones(self.g.train, self.g.test))

    @seguro
    def mapa(self):
        if self.requiere("mapa_pred"):
            ventana_figura(self.root, "Mapa de prioridad – Estado de México",
                           fig_mapa(self.g.mapa_pred, self.g.geoms))

    # ------------------------------------------------------------------ zona de búsqueda
    @seguro
    def busqueda(self):
        if not self.requiere("mapa_pred"):
            return
        g = self.g
        v = tk.Toplevel(self.root)
        v.title("Zona de búsqueda")
        tk.Label(v, text="Municipio de la última ubicación conocida:",
                 font=("Helvetica", 11)).pack(padx=15, pady=(15, 5))
        combo = ttk.Combobox(v, values=sorted(g.mun["municipio"].tolist()), width=40,
                             state="readonly")
        combo.set(MUNICIPIO_INICIAL_BUSQUEDA)
        combo.pack(padx=15, pady=5)

        @seguro
        def calcular():
            o = g.municipio_por_nombre(combo.get())
            zona = zona_busqueda_punto(g.mapa_pred, g.mun, o["lon"], o["lat"])
            v.destroy()
            ventana_figura(self.root, "Zona de búsqueda prioritaria",
                           fig_busqueda(zona, g.geoms, o["lon"], o["lat"], o["municipio"]))

        tk.Button(v, text="Calcular zona", command=calcular, bg="#c0392b", fg="white",
                  font=("Helvetica", 11)).pack(pady=12)

    # ------------------------------------------------------------------ secciones restringidas
    @seguro
    def personas(self):
        if not self.requiere("train"):
            return
        clave = pedir_contrasena(self.root, "Acceso restringido",
                                 "Registro confidencial de personas.\nIngresa la contraseña:")
        if not clave:
            return
        try:
            lista = abrir_registro_personas(clave)
        except PermissionError as e:
            messagebox.showerror("Acceso denegado", str(e))
            return
        VentanaPersonas(self, clave, lista)

    def fosas(self):
        # Maneja sus propios errores (no usa @seguro) para restaurar el estado y el cursor.
        root = self.root
        folio = pedir_contrasena(root, "Acceso restringido – fosas clandestinas",
                                 "Sección confidencial.\nIngresa el folio de una persona desaparecida:")
        if not folio:
            return
        try:
            datos, f_datos = abrir_datos_fosas(folio)
        except PermissionError as e:
            messagebox.showerror("Acceso denegado", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        estado_previo = self.estado.cget("text")
        self.estado.config(text="Entrenando el modelo de fosas con datos reales (validación cruzada)...")
        root.config(cursor="watch")
        root.update_idletasks()
        try:
            res, m = entrenar_fosas(preparar_fosas(self.g.mun, datos))
            guardar_resultados_fosas(res, m, f_datos)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        finally:
            root.config(cursor="")
            self.estado.config(text=estado_previo)
        ventana_figura(root, "Fosas clandestinas – probabilidad por municipio",
                       fig_fosas(res, m, self.g.geoms))
        ventana_texto(root, "Modelo de fosas – métricas y fuentes",
                      texto_fosas(m) + "\nFuentes\n- " + datos["fuente_fosas"]
                      + "\n- " + datos["fuente_homicidios"]
                      + "\n- RNPDNO (corte 30/11/2025) e INEGI (Censo 2020, localidades)\n",
                      "640x560")


def modo_gui():
    try:
        g = Geodetec()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("GEODETEC", str(e))
        return
    AppGeodetec(g).ejecutar()
