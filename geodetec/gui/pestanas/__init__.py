"""Pestañas de la ventana principal, en el orden en que aparecen."""
from .busqueda import PestanaBusqueda
from .confidencial import PestanaConfidencial
from .datos import PestanaDatos
from .inicio import PestanaInicio
from .modelo import PestanaModelo
from .prioridad import PestanaPrioridad

# (texto de la pestaña, clase)
PESTANAS = [
    ("Inicio", PestanaInicio),
    ("Datos", PestanaDatos),
    ("Modelo", PestanaModelo),
    ("Mapa de prioridad", PestanaPrioridad),
    ("Zona de búsqueda", PestanaBusqueda),
    ("Confidencial", PestanaConfidencial),
]

__all__ = ["PESTANAS"]
