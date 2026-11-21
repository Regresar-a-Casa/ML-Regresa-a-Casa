/* ============================================================
   BUSCÁNDOTE · Puente con GEODETEC_edomex.py
   ------------------------------------------------------------
   Replica en JS las funciones del modelo en Python:
     puntajePrioridad()  ≈ puntaje_prioridad(df)
     predecirMunicipio() ≈ modelo.predict_proba() (aproximación)
     distanciaKm()       ≈ distancia_km()  (Haversine)
     zonaBusqueda()      ≈ zona_busqueda_punto()
   El Random Forest real se sustituye por una función logística
   alrededor de los umbrales (terciles) del entrenamiento. Para
   producción: fetch() a un endpoint /predict que cargue el .pkl.
   ============================================================ */

const UMBRALES = { media: 0.4723, alta: 0.5301 };   // terciles del entrenamiento simulado
const PESOS_MODELO = { hist: 0.30, rep: 0.20, veg: 0.20, urb: 0.15, acc: 0.10, ter: 0.05 };
const PISO_MODELO = 0.25;      // aporte mínimo aunque P(alta) sea 0
const SIGMA_KM = 30.0;         // alcance de la cercanía
const PORCENTAJE_ZONA = 0.10;  // 10 % de municipios más prioritarios
const SUAVIDAD = 0.018;        // qué tan "dura" es la frontera entre clases

/* Paleta de prioridad: verde → ámbar → naranja → rojo */
const PALETA_PRIORIDAD = ["#3f9f78", "#e9b949", "#e3763a", "#c4413a"];
const ETIQUETAS_PRIORIDAD = ["Baja", "Media", "Alta", "Muy alta"];

/* Regla conceptual, idéntica a puntaje_prioridad() de Python */
function puntajePrioridad(m) {
  const clip = (v) => Math.min(Math.max(v, 0), 1);
  const urb = clip((Math.log10(m.population_density) - 1) / 3.3);
  const hist = clip(Math.log1p(m.historical_record_count) / Math.log1p(1000));
  const rep = clip(m.report_frequency / 15);
  const acc = 1 - Math.abs(m.accessibility_index - 0.5) * 2;   // accesibilidad intermedia
  return PESOS_MODELO.hist * hist + PESOS_MODELO.rep * rep + PESOS_MODELO.veg * m.vegetation_index +
         PESOS_MODELO.urb * (1 - urb) + PESOS_MODELO.acc * acc + PESOS_MODELO.ter * m.terrain_index;
}

const sigmoide = (z) => 1 / (1 + Math.exp(-z));

/* Probabilidades por clase: logísticas alrededor de cada umbral */
function probabilidades(p) {
  const alta = sigmoide((p - UMBRALES.alta) / SUAVIDAD);
  const baja = sigmoide((UMBRALES.media - p) / SUAVIDAD);
  const media = Math.max(0, 1 - alta - baja);
  const s = alta + media + baja;
  return { baja: baja / s, media: media / s, alta: alta / s };
}

function predecirMunicipio(m) {
  const p = puntajePrioridad(m);
  const prob = probabilidades(p);
  const clase = prob.alta >= prob.media && prob.alta >= prob.baja ? 2 : prob.media >= prob.baja ? 1 : 0;
  return {
    cvegeo: m.cvegeo, municipio: m.municipio, lat: m.lat, lon: m.lon,
    puntaje: +p.toFixed(4),
    prob_baja: +prob.baja.toFixed(4), prob_media: +prob.media.toFixed(4), prob_alta: +prob.alta.toFixed(4),
    clase, clase_label: ["Baja", "Media", "Alta"][clase],
  };
}

/* Haversine en km */
function distanciaKm(lon1, lat1, lon2, lat2) {
  const rad = Math.PI / 180;
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2 +
            Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(a));
}

/* Zona de búsqueda: (piso + (1-piso)·P(alta)) · cercanía gaussiana */
function zonaBusqueda(lat0, lon0, municipios) {
  const out = municipios.map((m) => {
    const pred = predecirMunicipio(m);
    const d = distanciaKm(lon0, lat0, m.lon, m.lat);
    const cercania = Math.exp(-(d * d) / (2 * SIGMA_KM * SIGMA_KM));
    const indice = (PISO_MODELO + (1 - PISO_MODELO) * pred.prob_alta) * cercania;
    return { ...pred, distancia_km: +d.toFixed(1), indice_busqueda: +indice.toFixed(5) };
  });
  out.sort((a, b) => b.indice_busqueda - a.indice_busqueda);
  const n = Math.ceil(PORCENTAJE_ZONA * out.length);
  out.forEach((r, i) => (r.en_zona = i < n));
  return out;
}

/* Prioridad continua (0–1) → nivel 0..3 y color */
function nivelPrioridad(p) { return p >= 0.72 ? 3 : p >= 0.58 ? 2 : p >= 0.42 ? 1 : 0; }
function colorPrioridad(p) { return PALETA_PRIORIDAD[nivelPrioridad(p)]; }
/* Clase del modelo municipal (0..2) → color */
function colorClase(c) { return [PALETA_PRIORIDAD[0], PALETA_PRIORIDAD[1], PALETA_PRIORIDAD[3]][c]; }

/* ---------- Red de grupos (grafo estado–estado) ----------
   Dos estados quedan unidos si comparten al menos un grupo;
   el peso es cuántos comparten. Después se mide si el grado
   del nodo se relaciona con el número de fosas (Pearson). */
function construirRed(estados, grupos) {
  const aristas = new Map();
  grupos.forEach((g) => {
    for (let i = 0; i < g.estados.length; i++)
      for (let j = i + 1; j < g.estados.length; j++) {
        const [a, b] = [g.estados[i], g.estados[j]].sort();
        const k = a + "-" + b;
        if (!aristas.has(k)) aristas.set(k, { a, b, peso: 0, grupos: [] });
        const e = aristas.get(k); e.peso++; e.grupos.push(g.id);
      }
  });
  const grado = {}, presencia = {};
  estados.forEach((e) => { grado[e.id] = 0; presencia[e.id] = 0; });
  aristas.forEach((e) => { grado[e.a] += e.peso; grado[e.b] += e.peso; });
  grupos.forEach((g) => g.estados.forEach((id) => presencia[id]++));
  const x = estados.map((e) => presencia[e.id]);
  const y = estados.map((e) => e.fosas);
  return { aristas: [...aristas.values()], grado, presencia, correlacion: pearson(x, y) };
}

function pearson(x, y) {
  const n = x.length, mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { const dx = x[i] - mx, dy = y[i] - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
  return sxy / Math.sqrt(sxx * syy);
}

window.GEODETEC = {
  UMBRALES, PALETA_PRIORIDAD, ETIQUETAS_PRIORIDAD,
  puntajePrioridad, probabilidades, predecirMunicipio, distanciaKm, zonaBusqueda,
  nivelPrioridad, colorPrioridad, colorClase, construirRed, pearson,
};
