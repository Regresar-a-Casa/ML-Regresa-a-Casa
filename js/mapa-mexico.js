/* ============================================================
   BUSCÁNDOTE · Mapa SVG de la República con límites estatales reales
   ------------------------------------------------------------
   new MapaMexico(contenedor, opciones)
     opciones.privado    true  → muestra fosas, calor, red y municipios
     opciones.onEstado   (estado) al entrar a un estado
     opciones.onPunto    (lon, lat, idEstado) clic dentro del estado abierto
     opciones.onNacional () al volver a la vista nacional
   Métodos: irA(id|null), setFosas(arr), setCapa(nombre, bool),
            marcarPunto(lon, lat), resaltarMunicipios([cvegeo])
   ============================================================ */

class MapaMexico {
  constructor(contenedor, opciones = {}) {
    this.el = typeof contenedor === "string" ? document.getElementById(contenedor) : contenedor;
    this.op = opciones;
    this.privado = !!opciones.privado;
    this.fosas = [];
    this.capas = { calor: true, fosas: true, red: false, municipios: true };
    this.actual = null;              // id del estado abierto (null = nacional)
    this.pin = null;
    this.resaltados = new Set();
    this.reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const b = GEO.bboxNacional();
    const [x0, y0] = GEO.proyectar(b.lonMin, b.latMax), [x1, y1] = GEO.proyectar(b.lonMax, b.latMin);
    this.vbNacional = this._margen([x0, y0, x1 - x0, y1 - y0], 0.03);
    this.vb = [...this.vbNacional];
    this._construir();
  }

  /* ---------- Estructura ---------- */
  _construir() {
    this.el.classList.add("mapa");
    if (!this.privado) this.el.classList.add("publico");
    if (this.op.neutro) this.el.classList.add("neutro");
    this.el.innerHTML = `
      <div class="mapa-barra">
        <nav class="mapa-ruta" aria-label="Ubicación en el mapa">
          <button type="button" class="ruta-nacional">República Mexicana</button>
          <span class="ruta-estado" hidden></span>
        </nav>
        <button type="button" class="mapa-volver" hidden>Volver al país</button>
      </div>
      <svg class="mapa-svg" role="img" aria-label="Mapa de México por estado" preserveAspectRatio="xMidYMid meet">
        <g class="capa-estados"></g><g class="capa-calor"></g><g class="capa-bordes"></g>
        <g class="capa-red"></g><g class="capa-municipios"></g><g class="capa-fosas"></g>
        <g class="capa-etiquetas"></g><g class="capa-pin"></g>
      </svg>
      <div class="mapa-tooltip" role="status" hidden></div>`;
    this.svg = this.el.querySelector("svg");
    this.g = {};
    ["estados", "calor", "bordes", "red", "municipios", "fosas", "etiquetas", "pin"]
      .forEach((n) => (this.g[n] = this.svg.querySelector(".capa-" + n)));
    this.tip = this.el.querySelector(".mapa-tooltip");

    /* Polígonos de los 32 estados */
    const NS = "http://www.w3.org/2000/svg";
    ESTADOS_MX.forEach((e) => {
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", GEO.caminoSVG(e.id));
      p.setAttribute("class", "estado");
      p.setAttribute("data-id", e.id);
      p.setAttribute("tabindex", "0");
      p.setAttribute("aria-label", `${e.nombre}, prioridad ${Math.round(e.prioridad * 100)} %`);
      p.style.setProperty("--relleno", GEODETEC.colorPrioridad(e.prioridad));
      this.g.estados.appendChild(p);
    });
    /* Bordes encima del calor para que la separación entre estados siempre se vea */
    this.g.bordes.innerHTML = ESTADOS_MX.map((e) => `<path class="borde" data-id="${e.id}" d="${GEO.caminoSVG(e.id)}"/>`).join("");

    this._eventos();
    this._aplicarViewBox();
    this.render();
  }

  _eventos() {
    /* Un solo manejador: las capas (calor, fosas, municipios) no deben "tapar" el clic */
    this.svg.addEventListener("click", (ev) => {
      const t = ev.target;
      const [lon, lat] = this._coordsEvento(ev);
      let id = t.classList.contains("estado") ? t.dataset.id : null;
      if (t.classList.contains("fosa")) id = this.fosas.find((f) => f.id === t.dataset.id)?.estado;
      if (!id && t.closest("g") && t.closest("g") !== this.g.estados) id = this.actual || GEO.estadoDe(lon, lat);
      if (!id) return;
      if (this.actual === id) {
        if (this.op.onPunto) this.op.onPunto(+lon.toFixed(4), +lat.toFixed(4), id);
      } else this.irA(id);
    });
    this.g.estados.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); this.irA(ev.target.dataset.id); }
    });
    this.svg.addEventListener("mousemove", (ev) => this._tooltip(ev));
    this.svg.addEventListener("mouseleave", () => (this.tip.hidden = true));
    this.el.querySelector(".mapa-volver").addEventListener("click", () => this.irA(null));
    this.el.querySelector(".ruta-nacional").addEventListener("click", () => this.irA(null));
  }

  _coordsEvento(ev) {
    const pt = this.svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const loc = pt.matrixTransform(this.svg.getScreenCTM().inverse());
    return GEO.desproyectar(loc.x, loc.y);
  }

  _tooltip(ev) {
    const t = ev.target;
    let html = "";
    if (t.classList.contains("fosa")) {
      const f = this.fosas.find((x) => x.id === t.dataset.id);
      if (f) html = `<strong>Fosa ${f.id}</strong><br>${f.municipio}<br>${f.fecha} · ${f.victimas} víctimas<br>${f.estado_proc}`;
    } else if (t.classList.contains("celda")) {
      html = `<strong>Probabilidad estimada ${Math.round(t.dataset.v * 100)} %</strong><br>Celda de ≈${t.dataset.km} km`;
    } else if (t.classList.contains("municipio")) {
      html = `<strong>${t.dataset.nombre}</strong><br>P(prioridad alta) ${Math.round(t.dataset.p * 100)} %`;
    } else if (t.classList.contains("estado")) {
      const e = ESTADOS_MX.find((x) => x.id === t.dataset.id);
      html = `<strong>${e.nombre}</strong><br>Prioridad ${Math.round(e.prioridad * 100)} % · ${GEODETEC.ETIQUETAS_PRIORIDAD[GEODETEC.nivelPrioridad(e.prioridad)]}`;
      if (this.privado) html += `<br>${this.fosas.filter((f) => f.estado === e.id).length} fosas registradas`;
      if (this.actual === e.id && this.op.onPunto) html += `<br><em>Clic para usar este punto</em>`;
    }
    if (!html) { this.tip.hidden = true; return; }
    const r = this.el.getBoundingClientRect();
    this.tip.innerHTML = html;
    this.tip.hidden = false;
    const x = Math.min(ev.clientX - r.left + 14, r.width - this.tip.offsetWidth - 8);
    this.tip.style.transform = `translate(${x}px, ${ev.clientY - r.top + 14}px)`;
  }

  /* ---------- Navegación ---------- */
  irA(id, { animar = true } = {}) {
    if (id === this.actual) return;
    this.actual = id;
    const destino = id ? this._vbEstado(id) : this.vbNacional;
    this.el.classList.toggle("en-estado", !!id);
    this.g.estados.querySelectorAll(".estado").forEach((p) => p.classList.toggle("activo", p.dataset.id === id));
    this.g.bordes.querySelectorAll(".borde").forEach((p) => p.classList.toggle("activo", p.dataset.id === id));
    const ruta = this.el.querySelector(".ruta-estado");
    ruta.hidden = !id;
    if (id) ruta.textContent = ESTADOS_MX.find((e) => e.id === id).nombre;
    this.el.querySelector(".mapa-volver").hidden = !id;
    this.pin = null; this.resaltados.clear();
    this.g.calor.innerHTML = this.g.fosas.innerHTML = this.g.municipios.innerHTML = this.g.pin.innerHTML = "";
    this._animar(destino, () => this.render(), animar);
    if (id && this.op.onEstado) this.op.onEstado(ESTADOS_MX.find((e) => e.id === id));
    if (!id && this.op.onNacional) this.op.onNacional();
  }

  _vbEstado(id) {
    const b = GEO.bbox(id);
    const [x0, y0] = GEO.proyectar(b.lonMin, b.latMax), [x1, y1] = GEO.proyectar(b.lonMax, b.latMin);
    let w = x1 - x0, h = y1 - y0;
    /* respetar la proporción del lienzo nacional para que no se deforme el encuadre */
    const ar = this.vbNacional[2] / this.vbNacional[3];
    if (w / h < ar) { const nw = h * ar; return this._margen([x0 - (nw - w) / 2, y0, nw, h], 0.08); }
    const nh = w / ar; return this._margen([x0, y0 - (nh - h) / 2, w, nh], 0.08);
  }

  _margen([x, y, w, h], m) { return [x - w * m, y - h * m, w * (1 + 2 * m), h * (1 + 2 * m)]; }

  _animar(destino, fin, animar = true) {
    if (!animar || this.reducirMovimiento) { this.vb = [...destino]; this._aplicarViewBox(); fin && fin(); return; }
    const ini = [...this.vb], t0 = performance.now(), dur = 520;
    const paso = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;   // ease-in-out cúbico
      this.vb = ini.map((v, i) => v + (destino[i] - v) * e);
      this._aplicarViewBox();
      if (k < 1) requestAnimationFrame(paso); else fin && fin();
    };
    requestAnimationFrame(paso);
  }

  _aplicarViewBox() { this.svg.setAttribute("viewBox", this.vb.map((v) => v.toFixed(2)).join(" ")); }

  /* ---------- Capas ---------- */
  setFosas(f) { this.fosas = f; this.render(); }
  setCapa(n, v) { this.capas[n] = v; this.render(); }
  marcarPunto(lon, lat) { this.pin = [lon, lat]; this._renderPin(); }
  resaltarMunicipios(cves) { this.resaltados = new Set(cves); this._renderMunicipios(); }

  render() {
    const u = this.vb[2] / 100;      // unidad relativa al zoom actual
    this.u = u;
    this._renderEtiquetas();
    this._renderCalor();
    this._renderRed();
    this._renderMunicipios();
    this._renderFosas();
    this._renderPin();
  }

  _renderEtiquetas() {
    const u = this.u, ocultar = ["09", "29", "17", "01", "06"];
    if (this.actual) { this.g.etiquetas.innerHTML = ""; return; }
    this.g.etiquetas.innerHTML = ESTADOS_MX.filter((e) => !ocultar.includes(e.id)).map((e) => {
      const [x, y] = GEO.proyectar(...GEO.centroide(e.id));
      return `<text x="${x}" y="${y}" font-size="${(u * 1.45).toFixed(2)}">${e.abrev}</text>`;
    }).join("");
  }

  _renderCalor() {
    this.g.calor.innerHTML = "";
    if (!this.privado || !this.actual || !this.capas.calor) return;
    const e = ESTADOS_MX.find((x) => x.id === this.actual);
    const celdas = GEO.densidad(e.id, this.fosas, e.prioridad);
    this.celdas = celdas;
    this.g.calor.innerHTML = celdas.filter((c) => c.valor > 0.06).map((c) => {
      const [x, y] = GEO.proyectar(c.lon - c.paso / 2, c.lat + c.paso / 2);
      const [x2, y2] = GEO.proyectar(c.lon + c.paso / 2, c.lat - c.paso / 2);
      const km = Math.round(c.paso * 111);
      return `<rect class="celda" x="${x}" y="${y}" width="${x2 - x + 0.02}" height="${y2 - y + 0.02}"
        fill="${MapaMexico.colorCalor(c.valor)}" fill-opacity="${(0.2 + 0.7 * c.valor).toFixed(2)}"
        data-v="${c.valor.toFixed(3)}" data-km="${km}"/>`;
    }).join("");
  }

  _renderRed() {
    this.g.red.innerHTML = "";
    if (!this.privado || this.actual || !this.capas.red) return;
    const red = GEODETEC.construirRed(ESTADOS_MX, GRUPOS_MOCK), u = this.u;
    const color = (g) => GRUPOS_MOCK.find((x) => x.id === g).color;
    const lineas = red.aristas.map((a) => {
      const [x1, y1] = GEO.proyectar(...GEO.centroide(a.a)), [x2, y2] = GEO.proyectar(...GEO.centroide(a.b));
      return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color(a.grupos[0])}"
        stroke-width="${(u * 0.28 * a.peso).toFixed(2)}" stroke-opacity="0.8"/>`;
    }).join("");
    const nodos = ESTADOS_MX.filter((e) => red.presencia[e.id] > 0).map((e) => {
      const [x, y] = GEO.proyectar(...GEO.centroide(e.id));
      return `<circle cx="${x}" cy="${y}" r="${(u * (0.5 + 0.35 * red.presencia[e.id])).toFixed(2)}" class="nodo"/>`;
    }).join("");
    this.g.red.innerHTML = lineas + nodos;
  }

  _renderMunicipios() {
    this.g.municipios.innerHTML = "";
    if (!(this.privado || this.op.municipios) || this.actual !== "15" || !this.capas.municipios) return;
    const u = this.u;
    this.g.municipios.innerHTML = MUNICIPIOS_EDOMEX.map((m) => {
      const p = GEODETEC.predecirMunicipio(m);
      const [x, y] = GEO.proyectar(m.lon, m.lat);
      const res = this.resaltados.has(m.cvegeo);
      return `<circle class="municipio${res ? " resaltado" : ""}" cx="${x}" cy="${y}" r="${(u * (res ? 1.3 : 0.85)).toFixed(2)}"
        fill="${GEODETEC.colorClase(p.clase)}" data-nombre="${m.municipio}" data-p="${p.prob_alta}"/>`;
    }).join("");
  }

  _renderFosas() {
    this.g.fosas.innerHTML = "";
    if (!this.privado || !this.capas.fosas) return;
    const u = this.u, lista = this.actual ? this.fosas.filter((f) => f.estado === this.actual) : this.fosas;
    const r = this.actual ? u * 0.75 : u * 0.42;
    this.g.fosas.innerHTML = lista.map((f) => {
      const [x, y] = GEO.proyectar(f.lon, f.lat);
      return `<circle class="fosa${f.simulada ? "" : " verificada"}" cx="${x}" cy="${y}" r="${r.toFixed(2)}" data-id="${f.id}"/>`;
    }).join("");
  }

  _renderPin() {
    this.g.pin.innerHTML = "";
    if (!this.pin) return;
    const [x, y] = GEO.proyectar(...this.pin), u = this.u;
    this.g.pin.innerHTML = `<circle class="pin-halo" cx="${x}" cy="${y}" r="${u * 2.6}"/>
      <circle class="pin" cx="${x}" cy="${y}" r="${u * 1.1}"/>`;
  }

  /* Rampa del mapa de calor: arena → ámbar → naranja → rojo profundo */
  static colorCalor(v) {
    const stops = [[0, [246, 226, 160]], [0.35, [238, 168, 76]], [0.7, [218, 92, 58]], [1, [158, 38, 46]]];
    for (let i = 1; i < stops.length; i++) if (v <= stops[i][0]) {
      const [a, ca] = stops[i - 1], [b, cb] = stops[i], t = (v - a) / (b - a);
      return `rgb(${ca.map((c, k) => Math.round(c + (cb[k] - c) * t)).join(",")})`;
    }
    return "rgb(158,38,46)";
  }
}
