"""Figuras de matplotlib (objetos ``Figure``, sin pyplot) usadas por la GUI y el modo consola."""
from .base import (contorno, dibujar_mapa, info_mapa, marcador_leyenda, marcar_referencias,
                   registrar_info)
from .busqueda import fig_busqueda
from .confidencial import fig_fosas, fig_personas
from .registros import color_registro, fig_conjunto, fig_registros, fig_zona_registro
from .modelo import (fig_curva_aprendizaje, fig_distribuciones, fig_importancia, fig_mapa,
                     fig_matriz_confusion, fig_variables_reales)

__all__ = [
    "contorno", "dibujar_mapa", "info_mapa", "marcador_leyenda", "marcar_referencias",
    "registrar_info",
    "fig_busqueda", "fig_fosas", "fig_personas",
    "color_registro", "fig_conjunto", "fig_registros", "fig_zona_registro",
    "fig_curva_aprendizaje", "fig_distribuciones", "fig_importancia", "fig_mapa",
    "fig_matriz_confusion", "fig_variables_reales",
]
