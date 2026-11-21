"""Pruebas del análisis de registros desde CSV (pestaña "Registros (CSV)")."""
from datetime import date

import pytest

from geodetec.datos import cargar_municipios, preparar_prueba_real, simular_entrenamiento
from geodetec.figuras import fig_conjunto, fig_registros, info_mapa
from geodetec.modelo import entrenar_modelo, predecir_mapa
from geodetec.registros import (EJEMPLO_PATH, MAX_REGISTROS, ErrorRegistros, analizar_registros,
                                leer_csv, texto_analisis, validar_registros)

HOY = date(2026, 11, 19)


@pytest.fixture(scope="module")
def base():
    mun, geoms = cargar_municipios()
    train, umbrales = simular_entrenamiento()
    modelo, _ = entrenar_modelo(train)
    return mun, geoms, predecir_mapa(modelo, preparar_prueba_real(mun, umbrales))


def procesar(base, origen):
    mun, geoms, _ = base
    return validar_registros(leer_csv(origen), mun, geoms, hoy=HOY)


def errores(avisos):
    return [m for _, n, m in avisos if n == "error"]


def test_ejemplo_tres_registros(base):
    regs, avisos = procesar(base, EJEMPLO_PATH)
    assert [r["id"] for r in regs] == ["R-001", "R-002", "R-003"] and avisos == []
    assert [r["metodo"] for r in regs] == ["centroide del municipio", "coordenadas", "coordenadas"]
    assert [r["municipio"] for r in regs] == ["Tejupilco", "Ecatepec de Morelos", "Valle de Bravo"]
    an = analizar_registros(regs, base[2], base[0])
    assert all(r["n_zona"] == 13 for r in an["registros"])
    # Tejupilco y Valle de Bravo están cerca: comparten municipios; Ecatepec queda aparte
    assert [(p["a"], p["b"]) for p in an["pares"]] == [("R-001", "R-003")]
    assert an["resumen"]["compartidos"] == len(an["pares"][0]["compartidos"]) > 0
    assert "Ejercicio académico" in texto_analisis(an, avisos)


def test_formato_excel_espanol(base, tmp_path):
    """Separador ';', Windows-1252, encabezados con acentos y fecha DD/MM/AAAA."""
    ruta = tmp_path / "excel.csv"
    ruta.write_bytes("ID;Fecha de desaparición;Municipio;Edad\n"
                     "A1;03/02/2025;Toluca;30\nA2;15/07/2024;Metepec;\n".encode("cp1252"))
    regs, avisos = procesar(base, str(ruta))
    assert avisos == [] and [r["municipio"] for r in regs] == ["Toluca", "Metepec"]
    assert regs[0]["fecha"] == date(2025, 2, 3) and regs[0]["edad"] == 30
    assert regs[1]["edad"] is None


def test_renglones_invalidos_se_descartan(base):
    texto = ("id,fecha_desaparicion,municipio,lat,lon\n"
             "B1,2025-01-10,Toluca,,\n"
             "B2,2030-01-01,Toluca,,\n"            # fecha futura
             "B3,ayer,Toluca,,\n"                  # fecha inválida
             "B4,2025-01-10,,19.4326,-99.1332\n"   # Zócalo de la CDMX: fuera del estado
             "B5,2025-01-10,Gotham,,\n"            # municipio inexistente y sin coordenadas
             "B1,2025-01-10,Toluca,,\n"            # id repetido
             ",2025-01-10,Toluca,,\n")             # sin id
    regs, avisos = procesar(base, texto)
    assert [r["id"] for r in regs] == ["B1"]
    assert len(errores(avisos)) == 6
    assert {r for r, n, _ in avisos if n == "error"} == {3, 4, 5, 6, 7, 8}


def test_correcciones_con_aviso(base):
    texto = ("id,fecha_desaparicion,municipio,lat,lon,edad\n"
             "C1,2025-05-01,Valle de Brabo,,,25\n"          # errata
             "C2,2025-05-01,Ecatepec,,,\n"                  # nombre corto
             "C3,2025-05-01,,-99.03,19.60,\n"               # lat/lon invertidas
             "C4,2025-05-01,Toluca,19.20,-100.10,150\n")    # coords en Valle de Bravo, edad mala
    regs, avisos = procesar(base, texto)
    assert errores(avisos) == []
    assert [r["municipio"] for r in regs] == ["Valle de Bravo", "Ecatepec de Morelos",
                                              "Ecatepec de Morelos", "Valle de Bravo"]
    assert regs[3]["edad"] is None and len(avisos) == 5


def test_archivos_inutilizables(base):
    with pytest.raises(ErrorRegistros, match="vacío"):
        leer_csv("\n\n")
    with pytest.raises(ErrorRegistros, match="fecha_desaparicion"):
        leer_csv("id,municipio\nX,Toluca\n")
    with pytest.raises(ErrorRegistros, match="municipio"):
        leer_csv("id,fecha\nX,2025-01-01\n")
    regs, _ = procesar(base, "id,fecha,municipio\nX,2025-01-01,Gotham\n")
    with pytest.raises(ErrorRegistros, match="válidos"):
        analizar_registros(regs, base[2], base[0])


def test_limite_de_registros(base):
    texto = "id,fecha,municipio\n" + "".join(f"D{i},2025-01-01,Toluca\n" for i in range(40))
    regs, avisos = procesar(base, texto)
    assert len(regs) == MAX_REGISTROS and "primeros" in avisos[-1][2]


def test_figuras_y_exportacion(base):
    mun, geoms, mapa = base
    an = analizar_registros(procesar(base, EJEMPLO_PATH)[0], mapa, mun)
    fig = fig_registros(an, mapa, geoms)
    datos = info_mapa(fig.axes[0])
    assert datos and any("R-003" in linea for linea in datos["lineas"]("15110"))
    assert fig_conjunto(an).axes


def test_reporte_pdf(base, tmp_path):
    from geodetec.reportes import Reporte, generar_reporte_registros
    from geodetec.reportes.registros import interpretar_registro, tiempo_legible
    mun, geoms, mapa = base
    regs, avisos = procesar(base, EJEMPLO_PATH)
    an = analizar_registros(regs, mapa, mun)
    ruta = tmp_path / "reporte.pdf"
    paginas = generar_reporte_registros(an, avisos, mapa, geoms, {"accuracy": 0.93}, str(ruta),
                                        EJEMPLO_PATH, es_ejemplo=True)
    assert paginas >= 3 + len(regs) and ruta.read_bytes()[:5] == b"%PDF-"
    # interpretaciones con datos reales del análisis
    texto = " ".join(interpretar_registro(an["registros"][0], an, 30))
    assert "Tejupilco" in texto and "coordenadas más precisas" in texto
    assert tiempo_legible(10) == "10 días" and tiempo_legible(400) == "1 año y 1 mes"
    # la plantilla sirve para cualquier reporte y numera las páginas
    r = Reporte("Prueba")
    r.portada([("Dato", "valor")], aviso="aviso")
    r.seccion("Sección")
    r.parrafo("texto " * 2000)                       # fuerza varias páginas
    assert r.guardar(str(tmp_path / "plantilla.pdf")) > 3
