/* ============================================================
   BUSCÁNDOTE · Panel de colectivos (dashboard.html)
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  if (!REGISTRO.haySesion()) { location.replace("index.html"); return; }

  const $ = (id) => document.getElementById(id);
  const estadoPorId = (id) => ESTADOS_MX.find((e) => e.id === id);
  const etiqueta = (p) => GEODETEC.ETIQUETAS_PRIORIDAD[GEODETEC.nivelPrioridad(p)];
  const fmt = (n) => n.toLocaleString("es-MX");
  const fechaLarga = (f) => new Date(f + "T12:00").toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
  const pill = (p) => `<span class="pill" style="--c:${GEODETEC.colorPrioridad(p)}">${etiqueta(p)} · ${Math.round(p * 100)} %</span>`;

  let fosas = REGISTRO.todas();

  /* ---------- Pestañas ---------- */
  const pestanas = document.querySelectorAll(".pestana");
  pestanas.forEach((t) => t.addEventListener("click", () => abrirPestana(t.dataset.tab)));
  function abrirPestana(nombre) {
    pestanas.forEach((x) => { const on = x.dataset.tab === nombre; x.classList.toggle("activa", on); x.setAttribute("aria-selected", on); });
    document.querySelectorAll(".vista").forEach((v) => v.classList.toggle("activa", v.id === "vista-" + nombre));
    document.querySelector(".principal").scrollTo({ top: 0 });
  }

  $("btnSalir").addEventListener("click", () => { REGISTRO.cerrarSesion(); location.href = "index.html"; });
  $("fechaCorte").textContent = "Corte: " + new Date().toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" });

  /* =========================================================
     RESUMEN
     ========================================================= */
  function pintarResumen() {
    const nuevas = REGISTRO.nuevas().length;
    animarNumero($("kpiFosas"), fosas.length);
    $("kpiFosasNota").textContent = nuevas ? `${nuevas} ${nuevas === 1 ? "registrada" : "registradas"} por tu colectivo` : `${FOSAS_MOCK.length} verificadas a mano en la demo`;
    animarNumero($("kpiVictimas"), fosas.reduce((s, f) => s + f.victimas, 0));
    animarNumero($("kpiEstados"), ESTADOS_MX.filter((e) => e.prioridad >= 0.72).length);
    animarNumero($("kpiModelo"), KPIS_NACIONALES.precision_modelo * 100, { decimales: 1, sufijo: " %" });

    const porEstado = ESTADOS_MX.map((e) => ({ e, n: fosas.filter((f) => f.estado === e.id).length }))
      .sort((a, b) => b.n - a.n).slice(0, 10);
    GRAFICAS.barras($("graficaEstados"), porEstado.map(({ e, n }) => ({
      etiqueta: e.nombre, valor: n, color: GEODETEC.colorPrioridad(e.prioridad),
    })));

    const anios = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026].filter((a) => a < 2026 || fosas.some((f) => f.fecha.startsWith(a)));
    GRAFICAS.linea($("graficaAnios"), anios.map((a) => ({ x: String(a), y: fosas.filter((f) => f.fecha.startsWith(a)).length })));

    $("listaPrioridad").innerHTML = [...ESTADOS_MX].sort((a, b) => b.prioridad - a.prioridad).slice(0, 7).map((e) => `
      <li><button type="button" data-id="${e.id}">
        <span class="nombre">${e.nombre}</span>${pill(e.prioridad)}
        <span class="sub">${fosas.filter((f) => f.estado === e.id).length} fosas · ${fmt(e.personas)} reportes</span>
      </button></li>`).join("");

    const ultimas = [...fosas].sort((a, b) => b.fecha.localeCompare(a.fecha)).slice(0, 6);
    $("tablaUltimas").querySelector("tbody").innerHTML = ultimas.map((f) => `
      <tr><td>${f.id}</td><td>${f.municipio === "Sin dato (simulada)" ? estadoPorId(f.estado).nombre : f.municipio}</td>
      <td>${fechaLarga(f.fecha)}</td><td class="num">${f.victimas}</td><td><span class="proc proc-${f.estado_proc.split(" ")[0].toLowerCase()}">${f.estado_proc}</span></td></tr>`).join("");
  }
  $("listaPrioridad").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-id]"); if (!b) return;
    abrirPestana("mapa"); mapa.irA(b.dataset.id);
  });

  /* =========================================================
     MAPA DE FOSAS
     ========================================================= */
  let puntoElegido = null;
  const detalle = $("detalleEstado");
  const mapa = new MapaMexico("mapaFosas", {
    privado: true,
    onEstado: (e) => pintarDetalle(e),
    onNacional: () => pintarDetalleNacional(),
    onPunto: (lon, lat, id) => { puntoElegido = { lon, lat, id }; mapa.marcarPunto(lon, lat); pintarDetalle(estadoPorId(id)); },
  });

  const filtradas = () => {
    const a = $("filtroAnio").value, p = $("filtroProc").value;
    return fosas.filter((f) => (!a || f.fecha.startsWith(a)) && (!p || f.estado_proc === p));
  };
  $("filtroAnio").innerHTML += [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019].map((a) => `<option>${a}</option>`).join("");
  ["filtroAnio", "filtroProc"].forEach((id) => $(id).addEventListener("change", () => {
    mapa.setFosas(filtradas()); if (mapa.actual) pintarDetalle(estadoPorId(mapa.actual)); else pintarDetalleNacional();
  }));
  document.querySelectorAll("[data-capa]").forEach((c) => c.addEventListener("change", () => mapa.setCapa(c.dataset.capa, c.checked)));

  function pintarLeyenda(enEstado) {
    $("leyendaMapa").innerHTML = enEstado
      ? `<span class="leyenda-titulo">Probabilidad de fosas</span>
         <span class="rampa"><i></i>baja · alta</span>
         <span><i class="ic-fosa"></i>Fosa simulada</span>
         <span><i class="ic-fosa ic-verif"></i>Verificada</span>`
      : `<span class="leyenda-titulo">Prioridad del estado</span>
         ${GEODETEC.PALETA_PRIORIDAD.map((c, i) => `<span><i style="background:${c}"></i>${GEODETEC.ETIQUETAS_PRIORIDAD[i]}</span>`).join("")}
         <span><i class="ic-fosa"></i>Fosa</span>`;
  }

  function pintarDetalleNacional() {
    pintarLeyenda(false);
    const lista = filtradas();
    detalle.innerHTML = `
      <h2>República Mexicana</h2>
      <p class="ayuda">Toca un estado para abrirlo. Dentro del estado, toca cualquier punto para marcarlo y registrar ahí una fosa.</p>
      <dl class="datos">
        <div><dt>Fosas con los filtros actuales</dt><dd>${fmt(lista.length)}</dd></div>
        <div><dt>Víctimas</dt><dd>${fmt(lista.reduce((s, f) => s + f.victimas, 0))}</dd></div>
        <div><dt>Estados con hallazgos</dt><dd>${new Set(lista.map((f) => f.estado)).size} de 32</dd></div>
      </dl>`;
  }

  function pintarDetalle(e) {
    pintarLeyenda(true);
    const lista = filtradas().filter((f) => f.estado === e.id);
    const celdas = GEO.densidad(e.id, filtradas(), e.prioridad).sort((a, b) => b.valor - a.valor);
    /* Top 5 celdas separadas entre sí (no cinco vecinas del mismo foco) */
    const top = [];
    celdas.forEach((c) => { if (top.length < 5 && top.every((t) => Math.hypot(t.lon - c.lon, t.lat - c.lat) > c.paso * 2.5)) top.push(c); });

    detalle.innerHTML = `
      <h2>${e.nombre}</h2>
      <p>${pill(e.prioridad)}</p>
      <dl class="datos">
        <div><dt>Fosas</dt><dd>${lista.length}</dd></div>
        <div><dt>Víctimas</dt><dd>${lista.reduce((s, f) => s + f.victimas, 0)}</dd></div>
        <div><dt>Reportes de desaparición</dt><dd>${fmt(e.personas)}</dd></div>
      </dl>
      <h3>Dónde es más probable encontrar otra fosa</h3>
      <ol class="zonas-probables">${top.map((c) => `
        <li><button type="button" data-lon="${c.lon.toFixed(4)}" data-lat="${c.lat.toFixed(4)}">
          <span class="barra-prob" style="--v:${c.valor};--c:${MapaMexico.colorCalor(c.valor)}"></span>
          <span>${c.lat.toFixed(3)}, ${c.lon.toFixed(3)}</span><strong>${Math.round(c.valor * 100)} %</strong>
        </button></li>`).join("") || "<li class='ayuda'>Sin fosas con estos filtros: la probabilidad no se puede estimar.</li>"}</ol>
      <p class="ayuda">Celdas de ≈${Math.round((celdas[0]?.paso || 0) * 111)} km. Toca una para marcarla en el mapa.</p>
      <div class="punto-elegido">
        ${puntoElegido && puntoElegido.id === e.id
          ? `<p>Punto marcado: <strong>${puntoElegido.lat}, ${puntoElegido.lon}</strong></p>
             <button type="button" class="boton boton-pino boton-ancho" id="btnRegistrarAqui">Registrar fosa en este punto</button>`
          : `<p class="ayuda">Toca dentro de ${e.nombre} para marcar un punto.</p>`}
      </div>
      ${e.id === "15" ? `<p class="ayuda nota-edomex">Los círculos con borde blanco son los municipios del Edomex, coloreados según la clase que predice el modelo.</p>` : ""}`;

    detalle.querySelectorAll(".zonas-probables button").forEach((b) => b.addEventListener("click", () => {
      puntoElegido = { lon: +b.dataset.lon, lat: +b.dataset.lat, id: e.id };
      mapa.marcarPunto(puntoElegido.lon, puntoElegido.lat); pintarDetalle(e);
    }));
    $("btnRegistrarAqui")?.addEventListener("click", () => {
      prellenarRegistro(puntoElegido); abrirPestana("registrar");
    });
  }

  /* =========================================================
     ZONA Y RUTA (Edomex)
     ========================================================= */
  const mapaZona = new MapaMexico("mapaZona", { privado: true });
  mapaZona.capas = { calor: false, fosas: false, red: false, municipios: true };
  mapaZona.irA("15", { animar: false });
  $("origenMunicipio").innerHTML = [...MUNICIPIOS_EDOMEX].sort((a, b) => a.municipio.localeCompare(b.municipio))
    .map((m) => `<option value="${m.cvegeo}"${m.municipio === "Valle de Bravo" ? " selected" : ""}>${m.municipio}</option>`).join("");

  $("btnCalcularZona").addEventListener("click", calcularZona);
  function calcularZona() {
    const o = MUNICIPIOS_EDOMEX.find((m) => m.cvegeo === $("origenMunicipio").value);
    const radio = +$("radioMax").value, n = +$("numParadas").value;
    const zona = GEODETEC.zonaBusqueda(o.lat, o.lon, MUNICIPIOS_EDOMEX).filter((z) => z.distancia_km <= radio);
    const paradas = zona.slice(0, n);

    /* Ruta por vecino más cercano partiendo del origen */
    const ruta = [], pend = [...paradas]; let actual = { lat: o.lat, lon: o.lon }, total = 0;
    while (pend.length) {
      pend.sort((a, b) => GEODETEC.distanciaKm(actual.lon, actual.lat, a.lon, a.lat) - GEODETEC.distanciaKm(actual.lon, actual.lat, b.lon, b.lat));
      const sig = pend.shift(), d = GEODETEC.distanciaKm(actual.lon, actual.lat, sig.lon, sig.lat);
      total += d; ruta.push({ ...sig, tramo: d }); actual = sig;
    }

    mapaZona.marcarPunto(o.lon, o.lat);
    mapaZona.resaltarMunicipios(paradas.map((p) => p.cvegeo));
    dibujarRuta(o, ruta);

    $("zonaResultado").innerHTML = `
      <h2>Ruta sugerida desde ${o.municipio}</h2>
      <p class="ayuda">${paradas.length} municipios dentro de ${radio} km, ordenados para recorrerlos en el menor trayecto.
        Distancia en línea recta: <strong>${Math.round(total)} km</strong>.</p>
      <ol class="ruta">${ruta.map((r) => `
        <li>
          <span class="ruta-mun">${r.municipio}</span>
          <span class="ruta-tramo">+${Math.round(r.tramo)} km</span>
          <span class="pill" style="--c:${GEODETEC.colorClase(r.clase)}">P(alta) ${Math.round(r.prob_alta * 100)} %</span>
        </li>`).join("")}</ol>
      <details class="desplegable-mini">
        <summary>Cómo se ordena la zona</summary>
        <p>Índice = (0.25 + 0.75 · P(alta)) · e<sup>−d²/2·30²</sup>. Los municipios cercanos al origen
          y con mayor probabilidad del modelo van primero; después la ruta une esos puntos por el vecino más cercano.</p>
      </details>`;
  }

  function dibujarRuta(o, ruta) {
    const g = mapaZona.g.pin, u = mapaZona.u;
    const pts = [[o.lon, o.lat], ...ruta.map((r) => [r.lon, r.lat])].map((p) => GEO.proyectar(...p));
    g.insertAdjacentHTML("afterbegin", `<polyline class="ruta-linea" points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke="#1e3a56" stroke-width="${u * 0.35}" stroke-dasharray="${u} ${u * 0.6}" stroke-linecap="round"/>` +
      ruta.map((r, i) => { const [x, y] = GEO.proyectar(r.lon, r.lat);
        return `<text x="${x}" y="${y - u * 1.8}" class="ruta-num" font-size="${u * 1.8}">${i + 1}</text>`; }).join(""));
  }

  /* =========================================================
     REGISTRAR FOSA
     ========================================================= */
  $("fosaEstado").innerHTML = ESTADOS_MX.map((e) => `<option value="${e.id}">${e.nombre}</option>`).join("");
  $("fosaFecha").max = $("fosaFecha").value = new Date().toISOString().slice(0, 10);
  $("fosaEstado").value = "15";
  const mapaReg = new MapaMexico("mapaRegistro", {
    privado: true,
    onEstado: (e) => ($("fosaEstado").value = e.id),
    onPunto: (lon, lat, id) => prellenarRegistro({ lon, lat, id }, false),
  });
  mapaReg.capas = { calor: true, fosas: true, red: false, municipios: false };
  $("fosaEstado").addEventListener("change", () => mapaReg.irA($("fosaEstado").value));

  function prellenarRegistro({ lon, lat, id }, mover = true) {
    $("fosaEstado").value = id; $("fosaLat").value = lat; $("fosaLon").value = lon;
    if (mover && mapaReg.actual !== id) { mapaReg.irA(id); setTimeout(() => mapaReg.marcarPunto(lon, lat), 600); }
    else mapaReg.marcarPunto(lon, lat);
    $("fosaError").textContent = ""; $("fosaMsg").textContent = "";
  }

  $("formFosa").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const err = $("fosaError"), ok = $("fosaMsg"); err.textContent = ok.textContent = "";
    const d = {
      estado: $("fosaEstado").value, municipio: $("fosaMunicipio").value.trim(),
      lat: parseFloat($("fosaLat").value), lon: parseFloat($("fosaLon").value),
      fecha: $("fosaFecha").value, victimas: parseInt($("fosaVictimas").value, 10), estado_proc: $("fosaProc").value,
    };
    if (!d.municipio) return (err.textContent = "Escribe el municipio del hallazgo.");
    if (isNaN(d.lat) || isNaN(d.lon)) return (err.textContent = "Faltan las coordenadas. Escríbelas o toca el punto en el mapa.");
    if (!GEO.dentro(d.estado, d.lon, d.lat)) {
      const real = GEO.estadoDe(d.lon, d.lat);
      return (err.textContent = real
        ? `Ese punto está en ${estadoPorId(real).nombre}, no en ${estadoPorId(d.estado).nombre}. Corrige el estado o las coordenadas.`
        : "Ese punto queda fuera del territorio nacional. Revisa latitud y longitud.");
    }
    if (!d.fecha) return (err.textContent = "Indica la fecha del hallazgo.");
    if (!(d.victimas >= 1)) return (err.textContent = "El número de víctimas debe ser 1 o más.");

    const f = REGISTRO.agregar(d);
    fosas = REGISTRO.todas();
    refrescarTodo();
    ok.textContent = `Fosa ${f.id} guardada. El mapa de probabilidad de ${estadoPorId(d.estado).nombre} ya la incluye.`;
    $("formFosa").reset(); $("fosaEstado").value = d.estado; $("fosaFecha").value = $("fosaFecha").max;
  });

  $("btnBorrarRegistros").addEventListener("click", () => {
    REGISTRO.borrarNuevas(); fosas = REGISTRO.todas(); refrescarTodo();
    $("fosaMsg").textContent = "Registros de prueba borrados.";
  });

  function pintarTablaNuevas() {
    const n = REGISTRO.nuevas();
    $("tablaNuevas").querySelector("tbody").innerHTML = n.length
      ? n.map((f) => `<tr><td>${f.id}</td><td>${estadoPorId(f.estado).nombre}</td><td>${f.municipio}</td>
          <td class="num">${f.lat.toFixed(4)}, ${f.lon.toFixed(4)}</td><td>${fechaLarga(f.fecha)}</td><td class="num">${f.victimas}</td></tr>`).join("")
      : `<tr><td colspan="6" class="vacio-tabla">Aún no registras fosas. Las que guardes aparecen aquí y en el mapa.</td></tr>`;
    $("btnBorrarRegistros").hidden = !n.length;
  }

  /* =========================================================
     RED DE GRUPOS
     ========================================================= */
  const mapaRed = new MapaMexico("mapaRed", { privado: true, neutro: true });
  mapaRed.capas = { calor: false, fosas: false, red: true, municipios: false };
  mapaRed.render();
  const red = GEODETEC.construirRed(ESTADOS_MX, GRUPOS_MOCK);
  $("leyendaGrupos").innerHTML = `<span class="leyenda-titulo">Grupos</span>` +
    GRUPOS_MOCK.map((g) => `<span><i style="background:${g.color}"></i>${g.nombre}</span>`).join("");
  const r = red.correlacion;
  const fuerza = Math.abs(r) >= 0.7 ? "fuerte" : Math.abs(r) >= 0.4 ? "moderada" : "débil";
  const ranking = [...ESTADOS_MX].sort((a, b) => red.presencia[b.id] - red.presencia[a.id] || b.fosas - a.fosas).slice(0, 8);
  $("detalleRed").innerHTML = `
    <h2>¿Influye la presencia de grupos?</h2>
    <div class="correlacion" style="--v:${Math.max(0, r)}">
      <strong>r = ${r.toFixed(2)}</strong>
      <span>Correlación ${fuerza} ${r >= 0 ? "positiva" : "negativa"} entre el número de grupos en un estado y sus fosas.</span>
    </div>
    <p class="ayuda">Pearson sobre los 32 estados. Correlación no implica causa: también influyen el terreno, la población y la capacidad de búsqueda.</p>
    <table class="tabla tabla-compacta">
      <thead><tr><th>Estado</th><th class="num">Grupos</th><th class="num">Conexiones</th><th class="num">Fosas</th></tr></thead>
      <tbody>${ranking.map((e) => `<tr><td>${e.nombre}</td><td class="num">${red.presencia[e.id]}</td><td class="num">${red.grado[e.id]}</td><td class="num">${e.fosas}</td></tr>`).join("")}</tbody>
    </table>`;

  /* =========================================================
     MODELO
     ========================================================= */
  GRAFICAS.barras($("graficaPesos"), [
    ["Registros históricos (RNPDNO)", 30], ["Frecuencia anual de reportes", 20], ["Proporción rural (vegetación)", 20],
    ["Baja densidad de población", 15], ["Accesibilidad intermedia", 10], ["Variación del terreno", 5],
  ].map(([etiqueta, valor]) => ({ etiqueta, valor, texto: valor + " %", color: "var(--tinta)" })));

  const M = [[37, 4, 0], [3, 35, 4], [0, 5, 37]], clases = ["Baja", "Media", "Alta"], maxM = 37;
  $("matrizConfusion").innerHTML = `
    <table class="matriz"><thead><tr><th></th>${clases.map((c) => `<th>${c}</th>`).join("")}</tr></thead>
    <tbody>${M.map((fila, i) => `<tr><th>${clases[i]}</th>${fila.map((v, j) =>
      `<td style="--a:${(v / maxM).toFixed(2)}" class="${i === j ? "diag" : ""}">${v}</td>`).join("")}</tr>`).join("")}</tbody></table>
    <p class="ayuda">109 de 125 municipios clasificados igual que la regla.</p>`;

  $("pruebaMunicipio").innerHTML = [...MUNICIPIOS_EDOMEX].sort((a, b) => a.municipio.localeCompare(b.municipio))
    .map((m) => `<option value="${m.cvegeo}">${m.municipio}</option>`).join("");
  $("pruebaMunicipio").addEventListener("change", probarModelo);
  function probarModelo() {
    const m = MUNICIPIOS_EDOMEX.find((x) => x.cvegeo === $("pruebaMunicipio").value);
    const p = GEODETEC.predecirMunicipio(m);
    $("pruebaResultado").innerHTML = `
      <div class="prueba">
        <dl class="datos datos-variables">
          <div><dt>Terreno</dt><dd>${m.terrain_index}</dd></div>
          <div><dt>Prop. rural</dt><dd>${m.vegetation_index}</dd></div>
          <div><dt>Densidad (hab/km²)</dt><dd>${fmt(m.population_density)}</dd></div>
          <div><dt>Accesibilidad</dt><dd>${m.accessibility_index}</dd></div>
          <div><dt>Registros RNPDNO</dt><dd>${m.historical_record_count}</dd></div>
          <div><dt>Reportes / 100 mil / año</dt><dd>${m.report_frequency}</dd></div>
        </dl>
        <div id="graficaProb"></div>
        <p>Puntaje ${p.puntaje} → clase <strong style="color:${GEODETEC.colorClase(p.clase)}">${p.clase_label}</strong></p>
      </div>`;
    GRAFICAS.barras($("graficaProb"), [
      { etiqueta: "P(baja)", valor: p.prob_baja, color: GEODETEC.colorClase(0), texto: Math.round(p.prob_baja * 100) + " %" },
      { etiqueta: "P(media)", valor: p.prob_media, color: GEODETEC.colorClase(1), texto: Math.round(p.prob_media * 100) + " %" },
      { etiqueta: "P(alta)", valor: p.prob_alta, color: GEODETEC.colorClase(2), texto: Math.round(p.prob_alta * 100) + " %" },
    ]);
  }

  /* ---------- Refresco general tras registrar ---------- */
  function refrescarTodo() {
    pintarResumen(); pintarTablaNuevas();
    mapa.setFosas(filtradas()); mapaReg.setFosas(fosas); mapaRed.setFosas(fosas);
    if (mapa.actual) pintarDetalle(estadoPorId(mapa.actual)); else pintarDetalleNacional();
  }

  refrescarTodo();
  calcularZona();
  probarModelo();
});
