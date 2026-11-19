"""Modelo de prioridad de búsqueda: entrenamiento (simulados), evaluación (reales) y predicción."""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score

from .config import CLASES, VARIABLES


def entrenar_modelo(train):
    """Entrena el Random Forest y devuelve ``(modelo, cv_scores)`` de la validación cruzada."""
    X, y = train[VARIABLES], train["prioridad"]
    modelo = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                    class_weight="balanced", random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(modelo, X, y, cv=cv, scoring="accuracy")
    modelo.fit(X, y)
    return modelo, cv_scores


def evaluar_modelo(modelo, test, cv_scores):
    """Métricas del modelo sobre los municipios reales."""
    X, y = test[VARIABLES], test["prioridad"]
    y_pred = modelo.predict(X)
    et = [0, 1, 2]
    return {
        "accuracy": accuracy_score(y, y_pred),
        "precision": precision_score(y, y_pred, labels=et, average="macro", zero_division=0),
        "recall": recall_score(y, y_pred, labels=et, average="macro", zero_division=0),
        "f1": f1_score(y, y_pred, labels=et, average="macro", zero_division=0),
        "matriz": confusion_matrix(y, y_pred, labels=et),
        "reporte": classification_report(y, y_pred, labels=et, target_names=CLASES,
                                         zero_division=0),
        "cv_media": float(np.mean(cv_scores)), "cv_desv": float(np.std(cv_scores)),
        "y_pred": y_pred,
    }


def texto_metricas(m, train, test, umbrales):
    """Resumen legible de las métricas (ventana de la GUI y modo consola)."""
    d_tr = train["prioridad"].value_counts().reindex([0, 1, 2], fill_value=0)
    d_te = test["prioridad"].value_counts().reindex([0, 1, 2], fill_value=0)
    t = "GEODETEC – Estado de México – Resultados\n" + "=" * 46 + "\n\n"
    t += f"Entrenamiento: {len(train)} municipios SIMULADOS\n"
    t += f"Prueba:        {len(test)} municipios REALES del Estado de México\n\n"
    t += (f"Umbrales de la regla (terciles del entrenamiento): "
          f"{umbrales[0]:.3f} / {umbrales[1]:.3f}\n\n")
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
    """Agrega ``prediccion`` y ``prob_baja/media/alta`` a una copia de ``datos``."""
    proba = modelo.predict_proba(datos[VARIABLES])
    prob = np.zeros((len(datos), 3))
    for j, c in enumerate(modelo.classes_):
        prob[:, int(c)] = proba[:, j]
    out = datos.copy()
    out["prediccion"] = prob.argmax(axis=1)
    out["prob_baja"], out["prob_media"], out["prob_alta"] = prob[:, 0], prob[:, 1], prob[:, 2]
    return out
