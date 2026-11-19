"""Pestaña del mapa de prioridad por municipio."""
from ...figuras import fig_mapa
from ..componentes import SelectorVistas
from .base import Pestana


class PestanaPrioridad(Pestana):
    titulo = "Mapa de prioridad"
    descripcion = ("Prioridad de búsqueda de cada uno de los 125 municipios del Estado de México "
                   "según la regla y según el modelo entrenado con datos simulados.")

    def construir(self):
        self.selector = SelectorVistas(self.contenido, self.app, [
            {"nombre": "Regla vs. modelo",
             "titulo": "Mapa de prioridad – Estado de México",
             "ayuda": "izquierda: prioridad según la regla (la referencia). Centro: prioridad que "
                      "predice el modelo (verde = Baja, amarillo = Media, rojo = Alta). Derecha: "
                      "probabilidad de prioridad Alta; entre más claro, más probable. Esta "
                      "probabilidad es la que alimenta la zona de búsqueda.",
             "fabrica": lambda: fig_mapa(self.g.mapa_pred, self.g.geoms)},
        ])
        self.selector.pack(fill="both", expand=True)

    def renderizar(self):
        self.selector.refrescar()
