/* ============================================================
   BUSCÁNDOTE · Datos simulados
   ------------------------------------------------------------
   Todo lo que hay aquí es SIMULADO salvo las 6 variables de los
   municipios del Edomex, que vienen de GEODETEC_edomex.py
   (INEGI 2020 / RNPDNO). Las personas son ficticias.
   ============================================================ */

/* --- 32 entidades (clave INEGI). prioridad = salida agregada del modelo (0–1) --- */
const ESTADOS_MX = [
  { id: "01", nombre: "Aguascalientes",      abrev: "AGS",  prioridad: 0.31, fosas: 4,  personas: 128  },
  { id: "02", nombre: "Baja California",     abrev: "BC",   prioridad: 0.62, fosas: 18, personas: 642  },
  { id: "03", nombre: "Baja California Sur", abrev: "BCS",  prioridad: 0.22, fosas: 2,  personas: 74   },
  { id: "04", nombre: "Campeche",            abrev: "CAMP", prioridad: 0.28, fosas: 3,  personas: 91   },
  { id: "05", nombre: "Coahuila",            abrev: "COAH", prioridad: 0.71, fosas: 26, personas: 890  },
  { id: "06", nombre: "Colima",              abrev: "COL",  prioridad: 0.55, fosas: 11, personas: 312  },
  { id: "07", nombre: "Chiapas",             abrev: "CHIS", prioridad: 0.48, fosas: 8,  personas: 245  },
  { id: "08", nombre: "Chihuahua",           abrev: "CHIH", prioridad: 0.78, fosas: 34, personas: 1120 },
  { id: "09", nombre: "Ciudad de México",    abrev: "CDMX", prioridad: 0.52, fosas: 6,  personas: 380  },
  { id: "10", nombre: "Durango",             abrev: "DGO",  prioridad: 0.58, fosas: 14, personas: 410  },
  { id: "11", nombre: "Guanajuato",          abrev: "GTO",  prioridad: 0.74, fosas: 29, personas: 980  },
  { id: "12", nombre: "Guerrero",            abrev: "GRO",  prioridad: 0.81, fosas: 41, personas: 1340 },
  { id: "13", nombre: "Hidalgo",             abrev: "HGO",  prioridad: 0.44, fosas: 7,  personas: 210  },
  { id: "14", nombre: "Jalisco",             abrev: "JAL",  prioridad: 0.83, fosas: 47, personas: 1580 },
  { id: "15", nombre: "Estado de México",    abrev: "MEX",  prioridad: 0.69, fosas: 22, personas: 760  },
  { id: "16", nombre: "Michoacán",           abrev: "MICH", prioridad: 0.72, fosas: 24, personas: 870  },
  { id: "17", nombre: "Morelos",             abrev: "MOR",  prioridad: 0.46, fosas: 5,  personas: 165  },
  { id: "18", nombre: "Nayarit",             abrev: "NAY",  prioridad: 0.51, fosas: 9,  personas: 240  },
  { id: "19", nombre: "Nuevo León",          abrev: "NL",   prioridad: 0.64, fosas: 17, personas: 520  },
  { id: "20", nombre: "Oaxaca",              abrev: "OAX",  prioridad: 0.42, fosas: 6,  personas: 190  },
  { id: "21", nombre: "Puebla",              abrev: "PUE",  prioridad: 0.57, fosas: 13, personas: 400  },
  { id: "22", nombre: "Querétaro",           abrev: "QRO",  prioridad: 0.34, fosas: 3,  personas: 110  },
  { id: "23", nombre: "Quintana Roo",        abrev: "QROO", prioridad: 0.39, fosas: 4,  personas: 145  },
  { id: "24", nombre: "San Luis Potosí",     abrev: "SLP",  prioridad: 0.53, fosas: 10, personas: 290  },
  { id: "25", nombre: "Sinaloa",             abrev: "SIN",  prioridad: 0.76, fosas: 31, personas: 1050 },
  { id: "26", nombre: "Sonora",              abrev: "SON",  prioridad: 0.67, fosas: 20, personas: 610  },
  { id: "27", nombre: "Tabasco",             abrev: "TAB",  prioridad: 0.41, fosas: 5,  personas: 175  },
  { id: "28", nombre: "Tamaulipas",          abrev: "TAMS", prioridad: 0.79, fosas: 37, personas: 1180 },
  { id: "29", nombre: "Tlaxcala",            abrev: "TLAX", prioridad: 0.30, fosas: 2,  personas: 85   },
  { id: "30", nombre: "Veracruz",            abrev: "VER",  prioridad: 0.75, fosas: 28, personas: 940  },
  { id: "31", nombre: "Yucatán",             abrev: "YUC",  prioridad: 0.24, fosas: 1,  personas: 60   },
  { id: "32", nombre: "Zacatecas",           abrev: "ZAC",  prioridad: 0.61, fosas: 15, personas: 430  },
];

/* --- Subconjunto representativo de municipios del Edomex (del GeoJSON real) ---
   Las 6 variables provienen de tus datos reales (INEGI/RNPDNO). --- */
const MUNICIPIOS_EDOMEX = [
  { cvegeo: "15001", municipio: "Acambay",            lat: 19.95, lon: -99.84, terrain_index: 0.74, vegetation_index: 0.62, population_density: 68.4,  accessibility_index: 0.42, historical_record_count: 12, report_frequency: 3.1 },
  { cvegeo: "15002", municipio: "Acolman",            lat: 19.63, lon: -98.91, terrain_index: 0.38, vegetation_index: 0.31, population_density: 1240,  accessibility_index: 0.86, historical_record_count: 38, report_frequency: 5.2 },
  { cvegeo: "15006", municipio: "Almoloya de Juárez", lat: 19.37, lon: -99.76, terrain_index: 0.52, vegetation_index: 0.58, population_density: 245,   accessibility_index: 0.61, historical_record_count: 27, report_frequency: 4.8 },
  { cvegeo: "15009", municipio: "Atizapán",           lat: 19.56, lon: -99.26, terrain_index: 0.28, vegetation_index: 0.22, population_density: 4800,  accessibility_index: 0.94, historical_record_count: 52, report_frequency: 6.1 },
  { cvegeo: "15013", municipio: "Atlacomulco",        lat: 19.80, lon: -99.87, terrain_index: 0.45, vegetation_index: 0.51, population_density: 380,   accessibility_index: 0.55, historical_record_count: 31, report_frequency: 5.4 },
  { cvegeo: "15020", municipio: "Chalco",             lat: 19.26, lon: -98.90, terrain_index: 0.33, vegetation_index: 0.34, population_density: 3100,  accessibility_index: 0.81, historical_record_count: 68, report_frequency: 7.3 },
  { cvegeo: "15024", municipio: "Chimalhuacán",       lat: 19.42, lon: -98.95, terrain_index: 0.21, vegetation_index: 0.18, population_density: 13500, accessibility_index: 0.88, historical_record_count: 74, report_frequency: 7.9 },
  { cvegeo: "15028", municipio: "Coacalco",           lat: 19.63, lon: -99.10, terrain_index: 0.18, vegetation_index: 0.15, population_density: 9800,  accessibility_index: 0.92, historical_record_count: 45, report_frequency: 6.4 },
  { cvegeo: "15031", municipio: "Cuautitlán",         lat: 19.67, lon: -99.18, terrain_index: 0.24, vegetation_index: 0.24, population_density: 4200,  accessibility_index: 0.90, historical_record_count: 39, report_frequency: 5.8 },
  { cvegeo: "15033", municipio: "Cuautitlán Izcalli", lat: 19.65, lon: -99.21, terrain_index: 0.19, vegetation_index: 0.20, population_density: 5200,  accessibility_index: 0.91, historical_record_count: 41, report_frequency: 6.0 },
  { cvegeo: "15035", municipio: "Ecatepec",           lat: 19.60, lon: -99.05, terrain_index: 0.16, vegetation_index: 0.12, population_density: 11200, accessibility_index: 0.93, historical_record_count: 121,report_frequency: 8.4 },
  { cvegeo: "15037", municipio: "El Oro",             lat: 19.80, lon: -100.13,terrain_index: 0.61, vegetation_index: 0.68, population_density: 95,    accessibility_index: 0.38, historical_record_count: 14, report_frequency: 3.3 },
  { cvegeo: "15039", municipio: "Huehuetoca",         lat: 19.83, lon: -99.20, terrain_index: 0.29, vegetation_index: 0.36, population_density: 680,   accessibility_index: 0.72, historical_record_count: 22, report_frequency: 4.5 },
  { cvegeo: "15044", municipio: "Ixtapaluca",         lat: 19.32, lon: -98.88, terrain_index: 0.35, vegetation_index: 0.31, population_density: 2900,  accessibility_index: 0.80, historical_record_count: 58, report_frequency: 6.8 },
  { cvegeo: "15046", municipio: "Jilotepec",          lat: 19.95, lon: -99.53, terrain_index: 0.55, vegetation_index: 0.60, population_density: 180,   accessibility_index: 0.47, historical_record_count: 19, report_frequency: 4.0 },
  { cvegeo: "15053", municipio: "Lerma",              lat: 19.29, lon: -99.51, terrain_index: 0.31, vegetation_index: 0.35, population_density: 1100,  accessibility_index: 0.75, historical_record_count: 26, report_frequency: 4.9 },
  { cvegeo: "15057", municipio: "Metepec",            lat: 19.25, lon: -99.60, terrain_index: 0.22, vegetation_index: 0.24, population_density: 3800,  accessibility_index: 0.89, historical_record_count: 33, report_frequency: 5.5 },
  { cvegeo: "15058", municipio: "Mexicaltzingo",      lat: 19.21, lon: -99.59, terrain_index: 0.20, vegetation_index: 0.25, population_density: 2400,  accessibility_index: 0.87, historical_record_count: 18, report_frequency: 4.7 },
  { cvegeo: "15059", municipio: "Morelos",            lat: 19.75, lon: -99.67, terrain_index: 0.40, vegetation_index: 0.55, population_density: 310,   accessibility_index: 0.52, historical_record_count: 21, report_frequency: 4.3 },
  { cvegeo: "15060", municipio: "Naucalpan",          lat: 19.48, lon: -99.24, terrain_index: 0.17, vegetation_index: 0.14, population_density: 8900,  accessibility_index: 0.95, historical_record_count: 86, report_frequency: 7.6 },
  { cvegeo: "15062", municipio: "Nezahualcóyotl",     lat: 19.40, lon: -99.02, terrain_index: 0.12, vegetation_index: 0.08, population_density: 17800, accessibility_index: 0.91, historical_record_count: 134,report_frequency: 8.9 },
  { cvegeo: "15065", municipio: "Nicolás Romero",     lat: 19.62, lon: -99.32, terrain_index: 0.26, vegetation_index: 0.33, population_density: 1800,  accessibility_index: 0.78, historical_record_count: 42, report_frequency: 5.9 },
  { cvegeo: "15067", municipio: "Ocoyoacac",          lat: 19.27, lon: -99.46, terrain_index: 0.44, vegetation_index: 0.61, population_density: 720,   accessibility_index: 0.68, historical_record_count: 17, report_frequency: 4.1 },
  { cvegeo: "15068", municipio: "Otzolotepec",        lat: 19.42, lon: -99.56, terrain_index: 0.37, vegetation_index: 0.52, population_density: 590,   accessibility_index: 0.63, historical_record_count: 16, report_frequency: 4.2 },
  { cvegeo: "15069", municipio: "Papalotla",          lat: 19.56, lon: -98.86, terrain_index: 0.25, vegetation_index: 0.42, population_density: 980,   accessibility_index: 0.70, historical_record_count: 11, report_frequency: 3.8 },
  { cvegeo: "15070", municipio: "La Paz",             lat: 19.36, lon: -98.96, terrain_index: 0.20, vegetation_index: 0.22, population_density: 5600,  accessibility_index: 0.84, historical_record_count: 64, report_frequency: 7.1 },
  { cvegeo: "15075", municipio: "San Felipe del Progreso", lat: 19.71, lon: -99.95, terrain_index: 0.58, vegetation_index: 0.64, population_density: 210, accessibility_index: 0.45, historical_record_count: 23, report_frequency: 4.6 },
  { cvegeo: "15081", municipio: "Tecámac",            lat: 19.71, lon: -98.97, terrain_index: 0.27, vegetation_index: 0.30, population_density: 3200,  accessibility_index: 0.82, historical_record_count: 47, report_frequency: 6.2 },
  { cvegeo: "15084", municipio: "Tepotzotlán",        lat: 19.72, lon: -99.22, terrain_index: 0.34, vegetation_index: 0.44, population_density: 850,   accessibility_index: 0.74, historical_record_count: 20, report_frequency: 4.4 },
  { cvegeo: "15086", municipio: "Texcoco",            lat: 19.51, lon: -98.88, terrain_index: 0.30, vegetation_index: 0.38, population_density: 1500,  accessibility_index: 0.77, historical_record_count: 36, report_frequency: 5.3 },
  { cvegeo: "15092", municipio: "Tlalnepantla",       lat: 19.54, lon: -99.19, terrain_index: 0.19, vegetation_index: 0.16, population_density: 9200,  accessibility_index: 0.94, historical_record_count: 78, report_frequency: 7.4 },
  { cvegeo: "15095", municipio: "Toluca",             lat: 19.29, lon: -99.66, terrain_index: 0.36, vegetation_index: 0.37, population_density: 2100,  accessibility_index: 0.85, historical_record_count: 89, report_frequency: 7.0 },
  { cvegeo: "15096", municipio: "Tonatico",           lat: 18.80, lon: -99.67, terrain_index: 0.67, vegetation_index: 0.71, population_density: 130,   accessibility_index: 0.35, historical_record_count: 9,  report_frequency: 3.0 },
  { cvegeo: "15100", municipio: "Tultepec",           lat: 19.69, lon: -99.13, terrain_index: 0.23, vegetation_index: 0.27, population_density: 2800,  accessibility_index: 0.88, historical_record_count: 28, report_frequency: 5.1 },
  { cvegeo: "15101", municipio: "Tultitlán",          lat: 19.65, lon: -99.17, terrain_index: 0.22, vegetation_index: 0.23, population_density: 6400,  accessibility_index: 0.89, historical_record_count: 51, report_frequency: 6.6 },
  { cvegeo: "15104", municipio: "Valle de Bravo",     lat: 19.20, lon: -100.13,terrain_index: 0.71, vegetation_index: 0.78, population_density: 95,    accessibility_index: 0.32, historical_record_count: 13, report_frequency: 3.4 },
  { cvegeo: "15106", municipio: "Villa Victoria",     lat: 19.44, lon: -100.00,terrain_index: 0.63, vegetation_index: 0.72, population_density: 110,   accessibility_index: 0.36, historical_record_count: 15, report_frequency: 3.6 },
  { cvegeo: "15108", municipio: "Xalatlaco",          lat: 19.18, lon: -99.42, terrain_index: 0.49, vegetation_index: 0.58, population_density: 320,   accessibility_index: 0.50, historical_record_count: 12, report_frequency: 3.9 },
  { cvegeo: "15109", municipio: "Xonacatlán",         lat: 19.40, lon: -99.53, terrain_index: 0.41, vegetation_index: 0.49, population_density: 720,   accessibility_index: 0.65, historical_record_count: 19, report_frequency: 4.4 },
  { cvegeo: "15112", municipio: "Zinacantepec",       lat: 19.29, lon: -99.74, terrain_index: 0.53, vegetation_index: 0.60, population_density: 460,   accessibility_index: 0.58, historical_record_count: 24, report_frequency: 4.7 },
  { cvegeo: "15113", municipio: "Zumpango",           lat: 19.80, lon: -99.10, terrain_index: 0.32, vegetation_index: 0.40, population_density: 980,   accessibility_index: 0.71, historical_record_count: 25, report_frequency: 4.9 },
];

/* --- Fosas verificadas por colectivos (registros "a mano" de la demo).
   El resto de puntos del mapa se generan en geo-utils.js a partir de
   ESTADOS_MX[].fosas (simulación reproducible con semilla). --- */
const FOSAS_MOCK = [
  { id: "F-001", estado: "15", municipio: "Valle de Bravo", lat: 19.21, lon: -100.14, fecha: "2024-03-12", victimas: 3, estado_proc: "En investigación" },
  { id: "F-002", estado: "15", municipio: "Toluca",         lat: 19.30, lon: -99.67,  fecha: "2024-07-08", victimas: 2, estado_proc: "Peritaje" },
  { id: "F-003", estado: "15", municipio: "Chalco",         lat: 19.25, lon: -98.91,  fecha: "2025-01-20", victimas: 5, estado_proc: "En investigación" },
  { id: "F-004", estado: "15", municipio: "Texcoco",        lat: 19.52, lon: -98.89,  fecha: "2023-11-02", victimas: 1, estado_proc: "Cerrada" },
  { id: "F-005", estado: "15", municipio: "Ixtapaluca",     lat: 19.33, lon: -98.87,  fecha: "2025-02-14", victimas: 4, estado_proc: "En investigación" },
  { id: "F-006", estado: "14", municipio: "Guadalajara",    lat: 20.67, lon: -103.35, fecha: "2024-09-30", victimas: 6, estado_proc: "En investigación" },
  { id: "F-007", estado: "14", municipio: "Zapopan",        lat: 20.72, lon: -103.39, fecha: "2025-03-05", victimas: 2, estado_proc: "Peritaje" },
  { id: "F-008", estado: "12", municipio: "Acapulco",       lat: 16.85, lon: -99.88,  fecha: "2024-12-18", victimas: 7, estado_proc: "En investigación" },
  { id: "F-009", estado: "12", municipio: "Iguala",         lat: 18.34, lon: -99.54,  fecha: "2023-06-22", victimas: 3, estado_proc: "Cerrada" },
  { id: "F-010", estado: "08", municipio: "Ciudad Juárez",  lat: 31.73, lon: -106.49, fecha: "2025-01-09", victimas: 9, estado_proc: "En investigación" },
];

/* --- Personas ficticias (consulta pública). Nunca se muestran nombre ni señas. --- */
const PERSONAS_MOCK = [
  { folio: "GD-2024-001", sexo: "Mujer",  edad: 24, municipio: "Valle de Bravo", estado: "15", fecha: "2025-02-10", estatura: 162, complexion: "delgada", lon: -100.13, lat: 19.20 },
  { folio: "GD-2024-002", sexo: "Hombre", edad: 41, municipio: "Ecatepec",       estado: "15", fecha: "2024-11-02", estatura: 175, complexion: "robusta", lon: -99.05,  lat: 19.60 },
  { folio: "GD-2024-003", sexo: "Mujer",  edad: 19, municipio: "Chalco",         estado: "15", fecha: "2025-01-15", estatura: 158, complexion: "media",   lon: -98.90,  lat: 19.26 },
  { folio: "GD-2024-004", sexo: "Hombre", edad: 35, municipio: "Toluca",         estado: "15", fecha: "2024-08-22", estatura: 178, complexion: "robusta", lon: -99.66,  lat: 19.29 },
  { folio: "GD-2024-005", sexo: "Mujer",  edad: 52, municipio: "Texcoco",        estado: "15", fecha: "2024-05-30", estatura: 155, complexion: "media",   lon: -98.88,  lat: 19.51 },
  { folio: "GD-2025-006", sexo: "Hombre", edad: 28, municipio: "Zapopan",        estado: "14", fecha: "2025-06-03", estatura: 170, complexion: "media",   lon: -103.39, lat: 20.72 },
  { folio: "GD-2025-007", sexo: "Mujer",  edad: 17, municipio: "Iguala",         estado: "12", fecha: "2025-04-19", estatura: 160, complexion: "delgada", lon: -99.54,  lat: 18.34 },
];

/* --- Perfil de localización (SIMULADO): de cada 100 casos con este perfil
   que fueron localizados, cuántos aparecieron a cada distancia del último
   punto conocido. Alimenta la gráfica de la consulta pública. --- */
const PERFIL_LOCALIZACION = {
  Mujer:  { "0-17": [38, 27, 18, 11, 6], "18-29": [31, 26, 21, 14, 8], "30-59": [36, 28, 19, 11, 6], "60+": [52, 25, 13, 7, 3] },
  Hombre: { "0-17": [34, 28, 20, 12, 6], "18-29": [24, 23, 23, 18, 12], "30-59": [27, 25, 22, 16, 10], "60+": [49, 26, 14, 8, 3] },
};
const RANGOS_DISTANCIA = ["< 5 km", "5–15 km", "15–40 km", "40–100 km", "> 100 km"];

/* --- Red de grupos delictivos (FICTICIA). Nombres genéricos a propósito:
   el objetivo es mostrar el método de grafos, no señalar a nadie. --- */
const GRUPOS_MOCK = [
  { id: "A", nombre: "Grupo A", color: "#b4413c", estados: ["14", "16", "06", "18", "11", "15", "12"] },
  { id: "B", nombre: "Grupo B", color: "#c7792b", estados: ["25", "26", "08", "10", "02", "03"] },
  { id: "C", nombre: "Grupo C", color: "#7a5aa6", estados: ["28", "19", "05", "24", "30"] },
  { id: "D", nombre: "Grupo D", color: "#2f7d8c", estados: ["12", "17", "15", "09", "21"] },
  { id: "E", nombre: "Grupo E", color: "#5c7a2e", estados: ["11", "22", "16", "32", "01"] },
  { id: "F", nombre: "Grupo F", color: "#8a6d3b", estados: ["30", "27", "07", "20", "21", "28"] },
];

/* --- Contactos reales de búsqueda (verificados nov. 2026) --- */
const CONTACTOS = [
  { nombre: "Comisión Nacional de Búsqueda", tel: "800 028 77 83", nota: "Reporte de desaparición, 24 h" },
  { nombre: "CNB por WhatsApp",              tel: "55 13 09 90 24", nota: "Mensajes y seguimiento de folio" },
  { nombre: "Comisión de Búsqueda Edomex",   tel: "800 216 0361",  nota: "También 800 509 0927" },
  { nombre: "Emergencias",                   tel: "911",           nota: "Si la desaparición acaba de ocurrir" },
  { nombre: "Denuncia anónima",              tel: "089",           nota: "Información sobre posibles fosas" },
];

/* --- KPIs nacionales (cifras de referencia simuladas) --- */
const KPIS_NACIONALES = {
  personas_desaparecidas: 124500,
  fosas_registradas:      4820,
  buscadoras_activas:     312,
  precision_modelo:       0.872,
};
