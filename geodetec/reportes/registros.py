"""Reporte PDF del análisis de registros (pestaña "Registros (CSV)").

Pensado para entregarse a familias, colectivos o personal que acompaña casos reales: cada gráfica
lleva una explicación en lenguaje claro ("Qué muestra") y una lectura de los datos
("Interpretación"), y el documento deja claro qué puede y qué no puede decir el análisis.
"""
import os

from ..figuras.registros import fig_conjunto, fig_registros, fig_zona_registro
from .plantilla import FONDO_AVISO, BORDE_AVISO, Reporte

CLASES = ["Baja", "Media", "Alta"]
MAX_TABLA_ZONA = 20

AVISO = ("Este reporte es una herramienta de apoyo para ordenar y priorizar la revisión de "
         "municipios a partir de la última ubicación conocida. No indica dónde se encuentra una "
         "persona ni sustituye la investigación ni las acciones de búsqueda que realizan las "
         "autoridades. Fue desarrollado como proyecto académico (UNAM) y sus resultados deben "
         "tomarse como una referencia adicional.")

COMO_USAR = [
    "Úsalo como apoyo para conversar con la autoridad que lleva el caso (por ejemplo, la "
    "Comisión de Búsqueda de Personas del Estado de México) y proponer qué municipios revisar "
    "primero.",
    "Si existen pistas concretas (testimonios, cámaras, rastreo de teléfono), esas pistas tienen "
    "prioridad sobre este análisis, aunque apunten a un municipio fuera de la zona.",
    "Mientras más precisa sea la última ubicación (coordenadas en lugar del municipio), más "
    "útil es la zona. Puedes corregir el archivo y generar el reporte de nuevo.",
    "El documento contiene datos personales: compártelo solo con personas e instituciones que "
    "participan en la búsqueda.",
]


# --------------------------------------------------------------------------- textos auxiliares
def tiempo_legible(dias):
    if dias < 31:
        return f"{dias} día{'s' if dias != 1 else ''}"
    meses = round(dias / 30.44)
    anios, meses = divmod(meses, 12)
    partes = []
    if anios:
        partes.append(f"{anios} año{'s' if anios > 1 else ''}")
    if meses:
        partes.append(f"{meses} mes{'es' if meses > 1 else ''}")
    return " y ".join(partes) or "menos de un mes"


def nivel_perfil(p):
    """Lectura en palabras de P(alta)."""
    if p >= 0.8:
        return "muy parecido al de los municipios de prioridad alta"
    if p >= 0.6:
        return "parecido al de los municipios de prioridad alta"
    if p >= 0.4:
        return "intermedio"
    if p >= 0.2:
        return "más cercano al de prioridad media o baja"
    return "propio de los municipios de prioridad baja"


def _lista(nombres):
    nombres = list(nombres)
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _plural(n, singular, plural=None):
    return singular if n == 1 else (plural or singular + "s")


# --------------------------------------------------------------------------- interpretaciones
def interpretar_mapa(an):
    regs, pares = an["registros"], an["pares"]
    s = an["resumen"]
    t = []
    con_comunes = [p for p in pares if p["compartidos"]]
    if con_comunes:
        for p in con_comunes[:4]:
            n = len(p["compartidos"])
            t.append(f"Las zonas de {p['a']} y {p['b']} se traslapan en {n} "
                     f"{_plural(n, 'municipio')} ({_lista(p['compartidos'][:4])}"
                     f"{'…' if n > 4 else ''}); sus últimas ubicaciones están a "
                     f"{p['distancia_km']:.0f} km. Revisar esos municipios atiende a ambos "
                     "registros a la vez.")
    elif len(regs) > 1:
        t.append("Ninguna zona se traslapa con otra: cada registro requiere revisar municipios "
                 "distintos.")
    aislados = [r["id"] for r in regs
                if not any(r["id"] in (p["a"], p["b"]) and p["compartidos"] for p in pares)]
    if aislados and con_comunes:
        t.append(f"{_lista(aislados)} no {'comparte' if len(aislados) == 1 else 'comparten'} "
                 "municipios con otros registros: su zona se revisa por separado.")
    t.append(f"En total, las zonas cubren {s['municipios_en_zonas']} de los 125 municipios del "
             "estado.")
    if con_comunes:
        t.append("Que dos zonas coincidan no significa que los casos estén relacionados; solo "
                 "indica que comparten municipios por revisar.")
    return t


def interpretar_conjunto(an):
    conj = an["conjunto"].sort_values("indice_total", ascending=False)
    top = conj.head(5)
    t = [f"Los municipios con mayor índice sumado son {_lista(top['municipio'])}."]
    multiples = conj[conj["n_registros"] > 1]
    if len(multiples):
        t.append(f"{len(multiples)} {_plural(len(multiples), 'municipio')} "
                 f"{'aparece' if len(multiples) == 1 else 'aparecen'} en la zona de dos o más "
                 f"registros; el primero es {multiples.iloc[0]['municipio']} "
                 f"({', '.join(multiples.iloc[0]['ids'])}).")
    else:
        t.append("Ningún municipio aparece en más de una zona, así que el orden refleja sobre "
                 "todo la cercanía a cada última ubicación.")
    t.append("Este orden sirve para repartir esfuerzos cuando se atienden varios registros a la "
             "vez; para un registro en particular, consulta su página de detalle.")
    return t


def interpretar_registro(r, an, sigma_km):
    zona = r["zona"]
    sel = zona[zona["en_zona"]]
    t = []
    ubic = ("según sus coordenadas" if r["metodo"] == "coordenadas"
            else "tomando el centro del municipio, porque el registro no trae coordenadas")
    t.append(f"La última ubicación conocida está en {r['municipio']} ({ubic}). Según el modelo, "
             f"este municipio tiene prioridad {CLASES[r['prioridad']]} (P(alta) = "
             f"{r['prob_alta']:.2f}): su perfil es {nivel_perfil(r['prob_alta'])}.")
    primeros = [f"{f.municipio} ({f.distancia_km:.0f} km)" for f in sel.head(3).itertuples()]
    t.append(f"La zona prioritaria abarca {len(sel)} municipios hasta {r['alcance_km']:.0f} km. "
             f"Los primeros en el orden son {_lista(primeros)}.")
    lejanos = sel[(sel["distancia_km"] > sigma_km) & (sel["prob_alta"] >= 0.6)]
    if len(lejanos):
        t.append(f"{_lista(lejanos['municipio'].head(3))} "
                 f"{'entra' if len(lejanos) == 1 else 'entran'} a la zona aunque "
                 f"{'está' if len(lejanos) == 1 else 'están'} a más de {sigma_km:.0f} km, "
                 "porque su perfil es de prioridad alta.")
    fuera = zona[(~zona["en_zona"]) & (zona["distancia_km"] <= sigma_km)].sort_values(
        "distancia_km")
    if len(fuera):
        nombres = [f"{f.municipio} (P(alta) {f.prob_alta:.2f})" for f in fuera.head(3).itertuples()]
        t.append(f"{_lista(nombres)} {'queda' if len(fuera) == 1 else 'quedan'} fuera de la zona "
                 f"a pesar de estar a menos de {sigma_km:.0f} km, porque el modelo "
                 f"{'le' if len(fuera) == 1 else 'les'} asigna una probabilidad de prioridad alta "
                 "menor. Si hay indicios concretos hacia esos municipios, conviene revisarlos de "
                 "todas formas.")
    otros = [p for p in an["pares"] if r["id"] in (p["a"], p["b"]) and p["compartidos"]]
    for p in otros:
        otro = p["b"] if p["a"] == r["id"] else p["a"]
        t.append(f"Comparte {len(p['compartidos'])} municipios de zona con {otro}.")
    if r["metodo"] != "coordenadas":
        t.append("Con coordenadas más precisas de la última ubicación, la zona sería más exacta.")
    return t


# --------------------------------------------------------------------------- reporte
def generar_reporte_registros(an, avisos, mapa_pred, geoms, metricas, ruta, archivo="",
                              es_ejemplo=False):
    """Crea el PDF del análisis de registros. Devuelve el número de páginas."""
    s = an["resumen"]
    par = s["parametros"]
    regs = an["registros"]
    errores = [a for a in avisos if a[1] == "error"]
    r = Reporte("Análisis de registros y zonas de búsqueda prioritaria",
                "Priorización de municipios a partir de la última ubicación conocida · "
                "Estado de México")

    datos = [("Fecha del reporte", f"{r.fecha:%d/%m/%Y %H:%M}"),
             ("Archivo analizado", os.path.basename(archivo) or "—"),
             ("Registros analizados", f"{s['n']}"
              + (f" ({len(errores)} renglones descartados por errores)" if errores else "")),
             ("Zona de búsqueda", f"{par['porcentaje']:.0%} de los municipios con mayor índice · "
                                  f"alcance σ = {par['sigma_km']:.0f} km · piso = {par['piso']:.2f}"),
             ("Modelo", f"Red neuronal · coincide con la regla de prioridad en "
                        f"{metricas['accuracy']:.0%} de los municipios reales")]
    r.portada(datos, aviso=AVISO,
              nota="Los registros de este archivo son ficticios (archivo de ejemplo)."
              if es_ejemplo else None)

    # 1. resumen
    r.seccion("1. Resumen")
    conj = an["conjunto"].sort_values("indice_total", ascending=False)
    puntos = [f"Se analizaron {s['n']} {_plural(s['n'], 'registro')} con desapariciones entre "
              f"{s['fecha_min']:%d/%m/%Y} y {s['fecha_max']:%d/%m/%Y} (tiempo transcurrido "
              f"típico: {tiempo_legible(int(s['dias_mediana']))}).",
              f"{s['alta']} de {s['n']} {_plural(s['n'], 'registro tiene', 'registros tienen')} su "
              "última ubicación en un municipio de prioridad Alta según el modelo.",
              f"Las zonas de búsqueda cubren {s['municipios_en_zonas']} municipios"
              + (f"; {s['compartidos']} aparecen en la zona de más de un registro."
                 if s["compartidos"] else "; ninguna zona se traslapa con otra."),
              f"Municipios a revisar primero considerando todos los registros: "
              f"{_lista(conj['municipio'].head(3))}."]
    if errores:
        puntos.append(f"{len(errores)} {_plural(len(errores), 'renglón', 'renglones')} del archivo "
                      "no se pudieron usar (ver sección 6).")
    r.vinetas(puntos)
    r.recuadro("Cómo usar este reporte", COMO_USAR)

    # 2. registros
    r.seccion("2. Registros analizados")
    r.parrafo("Datos tal como se leyeron del archivo, con el municipio de la última ubicación y "
              "la prioridad que el modelo asigna a ese municipio.")
    r.tabla(["#", "Id", "Nombre", "Fecha", "Días", "Municipio", "Ubicación", "Prioridad"],
            [[i + 1, x["id"], x["nombre"] or "—", f"{x['fecha']:%d/%m/%Y}",
              x["dias"], x["municipio"],
              "coordenadas" if x["metodo"] == "coordenadas" else "municipio",
              CLASES[x["prioridad"]]] for i, x in enumerate(regs)],
            anchos=[0.3, 0.75, 2.3, 0.95, 0.6, 1.9, 1.05, 0.95])

    # 3. mapa general
    r.grafica("Última ubicación y zona de búsqueda de cada registro",
              fig_registros(an, mapa_pred, geoms, panel=False),
              "Cada color corresponde a un registro (el número del círculo es su lugar en la "
              "tabla). El círculo marca la última ubicación conocida y el área sombreada del mismo "
              "color, su zona de búsqueda prioritaria. Los municipios con línea punteada negra "
              "están en la zona de dos o más registros. El fondo gris indica el perfil de "
              "prioridad de cada municipio según el modelo (más oscuro = más parecido a "
              "prioridad alta). Los cuadros blancos son CDMX y Toluca, como referencia.",
              interpretar_mapa(an), alto_max=4.6, seccion="3. Mapa general")

    # 4. conjunto
    r.grafica("Índice de búsqueda sumado de todos los registros", fig_conjunto(an),
              "Para cada municipio se suma el índice de búsqueda que obtiene respecto a cada "
              "registro. Arriba quedan los municipios que son prioritarios para varios registros "
              "a la vez o muy prioritarios para uno. El color indica en cuántas zonas aparece y, "
              "a la derecha de cada barra, a qué registros corresponde.",
              interpretar_conjunto(an), alto_max=4.6, seccion="4. Municipios a revisar primero")

    # 5. detalle
    r.seccion("5. Detalle por registro", reservar=99)    # empieza en página nueva
    for i, x in enumerate(regs):
        if i:
            r.salto_pagina()
        r.subseccion(f"5.{i + 1}  {x['id']}" + (f" · {x['nombre']}" if x["nombre"] else ""))
        info = [f"Desaparición: {x['fecha']:%d/%m/%Y} (hace {tiempo_legible(x['dias'])})",
                f"Última ubicación: {x['municipio']} · {x['lat']:.4f}, {x['lon']:.4f} "
                f"({'coordenadas del registro' if x['metodo'] == 'coordenadas' else 'centro del municipio'})"]
        extra = ", ".join(v for v in (x["sexo"], f"{x['edad']} años" if x["edad"] else "") if v)
        if extra:
            info.append(f"Datos: {extra}")
        if x["descripcion"]:
            info.append(f"Descripción: {x['descripcion']}")
        r.vinetas(info, tam=9)
        r.grafica("Zona de búsqueda", fig_zona_registro(x, i, geoms),
                  "Acercamiento a la zona prioritaria del registro. La estrella marca la última "
                  "ubicación conocida; el color de cada municipio es su índice de búsqueda (más "
                  "rojo = revisar antes) y el número indica el orden sugerido dentro de la zona "
                  "(el mismo de la tabla siguiente).",
                  interpretar_registro(x, an, par["sigma_km"]), alto_max=3.0)
        sel = x["zona"][x["zona"]["en_zona"]].head(MAX_TABLA_ZONA)
        r._reservar(0.5 + 0.2 * (len(sel) + 1))
        r.subseccion(f"Municipios de la zona de {x['id']} en orden sugerido de revisión")
        r.tabla(["Orden", "Municipio", "Distancia", "P(alta)", "Prioridad", "Índice"],
                [[k, f.municipio, f"{f.distancia_km:.0f} km", f"{f.prob_alta:.2f}",
                  CLASES[int(f.prediccion)], f"{f.indice_busqueda:.3f}"]
                 for k, f in enumerate(sel.itertuples(), 1)],
                anchos=[0.6, 2.6, 1, 0.8, 0.9, 0.8])

    # 6. calidad de datos
    r.seccion("6. Calidad de los datos del archivo")
    if avisos:
        r.parrafo("Renglones con problemas. Los marcados como «error» no se analizaron; los "
                  "«aviso» se corrigieron automáticamente y conviene confirmarlos.")
        r.tabla(["Renglón", "Tipo", "Detalle"],
                [[a[0], a[1], a[2]] for a in avisos], anchos=[0.7, 0.7, 6])
    else:
        r.parrafo("Todos los renglones del archivo se leyeron sin errores ni correcciones.")

    # 7. metodología
    r.seccion("7. Cómo se hizo el análisis y sus límites")
    r.subseccion("Índice de búsqueda")
    r.parrafo(f"Para cada municipio: índice = ({par['piso']:.2f} + {1 - par['piso']:.2f} · "
              f"P(alta)) · exp(−d² / 2·{par['sigma_km']:.0f}²), donde d es la distancia en línea "
              "recta (km) entre la última ubicación y el centro del municipio. La cercanía pesa "
              f"1 en el origen, 0.61 a {par['sigma_km']:.0f} km y 0.14 a "
              f"{2 * par['sigma_km']:.0f} km. La zona prioritaria es el {par['porcentaje']:.0%} "
              "de los municipios con mayor índice.")
    r.subseccion("Qué es P(alta)")
    r.parrafo("Es la probabilidad, según una red neuronal, de que el municipio tenga prioridad "
              "de búsqueda alta. La red aprendió una regla de prioridad que combina seis "
              f"características del municipio (variación del terreno, proporción de localidades rurales, "
              "densidad de población, accesibilidad a centros metropolitanos, registros "
              "históricos de personas desaparecidas y tasa anual de reportes). Se entrenó con 500 municipios "
              f"simulados y coincide con la regla en {metricas['accuracy']:.0%} de los 125 "
              "municipios reales. P(alta) describe el perfil del municipio, no la probabilidad de "
              "encontrar a una persona en él.")
    r.recuadro("Límites que hay que tener presentes", [
        "La regla de prioridad la definió el equipo del proyecto; no se validó contra hallazgos "
        "reales de personas.",
        "El análisis es por municipio: no señala lugares específicos dentro de un municipio.",
        "La distancia es en línea recta; no considera carreteras, rutas de transporte ni "
        "barreras geográficas.",
        "Los registros oficiales (RNPDNO) tienen subregistro, lo que afecta el perfil de "
        "algunos municipios.",
        "Que un municipio quede fuera de la zona no lo descarta: las pistas concretas del caso "
        "siempre deben tener prioridad.",
    ], fondo=FONDO_AVISO, borde=BORDE_AVISO)
    r.subseccion("Fuentes de datos")
    r.vinetas(["Límites municipales: Marco Geoestadístico INEGI 2020 (CONABIO).",
               "Población y localidades: INEGI, Censo de Población y Vivienda 2020.",
               "Personas desaparecidas: RNPDNO, Consulta Pública (corte 30/11/2025).",
               "Registros analizados: archivo CSV proporcionado por quien generó el reporte; no "
               "se guardaron en el sistema."], tam=9)
    r.subseccion("A dónde acudir")
    r.parrafo("Para reportar una desaparición o dar seguimiento a un caso en el Estado de México "
              "se puede acudir a la Comisión de Búsqueda de Personas del Estado de México, a la "
              "Fiscalía General de Justicia del Estado de México (área especializada en personas "
              "desaparecidas) o a la Comisión Nacional de Búsqueda. Los colectivos de familias "
              "también acompañan procesos de búsqueda.")
    return r.guardar(ruta)
