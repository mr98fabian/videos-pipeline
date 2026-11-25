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
  // gradosPorRizo: giro de la PUNTA por unidad de rizo; cada tramo gira
  // (rizo − rizoNeutro) · gradosPorRizo · s² (s = 0 base, 1 punta), iteración 2 punto 9.
  cola: { base: TRAZA.cola.base, rizoNeutro: 0.3, gradosPorRizo: 40 },
  guante: { radio: 110 }, // radio envolvente del guante abierto desde la muñeca
  pantalla: { x: 468, y: 1180, alto: 640 }, // pies en y = 1180, 1 u = 0,64 px
  beatEscala: 1.12,
  acentoRebase: 1.25,
  linea: { exterior: 7.3, interior: 5.0, fina: 3.6 }, // pesos medidos en la madre (iteración 2, punto 14)
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

// ------------------------------------------------------------- R3: deformar por la espina
// Una espina es una polilínea densa (longitud de arco, tangente y curvatura en
// cada vértice). Cada punto trazado se ancla a la espina NEUTRA como
// (σ / L, v): fracción de longitud y distancia con signo a ella, más el resto
// exacto que deja la proyección. En la pose se coloca en espina'(σ') + v·normal'(σ')
// (+ el resto, girado con el marco): en el neutro es la identidad exacta.
// Por el lado cóncavo, si la pose curva más que el neutro, v se comprime para
// que la carne del codo no se pliegue sobre sí misma.
export const TRAMOS = 24;
const _espina = (pts) => {
  const n = pts.length;
  const cum = [0];
  for (let i = 1; i < n; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const t = pts.map((_, i) => {
    const a = pts[Math.max(0, i - 1)];
    const b = pts[Math.min(n - 1, i + 1)];
    const l = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    return [(b[0] - a[0]) / l, (b[1] - a[1]) / l];
  });
  const h = [];
  t.forEach((d, i) => {
    let a = Math.atan2(d[1], d[0]);
    if (i) while (a - h[i - 1] > Math.PI) a -= 2 * Math.PI;
    if (i) while (a - h[i - 1] < -Math.PI) a += 2 * Math.PI;
    h.push(a);
  });
  const k = h.map((_, i) => {
    const a = Math.max(0, i - 1);
    const b = Math.min(n - 1, i + 1);
    return (h[b] - h[a]) / Math.max(1e-9, cum[b] - cum[a]);
  });
  return { p: pts, cum, L: cum[n - 1], t, h, k };
};
export const evaluar = (e, s) => {
  const n = e.p.length;
  if (s <= 0) return { c: [e.p[0][0] + e.t[0][0] * s, e.p[0][1] + e.t[0][1] * s], d: e.t[0], k: 0 };
  if (s >= e.L) return { c: [e.p[n - 1][0] + e.t[n - 1][0] * (s - e.L), e.p[n - 1][1] + e.t[n - 1][1] * (s - e.L)], d: e.t[n - 1], k: 0 };
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (e.cum[m] <= s) lo = m; else hi = m; }
  const a = (s - e.cum[lo]) / Math.max(1e-9, e.cum[hi] - e.cum[lo]);
  const P = e.p;
  const dx = e.t[lo][0] + (e.t[hi][0] - e.t[lo][0]) * a;
  const dy = e.t[lo][1] + (e.t[hi][1] - e.t[lo][1]) * a;
  const l = Math.hypot(dx, dy) || 1;
  return { c: [P[lo][0] + (P[hi][0] - P[lo][0]) * a, P[lo][1] + (P[hi][1] - P[lo][1]) * a], d: [dx / l, dy / l], k: e.k[lo] + (e.k[hi] - e.k[lo]) * a };
};
export const anclar = (polys, e) => polys.map((poly) => poly.map((q) => {
  const n = e.p.length;
  let bs = 0;
  let bd = Infinity;
  for (let i = 0; i < n - 1; i++) {
    const a = e.p[i];
    const b = e.p[i + 1];
    const lx = b[0] - a[0];
    const ly = b[1] - a[1];
    const ll = lx * lx + ly * ly || 1e-9;
    let tau = ((q[0] - a[0]) * lx + (q[1] - a[1]) * ly) / ll;
    if (!(i === 0 && tau < 0) && !(i === n - 2 && tau > 1)) tau = Math.max(0, Math.min(1, tau));
    const fx = a[0] + lx * tau;
    const fy = a[1] + ly * tau;
    const dd = (q[0] - fx) ** 2 + (q[1] - fy) ** 2;
    if (dd < bd) { bd = dd; bs = e.cum[i] + tau * Math.sqrt(ll); }
  }
  const { c, d, k } = evaluar(e, bs);
  const v = -(q[0] - c[0]) * d[1] + (q[1] - c[1]) * d[0];
  const rx = q[0] - (c[0] - d[1] * v);
  const ry = q[1] - (c[1] + d[0] * v);
  return [bs / e.L, v, rx * d[0] + ry * d[1], -rx * d[1] + ry * d[0], Math.abs(k)];
}));
const CODO = 0.6; // |v|·κ máximo por el lado cóncavo (1 = la carne llega al centro de curvatura)
export const deformar = (anclados, e1) => anclados.map((poly) => poly.map(([f, v, rt, rn, k0]) => {
  const { c, d, k } = evaluar(e1, f * e1.L);
  let w = v;
  if (Math.abs(k) > k0 && v * k > CODO) w = CODO / k;
  return [c[0] + d[0] * rt - d[1] * (w + rn), c[1] + d[1] * rt + d[0] * (w + rn)];
}));
export const nodosCurva = (pts, m = 160) => _espina(Array.from({ length: m + 1 }, (_, i) => bezierQ(pts, i / m)));
export const inicioEspina = (e) => ({ a: e.p[0], d: e.t[0], L: e.L });

// Cola (punto 9): espina = eje medio trazado (Bézier cúbica) prolongado recto
// hasta la base, en 24 tramos de igual largo. El rumbo de cada tramo es el
// trazado + alza + (rizo − rizoNeutro) · gradosPorRizo · s² (s = 0 base, 1 punta):
// la base casi no se mueve y la punta se enrosca. Se integra a paso fino.
const _bc = (B, t) => [0, 1].map((i) => (1 - t) ** 3 * B[0][i] + 3 * (1 - t) ** 2 * t * B[1][i] + 3 * (1 - t) * t * t * B[2][i] + t ** 3 * B[3][i]);
const _colaTramos = (() => {
  const B = TRAZA.cola.espina;
  const base = TRAZA.cola.base;
  const l0 = Math.hypot(B[0][0] - base[0], B[0][1] - base[1]);
  const lb = largoCurva([B[0], B[1], B[3]]); // solo reparte el parámetro: luego se remuestrea por arco
  const fr = l0 / (l0 + lb);
  const f = (t) => (t <= fr ? [base[0] + (B[0][0] - base[0]) * (t / fr), base[1] + (B[0][1] - base[1]) * (t / fr)] : _bc(B, (t - fr) / (1 - fr)));
  const e = _espina(Array.from({ length: 801 }, (_, i) => f(i / 800)));
  const L = e.L;
  const rumbos = Array.from({ length: TRAMOS }, (_, j) => {
    const a = evaluar(e, (L * j) / TRAMOS).c;
    const b = evaluar(e, (L * (j + 1)) / TRAMOS).c;
    return Math.atan2(b[1] - a[1], b[0] - a[0]);
  });
  return { base, L, rumbos };
})();
const COLA_PASOS = 8; // sub-pasos por tramo: el rumbo se interpola entre centros de tramo
export const colaGiros = (cola, f = 1) => _colaTramos.rumbos.map((_, j) => {
  const s = (j + 0.5) / TRAMOS;
  return cola.alza + f * (cola.rizo - RIG.cola.rizoNeutro) * RIG.cola.gradosPorRizo * s * s;
});
export const colaNodos = (cola, f = 1) => {
  const { base, L, rumbos } = _colaTramos;
  const g = colaGiros(cola, f);
  const th = rumbos.map((r, j) => r + rad(g[j]));
  const n = TRAMOS * COLA_PASOS;
  const ds = L / n;
  const pts = [base];
  for (let i = 0; i < n; i++) {
    const s = (i + 0.5) / COLA_PASOS - 0.5; // posición en «tramos» respecto al centro del primero
    const j = Math.max(0, Math.min(TRAMOS - 2, Math.floor(s)));
    const a = Math.max(0, Math.min(1, s - j));
    const r = th[j] + (th[j + 1] - th[j]) * a;
    const p = pts[i];
    pts.push([p[0] + Math.cos(r) * ds, p[1] + Math.sin(r) * ds]);
  }
  return _espina(pts);
};
export const COLA_NODOS = colaNodos({ rizo: RIG.cola.rizoNeutro, alza: 0 });
const _colaForma = anclar(TRAZA.cola.forma, COLA_NODOS);
export const COLA_SUELO = 6;
// Si algún punto baja de 6 u del suelo, el término de rizo se reduce por bisección (8 pasos).
export const colaRizoEfectivo = (cola) => {
  const minY = (f) => Math.min(...deformar(_colaForma, colaNodos(cola, f)).flat().map((q) => q[1]));
  if (minY(1) >= COLA_SUELO) return 1;
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 8; i++) {
    const m = (lo + hi) / 2;
    if (minY(m) >= COLA_SUELO) lo = m; else hi = m;
  }
  return lo;
};
// Desviación declarada (Reporte iteración 2): si ni sin rizo cabe (alza negativa,
// `estafado`), se reduce también el alza negativa, por bisección igual.
const _colaAjustada = (cola) => {
  const f = colaRizoEfectivo(cola);
  if (f > 0 || cola.alza >= 0) return { cola, f };
  const minY = (c) => Math.min(...deformar(_colaForma, colaNodos(c, 0)).flat().map((q) => q[1]));
  if (minY(cola) >= COLA_SUELO) return { cola, f };
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 8; i++) {
    const m = (lo + hi) / 2;
    if (minY({ ...cola, alza: cola.alza * m }) >= COLA_SUELO) lo = m; else hi = m;
  }
  return { cola: { ...cola, alza: cola.alza * lo }, f };
};
export const colaPose = (cola) => { const a = _colaAjustada(cola); return colaNodos(a.cola, a.f); };
export const colaForma = (cola) => deformar(_colaForma, colaPose(cola)).flat();

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
