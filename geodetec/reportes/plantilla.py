"""Plantilla común de los reportes PDF de GEODETEC.

Todos los reportes comparten el mismo formato: portada, encabezado y pie en cada página, títulos de
sección, párrafos, viñetas, recuadros destacados, tablas y el **bloque de gráfica** estándar:

    título · gráfica · "Qué muestra" (explicación) · "Interpretación" (lectura de los datos)

Se construye con matplotlib (``PdfPages``), sin dependencias extra. Uso típico::

    r = Reporte("Título", "Subtítulo")
    r.portada([("Fecha", "..."), ...], aviso="...")
    r.seccion("1. Resumen")
    r.parrafo("...")
    r.grafica("Mapa", figura, que_muestra="...", interpretacion=["...", "..."])
    r.guardar("reporte.pdf")
"""
import io
import textwrap
from datetime import datetime

import matplotlib.image as mpimg
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Rectangle

# --------------------------------------------------------------------------- medidas (pulgadas)
ANCHO, ALTO = 8.27, 11.69            # A4 vertical
MARGEN_X = 0.75
MARGEN_SUP = 0.95                    # deja lugar al encabezado
MARGEN_INF = 0.85                    # deja lugar al pie
ANCHO_UTIL = ANCHO - 2 * MARGEN_X

# --------------------------------------------------------------------------- estilo
PRIMARIO = "#1e3d59"
ACENTO = "#c0392b"
TEXTO = "#1f2933"
SUAVE = "#5f6b7a"
FONDO_INFO = "#eef3f8"
FONDO_AVISO = "#fdf2e9"
BORDE_AVISO = "#e67e22"
FONDO_INTERP = "#eaf5ee"
BORDE_INTERP = "#1e8449"
TAM_TEXTO = 9.5
INTERLINEADO = 1.42


def _caracteres(tam, ancho_in=ANCHO_UTIL):
    """Caracteres por línea aproximados para un tamaño de letra (DejaVu Sans)."""
    return max(20, int(ancho_in * 72 / (tam * 0.515)))


def _alto_lineas(n, tam):
    return n * tam * INTERLINEADO / 72


def _envolver(texto, tam, ancho_in=ANCHO_UTIL, sangria=""):
    lineas = []
    for parrafo in str(texto).split("\n"):
        lineas += textwrap.wrap(parrafo, _caracteres(tam, ancho_in), subsequent_indent=sangria) or [""]
    return lineas


def figura_a_imagen(fig, dpi=200):
    """Rasteriza una figura de matplotlib para incrustarla en una página."""
    buf = io.BytesIO()
    FigureCanvasAgg(fig)
    fig.savefig(buf, format="png", dpi=dpi)
    buf.seek(0)
    return mpimg.imread(buf)


class Reporte:
    """Documento PDF con el formato común de GEODETEC."""

    def __init__(self, titulo, subtitulo="", pie="", confidencial=True):
        self.titulo, self.subtitulo = titulo, subtitulo
        self.pie = pie
        self.confidencial = confidencial
        self.fecha = datetime.now()
        self.paginas = []
        self._nueva_pagina()

    # ------------------------------------------------------------------ paginación
    @property
    def pagina(self):
        return self.paginas[-1]

    def _nueva_pagina(self):
        self.paginas.append(Figure(figsize=(ANCHO, ALTO)))
        self.y = MARGEN_SUP

    def _reservar(self, alto):
        """Salta de página si ``alto`` (pulgadas) no cabe en la actual."""
        if self.y + alto > ALTO - MARGEN_INF and self.y > MARGEN_SUP + 0.01:
            self._nueva_pagina()

    def salto_pagina(self):
        if self.y > MARGEN_SUP + 0.01:
            self._nueva_pagina()

    def espacio(self, alto=0.12):
        self.y += alto

    def _texto(self, x, y, texto, **kw):
        kw.setdefault("color", TEXTO)
        kw.setdefault("fontsize", TAM_TEXTO)
        self.pagina.text(x / ANCHO, 1 - y / ALTO, texto, va="top", ha="left",
                         linespacing=INTERLINEADO, **kw)

    def _rect(self, x, y, w, h, **kw):
        self.pagina.patches.append(Rectangle((x / ANCHO, 1 - (y + h) / ALTO), w / ANCHO,
                                             h / ALTO, transform=self.pagina.transFigure, **kw))

    # ------------------------------------------------------------------ bloques de texto
    def portada(self, datos, aviso=None, nota=None):
        """Primera página: título, datos del documento, aviso y nota opcional."""
        self._rect(0, 0, ANCHO, 3.1, color=PRIMARIO, zorder=0)
        self._texto(MARGEN_X, 0.9, "GEODETEC", fontsize=13, color="white", fontweight="bold")
        self._texto(MARGEN_X, 1.35, "\n".join(_envolver(self.titulo, 22)), fontsize=22,
                    color="white", fontweight="bold")
        if self.subtitulo:
            self._texto(MARGEN_X, 2.45, "\n".join(_envolver(self.subtitulo, 11.5)),
                        fontsize=11.5, color="#d6e2ee")
        self.y = 3.55
        for etiqueta, valor in datos:
            lineas = _envolver(valor, 10.5, ANCHO_UTIL - 2.1)
            self._texto(MARGEN_X, self.y, etiqueta, fontsize=10.5, color=SUAVE)
            self._texto(MARGEN_X + 2.1, self.y, "\n".join(lineas), fontsize=10.5)
            self.y += _alto_lineas(len(lineas), 10.5) + 0.08
        self.espacio(0.25)
        if aviso:
            self.recuadro("Importante", aviso, fondo=FONDO_AVISO, borde=BORDE_AVISO)
        if nota:
            self.recuadro("Nota", nota)
        self._nueva_pagina()

    def seccion(self, texto, reservar=0.9):
        """Título de sección. ``reservar`` (pulgadas) = espacio que necesita lo que sigue, para
        que el título no quede solo al final de una página."""
        self._reservar(min(reservar, ALTO - MARGEN_SUP - MARGEN_INF))
        self.espacio(0.1)
        self._texto(MARGEN_X, self.y, texto, fontsize=14, color=PRIMARIO, fontweight="bold")
        self.y += 0.3
        self.pagina.add_artist(_linea(self.y, PRIMARIO, 1.2))
        self.y += 0.15

    def subseccion(self, texto):
        self._reservar(0.6)
        self._texto(MARGEN_X, self.y, texto, fontsize=11.5, color=PRIMARIO, fontweight="bold")
        self.y += 0.28

    def parrafo(self, texto, tam=TAM_TEXTO, color=TEXTO):
        for linea in _envolver(texto, tam):          # línea por línea: puede partir páginas
            self._reservar(_alto_lineas(1, tam))
            self._texto(MARGEN_X, self.y, linea, fontsize=tam, color=color)
            self.y += _alto_lineas(1, tam)
        self.y += 0.08

    def vinetas(self, elementos, tam=TAM_TEXTO):
        for e in elementos:
            lineas = _envolver(e, tam, ANCHO_UTIL - 0.25)
            self._reservar(_alto_lineas(len(lineas), tam))
            self._texto(MARGEN_X + 0.05, self.y, "•", fontsize=tam, color=PRIMARIO)
            self._texto(MARGEN_X + 0.25, self.y, "\n".join(lineas), fontsize=tam)
            self.y += _alto_lineas(len(lineas), tam) + 0.04
        self.y += 0.06

    @staticmethod
    def _lineas_recuadro(contenido, tam):
        ancho_txt = ANCHO_UTIL - 2 * 0.14 - 0.2
        if isinstance(contenido, (list, tuple)):
            lineas = []
            for e in contenido:
                partes = _envolver(e, tam, ancho_txt - 0.1, sangria="  ")
                lineas += ["• " + partes[0]] + partes[1:]
            return lineas
        return _envolver(contenido, tam, ancho_txt)

    def _alto_recuadro(self, contenido, tam=TAM_TEXTO):
        return 0.14 * 2 + 0.26 + _alto_lineas(len(self._lineas_recuadro(contenido, tam)), tam)

    def recuadro(self, titulo, contenido, fondo=FONDO_INFO, borde=PRIMARIO, tam=TAM_TEXTO):
        """Caja destacada. ``contenido`` puede ser texto o una lista (viñetas)."""
        pad = 0.14
        lineas = self._lineas_recuadro(contenido, tam)
        alto = self._alto_recuadro(contenido, tam)
        if alto > ALTO - MARGEN_SUP - MARGEN_INF:     # muy largo: sin caja
            self.subseccion(titulo)
            return self.vinetas(contenido, tam) if isinstance(contenido, (list, tuple)) \
                else self.parrafo(contenido, tam)
        self._reservar(alto)
        y0 = self.y
        caja = FancyBboxPatch(((MARGEN_X) / ANCHO, 1 - (y0 + alto) / ALTO), ANCHO_UTIL / ANCHO,
                              alto / ALTO, boxstyle="round,pad=0,rounding_size=0.006",
                              transform=self.pagina.transFigure, facecolor=fondo,
                              edgecolor="none", zorder=0)
        self.pagina.patches.append(caja)
        self._rect(MARGEN_X, y0, 0.06, alto, color=borde, zorder=1)
        self._texto(MARGEN_X + 0.2, y0 + pad, titulo, fontsize=tam + 0.5, color=borde,
                    fontweight="bold")
        self._texto(MARGEN_X + 0.2, y0 + pad + 0.26, "\n".join(lineas), fontsize=tam)
        self.y = y0 + alto + 0.14

    # ------------------------------------------------------------------ gráficas y tablas
    def figura(self, fig, alto_max=5.2, ancho_max=ANCHO_UTIL):
        """Incrusta una figura de matplotlib conservando su proporción."""
        w, h = fig.get_size_inches()
        escala = min(ancho_max / w, alto_max / h)
        ancho, alto = w * escala, h * escala
        self._reservar(alto)
        x = MARGEN_X + (ANCHO_UTIL - ancho) / 2
        ax = self.pagina.add_axes([x / ANCHO, 1 - (self.y + alto) / ALTO, ancho / ANCHO,
                                   alto / ALTO])
        ax.imshow(figura_a_imagen(fig), interpolation="lanczos")
        ax.axis("off")
        self.y += alto + 0.1

    def grafica(self, titulo, fig, que_muestra, interpretacion, alto_max=5.0, seccion=None):
        """Bloque estándar: título, gráfica, explicación e interpretación de los datos.

        Si el bloque completo cabe en una página, no se parte entre páginas. ``seccion`` (opcional)
        antepone un título de sección que viaja junto con el bloque."""
        w, h = fig.get_size_inches()
        alto_fig = min(ANCHO_UTIL / w, alto_max / h) * h
        total = (0.28 + alto_fig + 0.1 + self._alto_recuadro(que_muestra) + 0.14
                 + self._alto_recuadro(interpretacion) + 0.14 + (0.65 if seccion else 0))
        if total <= ALTO - MARGEN_SUP - MARGEN_INF:
            self._reservar(total)
        else:
            self._reservar(0.28 + alto_fig + 0.6)   # al menos título, gráfica e inicio del texto
        if seccion:
            self.seccion(seccion, reservar=0)
        self.subseccion(titulo)
        self.figura(fig, alto_max)
        self.recuadro("Qué muestra", que_muestra)
        self.recuadro("Interpretación", interpretacion, fondo=FONDO_INTERP, borde=BORDE_INTERP)

    def tabla(self, columnas, filas, anchos=None, tam=8.3, encabezado=PRIMARIO):
        """Tabla simple. ``columnas`` = títulos; ``filas`` = listas de textos. Se parte entre
        páginas repitiendo el encabezado."""
        n = len(columnas)
        anchos = anchos or [1 / n] * n
        total = sum(anchos)
        anchos = [a / total * ANCHO_UTIL for a in anchos]
        alto_fila = _alto_lineas(1, tam) + 0.07

        def cortar(texto, ancho):
            maximo = max(3, int((ancho - 0.1) * 72 / (tam * 0.55)))
            texto = str(texto)
            return texto if len(texto) <= maximo else texto[:maximo - 1] + "…"

        def encabezar():
            self._rect(MARGEN_X, self.y, ANCHO_UTIL, alto_fila, color=encabezado)
            x = MARGEN_X
            for c, a in zip(columnas, anchos):
                self._texto(x + 0.05, self.y + 0.035, cortar(c, a), fontsize=tam, color="white",
                            fontweight="bold")
                x += a
            self.y += alto_fila

        total = alto_fila * (len(filas) + 1)
        util = ALTO - MARGEN_SUP - MARGEN_INF
        self._reservar(total if total <= util else alto_fila * 3)   # tablas cortas: enteras
        encabezar()
        for i, fila in enumerate(filas):
            if self.y + alto_fila > ALTO - MARGEN_INF:
                self._nueva_pagina()
                encabezar()
            if i % 2:
                self._rect(MARGEN_X, self.y, ANCHO_UTIL, alto_fila, color="#f2f5f8")
            x = MARGEN_X
            for v, a in zip(fila, anchos):
                self._texto(x + 0.05, self.y + 0.035, cortar(v, a), fontsize=tam)
                x += a
            self.y += alto_fila
        self.y += 0.15

    # ------------------------------------------------------------------ salida
    def _marco(self, fig, numero, total):
        if numero > 1:
            fig.text(MARGEN_X / ANCHO, 1 - 0.45 / ALTO, f"GEODETEC · {self.titulo}",
                     fontsize=8, color=SUAVE, va="center")
            fig.add_artist(_linea(0.6, "#c9d3de", 0.6))
        fig.add_artist(_linea(ALTO - 0.6, "#c9d3de", 0.6))
        izquierda = self.pie or f"Generado el {self.fecha:%d/%m/%Y %H:%M}"
        if self.confidencial:
            izquierda += " · Documento confidencial: puede contener datos personales"
        fig.text(MARGEN_X / ANCHO, 0.42 / ALTO, izquierda, fontsize=7.5, color=SUAVE,
                 va="center")
        fig.text(1 - MARGEN_X / ANCHO, 0.42 / ALTO, f"Página {numero} de {total}", fontsize=7.5,
                 color=SUAVE, va="center", ha="right")

    def guardar(self, ruta):
        """Escribe el PDF. Devuelve el número de páginas."""
        if self.y <= MARGEN_SUP + 0.01 and len(self.paginas) > 1:
            self.paginas.pop()                  # última página vacía
        total = len(self.paginas)
        with PdfPages(ruta, metadata={"Title": self.titulo, "Subject": self.subtitulo,
                                      "Creator": "GEODETEC", "CreationDate": self.fecha}) as pdf:
            for i, fig in enumerate(self.paginas, 1):
                self._marco(fig, i, total)
                pdf.savefig(fig)
        return total


def _linea(y_in, color, ancho):
    from matplotlib.lines import Line2D
    return Line2D([MARGEN_X / ANCHO, 1 - MARGEN_X / ANCHO], [1 - y_in / ALTO] * 2,
                  color=color, linewidth=ancho)
