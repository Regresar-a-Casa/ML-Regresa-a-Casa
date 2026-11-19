"""Registro confidencial de personas desaparecidas (100 % FICTICIAS), cifrado dentro de SQLite.

Tablas:
    seguridad              (sal BLOB, verificador TEXT)  -> valida la contraseña
    personas_desaparecidas (id_persona, color, datos_cifrados)
"""
import json
import os

import numpy as np
import pandas as pd

from . import cripto
from .config import (COLORES_PERSONAS, DB_PATH, MIN_LONGITUD_CONTRASENA, N_PERSONAS,
                     SEMILLA_PERSONAS, VERIFICADOR, contrasena_inicial)
from .db import conectar


def simular_personas(mun, geoms, semilla=SEMILLA_PERSONAS):
    """Genera ``N_PERSONAS`` fichas ficticias con un punto aleatorio dentro de su municipio."""
    from matplotlib.path import Path
    rng = np.random.default_rng(semilla)
    nombres = {"Mujer": ["María Fernanda", "Guadalupe", "Ana Karen", "Daniela", "Rosa Isela"],
               "Hombre": ["José Luis", "Juan Carlos", "Miguel Ángel", "Ricardo", "Fernando"]}
    apellidos = ["Hernández", "García", "Martínez", "López", "González", "Pérez",
                 "Rodríguez", "Sánchez", "Ramírez", "Cruz", "Flores", "Gómez"]
    complexion = ["delgada", "media", "robusta"]
    senas = ["lunar en la mejilla izquierda", "cicatriz en el antebrazo derecho",
             "tatuaje de una golondrina en la muñeca", "usa lentes", "sin señas particulares"]
    ropa = ["sudadera gris y pantalón de mezclilla", "chamarra negra y tenis blancos",
            "playera roja y pants azul marino", "suéter verde y falda negra",
            "camisa a cuadros y botas cafés"]
    municipios = rng.choice(len(mun), size=N_PERSONAS, replace=False)
    pila = {k: list(rng.permutation(v)) for k, v in nombres.items()}
    personas = []
    for i, idx in enumerate(municipios):
        m = mun.iloc[idx]
        sexo = "Mujer" if i % 2 == 0 else "Hombre"
        anillo = max(geoms[m["cvegeo"]], key=len)
        ruta = Path(anillo)
        (xmin, ymin), (xmax, ymax) = anillo.min(0), anillo.max(0)
        while True:
            x, y = rng.uniform(xmin, xmax), rng.uniform(ymin, ymax)
            if ruta.contains_point((x, y)):
                break
        fecha = pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 640)))
        personas.append({
            "id": f"Persona {i + 1}",
            "folio": f"GD-{fecha.year}-{i + 1:03d}",
            "color": COLORES_PERSONAS[i],
            "nombre": f"{pila[sexo].pop()} {rng.choice(apellidos)} {rng.choice(apellidos)} (ficticio)",
            "edad": int(rng.integers(18, 66)),
            "sexo": sexo,
            "estatura_cm": int(rng.integers(150, 186)),
            "complexion": str(rng.choice(complexion)),
            "senas_particulares": str(rng.choice(senas)),
            "vestimenta": str(ropa[i]),
            "fecha_desaparicion": fecha.strftime("%Y-%m-%d"),
            "cvegeo": m["cvegeo"],
            "municipio": m["municipio"],
            "lon": round(float(x), 5),
            "lat": round(float(y), 5),
        })
    return personas


def _cifrar_persona(f, p):
    return f.encrypt(json.dumps(p, ensure_ascii=False).encode("utf-8")).decode()


def _escribir_registro(con, f, sal, personas):
    """Reescribe ``seguridad`` y ``personas_desaparecidas`` con la llave ``f``."""
    con.execute("DELETE FROM seguridad")
    con.execute("INSERT INTO seguridad VALUES (?, ?)", (sal, f.encrypt(VERIFICADOR).decode()))
    con.execute("DELETE FROM personas_desaparecidas")
    for p in personas:
        con.execute("INSERT INTO personas_desaparecidas VALUES (?, ?, ?)",
                    (p["id"], p["color"], _cifrar_persona(f, p)))


def crear_registro_personas(mun, geoms, contrasena=None, db=DB_PATH, forzar=False):
    """Crea el registro cifrado si no existe (o si ``forzar``). Devuelve True si lo creó.

    Si no se pasa ``contrasena`` se usa ``GEODETEC_CONTRASENA_INICIAL`` del archivo ``.env``.
    """
    with conectar(db) as con:
        existe = con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                             "AND name='personas_desaparecidas'").fetchone()
        if existe and not forzar:
            return False
        if contrasena is None:
            contrasena = contrasena_inicial()
        sal = os.urandom(16)
        f = cripto.derivar_clave(contrasena, sal)
        con.execute("DROP TABLE IF EXISTS seguridad")
        con.execute("DROP TABLE IF EXISTS personas_desaparecidas")
        con.execute("CREATE TABLE seguridad (sal BLOB, verificador TEXT)")
        con.execute("CREATE TABLE personas_desaparecidas "
                    "(id_persona TEXT, color TEXT, datos_cifrados TEXT)")
        _escribir_registro(con, f, sal, simular_personas(mun, geoms))
    return True


def _fernet_validado(con, contrasena):
    """Devuelve la llave Fernet si la contraseña es correcta; si no, ``PermissionError``."""
    InvalidToken = cripto.token_invalido()
    fila = con.execute("SELECT sal, verificador FROM seguridad").fetchone()
    if fila is None:
        raise RuntimeError("No existe el registro de personas. Cierra y vuelve a abrir el programa.")
    f = cripto.derivar_clave(contrasena, fila[0])
    try:
        f.decrypt(fila[1].encode())
    except InvalidToken:
        raise PermissionError("Contraseña incorrecta. Acceso denegado.")
    return f


def abrir_registro_personas(contrasena, db=DB_PATH):
    """Descifra y devuelve la lista de fichas (ordenadas por id)."""
    with conectar(db) as con:
        f = _fernet_validado(con, contrasena)
        filas = con.execute("SELECT datos_cifrados FROM personas_desaparecidas "
                            "ORDER BY id_persona").fetchall()
    return [json.loads(f.decrypt(r[0].encode()).decode("utf-8")) for r in filas]


def cambiar_contrasena(actual, nueva, db=DB_PATH):
    """Vuelve a cifrar todo el registro con una contraseña nueva (sal nueva)."""
    if len(nueva) < MIN_LONGITUD_CONTRASENA:
        raise ValueError(f"La contraseña nueva debe tener al menos "
                         f"{MIN_LONGITUD_CONTRASENA} caracteres.")
    personas = abrir_registro_personas(actual, db)
    sal = os.urandom(16)
    f = cripto.derivar_clave(nueva, sal)
    with conectar(db) as con:
        _escribir_registro(con, f, sal, personas)
