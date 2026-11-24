// Biblioteca FINITA de Tadeo (Misión 0001, Fase 2, A4-A5) y la geometría
// que comparten el render y los tests. Solo números: ni colores ni React.
// Espacio del rig: alto total 1000 u, origen en el suelo, x = 0 al centro,
// y hacia ARRIBA. I/D = izquierda/derecha de pantalla.

import { TRAZA } from "./traza.js";

// Las medidas salen de la TRAZA de la hoja madre (kx_trazo.py), no de
// proporciones estimadas: hombros, caderas, barbilla, grosores y largos de
// brazo y pierna son los del dibujo neutro.
const _len = (p0, p1, p2, n = 64) => {
  let L = 0;
  let prev = p0;
  for (let i = 1; i <= n; i++) {
    const t = i / n;
    const p = [0, 1].map((k) => (1 - t) ** 2 * p0[k] + 2 * (1 - t) * t * p1[k] + t * t * p2[k]);
    L += Math.hypot(p[0] - prev[0], p[1] - prev[1]);
    prev = p;
  }
  return L;
};
const _B = TRAZA.brazos;
const _Pi = TRAZA.pierna;
const _hx = (Math.abs(_B.I.P0[0]) + Math.abs(_B.D.P0[0])) / 2;
const _hy = (_B.I.P0[1] + _B.D.P0[1]) / 2;
const _largoBrazo = (_len(_B.I.P0, _B.I.P1, _B.I.P2) + _len(_B.D.P0, _B.D.P1, _B.D.P2)) / 2;

export const RIG = {
  alto: 1000,
  torsoPivote: [0, TRAZA.torso_base_y],
  hombro: [_hx, _hy],
  cadera: [Math.abs(_Pi.P0[0]), _Pi.P0[1]],
  tobillo: [Math.abs(_Pi.P2[0]), _Pi.P2[1]],
  rodilla: [Math.abs(_Pi.P1[0]), _Pi.P1[1]],
  cuelloLocal: TRAZA.menton, // barbilla trazada: la cabeza se apoya aquí
  // curvaMax 2 (A3 decía 1): con 1 el codo sale como mucho 62 u y las jarras de
  // `orgulloso` o la bocina de `grito` son imposibles. Desviación declarada en el Reporte.
  brazo: { largo: _largoBrazo, grosor: (_B.I.grosor + _B.D.grosor) / 2, factorCurva: 0.38, min: 0.75, max: 1.35, curvaMax: 2 },
  pierna: { largo: _len(_Pi.P0, _Pi.P1, _Pi.P2), grosor: _Pi.grosor, curvaMax: 0.35 },
  cola: { base: TRAZA.cola.base, rizoNeutro: 0.3, gradosPorRizo: 12 },
  guante: { radio: 110 }, // radio envolvente del guante abierto desde la muñeca
  pantalla: { x: 468, y: 1180, alto: 640 }, // pies en y = 1180, 1 u = 0,64 px
  beatEscala: 1.12,
  acentoRebase: 1.25,
  linea: { exterior: 7, interior: 4.5, fina: 3.5 },
};

// Las poses se escribieron para el brazo de diseño (hombro ±128/585, 330 u).
// Se conservan como lenguaje corporal: la mano se re-escala desde el hombro
// trazado en proporción al largo real del brazo.
const _VIEJO = { hombro: [128, 585], largo: 330 };
const _mano = ([x, y]) => {
  const s = x < 0 ? -1 : 1;
  const k = RIG.brazo.largo / _VIEJO.largo;
  return [s * RIG.hombro[0] + (x - s * _VIEJO.hombro[0]) * k, RIG.hombro[1] + (y - _VIEJO.hombro[1]) * k];
};
// Brazo neutro = el trazado: misma muñeca y la curva que reproduce su codo.
const _curvaTrazada = (b) => {
  const mid = [(b.P0[0] + b.P2[0]) / 2, (b.P0[1] + b.P2[1]) / 2];
  const dx = b.P2[0] - b.P0[0];
  const dy = b.P2[1] - b.P0[1];
  const d = Math.hypot(dx, dy);
  const perp = [-dy / d, dx / d];
  return ((b.P1[0] - mid[0]) * perp[0] + (b.P1[1] - mid[1]) * perp[1]) / (RIG.brazo.largo * RIG.brazo.factorCurva);
};

export const GUANTES = ["abierta", "puno", "senala", "palma", "agarra"];

const brazo = (mano, curva, guante = "abierta", giro = 0, capa = "delante") => ({ mano: _mano(mano), curva, guante, giro, capa });
const brazoTrazado = (lado) => ({ mano: _B[lado].P2, curva: _curvaTrazada(_B[lado]), guante: "abierta", giro: 0, capa: "delante" });
const base = {
  cabeza: { inclina: 0, gira: 0, dx: 0, dy: 0 },
  torso: { inclina: 0, sy: 1 },
  piernas: { apertura: 1, flexion: 0, pieI: 12, pieD: 12, salto: 0 },
  cola: { rizo: 0.3, alza: 0 },
  orejas: { i: 0, d: 0 },
  extra: null,
};
const pose = (id, expr, mirada, p) => ({
  id, expr, mirada,
  cabeza: { ...base.cabeza, ...(p.cabeza || {}) },
  torso: { ...base.torso, ...(p.torso || {}) },
  brazoI: p.brazoI,
  brazoD: p.brazoD,
  piernas: { ...base.piernas, ...(p.piernas || {}) },
  cola: { ...base.cola, ...(p.cola || {}) },
  orejas: { ...base.orejas, ...(p.orejas || {}) },
  extra: p.extra || null,
});

// curva > 0 arquea hacia la izquierda de la cuerda hombro→mano (giro
// antihorario): para el brazo I eso es hacia dentro, para el D hacia fuera.
// `giro` (guante) y `orejas` van en espejo: el mismo signo en I y D es una
// pose simétrica (orejas > 0 = hacia fuera; giro > 0 = antihorario en D).
export const POSES = {
  neutro: pose("neutro", "sonrisa", "camara", {
    brazoI: brazoTrazado("I"), brazoD: brazoTrazado("D"),
  }),
  confundido: pose("confundido", "confundido", "camara", {
    cabeza: { inclina: 10 }, torso: { sy: 1.04 },
    brazoI: brazo([-320, 450], 1.2, "palma", 90), brazoD: brazo([320, 450], -1.2, "palma", 90),
    orejas: { i: 10, d: -6 },
  }),
  decidido: pose("decidido", "decidido", "camara", {
    torso: { inclina: 5 }, piernas: { apertura: 1.2 },
    brazoI: brazo([-185, 330], -0.8, "puno"), brazoD: brazo([330, 520], -1, "puno", 60),
    orejas: { i: -6, d: -6 },
  }),
  explicando: pose("explicando", "sonrisa", "camara", {
    cabeza: { gira: 0.2 },
    brazoI: brazo([-230, 320], -0.2, "abierta"), brazoD: brazo([340, 690], -0.9, "abierta", -30),
  }),
  estafado: pose("estafado", "estafado", "abajo", {
    cabeza: { dy: -25, inclina: -4 }, torso: { sy: 0.93 },
    brazoI: brazo([-165, 290], 0.35, "abierta", 15), brazoD: brazo([165, 290], -0.35, "abierta", 15),
    cola: { rizo: -0.4, alza: -18 }, orejas: { i: 22, d: 22 },
  }),
  orgulloso: pose("orgulloso", "codicia", "camara", {
    torso: { inclina: -5, sy: 1.04 },
    brazoI: brazo([-160, 340], -1.8, "puno", 90), brazoD: brazo([160, 340], 1.8, "puno", 90),
    cola: { rizo: 0.6, alza: 12 },
  }),
  grito: pose("grito", "grito", "camara", {
    torso: { inclina: 8, sy: 1.08 },
    brazoI: brazo([-165, 620], 1.9, "abierta", -75), brazoD: brazo([165, 620], -1.9, "abierta", -75),
    orejas: { i: -12, d: -12 },
  }),
  senalando: pose("senalando", "decidido", "der", {
    cabeza: { gira: 0.35 },
    brazoI: brazo([-225, 330], -0.3, "puno", 0, "detras"), brazoD: brazo([400, 600], 0.9, "senala", 0),
  }),
  triunfo: pose("triunfo", "risa", "camara", {
    torso: { sy: 1.1 }, piernas: { salto: 20, flexion: 0.4 },
    brazoI: brazo([-230, 930], -0.3, "puno"), brazoD: brazo([230, 930], 0.3, "puno"),
    cola: { rizo: 0.8, alza: 25 }, orejas: { i: -10, d: -10 },
  }),
  codicia: pose("codicia", "codicia", "abajo", {
    cabeza: { dy: -10 }, torso: { inclina: 6 },
    brazoI: brazo([-34, 420], -1.8, "agarra", 70), brazoD: brazo([34, 420], 1.8, "agarra", 70),
    cola: { rizo: 0.5 },
  }),
  bolsillos: pose("bolsillos", "triste", "abajo", {
    cabeza: { inclina: -8 },
    brazoI: brazo([-240, 300], -0.25, "palma", 0), brazoD: brazo([240, 300], 0.25, "palma", 0),
    orejas: { i: 15, d: 15 }, extra: "bolsillos",
  }),
  asombro: pose("asombro", "asombro", "camara", {
    torso: { inclina: -6, sy: 1.06 },
    brazoI: brazo([-330, 760], 0.4, "abierta", 20), brazoD: brazo([330, 760], -0.4, "abierta", 20),
    orejas: { i: -12, d: -12 }, cola: { rizo: 0.7, alza: 20 },
  }),
  picaro: pose("picaro", "guino", "camara", {
    cabeza: { gira: -0.25, inclina: 4 }, torso: { inclina: 6 },
    brazoI: brazo([-180, 320], -0.8, "puno"), brazoD: brazo([205, 820], 0.3, "senala", 0),
  }),
  pensando: pose("pensando", "confundido", "izq", {
    cabeza: { inclina: -6 },
    brazoI: brazo([110, 430], -0.35, "agarra", 0), brazoD: brazo([-70, 530], 1.3, "agarra", -90),
  }),
};

// Expresiones: solo la cara. Cejas en u relativas a su sitio de reposo
// (20 u sobre el ojo); `arco` > 0 curva hacia arriba. Párpado = fracción del
// ojo tapada desde arriba (1 = cerrado). `cerrado` dibuja el arco «^».
const ceja = (interior, exterior, arco = 6) => ({ interior, exterior, arco });
const expr = (id, p) => ({
  id,
  cejaI: p.cejaI, cejaD: p.cejaD || p.cejaI,
  parpadoI: p.parpadoI ?? 0, parpadoD: p.parpadoD ?? p.parpadoI ?? 0,
  cerradoI: !!p.cerradoI, cerradoD: !!p.cerradoD,
  ojo: p.ojo ?? 1, pupila: p.pupila ?? 1,
  boca: p.boca, mandibula: p.mandibula ?? 0, lagrima: !!p.lagrima,
});
const tan = (deg) => 35 * Math.tan((deg * Math.PI) / 180);
export const EXPRESIONES = {
  sonrisa: expr("sonrisa", { cejaI: ceja(0, 0, 8), boca: "sonrisa" }),
  asombro: expr("asombro", { cejaI: ceja(14, 14, 12), ojo: 1.08, boca: "o" }),
  triste: expr("triste", { cejaI: ceja(tan(16), -tan(16), 2), parpadoI: 0.25, boca: "triste" }),
  decidido: expr("decidido", { cejaI: ceja(-tan(18) - 6, tan(18) - 6, 0), parpadoI: 0.3, boca: "apretada" }),
  guino: expr("guino", { cejaI: ceja(10, 12, 8), cejaD: ceja(-6, -8, 4), cerradoD: true, boca: "ladeada" }),
  risa: expr("risa", { cejaI: ceja(10, 10, 8), cerradoI: true, cerradoD: true, boca: "risa", mandibula: 35 }),
  grito: expr("grito", { cejaI: ceja(-tan(22) - 10, tan(22) - 10, 0), pupila: 0.8, ojo: 1.05, boca: "grito", mandibula: 60 }),
  confundido: expr("confundido", { cejaI: ceja(16, 16, 10), cejaD: ceja(-4, -6, 2), parpadoD: 0.25, boca: "ondulada" }),
  codicia: expr("codicia", { cejaI: ceja(-8, 2, 10), parpadoI: 0.4, boca: "ancha" }),
  estafado: expr("estafado", { cejaI: ceja(tan(22), -tan(22), 2), parpadoI: 0.35, boca: "temblorosa", lagrima: true }),
};

// Desplazamiento de pupila en fracción del recorrido (±16 u x, ±20 u y).
export const MIRADAS = {
  camara: { x: 0, y: 0, gira: 0 },
  izq: { x: -1, y: 0, gira: -0.15 },
  der: { x: 1, y: 0, gira: 0.15 },
  abajo: { x: 0, y: -0.8, gira: 0 },
};

// ------------------------------------------------------------- geometría
const rad = (d) => (d * Math.PI) / 180;
// Gira (x, y) alrededor de c; `deg` positivo = horario EN PANTALLA.
export const rotar = ([x, y], deg, [cx, cy] = [0, 0]) => {
  const a = -rad(deg);
  const dx = x - cx;
  const dy = y - cy;
  return [cx + dx * Math.cos(a) - dy * Math.sin(a), cy + dx * Math.sin(a) + dy * Math.cos(a)];
};

// Transformación del torso: squash (sx = 1/sy) y giro, pivote en su base.
export const torsoPunto = ([x, y], torso, salto = 0) => {
  const [px, py] = RIG.torsoPivote;
  const sy = torso.sy;
  const p = [px + (x - px) / sy, py + (y - py) * sy];
  const r = rotar(p, torso.inclina, RIG.torsoPivote);
  return [r[0], r[1] + salto];
};

export const hombros = (torso, salto = 0) => ({
  I: torsoPunto([-RIG.hombro[0], RIG.hombro[1]], torso, salto),
  D: torsoPunto([RIG.hombro[0], RIG.hombro[1]], torso, salto),
});

// La mano sube y baja con el hombro (squash) y gira con el torso.
export const manoMundo = (mano, torso, salto = 0) => {
  const dShoulder = (torso.sy - 1) * (RIG.hombro[1] - RIG.torsoPivote[1]);
  const r = rotar([mano[0], mano[1] + dShoulder], torso.inclina, RIG.torsoPivote);
  return [r[0], r[1] + salto];
};

// Rubber hose (A3): Bézier cuadrática, P1 = medio + perpendicular × curva × largo × 0,38.
export const brazoCurva = (hombro, mano, curva) => {
  const mx = (hombro[0] + mano[0]) / 2;
  const my = (hombro[1] + mano[1]) / 2;
  const dx = mano[0] - hombro[0];
  const dy = mano[1] - hombro[1];
  const d = Math.hypot(dx, dy) || 1;
  const k = curva * RIG.brazo.largo * RIG.brazo.factorCurva;
  return [hombro, [mx + (-dy / d) * k, my + (dx / d) * k], mano];
};

export const bezierQ = ([p0, p1, p2], t) => [
  (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
  (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1],
];
export const largoCurva = (pts, n = 64) => {
  let L = 0;
  let prev = bezierQ(pts, 0);
  for (let i = 1; i <= n; i++) {
    const p = bezierQ(pts, i / n);
    L += Math.hypot(p[0] - prev[0], p[1] - prev[1]);
    prev = p;
  }
  return L;
};
// Ángulo (grados, matemático) de la tangente final de la curva.
export const tangenteFinal = ([, p1, p2]) => (Math.atan2(p2[1] - p1[1], p2[0] - p1[0]) * 180) / Math.PI;

// Pierna trazada: cadera, rodilla y tobillo del dibujo; `apertura` separa el
// tobillo y `flexion` saca la rodilla hacia fuera.
export const piernaPuntos = (lado, piernas) => {
  const s = lado === "I" ? -1 : 1;
  const salto = piernas.salto || 0;
  const f = Math.max(0, Math.min(1, piernas.flexion || 0));
  const cadera = [s * RIG.cadera[0], RIG.cadera[1] + salto];
  const rodilla = [s * (RIG.rodilla[0] + f * 45), RIG.rodilla[1] + salto - f * 12];
  const tobillo = [s * RIG.tobillo[0] * piernas.apertura, RIG.tobillo[1] + salto];
  return [cadera, rodilla, tobillo];
};

// Cola trazada: pieza rígida que gira sobre su base (alza + rizo).
export const colaAngulo = (cola) => cola.alza + (cola.rizo - RIG.cola.rizoNeutro) * RIG.cola.gradosPorRizo;
export const colaForma = (cola) => {
  const a = colaAngulo(cola);
  const b = RIG.cola.base;
  return TRAZA.cola.forma.flat().map((q) => rotar(q, -a, b));
};

const _ext = (polys) => {
  const pts = polys.flat();
  return [Math.min(...pts.map((q) => q[0])), Math.min(...pts.map((q) => q[1])), Math.max(...pts.map((q) => q[0])), Math.max(...pts.map((q) => q[1]))];
};
const _cab = _ext([...TRAZA.craneo.forma, ...TRAZA.orejas.I.forma, ...TRAZA.orejas.D.forma, ...TRAZA.mechon.forma]);
// Caja de la cabeza respecto a la barbilla (con holgura para orejas que giran y bocas que bajan).
export const CABEZA_EXT = [_cab[0] - 40 - RIG.cuelloLocal[0], _cab[1] - 130 - RIG.cuelloLocal[1], _cab[2] + 40 - RIG.cuelloLocal[0], _cab[3] + 40 - RIG.cuelloLocal[1]];

// Geometría completa de una pose en reposo (sin idle): la usan la caja
// envolvente, el test de largos y el de zona segura.
export const geometria = (p) => {
  const salto = p.piernas.salto || 0;
  const h = hombros(p.torso, salto);
  const out = { brazos: {}, piernas: {} };
  for (const lado of ["I", "D"]) {
    const b = p[`brazo${lado}`];
    const mano = manoMundo(b.mano, p.torso, salto);
    const pts = brazoCurva(h[lado], mano, b.curva);
    out.brazos[lado] = { hombro: h[lado], control: pts[1], mano, largo: largoCurva(pts), ratio: largoCurva(pts) / RIG.brazo.largo };
    out.piernas[lado] = { puntos: piernaPuntos(lado, p.piernas) };
  }
  const cuello = torsoPunto(RIG.cuelloLocal, p.torso, salto);
  out.cabeza = { cuello: [cuello[0] + p.cabeza.dx, cuello[1] + p.cabeza.dy] };
  out.cola = colaForma(p.cola);
  return out;
};

// Caja envolvente en u (x0, y0, x1, y1), y arriba. Generosa: incluye grosores.
export const cajaU = (p) => {
  const g = geometria(p);
  const xs = [];
  const ys = [];
  const add = (x, y, r) => { xs.push(x - r, x + r); ys.push(y - r, y + r); };
  const c = g.cabeza.cuello;
  xs.push(c[0] + CABEZA_EXT[0], c[0] + CABEZA_EXT[2]);
  ys.push(c[1] + CABEZA_EXT[1], c[1] + CABEZA_EXT[3]);
  for (const lado of ["I", "D"]) {
    const b = g.brazos[lado];
    for (let i = 0; i <= 16; i++) add(...bezierQ([b.hombro, b.control, b.mano], i / 16), 40);
    add(...b.mano, RIG.guante.radio);
  }
  const t = _ext([TRAZA.torso.forma[0], ...TRAZA.pies.I.forma.map((f) => f.map(([x, y]) => [x - RIG.tobillo[0], y + RIG.tobillo[1]])), ...TRAZA.pies.D.forma.map((f) => f.map(([x, y]) => [x + RIG.tobillo[0], y + RIG.tobillo[1]]))]);
  xs.push(t[0] * 1.2 - 20, t[2] * 1.2 + 20);
  ys.push(0, t[3] + 20);
  for (const q of g.cola) add(q[0], q[1], 8);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

// Caja en píxeles de pantalla para el gate y las plantillas (A8).
export const tadeoBox = (poseId, x = RIG.pantalla.x, y = RIG.pantalla.y, escala = 1) => {
  const [x0, y0, x1, y1] = cajaU(POSES[poseId]);
  const s = (RIG.pantalla.alto / RIG.alto) * escala;
  return { x: Math.floor(x + x0 * s), y: Math.floor(y - y1 * s), w: Math.ceil((x1 - x0) * s), h: Math.ceil((y1 - y0) * s) };
};

// Export para el test de la biblioteca: lo que la hoja de poses debe cubrir
// y las medidas que el rig promete.
export const bibliotecaJSON = () => ({
  poses: Object.keys(POSES),
  expresiones: Object.keys(EXPRESIONES),
  miradas: Object.keys(MIRADAS),
  guantes: GUANTES,
  rig: RIG,
  definiciones: { POSES, EXPRESIONES, MIRADAS },
  medidas: Object.fromEntries(Object.entries(POSES).map(([id, p]) => {
    const g = geometria(p);
    return [id, {
      brazos: Object.fromEntries(["I", "D"].map((l) => [l, {
        hombro: g.brazos[l].hombro, control: g.brazos[l].control, mano: g.brazos[l].mano,
        ratio: g.brazos[l].ratio, guante: p[`brazo${l}`].guante,
      }])),
      piernas: Object.fromEntries(["I", "D"].map((l) => [l, g.piernas[l].puntos])),
      caja_u: cajaU(p),
    }];
  })),
});
