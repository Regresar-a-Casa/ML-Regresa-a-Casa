"""Persistencia en SQLite (``geodetec_edomex.db``)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

from .config import DB_PATH


@contextmanager
def conectar(db=DB_PATH):
    """Abre una conexión, hace commit al salir sin errores y siempre la cierra."""
    con = sqlite3.connect(db)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def guardar_tablas(tablas, db=DB_PATH):
    """Guarda (reemplazando) cada DataFrame de ``{nombre: df}`` como tabla."""
    with conectar(db) as con:
        for nombre, df in tablas.items():
            df.to_sql(nombre, con, if_exists="replace", index=False)


def cargar_tabla(tabla, db=DB_PATH):
    """Lee una tabla completa. ``tabla`` es siempre un nombre interno, nunca entrada del usuario."""
    with conectar(db) as con:
        return pd.read_sql(f"SELECT * FROM {tabla}", con)


def guardar_metricas(m, db=DB_PATH):
    """Agrega una fila al historial de métricas del modelo de prioridad."""
    fila = pd.DataFrame([{
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "accuracy": m["accuracy"], "precision_macro": m["precision"],
        "recall_macro": m["recall"], "f1_macro": m["f1"],
        "cv_media": m["cv_media"], "cv_desv": m["cv_desv"]}])
    with conectar(db) as con:
        fila.to_sql("historial_metricas", con, if_exists="append", index=False)
