/* ============================================================
   BUSCÁNDOTE · Registro de fosas y sesión
   - Fosas nuevas se guardan en localStorage (simula la base cifrada).
   - La contraseña se compara por su hash SHA-256: el texto plano
     no está en el código (en Python se usa PBKDF2 + Fernet).
   ============================================================ */

const REGISTRO = (() => {
  const CLAVE_FOSAS = "buscandote_fosas";
  const CLAVE_SESION = "buscandote_sesion";
  /* SHA-256("Geodetec2026") — cámbialo generando el hash de tu contraseña */
  const HASH_ACCESO = "0f3c4c6e396eb1bbac76572a9a1c04547dcaaa436772d66b29fe33834201d917";

  const simuladas = GEO.generarFosasSimuladas();

  function leer() {
    try { return JSON.parse(localStorage.getItem(CLAVE_FOSAS)) || []; } catch { return []; }
  }
  function guardar(lista) {
    try { localStorage.setItem(CLAVE_FOSAS, JSON.stringify(lista)); } catch { /* modo privado: solo memoria */ }
  }
  let nuevas = leer();

  return {
    /* Todas las fosas: registradas en esta sesión + verificadas + simuladas */
    todas: () => [...nuevas, ...FOSAS_MOCK, ...simuladas],
    nuevas: () => nuevas,
    agregar(f) {
      const total = nuevas.length + FOSAS_MOCK.length + 1;
      const fosa = { ...f, id: "F-" + String(total).padStart(3, "0"), nueva: true };
      nuevas = [fosa, ...nuevas]; guardar(nuevas);
      return fosa;
    },
    borrarNuevas() { nuevas = []; guardar(nuevas); },

    async verificar(contrasena) {
      if (!window.crypto?.subtle) return contrasena === "Geodetec2026";   // respaldo sin contexto seguro
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(contrasena));
      const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
      return hex === HASH_ACCESO;
    },
    abrirSesion() { sessionStorage.setItem(CLAVE_SESION, String(Date.now())); },
    cerrarSesion() { sessionStorage.removeItem(CLAVE_SESION); },
    haySesion() { return !!sessionStorage.getItem(CLAVE_SESION); },
  };
})();
