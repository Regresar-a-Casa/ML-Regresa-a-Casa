"""Clase base de las pestañas de la ventana principal."""
from tkinter import ttk

from ..componentes import etiqueta_ajustable


class Pestana(ttk.Frame):
    """Pestaña con encabezado (título + descripción) y dibujo perezoso.

    - ``construir()`` crea los widgets una sola vez.
    - ``renderizar()`` dibuja el contenido que depende del modelo; se llama la primera vez que la
      pestaña se muestra después de que el sistema está listo (así el arranque es más rápido).
    """
    titulo = ""
    descripcion = ""
    requiere_sistema = True

    def __init__(self, master, app):
        super().__init__(master, padding=(18, 14))
        self.app = app
        self._pendiente = True
        if self.titulo:
            ttk.Label(self, text=self.titulo, style="Titulo.TLabel").pack(anchor="w")
        if self.descripcion:
            etiqueta_ajustable(self, self.descripcion, "Suave.TLabel").pack(
                anchor="w", fill="x", pady=(2, 12))
        self.contenido = ttk.Frame(self)
        self.contenido.pack(fill="both", expand=True)
        self.construir()

    @property
    def g(self):
        return self.app.g

    def construir(self):
        """Crear widgets (sobrescribir)."""

    def renderizar(self):
        """Dibujar contenido dependiente del modelo (sobrescribir)."""

    def sistema_listo(self):
        """El sistema terminó de entrenar: la próxima vez que se muestre, se dibuja."""
        self._pendiente = True

    def al_mostrar(self):
        if self._pendiente and (self.app.listo or not self.requiere_sistema):
            self._pendiente = False
            self.renderizar()
