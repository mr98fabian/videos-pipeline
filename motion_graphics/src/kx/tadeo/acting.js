// Reglas de acting de Tadeo (Misión 0001, Fase 2, A6) como funciones puras
// de `frame`: el render (Tadeo.jsx) y los tests (tests/test_tadeo_acting.py)
// llaman exactamente a estas mismas funciones. Sin React, sin Remotion.
import { SPRING } from "../tokens.js";
import { EXPRESIONES, MIRADAS, POSES, cruzaCuerpo } from "./poses.js";

export const FPS = 30;

// ------------------------------------------------------------ spring
// Solución analítica del oscilador amortiguado de 0 a 1 con velocidad 0
// (mismos parámetros que spring() de Remotion: mass, stiffness, damping).
export const springAt = (frame, { damping, stiffness, mass }, fps = FPS) => {
  if (frame <= 0) return 0;
  const t = frame / fps;
  const w0 = Math.sqrt(stiffness / mass);
  const z = damping / (2 * Math.sqrt(stiffness * mass));
  if (z < 1) {
    const wd = w0 * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t));
  }
  if (z === 1) return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
  const s = Math.sqrt(z * z - 1);
  const r1 = -w0 * (z - s);
  const r2 = -w0 * (z + s);
  return 1 - (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r2 - r1);
};

// Primer frame a partir del cual el spring queda a < tol de 1 para siempre.
export const settleFrames = (cfg, tol = 0.002) => {
  let last = 0;
  for (let f = 1; f < 600; f++) if (Math.abs(springAt(f, cfg) - 1) >= tol) last = f;
  return last + 1;
};

// ------------------------------------------------------------ capas (regla 1)
// La mirada lidera: cada capa arranca con un retraso fijo tras t0.
export const CAPAS = ["pupilas", "cara", "cabeza", "torso", "brazos", "orejas", "cola", "mechon"];
export const RETRASO = { pupilas: 0, cara: 1, cabeza: 3, torso: 6, brazos: 8, orejas: 10, cola: 12, mechon: 13 };
const MASA = { pupilas: "ligera", cara: "ligera", cabeza: "media", brazos: "media", torso: "pesada", cola: "pesada", orejas: "pesada", mechon: "pesada" };
const POSES_ACENTO_MANOS = new Set(["grito", "senalando", "triunfo"]);

export const presetCapa = (capa, { beat = false, hacia = null } = {}) => {
  if (beat || (capa === "brazos" && POSES_ACENTO_MANOS.has(hacia))) return SPRING.ACENTO;
  return { damping: SPRING.POP.damping, stiffness: SPRING.POP.stiffness, mass: SPRING.POP.mass[MASA[capa]] };
};

export const progresoCapa = (capa, frame, t0, opts = {}) =>
  springAt(frame - (t0 + RETRASO[capa]), presetCapa(capa, opts));

// Frames que tarda un cambio de pose en asentarse del todo (última capa).
export const asentamiento = (opts = {}) =>
  Math.max(...CAPAS.map((c) => RETRASO[c] + settleFrames(presetCapa(c, opts))));

// ------------------------------------------------------------ parpadeo (regla 2)
export const PARPADEO = { dur: 6, cierre: 2.5, apertura: 3.5, minSeparacion: 20, idleMin: 84, idleMax: 156 };
const SIN_PARPADEO = new Set(["risa", "guino"]);

// Cierre del párpado (0 abierto, 1 cerrado) a `u` frames del inicio.
// Cierre 42 % con ease-in, apertura 58 % con ease-out.
export const curvaParpadeo = (u) => {
  const { cierre, dur } = PARPADEO;
  if (u <= 0 || u >= dur) return 0;
  if (u <= cierre) return (u / cierre) ** 2;
  const v = (u - cierre) / (dur - cierre);
  return 1 - (1 - (1 - v) ** 2);
};

const mulberry32 = (a) => () => {
  a |= 0;
  a = (a + 0x6d2b79f5) | 0;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

// Expresión activa en `f` dada la lista de cambios (la boca cambia en t0+1).
export const exprEn = (f, exprInicial, cambios) => {
  let e = exprInicial;
  let desde = -Infinity;
  for (const c of cambios) if (f >= c.t0 + RETRASO.cara) { e = c.expr; desde = c.t0 + RETRASO.cara; }
  return { expr: e, desde };
};

const parpadeoPermitido = (inicio, exprInicial, cambios) => {
  for (let f = Math.floor(inicio); f <= Math.ceil(inicio + PARPADEO.dur); f++) {
    const { expr, desde } = exprEn(f, exprInicial, cambios);
    if (SIN_PARPADEO.has(expr)) return false;
    if (expr === "grito" && f - desde < 8) return false;
  }
  return true;
};

// Inicios de parpadeo de toda la escena (frames, pueden ser fraccionarios).
// (a) uno por cambio, con el cierre máximo en t0+1; (b) en reposo cada
// 84-156 frames con semilla; (c) nunca dos a < 20 frames; (d) nunca en
// risa/guino ni en los 8 primeros frames de un grito.
export const agendaParpadeo = ({ exprInicial, cambios = [], duracion, semilla = 0 }) => {
  const out = [];
  const lejos = (s) => out.every((o) => Math.abs(o - s) >= PARPADEO.minSeparacion);
  for (const c of cambios) {
    const s = c.t0 + 1 - PARPADEO.cierre;
    if (parpadeoPermitido(s, exprInicial, cambios) && lejos(s)) out.push(s);
  }
  const rnd = mulberry32(semilla * 7919 + 17);
  const gap = () => PARPADEO.idleMin + Math.floor(rnd() * (PARPADEO.idleMax - PARPADEO.idleMin + 1));
  for (let s = Math.floor(rnd() * 40) + 20; s < duracion - PARPADEO.dur; s += gap()) {
    if (parpadeoPermitido(s, exprInicial, cambios) && lejos(s)) out.push(s);
  }
  return out.sort((a, b) => a - b);
};

export const cierreParpadeo = (frame, agenda) => Math.max(0, ...agenda.map((s) => curvaParpadeo(frame - s)));

// ------------------------------------------------------------ idle (regla 3)
export const IDLE = { respira: 0.0125, vaiven: 0.0047, amplitudSy: 0.012, amplitudInclina: 0.8, contraCabeza: 0.6, retrasoCabeza: 4, colaRizo: 0.08 };
export const idle = (f, semilla = 0) => {
  const g = f + semilla * 53;
  const vai = (x) => Math.sin(2 * Math.PI * IDLE.vaiven * x + 1.3);
  return {
    sy: 1 + IDLE.amplitudSy * Math.sin(2 * Math.PI * IDLE.respira * g),
    inclina: IDLE.amplitudInclina * vai(g),
    cabezaInclina: -IDLE.contraCabeza * IDLE.amplitudInclina * vai(g - IDLE.retrasoCabeza),
    colaRizo: IDLE.colaRizo * Math.sin(2 * Math.PI * IDLE.vaiven * g + 1.3 + Math.PI / 2),
  };
};

// ------------------------------------------------------------ squash (regla 5)
export const SQUASH = { min: 0.85, max: 1.15, cabeza: 0.35 };
export const squash = (sy) => {
  const y = Math.min(SQUASH.max, Math.max(SQUASH.min, sy));
  const hy = 1 + SQUASH.cabeza * (y - 1);
  return { sy: y, sx: 1 / y, cabezaSy: hy, cabezaSx: 1 / hy };
};

// ------------------------------------------------------------ holds (regla 4)
export const HOLD = { min: 10, beat: 15 };

// Una línea de tiempo es [{pose, t0, expr?, mirada?, beat?}] ordenada; cada
// cambio debe dejar asentarse el anterior y sostenerlo ≥ 10 frames (15 si beat).
export const validarLinea = (linea) => {
  for (const c of linea) if (!POSES[c.pose]) throw new Error(`pose desconocida: ${c.pose}`);
  for (let i = 1; i < linea.length; i++) {
    const prev = linea[i - 1];
    // la primera entrada es la pose inicial: no viene de ninguna transición
    const listo = prev.t0 + (i === 1 ? 0 : asentamiento({ beat: prev.beat, hacia: prev.pose }));
    const hold = linea[i].t0 - listo;
    const min = prev.beat ? HOLD.beat : HOLD.min;
    if (hold < min) throw new Error(`hold de ${hold} frames antes de «${linea[i].pose}» (mínimo ${min})`);
  }
  return true;
};

// ------------------------------------------------------------ anticipación (regla 6)
export const ANTICIPA = { umbral: 250, frames: 3, fraccion: 0.08 };

// ------------------------------------------------------------ estado
const lerp = (a, b, t) => a + (b - a) * t;
const lerpObj = (a, b, t) => Object.fromEntries(Object.keys(a).map((k) => [k, typeof a[k] === "number" ? lerp(a[k], b[k], t) : (t < 0.5 ? a[k] : b[k])]));
const lerpCeja = (a, b, t) => ({ interior: lerp(a.interior, b.interior, t), exterior: lerp(a.exterior, b.exterior, t), arco: lerp(a.arco, b.arco, t) });

const brazoEstado = (a, b, p, frame, t0) => {
  const dist = Math.hypot(b.mano[0] - a.mano[0], b.mano[1] - a.mano[1]);
  let mano = [lerp(a.mano[0], b.mano[0], p), lerp(a.mano[1], b.mano[1], p)];
  if (dist > ANTICIPA.umbral) {
    const inicio = t0 + RETRASO.brazos - ANTICIPA.frames;
    const sube = Math.min(1, Math.max(0, (frame - inicio) / ANTICIPA.frames));
    const k = ANTICIPA.fraccion * sube * (1 - Math.min(1, p));
    mano = [mano[0] - (b.mano[0] - a.mano[0]) * k, mano[1] - (b.mano[1] - a.mano[1]) * k];
  }
  return {
    mano,
    curva: lerp(a.curva, b.curva, p),
    giro: lerp(a.giro, b.giro, p),
    guante: p < 0.5 ? a.guante : b.guante,
    capa: p < 0.5 ? a.capa : b.capa,
    // iteración 3: delante/detrás del torso según la pose de reposo, cambia a la vez que la capa
    cruza: p < 0.5 ? cruzaCuerpo(a.mano) : cruzaCuerpo(b.mano),
  };
};

// Agenda de parpadeo de una línea de tiempo completa.
export const agendaLinea = (linea, duracion, semilla = 0) => agendaParpadeo({
  exprInicial: linea[0].expr || POSES[linea[0].pose].expr,
  cambios: linea.slice(1).map((c) => ({ t0: c.t0, expr: c.expr || POSES[c.pose].expr })),
  duracion, semilla,
});

// Estado en `frame` de una línea de tiempo [{pose, t0, expr?, mirada?, beat?}].
export const estadoLinea = (linea, frame, { semilla = 0, duracion = 450, conIdle = true, agenda = null } = {}) => {
  let i = 0;
  for (let k = 0; k < linea.length; k++) if (frame >= linea[k].t0) i = k;
  const cur = linea[i];
  const prev = i > 0 ? linea[i - 1] : cur;
  return estado({
    desde: prev.pose, hacia: cur.pose, t0: i > 0 ? cur.t0 : 0, frame,
    exprDesde: prev.expr, exprHacia: cur.expr, miradaDesde: prev.mirada, miradaHacia: cur.mirada,
    semilla, beat: !!cur.beat, conIdle, duracion,
    agenda: agenda || agendaLinea(linea, duracion, semilla),
  });
};

// Estado completo del rig en `frame`: lo que Tadeo.jsx dibuja.
//   desde/hacia: ids de pose · t0: frame del cambio (hacia = desde si no hay)
//   exprDesde/exprHacia, miradaDesde/miradaHacia: sobrescriben las de la pose
export const estado = ({
  desde, hacia = desde, t0 = 0, frame, exprDesde, exprHacia, miradaDesde, miradaHacia,
  semilla = 0, beat = false, conIdle = true, agenda = null, duracion = 450,
}) => {
  const A = POSES[desde];
  const B = POSES[hacia];
  if (!A || !B) throw new Error(`pose desconocida: ${!A ? desde : hacia}`);
  const eA = EXPRESIONES[exprDesde || A.expr];
  const eB = EXPRESIONES[exprHacia || B.expr];
  const mA = MIRADAS[miradaDesde || A.mirada];
  const mB = MIRADAS[miradaHacia || B.mirada];
  const hay = desde !== hacia || eA !== eB || mA !== mB;
  const opts = { beat, hacia };
  const pr = (c) => (hay ? progresoCapa(c, frame, t0, opts) : 1);

  const pPup = pr("pupilas");
  const pCara = pr("cara");
  const pCab = pr("cabeza");
  const pTor = pr("torso");
  const pBra = pr("brazos");
  const pOre = pr("orejas");
  const pCol = pr("cola");
  const pMec = pr("mechon");
  const id = conIdle ? idle(frame, semilla) : { sy: 1, inclina: 0, cabezaInclina: 0, colaRizo: 0 };

  const torsoBase = lerpObj(A.torso, B.torso, pTor);
  const sq = squash(torsoBase.sy * id.sy);
  const cabezaPose = lerpObj(A.cabeza, B.cabeza, pCab);
  const miradaGira = lerp(mA.gira, mB.gira, pCab);
  const mecInclina = lerp(A.cabeza.inclina, B.cabeza.inclina, pMec);

  const cambioCara = frame >= t0 + RETRASO.cara;
  const e = hay && cambioCara ? eB : eA;
  const ag = agenda || agendaParpadeo({
    exprInicial: eA.id, cambios: hay ? [{ t0, expr: eB.id }] : [], duracion, semilla,
  });
  const blink = cierreParpadeo(frame, ag);

  return {
    torso: { inclina: torsoBase.inclina + id.inclina, sy: sq.sy, sx: sq.sx },
    piernas: lerpObj(A.piernas, B.piernas, pTor),
    cabeza: {
      inclina: cabezaPose.inclina + id.cabezaInclina,
      gira: cabezaPose.gira + miradaGira,
      dx: cabezaPose.dx, dy: cabezaPose.dy, sy: sq.cabezaSy, sx: sq.cabezaSx,
    },
    mechon: mecInclina - cabezaPose.inclina, // rezago del mechón respecto a la cabeza
    brazoI: brazoEstado(A.brazoI, B.brazoI, pBra, frame, t0),
    brazoD: brazoEstado(A.brazoD, B.brazoD, pBra, frame, t0),
    cola: { rizo: lerp(A.cola.rizo, B.cola.rizo, pCol) + id.colaRizo, alza: lerp(A.cola.alza, B.cola.alza, pCol) },
    orejas: lerpObj(A.orejas, B.orejas, pOre),
    mirada: { x: lerp(mA.x, mB.x, pPup), y: lerp(mA.y, mB.y, pPup) },
    cara: {
      cejaI: lerpCeja(eA.cejaI, eB.cejaI, pCara),
      cejaD: lerpCeja(eA.cejaD, eB.cejaD, pCara),
      parpadoI: Math.max(lerp(eA.parpadoI, eB.parpadoI, pCara), blink),
      parpadoD: Math.max(lerp(eA.parpadoD, eB.parpadoD, pCara), blink),
      cerradoI: e.cerradoI, cerradoD: e.cerradoD,
      ojo: lerp(eA.ojo, eB.ojo, pCara), pupila: lerp(eA.pupila, eB.pupila, pCara),
      boca: e.boca, mandibula: Math.max(0, lerp(eA.mandibula, eB.mandibula, pCara)), lagrima: e.lagrima,
    },
    extra: pTor < 0.5 ? A.extra : B.extra,
    parpadeo: blink,
    progreso: { pupilas: pPup, cara: pCara, cabeza: pCab, torso: pTor, brazos: pBra, orejas: pOre, cola: pCol, mechon: pMec },
  };
};
