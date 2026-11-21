/* ============================================================
   BUSCÁNDOTE · Página pública (index.html)
   Mapa nacional, consulta por folio, contacto y acceso.
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);
  const nombreEstado = (id) => ESTADOS_MX.find((e) => e.id === id)?.nombre || "";
  const etiqueta = (p) => GEODETEC.ETIQUETAS_PRIORIDAD[GEODETEC.nivelPrioridad(p)];

  /* ---------- Menú móvil ---------- */
  const nav = $("navPrincipal"), btnMenu = $("btnMenu");
  btnMenu.addEventListener("click", () => {
    const abierto = nav.classList.toggle("abierto");
    btnMenu.setAttribute("aria-expanded", abierto);
  });
  nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => nav.classList.remove("abierto")));

  /* ---------- Cifras del hero ---------- */
  animarNumero($("cifraPersonas"), KPIS_NACIONALES.personas_desaparecidas);
  animarNumero($("cifraFosas"), KPIS_NACIONALES.fosas_registradas);
  animarNumero($("cifraModelo"), KPIS_NACIONALES.precision_modelo * 100, { decimales: 1, sufijo: " %" });

  /* ---------- Mapa público (sin fosas: solo prioridad por estado) ---------- */
  const ficha = $("fichaEstado");
  const mapa = new MapaMexico("mapaPublico", {
    onEstado: (e) => {
      ficha.innerHTML = `
        <div class="ficha-fila">
          <div>
            <h3>${e.nombre}</h3>
            <p><span class="punto" style="background:${GEODETEC.colorPrioridad(e.prioridad)}"></span>
              Prioridad ${etiqueta(e.prioridad).toLowerCase()} (${Math.round(e.prioridad * 100)} %) ·
              ${e.personas.toLocaleString("es-MX")} reportes en la muestra</p>
          </div>
          <button type="button" class="boton boton-pino boton-chico" id="btnConsultarEstado">Consultar aquí</button>
        </div>`;
      $("btnConsultarEstado").addEventListener("click", () => {
        $("consultaEstado").value = e.id;
        $("consulta").scrollIntoView({ behavior: "smooth" });
        $("consultaFolio").focus({ preventScroll: true });
      });
    },
    onNacional: () => (ficha.innerHTML = `<p>Toca un estado para ver su nivel de prioridad y consultar un folio ahí.</p>`),
  });

  /* ---------- Consulta por folio ---------- */
  $("consultaEstado").innerHTML += ESTADOS_MX.map((e) => `<option value="${e.id}">${e.nombre}</option>`).join("");
  const res = $("consultaResultado"), err = $("consultaError");

  $("formConsulta").addEventListener("submit", (ev) => {
    ev.preventDefault();
    err.textContent = "";
    const folio = $("consultaFolio").value.trim().toUpperCase();
    const sexo = document.querySelector('input[name="sexo"]:checked')?.value;
    const estadoSel = $("consultaEstado").value;

    if (!sexo) { err.textContent = "Elige el sexo registrado en el acta."; return; }
    if (!folio) { err.textContent = "Escribe el folio del acta, por ejemplo GD-2024-001."; $("consultaFolio").focus(); return; }

    const p = PERSONAS_MOCK.find((x) => x.folio === folio);
    if (!p) return mostrarSinRegistro(folio);
    if (p.sexo !== sexo) { err.textContent = "El folio existe, pero el sexo no coincide con el del acta. Revisa ambos datos."; return; }
    if (estadoSel && estadoSel !== p.estado) {
      err.textContent = `Ese folio está registrado en ${nombreEstado(p.estado)}, no en ${nombreEstado(estadoSel)}.`; return;
    }
    mostrarResultado(p, $("consultaEdad").value || rangoEdad(p.edad));
  });

  const rangoEdad = (e) => (e < 18 ? "0-17" : e < 30 ? "18-29" : e < 60 ? "30-59" : "60+");

  function mostrarSinRegistro(folio) {
    res.innerHTML = `
      <div class="panel resultado">
        <h3>No hay un registro activo con el folio ${folio}</h3>
        <p>Revisa que el folio esté escrito como aparece en el acta. Si acabas de levantar el reporte,
          puede tardar en aparecer. Confirma tu folio con la Comisión Nacional de Búsqueda:
          <a href="tel:8000287783">800 028 77 83</a>.</p>
      </div>`;
  }

  function mostrarResultado(p, edad) {
    const estado = ESTADOS_MX.find((e) => e.id === p.estado);
    const mun = MUNICIPIOS_EDOMEX.find((m) => m.municipio === p.municipio);
    let bloqueZona, cvesZona = [];

    if (mun) {
      const pred = GEODETEC.predecirMunicipio(mun);
      const zona = GEODETEC.zonaBusqueda(p.lat, p.lon, MUNICIPIOS_EDOMEX).filter((z) => z.en_zona);
      cvesZona = zona.map((z) => z.cvegeo);
      bloqueZona = `
        <div class="resultado-prioridad" style="--c:${GEODETEC.colorClase(pred.clase)}">
          <span>Prioridad del municipio</span>
          <strong>${pred.clase_label}</strong>
          <small>P(prioridad alta) ${(pred.prob_alta * 100).toFixed(0)} %</small>
        </div>
        <h4>Recorrer primero</h4>
        <ol class="lista-zona">${zona.map((z) => `
          <li><span>${z.municipio}</span><span>${z.distancia_km} km</span>
            <span class="punto" style="background:${GEODETEC.colorClase(z.clase)}" title="${z.clase_label}"></span></li>`).join("")}
        </ol>`;
    } else {
      bloqueZona = `
        <div class="resultado-prioridad" style="--c:${GEODETEC.colorPrioridad(estado.prioridad)}">
          <span>Prioridad del estado</span>
          <strong>${etiqueta(estado.prioridad)}</strong>
          <small>${Math.round(estado.prioridad * 100)} % según el modelo agregado</small>
        </div>
        <p class="ayuda">El modelo municipal solo está entrenado para el Estado de México.
          Para ${estado.nombre} mostramos la prioridad estatal.</p>`;
    }

    const perfil = PERFIL_LOCALIZACION[p.sexo][edad];
    res.innerHTML = `
      <div class="panel resultado">
        <header class="resultado-cabeza">
          <div>
            <p class="folio">Folio ${p.folio}</p>
            <h3>Última ubicación: ${p.municipio}, ${estado.nombre}</h3>
          </div>
          <span class="desde">Desde ${new Date(p.fecha + "T12:00").toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" })}</span>
        </header>
        <div class="resultado-cuerpo">
          <div>${bloqueZona}</div>
          <div class="mini-mapa" id="miniMapa"></div>
        </div>
        <h4>Dónde se localizó a personas con un perfil parecido</h4>
        <p class="ayuda">${p.sexo === "Mujer" ? "Mujeres" : "Hombres"} de ${edad.replace("-", " a ").replace("+", " o más")} años.
          Porcentaje según la distancia al último punto conocido (datos simulados).</p>
        <div id="graficaPerfil"></div>
        <p class="aviso">Por seguridad no mostramos datos personales. Para información completa del caso,
          acude a la fiscalía o a la comisión de búsqueda de tu estado.</p>
      </div>`;

    GRAFICAS.columnas($("graficaPerfil"), RANGOS_DISTANCIA, perfil, { sufijo: " %" });
    const mini = new MapaMexico("miniMapa", { municipios: true });
    mini.irA(p.estado, { animar: false });
    mini.marcarPunto(p.lon, p.lat);
    mini.resaltarMunicipios(cvesZona);
    res.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /* ---------- Contactos ---------- */
  $("listaContactos").innerHTML = CONTACTOS.map((c) => `
    <li><a href="tel:${c.tel.replace(/\s/g, "")}">
      <span class="c-nombre">${c.nombre}</span>
      <span class="c-tel">${c.tel}</span>
      <span class="c-nota">${c.nota}</span>
    </a></li>`).join("");

  /* ---------- Modal de acceso ---------- */
  const modal = $("modalLogin"), input = $("inputPassword"), loginError = $("loginError");
  let ultimoFoco = null;
  const abrir = () => { ultimoFoco = document.activeElement; modal.hidden = false; input.focus(); };
  const cerrar = () => { modal.hidden = true; loginError.textContent = ""; ultimoFoco?.focus(); };
  $("btnAbrirLogin").addEventListener("click", abrir);
  $("btnHeroLogin").addEventListener("click", abrir);
  $("btnCerrarLogin").addEventListener("click", cerrar);
  modal.addEventListener("click", (e) => { if (e.target === modal) cerrar(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modal.hidden) cerrar(); });

  $("formLogin").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("btnIngresar");
    btn.disabled = true; btn.textContent = "Verificando…";
    const ok = await REGISTRO.verificar(input.value);
    if (ok) {
      REGISTRO.abrirSesion();
      btn.textContent = "Acceso concedido";
      window.location.href = "dashboard.html";
    } else {
      btn.disabled = false; btn.textContent = "Entrar";
      loginError.textContent = "La contraseña no es correcta. Pídela a la coordinación de tu colectivo.";
      input.value = ""; input.focus();
      modal.querySelector(".modal").classList.remove("sacudir"); void modal.offsetWidth;
      modal.querySelector(".modal").classList.add("sacudir");
    }
  });
});
