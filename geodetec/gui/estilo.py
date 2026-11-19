"""Estilo visual de la interfaz: paleta, tipografías y configuración de ttk.

Todas las fuentes son objetos ``tkinter.font.Font`` con nombre: al cambiar su tamaño (modo
presentación) se actualizan solas en todos los widgets que las usan.
"""
import tkinter.font as tkfont
from tkinter import ttk

# --------------------------------------------------------------------------- paleta
FONDO = "#f3f5f8"           # fondo general
SUPERFICIE = "#ffffff"      # tarjetas y paneles
BORDE = "#d8dee6"
TEXTO = "#1f2933"
TEXTO_SUAVE = "#5f6b7a"
PRIMARIO = "#1e3d59"        # azul institucional (encabezado, pestaña activa)
PRIMARIO_CLARO = "#e3ebf3"
ACENTO = "#c0392b"          # acciones principales
ACENTO_OSCURO = "#a93226"
CONFIDENCIAL = "#6c1d45"    # secciones restringidas
EXITO = "#1e8449"
INFO_FONDO = "#1f2933"   # recuadro informativo sobre los mapas
INFO_TEXTO = "#f5f7fa"
ERROR = "#c0392b"

# --------------------------------------------------------------------------- tipografía
_FAMILIAS_PREFERIDAS = ("Segoe UI", "Helvetica Neue", "Helvetica", "Arial")
_MONO_PREFERIDAS = ("Cascadia Mono", "Consolas", "Courier New", "Courier")

# nombre -> (tamaño base, peso)
_FUENTES = {
    "base": (10, "normal"),
    "pequena": (9, "normal"),
    "negrita": (10, "bold"),
    "subtitulo": (12, "bold"),
    "titulo": (16, "bold"),
    "marca": (22, "bold"),
    "valor": (22, "bold"),
    "pestana": (11, "normal"),
}

FUENTES = {}
_escala_actual = 1.0


def _elegir_familia(preferidas):
    disponibles = set(tkfont.families())
    return next((f for f in preferidas if f in disponibles), "TkDefaultFont")


def _crear_fuentes(root):
    familia = _elegir_familia(_FAMILIAS_PREFERIDAS)
    mono = _elegir_familia(_MONO_PREFERIDAS)
    for nombre, (tam, peso) in _FUENTES.items():
        FUENTES[nombre] = tkfont.Font(root=root, name=f"geodetec_{nombre}", family=familia,
                                      size=tam, weight=peso)
    FUENTES["mono"] = tkfont.Font(root=root, name="geodetec_mono", family=mono, size=9)
    # Las fuentes por defecto de Tk también siguen la escala (diálogos, Treeview, etc.)
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(nombre, root=root).configure(family=familia, size=10)
        except Exception:
            pass


def escalar(factor):
    """Cambia el tamaño de todas las fuentes (1.0 = normal; 1.3 = modo presentación)."""
    global _escala_actual
    _escala_actual = factor
    for nombre, (tam, _) in _FUENTES.items():
        FUENTES[nombre].configure(size=round(tam * factor))
    FUENTES["mono"].configure(size=round(9 * factor))
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(nombre).configure(size=round(10 * factor))
        except Exception:
            pass
    estilo = ttk.Style()
    estilo.configure("Treeview", rowheight=round(24 * factor))


def escala_actual():
    return _escala_actual


def aplicar(root):
    """Configura el tema ttk y las fuentes. Llamar una vez, después de crear ``tk.Tk()``."""
    _crear_fuentes(root)
    root.configure(bg=FONDO)
    e = ttk.Style(root)
    e.theme_use("clam")   # permite personalizar colores de forma consistente en Windows

    e.configure(".", background=FONDO, foreground=TEXTO, font=FUENTES["base"],
                bordercolor=BORDE, lightcolor=FONDO, darkcolor=FONDO, focuscolor=PRIMARIO)
    e.configure("TFrame", background=FONDO)
    e.configure("Tarjeta.TFrame", background=SUPERFICIE, relief="solid", borderwidth=1)
    e.configure("Encabezado.TFrame", background=PRIMARIO)
    e.configure("Plano.TFrame", background=SUPERFICIE)   # fondo de tarjeta sin borde

    # Etiquetas
    e.configure("TLabel", background=FONDO, foreground=TEXTO)
    e.configure("Suave.TLabel", foreground=TEXTO_SUAVE)
    e.configure("Titulo.TLabel", font=FUENTES["titulo"], foreground=PRIMARIO)
    e.configure("Subtitulo.TLabel", font=FUENTES["subtitulo"], foreground=TEXTO)
    e.configure("Error.TLabel", foreground=ERROR)
    e.configure("Marca.TLabel", background=PRIMARIO, foreground="white", font=FUENTES["marca"])
    e.configure("EncabezadoTexto.TLabel", background=PRIMARIO, foreground="#c9d6e3",
                font=FUENTES["base"])
    e.configure("Tarjeta.TLabel", background=SUPERFICIE, foreground=TEXTO)
    e.configure("TarjetaSuave.TLabel", background=SUPERFICIE, foreground=TEXTO_SUAVE,
                font=FUENTES["pequena"])
    e.configure("TarjetaTitulo.TLabel", background=SUPERFICIE, foreground=PRIMARIO,
                font=FUENTES["subtitulo"])
    e.configure("TarjetaValor.TLabel", background=SUPERFICIE, foreground=PRIMARIO,
                font=FUENTES["valor"])
    e.configure("TarjetaError.TLabel", background=SUPERFICIE, foreground=ERROR)
    e.configure("Confidencial.TLabel", background=SUPERFICIE, foreground=CONFIDENCIAL,
                font=FUENTES["subtitulo"])
    e.configure("Estado.TLabel", background=SUPERFICIE, foreground=TEXTO_SUAVE,
                font=FUENTES["pequena"])

    # Botones
    e.configure("TButton", padding=(12, 6), background=SUPERFICIE, foreground=TEXTO,
                bordercolor=BORDE, font=FUENTES["base"])
    e.map("TButton", background=[("active", PRIMARIO_CLARO), ("disabled", FONDO)],
          foreground=[("disabled", "#9aa5b1")])
    for nombre, color, activo in (("Primario", ACENTO, ACENTO_OSCURO),
                                  ("Confidencial", CONFIDENCIAL, "#561737"),
                                  ("Encabezado", "#2c5578", "#365f86")):
        e.configure(f"{nombre}.TButton", background=color, foreground="white",
                    bordercolor=color, font=FUENTES["negrita"])
        e.map(f"{nombre}.TButton", background=[("active", activo), ("disabled", "#b8c2cc")],
              foreground=[("disabled", "#eef1f4")])

    # Selector de vistas (botones tipo "segmento")
    e.configure("Segmento.Toolbutton", padding=(14, 6), background=SUPERFICIE,
                foreground=TEXTO, bordercolor=BORDE, font=FUENTES["base"])
    e.map("Segmento.Toolbutton",
          background=[("selected", PRIMARIO), ("active", PRIMARIO_CLARO)],
          foreground=[("selected", "white")])

    # Pestañas
    e.configure("TNotebook", background=FONDO, borderwidth=0, tabmargins=(8, 6, 8, 0))
    e.configure("TNotebook.Tab", padding=(18, 8), background="#e6eaf0", foreground=TEXTO_SUAVE,
                font=FUENTES["pestana"], bordercolor=BORDE)
    e.map("TNotebook.Tab",
          background=[("selected", SUPERFICIE), ("disabled", "#eef1f4")],
          foreground=[("selected", PRIMARIO), ("disabled", "#aab4bf")])
    e.configure("Interno.TNotebook", background=SUPERFICIE, tabmargins=(4, 4, 4, 0))
    e.configure("Interno.TNotebook.Tab", padding=(14, 6), font=FUENTES["base"])

    # Entradas, listas y tablas
    e.configure("TEntry", padding=6, fieldbackground=SUPERFICIE)
    e.configure("TCombobox", padding=5, fieldbackground=SUPERFICIE)
    e.configure("Treeview", background=SUPERFICIE, fieldbackground=SUPERFICIE,
                rowheight=24, bordercolor=BORDE)
    e.map("Treeview", background=[("selected", PRIMARIO)], foreground=[("selected", "white")])
    e.configure("Treeview.Heading", background="#e6eaf0", foreground=TEXTO,
                font=FUENTES["negrita"], relief="flat")
    e.configure("TProgressbar", background=PRIMARIO, troughcolor="#e6eaf0", bordercolor=BORDE)
    e.configure("TSeparator", background=BORDE)
    e.configure("Tarjeta.Horizontal.TScale", background=SUPERFICIE, troughcolor="#e6eaf0",
                bordercolor=BORDE, lightcolor=SUPERFICIE, darkcolor=BORDE)
    e.map("Tarjeta.Horizontal.TScale", background=[("active", PRIMARIO_CLARO)])
    e.configure("Pista.TLabel", background=SUPERFICIE, foreground=TEXTO_SUAVE,
                font=FUENTES["pequena"])
    return e
