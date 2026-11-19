"""Pestaña confidencial: registro de personas (contraseña) y modelo de fosas (folio).

Cada sección empieza bloqueada con una pantalla de acceso dentro de la misma pestaña (sin
ventanas emergentes). Al desbloquear se muestra el contenido; "Bloquear" vuelve a ocultarlo y
descarta los datos descifrados de la memoria de la interfaz.
"""
import tkinter as tk
from tkinter import messagebox, ttk

from ...busqueda import zona_busqueda_punto
from ...config import MIN_LONGITUD_CONTRASENA
from ...figuras import fig_busqueda, fig_fosas, fig_personas
from ...fosas import (abrir_datos_fosas, entrenar_fosas, guardar_resultados_fosas,
                      preparar_fosas, texto_fosas)
from ...personas import abrir_registro_personas, cambiar_contrasena
from .. import estilo
from ..componentes import (DialogoClaveNueva, SelectorVistas, TextoSoloLectura,
                           panel_ancho_fijo, seguro)
from .base import Pestana

ANCHO_PANEL = 520


# --------------------------------------------------------------------------- pantalla de acceso
class PantallaAcceso(ttk.Frame):
    """Tarjeta centrada con un campo oculto. ``al_enviar(valor)`` puede lanzar
    ``PermissionError``; su mensaje se muestra debajo del campo."""

    def __init__(self, master, titulo, texto, etiqueta, boton, al_enviar, nota=""):
        super().__init__(master)
        self._al_enviar = al_enviar
        tarjeta = ttk.Frame(self, style="Tarjeta.TFrame", padding=28)
        tarjeta.place(relx=0.5, rely=0.42, anchor="center")
        ttk.Label(tarjeta, text="ACCESO RESTRINGIDO", style="Confidencial.TLabel").pack(anchor="w")
        ttk.Label(tarjeta, text=titulo, style="TarjetaTitulo.TLabel").pack(anchor="w", pady=(6, 2))
        ttk.Label(tarjeta, text=texto, style="TarjetaSuave.TLabel", wraplength=380,
                  justify="left").pack(anchor="w", pady=(0, 14))
        ttk.Label(tarjeta, text=etiqueta, style="Tarjeta.TLabel").pack(anchor="w")
        fila = ttk.Frame(tarjeta, style="Tarjeta.TFrame")
        fila.pack(fill="x", pady=(2, 0))
        self.entrada = ttk.Entry(fila, show="•", width=30, font=estilo.FUENTES["base"])
        self.entrada.pack(side="left", fill="x", expand=True)
        self.boton = ttk.Button(fila, text=boton, style="Confidencial.TButton",
                                command=self._enviar)
        self.boton.pack(side="left", padx=(8, 0))
        self.entrada.bind("<Return>", lambda _: self._enviar())
        self._error = ttk.Label(tarjeta, text="", style="TarjetaError.TLabel")
        self._error.pack(anchor="w", pady=(8, 0))
        if nota:
            ttk.Label(tarjeta, text=nota, style="TarjetaSuave.TLabel", wraplength=380,
                      justify="left").pack(anchor="w", pady=(4, 0))

    def limpiar(self):
        self.entrada.delete(0, "end")
        self._error.configure(text="")

    def _enviar(self):
        valor = self.entrada.get()
        if not valor:
            self._error.configure(text="Escribe un valor para continuar.")
            return
        self._error.configure(text="")
        try:
            self._al_enviar(valor)
        except PermissionError as e:
            self._error.configure(text=str(e))
            self.entrada.selection_range(0, "end")
            self.entrada.focus_set()
        except Exception as e:
            messagebox.showerror("Error", str(e))


def _barra_autorizado(master, texto, acciones):
    """Barra superior "ACCESO AUTORIZADO" con botones a la derecha."""
    barra = ttk.Frame(master, style="Tarjeta.TFrame", padding=(14, 8))
    ttk.Label(barra, text="ACCESO AUTORIZADO", style="Confidencial.TLabel").pack(side="left")
    ttk.Label(barra, text=texto, style="TarjetaSuave.TLabel").pack(side="left", padx=(12, 0))
    for nombre, cmd, estilo_ttk in reversed(acciones):
        ttk.Button(barra, text=nombre, command=cmd, style=estilo_ttk).pack(side="right", padx=(6, 0))
    return barra


# --------------------------------------------------------------------------- personas
class SeccionPersonas(ttk.Frame):
    COLUMNAS = (("folio", "Folio", 95), ("nombre", "Nombre", 230), ("edad", "Edad", 45),
                ("municipio", "Última ubicación", 150))
    CAMPOS_FICHA = (("Folio", "folio"), ("Nombre", "nombre"), ("Edad", "edad"),
                    ("Sexo", "sexo"), ("Estatura", "estatura_cm"), ("Complexión", "complexion"),
                    ("Señas particulares", "senas_particulares"), ("Vestimenta", "vestimenta"),
                    ("Desaparición", "fecha_desaparicion"), ("Última ubicación", "municipio"),
                    ("Coordenadas", None))

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.clave = self.lista = None
        self.acceso = PantallaAcceso(
            self, "Registro de personas desaparecidas",
            "Fichas de 5 personas 100 % ficticias con su última ubicación conocida y su zona "
            "de búsqueda. Los datos están cifrados en la base de datos.",
            "Contraseña", "Desbloquear", self._desbloquear)
        self.acceso.pack(fill="both", expand=True)
        self.vista = None

    def _desbloquear(self, clave):
        if not self.app.listo:
            raise PermissionError("Espera a que el sistema termine de prepararse.")
        lista = abrir_registro_personas(clave)     # PermissionError si es incorrecta
        self.clave, self.lista = clave, lista
        self.acceso.limpiar()
        self.acceso.pack_forget()
        self._construir_vista()
        self.app.estado("Registro de personas desbloqueado.")

    def bloquear(self):
        self.clave = self.lista = None
        if self.vista is not None:
            self.vista.destroy()
            self.vista = None
        self.acceso.pack(fill="both", expand=True)
        self.acceso.entrada.focus_set()

    # ---------------------------------------------------------------- vista desbloqueada
    def _construir_vista(self):
        self.vista = v = ttk.Frame(self)
        v.pack(fill="both", expand=True)
        _barra_autorizado(v, "Datos 100 % ficticios", [
            ("Cambiar contraseña", self._cambiar_clave, "TButton"),
            ("Bloquear", self.bloquear, "Confidencial.TButton"),
        ]).pack(fill="x", pady=(0, 10))

        cuerpo = ttk.Frame(v)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=0, minsize=ANCHO_PANEL)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        izq = panel_ancho_fijo(cuerpo, ANCHO_PANEL)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.tabla = ttk.Treeview(izq, columns=[c for c, _, _ in self.COLUMNAS],
                                  show="headings", height=len(self.lista), selectmode="browse")
        for col, titulo, ancho in self.COLUMNAS:
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="w", stretch=col == "nombre")
        for p in self.lista:
            self.tabla.insert("", "end", iid=p["id"], tags=(p["id"],),
                              values=(p["folio"], p["nombre"].replace(" (ficticio)", ""),
                                      p["edad"], p["municipio"]))
            self.tabla.tag_configure(p["id"], background=p["color"], foreground="white")
        self.tabla.pack(fill="x")
        self.tabla.bind("<<TreeviewSelect>>", lambda _: self._al_seleccionar())

        ficha = ttk.Frame(izq, style="Tarjeta.TFrame", padding=14)
        ficha.pack(fill="both", expand=True, pady=(10, 0))
        self._franja = tk.Frame(ficha, width=6, bg=estilo.BORDE)
        self._franja.pack(side="left", fill="y", padx=(0, 12))
        datos = ttk.Frame(ficha, style="Tarjeta.TFrame")
        datos.pack(side="left", fill="both", expand=True)
        self._titulo_ficha = ttk.Label(datos, text="", style="TarjetaTitulo.TLabel")
        self._titulo_ficha.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        datos.columnconfigure(1, weight=1)
        self._valores = {}
        for i, (etq, _) in enumerate(self.CAMPOS_FICHA, start=1):
            ttk.Label(datos, text=etq, style="TarjetaSuave.TLabel").grid(
                row=i, column=0, sticky="nw", padx=(0, 10), pady=1)
            val = ttk.Label(datos, text="", style="Tarjeta.TLabel", justify="left")
            val.grid(row=i, column=1, sticky="w", pady=1)
            self._valores[etq] = val

        self.selector = SelectorVistas(cuerpo, self.app, [
            {"nombre": "Todas las ubicaciones",
             "titulo": "Últimas ubicaciones por persona",
             "ayuda": "cada círculo es la última ubicación conocida de una persona; el área de su "
                      "color es su zona de búsqueda prioritaria. El fondo gris es P(alta) del "
                      "modelo.",
             "fabrica": lambda: fig_personas(self.lista, self.app.g.mapa_pred, self.app.g.mun,
                                             self.app.g.geoms)},
            {"nombre": "Zona de la persona seleccionada",
             "ayuda": "zona de búsqueda calculada desde el punto exacto de la última ubicación de "
                      "la persona elegida en la tabla.",
             "fabrica": self._fig_zona_persona},
        ])
        self.selector.grid(row=0, column=1, sticky="nsew")

        self.tabla.selection_set(self.lista[0]["id"])
        self._mostrar_ficha(self.lista[0])
        self.selector.refrescar()

    def seleccionada(self):
        sel = self.tabla.selection()
        objetivo = sel[0] if sel else self.lista[0]["id"]
        return next(p for p in self.lista if p["id"] == objetivo)

    def _mostrar_ficha(self, p):
        self._franja.configure(bg=p["color"])
        self._titulo_ficha.configure(text=f"{p['id']} · ficha completa")
        for etq, clave in self.CAMPOS_FICHA:
            if clave is None:
                texto = f"{p['lat']:.4f}, {p['lon']:.4f}"
            elif clave == "edad":
                texto = f"{p['edad']} años"
            elif clave == "estatura_cm":
                texto = f"{p['estatura_cm']} cm"
            else:
                texto = str(p[clave])
            self._valores[etq].configure(text=texto, wraplength=260)

    def _al_seleccionar(self):
        if self.lista is None:
            return
        self._mostrar_ficha(self.seleccionada())
        if self.selector.indice == 1:       # la vista de zona depende de la persona elegida
            self.selector.refrescar()

    def _fig_zona_persona(self):
        g, p = self.app.g, self.seleccionada()
        zona = zona_busqueda_punto(g.mapa_pred, g.mun, p["lon"], p["lat"])
        return fig_busqueda(zona, g.geoms, p["lon"], p["lat"], f"{p['id']} ({p['municipio']})",
                            color_zona=p["color"], color_punto=p["color"], cmap="Greys")

    @seguro
    def _cambiar_clave(self):
        nueva = DialogoClaveNueva(self.app.root, MIN_LONGITUD_CONTRASENA).resultado
        if not nueva:
            return
        cambiar_contrasena(self.clave, nueva)
        self.clave = nueva
        messagebox.showinfo("Listo", "Contraseña actualizada. El registro se volvió a cifrar.",
                            parent=self.app.root)


# --------------------------------------------------------------------------- fosas
class SeccionFosas(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.acceso = PantallaAcceso(
            self, "Fosas clandestinas – datos reales",
            "Modelo con registros reales de fosas (CNB 2018-2023) y homicidios (2019-2024). "
            "Estima qué municipios tienen mayor probabilidad de tener fosas registradas.",
            "Folio de una persona desaparecida", "Desbloquear y entrenar", self._desbloquear,
            nota="El entrenamiento usa validación cruzada repetida y tarda unos segundos.")
        self.acceso.pack(fill="both", expand=True)
        self.vista = None

    def _desbloquear(self, folio):
        if not self.app.listo:
            raise PermissionError("Espera a que el sistema termine de prepararse.")
        datos, f_datos = abrir_datos_fosas(folio)  # PermissionError si el folio no es válido
        self.app.estado("Entrenando el modelo de fosas con datos reales (validación cruzada)…")
        self.app.ocupado(True)
        try:
            res, m = entrenar_fosas(preparar_fosas(self.app.g.mun, datos))
            guardar_resultados_fosas(res, m, f_datos)
        finally:
            self.app.ocupado(False)
        self.acceso.limpiar()
        self.acceso.pack_forget()
        self._construir_vista(datos, res, m)
        self.app.estado(f"Modelo de fosas listo · AUC Random Forest {m['auc_rf']:.2f}.")

    def bloquear(self):
        if self.vista is not None:
            self.vista.destroy()
            self.vista = None
        self.acceso.pack(fill="both", expand=True)
        self.acceso.entrada.focus_set()

    def _construir_vista(self, datos, res, m):
        self.vista = v = ttk.Frame(self)
        v.pack(fill="both", expand=True)
        _barra_autorizado(v, "Datos reales · candidatos a revisión, no hallazgos", [
            ("Bloquear", self.bloquear, "Confidencial.TButton"),
        ]).pack(fill="x", pady=(0, 10))
        cuerpo = ttk.Frame(v)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=0, minsize=ANCHO_PANEL)
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        izq = panel_ancho_fijo(cuerpo, ANCHO_PANEL)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        ttk.Label(izq, text="Métricas y fuentes", style="Subtitulo.TLabel").pack(anchor="w",
                                                                                pady=(0, 4))
        texto = TextoSoloLectura(izq, ajustar=True)
        texto.pack(fill="both", expand=True)
        texto.poner(texto_fosas(m) + "\nFuentes\n- " + datos["fuente_fosas"]
                    + "\n- " + datos["fuente_homicidios"]
                    + "\n- RNPDNO (corte 30/11/2025) e INEGI (Censo 2020, localidades)\n")

        selector = SelectorVistas(cuerpo, self.app, [
            {"nombre": "Probabilidad por municipio",
             "titulo": "Fosas clandestinas – probabilidad por municipio",
             "ayuda": "color más oscuro = mayor probabilidad estimada (calculada con modelos que no "
                      "vieron ese municipio al entrenar). Contorno azul = municipio con fosa "
                      "registrada. Un municipio oscuro sin contorno es un candidato a revisión.",
             "fabrica": lambda: fig_fosas(res, m, self.app.g.geoms)},
        ])
        selector.grid(row=0, column=1, sticky="nsew")
        selector.refrescar()


# --------------------------------------------------------------------------- pestaña
class PestanaConfidencial(Pestana):
    titulo = "Confidencial"
    descripcion = ("Secciones de acceso restringido. El registro de personas usa datos 100 % "
                   "ficticios; el modelo de fosas usa datos reales y sus resultados son "
                   "candidatos a revisión, no hallazgos.")
    requiere_sistema = False

    def construir(self):
        cuaderno = ttk.Notebook(self.contenido, style="Interno.TNotebook")
        cuaderno.pack(fill="both", expand=True)
        self.personas = SeccionPersonas(cuaderno, self.app)
        self.fosas = SeccionFosas(cuaderno, self.app)
        cuaderno.add(self.personas, text="Registro de personas")
        cuaderno.add(self.fosas, text="Fosas clandestinas")
