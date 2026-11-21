/* ============================================================
   BUSCÁNDOTE · Gráficas SVG ligeras (sin librerías)
   ============================================================ */

const GRAFICAS = {
  /* Barras horizontales: [{ etiqueta, valor, color, texto? }] */
  barras(el, datos, { formato = (v) => v } = {}) {
    const max = Math.max(...datos.map((d) => d.valor)) || 1;
    el.innerHTML = `<ul class="g-barras">${datos.map((d) => `
      <li>
        <span class="g-etq">${d.etiqueta}</span>
        <span class="g-pista"><span class="g-barra" style="--w:${(d.valor / max) * 100}%;--c:${d.color || "var(--pino)"}"></span></span>
        <span class="g-val">${d.texto ?? formato(d.valor)}</span>
      </li>`).join("")}</ul>`;
  },

  /* Columnas verticales: perfil de distancia, etc. */
  columnas(el, etiquetas, valores, { color = "var(--pino)", sufijo = "" } = {}) {
    const max = Math.max(...valores) || 1;
    el.innerHTML = `<div class="g-columnas">${valores.map((v, i) => `
      <div class="g-col">
        <span class="g-col-val">${v}${sufijo}</span>
        <span class="g-col-barra" style="--h:${(v / max) * 100}%;--c:${color}"></span>
        <span class="g-col-etq">${etiquetas[i]}</span>
      </div>`).join("")}</div>`;
  },

  /* Línea con área: serie temporal [{ x: "2024", y: 12 }] */
  linea(el, serie, { color = "#12513f" } = {}) {
    const W = 560, H = 190, P = { l: 34, r: 10, t: 14, b: 26 };
    const max = Math.max(...serie.map((d) => d.y)) * 1.1 || 1;
    const x = (i) => P.l + (i * (W - P.l - P.r)) / Math.max(1, serie.length - 1);
    const y = (v) => H - P.b - (v / max) * (H - P.t - P.b);
    const pts = serie.map((d, i) => `${x(i).toFixed(1)},${y(d.y).toFixed(1)}`);
    const ticks = [0, 0.5, 1].map((k) => Math.round(max * k / 1.1));
    el.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" class="g-linea" role="img" aria-label="Serie temporal">
        ${ticks.map((t) => `<line x1="${P.l}" x2="${W - P.r}" y1="${y(t)}" y2="${y(t)}" class="g-rejilla"/>
          <text x="${P.l - 6}" y="${y(t) + 4}" text-anchor="end" class="g-eje">${t}</text>`).join("")}
        <polygon points="${P.l},${H - P.b} ${pts.join(" ")} ${x(serie.length - 1)},${H - P.b}" fill="${color}" fill-opacity="0.12"/>
        <polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="2.2" stroke-linejoin="round"/>
        ${serie.map((d, i) => `<circle cx="${x(i)}" cy="${y(d.y)}" r="3.2" fill="#fff" stroke="${color}" stroke-width="2"><title>${d.x}: ${d.y}</title></circle>
          <text x="${x(i)}" y="${H - 8}" text-anchor="middle" class="g-eje">${d.x}</text>`).join("")}
      </svg>`;
  },
};

/* Contador animado para KPIs (respeta prefers-reduced-motion) */
function animarNumero(el, destino, { decimales = 0, sufijo = "" } = {}) {
  const fmt = (v) => v.toLocaleString("es-MX", { minimumFractionDigits: decimales, maximumFractionDigits: decimales }) + sufijo;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = fmt(destino); return; }
  const t0 = performance.now(), dur = 900;
  const paso = (t) => {
    const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    el.textContent = fmt(destino * e);
    if (k < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}
