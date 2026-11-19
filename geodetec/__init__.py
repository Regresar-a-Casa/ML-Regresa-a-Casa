"""GEODETEC – análisis territorial con Machine Learning para la búsqueda de personas
desaparecidas en el Estado de México (proyecto académico).

Módulos:
    config       rutas, constantes y lectura del archivo .env
    datos        municipios reales, variables, regla de prioridad y datos simulados
    db           persistencia en SQLite
    modelo       Random Forest de prioridad (entrenar, evaluar, predecir)
    busqueda     zona de búsqueda prioritaria
    cripto       derivación de claves y cifrado Fernet
    personas     registro confidencial de personas ficticias
    fosas        modelo de fosas clandestinas (datos reales cifrados)
    figuras      gráficas y mapas (matplotlib)
    sistema      orquestador (clase Geodetec)
    consola      modo sin interfaz gráfica
    gui          interfaz Tkinter
"""
__version__ = "1.1.0"
