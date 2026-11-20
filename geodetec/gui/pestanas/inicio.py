"""Pestaña de inicio: qué es el sistema, cómo recorrerlo y métricas principales."""
from tkinter import ttk

from ...config import N_TRAIN
from ..componentes import MarcoDesplazable, Tarjeta, etiqueta_ajustable
from .base import Pestana

PASOS = [
    ("Datos", "Las 6 variables de los 125 municipios reales (INEGI 2020, RNPDNO) y cómo se "
              "comparan con los 500 municipios simulados que se usan para entrenar."),
    ("Modelo", "Red neuronal entrenada con simulados y evaluado con los municipios reales: "
               "métricas, matriz de confusión e importancia de variables."),
    ("Mapa de prioridad", "Prioridad de búsqueda (Baja, Media, Alta) para cada municipio y "
                          "probabilidad de prioridad alta."),
    ("Zona de búsqueda", "A partir de la última ubicación conocida, combina la probabilidad del "
                         "modelo con la distancia y marca el 10 % de municipios prioritarios."),
    ("Confidencial", "Registro de personas (ficticias) protegido con contraseña y modelo de fosas "
                     "clandestinas con datos reales, protegido con folio."),
]


VARIABLES_EXPLICADAS = [
    ("Terreno", "Variación de la altitud dentro del municipio (relieve accidentado = valor alto)."),
    ("Vegetación", "Proporción de localidades rurales; aproxima zonas poco urbanizadas."),
    ("Densidad", "Habitantes por km² según el Censo 2020."),
    ("Accesibilidad", "Cercanía a un centro metropolitano (1 = muy cerca, 0 = a 110 km o más)."),
    ("Registros históricos", "Personas desaparecidas y no localizadas acumuladas en el RNPDNO."),
    ("Frecuencia de reportes", "Registros por cada 100 mil habitantes al año (2020-2025)."),
]


def texto_brecha(m):
    """Valor y explicación de la diferencia entre la prueba real y la validación cruzada."""
    dif = (m["accuracy"] - m["cv_media"]) * 100
    if abs(dif) < 0.05:
        return "0.0 pts", "El modelo rinde igual con datos reales que con simulados."
    if dif > 0:
        return (f"+{dif:.1f} pts", "Accuracy real − validación cruzada: con los datos reales el "
                                   "modelo rinde mejor que con los simulados.")
    return (f"{dif:.1f} pts", "Accuracy real − validación cruzada: lo que se pierde al pasar de "
                              "datos simulados a reales.")


class PestanaInicio(Pestana):
    requiere_sistema = False

    def construir(self):
        desplazable = MarcoDesplazable(self.contenido)
        desplazable.pack(fill="both", expand=True)
        c = desplazable.interior
        c.columnconfigure(0, weight=3, uniform="col")
        c.columnconfigure(1, weight=2, uniform="col")

        # ---- columna izquierda: presentación y recorrido
        izq = ttk.Frame(c)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        etiqueta_ajustable(izq, "Análisis territorial para la búsqueda de personas desaparecidas",
                           "Titulo.TLabel").pack(anchor="w", fill="x")
        etiqueta_ajustable(
            izq, "GEODETEC estima qué municipios del Estado de México deberían priorizarse en la "
                 "búsqueda, combinando datos territoriales, demográficos y de registros de "
                 "personas desaparecidas con un modelo de Machine Learning.",
            "Suave.TLabel").pack(anchor="w", fill="x", pady=(4, 14))

        ttk.Label(izq, text="Recorrido sugerido", style="Subtitulo.TLabel").pack(anchor="w")
        lista = ttk.Frame(izq)
        lista.pack(fill="x", pady=(6, 10))
        lista.columnconfigure(1, weight=1)
        self._botones_paso = []
        for i, (nombre, texto) in enumerate(PASOS, start=1):
            b = ttk.Button(lista, text=f"{i}. {nombre}", width=20, state="disabled",
                           command=lambda n=i: self.app.ir_a(n))
            b.grid(row=i, column=0, sticky="nw", pady=4)
            self._botones_paso.append(b)
            etiqueta_ajustable(lista, texto, "Suave.TLabel").grid(
                row=i, column=1, sticky="ew", padx=(12, 0), pady=4)

        ttk.Label(izq, text="Variables del modelo", style="Subtitulo.TLabel").pack(
            anchor="w", pady=(10, 4))
        rejilla_var = ttk.Frame(izq)
        rejilla_var.pack(fill="x")
        rejilla_var.columnconfigure((0, 1, 2), weight=1, uniform="var")
        for k, (nombre, texto) in enumerate(VARIABLES_EXPLICADAS):
            tarjeta = ttk.Frame(rejilla_var, style="Tarjeta.TFrame", padding=(12, 8))
            tarjeta.grid(row=k // 3, column=k % 3, sticky="nsew", padx=3, pady=3)
            ttk.Label(tarjeta, text=nombre, style="TarjetaTitulo.TLabel").pack(anchor="w")
            etiqueta_ajustable(tarjeta, texto, "TarjetaSuave.TLabel").pack(anchor="w", fill="x")

        etiqueta_ajustable(
            izq, "Atajos: Ctrl+1 … Ctrl+6 cambian de pestaña · F11 activa el modo presentación "
                 "(pantalla completa y letra más grande) · Esc lo desactiva.",
            "Suave.TLabel").pack(anchor="w", fill="x", pady=(12, 0))

        # ---- columna derecha: estado y métricas
        der = ttk.Frame(c)
        der.grid(row=0, column=1, sticky="nsew")
        ttk.Label(der, text="Resultados del modelo", style="Subtitulo.TLabel").pack(anchor="w")
        self._estado = etiqueta_ajustable(der, "Preparando el sistema…", "Suave.TLabel")
        self._estado.pack(anchor="w", fill="x", pady=(2, 8))
        rejilla = ttk.Frame(der)
        rejilla.pack(fill="x")
        rejilla.columnconfigure((0, 1), weight=1, uniform="tarjeta")
        self.t_accuracy = Tarjeta(rejilla, "Accuracy en municipios reales",
                                  "Proporción de municipios reales clasificados igual que la regla.")
        self.t_cv = Tarjeta(rejilla, "Validación cruzada (simulados)",
                            "Desempeño esperado si los datos reales se parecieran a los simulados.")
        self.t_f1 = Tarjeta(rejilla, "F1 macro (reales)", "Balance entre precisión y recall, "
                                                           "promediado en las 3 clases.")
        self.t_brecha = Tarjeta(rejilla, "Diferencia real vs. simulado",
                                "Accuracy real − validación cruzada.")
        for k, t in enumerate((self.t_accuracy, self.t_cv, self.t_f1, self.t_brecha)):
            t.grid(row=k // 2, column=k % 2, sticky="nsew", padx=4, pady=4)

        aviso = ttk.Frame(der, style="Tarjeta.TFrame", padding=(14, 10))
        aviso.pack(fill="x", pady=(12, 0), padx=4)
        ttk.Label(aviso, text="Ejercicio académico", style="Confidencial.TLabel").pack(anchor="w")
        etiqueta_ajustable(
            aviso, "Las personas del registro son 100 % ficticias. Una probabilidad alta indica un "
                   "municipio a revisar, no un hallazgo. Fuentes: INEGI (Censo 2020, catálogo de "
                   "localidades), RNPDNO (corte 30/11/2025), CNB.",
            "TarjetaSuave.TLabel").pack(anchor="w", fill="x")

    def estado(self, texto):
        self._estado.configure(text=texto)

    def renderizar(self):
        g = self.g
        if g.metricas is None:
            return
        m = g.metricas
        self.t_accuracy.actualizar(f"{m['accuracy']:.1%}")
        self.t_cv.actualizar(f"{m['cv_media']:.1%}", f"± {m['cv_desv']:.1%} entre las 5 "
                                                      f"particiones de {N_TRAIN} simulados.")
        self.t_f1.actualizar(f"{m['f1']:.3f}")
        self.t_brecha.actualizar(*texto_brecha(m))
        self.estado(f"Sistema listo · {len(g.train)} municipios simulados para entrenar · "
                    f"{len(g.test)} municipios reales evaluados.")
        for b in self._botones_paso:
            b.configure(state="normal")
