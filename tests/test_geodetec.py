"""Pruebas básicas de GEODETEC. Ejecutar con:  python -m pytest

No usan la base de datos real (cada prueba trabaja en una carpeta temporal) ni requieren el
archivo .env.
"""
import numpy as np
import pytest

from geodetec import config
from geodetec.busqueda import distancia_km, localizador, zona_busqueda_punto
from geodetec.datos import cargar_municipios, preparar_prueba_real, simular_entrenamiento, variables_reales
from geodetec.modelo import entrenar_modelo, evaluar_modelo, predecir_mapa


@pytest.fixture(scope="module")
def municipios():
    return cargar_municipios()


@pytest.fixture(scope="module")
def pipeline(municipios):
    mun, _ = municipios
    train, umbrales = simular_entrenamiento()
    test = preparar_prueba_real(mun, umbrales)
    modelo, cv = entrenar_modelo(train)
    return train, test, modelo, evaluar_modelo(modelo, test, cv), predecir_mapa(modelo, test)


# ------------------------------------------------------------------ datos
def test_carga_125_municipios(municipios):
    mun, geoms = municipios
    assert len(mun) == 125 and len(geoms) == 125
    assert mun["cvegeo"].is_monotonic_increasing


def test_variables_en_rango(municipios):
    df = variables_reales(municipios[0])
    for c in ("terrain_index", "vegetation_index", "accessibility_index"):
        assert df[c].between(0, 1).all(), c


def test_simulacion_reproducible():
    a, ua = simular_entrenamiento()
    b, ub = simular_entrenamiento()
    assert a.equals(b) and np.allclose(ua, ub)
    assert len(a) == config.N_TRAIN
    assert sorted(a["prioridad"].unique()) == [0, 1, 2]


# ------------------------------------------------------------------ modelo y búsqueda
def test_metricas_validas(pipeline):
    _, test, _, m, mapa = pipeline
    assert 0 <= m["accuracy"] <= 1 and m["matriz"].sum() == len(test)
    assert np.allclose(mapa[["prob_baja", "prob_media", "prob_alta"]].sum(axis=1), 1)


def test_red_neuronal(pipeline):
    from geodetec.figuras import fig_curva_aprendizaje, fig_importancia
    _, _, modelo, m, _ = pipeline
    red = modelo.named_steps["red"]
    assert red.n_features_in_ == len(config.VARIABLES) and red.n_outputs_ == 3
    assert len(red.loss_curve_) == red.n_iter_ and red.loss_curve_[-1] < red.loss_curve_[0]
    assert m["accuracy"] > 0.85          # el RF anterior daba 0.704 con la misma semilla
    assert set(m["importancia"]) == set(config.VARIABLES)
    assert max(m["importancia"], key=m["importancia"].get) == "historical_record_count"
    assert fig_importancia(m).axes and fig_curva_aprendizaje(modelo).axes


def test_distancia_km_conocida():
    # Zócalo CDMX -> centro de Toluca ≈ 55 km
    (lon1, lat1), (lon2, lat2) = config.CENTROS.values()
    assert 50 < distancia_km(lon1, lat1, lon2, lat2) < 60


def test_zona_busqueda_10_por_ciento(municipios, pipeline):
    mun, _ = municipios
    mapa = pipeline[4]
    o = mun.iloc[0]
    zona = zona_busqueda_punto(mapa, mun, o["lon"], o["lat"])
    assert zona["en_zona"].sum() == int(np.ceil(config.PORCENTAJE_ZONA * len(mun)))
    assert zona["indice_busqueda"].is_monotonic_decreasing


def test_zona_parametros(municipios, pipeline):
    mun, _ = municipios
    mapa = pipeline[4]
    o = mun.iloc[10]
    base = zona_busqueda_punto(mapa, mun, o["lon"], o["lat"])
    explicita = zona_busqueda_punto(mapa, mun, o["lon"], o["lat"], sigma_km=config.SIGMA_KM,
                                    piso=config.PISO_MODELO, porcentaje=config.PORCENTAJE_ZONA)
    assert base.equals(explicita)                       # los valores por omisión no cambian nada
    assert zona_busqueda_punto(mapa, mun, o["lon"], o["lat"], porcentaje=0.2)["en_zona"].sum() == 25
    # con piso = 1 solo cuenta la distancia: el orden es del más cercano al más lejano
    solo_distancia = zona_busqueda_punto(mapa, mun, o["lon"], o["lat"], piso=1.0)
    assert solo_distancia["distancia_km"].is_monotonic_increasing
    # un σ mayor permite incluir municipios más lejanos
    lejos = zona_busqueda_punto(mapa, mun, o["lon"], o["lat"], sigma_km=80)
    assert lejos.loc[lejos["en_zona"], "distancia_km"].max() >=         base.loc[base["en_zona"], "distancia_km"].max()
    for malo in ({"sigma_km": 0}, {"piso": 1.5}, {"porcentaje": 0}):
        with pytest.raises(ValueError):
            zona_busqueda_punto(mapa, mun, o["lon"], o["lat"], **malo)


def test_localizador_municipios(municipios):
    mun, geoms = municipios
    loc = localizador(geoms)
    assert loc is localizador(geoms)                    # se reutiliza
    toluca = mun[mun["municipio"] == "Toluca"].iloc[0]
    assert loc.buscar(toluca["lon"], toluca["lat"]) == toluca["cvegeo"]
    assert loc.buscar(*config.CENTROS["CDMX (Zócalo)"]) is None    # la CDMX no es del Edomex
    dentro = sum(loc.buscar(r.lon, r.lat) == r.cvegeo for r in mun.itertuples())
    assert dentro >= 0.9 * len(mun)                     # casi todos los centroides caen dentro


def test_mapas_con_informacion(municipios, pipeline):
    from geodetec.figuras import fig_busqueda, fig_mapa, info_mapa
    mun, geoms = municipios
    mapa = pipeline[4]
    cve = mapa["cvegeo"].iloc[0]
    fig = fig_mapa(mapa, geoms)
    infos = [info_mapa(ax) for ax in fig.axes if info_mapa(ax)]
    assert len(infos) == 3
    assert infos[0]["lineas"](cve)[0].split(": ")[1] in config.CLASES
    o = mun.iloc[0]
    zona = zona_busqueda_punto(mapa, mun, o["lon"], o["lat"])
    fig = fig_busqueda(zona, geoms, o["lon"], o["lat"], o["municipio"])
    info = next(info_mapa(ax) for ax in fig.axes if info_mapa(ax))
    assert len(info["lineas"](cve)) == 3 and info["lineas"]("no-existe") == []


# ------------------------------------------------------------------ registro cifrado
def test_registro_personas_ciclo_completo(municipios, tmp_path):
    pytest.importorskip("cryptography")
    from geodetec.personas import abrir_registro_personas, cambiar_contrasena, crear_registro_personas
    mun, geoms = municipios
    db = str(tmp_path / "prueba.db")
    assert crear_registro_personas(mun, geoms, contrasena="clave-prueba", db=db)
    assert not crear_registro_personas(mun, geoms, contrasena="otra", db=db)   # no se recrea
    personas = abrir_registro_personas("clave-prueba", db=db)
    assert len(personas) == config.N_PERSONAS
    with pytest.raises(PermissionError):
        abrir_registro_personas("incorrecta", db=db)
    with pytest.raises(ValueError):
        cambiar_contrasena("clave-prueba", "corta", db=db)
    cambiar_contrasena("clave-prueba", "clave-nueva-123", db=db)
    assert abrir_registro_personas("clave-nueva-123", db=db) == personas


def test_folio_invalido_en_fosas():
    pytest.importorskip("cryptography")
    from geodetec.fosas import abrir_datos_fosas
    with pytest.raises(PermissionError):
        abrir_datos_fosas("FOLIO-INEXISTENTE")


# ------------------------------------------------------------------ configuración
def test_cargar_env(tmp_path, monkeypatch):
    archivo = tmp_path / ".env"
    archivo.write_text('# comentario\nGEODETEC_PRUEBA_A="con comillas"\nexport GEODETEC_PRUEBA_B=2\n',
                       encoding="utf-8")
    monkeypatch.delenv("GEODETEC_PRUEBA_A", raising=False)
    monkeypatch.delenv("GEODETEC_PRUEBA_B", raising=False)
    config.cargar_env(str(archivo))
    import os
    assert os.environ["GEODETEC_PRUEBA_A"] == "con comillas"
    assert os.environ["GEODETEC_PRUEBA_B"] == "2"


def test_falta_contrasena_inicial(monkeypatch):
    monkeypatch.delenv("GEODETEC_CONTRASENA_INICIAL", raising=False)
    with pytest.raises(RuntimeError):
        config.contrasena_inicial()
