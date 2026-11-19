"""Orquestador del sistema: genera los datos, entrena el modelo y guarda todo en SQLite."""
import pandas as pd

from .datos import cargar_municipios, preparar_prueba_real, simular_entrenamiento
from .db import cargar_tabla, guardar_metricas, guardar_tablas
from .modelo import entrenar_modelo, evaluar_modelo, predecir_mapa
from .personas import crear_registro_personas


class Geodetec:
    """Estado compartido por la GUI y el modo consola.

    Uso: ``g = Geodetec(); g.paso_generar(); g.paso_entrenar()``.
    """

    def __init__(self):
        self.mun, self.geoms = cargar_municipios()
        self.train = self.test = self.umbrales = None
        self.modelo = self.cv_scores = self.metricas = self.mapa_pred = None

    def paso_generar(self):
        """Simula el entrenamiento, etiqueta los reales y crea el registro de personas si falta."""
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
        """Entrena con simulados, evalúa en reales y guarda métricas y predicciones."""
        self.modelo, self.cv_scores = entrenar_modelo(self.train)
        self.metricas = evaluar_modelo(self.modelo, self.test, self.cv_scores)
        guardar_metricas(self.metricas)
        self.mapa_pred = predecir_mapa(self.modelo, self.test)
        guardar_tablas({"predicciones_reales": self.mapa_pred[
            ["cvegeo", "municipio", "prioridad", "prediccion",
             "prob_baja", "prob_media", "prob_alta"]]})

    def cve_por_nombre(self, nombre):
        fila = self.mun[self.mun["municipio"] == nombre]
        if fila.empty:
            raise ValueError(f"No existe el municipio '{nombre}'")
        return fila["cvegeo"].iloc[0]

    def municipio_por_nombre(self, nombre):
        """Fila completa (Series) del municipio con ese nombre."""
        return self.mun[self.mun["cvegeo"] == self.cve_por_nombre(nombre)].iloc[0]
