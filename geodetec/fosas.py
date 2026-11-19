"""Modelo de fosas clandestinas con datos REALES (CNB 2018-2023 + homicidios 2019-2024).

Los datos viven cifrados en ``datos/fosas_edomex.enc`` con cifrado de sobre: cada folio
válido deriva una llave que desenvuelve la llave de datos.
"""
import base64
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import cripto
from .config import CARPETA_DATOS, DB_PATH, FOSAS_PATH, REPETICIONES_FOSAS, VARIABLES_FOSAS
from .datos import variables_reales
from .db import conectar

COLUMNAS_LOG = ("population_density", "historical_record_count", "homicidios_2019_2024")


def abrir_datos_fosas(folio, ruta=FOSAS_PATH):
    """Descifra el archivo con un folio. Devuelve ``(datos, f_datos)`` o ``PermissionError``."""
    Fernet, InvalidToken = cripto.fernet(), cripto.token_invalido()
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró {os.path.basename(ruta)}. Debe estar en la "
                                f"carpeta de datos del proyecto:\n{CARPETA_DATOS}")
    with open(ruta, encoding="utf-8") as f:
        sobre = json.load(f)
    folio = folio.strip().upper()
    for ll in sobre["llaves"]:
        try:
            llave_datos = cripto.derivar_clave(folio, base64.b64decode(ll["sal"])).decrypt(
                ll["llave_envuelta"].encode())
            break
        except InvalidToken:
            continue
    else:
        raise PermissionError("Folio no válido. Acceso denegado.")
    f_datos = Fernet(llave_datos)
    datos = json.loads(f_datos.decrypt(sobre["datos"].encode()).decode("utf-8"))
    return datos, f_datos


def preparar_fosas(mun, datos):
    """Une variables reales + homicidios + conteo de fosas; ``con_fosa`` es la etiqueta."""
    df = variables_reales(mun)
    hom = pd.DataFrame(datos["homicidios"]).astype({"cvegeo": str})
    fos = pd.DataFrame(datos["fosas"])
    fos["Total_fosas"] = pd.to_numeric(fos["Total_fosas"])
    conteo = fos.groupby("Cve_geo")["Total_fosas"].sum().rename("fosas_registradas")
    df = df.merge(hom, on="cvegeo", how="left").merge(conteo, left_on="cvegeo",
                                                      right_index=True, how="left")
    columnas = ["homicidios_2019_2024", "tasa_homicidios_100k", "fosas_registradas"]
    df[columnas] = df[columnas].fillna(0)
    df["con_fosa"] = (df["fosas_registradas"] > 0).astype(int)
    return df


def _random_forest():
    return RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                  class_weight="balanced_subsample", random_state=0, n_jobs=-1)


def _logistica():
    return make_pipeline(StandardScaler(),
                         LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000))


def entrenar_fosas(df):
    """Probabilidades fuera de muestra (CV 5 × ``REPETICIONES_FOSAS``) para RF y logística.

    Devuelve ``(resultados ordenados por prob_fosa, metricas)``.
    """
    X, y = df[VARIABLES_FOSAS], df["con_fosa"].to_numpy()
    X_log = X.copy()
    for c in COLUMNAS_LOG:
        X_log[c] = np.log1p(X_log[c])

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=REPETICIONES_FOSAS, random_state=42)
    p_rf, p_lr, n = np.zeros(len(df)), np.zeros(len(df)), np.zeros(len(df))
    for tr, te in cv.split(X, y):
        p_rf[te] += _random_forest().fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1]
        p_lr[te] += _logistica().fit(X_log.iloc[tr], y[tr]).predict_proba(X_log.iloc[te])[:, 1]
        n[te] += 1
    p_rf, p_lr = p_rf / n, p_lr / n
    final = _random_forest().fit(X, y)
    top = np.argsort(-p_rf)[:20]
    res = df.copy()
    res["prob_fosa"] = p_rf.round(4)
    metricas = {
        "n": len(df), "positivos": int(y.sum()), "tasa_base": float(y.mean()),
        "auc_rf": float(roc_auc_score(y, p_rf)), "ap_rf": float(average_precision_score(y, p_rf)),
        "auc_logistica": float(roc_auc_score(y, p_lr)),
        "ap_logistica": float(average_precision_score(y, p_lr)),
        "aciertos_top20": int(y[top].sum()),
        "importancias": dict(zip(VARIABLES_FOSAS, final.feature_importances_.round(4).tolist())),
    }
    return res.sort_values("prob_fosa", ascending=False).reset_index(drop=True), metricas


def guardar_resultados_fosas(res, metricas, f_datos, db=DB_PATH):
    """Guarda los resultados cifrados con la misma llave de datos."""
    paquete = {"resultados": res[["cvegeo", "municipio", "prob_fosa", "con_fosa",
                                  "fosas_registradas", "tasa_homicidios_100k"]].to_dict("records"),
               "metricas": metricas, "fecha": datetime.now().isoformat(timespec="seconds")}
    with conectar(db) as con:
        con.execute("CREATE TABLE IF NOT EXISTS fosas_resultados (fecha TEXT, datos_cifrados TEXT)")
        con.execute("DELETE FROM fosas_resultados")
        con.execute("INSERT INTO fosas_resultados VALUES (?, ?)",
                    (paquete["fecha"], f_datos.encrypt(json.dumps(paquete, ensure_ascii=False)
                                                       .encode()).decode()))


def texto_fosas(m):
    """Resumen legible de las métricas del modelo de fosas."""
    t = "MODELO DE FOSAS CLANDESTINAS – datos reales\n" + "=" * 46 + "\n\n"
    t += f"Municipios: {m['n']} · con fosa registrada (CNB): {m['positivos']} "
    t += f"({m['tasa_base']:.1%})\n"
    t += f"Validación: 5 particiones × {REPETICIONES_FOSAS} repeticiones (fuera de muestra)\n\n"
    t += "                      AUC-ROC   Precisión promedio\n"
    t += f"  Random Forest        {m['auc_rf']:.3f}     {m['ap_rf']:.3f}\n"
    t += f"  Regresión logística  {m['auc_logistica']:.3f}     {m['ap_logistica']:.3f}\n"
    t += f"  Azar (referencia)    0.500     {m['tasa_base']:.3f}\n\n"
    t += f"De los 20 municipios con mayor probabilidad, {m['aciertos_top20']} tienen fosa registrada\n"
    t += f"(al azar se esperarían {20 * m['tasa_base']:.1f}).\n\n"
    t += "Importancia de variables (Random Forest)\n"
    for k, v in sorted(m["importancias"].items(), key=lambda kv: -kv[1]):
        t += f"  {k:26s} {v:.3f}\n"
    t += ("\nLos municipios con alta probabilidad SIN fosa registrada son candidatos\n"
          "a revisión, no hallazgos. El registro oficial es incompleto.\n")
    return t
