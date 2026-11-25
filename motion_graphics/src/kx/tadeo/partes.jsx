// Tadeo vectorial por partes (Misión 0001, Fase 2). Las piezas NO son
// primitivas: son los contornos TRAZADOS de la hoja madre (traza.js, generado
// por kx_trazo.py). El rig solo las separa en capas y las mueve.
// Iteración 2 (I2-2): la tinta se COPIA, no se reconstruye.
//   R1  cada pieza trae su `tinta` (polígonos con agujeros de la máscara de
//       tinta de la madre en su zona) y se pinta en INK sin stroke;
//   R2  en los cortes entre piezas no se dibuja nada;
//   R3  brazos, piernas y cola se deforman por su espina (poses.js: deformar).
// Todo en el espacio del rig (u, y hacia arriba): el grupo exterior voltea y.
// Colores: solo INK, PAPER y mezclas TADEO_TONE de la recta INK→PAPER.
import React from "react";
import { INK, PAPER, TADEO_TONE, tone } from "../tokens.js";
import {
  COLA_NODOS, EXPRESIONES, RIG, anclar, brazoCurva, colaPose, deformar, hombros, manoMundo, nodosCurva, piernaPuntos, POSES,
  tangenteFinal, torsoPunto,
} from "./poses.js";
import { TRAZA } from "./traza.js";

const TONO = Object.fromEntries(Object.entries(TADEO_TONE).map(([k, v]) => [k, v === 0 ? PAPER : v === 1 ? INK : tone(v)]));
const C = { white: TONO.T_WHITE, cream: TONO.T_CREAM, fur: TONO.T_FUR, mask: TONO.T_MASK, ink: INK };
const L = RIG.linea;
const pt = (p) => `${p[0].toFixed(2)},${p[1].toFixed(2)}`;

// polígonos trazados → atributo d
const cerrado = (polys) => polys.map((p) => `M ${p.map(pt).join(" L ")} Z`).join(" ");
const caja = (polys) => {
  const q = polys.flat();
  const xs = q.map((v) => v[0]);
  const ys = q.map((v) => v[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

// R1: relleno del tono base, sombras planas medidas y la tinta de la madre.
const Tinta = ({ polys, color = C.ink }) => (polys && polys.length ? <path d={cerrado(polys)} fill={color} fillRule="evenodd" /> : null);
const Pieza = ({ p, tono = C.fur, children = null }) => (
  <g>
    <path d={cerrado(p.forma)} fill={tono} />
    {children}
    {(p.sombras || []).map((s, i) => <path key={i} d={cerrado(s.forma)} fill={TONO[s.tono]} />)}
    <Tinta polys={p.tinta} />
  </g>
);

// Trazo abierto como RELLENO (punto 14): se afina al 70 % en los extremos libres y acaba en punta.
const trazoRelleno = (pts, w) => {
  const n = pts.length;
  const izq = [];
  const der = [];
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)];
    const b = pts[Math.min(n - 1, i + 1)];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const l = Math.hypot(dx, dy) || 1;
    const t = i / (n - 1);
    const h = (w / 2) * Math.min(1, 0.7 + 0.3 * Math.min(t, 1 - t) / 0.2);
    izq.push([pts[i][0] - (dy / l) * h, pts[i][1] + (dx / l) * h]);
    der.push([pts[i][0] + (dy / l) * h, pts[i][1] - (dx / l) * h]);
  }
  const punta = (p, q) => {
    const dx = p[0] - q[0];
    const dy = p[1] - q[1];
    const l = Math.hypot(dx, dy) || 1;
    return [p[0] + (dx / l) * w * 0.6, p[1] + (dy / l) * w * 0.6];
  };
  return [...izq, punta(pts[n - 1], pts[n - 2]), ...der.reverse(), punta(pts[0], pts[1])];
};
const curvaQ = ([a, c, b], n = 14) => Array.from({ length: n + 1 }, (_, i) => {
  const t = i / n;
  return [0, 1].map((k) => (1 - t) ** 2 * a[k] + 2 * (1 - t) * t * c[k] + t * t * b[k]);
});
const Linea = ({ q, w }) => <path d={cerrado([trazoRelleno(curvaQ(q), w)])} fill={C.ink} />;

// R3: piezas que se doblan, ancladas una vez a su espina neutra.
const anclarPieza = (p, nodos) => ({
  forma: anclar(p.forma, nodos),
  tinta: anclar(p.tinta, nodos),
  sombras: (p.sombras || []).map((s) => ({ tono: s.tono, forma: anclar(s.forma, nodos) })),
  anillos: (p.anillos || []).map((s) => ({ tono: s.tono, forma: anclar(s.forma, nodos) })),
});
const deformarPieza = (a, n0, n1) => ({
  forma: deformar(a.forma, n1),
  tinta: deformar(a.tinta, n1),
  sombras: a.sombras.map((s) => ({ tono: s.tono, forma: deformar(s.forma, n1) })),
  anillos: a.anillos.map((s) => ({ tono: s.tono, forma: deformar(s.forma, n1) })),
});
const TORSO0 = { inclina: 0, sy: 1 };
const BRAZO0 = Object.fromEntries(["I", "D"].map((l) => {
  const b = POSES.neutro[`brazo${l}`];
  const n0 = nodosCurva(brazoCurva(hombros(TORSO0)[l], manoMundo(b.mano, TORSO0), b.curva));
  return [l, { n0, a: anclarPieza(TRAZA.brazo_piel[l], n0), r: anclarPieza(TRAZA.brazo_piel[l].raiz, n0) }];
}));
const PIERNA0 = Object.fromEntries(["I", "D"].map((l) => {
  const n0 = nodosCurva(piernaPuntos(l, POSES.neutro.piernas));
  return [l, { n0, a: anclarPieza(TRAZA.pierna_piel[l], n0) }];
}));
const COLA0 = anclarPieza({ ...TRAZA.cola, sombras: [] }, COLA_NODOS);

// ------------------------------------------------------------ guantes
// Local: muñeca en el origen, dedos hacia +x. `abierta` es el guante TRAZADO
// de cada lado; los demás tipos se construyen a su misma escala y llevan el
// puño enrollado trazado del abierto (punto 14).
const cap = (a, b, w) => ({ t: "cap", a, b, w });
const ell = (cx, cy, rx, ry) => ({ t: "ell", cx, cy, rx, ry });
const cir = (cx, cy, r) => ({ t: "ell", cx, cy, rx: r, ry: r });
const FORMAS = {
  palma: [ell(76, 0, 52, 58), cap([92, 32], [156, 66], 32), cap([98, 6], [178, 14], 32), cap([94, -24], [166, -42], 32), cap([56, 46], [74, 104], 32)],
  puno: [ell(70, 0, 54, 58), cir(112, 34, 22), cir(120, 0, 23), cir(112, -34, 22), cap([62, 44], [104, 22], 30)],
  senala: [ell(70, 0, 54, 58), cap([96, -28], [196, -30], 32), cir(112, 12, 22), cir(106, 42, 20), cap([60, 46], [100, 30], 30)],
  agarra: [ell(70, 0, 54, 58), cap([92, -30], [152, -18], 30), cap([62, 46], [146, 4], 30), cir(104, -50, 18)],
};
// líneas interiores: curvas cuadráticas [inicio, control, fin]
const INTERIOR = {
  palma: [[[52, -20], [76, -6], [96, -22]], [[50, 18], [70, 30], [84, 12]]],
  puno: [[[100, 18], [115, 17], [130, 16]], [[100, -18], [115, -17], [130, -16]]],
  senala: [[[98, 28], [111, 27], [124, 26]]],
  agarra: [[[96, -6], [120, 0], [140, -8]]],
};
// escala de los guantes construidos = largo del guante trazado / largo del construido (≈ 193 u)
const _gl = (lado) => caja(TRAZA.guantes[lado].forma)[2];
const ESCALA_GUANTE = ((_gl("I") + _gl("D")) / 2) / 193;
const formaSVG = (f, grow, fill, key) => {
  if (f.t === "cap") {
    return <path key={key} d={`M ${pt(f.a)} L ${pt(f.b)}`} stroke={fill} strokeWidth={f.w + 2 * grow} strokeLinecap="round" fill="none" />;
  }
  return <ellipse key={key} cx={f.cx} cy={f.cy} rx={f.rx + grow} ry={f.ry + grow} fill={fill} />;
};

export const Guante = ({ tipo = "abierta", angulo = 0, espejo = 1, x = 0, y = 0, lado = "D" }) => {
  const g = TRAZA.guantes[lado];
  if (tipo === "abierta" || !FORMAS[tipo]) {
    // trazado: cada lado trae su propio dibujo, ya orientado (sin espejo)
    return (
      <g transform={`translate(${x} ${y}) rotate(${angulo})`}>
        <Pieza p={g} tono={C.white} />
      </g>
    );
  }
  const fs = FORMAS[tipo];
  const k = ESCALA_GUANTE;
  const e = L.exterior / k;
  return (
    <g transform={`translate(${x} ${y}) rotate(${angulo})`}>
      <g transform={`scale(${k} ${k * espejo})`}>
        {fs.map((f, i) => formaSVG(f, e, C.ink, `o${i}`))}
        {fs.map((f, i) => formaSVG(f, 0, C.white, `f${i}`))}
        {(INTERIOR[tipo] || []).map((q, i) => <Linea key={i} q={q} w={L.interior / k} />)}
      </g>
      <Pieza p={g.puno} tono={C.white} />
    </g>
  );
};

// ------------------------------------------------------------ miembros
// El guante trazado se midió con la tangente del brazo trazado: el ángulo de
// reposo es la tangente final; `giro` lo desvía (en espejo I/D).
// Punto 3: el brazo no tiene remate; su relleno y su tinta siguen 40 u más allá
// del hombro. Esa prolongación («raiz») se pinta DETRÁS del torso y el brazo
// visible delante: con el brazo alzado la prolongación no asoma sobre el pecho.
export const Brazo = ({ lado, brazo, torso, salto, parte = "todo" }) => {
  const h = hombros(torso, salto)[lado];
  const mano = manoMundo(brazo.mano, torso, salto);
  const pts = brazoCurva(h, mano, brazo.curva);
  const espejo = lado === "D" ? -1 : 1;
  const giro = lado === "D" ? brazo.giro : -brazo.giro;
  const b0 = BRAZO0[lado];
  const nodos = parte !== "guante" ? nodosCurva(pts) : null;
  const raiz = parte === "raiz" || parte === "todo" ? <Pieza p={deformarPieza(b0.r, b0.n0, nodos)} /> : null;
  if (parte === "raiz") return raiz;
  return (
    <g>
      {raiz}
      {parte !== "guante" ? <Pieza p={deformarPieza(b0.a, b0.n0, nodos)} /> : null}
    {parte !== "tubo" ? <Guante tipo={brazo.guante} lado={lado} x={mano[0]} y={mano[1]} angulo={tangenteFinal(pts) + giro} espejo={espejo} /> : null}
    </g>
  );
};

const Pierna = ({ lado, piernas }) => {
  const pts = piernaPuntos(lado, piernas);
  const s = lado === "I" ? -1 : 1;
  const t = pts[2];
  const ang = s * ((piernas[lado === "I" ? "pieI" : "pieD"] ?? 12) - 12); // 12° = el pie del dibujo
  const p0 = PIERNA0[lado];
  return (
    <g>
      <Pieza p={deformarPieza(p0.a, p0.n0, nodosCurva(pts))} />
      <g transform={`translate(${t[0]} ${t[1]}) rotate(${-ang})`}>
        <Pieza p={TRAZA.pies[lado]} tono={C.mask} />
      </g>
    </g>
  );
};

// ------------------------------------------------------------ cola
export const Cola = ({ cola }) => {
  const c = deformarPieza(COLA0, COLA_NODOS, colaPose(cola));
  return (
    <Pieza p={{ forma: c.forma, tinta: c.tinta }}>
      {c.anillos.map((a, i) => <path key={i} d={cerrado(a.forma)} fill={TONO[a.tono]} />)}
    </Pieza>
  );
};

// ------------------------------------------------------------ torso
const torsoTr = (torso, salto) => {
  const [px, py] = RIG.torsoPivote;
  return `translate(0 ${salto}) translate(${px} ${py}) rotate(${-torso.inclina}) scale(${torso.sx} ${torso.sy}) translate(${-px} ${-py})`;
};
export const Torso = ({ torso, salto, extra }) => {
  const tr = torsoTr(torso, salto);
  return (
    <g transform={tr}>
      <Pieza p={TRAZA.torso}>
        <path d={cerrado(TRAZA.panza.forma)} fill={C.cream} />
      </Pieza>
      {extra === "bolsillos"
        ? [-1, 1].map((s) => (
          <rect key={s} x={s * 172 - 35} y={160} width={70} height={90} rx={14} fill={C.white} stroke={C.ink} strokeWidth={L.interior}
            transform={`rotate(${s * -8} ${s * 172} 250)`} />
        ))
        : null}
    </g>
  );
};

// ------------------------------------------------------------ cara
// La sonrisa del neutro es la de la vista frontal (la misma cabeza que se
// calca); el resto de bocas sale de la fila de expresiones de la hoja madre.
const EXPR = { ...TRAZA.expresiones, frente: { boca: TRAZA.boca_sonrisa, boca_relleno: [], cerrado: {} } };
// Boca de cada expresión: las 6 de la hoja madre se trazan; las otras se
// derivan transformando una trazada (mismo trazo, otra forma).
const BOCAS = {
  sonrisa: { de: "frente" },
  triste: { de: "triste" },
  apretada: { de: "decidido" },
  ladeada: { de: "guino" },
  ondulada: { de: "decidido", sx: 0.7, sy: 1.0, rot: -7 },
  ancha: { de: "frente", sx: 1.12, sy: 1.3 },
  temblorosa: { de: "triste", sx: 0.92, sy: 1.25, rot: 4 },
};

// Risa y grito (punto 10): la barbilla DEL PROPIO CRÁNEO baja y la boca se
// abre dentro de la cara. Comisuras y curva de arriba = sonrisa frontal trazada.
const SONR = TRAZA.sonrisa_linea;
const X_COM = (SONR[SONR.length - 1][0] - SONR[0][0]) / 2;
const X_CEN = (SONR[SONR.length - 1][0] + SONR[0][0]) / 2;
const Y_COM = (SONR[0][1] + SONR[SONR.length - 1][1]) / 2;
const H_MAND = Y_COM - TRAZA.menton[1];
const ySonrisa = (x) => {
  for (let i = 1; i < SONR.length; i++) {
    if (x <= SONR[i][0]) {
      const a = (x - SONR[i - 1][0]) / (SONR[i][0] - SONR[i - 1][0]);
      return SONR[i - 1][1] + (SONR[i][1] - SONR[i - 1][1]) * Math.max(0, Math.min(1, a));
    }
  }
  return SONR[SONR.length - 1][1];
};
const mandibula = (polys, m) => polys.map((p) => p.map(([x, y]) => {
  if (y >= Y_COM) return [x, y];
  const fuera = Math.abs(x - X_CEN) - X_COM;
  const w = fuera <= 0 ? 1 : Math.max(0, 1 - fuera / 40);
  return [x, Y_COM - (Y_COM - y) * (1 + (w * m) / H_MAND)];
}));
const bajarPieza = (p, m) => ({ ...p, forma: mandibula(p.forma, m), tinta: mandibula(p.tinta, m),
  sombras: (p.sombras || []).map((s) => ({ ...s, forma: mandibula(s.forma, m) })) });

const BocaAbierta = ({ m, uid }) => {
  const xs = Array.from({ length: 33 }, (_, i) => X_CEN - X_COM + (2 * X_COM * i) / 32);
  const arriba = xs.map((x) => [x, ySonrisa(x)]);
  const abajo = xs.map((x) => [x, ySonrisa(x) - 0.85 * m * (1 - ((x - X_CEN) / X_COM) ** 2)]).reverse();
  const d = cerrado([[...arriba, ...abajo]]);
  const id = `${uid}-boca`;
  const fondo = ySonrisa(X_CEN) - 0.85 * m;
  return (
    <g>
      <clipPath id={id}><path d={d} /></clipPath>
      <path d={d} fill={C.ink} />
      <g clipPath={`url(#${id})`}>
        <path d={cerrado([[...arriba, ...arriba.map(([x, y]) => [x, y - 16]).reverse()]])} fill={C.white} />
        <ellipse cx={X_CEN} cy={fondo + 4} rx={X_COM * 0.5} ry={Math.max(10, 0.28 * m)} fill={C.mask} />
      </g>
      <Tinta polys={TRAZA.boca_sonrisa} />
    </g>
  );
};

const ABIERTAS = new Set(["risa", "grito"]);
const Boca = ({ tipo, x }) => {
  if (ABIERTAS.has(tipo)) return null; // se abre en la cara, aparte
  if (tipo === "o") {
    // punto 13: centrada en el eje, bajo la sonrisa frontal, simétrica
    const o = TRAZA.boca_o;
    return (
      <g transform={`translate(${x} 0)`}>
        <Tinta polys={o.tinta} />
        <Tinta polys={o.lengua} color={TONO[o.lengua_tono]} />
      </g>
    );
  }
  const def = BOCAS[tipo] || BOCAS.sonrisa;
  const src = EXPR[def.de];
  if (!src || !src.boca.length) return null;
  const [x0, y0, x1, y1] = caja(src.boca);
  const cx = (x0 + x1) / 2;
  // las cabezas de la hoja no están todas de frente (guiño viene en 3/4):
  // cada boca se recoloca sobre la sonrisa del frente, centrada.
  const [fx0, fy0, fx1, fy1] = caja(EXPR.frente.boca);
  const dx = (fx0 + fx1) / 2 - cx;
  const dy = (fy0 + fy1) / 2 - (y0 + y1) / 2;
  const tr = `translate(${x + dx} ${dy}) translate(${cx} ${y1}) rotate(${def.rot || 0}) scale(${def.sx || 1} ${def.sy || 1}) translate(${-cx} ${-y1})`;
  return (
    <g transform={tr}>
      {src.boca_relleno.map((r, i) => <Tinta key={i} polys={r.forma} color={TONO[r.tono]} />)}
      <Tinta polys={src.boca} />
    </g>
  );
};

// Cejas (punto 11): la forma es una mezcla entre la ceja de sonrisa (base) y
// la trazada de triste (τ > 0) o de decidido (τ < 0); el resto de la
// inclinación, el desplazamiento y el arco se aplican sobre esa mezcla, así
// que los parámetros de las tres expresiones reproducen su ceja trazada.
const CEJAS = TRAZA.cejas_mezcla;
const Ceja = ({ lado, ceja, dx }) => {
  const s = lado === "I" ? 1 : -1; // en I el extremo interior es el derecho
  if (!CEJAS) {
    const c = TRAZA.cejas[lado];
    const ang = (Math.atan2((ceja.interior - ceja.exterior) * s, c.largo) * 180) / Math.PI;
    return <g transform={`translate(${dx} ${(ceja.interior + ceja.exterior) / 2}) rotate(${ang} ${c.centro[0]} ${c.centro[1]})`}><Tinta polys={c.forma} /></g>;
  }
  const M = CEJAS[lado];
  const tau = ceja.interior - ceja.exterior;
  const obj = tau > 0 ? M.triste : M.decidido;
  const ref = (tau > 0 ? EXPRESIONES.triste : EXPRESIONES.decidido)[`ceja${lado}`];
  const w = Math.max(0, Math.min(1.3, tau / (ref.interior - ref.exterior))) || 0;
  const forma = M.base.map((q, i) => [q[0] + w * (obj[i][0] - q[0]), q[1] + w * (obj[i][1] - q[1])]);
  const resto = {
    tau: tau - w * (ref.interior - ref.exterior),
    dy: (ceja.interior + ceja.exterior) / 2 - w * (ref.interior + ref.exterior) / 2,
    arco: (ceja.arco ?? 8) - (8 + w * ((ref.arco ?? 8) - 8)),
  };
  const xs = forma.map((q) => q[0]);
  const ys = forma.map((q) => q[1]);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
  const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const ang = (Math.atan2(resto.tau * s, Math.max(...xs) - Math.min(...xs)) * 180) / Math.PI;
  const sy = 1 + resto.arco * 0.03;
  return (
    <g transform={`translate(${dx} ${resto.dy}) rotate(${ang} ${cx} ${cy}) translate(${cx} ${cy}) scale(1 ${sy}) translate(${-cx} ${-cy})`}>
      <Tinta polys={[forma]} />
    </g>
  );
};

const Ojo = ({ lado, uid, ancho, escala, pupila, mirada, parpado, cerrado: estaCerrado, lagrima, cerradoTrazado, dx }) => {
  const o = TRAZA.ojos[lado];
  const [cx, cy] = o.centro;
  const s = lado === "I" ? -1 : 1;
  const tr = `translate(${dx} 0) translate(${cx} ${cy}) scale(${ancho * escala} ${escala}) translate(${-cx} ${-cy})`;
  if (estaCerrado) {
    // punto 12: el blanco del ojo relleno de pelaje y el arco trazado encima
    const arco = cerradoTrazado && cerradoTrazado.length ? cerradoTrazado : null;
    const [a0, b0, a1, b1] = arco ? caja(arco) : [0, 0, 0, 0];
    return (
      <g>
        <g transform={tr}><path d={cerrado(o.forma)} fill={C.fur} /></g>
        {arco ? (
          <g transform={`translate(${dx + cx - (a0 + a1) / 2} ${cy - (b0 + b1) / 2})`}><Tinta polys={arco} /></g>
        ) : (
          <path d={cerrado([trazoRelleno(curvaQ([[cx - 32 + dx, cy - 6], [cx + dx, cy + 30], [cx + 32 + dx, cy - 6]]), L.interior)])} fill={C.ink} />
        )}
      </g>
    );
  }
  const p = o.pupila;
  const [pcx, pcy] = p.centro;
  const px = mirada.x * 16;
  const py = mirada.y * 20;
  const ry = o.ry;
  const lidY = cy + ry - parpado * 2 * ry;
  const id = `${uid}-ojo${lado}`;
  return (
    <g>
      <g transform={tr}>
        <clipPath id={id}><path d={cerrado(o.forma)} /></clipPath>
        <path d={cerrado(o.forma)} fill={C.white} />
        <g clipPath={`url(#${id})`}>
          {/* punto 7: la pupila trazada con sus brillos (agujeros), entera con la mirada */}
          <g transform={`translate(${px} ${py}) translate(${pcx} ${pcy}) scale(${pupila}) translate(${-pcx} ${-pcy})`}>
            <Tinta polys={p.tinta} />
          </g>
          {parpado > 0.01 ? (
            <g>
              <rect x={cx - o.rx - 8} y={lidY} width={2 * o.rx + 16} height={2 * ry + 16} fill={C.fur} />
              <path d={`M ${cx - o.rx - 8} ${lidY + 3} Q ${cx} ${lidY - 6} ${cx + o.rx + 8} ${lidY + 3}`} fill="none" stroke={C.ink} strokeWidth={L.interior} strokeLinecap="round" />
            </g>
          ) : null}
        </g>
        <Tinta polys={o.tinta} />
      </g>
      {lagrima ? (
        <path transform={`translate(${dx} 0)`} d={`M ${cx + s * 26} ${cy - ry + 8} C ${cx + s * 14} ${cy - ry - 10} ${cx + s * 16} ${cy - ry - 24} ${cx + s * 28} ${cy - ry - 24} C ${cx + s * 40} ${cy - ry - 24} ${cx + s * 42} ${cy - ry - 10} ${cx + s * 26} ${cy - ry + 8} Z`}
          fill={C.white} stroke={C.ink} strokeWidth={L.fina} />
      ) : null}
    </g>
  );
};

const FUENTE_CERRADO = { risa: "risa", ladeada: "guino" };

// Cabeza trazada, en la posición del dibujo neutro (barbilla en RIG.cuelloLocal).
export const CabezaPartes = ({ cabeza, cara, mirada, orejas, mechon = 0, uid = "t" }) => {
  const G = cabeza.gira * 100; // falso 3/4: desplazamiento de paralaje en u
  const lejos = 1 - Math.min(0.2, (Math.abs(cabeza.gira) * 0.2) / 0.6);
  const anchoI = cabeza.gira > 0 ? lejos : 1;
  const anchoD = cabeza.gira < 0 ? lejos : 1;
  const ex = 0.6 * G;
  const clip = `${uid}-craneo`;
  const fc = EXPR[FUENTE_CERRADO[cara.boca]];
  const abierta = ABIERTAS.has(cara.boca);
  const m = abierta ? Math.max(20, cara.mandibula) : 0;
  const craneo = m ? bajarPieza(TRAZA.craneo, m) : TRAZA.craneo;
  const crema = m ? mandibula(TRAZA.crema_cara, m) : TRAZA.crema_cara;
  const oreja = (lado) => {
    const o = TRAZA.orejas[lado];
    const ang = lado === "I" ? orejas.i : -orejas.d;
    const [px, py] = o.pivote;
    return (
      <g key={lado} transform={`translate(${-0.3 * G} 0) rotate(${ang} ${px} ${py})`}>
        <Pieza p={o} />
      </g>
    );
  };
  const [mx, my] = TRAZA.mechon.pivote;
  return (
    <g>
      <clipPath id={clip}><path d={cerrado(craneo.forma)} /></clipPath>
      {oreja("I")}
      {oreja("D")}
      <g transform={`rotate(${-mechon} ${mx} ${my})`}>
        <Pieza p={TRAZA.mechon} />
      </g>
      <Pieza p={craneo}>
        <g clipPath={`url(#${clip})`}>
          <g transform={`translate(${0.5 * G} 0)`}><path d={cerrado(crema)} fill={C.cream} /></g>
        </g>
      </Pieza>
      <g clipPath={`url(#${clip})`}>
        <g transform={`translate(${ex} 0)`}>
          <path d={cerrado(TRAZA.antifaz.I)} fill={C.mask} />
          <path d={cerrado(TRAZA.antifaz.D)} fill={C.mask} />
        </g>
        <Ojo lado="I" uid={uid} dx={ex} ancho={anchoI} escala={cara.ojo} pupila={cara.pupila} mirada={mirada}
          parpado={cara.parpadoI} cerrado={cara.cerradoI} lagrima={cara.lagrima} cerradoTrazado={fc && fc.cerrado.I} />
        <Ojo lado="D" uid={uid} dx={ex} ancho={anchoD} escala={cara.ojo} pupila={cara.pupila} mirada={mirada}
          parpado={cara.parpadoD} cerrado={cara.cerradoD} lagrima={cara.lagrima} cerradoTrazado={fc && fc.cerrado.D} />
        <g transform={`translate(${ex} 0)`}>
          <Tinta polys={TRAZA.antifaz_tinta.I} />
          <Tinta polys={TRAZA.antifaz_tinta.D} />
        </g>
        <Ceja lado="I" ceja={cara.cejaI} dx={ex} />
        <Ceja lado="D" ceja={cara.cejaD} dx={ex} />
        {abierta ? <g transform={`translate(${0.9 * G} 0)`}><BocaAbierta m={m} uid={uid} /></g> : null}
        <g transform={`translate(${G} 0)`}>
          <Tinta polys={TRAZA.nariz.forma} />
          <Tinta polys={TRAZA.nariz.brillo} color={C.white} />
        </g>
        <Boca tipo={cara.boca} x={0.9 * G} />
      </g>
    </g>
  );
};

// Transformación SVG de la cabeza sobre el torso.
export const cabezaTransform = (est) => {
  const salto = est.piernas.salto || 0;
  const cuello = torsoPunto(RIG.cuelloLocal, est.torso, salto);
  const ang = est.torso.inclina + est.cabeza.inclina;
  const [chx, chy] = RIG.cuelloLocal;
  return `translate(${cuello[0] + est.cabeza.dx} ${cuello[1] + est.cabeza.dy}) rotate(${-ang}) scale(${est.cabeza.sx} ${est.cabeza.sy}) translate(${-chx} ${-chy})`;
};

// Tadeo entero a partir de un estado de acting.estado(). Coordenadas del rig.
export const TadeoPartes = ({ est, uid = "t" }) => {
  const salto = est.piernas.salto || 0;
  const brazo = (lado, parte = "todo") => <Brazo key={lado + parte} lado={lado} parte={parte} brazo={est[`brazo${lado}`]} torso={est.torso} salto={salto} />;
  const detras = ["I", "D"].filter((l) => est[`brazo${l}`].capa === "detras");
  const delante = ["I", "D"].filter((l) => est[`brazo${l}`].capa !== "detras");
  return (
    <g>
      <Cola cola={est.cola} />
      {detras.map((l) => brazo(l))}
      <Pierna lado="I" piernas={est.piernas} />
      <Pierna lado="D" piernas={est.piernas} />
      {/* la raíz del brazo solo existe donde la tapan torso o cabeza: con el brazo
          alzado no asoma como una losa sin contorno */}
      <clipPath id={`${uid}-raiz`}>
        <path d={cerrado(TRAZA.torso.forma)} transform={torsoTr(est.torso, salto)} />
        <path d={cerrado(TRAZA.craneo.forma)} transform={cabezaTransform(est)} />
      </clipPath>
      <g clipPath={`url(#${uid}-raiz)`}>{delante.map((l) => brazo(l, "raiz"))}</g>
      <Torso torso={est.torso} salto={salto} extra={est.extra} />
      {/* como en la hoja madre: la cabeza tapa los hombros; los guantes van delante de todo */}
      {delante.map((l) => brazo(l, "tubo"))}
      <g transform={cabezaTransform(est)}>
        <CabezaPartes cabeza={est.cabeza} cara={est.cara} mirada={est.mirada} orejas={est.orejas} mechon={est.mechon} uid={uid} />
      </g>
      {delante.map((l) => brazo(l, "guante"))}
    </g>
  );
};
