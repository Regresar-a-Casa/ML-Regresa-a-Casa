"""Piezas reutilizables de la interfaz Tkinter: manejo de errores, ventanas y diálogos."""
import functools
import tkinter as tk
from tkinter import messagebox, scrolledtext

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


def seguro(func):
    """Decorador: cualquier excepción se muestra en un cuadro de error en vez de romper la GUI."""
    @functools.wraps(func)
    def envoltura(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    return envoltura


def ventana_figura(root, titulo, fig):
    """Abre una figura de matplotlib en una ventana nueva con barra de herramientas."""
    v = tk.Toplevel(root)
    v.title(titulo)
    canvas = FigureCanvasTkAgg(fig, master=v)
    canvas.draw()
    NavigationToolbar2Tk(canvas, v)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    return v


def ventana_texto(root, titulo, texto, tamano):
    """Ventana de solo lectura con texto en fuente monoespaciada."""
    v = tk.Toplevel(root)
    v.title(titulo)
    v.geometry(tamano)
    t = scrolledtext.ScrolledText(v, wrap=tk.WORD, font=("Courier", 10))
    t.pack(expand=True, fill="both", padx=10, pady=10)
    t.insert(tk.END, texto)
    t.config(state=tk.DISABLED)
    return v


def pedir_contrasena(root, titulo, texto):
    """Diálogo modal con campo oculto. Devuelve el texto o ``None`` si se cerró la ventana."""
    resultado = {"valor": None}
    d = tk.Toplevel(root)
    d.title(titulo)
    d.resizable(False, False)
    d.grab_set()
    tk.Label(d, text=texto, font=("Helvetica", 11)).pack(padx=20, pady=(15, 5))
    e = tk.Entry(d, show="*", width=30, font=("Helvetica", 11))
    e.pack(padx=20, pady=5)
    e.focus_set()

    def aceptar(_=None):
        resultado["valor"] = e.get()
        d.destroy()

    e.bind("<Return>", aceptar)
    tk.Button(d, text="Aceptar", command=aceptar, width=12).pack(pady=12)
    root.wait_window(d)
    return resultado["valor"]
