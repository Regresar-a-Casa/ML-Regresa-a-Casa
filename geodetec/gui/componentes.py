"""Componentes reutilizables de la interfaz: figuras incrustadas (con recuadro informativo y clic
sobre los mapas), selector de vistas, tarjetas, deslizadores, texto de solo lectura y diálogos."""
import functools
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from ..busqueda import localizador
from ..figuras import info_mapa
from . import estilo


# --------------------------------------------------------------------------- errores
def seguro(func):
    """Decorador: cualquier excepción se muestra en un cuadro de error en vez de romper la GUI."""
    @functools.wraps(func)
    def envoltura(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    return envoltura


# --------------------------------------------------------------------------- figuras
class LienzoAjustable(FigureCanvasTkAgg):
    """Lienzo de matplotlib que escala la figura completa (texto incluido) al espacio disponible.

    Las figuras se diseñaron con un tamaño fijo en pulgadas. En vez de deformarlas, se ajustan los
    DPI para que el diseño quepa en el widget: en una ventana pequeña todo se ve proporcionalmente
    más chico y en un proyector o pantalla completa, más grande.
    """
    DPI_MINIMO = 20

    def __init__(self, figura, master):
        self._tamano_diseno = tuple(figura.get_size_inches())
        super().__init__(figura, master=master)
        # Sin esto el widget pediría el tamaño original de la figura (p. ej. 1500 px de ancho)
        self.get_tk_widget().configure(width=320, height=240)

    def resize(self, event):
        if event.width > 1 and event.height > 1:
            ancho, alto = self._tamano_diseno
            dpi = max(self.DPI_MINIMO, min(event.width / ancho, event.height / alto))
            self.figure.set_dpi(dpi)
        super().resize(event)


class MarcoFigura(tk.Frame):
    """Marco que coloca un ``LienzoAjustable`` centrado y con la proporción original de la figura,
    para que las figuras con varios paneles no se estiren ni dejen huecos entre ellos."""

    def __init__(self, master, **kw):
        super().__init__(master, bg=estilo.SUPERFICIE, **kw)
        self.lienzo = None
        self.bind("<Configure>", lambda _: self._ajustar())

    def poner(self, figura):
        self.quitar()
        self.lienzo = LienzoAjustable(figura, self)
        self._ajustar()
        self.lienzo.draw()
        return self.lienzo

    def quitar(self):
        if self.lienzo is not None:
            self.lienzo.get_tk_widget().destroy()
            self.lienzo = None

    def _ajustar(self):
        if self.lienzo is None:
            return
        ancho, alto = self.winfo_width(), self.winfo_height()
        if ancho < 2 or alto < 2:
            ancho, alto = 800, 500     # aún no se dibuja el marco; se corrige en <Configure>
        w0, h0 = self.lienzo._tamano_diseno
        escala = min(ancho / w0, alto / h0)
        self.lienzo.get_tk_widget().place(relx=0.5, rely=0.5, anchor="center",
                                          width=int(w0 * escala), height=int(h0 * escala))


def nombre_municipio(app, cve):
    """Nombre del municipio con clave ``cve`` (o la clave si el sistema aún no carga datos)."""
    nombres = getattr(app, "_nombres_municipios", None)
    if nombres is None:
        mun = getattr(getattr(app, "g", None), "mun", None)
        if mun is None:
            return cve
        nombres = dict(zip(mun["cvegeo"], mun["municipio"]))
        app._nombres_municipios = nombres
    return nombres.get(cve, cve)


def figura_tiene_mapas(figura):
    return any(info_mapa(ax) for ax in figura.axes)


class InfoMapa:
    """Interactividad de los mapas de una figura ya colocada en un ``MarcoFigura``.

    - Al pasar el ratón sobre un municipio muestra un recuadro con su nombre y los valores que la
      figura registró con ``figuras.registrar_info``. El recuadro es un widget de Tk encima del
      lienzo, así que no hay que volver a dibujar la figura y responde al instante.
    - Si se da ``al_clic(lon, lat)``, un clic izquierdo sobre un mapa la llama con las
      coordenadas del punto (salvo que la herramienta de zoom o desplazamiento esté activa).
    """
    DESPLAZAMIENTO = 16   # píxeles entre el puntero y el recuadro

    def __init__(self, marco, nombres, al_clic=None, barra=None):
        self.marco, self.nombres, self.al_clic, self.barra = marco, nombres, al_clic, barra
        self.lienzo = marco.lienzo
        self._actual = None
        self._recuadro = tk.Frame(marco, bg=estilo.INFO_FONDO, padx=9, pady=6)
        self._titulo = tk.Label(self._recuadro, bg=estilo.INFO_FONDO, fg=estilo.INFO_TEXTO,
                                font=estilo.FUENTES["negrita"], justify="left", anchor="w")
        self._titulo.pack(anchor="w")
        self._cuerpo = tk.Label(self._recuadro, bg=estilo.INFO_FONDO, fg=estilo.INFO_TEXTO,
                                font=estilo.FUENTES["pequena"], justify="left", anchor="w")
        self._cuerpo.pack(anchor="w")
        self.lienzo.mpl_connect("motion_notify_event", self._mover)
        self.lienzo.mpl_connect("figure_leave_event", lambda _: self._ocultar())
        self.lienzo.mpl_connect("axes_leave_event", lambda _: self._ocultar())
        if al_clic is not None:
            self.lienzo.mpl_connect("button_press_event", self._clic)

    def _herramienta_activa(self):
        modo = getattr(self.barra, "mode", "")
        return bool(getattr(modo, "value", modo))

    def _municipio(self, evento):
        info = info_mapa(evento.inaxes) if evento.inaxes is not None else None
        if info is None or evento.xdata is None:
            return info, None
        return info, localizador(info["geoms"]).buscar(evento.xdata, evento.ydata)

    def _mover(self, evento):
        info, cve = self._municipio(evento)
        clic_posible = (info is not None and self.al_clic is not None
                        and not self._herramienta_activa())
        self.lienzo.get_tk_widget().configure(cursor="crosshair" if clic_posible else "")
        if cve is None:
            self._ocultar()
            return
        if cve != self._actual:
            self._actual = cve
            self._titulo.configure(text=self.nombres(cve))
            lineas = list(info["lineas"](cve))
            if clic_posible:
                lineas.append("Clic: mover aquí el origen")
            self._cuerpo.configure(text="\n".join(lineas))
            if lineas:
                self._cuerpo.pack(anchor="w")
            else:
                self._cuerpo.pack_forget()
        self._colocar()

    def _colocar(self):
        m = self.marco
        x = m.winfo_pointerx() - m.winfo_rootx() + self.DESPLAZAMIENTO
        y = m.winfo_pointery() - m.winfo_rooty() + self.DESPLAZAMIENTO
        self._recuadro.update_idletasks()
        ancho, alto = self._recuadro.winfo_reqwidth(), self._recuadro.winfo_reqheight()
        if x + ancho > m.winfo_width():               # no salirse por la derecha ni por abajo
            x = max(0, x - ancho - 2 * self.DESPLAZAMIENTO)
        if y + alto > m.winfo_height():
            y = max(0, y - alto - 2 * self.DESPLAZAMIENTO)
        self._recuadro.place(x=x, y=y)
        self._recuadro.lift()

    def _ocultar(self):
        self._actual = None
        self._recuadro.place_forget()

    def _clic(self, evento):
        if (evento.button != 1 or evento.dblclick or self._herramienta_activa()
                or evento.inaxes is None or info_mapa(evento.inaxes) is None
                or evento.xdata is None):
            return
        self._ocultar()
        # Diferido: al_clic suele redibujar (y destruir) este mismo lienzo, lo que no debe
        # ocurrir dentro de su propio manejador de eventos.
        self.marco.after_idle(self.al_clic, float(evento.xdata), float(evento.ydata))


def ventana_figura(root, titulo, figura, tamano="1200x720", nombres=None):
    """Abre una figura en una ventana independiente con barra de herramientas.

    Con ``nombres(cve)`` los mapas muestran el recuadro informativo al pasar el ratón."""
    v = tk.Toplevel(root)
    v.title(titulo)
    v.geometry(tamano)
    v.configure(bg=estilo.SUPERFICIE)
    marco = MarcoFigura(v)
    lienzo = marco.poner(figura)
    barra = NavigationToolbar2Tk(lienzo, v, pack_toolbar=False)
    barra.pack(side="bottom", fill="x")
    marco.pack(fill="both", expand=True)
    if nombres is not None and figura_tiene_mapas(figura):
        v._info = InfoMapa(marco, nombres, barra=barra)
    return v


class PanelFigura(ttk.Frame):
    """Contenedor de una figura con barra de herramientas y botón para abrirla en otra ventana.

    ``mostrar(fabrica, titulo)`` recibe una función que crea la figura; así se puede volver a
    crear para la ventana independiente (una figura solo puede estar en un lienzo a la vez).
    """

    def __init__(self, master, app, **kw):
        super().__init__(master, style="Tarjeta.TFrame", **kw)
        self.app = app
        self._fabrica = self._titulo = None
        self._barra = None

        self._zona_barra = ttk.Frame(self, style="Tarjeta.TFrame")
        self._zona_barra.pack(side="top", fill="x", padx=6, pady=(4, 0))
        self._boton_ventana = ttk.Button(self._zona_barra, text="Abrir en ventana  ⧉",
                                         command=self.abrir_en_ventana, state="disabled")
        self._boton_ventana.pack(side="right", padx=4, pady=2)
        self._pista = ttk.Label(self._zona_barra, text="", style="Pista.TLabel")
        self._info = None
        self._marco = MarcoFigura(self)
        self._marco.pack(side="top", fill="both", expand=True, padx=6, pady=6)
        self._aviso = ttk.Label(self._marco, text="", style="TarjetaSuave.TLabel")
        self._aviso.place(relx=0.5, rely=0.5, anchor="center")

    def aviso(self, texto):
        """Muestra un mensaje centrado en lugar de la figura."""
        self._limpiar()
        self._aviso.configure(text=texto)
        self._aviso.place(relx=0.5, rely=0.5, anchor="center")
        self._boton_ventana.configure(state="disabled")
        self._pista.pack_forget()

    def _limpiar(self):
        if self._info is not None:
            self._info._recuadro.destroy()
            self._info = None
        self._pista.pack_forget()       # se vuelve a colocar después de la barra de herramientas
        self._marco.quitar()
        if self._barra is not None:
            self._barra.destroy()
            self._barra = None

    def mostrar(self, fabrica, titulo, al_clic=None):
        """Dibuja la figura que crea ``fabrica``. Si tiene mapas, al pasar el ratón se ve la
        información de cada municipio; ``al_clic(lon, lat)`` (opcional) recibe los clics."""
        self._limpiar()
        self._aviso.place_forget()
        self._fabrica, self._titulo = fabrica, titulo
        figura = fabrica()
        lienzo = self._marco.poner(figura)
        self._barra = NavigationToolbar2Tk(lienzo, self._zona_barra, pack_toolbar=False)
        self._barra.configure(background=estilo.SUPERFICIE)
        for hijo in self._barra.winfo_children():
            try:
                hijo.configure(background=estilo.SUPERFICIE)
            except tk.TclError:
                pass
        self._barra.pack(side="left")
        self._boton_ventana.configure(state="normal")
        if figura_tiene_mapas(figura):
            self._info = InfoMapa(self._marco, self._nombre, al_clic=al_clic, barra=self._barra)
            self._pista.configure(text="Pasa el ratón sobre un municipio para ver sus datos"
                                       + (" · clic para mover el origen" if al_clic else ""))
            self._pista.pack(side="right", padx=8)
        else:
            self._pista.pack_forget()

    def _nombre(self, cve):
        return nombre_municipio(self.app, cve)

    @seguro
    def abrir_en_ventana(self):
        if self._fabrica is not None:
            ventana_figura(self.app.root, self._titulo, self._fabrica(), nombres=self._nombre)


class SelectorVistas(ttk.Frame):
    """Botones tipo segmento + explicación "Cómo leer" + panel de figura.

    ``vistas`` es una lista de diccionarios con ``nombre``, ``ayuda`` y ``fabrica`` (función que
    devuelve la figura). La figura solo se crea al seleccionar la vista.
    """

    def __init__(self, master, app, vistas, **kw):
        super().__init__(master, **kw)
        self.app, self.vistas = app, vistas
        self._seleccion = tk.IntVar(value=0)
        self._mostrada = None

        barra = ttk.Frame(self)
        if len(vistas) > 1:                       # con una sola vista no hace falta elegir
            barra.pack(side="top", fill="x", pady=(0, 6))
        for i, v in enumerate(vistas):
            ttk.Radiobutton(barra, text=v["nombre"], value=i, variable=self._seleccion,
                            style="Segmento.Toolbutton",
                            command=self.refrescar).pack(side="left", padx=(0, 4))
        self._ayuda = ttk.Label(self, text="", style="Suave.TLabel", justify="left")
        self._ayuda.pack(side="top", fill="x", pady=(0, 6))
        self._ayuda.bind("<Configure>", lambda e: self._ayuda.configure(wraplength=e.width))
        self.panel = PanelFigura(self, app)
        self.panel.pack(side="top", fill="both", expand=True)

    @property
    def indice(self):
        return self._seleccion.get()

    def seleccionar(self, indice):
        self._seleccion.set(indice)
        self.refrescar()

    @seguro
    def refrescar(self):
        """Vuelve a dibujar la vista seleccionada."""
        v = self.vistas[self.indice]
        self._ayuda.configure(text="Cómo leer: " + v["ayuda"] if v.get("ayuda") else "")
        self.app.ocupado(True)
        try:
            self.panel.mostrar(v["fabrica"], v.get("titulo", v["nombre"]))
        finally:
            self.app.ocupado(False)
        self._mostrada = self.indice


# --------------------------------------------------------------------------- tarjetas y texto
class Tarjeta(ttk.Frame):
    """Tarjeta con un indicador grande (valor) y su descripción."""

    def __init__(self, master, titulo, descripcion="", **kw):
        super().__init__(master, style="Tarjeta.TFrame", padding=(16, 12), **kw)
        etiqueta_ajustable(self, titulo, "TarjetaSuave.TLabel").pack(anchor="w", fill="x")
        self._valor = ttk.Label(self, text="—", style="TarjetaValor.TLabel")
        self._valor.pack(anchor="w", pady=(2, 0))
        self._detalle = ttk.Label(self, text=descripcion, style="TarjetaSuave.TLabel",
                                  justify="left")
        self._detalle.pack(anchor="w", fill="x")
        self._detalle.bind("<Configure>", lambda e: self._detalle.configure(wraplength=e.width))

    def actualizar(self, valor, detalle=None):
        self._valor.configure(text=valor)
        if detalle is not None:
            self._detalle.configure(text=detalle)


class TextoSoloLectura(ttk.Frame):
    """Cuadro de texto monoespaciado con barra de desplazamiento y sin edición."""

    def __init__(self, master, alto=12, ajustar=False, **kw):
        super().__init__(master, style="Tarjeta.TFrame", **kw)
        self.texto = tk.Text(self, wrap="word" if ajustar else "none", height=alto, font=estilo.FUENTES["mono"],
                             bg=estilo.SUPERFICIE, fg=estilo.TEXTO, relief="flat",
                             padx=10, pady=8, borderwidth=0, highlightthickness=0)
        barra_v = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        barra_h = ttk.Scrollbar(self, orient="horizontal", command=self.texto.xview)
        self.texto.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set,
                             state="disabled")
        self.texto.grid(row=0, column=0, sticky="nsew")
        barra_v.grid(row=0, column=1, sticky="ns")
        if not ajustar:                       # con ajuste de línea no hay desplazamiento lateral
            barra_h.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def poner(self, contenido):
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("end", contenido)
        self.texto.configure(state="disabled")


class Deslizador(ttk.Frame):
    """Control deslizante con nombre y valor visible, para usarse dentro de una tarjeta.

    El valor se redondea a múltiplos de ``paso``. ``al_cambiar(valor)`` se llama al soltar el
    control o cuando el usuario deja de moverlo un momento (no se recalcula en cada píxel).
    """
    ESPERA_MS = 350

    def __init__(self, master, texto, desde, hasta, paso, valor, formato="{:g}",
                 al_cambiar=None, ayuda="", **kw):
        super().__init__(master, style="Plano.TFrame", **kw)
        self.desde, self.hasta, self.paso = desde, hasta, paso
        self.formato, self.al_cambiar = formato, al_cambiar
        self._valor = self._redondear(valor)
        self._emitido = self._valor
        self._pendiente = None

        self.columnconfigure(0, weight=1)
        etiqueta_ajustable(self, texto, "Tarjeta.TLabel").grid(row=0, column=0, sticky="ew")
        self._etiqueta = ttk.Label(self, text="", style="TarjetaTitulo.TLabel")
        self._etiqueta.grid(row=0, column=1, sticky="e", padx=(8, 0))
        if ayuda:
            etiqueta_ajustable(self, ayuda, "Pista.TLabel").grid(row=1, column=0, columnspan=2,
                                                               sticky="ew")
        self._escala = ttk.Scale(self, from_=desde, to=hasta, value=self._valor,
                                 style="Tarjeta.Horizontal.TScale", command=self._mover)
        self._escala.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        self._escala.bind("<ButtonRelease-1>", lambda _: self._emitir())
        self._mostrar()

    def _redondear(self, v):
        v = round((float(v) - self.desde) / self.paso) * self.paso + self.desde
        return round(min(self.hasta, max(self.desde, v)), 6)

    def _mostrar(self):
        f = self.formato
        self._etiqueta.configure(text=f(self._valor) if callable(f) else f.format(self._valor))

    @property
    def valor(self):
        return self._valor

    def poner(self, valor, notificar=False):
        """Cambia el valor desde el programa (por omisión sin llamar a ``al_cambiar``)."""
        self._valor = self._redondear(valor)
        self._escala.set(self._valor)
        self._mostrar()
        if notificar:
            self._emitir()
        else:
            self._emitido = self._valor

    def _mover(self, crudo):
        nuevo = self._redondear(crudo)
        if nuevo == self._valor:
            return
        self._valor = nuevo
        self._mostrar()
        if self._pendiente is not None:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(self.ESPERA_MS, self._emitir)

    def _emitir(self):
        if self._pendiente is not None:
            self.after_cancel(self._pendiente)
            self._pendiente = None
        if self._valor != self._emitido:
            self._emitido = self._valor
            if self.al_cambiar is not None:
                self.al_cambiar(self._valor)


def etiqueta_ajustable(master, texto, estilo_ttk="TLabel", **kw):
    """Etiqueta cuyo texto se reacomoda al ancho disponible."""
    lbl = ttk.Label(master, text=texto, style=estilo_ttk, justify="left", **kw)
    lbl.bind("<Configure>", lambda e: lbl.configure(wraplength=max(50, e.width)))
    return lbl


def panel_ancho_fijo(master, ancho, **kw):
    """Marco de ancho fijo: su contenido se acomoda a ese ancho en vez de ensancharlo."""
    marco = ttk.Frame(master, width=ancho, **kw)
    marco.pack_propagate(False)
    return marco


class MarcoDesplazable(ttk.Frame):
    """Contenedor con barra de desplazamiento vertical (aparece solo si el contenido no cabe).

    Los widgets se colocan dentro de ``self.interior``.
    """

    def __init__(self, master, fondo=None, estilo_interior="TFrame", **kw):
        super().__init__(master, **kw)
        self._lienzo = tk.Canvas(self, bg=fondo or estilo.FONDO, highlightthickness=0,
                                 borderwidth=0)
        self._barra = ttk.Scrollbar(self, orient="vertical", command=self._lienzo.yview)
        self._lienzo.configure(yscrollcommand=self._barra.set)
        self.interior = ttk.Frame(self._lienzo, style=estilo_interior)
        self._ventana = self._lienzo.create_window(0, 0, window=self.interior, anchor="nw")
        self._lienzo.pack(side="left", fill="both", expand=True)
        self.interior.bind("<Configure>", lambda _: self._actualizar())
        self._lienzo.bind("<Configure>", lambda _: self._actualizar())
        self._lienzo.bind("<Enter>", lambda _: self._lienzo.bind_all("<MouseWheel>", self._rueda))
        self._lienzo.bind("<Leave>", lambda _: self._lienzo.unbind_all("<MouseWheel>"))

    def _actualizar(self):
        ancho, alto = self._lienzo.winfo_width(), self._lienzo.winfo_height()
        self._lienzo.itemconfigure(self._ventana, width=ancho)
        self._lienzo.configure(scrollregion=(0, 0, ancho, self.interior.winfo_reqheight()))
        if self.interior.winfo_reqheight() > alto + 1:
            if not self._barra.winfo_ismapped():
                self._barra.pack(side="right", fill="y", before=self._lienzo)
        elif self._barra.winfo_ismapped():
            self._barra.pack_forget()
            self._lienzo.yview_moveto(0)

    def _rueda(self, evento):
        if self._barra.winfo_ismapped():
            self._lienzo.yview_scroll(int(-evento.delta / 120), "units")


# --------------------------------------------------------------------------- diálogos
class DialogoClaveNueva(tk.Toplevel):
    """Diálogo modal para escribir y confirmar una contraseña nueva.

    Tras cerrarse, ``resultado`` contiene la contraseña o ``None`` si se canceló.
    """

    def __init__(self, master, minimo):
        super().__init__(master)
        self.title("Cambiar contraseña")
        self.configure(bg=estilo.SUPERFICIE)
        self.resizable(False, False)
        self.transient(master)
        self.resultado = None
        self._minimo = minimo

        marco = ttk.Frame(self, style="Tarjeta.TFrame", padding=20)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Contraseña nueva", style="TarjetaTitulo.TLabel").pack(anchor="w")
        ttk.Label(marco, text=f"Mínimo {minimo} caracteres. El registro se volverá a cifrar.",
                  style="TarjetaSuave.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(marco, text="Nueva", style="Tarjeta.TLabel").pack(anchor="w")
        self._nueva = ttk.Entry(marco, show="•", width=32)
        self._nueva.pack(fill="x", pady=(0, 8))
        ttk.Label(marco, text="Confirmar", style="Tarjeta.TLabel").pack(anchor="w")
        self._confirma = ttk.Entry(marco, show="•", width=32)
        self._confirma.pack(fill="x")
        self._error = ttk.Label(marco, text="", style="TarjetaError.TLabel")
        self._error.pack(anchor="w", pady=(6, 0))
        botones = ttk.Frame(marco, style="Tarjeta.TFrame")
        botones.pack(fill="x", pady=(10, 0))
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(botones, text="Guardar", style="Primario.TButton",
                   command=self._aceptar).pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda _: self._aceptar())
        self.bind("<Escape>", lambda _: self.destroy())
        self._nueva.focus_set()
        self.grab_set()
        master.wait_window(self)

    def _aceptar(self):
        nueva, confirma = self._nueva.get(), self._confirma.get()
        if len(nueva) < self._minimo:
            self._error.configure(text=f"Debe tener al menos {self._minimo} caracteres.")
        elif nueva != confirma:
            self._error.configure(text="Las contraseñas no coinciden.")
        else:
            self.resultado = nueva
            self.destroy()
