"""Análisis de registros cargados desde un archivo CSV (última ubicación conocida).

El CSV se lee, se valida renglón por renglón y se analiza **solo en memoria**: nada se guarda en
la base de datos. Los registros de ejemplo (``datos/registros_ejemplo.csv``) son ficticios.

Formato (los encabezados no distinguen mayúsculas ni acentos y admiten sinónimos):

==================== =========== ===================================================
Columna              Obligatoria Notas
==================== =========== ===================================================
id                   sí          identificador del registro (único)
fecha_desaparicion   sí          AAAA-MM-DD o DD/MM/AAAA; no puede ser futura
municipio            *           nombre del municipio (se toleran acentos y erratas)
lat, lon             *           coordenadas decimales (WGS84)
nombre, edad, sexo   no          informativos
descripcion          no          informativo
==================== =========== ===================================================

``*`` se necesita ``municipio`` o el par ``lat``/``lon`` (si vienen ambos, mandan las
coordenadas y se avisa si caen en otro municipio).
"""
import csv
import difflib
import io
import os
import unicodedata
from datetime import date

import numpy as np
import pandas as pd

from .busqueda import distancia_km, localizador, zona_busqueda_punto
from .config import CARPETA_DATOS, PISO_MODELO, PORCENTAJE_ZONA, SIGMA_KM

EJEMPLO_PATH = os.path.join(CARPETA_DATOS, "registros_ejemplo.csv")
MAX_REGISTROS = 30
MAX_BYTES = 2_000_000

# nombre interno -> sinónimos aceptados en el encabezado (ya normalizados)
SINONIMOS = {
    "id": ["id", "folio", "clave", "registro", "id_registro"],
    "fecha_desaparicion": ["fecha_desaparicion", "fecha", "fecha_de_desaparicion",
                           "desaparicion", "fecha_hechos"],
    "municipio": ["municipio", "ultima_ubicacion", "ubicacion", "municipio_ultima_ubicacion"],
    "lat": ["lat", "latitud", "latitude"],
    "lon": ["lon", "lng", "long", "longitud", "longitude"],
    "nombre": ["nombre", "nombre_completo"],
    "edad": ["edad", "anios", "edad_anios"],
    "sexo": ["sexo", "genero"],
    "descripcion": ["descripcion", "observaciones", "notas", "comentarios", "senas"],
}
OBLIGATORIAS = ("id", "fecha_desaparicion")


class ErrorRegistros(ValueError):
    """El archivo no se puede usar (falta una columna, está vacío, no es un CSV...)."""


def normalizar(texto):
    """minúsculas, sin acentos, espacios/guiones como ``_``."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return "_".join(t.lower().replace("-", " ").replace(".", " ").split())


# ---------------------------------------------------------------------------- lectura
def _decodificar(datos):
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ErrorRegistros("No se pudo leer el texto del archivo (codificación desconocida).")


def _separador(texto):
    muestra = "\n".join(texto.splitlines()[:10])
    try:
        return csv.Sniffer().sniff(muestra, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def leer_csv(origen):
    """Lee el CSV (ruta o texto) y devuelve un DataFrame con columnas internas, todo como texto.

    Acepta UTF-8 (con o sin BOM) y Windows-1252, separador ``,`` ``;`` tabulador o ``|``.
    """
    if isinstance(origen, str) and "\n" not in origen:
        if os.path.getsize(origen) > MAX_BYTES:
            raise ErrorRegistros("El archivo es demasiado grande para este análisis.")
        with open(origen, "rb") as f:
            texto = _decodificar(f.read())
    else:
        texto = origen
    if not texto.strip():
        raise ErrorRegistros("El archivo está vacío.")
    try:
        df = pd.read_csv(io.StringIO(texto), sep=_separador(texto), dtype=str,
                         keep_default_na=False, skipinitialspace=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as e:
        raise ErrorRegistros(f"El archivo no tiene formato CSV válido ({e}).") from None

    mapa = {}
    for col in df.columns:
        n = normalizar(col)
        for interno, sinonimos in SINONIMOS.items():
            if n in sinonimos and interno not in mapa.values():
                mapa[col] = interno
                break
    df = df.rename(columns=mapa)[list(dict.fromkeys(mapa.values()))]
    faltan = [c for c in OBLIGATORIAS if c not in df.columns]
    if faltan:
        raise ErrorRegistros("Faltan columnas obligatorias: " + ", ".join(faltan) +
                             ". Revisa el formato en la pestaña.")
    if "municipio" not in df.columns and not {"lat", "lon"} <= set(df.columns):
        raise ErrorRegistros("Se necesita la columna 'municipio' o las columnas 'lat' y 'lon'.")
    df = df.apply(lambda s: s.str.strip())
    df = df[(df != "").any(axis=1)].reset_index(drop=True)      # renglones vacíos
    if df.empty:
        raise ErrorRegistros("El archivo no tiene registros.")
    return df


# ---------------------------------------------------------------------------- validación
def _fecha(valor):
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return pd.to_datetime(valor, format=formato).date()
        except (ValueError, TypeError):
            continue
    return None


def _numero(valor):
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


class _Municipios:
    """Búsqueda tolerante de municipios por nombre."""

    def __init__(self, mun):
        self.por_clave = {normalizar(n): (c, n) for c, n in zip(mun["cvegeo"], mun["municipio"])}
        self.centroides = mun.set_index("cvegeo")[["lon", "lat", "municipio"]]

    def buscar(self, nombre):
        """``(cvegeo, nombre_oficial, aproximado)`` o ``None``."""
        n = normalizar(nombre)
        if n in self.por_clave:
            return (*self.por_clave[n], False)
        # nombre corto: "Ecatepec" -> "Ecatepec de Morelos"
        prefijos = [k for k in self.por_clave if k.startswith(n + "_")]
        if len(prefijos) == 1:
            return (*self.por_clave[prefijos[0]], True)
        parecido = difflib.get_close_matches(n, self.por_clave, n=1, cutoff=0.82)
        if parecido:
            return (*self.por_clave[parecido[0]], True)
        return None


def validar_registros(df, mun, geoms, hoy=None):
    """Valida cada renglón. Devuelve ``(registros, avisos)``.

    ``registros`` es una lista de diccionarios con ubicación resuelta; ``avisos`` una lista de
    ``(renglón, nivel, mensaje)`` con nivel ``"error"`` (renglón descartado) o ``"aviso"``.
    El número de renglón es el del archivo (el encabezado es el renglón 1).
    """
    hoy = hoy or date.today()
    munis, loc = _Municipios(mun), localizador(geoms)
    registros, avisos, vistos = [], [], set()
    for i, fila in df.iterrows():
        r = i + 2
        error = lambda m: avisos.append((r, "error", m))     # noqa: E731
        aviso = lambda m: avisos.append((r, "aviso", m))     # noqa: E731
        ident = fila.get("id", "")
        if not ident:
            error("sin id")
            continue
        if ident in vistos:
            error(f"id repetido '{ident}'")
            continue
        fecha = _fecha(fila.get("fecha_desaparicion", ""))
        if fecha is None:
            error(f"{ident}: fecha no reconocida '{fila.get('fecha_desaparicion', '')}' "
                  "(usa AAAA-MM-DD o DD/MM/AAAA)")
            continue
        if fecha > hoy:
            error(f"{ident}: la fecha {fecha.isoformat()} es futura")
            continue

        # ubicación
        lat, lon = _numero(fila.get("lat", "")), _numero(fila.get("lon", ""))
        nombre_mun = fila.get("municipio", "")
        encontrado = munis.buscar(nombre_mun) if nombre_mun else None
        if nombre_mun and encontrado is None:
            aviso(f"{ident}: no se reconoce el municipio '{nombre_mun}'")
        if lat is not None and lon is not None:
            if lon > 0 and lat < 0 or (abs(lat) > 90 and abs(lon) <= 90):
                lat, lon = lon, lat
                aviso(f"{ident}: latitud y longitud parecían invertidas; se intercambiaron")
            cve = loc.buscar(lon, lat)
            if cve is None:
                error(f"{ident}: las coordenadas ({lat}, {lon}) están fuera del Estado de México")
                continue
            metodo = "coordenadas"
            if encontrado and encontrado[0] != cve:
                aviso(f"{ident}: las coordenadas caen en "
                      f"{munis.centroides.loc[cve, 'municipio']}, no en {encontrado[1]}; "
                      "se usaron las coordenadas")
        elif encontrado:
            cve = encontrado[0]
            c = munis.centroides.loc[cve]
            lon, lat = float(c["lon"]), float(c["lat"])
            metodo = "centroide del municipio"
            if encontrado[2]:
                aviso(f"{ident}: '{nombre_mun}' se interpretó como {encontrado[1]}")
        else:
            error(f"{ident}: sin ubicación válida (falta municipio reconocible o lat/lon)")
            continue

        edad = _numero(fila.get("edad", "")) if fila.get("edad", "") else None
        if edad is not None and not 0 <= edad <= 110:
            aviso(f"{ident}: edad fuera de rango ({fila['edad']}); se ignora")
            edad = None
        vistos.add(ident)
        registros.append({
            "id": ident, "nombre": fila.get("nombre", ""), "sexo": fila.get("sexo", ""),
            "edad": None if edad is None else int(edad), "descripcion": fila.get("descripcion", ""),
            "fecha": fecha, "dias": (hoy - fecha).days, "lon": float(lon), "lat": float(lat),
            "cvegeo": cve, "municipio": munis.centroides.loc[cve, "municipio"], "metodo": metodo,
        })
        if len(registros) == MAX_REGISTROS and i + 1 < len(df):
            avisos.append((r, "aviso", f"solo se analizan los primeros {MAX_REGISTROS} "
                                       "registros válidos"))
            break
    return registros, avisos


# ---------------------------------------------------------------------------- análisis
def analizar_registros(registros, mapa_pred, mun, sigma_km=SIGMA_KM, piso=PISO_MODELO,
                       porcentaje=PORCENTAJE_ZONA):
    """Zona de búsqueda de cada registro y análisis conjunto.

    Devuelve un diccionario con:
      - ``registros``: los registros con ``prioridad``, ``prob_alta``, ``zona`` (DataFrame),
        ``n_zona`` y ``alcance_km`` (distancia al municipio más lejano de su zona);
      - ``conjunto``: DataFrame por municipio con ``n_registros`` (en cuántas zonas aparece),
        ``ids`` e ``indice_total`` (suma del índice de búsqueda de todos los registros);
      - ``pares``: registros cercanos entre sí (distancia y municipios compartidos);
      - ``resumen``: conteos y estadísticas generales.
    """
    if not registros:
        raise ErrorRegistros("No hay registros válidos para analizar.")
    pred = mapa_pred.set_index("cvegeo")
    salida = []
    acumulado = pd.DataFrame({"cvegeo": mun["cvegeo"], "municipio": mun["municipio"]}).set_index(
        "cvegeo")
    acumulado["n_registros"], acumulado["indice_total"] = 0, 0.0
    acumulado["ids"] = [[] for _ in range(len(acumulado))]
    for reg in registros:
        zona = zona_busqueda_punto(mapa_pred, mun, reg["lon"], reg["lat"], sigma_km, piso,
                                   porcentaje)
        sel = zona[zona["en_zona"]]
        r = dict(reg, zona=zona, n_zona=len(sel), alcance_km=float(sel["distancia_km"].max()),
                 prioridad=int(pred.loc[reg["cvegeo"], "prediccion"]),
                 prob_alta=float(pred.loc[reg["cvegeo"], "prob_alta"]))
        salida.append(r)
        idx = zona.set_index("cvegeo")
        acumulado["indice_total"] += idx["indice_busqueda"].reindex(acumulado.index).fillna(0)
        for c in sel["cvegeo"]:
            acumulado.at[c, "n_registros"] += 1
            acumulado.at[c, "ids"].append(reg["id"])
    acumulado["prob_alta"] = pred["prob_alta"].reindex(acumulado.index)
    conjunto = acumulado[acumulado["n_registros"] > 0].sort_values(
        ["n_registros", "indice_total"], ascending=False).reset_index()

    pares = []
    for a in range(len(salida)):
        for b in range(a + 1, len(salida)):
            ra, rb = salida[a], salida[b]
            d = distancia_km(ra["lon"], ra["lat"], rb["lon"], rb["lat"])
            za = set(ra["zona"].loc[ra["zona"]["en_zona"], "cvegeo"])
            zb = set(rb["zona"].loc[rb["zona"]["en_zona"], "cvegeo"])
            comunes = za & zb
            if comunes or d <= 2 * sigma_km:
                pares.append({"a": ra["id"], "b": rb["id"], "distancia_km": float(d),
                              "dias_entre": abs((ra["fecha"] - rb["fecha"]).days),
                              "compartidos": sorted(acumulado.loc[list(comunes), "municipio"])})
    pares.sort(key=lambda p: (-len(p["compartidos"]), p["distancia_km"]))

    edades = [r["edad"] for r in salida if r["edad"] is not None]
    resumen = {
        "n": len(salida),
        "alta": sum(r["prioridad"] == 2 for r in salida),
        "por_metodo": pd.Series([r["metodo"] for r in salida]).value_counts().to_dict(),
        "sexo": pd.Series([r["sexo"] or "sin dato" for r in salida]).value_counts().to_dict(),
        "edad_media": float(np.mean(edades)) if edades else None,
        "fecha_min": min(r["fecha"] for r in salida), "fecha_max": max(r["fecha"] for r in salida),
        "dias_mediana": float(np.median([r["dias"] for r in salida])),
        "municipios_en_zonas": len(conjunto),
        "compartidos": int((conjunto["n_registros"] > 1).sum()),
        "parametros": {"sigma_km": sigma_km, "piso": piso, "porcentaje": porcentaje},
    }
    return {"registros": salida, "conjunto": conjunto, "pares": pares, "resumen": resumen}


CLASES_TEXTO = ["Baja", "Media", "Alta"]


def texto_analisis(an, avisos=()):
    """Reporte legible del análisis."""
    s = an["resumen"]
    t = "ANÁLISIS DE REGISTROS (CSV)\n" + "=" * 46 + "\n"
    t += "Ejercicio académico · se analiza solo en memoria, no se guarda\n\n"
    t += f"Registros válidos: {s['n']}"
    errores = sum(1 for a in avisos if a[1] == "error")
    if errores:
        t += f"  ·  descartados: {errores}"
    t += "\n"
    t += "Ubicación: " + ", ".join(f"{v} por {k}" for k, v in s["por_metodo"].items()) + "\n"
    t += f"Desapariciones: {s['fecha_min']} a {s['fecha_max']} "
    t += f"(mediana {s['dias_mediana']:.0f} días)\n"
    if s["edad_media"] is not None:
        t += f"Edad promedio: {s['edad_media']:.0f} años\n"
    t += f"Municipio de última ubicación con prioridad Alta: {s['alta']} de {s['n']}\n\n"

    t += "Por registro\n"
    for r in an["registros"]:
        t += (f"  {r['id']}: {r['municipio']} · prioridad {CLASES_TEXTO[r['prioridad']]} "
              f"(P(alta) {r['prob_alta']:.2f}) · hace {r['dias']} días\n"
              f"      zona: {r['n_zona']} municipios hasta {r['alcance_km']:.0f} km\n")
    t += f"\nMunicipios dentro de alguna zona: {s['municipios_en_zonas']}\n"
    if s["compartidos"]:
        t += f"En la zona de 2 o más registros: {s['compartidos']}\n"
        for f in an["conjunto"][an["conjunto"]["n_registros"] > 1].head(10).itertuples():
            t += f"  · {f.municipio} ({', '.join(f.ids)})\n"
    if an["pares"]:
        t += "\nRegistros cercanos entre sí\n"
        for p in an["pares"]:
            t += (f"  {p['a']} – {p['b']}: {p['distancia_km']:.0f} km, "
                  f"{p['dias_entre']} días entre fechas, "
                  f"{len(p['compartidos'])} municipios en común\n")
    if avisos:
        t += "\nAvisos de lectura\n"
        for renglon, nivel, msg in avisos:
            t += f"  renglón {renglon} [{nivel}]: {msg}\n"
    t += ("\nLas zonas usan el mismo índice que la pestaña Zona de búsqueda. Coincidir en una "
          "zona\nno implica relación entre casos: es un criterio para ordenar la revisión.\n")
    return t

