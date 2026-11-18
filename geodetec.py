import json
import os
import sqlite3
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score


CARPETA = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(CARPETA, "edomex_municipios.geojson")
DB_PATH = os.path.join(CARPETA, "geodetec_edomex.db")

N_TRAIN = 500
SEMILLA_TRAIN = 2024
RUIDO_ETIQUETA = 0.025

VARIABLES = [
    "terrain_index",
    "vegetation_index",
    "population_density",
    "accessibility_index",
    "historical_record_count",
    "report_frequency",
]

CLASES = ["Baja", "Media", "Alta"]
COLORES_CLASES = ["#2ecc71", "#f1c40f", "#e74c3c"]


CENTROS = {"CDMX (Zócalo)": (-99.1332, 19.4326), "Toluca (centro)": (-99.6557, 19.2925)}


SIGMA_KM = 30.0
PISO_MODELO = 0.25
PORCENTAJE_ZONA = 0.10


N_PERSONAS = 5
SEMILLA_PERSONAS = 2026


CONTRASENA_INICIAL = "Geodetec2026"
COLORES_PERSONAS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4"]


FOSAS_PATH = os.path.join(CARPETA, "fosas_edomex.enc")
VARIABLES_FOSAS = VARIABLES + ["tasa_homicidios_100k", "homicidios_2019_2024"]
REPETICIONES_FOSAS = 5


def cargar_municipios(ruta=GEOJSON_PATH):
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró {os.path.basename(ruta)}. Debe estar en la misma "
            f"carpeta que este programa:\n{CARPETA}")
    with open(ruta, encoding="utf-8") as f:
        gj = json.load(f)
    filas, geoms = [], {}
    for feat in gj["features"]:
        p = feat["properties"]
        filas.append(p)
        g = feat["geometry"]
        poligonos = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        geoms[p["cvegeo"]] = [np.array(poly[0]) for poly in poligonos]
    mun = pd.DataFrame(filas)
    if "registros_rnpdno" not in mun.columns:
        raise ValueError("El archivo edomex_municipios.geojson es de una versión anterior: "
                         "usa el que acompaña a esta versión del programa.")
    mun["population_density"] = (mun["poblacion_2020"] / mun["area_km2"]).round(2)
    return mun.sort_values("cvegeo").reset_index(drop=True), geoms


def variables_reales(mun):
    df = mun[["cvegeo", "municipio", "zona_metropolitana"]].copy()
    df["terrain_index"] = np.clip(mun["altitud_desv_m"] / 500, 0, 1).round(4)
    df["vegetation_index"] = mun["prop_localidades_rurales"].round(4)
    df["population_density"] = mun["population_density"]
    df["accessibility_index"] = (1 - np.clip(mun["dist_centro_km"] / 110, 0, 1)).round(4)
    df["historical_record_count"] = mun["registros_rnpdno"].astype(int)
    df["report_frequency"] = mun["tasa_anual_100k_2020_2025"].round(2)
    return df


def puntaje_prioridad(df):
    urb = np.clip((np.log10(df["population_density"]) - 1) / 3.3, 0, 1)
    hist = np.clip(np.log1p(df["historical_record_count"]) / np.log1p(1000), 0, 1)
    rep = np.clip(df["report_frequency"] / 15, 0, 1)
    veg = df["vegetation_index"]
    acc = 1 - np.abs(df["accessibility_index"] - 0.5) * 2
    ter = df["terrain_index"]
    return (0.30 * hist + 0.20 * rep + 0.20 * veg + 0.15 * (1 - urb)
            + 0.10 * acc + 0.05 * ter)


def etiquetar(puntaje, umbrales):
    return np.digitize(puntaje, umbrales)


def simular_entrenamiento(n=N_TRAIN, semilla=SEMILLA_TRAIN):
    rng = np.random.default_rng(semilla)
    urb = rng.beta(1.3, 2.0, n)
    densidad = 10 ** (1.3 + urb * 3.0 + rng.normal(0, 0.12, n))
    area = np.exp(rng.normal(4.67, 1.1, n))
    poblacion = densidad * area
    vegetacion = np.clip(0.97 - 0.55 * urb ** 2 + rng.normal(0, 0.07, n), 0, 1)
    desv_alt = rng.gamma(1.5, 85, n) * (1.25 - 0.8 * urb)
    distancia = np.clip(rng.normal(62 - 45 * urb, 14, n), 1, 110)
    tasa = np.exp(rng.normal(np.log(4.8), 0.5, n)) * (0.8 + 0.5 * urb)
    anios_acumulados = np.exp(rng.normal(np.log(8.8), 0.3, n))
    historicos = rng.poisson(tasa * poblacion / 1e5 * anios_acumulados)

    df = pd.DataFrame({
        "cvegeo": [f"SIM-{i:04d}" for i in range(n)],
        "municipio": [f"Municipio sintético {i}" for i in range(n)],
        "zona_metropolitana": "Simulado",
        "terrain_index": np.clip(desv_alt / 500, 0, 1).round(4),
        "vegetation_index": vegetacion.round(4),
        "population_density": densidad.round(2),
        "accessibility_index": (1 - distancia / 110).round(4),
        "historical_record_count": historicos,
        "report_frequency": tasa.round(2),
    })
    puntaje = puntaje_prioridad(df) + rng.normal(0, RUIDO_ETIQUETA, n)
    umbrales = np.quantile(puntaje, [1 / 3, 2 / 3])
    df["puntaje"] = puntaje.round(4)
    df["prioridad"] = etiquetar(puntaje, umbrales)
    return df, umbrales


def preparar_prueba_real(mun, umbrales):
    df = variables_reales(mun)
    df["puntaje"] = puntaje_prioridad(df).round(4)
    df["prioridad"] = etiquetar(df["puntaje"], umbrales)
    return df


from contextlib import contextmanager


@contextmanager
def conectar(db=DB_PATH):
    con = sqlite3.connect(db)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def guardar_tablas(tablas, db=DB_PATH):
    with conectar(db) as con:
        for nombre, df in tablas.items():
            df.to_sql(nombre, con, if_exists="replace", index=False)


def cargar_tabla(tabla, db=DB_PATH):
    with conectar(db) as con:
        return pd.read_sql(f"SELECT * FROM {tabla}", con)


def guardar_metricas(m, db=DB_PATH):
    fila = pd.DataFrame([{
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "accuracy": m["accuracy"], "precision_macro": m["precision"],
        "recall_macro": m["recall"], "f1_macro": m["f1"],
        "cv_media": m["cv_media"], "cv_desv": m["cv_desv"]}])
    with conectar(db) as con:
        fila.to_sql("historial_metricas", con, if_exists="append", index=False)


def entrenar_modelo(train):
    X, y = train[VARIABLES], train["prioridad"]
    modelo = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                    class_weight="balanced", random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(modelo, X, y, cv=cv, scoring="accuracy")
    modelo.fit(X, y)
    return modelo, cv_scores


def evaluar_modelo(modelo, test, cv_scores):
    X, y = test[VARIABLES], test["prioridad"]
    y_pred = modelo.predict(X)
    et = [0, 1, 2]
    return {
        "accuracy": accuracy_score(y, y_pred),
        "precision": precision_score(y, y_pred, labels=et, average="macro", zero_division=0),
        "recall": recall_score(y, y_pred, labels=et, average="macro", zero_division=0),
        "f1": f1_score(y, y_pred, labels=et, average="macro", zero_division=0),
        "matriz": confusion_matrix(y, y_pred, labels=et),
        "reporte": classification_report(y, y_pred, labels=et, target_names=CLASES, zero_division=0),
        "cv_media": float(np.mean(cv_scores)), "cv_desv": float(np.std(cv_scores)),
        "y_pred": y_pred,
    }


def texto_metricas(m, train, test, umbrales):
    d_tr = train["prioridad"].value_counts().reindex([0, 1, 2], fill_value=0)
    d_te = test["prioridad"].value_counts().reindex([0, 1, 2], fill_value=0)
    t = "GEODETEC – Estado de México – Resultados\n" + "=" * 46 + "\n\n"
    t += f"Entrenamiento: {len(train)} municipios SIMULADOS\n"
    t += f"Prueba:        {len(test)} municipios REALES del Estado de México\n\n"
    t += f"Umbrales de la regla (terciles del entrenamiento): {umbrales[0]:.3f} / {umbrales[1]:.3f}\n\n"
    t += "Distribución de clases (Baja / Media / Alta)\n"
    t += f"  Entrenamiento (simulado): {d_tr[0]} / {d_tr[1]} / {d_tr[2]}\n"
    t += f"  Prueba (real):            {d_te[0]} / {d_te[1]} / {d_te[2]}\n\n"
    t += f"Validación cruzada (solo simulados): {m['cv_media']:.3f} ± {m['cv_desv']:.3f}\n\n"
    t += "Métricas en los datos REALES (promedio macro)\n"
    t += f"  Accuracy : {m['accuracy']:.3f}\n  Precision: {m['precision']:.3f}\n"
    t += f"  Recall   : {m['recall']:.3f}\n  F1-score : {m['f1']:.3f}\n\n"
    t += "Reporte por clase\n" + m["reporte"] + "\n"
    t += ("La diferencia entre la validación cruzada y la prueba real mide\n"
          "cuánto se pierde al pasar de datos simulados a datos reales.\n")
    return t


def predecir_mapa(modelo, datos):
    proba = modelo.predict_proba(datos[VARIABLES])
    prob = np.zeros((len(datos), 3))
    for j, c in enumerate(modelo.classes_):
        prob[:, int(c)] = proba[:, j]
    out = datos.copy()
    out["prediccion"] = prob.argmax(axis=1)
    out["prob_baja"], out["prob_media"], out["prob_alta"] = prob[:, 0], prob[:, 1], prob[:, 2]
    return out


def distancia_km(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def zona_busqueda(mapa_pred, mun, cve_origen):
    o = mun[mun["cvegeo"] == cve_origen].iloc[0]
    return zona_busqueda_punto(mapa_pred, mun, o["lon"], o["lat"])


def zona_busqueda_punto(mapa_pred, mun, lon0, lat0):
    df = mapa_pred.merge(mun[["cvegeo", "lon", "lat"]], on="cvegeo")
    df["distancia_km"] = distancia_km(lon0, lat0, df["lon"], df["lat"])
    cercania = np.exp(-df["distancia_km"] ** 2 / (2 * SIGMA_KM ** 2))


    df["indice_busqueda"] = (PISO_MODELO + (1 - PISO_MODELO) * df["prob_alta"]) * cercania
    n = int(np.ceil(PORCENTAJE_ZONA * len(df)))
    df = df.sort_values("indice_busqueda", ascending=False).reset_index(drop=True)
    df["en_zona"] = df.index < n
    return df


def _cripto():
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        raise ImportError("Falta la librería 'cryptography'. Instálala con:\n"
                          "python -m pip install cryptography")
    return Fernet, InvalidToken, hashes, PBKDF2HMAC


def derivar_clave(contrasena, sal):
    import base64
    Fernet, _, hashes, PBKDF2HMAC = _cripto()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=390_000)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(contrasena.encode("utf-8"))))


def simular_personas(mun, geoms, semilla=SEMILLA_PERSONAS):
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


def crear_registro_personas(mun, geoms, contrasena=CONTRASENA_INICIAL, db=DB_PATH, forzar=False):
    with conectar(db) as con:
        existe = con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                             "AND name='personas_desaparecidas'").fetchone()
        if existe and not forzar:
            return False
        sal = os.urandom(16)
        f = derivar_clave(contrasena, sal)
        con.execute("DROP TABLE IF EXISTS seguridad")
        con.execute("DROP TABLE IF EXISTS personas_desaparecidas")
        con.execute("CREATE TABLE seguridad (sal BLOB, verificador TEXT)")
        con.execute("INSERT INTO seguridad VALUES (?, ?)",
                    (sal, f.encrypt(b"GEODETEC-OK").decode()))
        con.execute("CREATE TABLE personas_desaparecidas "
                    "(id_persona TEXT, color TEXT, datos_cifrados TEXT)")
        for p in simular_personas(mun, geoms):
            cifrado = f.encrypt(json.dumps(p, ensure_ascii=False).encode("utf-8")).decode()
            con.execute("INSERT INTO personas_desaparecidas VALUES (?, ?, ?)",
                        (p["id"], p["color"], cifrado))
    return True


def _fernet_validado(con, contrasena):
    _, InvalidToken, _, _ = _cripto()
    fila = con.execute("SELECT sal, verificador FROM seguridad").fetchone()
    if fila is None:
        raise RuntimeError("No existe el registro de personas. Cierra y vuelve a abrir el programa.")
    f = derivar_clave(contrasena, fila[0])
    try:
        f.decrypt(fila[1].encode())
    except InvalidToken:
        raise PermissionError("Contraseña incorrecta. Acceso denegado.")
    return f


def abrir_registro_personas(contrasena, db=DB_PATH):
    with conectar(db) as con:
        f = _fernet_validado(con, contrasena)
        filas = con.execute("SELECT datos_cifrados FROM personas_desaparecidas "
                            "ORDER BY id_persona").fetchall()
    return [json.loads(f.decrypt(r[0].encode()).decode("utf-8")) for r in filas]


def cambiar_contrasena(actual, nueva, db=DB_PATH):
    if len(nueva) < 8:
        raise ValueError("La contraseña nueva debe tener al menos 8 caracteres.")
    personas = abrir_registro_personas(actual, db)
    sal = os.urandom(16)
    f = derivar_clave(nueva, sal)
    with conectar(db) as con:
        con.execute("DELETE FROM seguridad")
        con.execute("INSERT INTO seguridad VALUES (?, ?)", (sal, f.encrypt(b"GEODETEC-OK").decode()))
        con.execute("DELETE FROM personas_desaparecidas")
        for p in personas:
            con.execute("INSERT INTO personas_desaparecidas VALUES (?, ?, ?)",
                        (p["id"], p["color"],
                         f.encrypt(json.dumps(p, ensure_ascii=False).encode("utf-8")).decode()))


def abrir_datos_fosas(folio, ruta=FOSAS_PATH):
    import base64
    Fernet, InvalidToken, _, _ = _cripto()
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró {os.path.basename(ruta)}. Debe estar en la "
                                f"misma carpeta que el programa:\n{CARPETA}")
    with open(ruta, encoding="utf-8") as f:
        sobre = json.load(f)
    folio = folio.strip().upper()
    for ll in sobre["llaves"]:
        try:
            llave_datos = derivar_clave(folio, base64.b64decode(ll["sal"])).decrypt(
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
    df = variables_reales(mun)
    hom = pd.DataFrame(datos["homicidios"]).astype({"cvegeo": str})
    fos = pd.DataFrame(datos["fosas"])
    fos["Total_fosas"] = pd.to_numeric(fos["Total_fosas"])
    conteo = fos.groupby("Cve_geo")["Total_fosas"].sum().rename("fosas_registradas")
    df = df.merge(hom, on="cvegeo", how="left").merge(conteo, left_on="cvegeo",
                                                      right_index=True, how="left")
    df[["homicidios_2019_2024", "tasa_homicidios_100k", "fosas_registradas"]] = df[
        ["homicidios_2019_2024", "tasa_homicidios_100k", "fosas_registradas"]].fillna(0)
    df["con_fosa"] = (df["fosas_registradas"] > 0).astype(int)
    return df


def entrenar_fosas(df):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, roc_auc_score
    from sklearn.model_selection import RepeatedStratifiedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X, y = df[VARIABLES_FOSAS], df["con_fosa"].to_numpy()
    X_log = X.copy()
    for c in ("population_density", "historical_record_count", "homicidios_2019_2024"):
        X_log[c] = np.log1p(X_log[c])

    def rf():
        return RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                      class_weight="balanced_subsample", random_state=0, n_jobs=-1)

    def logistica():
        return make_pipeline(StandardScaler(),
                             LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000))

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=REPETICIONES_FOSAS, random_state=42)
    p_rf, p_lr, n = np.zeros(len(df)), np.zeros(len(df)), np.zeros(len(df))
    for tr, te in cv.split(X, y):
        p_rf[te] += rf().fit(X.iloc[tr], y[tr]).predict_proba(X.iloc[te])[:, 1]
        p_lr[te] += logistica().fit(X_log.iloc[tr], y[tr]).predict_proba(X_log.iloc[te])[:, 1]
        n[te] += 1
    p_rf, p_lr = p_rf / n, p_lr / n
    final = rf().fit(X, y)
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


def dibujar_mapa(ax, geoms, cves, valores, cmap, norm, borde="#555555", ancho=0.3):
    polys, vals = [], []
    for cve, v in zip(cves, valores):
        for anillo in geoms[cve]:
            polys.append(anillo)
            vals.append(v)
    pc = PolyCollection(polys, array=np.array(vals, dtype=float), cmap=cmap, norm=norm,
                        edgecolor=borde, linewidth=ancho)
    ax.add_collection(pc)
    todos = np.vstack([a for c in geoms for a in geoms[c]])
    ax.set_xlim(todos[:, 0].min() - 0.03, todos[:, 0].max() + 0.03)
    ax.set_ylim(todos[:, 1].min() - 0.03, todos[:, 1].max() + 0.03)
    ax.set_aspect(1 / np.cos(np.radians(19.4)))
    ax.set_xticks([]); ax.set_yticks([])
    return pc


def contorno(ax, geoms, cves, color="blue", ancho=2.0):
    polys = [a for c in cves for a in geoms[c]]
    ax.add_collection(PolyCollection(polys, facecolor="none", edgecolor=color, linewidth=ancho))


TITULOS_VARIABLES = {
    "terrain_index": "Terreno (variación de altitud)",
    "vegetation_index": "Vegetación (prop. localidades rurales)",
    "population_density": "Densidad log10(hab/km²)",
    "accessibility_index": "Accesibilidad a centro metropolitano",
    "historical_record_count": "Registros RNPDNO log10(1+n)",
    "report_frequency": "Registros por 100 mil hab/año 2020-25",
}


def _transformar(var, serie):
    if var == "population_density":
        return np.log10(serie)
    if var == "historical_record_count":
        return np.log10(1 + serie)
    return serie


def fig_variables_reales(test, geoms):
    fig = Figure(figsize=(14, 8.5))
    for k, var in enumerate(VARIABLES, 1):
        ax = fig.add_subplot(2, 3, k)
        pc = dibujar_mapa(ax, geoms, test["cvegeo"], _transformar(var, test[var]),
                          "viridis", Normalize(), ancho=0.2)
        fig.colorbar(pc, ax=ax, fraction=0.04)
        ax.set_title(TITULOS_VARIABLES[var], fontsize=10)
    fig.suptitle("Datos REALES del conjunto de prueba – 125 municipios del Estado de México\n"
                 "Fuentes: INEGI (Censo 2020, catálogo de localidades) y RNPDNO (corte 30/11/2025)")
    fig.tight_layout()
    return fig


def fig_matriz_confusion(m):
    fig = Figure(figsize=(5.5, 4.5))
    ax = fig.add_subplot(111)
    M = m["matriz"]
    im = ax.imshow(M, cmap="Blues")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, M[i, j], ha="center", va="center", fontsize=13,
                    color="white" if M[i, j] > M.max() / 2 else "black")
    ax.set_xticks(range(3), CLASES); ax.set_yticks(range(3), CLASES)
    ax.set_xlabel("Predicción del modelo"); ax.set_ylabel("Etiqueta según la regla (datos reales)")
    ax.set_title(f"Matriz de confusión – {M.sum()} municipios reales")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    return fig


def fig_importancia(modelo):
    imp = pd.Series(modelo.feature_importances_, index=VARIABLES).sort_values()
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    ax.barh(imp.index, imp.values, color="#3498db")
    for i, v in enumerate(imp.values):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlim(0, imp.max() * 1.2)
    ax.set_xlabel("Importancia (reducción media de impureza)")
    ax.set_title("Importancia de variables – Random Forest (entrenado con simulados)")
    fig.tight_layout()
    return fig


def fig_distribuciones(train, test):
    fig = Figure(figsize=(11, 6.5))
    for k, var in enumerate(VARIABLES, 1):
        ax = fig.add_subplot(2, 3, k)
        a, b = _transformar(var, train[var]), _transformar(var, test[var])
        bins = np.histogram_bin_edges(np.concatenate([a, b]), bins=18)
        ax.hist(a, bins=bins, alpha=0.55, density=True, label="Entrenamiento (simulado)", color="#3498db")
        ax.hist(b, bins=bins, alpha=0.55, density=True, label="Prueba (real)", color="#e67e22")
        ax.set_title(TITULOS_VARIABLES[var], fontsize=9)
        ax.tick_params(labelsize=7)
    fig.axes[0].legend(fontsize=7)
    fig.suptitle("Distribuciones: datos simulados de entrenamiento vs datos reales de prueba")
    fig.tight_layout()
    return fig


def fig_mapa(mapa_pred, geoms):
    cmap = ListedColormap(COLORES_CLASES)
    fig = Figure(figsize=(15, 5.6))
    cves = mapa_pred["cvegeo"]
    ax1 = fig.add_subplot(131)
    dibujar_mapa(ax1, geoms, cves, mapa_pred["prioridad"], cmap, Normalize(0, 2))
    ax1.set_title("Prioridad según la regla (datos reales)")
    ax2 = fig.add_subplot(132)
    dibujar_mapa(ax2, geoms, cves, mapa_pred["prediccion"], cmap, Normalize(0, 2))
    ax2.set_title("Prioridad predicha por el modelo")
    ax3 = fig.add_subplot(133)
    pc = dibujar_mapa(ax3, geoms, cves, mapa_pred["prob_alta"], "inferno", Normalize(0, 1))
    fig.colorbar(pc, ax=ax3, fraction=0.04)
    ax3.set_title("Mapa de calor: P(prioridad alta)")
    fig.legend(handles=[mpatches.Patch(color=c, label=l) for c, l in zip(COLORES_CLASES, CLASES)],
               loc="lower center", ncol=3)
    acierto = (mapa_pred["prioridad"] == mapa_pred["prediccion"]).mean()
    fig.suptitle(f"Estado de México – modelo entrenado con simulados aplicado a datos reales – coincidencia {acierto:.1%}")
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    return fig


def fig_busqueda(zona, geoms, lon0, lat0, origen, color_zona="blue", color_punto="cyan",
                 cmap="YlOrRd"):
    fig = Figure(figsize=(12, 6.2))
    ax = fig.add_axes([0.01, 0.08, 0.56, 0.84])
    pc = dibujar_mapa(ax, geoms, zona["cvegeo"], zona["indice_busqueda"], cmap, Normalize())
    contorno(ax, geoms, zona.loc[zona["en_zona"], "cvegeo"], color=color_zona, ancho=2.5)
    ax.plot(lon0, lat0, marker="*", color=color_punto, markersize=22,
            markeredgecolor="black", linestyle="none")
    fig.colorbar(pc, ax=ax, fraction=0.035, label="Índice de prioridad de búsqueda")
    ax.set_title(f"Zona de búsqueda prioritaria – origen: {origen}")
    ax.legend(handles=[plt_linea(color_punto, "*", "Última ubicación conocida (ficticia)"),
                       mpatches.Patch(facecolor="none", edgecolor=color_zona, linewidth=2,
                                      label="Zona prioritaria (10%)")],
              loc="lower left", fontsize=8)

    axt = fig.add_axes([0.71, 0.08, 0.28, 0.84])
    axt.axis("off")
    sel = zona[zona["en_zona"]]
    texto = "Municipios en la zona prioritaria\n(orden de prioridad)\n\n"
    for i, r in enumerate(sel.itertuples(), 1):
        texto += f"{i:2d}. {r.municipio[:26]:26s} {r.distancia_km:5.0f} km\n"
    texto += ("\nÍndice = (0.25 + 0.75·P(alta)) · cercanía\n"
              "cercanía = exp(-d² / 2·30²)\n\nP(alta): modelo aplicado a datos reales\n"
              "Ejercicio académico")
    axt.text(0, 1, texto, va="top", family="monospace", fontsize=8.5)
    return fig


def plt_linea(color, marker, label):
    from matplotlib.lines import Line2D
    return Line2D([], [], color=color, marker=marker, markersize=12, markeredgecolor="black",
                  linestyle="none", label=label)


def fig_fosas(res, metricas, geoms):
    fig = Figure(figsize=(13, 6.8))
    ax = fig.add_axes([0.01, 0.06, 0.55, 0.86])
    pc = dibujar_mapa(ax, geoms, res["cvegeo"], res["prob_fosa"], "magma_r",
                      Normalize(0, max(0.5, res["prob_fosa"].max())), ancho=0.25)
    contorno(ax, geoms, res.loc[res["con_fosa"] == 1, "cvegeo"], color="#00bcd4", ancho=2.2)
    fig.colorbar(pc, ax=ax, fraction=0.035, label="Probabilidad estimada de fosa (fuera de muestra)")
    ax.set_title("Fosas clandestinas – probabilidad por municipio (datos reales)")
    ax.legend(handles=[mpatches.Patch(facecolor="none", edgecolor="#00bcd4", linewidth=2,
                                      label="Fosa registrada (CNB, 2018-2023)")],
              loc="lower left", fontsize=8)
    axt = fig.add_axes([0.62, 0.06, 0.37, 0.86])
    axt.axis("off")
    t = "ACCESO AUTORIZADO – sección confidencial\n\n"
    t += "Municipios con mayor probabilidad\n"
    t += f"{'#':>2}  {'Municipio':24s} {'Prob.':>5}  Fosa reg.\n"
    for i, r in enumerate(res.head(20).itertuples(), 1):
        t += f"{i:2d}. {r.municipio[:24]:24s} {r.prob_fosa:5.2f}  {'sí' if r.con_fosa else '—'}\n"
    t += (f"\nAUC Random Forest: {metricas['auc_rf']:.2f} · logística: {metricas['auc_logistica']:.2f}\n"
          f"Fosas registradas en el top 20: {metricas['aciertos_top20']} de {metricas['positivos']}\n"
          "'—' = sin fosa registrada: candidato a revisión,\nno un hallazgo.")
    axt.text(0, 1, t, va="top", family="monospace", fontsize=8.3)
    return fig


def fig_personas(personas, mapa_pred, mun, geoms):
    fig = Figure(figsize=(13, 6.6))
    ax = fig.add_axes([0.01, 0.06, 0.55, 0.86])
    pc = dibujar_mapa(ax, geoms, mapa_pred["cvegeo"], mapa_pred["prob_alta"], "Greys",
                      Normalize(0, 1.6), borde="#9a9a9a", ancho=0.3)
    for p in personas:
        zona = zona_busqueda_punto(mapa_pred, mun, p["lon"], p["lat"])
        cves = zona.loc[zona["en_zona"], "cvegeo"]
        polys = [a for c in cves for a in geoms[c]]
        ax.add_collection(PolyCollection(polys, facecolor=p["color"], alpha=0.22, edgecolor="none"))
        contorno(ax, geoms, cves, color=p["color"], ancho=2.2)
    for p in personas:
        ax.plot(p["lon"], p["lat"], marker="o", color=p["color"], markersize=15,
                markeredgecolor="black", markeredgewidth=1.5, linestyle="none")
        ax.text(p["lon"], p["lat"], p["id"][-1], ha="center", va="center",
                color="white", fontsize=8, fontweight="bold")
    ax.set_title("Última ubicación conocida y zona de búsqueda por persona")

    axt = fig.add_axes([0.59, 0.06, 0.40, 0.86])
    axt.axis("off")
    axt.text(0, 1.0, "REGISTRO CONFIDENCIAL – acceso autorizado\nDatos 100% ficticios",
             va="top", fontsize=10, fontweight="bold", color="#8b0000")
    y = 0.88
    for p in personas:
        axt.add_patch(mpatches.Rectangle((0, y - 0.115), 0.025, 0.125, color=p["color"],
                                         transform=axt.transAxes))
        txt = (f"{p['id']}  ·  Folio {p['folio']}\n"
               f"{p['nombre']}, {p['edad']} años, {p['sexo']}\n"
               f"Desaparición: {p['fecha_desaparicion']}\n"
               f"Última ubicación: {p['municipio']}\n"
               f"({p['lat']:.4f}, {p['lon']:.4f})")
        axt.text(0.04, y, txt, va="top", fontsize=8.3, family="monospace")
        y -= 0.175
    return fig


class Geodetec:
    def __init__(self):
        self.mun, self.geoms = cargar_municipios()
        self.train = self.test = self.umbrales = None
        self.modelo = self.cv_scores = self.metricas = self.mapa_pred = None

    def paso_generar(self):
        train, umbrales = simular_entrenamiento()
        test = preparar_prueba_real(self.mun, umbrales)
        guardar_tablas({
            "municipios": self.mun,
            "entrenamiento_simulado": train,
            "prueba_real": test,
            "umbrales": pd.DataFrame({"umbral_media": [umbrales[0]], "umbral_alta": [umbrales[1]]}),
        })

        crear_registro_personas(self.mun, self.geoms)

        self.train = cargar_tabla("entrenamiento_simulado")
        self.test = cargar_tabla("prueba_real")
        u = cargar_tabla("umbrales").iloc[0]
        self.umbrales = (float(u["umbral_media"]), float(u["umbral_alta"]))

    def paso_entrenar(self):
        self.modelo, self.cv_scores = entrenar_modelo(self.train)
        self.metricas = evaluar_modelo(self.modelo, self.test, self.cv_scores)
        guardar_metricas(self.metricas)
        self.mapa_pred = predecir_mapa(self.modelo, self.test)
        guardar_tablas({"predicciones_reales": self.mapa_pred[
            ["cvegeo", "municipio", "prioridad", "prediccion", "prob_baja", "prob_media", "prob_alta"]]})

    def cve_por_nombre(self, nombre):
        fila = self.mun[self.mun["municipio"] == nombre]
        if fila.empty:
            raise ValueError(f"No existe el municipio '{nombre}'")
        return fila["cvegeo"].iloc[0]


def modo_consola(carpeta=os.path.join(CARPETA, "salidas_edomex"), origen="Valle de Bravo"):
    os.makedirs(carpeta, exist_ok=True)
    g = Geodetec()
    g.paso_generar()
    g.paso_entrenar()
    print(texto_metricas(g.metricas, g.train, g.test, g.umbrales))
    o = g.mun[g.mun["cvegeo"] == g.cve_por_nombre(origen)].iloc[0]
    zona = zona_busqueda_punto(g.mapa_pred, g.mun, o["lon"], o["lat"])
    figuras = {
        "variables_reales.png": fig_variables_reales(g.test, g.geoms),
        "matriz_confusion.png": fig_matriz_confusion(g.metricas),
        "importancia_variables.png": fig_importancia(g.modelo),
        "distribuciones.png": fig_distribuciones(g.train, g.test),
        "mapa_prioridad.png": fig_mapa(g.mapa_pred, g.geoms),
        "zona_busqueda.png": fig_busqueda(zona, g.geoms, o["lon"], o["lat"], o["municipio"]),
    }

    import getpass
    try:
        clave = getpass.getpass("Contraseña del registro de personas (Enter para omitir): ")
    except Exception:
        clave = ""
    if clave:
        try:
            personas = abrir_registro_personas(clave)
            figuras["personas_ubicaciones.png"] = fig_personas(personas, g.mapa_pred, g.mun, g.geoms)
            p = personas[0]
            zp = zona_busqueda_punto(g.mapa_pred, g.mun, p["lon"], p["lat"])
            figuras["zona_persona1.png"] = fig_busqueda(zp, g.geoms, p["lon"], p["lat"],
                                                        f"{p['id']} ({p['municipio']})",
                                                        color_zona=p["color"], color_punto=p["color"],
                                                        cmap="Greys")
        except PermissionError as e:
            print(e)
    try:
        folio = getpass.getpass("Folio para la sección de fosas (Enter para omitir): ")
    except Exception:
        folio = ""
    if folio:
        try:
            datos, f_datos = abrir_datos_fosas(folio)
            res, m = entrenar_fosas(preparar_fosas(g.mun, datos))
            guardar_resultados_fosas(res, m, f_datos)
            print(texto_fosas(m))
            figuras["fosas_probabilidad.png"] = fig_fosas(res, m, g.geoms)
        except PermissionError as e:
            print(e)
    for nombre, fig in figuras.items():
        fig.savefig(os.path.join(carpeta, nombre), dpi=130)
    print(f"Gráficas en {carpeta}\nBase de datos: {DB_PATH}")
    return g


def modo_gui():
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

    try:
        g = Geodetec()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("GEODETEC", str(e))
        return

    def ventana_figura(titulo, fig):
        v = tk.Toplevel(root)
        v.title(titulo)
        canvas = FigureCanvasTkAgg(fig, master=v)
        canvas.draw()
        NavigationToolbar2Tk(canvas, v)
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def requiere(attr):
        if getattr(g, attr) is None:
            messagebox.showwarning("GEODETEC", "Primero completa los pasos anteriores.")
            return False
        return True

    def seguro(func):
        def envoltura():
            try:
                func()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        return envoltura

    def preparar_sistema():
        try:
            g.paso_generar()
            estado.config(text="Entrenando el modelo con los municipios simulados...")
            root.update_idletasks()
            g.paso_entrenar()
            estado.config(text=f"Sistema listo · {len(g.train)} municipios simulados para entrenar · "
                               f"{len(g.test)} municipios reales evaluados · accuracy en datos reales: "
                               f"{g.metricas['accuracy']:.1%}")
            for b in lista_botones:
                b.config(state="normal")
        except Exception as e:
            estado.config(text="No se pudo preparar el sistema.", fg="#c0392b")
            messagebox.showerror("Error al iniciar", str(e))
        finally:
            root.config(cursor="")

    @seguro
    def metricas():
        if requiere("metricas"):
            v = tk.Toplevel(root)
            v.title("Métricas")
            v.geometry("600x540")
            t = scrolledtext.ScrolledText(v, wrap=tk.WORD, font=("Courier", 10))
            t.pack(expand=True, fill="both", padx=10, pady=10)
            t.insert(tk.END, texto_metricas(g.metricas, g.train, g.test, g.umbrales))
            t.config(state=tk.DISABLED)

    @seguro
    def division():
        if requiere("train"):
            ventana_figura("Variables reales por municipio", fig_variables_reales(g.test, g.geoms))

    @seguro
    def matriz():
        if requiere("metricas"):
            ventana_figura("Matriz de confusión", fig_matriz_confusion(g.metricas))

    @seguro
    def importancia():
        if requiere("modelo"):
            ventana_figura("Importancia de variables", fig_importancia(g.modelo))

    @seguro
    def distribuciones():
        if requiere("train"):
            ventana_figura("Distribuciones", fig_distribuciones(g.train, g.test))

    @seguro
    def mapa():
        if requiere("mapa_pred"):
            ventana_figura("Mapa de prioridad – Estado de México", fig_mapa(g.mapa_pred, g.geoms))

    @seguro
    def busqueda():
        if not requiere("mapa_pred"):
            return
        v = tk.Toplevel(root)
        v.title("Zona de búsqueda")
        tk.Label(v, text="Municipio de la última ubicación conocida:",
                 font=("Helvetica", 11)).pack(padx=15, pady=(15, 5))
        nombres = sorted(g.mun["municipio"].tolist())
        combo = ttk.Combobox(v, values=nombres, width=40, state="readonly")
        combo.set("Toluca")
        combo.pack(padx=15, pady=5)

        @seguro
        def calcular():
            o = g.mun[g.mun["cvegeo"] == g.cve_por_nombre(combo.get())].iloc[0]
            zona = zona_busqueda_punto(g.mapa_pred, g.mun, o["lon"], o["lat"])
            v.destroy()
            ventana_figura("Zona de búsqueda prioritaria",
                           fig_busqueda(zona, g.geoms, o["lon"], o["lat"], o["municipio"]))

        tk.Button(v, text="Calcular zona", command=calcular, bg="#c0392b", fg="white",
                  font=("Helvetica", 11)).pack(pady=12)


    def pedir_contrasena(titulo, texto):
        resultado = {"valor": None}
        d = tk.Toplevel(root)
        d.title(titulo)
        d.resizable(False, False)
        d.grab_set()
        tk.Label(d, text=texto, font=("Helvetica", 11)).pack(padx=20, pady=(15, 5))
        e = tk.Entry(d, show="*", width=30, font=("Helvetica", 11))
        e.pack(padx=20, pady=5)
        e.focus_set()

        def aceptar(_=None):
            resultado["valor"] = e.get()
            d.destroy()

        e.bind("<Return>", aceptar)
        tk.Button(d, text="Aceptar", command=aceptar, width=12).pack(pady=12)
        root.wait_window(d)
        return resultado["valor"]

    @seguro
    def personas():
        if not requiere("train"):
            return
        clave = pedir_contrasena("Acceso restringido",
                                 "Registro confidencial de personas.\nIngresa la contraseña:")
        if not clave:
            return
        try:
            lista = abrir_registro_personas(clave)
        except PermissionError as e:
            messagebox.showerror("Acceso denegado", str(e))
            return

        v = tk.Toplevel(root)
        v.title("Personas desaparecidas – registro confidencial (datos ficticios)")
        v.geometry("980x420")
        tk.Label(v, text="ACCESO AUTORIZADO – información confidencial (personas ficticias)",
                 fg="#8b0000", font=("Helvetica", 11, "bold")).pack(pady=(10, 4))
        cols = ("folio", "nombre", "edad", "sexo", "fecha", "municipio")
        tabla = ttk.Treeview(v, columns=cols, show="headings", height=6)
        for c, w in zip(cols, (110, 330, 50, 70, 100, 230)):
            tabla.heading(c, text=c.capitalize())
            tabla.column(c, width=w, anchor="w")
        for p in lista:
            tabla.insert("", "end", iid=p["id"], tags=(p["id"],),
                         values=(p["folio"], p["nombre"], p["edad"], p["sexo"],
                                 p["fecha_desaparicion"], p["municipio"]))
            tabla.tag_configure(p["id"], background=p["color"], foreground="white")
        tabla.pack(fill="x", padx=10, pady=5)
        tabla.selection_set(lista[0]["id"])

        def seleccionada():
            sel = tabla.selection()
            return next(p for p in lista if p["id"] == (sel[0] if sel else lista[0]["id"]))

        @seguro
        def ver_ficha():
            p = seleccionada()
            messagebox.showinfo(p["id"], (
                f"Folio: {p['folio']}\nNombre: {p['nombre']}\nEdad: {p['edad']} años\n"
                f"Sexo: {p['sexo']}\nEstatura: {p['estatura_cm']} cm\n"
                f"Complexión: {p['complexion']}\nSeñas particulares: {p['senas_particulares']}\n"
                f"Vestimenta: {p['vestimenta']}\nFecha de desaparición: {p['fecha_desaparicion']}\n"
                f"Última ubicación: {p['municipio']} ({p['lat']}, {p['lon']})\n"
                f"Color asignado: {p['color']}"), parent=v)

        @seguro
        def mapa_personas():
            if requiere("mapa_pred"):
                ventana_figura("Últimas ubicaciones por persona",
                               fig_personas(lista, g.mapa_pred, g.mun, g.geoms))

        @seguro
        def zona_persona():
            if requiere("mapa_pred"):
                p = seleccionada()
                zona = zona_busqueda_punto(g.mapa_pred, g.mun, p["lon"], p["lat"])
                ventana_figura(f"Zona de búsqueda – {p['id']}",
                               fig_busqueda(zona, g.geoms, p["lon"], p["lat"],
                                            f"{p['id']} ({p['municipio']})",
                                            color_zona=p["color"], color_punto=p["color"],
                                            cmap="Greys"))

        @seguro
        def nueva_clave():
            n1 = pedir_contrasena("Cambiar contraseña", "Contraseña nueva (mín. 8 caracteres):")
            if not n1:
                return
            n2 = pedir_contrasena("Cambiar contraseña", "Confirma la contraseña nueva:")
            if n1 != n2:
                messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=v)
                return
            cambiar_contrasena(clave, n1)
            messagebox.showinfo("Listo", "Contraseña actualizada. El registro se volvió a cifrar.",
                                parent=v)
            v.destroy()

        barra = tk.Frame(v)
        barra.pack(pady=10)
        for texto, cmd in (("Ver ficha completa", ver_ficha),
                           ("Mapa de todas las ubicaciones", mapa_personas),
                           ("Zona de búsqueda de la persona", zona_persona),
                           ("Cambiar contraseña", nueva_clave)):
            tk.Button(barra, text=texto, command=cmd, width=26).pack(side="left", padx=5)


    def fosas():
        folio = pedir_contrasena("Acceso restringido – fosas clandestinas",
                                 "Sección confidencial.\nIngresa el folio de una persona desaparecida:")
        if not folio:
            return
        try:
            datos, f_datos = abrir_datos_fosas(folio)
        except PermissionError as e:
            messagebox.showerror("Acceso denegado", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        estado_previo = estado.cget("text")
        estado.config(text="Entrenando el modelo de fosas con datos reales (validación cruzada)...")
        root.config(cursor="watch")
        root.update_idletasks()
        try:
            res, m = entrenar_fosas(preparar_fosas(g.mun, datos))
            guardar_resultados_fosas(res, m, f_datos)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        finally:
            root.config(cursor="")
            estado.config(text=estado_previo)
        ventana_figura("Fosas clandestinas – probabilidad por municipio", fig_fosas(res, m, g.geoms))
        v = tk.Toplevel(root)
        v.title("Modelo de fosas – métricas y fuentes")
        v.geometry("640x560")
        t = scrolledtext.ScrolledText(v, wrap=tk.WORD, font=("Courier", 10))
        t.pack(expand=True, fill="both", padx=10, pady=10)
        t.insert(tk.END, texto_fosas(m) + "\nFuentes\n- " + datos["fuente_fosas"]
                 + "\n- " + datos["fuente_homicidios"]
                 + "\n- RNPDNO (corte 30/11/2025) e INEGI (Censo 2020, localidades)\n")
        t.config(state=tk.DISABLED)

    root = tk.Tk()
    root.title("GEODETEC – Estado de México")
    root.geometry("640x460")
    root.config(bg="#f0f0f0")
    tk.Label(root, text="GEODETEC", font=("Helvetica", 28, "bold"),
             fg="#1e3d59", bg="#f0f0f0").pack(pady=(16, 2))
    tk.Label(root, text="Análisis territorial inteligente – Estado de México\n"
                        "Entrena con municipios simulados · prueba con los 125 municipios reales\n"
                        "INEGI 2020 · RNPDNO · Random Forest",
             font=("Helvetica", 11), bg="#f0f0f0").pack(pady=(0, 10))


    botones = [
        ("Mapa de prioridad por municipio", mapa, "#c0392b"),
        ("Zona de búsqueda por municipio", busqueda, "#c0392b"),
        ("Personas desaparecidas (acceso restringido)", personas, "#6c1d45"),
        ("Fosas clandestinas (acceso restringido)", fosas, "#2c2c2c"),
    ]
    lista_botones = []
    for texto, cmd, color in botones:
        b = tk.Button(root, text=texto, command=cmd, font=("Helvetica", 12), bg=color,
                      fg="white", width=36, pady=3, state="disabled")
        b.pack(pady=3)
        lista_botones.append(b)
    estado = tk.Label(root, text="Preparando el sistema: simulando datos de entrenamiento "
                                 "y cargando los datos reales...", bg="#f0f0f0",
                      fg="#555", font=("Helvetica", 9), wraplength=620)
    estado.pack(pady=10)
    root.config(cursor="watch")

    root.after(300, preparar_sistema)
    root.mainloop()


if __name__ == "__main__":
    if "--consola" in sys.argv:
        modo_consola()
    else:
        modo_gui()
