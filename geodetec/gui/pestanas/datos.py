"""Pestaña de datos: variables reales y comparación simulado vs real."""
from ...figuras import fig_distribuciones, fig_variables_reales
from ..componentes import SelectorVistas
from .base import Pestana


class PestanaDatos(Pestana):
    titulo = "Datos"
    descripcion = ("El modelo usa 6 variables por municipio: relieve, vegetación (proporción de "
                   "localidades rurales), densidad de población, accesibilidad a un centro "
                   "metropolitano, registros históricos del RNPDNO y frecuencia de reportes. "
                   "Se entrena con 500 municipios simulados y se prueba con los 125 reales.")

    def construir(self):
        self.selector = SelectorVistas(self.contenido, self.app, [
            {"nombre": "Variables reales por municipio",
             "titulo": "Variables reales por municipio",
             "ayuda": "cada mapa es una variable; los colores claros (amarillo) indican valores "
                      "altos y los oscuros (morado), bajos. Densidad y registros están en escala "
                      "logarítmica para que se distingan los municipios pequeños.",
             "fabrica": lambda: fig_variables_reales(self.g.test, self.g.geoms)},
            {"nombre": "Simulados vs. reales",
             "titulo": "Distribuciones: simulados vs. reales",
             "ayuda": "azul = 500 municipios simulados (entrenamiento); naranja = 125 municipios "
                      "reales (prueba). Donde las barras no se traslapan, el modelo encuentra en "
                      "la prueba casos distintos a los que aprendió.",
             "fabrica": lambda: fig_distribuciones(self.g.train, self.g.test)},
        ])
        self.selector.pack(fill="both", expand=True)

    def renderizar(self):
        self.selector.refrescar()
