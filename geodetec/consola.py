"""Modo consola (sin interfaz gráfica): imprime métricas y guarda las figuras como PNG."""
import getpass
import os

from .busqueda import zona_busqueda_punto
from .config import CARPETA_SALIDAS, DB_PATH
from .figuras import (fig_busqueda, fig_distribuciones, fig_fosas, fig_importancia, fig_mapa,
                      fig_matriz_confusion, fig_personas, fig_variables_reales)
from .fosas import abrir_datos_fosas, entrenar_fosas, guardar_resultados_fosas, preparar_fosas, texto_fosas
from .modelo import texto_metricas
from .personas import abrir_registro_personas
from .sistema import Geodetec


def _pedir_oculto(mensaje):
    try:
        return getpass.getpass(mensaje)
    except Exception:
        return ""


def _figuras_personas(g, clave):
    personas = abrir_registro_personas(clave)
    p = personas[0]
    zp = zona_busqueda_punto(g.mapa_pred, g.mun, p["lon"], p["lat"])
    return {
        "personas_ubicaciones.png": fig_personas(personas, g.mapa_pred, g.mun, g.geoms),
        "zona_persona1.png": fig_busqueda(zp, g.geoms, p["lon"], p["lat"],
                                          f"{p['id']} ({p['municipio']})",
                                          color_zona=p["color"], color_punto=p["color"],
                                          cmap="Greys"),
    }


def _figuras_fosas(g, folio):
    datos, f_datos = abrir_datos_fosas(folio)
    res, m = entrenar_fosas(preparar_fosas(g.mun, datos))
    guardar_resultados_fosas(res, m, f_datos)
    print(texto_fosas(m))
    return {"fosas_probabilidad.png": fig_fosas(res, m, g.geoms)}


def modo_consola(carpeta=CARPETA_SALIDAS, origen="Valle de Bravo"):
    os.makedirs(carpeta, exist_ok=True)
    g = Geodetec()
    g.paso_generar()
    g.paso_entrenar()
    print(texto_metricas(g.metricas, g.train, g.test, g.umbrales))
    o = g.municipio_por_nombre(origen)
    zona = zona_busqueda_punto(g.mapa_pred, g.mun, o["lon"], o["lat"])
    figuras = {
        "variables_reales.png": fig_variables_reales(g.test, g.geoms),
        "matriz_confusion.png": fig_matriz_confusion(g.metricas),
        "importancia_variables.png": fig_importancia(g.modelo),
        "distribuciones.png": fig_distribuciones(g.train, g.test),
        "mapa_prioridad.png": fig_mapa(g.mapa_pred, g.geoms),
        "zona_busqueda.png": fig_busqueda(zona, g.geoms, o["lon"], o["lat"], o["municipio"]),
    }

    clave = _pedir_oculto("Contraseña del registro de personas (Enter para omitir): ")
    if clave:
        try:
            figuras.update(_figuras_personas(g, clave))
        except PermissionError as e:
            print(e)

    folio = _pedir_oculto("Folio para la sección de fosas (Enter para omitir): ")
    if folio:
        try:
            figuras.update(_figuras_fosas(g, folio))
        except PermissionError as e:
            print(e)

    for nombre, fig in figuras.items():
        fig.savefig(os.path.join(carpeta, nombre), dpi=130)
    print(f"Gráficas en {carpeta}\nBase de datos: {DB_PATH}")
    return g
