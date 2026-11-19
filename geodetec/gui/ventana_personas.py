"""Ventana del registro confidencial de personas (datos ficticios)."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..busqueda import zona_busqueda_punto
from ..figuras import fig_busqueda, fig_personas
from ..personas import cambiar_contrasena
from .comun import pedir_contrasena, seguro, ventana_figura


class VentanaPersonas:
    """Tabla de personas + acciones (ficha, mapa, zona de búsqueda, cambio de contraseña)."""

    COLUMNAS = ("folio", "nombre", "edad", "sexo", "fecha", "municipio")
    ANCHOS = (110, 330, 50, 70, 100, 230)

    def __init__(self, app, clave, lista):
        self.app, self.clave, self.lista = app, clave, lista
        self.v = v = tk.Toplevel(app.root)
        v.title("Personas desaparecidas – registro confidencial (datos ficticios)")
        v.geometry("980x420")
        tk.Label(v, text="ACCESO AUTORIZADO – información confidencial (personas ficticias)",
                 fg="#8b0000", font=("Helvetica", 11, "bold")).pack(pady=(10, 4))
        self._crear_tabla()
        self._crear_botones()

    def _crear_tabla(self):
        self.tabla = tabla = ttk.Treeview(self.v, columns=self.COLUMNAS, show="headings", height=6)
        for c, w in zip(self.COLUMNAS, self.ANCHOS):
            tabla.heading(c, text=c.capitalize())
            tabla.column(c, width=w, anchor="w")
        for p in self.lista:
            tabla.insert("", "end", iid=p["id"], tags=(p["id"],),
                         values=(p["folio"], p["nombre"], p["edad"], p["sexo"],
                                 p["fecha_desaparicion"], p["municipio"]))
            tabla.tag_configure(p["id"], background=p["color"], foreground="white")
        tabla.pack(fill="x", padx=10, pady=5)
        tabla.selection_set(self.lista[0]["id"])

    def _crear_botones(self):
        barra = tk.Frame(self.v)
        barra.pack(pady=10)
        for texto, cmd in (("Ver ficha completa", self.ver_ficha),
                           ("Mapa de todas las ubicaciones", self.mapa_personas),
                           ("Zona de búsqueda de la persona", self.zona_persona),
                           ("Cambiar contraseña", self.nueva_clave)):
            tk.Button(barra, text=texto, command=cmd, width=26).pack(side="left", padx=5)

    def seleccionada(self):
        sel = self.tabla.selection()
        objetivo = sel[0] if sel else self.lista[0]["id"]
        return next(p for p in self.lista if p["id"] == objetivo)

    @seguro
    def ver_ficha(self):
        p = self.seleccionada()
        messagebox.showinfo(p["id"], (
            f"Folio: {p['folio']}\nNombre: {p['nombre']}\nEdad: {p['edad']} años\n"
            f"Sexo: {p['sexo']}\nEstatura: {p['estatura_cm']} cm\n"
            f"Complexión: {p['complexion']}\nSeñas particulares: {p['senas_particulares']}\n"
            f"Vestimenta: {p['vestimenta']}\nFecha de desaparición: {p['fecha_desaparicion']}\n"
            f"Última ubicación: {p['municipio']} ({p['lat']}, {p['lon']})\n"
            f"Color asignado: {p['color']}"), parent=self.v)

    @seguro
    def mapa_personas(self):
        g = self.app.g
        if self.app.requiere("mapa_pred"):
            ventana_figura(self.app.root, "Últimas ubicaciones por persona",
                           fig_personas(self.lista, g.mapa_pred, g.mun, g.geoms))

    @seguro
    def zona_persona(self):
        g = self.app.g
        if self.app.requiere("mapa_pred"):
            p = self.seleccionada()
            zona = zona_busqueda_punto(g.mapa_pred, g.mun, p["lon"], p["lat"])
            ventana_figura(self.app.root, f"Zona de búsqueda – {p['id']}",
                           fig_busqueda(zona, g.geoms, p["lon"], p["lat"],
                                        f"{p['id']} ({p['municipio']})",
                                        color_zona=p["color"], color_punto=p["color"],
                                        cmap="Greys"))

    @seguro
    def nueva_clave(self):
        root = self.app.root
        n1 = pedir_contrasena(root, "Cambiar contraseña", "Contraseña nueva (mín. 8 caracteres):")
        if not n1:
            return
        n2 = pedir_contrasena(root, "Cambiar contraseña", "Confirma la contraseña nueva:")
        if n1 != n2:
            messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=self.v)
            return
        cambiar_contrasena(self.clave, n1)
        messagebox.showinfo("Listo", "Contraseña actualizada. El registro se volvió a cifrar.",
                            parent=self.v)
        self.v.destroy()
