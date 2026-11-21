/* ============================================================
   BUSCÁNDOTE · Utilidades geográficas
   Proyección, polígonos, simulación de fosas y mapa de calor (KDE).
   Depende de GEO_ESTADOS (geo-estados.js) y ESTADOS_MX (datos-mock.js).
   ============================================================ */

const GEO = (() => {
  /* Proyección equirectangular corregida por la latitud media de México (≈23°) */
  const K = 20, COS = Math.cos((23 * Math.PI) / 180);
  const proyectar = (lon, lat) => [(lon + 118) * COS * K, (33 - lat) * K];
  const desproyectar = (x, y) => [x / (COS * K) - 118, 33 - y / K];

  /* GEO_ESTADOS[id] = [poligono, ...]; poligono = [anillo, ...]; anillo = [[lon,lat], ...] */
  function caminoSVG(id) {
    return GEO_ESTADOS[id].map((poly) => poly.map((anillo) =>
      "M" + anillo.map(([lon, lat]) => proyectar(lon, lat).map((v) => v.toFixed(1)).join(",")).join("L") + "Z"
    ).join("")).join("");
  }

  function bbox(id) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    GEO_ESTADOS[id].forEach((poly) => poly[0].forEach(([lon, lat]) => {
      x0 = Math.min(x0, lon); x1 = Math.max(x1, lon); y0 = Math.min(y0, lat); y1 = Math.max(y1, lat);
    }));
    return { lonMin: x0, lonMax: x1, latMin: y0, latMax: y1 };
  }

  function bboxNacional() {
    const b = ESTADOS_MX.map((e) => bbox(e.id));
    return {
      lonMin: Math.min(...b.map((v) => v.lonMin)), lonMax: Math.max(...b.map((v) => v.lonMax)),
      latMin: Math.min(...b.map((v) => v.latMin)), latMax: Math.max(...b.map((v) => v.latMax)),
    };
  }

  /* Punto en polígono (ray casting, regla par-impar sobre todos los anillos) */
  function dentro(id, lon, lat) {
    let adentro = false;
    GEO_ESTADOS[id].forEach((poly) => poly.forEach((r) => {
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const [xi, yi] = r[i], [xj, yj] = r[j];
        if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) adentro = !adentro;
      }
    }));
    return adentro;
  }

  /* ¿En qué estado cae un punto? */
  function estadoDe(lon, lat) {
    const e = ESTADOS_MX.find((s) => dentro(s.id, lon, lat));
    return e ? e.id : null;
  }

  /* Centroide del polígono más grande (para etiquetas y nodos del grafo) */
  const _centroides = {};
  function centroide(id) {
    if (_centroides[id]) return _centroides[id];
    let mejor = null, areaMax = 0;
    GEO_ESTADOS[id].forEach((poly) => {
      const r = poly[0]; let a = 0, cx = 0, cy = 0;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const f = r[j][0] * r[i][1] - r[i][0] * r[j][1];
        a += f; cx += (r[j][0] + r[i][0]) * f; cy += (r[j][1] + r[i][1]) * f;
      }
      if (Math.abs(a) > areaMax) { areaMax = Math.abs(a); mejor = [cx / (3 * a), cy / (3 * a)]; }
    });
    /* Ajustes manuales donde el centroide cae fuera o se encima */
    const ajuste = { "15": [-99.75, 19.45], "09": [-99.13, 19.31], "26": [-110.6, 29.6] };
    return (_centroides[id] = ajuste[id] || mejor);
  }

  /* Generador pseudoaleatorio con semilla (mulberry32): mismos datos en cada carga */
  function rng(semilla) {
    let a = semilla >>> 0;
    return () => {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const gauss = (r) => Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(2 * Math.PI * r());

  function puntoAleatorio(id, r) {
    const b = bbox(id);
    for (let k = 0; k < 500; k++) {
      const lon = b.lonMin + r() * (b.lonMax - b.lonMin), lat = b.latMin + r() * (b.latMax - b.latMin);
      if (dentro(id, lon, lat)) return [lon, lat];
    }
    return centroide(id);
  }

  /* Fosas simuladas: se agrupan en 1–3 "focos" por estado, como ocurre
     en los hallazgos reales (los sitios se concentran, no son uniformes). */
  function generarFosasSimuladas() {
    const r = rng(2026), out = [];
    const procs = ["En investigación", "Peritaje", "Cerrada"];
    ESTADOS_MX.forEach((e) => {
      const b = bbox(e.id);
      const escala = Math.max(b.lonMax - b.lonMin, b.latMax - b.latMin) * 0.09;
      const focos = Array.from({ length: 1 + Math.floor(r() * 3) }, () => puntoAleatorio(e.id, r));
      for (let i = 0; i < e.fosas; i++) {
        const f = focos[i % focos.length];
        let p = null;
        for (let k = 0; k < 40 && !p; k++) {
          const lon = f[0] + gauss(r) * escala, lat = f[1] + gauss(r) * escala;
          if (dentro(e.id, lon, lat)) p = [lon, lat];
        }
        p = p || f;
        const fecha = new Date(Date.UTC(2019, 0, 1) + Math.floor(r() * 2500) * 864e5);
        out.push({
          id: `S-${e.id}-${String(i + 1).padStart(2, "0")}`, estado: e.id, municipio: "Sin dato (simulada)",
          lon: +p[0].toFixed(4), lat: +p[1].toFixed(4), fecha: fecha.toISOString().slice(0, 10),
          victimas: 1 + Math.floor(r() * 6), estado_proc: procs[Math.floor(r() * 3)], simulada: true,
        });
      }
    });
    return out;
  }

  /* Mapa de calor por estimación de densidad de kernel (KDE gaussiano)
     sobre las fosas conocidas, escalado por la prioridad del modelo.
     Devuelve celdas de una rejilla recortada al polígono del estado. */
  function densidad(id, fosas, prioridad, columnas = 34) {
    const b = bbox(id);
    const ancho = b.lonMax - b.lonMin, alto = b.latMax - b.latMin;
    const paso = Math.max(ancho, alto) / columnas;
    const h = Math.max(ancho, alto) * 0.07;            // ancho de banda
    const pts = fosas.filter((f) => f.estado === id);
    const celdas = [];
    for (let lon = b.lonMin + paso / 2; lon < b.lonMax; lon += paso)
      for (let lat = b.latMin + paso / 2; lat < b.latMax; lat += paso) {
        if (!dentro(id, lon, lat)) continue;
        let d = 0;
        pts.forEach((f) => {
          const dx = (f.lon - lon) * COS, dy = f.lat - lat;
          d += Math.exp(-(dx * dx + dy * dy) / (2 * h * h)) * (f.simulada ? 1 : 1.4);
        });
        celdas.push({ lon, lat, paso, d });
      }
    const max = Math.max(1e-9, ...celdas.map((c) => c.d));
    celdas.forEach((c) => {
      /* probabilidad = densidad normalizada · (0.55 + 0.45·prioridad del estado) */
      c.valor = (c.d / max) * (0.55 + 0.45 * prioridad);
    });
    return celdas;
  }

  return { proyectar, desproyectar, caminoSVG, bbox, bboxNacional, dentro, estadoDe, centroide,
           generarFosasSimuladas, densidad };
})();
