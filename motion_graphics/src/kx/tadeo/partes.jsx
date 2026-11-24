// Tadeo vectorial por partes (Misión 0001, Fase 2, A0-A3). Todo se dibuja en
// el espacio del rig (u, y hacia arriba): el grupo exterior voltea el eje y.
// Colores: solo INK, PAPER y mezclas TADEO_TONE de la recta INK→PAPER.
import React from "react";
import { INK, PAPER, TADEO_TONE, tone } from "../tokens.js";
import { RIG, bezierQ, brazoCurva, colaPuntos, hombros, manoMundo, piernaPuntos, tangenteFinal, torsoPunto } from "./poses.js";

const C = {
  white: PAPER,
  cream: tone(TADEO_TONE.T_CREAM),
  fur: tone(TADEO_TONE.T_FUR),
  mask: tone(TADEO_TONE.T_MASK),
  ink: INK,
};
const L = RIG.linea;
const pt = (p) => `${p[0].toFixed(2)},${p[1].toFixed(2)}`;
const lineProps = { stroke: C.ink, strokeLinejoin: "round", strokeLinecap: "round" };

// ------------------------------------------------------------ guantes
// Local: muñeca en el origen, dedos hacia +x, pulgar hacia +y.
const cap = (a, b, w) => ({ t: "cap", a, b, w });
const ell = (cx, cy, rx, ry) => ({ t: "ell", cx, cy, rx, ry });
const cir = (cx, cy, r) => ({ t: "ell", cx, cy, rx: r, ry: r });

const FORMAS = {
  abierta: [ell(76, 0, 50, 56), cap([92, 30], [162, 44], 34), cap([98, 0], [176, 4], 34), cap([92, -30], [158, -40], 34), cap([58, 42], [92, 88], 34)],
  palma: [ell(76, 0, 52, 58), cap([92, 32], [156, 66], 32), cap([98, 6], [178, 14], 32), cap([94, -24], [166, -42], 32), cap([56, 46], [74, 104], 32)],
  puno: [ell(70, 0, 54, 58), cir(112, 34, 22), cir(120, 0, 23), cir(112, -34, 22), cap([62, 44], [104, 22], 30)],
  senala: [ell(70, 0, 54, 58), cap([96, -28], [196, -30], 32), cir(112, 12, 22), cir(106, 42, 20), cap([60, 46], [100, 30], 30)],
  agarra: [ell(70, 0, 54, 58), cap([92, -30], [152, -18], 30), cap([62, 46], [146, 4], 30), cir(104, -50, 18)],
};
const INTERIOR = {
  abierta: ["M 40 -16 L 62 -18", "M 40 0 L 64 0", "M 40 16 L 62 18"],
  palma: ["M 52 -20 Q 76 -6 96 -22", "M 50 18 Q 70 30 84 12"],
  puno: ["M 100 18 L 130 16", "M 100 -18 L 130 -16"],
  senala: ["M 98 28 L 124 26"],
  agarra: ["M 96 -6 Q 120 0 140 -8"],
};
const formaSVG = (f, grow, fill, key) => {
  if (f.t === "cap") {
    return <path key={key} d={`M ${pt(f.a)} L ${pt(f.b)}`} stroke={fill} strokeWidth={f.w + 2 * grow} strokeLinecap="round" fill="none" />;
  }
  return <ellipse key={key} cx={f.cx} cy={f.cy} rx={f.rx + grow} ry={f.ry + grow} fill={fill} />;
};

export const Guante = ({ tipo = "abierta", angulo = 0, espejo = 1, x = 0, y = 0 }) => {
  const fs = FORMAS[tipo] || FORMAS.abierta;
  return (
    <g transform={`translate(${x} ${y}) rotate(${angulo}) scale(1 ${espejo})`}>
      {/* puño enrollado 120 × 38 */}
      <rect x={-6} y={-60 - L.exterior} width={38 + 2 * L.exterior} height={120 + 2 * L.exterior} rx={19 + L.exterior} fill={C.ink} />
      {fs.map((f, i) => formaSVG(f, L.exterior, C.ink, `o${i}`))}
      {fs.map((f, i) => formaSVG(f, 0, C.white, `f${i}`))}
      <rect x={1} y={-60} width={38} height={120} rx={19} fill={C.white} stroke={C.ink} strokeWidth={L.interior} />
      {(INTERIOR[tipo] || []).map((d, i) => <path key={i} d={d} fill="none" strokeWidth={L.fina} {...lineProps} />)}
    </g>
  );
};

// ------------------------------------------------------------ miembros
const Tubo = ({ pts, grosor, color = C.fur }) => {
  const d = `M ${pt(pts[0])} Q ${pt(pts[1])} ${pt(pts[2])}`;
  return (
    <g>
      <path d={d} fill="none" stroke={C.ink} strokeWidth={grosor + 2 * L.exterior} strokeLinecap="round" />
      <path d={d} fill="none" stroke={color} strokeWidth={grosor} strokeLinecap="round" />
    </g>
  );
};

export const Brazo = ({ lado, brazo, torso, salto }) => {
  const h = hombros(torso, salto)[lado];
  const mano = manoMundo(brazo.mano, torso, salto);
  const pts = brazoCurva(h, mano, brazo.curva);
  const espejo = lado === "D" ? -1 : 1;
  const giro = lado === "D" ? brazo.giro : -brazo.giro;
  return (
    <g>
      <Tubo pts={pts} grosor={RIG.brazo.grosor} />
      <Guante tipo={brazo.guante} x={mano[0]} y={mano[1]} angulo={tangenteFinal(pts) + giro} espejo={espejo} />
    </g>
  );
};

const Pierna = ({ lado, piernas }) => {
  const pts = piernaPuntos(lado, piernas);
  const s = lado === "I" ? -1 : 1;
  const t = pts[2];
  const ang = s * (piernas[lado === "I" ? "pieI" : "pieD"] || 0);
  return (
    <g>
      <Tubo pts={pts} grosor={RIG.pierna.grosor} />
      <g transform={`translate(${t[0] + s * 28} ${t[1] - 18}) rotate(${-ang})`}>
        <ellipse cx={0} cy={0} rx={107.5} ry={37.5} fill={C.mask} stroke={C.ink} strokeWidth={L.exterior} />
        {[-1, 1].map((k) => (
          <path key={k} d={`M ${s * (40 + k * 22)} -36 L ${s * (36 + k * 20)} -18`} fill="none" strokeWidth={L.fina} {...lineProps} />
        ))}
      </g>
    </g>
  );
};

// ------------------------------------------------------------ cola
const cubica = (q, t) => {
  const u = 1 - t;
  return [0, 1].map((i) => u ** 3 * q[0][i] + 3 * u * u * t * q[1][i] + 3 * u * t * t * q[2][i] + t ** 3 * q[3][i]);
};
export const Cola = ({ cola }) => {
  const q = colaPuntos(cola);
  const N = 48;
  const P = Array.from({ length: N + 1 }, (_, i) => cubica(q, i / N));
  const acc = [0];
  for (let i = 1; i <= N; i++) acc.push(acc[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
  const total = acc[N];
  const [w0, w1] = RIG.cola.grosor;
  const half = (i) => (w0 + (w1 - w0) * Math.min(1, acc[i] / total / 0.75)) / 2;
  const nrm = (i) => {
    const a = P[Math.max(0, i - 1)];
    const b = P[Math.min(N, i + 1)];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const d = Math.hypot(dx, dy) || 1;
    return [-dy / d, dx / d];
  };
  const lado = (i, s) => { const n = nrm(i); const h = half(i) * s; return [P[i][0] + n[0] * h, P[i][1] + n[1] * h]; };
  const banda = (i0, i1) => {
    const a = [];
    for (let i = i0; i <= i1; i++) a.push(lado(i, 1));
    for (let i = i1; i >= i0; i--) a.push(lado(i, -1));
    return `M ${a.map(pt).join(" L ")} Z`;
  };
  const end = P[N];
  const rEnd = half(N);
  // 10 tramos por longitud de arco: claro/oscuro alternos, el último oscuro (5 anillos).
  const idx = (f) => { let k = 0; while (k < N && acc[k] / total < f) k++; return k; };
  const tramos = Array.from({ length: 5 }, (_, k) => [idx((2 * k + 1) / 10), idx((2 * k + 2) / 10)]);
  return (
    <g>
      <path d={banda(0, N)} fill={C.ink} stroke={C.ink} strokeWidth={2 * L.exterior} strokeLinejoin="round" />
      <circle cx={end[0]} cy={end[1]} r={rEnd + L.exterior} fill={C.ink} />
      <path d={banda(0, N)} fill={C.fur} />
      {tramos.map(([a, b], k) => <path key={k} d={banda(a, b)} fill={C.mask} />)}
      <circle cx={end[0]} cy={end[1]} r={rEnd} fill={C.mask} />
      {tramos.flatMap(([a, b], k) => [a, b].filter((i) => i < N).map((i) => (
        <path key={`${k}-${i}`} d={`M ${pt(lado(i, 1))} L ${pt(lado(i, -1))}`} strokeWidth={L.interior} fill="none" {...lineProps} />
      )))}
    </g>
  );
};

// ------------------------------------------------------------ torso
const TORSO = "M -125 610 C -150 480 -185 380 -185 300 C -185 240 -120 215 0 215 C 120 215 185 240 185 300 C 185 380 150 480 125 610 C 80 650 -80 650 -125 610 Z";
const PANZA = "M 0 565 C -60 565 -85 520 -92 460 C -105 380 -108 300 -80 262 C -55 238 55 238 80 262 C 108 300 105 380 92 460 C 85 520 60 565 0 565 Z";
export const Torso = ({ torso, salto, extra }) => {
  const [px, py] = RIG.torsoPivote;
  const tr = `translate(0 ${salto}) translate(${px} ${py}) rotate(${-torso.inclina}) scale(${torso.sx} ${torso.sy}) translate(${-px} ${-py})`;
  return (
    <g transform={tr}>
      <path d={TORSO} fill={C.fur} stroke={C.ink} strokeWidth={L.exterior} strokeLinejoin="round" />
      <path d={PANZA} fill={C.cream} stroke={C.ink} strokeWidth={L.interior} />
      <path d="M -22 568 L -12 552 L -2 564 L 8 550 L 20 566" fill="none" strokeWidth={L.fina} {...lineProps} />
      <path d="M -30 334 Q 0 322 30 334" fill="none" strokeWidth={L.fina} {...lineProps} />
      {extra === "bolsillos"
        ? [-1, 1].map((s) => (
          <rect key={s} x={s * 172 - 35} y={160} width={70} height={90} rx={14} fill={C.white} stroke={C.ink} strokeWidth={L.interior}
            transform={`rotate(${s * -8} ${s * 172} 250)`} />
        ))
        : null}
    </g>
  );
};

// ------------------------------------------------------------ cabeza
const craneo = (m) => {
  const b = 625 - m;
  return `M 0 915 C 120 915 205 880 215 800 L 250 745 L 222 728 L 245 ${690 - m * 0.3} L 205 ${672 - m * 0.5} `
    + `C 170 ${640 - m * 0.8} 90 ${b} 0 ${b} C -90 ${b} -170 ${640 - m * 0.8} -205 ${672 - m * 0.5} `
    + `L -245 ${690 - m * 0.3} L -222 728 L -250 745 L -215 800 C -205 880 -120 915 0 915 Z`;
};
const ANTIFAZ = "M 0 805 C 18 838 52 850 88 850 C 128 850 156 826 170 796 L 215 745 C 186 742 168 730 150 716 C 132 702 108 700 88 700 C 52 700 22 720 0 745 "
  + "C -22 720 -52 700 -88 700 C -108 700 -132 702 -150 716 C -168 730 -186 742 -215 745 L -170 796 C -156 826 -128 850 -88 850 C -52 850 -18 838 0 805 Z";

const Oreja = ({ s, ang, dx }) => (
  <g transform={`translate(${dx} 0) rotate(${s * -ang} ${s * 165} 880)`}>
    <path d={`M ${s * 105} 870 Q ${s * 120} 960 ${s * 190} 1005 Q ${s * 215} 940 ${s * 225} 870 Z`} fill={C.fur} stroke={C.ink} strokeWidth={L.exterior} strokeLinejoin="round" />
    <path d={`M ${s * 130} 878 Q ${s * 140} 935 ${s * 184} 970 Q ${s * 198} 925 ${s * 202} 878 Z`} fill={C.cream} />
  </g>
);

const Ceja = ({ ojoX, s, ceja }) => {
  const y = 858;
  const inner = [ojoX - s * 35, y + ceja.interior];
  const outer = [ojoX + s * 35, y + ceja.exterior];
  const mid = [(inner[0] + outer[0]) / 2, (inner[1] + outer[1]) / 2 + ceja.arco * 2];
  return <path d={`M ${pt(inner)} Q ${pt(mid)} ${pt(outer)}`} fill="none" strokeWidth={9} {...lineProps} />;
};

const Ojo = ({ id, cx, ancho, escala, pupila, mirada, parpado, cerrado, lagrima, s }) => {
  const rx = (39 * ancho) * escala;
  const ry = 56 * escala;
  const cy = 782;
  if (cerrado) {
    return <path d={`M ${cx - 32} ${cy - 6} Q ${cx} ${cy + 30} ${cx + 32} ${cy - 6}`} fill="none" strokeWidth={10} {...lineProps} />;
  }
  const px = cx + mirada.x * 16 * ancho;
  const py = cy + mirada.y * 20;
  const lidY = cy + ry - parpado * 2 * ry;
  return (
    <g>
      <clipPath id={id}><ellipse cx={cx} cy={cy} rx={rx} ry={ry} /></clipPath>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={C.white} />
      <g clipPath={`url(#${id})`}>
        <ellipse cx={px} cy={py} rx={20 * pupila * ancho} ry={29 * pupila} fill={C.ink} />
        <circle cx={px - 8 * ancho} cy={py + 13} r={6} fill={C.white} />
        {parpado > 0.01 ? (
          <g>
            <rect x={cx - rx - 4} y={lidY} width={2 * rx + 8} height={2 * ry + 8} fill={C.mask} />
            <path d={`M ${cx - rx - 4} ${lidY + 3} Q ${cx} ${lidY - 6} ${cx + rx + 4} ${lidY + 3}`} fill="none" strokeWidth={L.interior + 1} {...lineProps} />
          </g>
        ) : null}
      </g>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={C.ink} strokeWidth={L.interior} />
      {lagrima ? (
        <path d={`M ${cx + s * 26} ${cy - 44} C ${cx + s * 14} ${cy - 62} ${cx + s * 16} ${cy - 76} ${cx + s * 28} ${cy - 76} C ${cx + s * 40} ${cy - 76} ${cx + s * 42} ${cy - 62} ${cx + s * 26} ${cy - 44} Z`}
          fill={C.white} stroke={C.ink} strokeWidth={L.fina} />
      ) : null}
    </g>
  );
};

const Boca = ({ tipo, m, x, uid }) => {
  const st = { fill: "none", strokeWidth: L.interior, ...lineProps };
  const y = 668;
  const open = (H, rx, top, id) => (
    <g>
      <clipPath id={id}><path d={`M ${-rx} ${top} Q 0 ${top - 8} ${rx} ${top} C ${rx} ${top - H * 0.9} ${rx * 0.5} ${top - H} 0 ${top - H} C ${-rx * 0.5} ${top - H} ${-rx} ${top - H * 0.9} ${-rx} ${top} Z`} /></clipPath>
      <path d={`M ${-rx} ${top} Q 0 ${top - 8} ${rx} ${top} C ${rx} ${top - H * 0.9} ${rx * 0.5} ${top - H} 0 ${top - H} C ${-rx * 0.5} ${top - H} ${-rx} ${top - H * 0.9} ${-rx} ${top} Z`} fill={C.ink} />
      <g clipPath={`url(#${id})`}>
        <rect x={-rx} y={top - 18} width={2 * rx} height={26} fill={C.white} />
        <ellipse cx={0} cy={top - H} rx={rx * 0.55} ry={H * 0.35} fill={C.mask} />
      </g>
      <path d={`M ${-rx} ${top} Q 0 ${top - 8} ${rx} ${top} C ${rx} ${top - H * 0.9} ${rx * 0.5} ${top - H} 0 ${top - H} C ${-rx * 0.5} ${top - H} ${-rx} ${top - H * 0.9} ${-rx} ${top} Z`} fill="none" strokeWidth={L.interior} {...lineProps} />
    </g>
  );
  let el = null;
  if (tipo === "sonrisa") el = <path d={`M -55 ${y + 12} Q 0 ${y - 30} 55 ${y + 12}`} {...st} />;
  else if (tipo === "o") el = <ellipse cx={12} cy={y - 14} rx={17} ry={22} fill={C.ink} />;
  else if (tipo === "triste") el = <path d={`M -40 ${y - 14} Q 0 ${y + 14} 40 ${y - 14}`} {...st} />;
  else if (tipo === "apretada") el = <path d={`M -38 ${y - 2} Q 0 ${y + 2} 30 ${y - 2} L 42 ${y - 12}`} {...st} />;
  else if (tipo === "ladeada") el = <path d={`M -55 ${y + 16} Q -10 ${y - 22} 48 ${y + 2}`} {...st} />;
  else if (tipo === "risa") el = open(Math.max(20, 80 * Math.min(1, m / 35)), 75, y + 9, `${uid}-boca`);
  else if (tipo === "grito") el = open(Math.max(24, 100 * Math.min(1, m / 60)), 55, y + 4, `${uid}-boca`);
  else if (tipo === "ondulada") el = <path d={`M -30 ${y} q 7.5 7 15 0 t 15 0 t 15 0 t 15 0`} {...st} />;
  else if (tipo === "ancha") el = (
    <g>
      <path d={`M -72 ${y + 24} Q 0 ${y - 34} 72 ${y + 24}`} {...st} />
      <path d={`M -80 ${y + 30} Q -72 ${y + 24} -66 ${y + 34}`} {...st} />
      <path d={`M 80 ${y + 30} Q 72 ${y + 24} 66 ${y + 34}`} {...st} />
    </g>
  );
  else if (tipo === "temblorosa") el = <path d={`M -40 ${y - 14} L -28 ${y - 4} L -18 ${y + 2} L -6 ${y + 6} L 6 ${y + 4} L 18 ${y + 6} L 28 ${y - 2} L 40 ${y - 14}`} {...st} />;
  return <g transform={`translate(${x} 0)`}>{el}</g>;
};

// Cabeza en coordenadas del rig, centrada como en la pose neutra (centro y = 770).
export const CabezaPartes = ({ cabeza, cara, mirada, orejas, mechon = 0, uid = "t" }) => {
  const G = cabeza.gira * 100; // falso 3/4: desplazamiento de paralaje en u
  const m = cara.mandibula;
  const lejos = 1 - Math.min(0.2, (Math.abs(cabeza.gira) * 0.2) / 0.6);
  const anchoI = cabeza.gira > 0 ? lejos : 1;
  const anchoD = cabeza.gira < 0 ? lejos : 1;
  const ex = 0.6 * G;
  return (
    <g>
      <Oreja s={-1} ang={orejas.i} dx={-0.3 * G} />
      <Oreja s={1} ang={orejas.d} dx={-0.3 * G} />
      <path d={craneo(m)} fill={C.fur} stroke={C.ink} strokeWidth={L.exterior} strokeLinejoin="round" />
      {/* hocico debajo del antifaz: los ojos quedan enteros dentro del antifaz (A0.2) */}
      <ellipse cx={G} cy={690 - m / 2} rx={125} ry={65 + m / 2} fill={C.cream} stroke={C.ink} strokeWidth={L.interior} />
      <g transform={`translate(${ex} 0)`}>
        <path d={ANTIFAZ} fill={C.mask} stroke={C.ink} strokeWidth={L.interior} strokeLinejoin="round" />
      </g>
      <Ojo id={`${uid}-oi`} s={-1} cx={-82 + ex} ancho={anchoI} escala={cara.ojo} pupila={cara.pupila} mirada={mirada}
        parpado={cara.parpadoI} cerrado={cara.cerradoI} lagrima={cara.lagrima} />
      <Ojo id={`${uid}-od`} s={1} cx={82 + ex} ancho={anchoD} escala={cara.ojo} pupila={cara.pupila} mirada={mirada}
        parpado={cara.parpadoD} cerrado={cara.cerradoD} lagrima={cara.lagrima} />
      <Ceja ojoX={-82 + ex} s={-1} ceja={cara.cejaI} />
      <Ceja ojoX={82 + ex} s={1} ceja={cara.cejaD} />
      <g transform={`translate(${G} 0)`}>
        <path d="M 0 699 L 0 677" fill="none" strokeWidth={L.interior} {...lineProps} />
        {[[70, 700], [88, 692], [78, 680]].flatMap(([x, y]) => [-1, 1].map((s) => <circle key={`${s}${x}`} cx={s * x} cy={y} r={4} fill={C.ink} />))}
        <path d="M -23 725 Q 0 735 23 725 Q 18 705 0 699 Q -18 705 -23 725 Z" fill={C.ink} />
        <ellipse cx={-7} cy={724} rx={5} ry={3} fill={C.white} />
      </g>
      <Boca tipo={cara.boca} m={m} x={G} uid={uid} />
      <g transform={`rotate(${-mechon} 0 905)`}>
        <path d="M -48 902 L -32 946 L -16 910 L 0 952 L 16 910 L 32 944 L 48 902 Z" fill={C.fur} />
        <path d="M -48 906 L -32 946 L -16 910 L 0 952 L 16 910 L 32 944 L 48 906" fill="none" strokeWidth={L.fina} {...lineProps} />
      </g>
    </g>
  );
};

// Transformación SVG de la cabeza sobre el torso.
export const cabezaTransform = (est) => {
  const salto = est.piernas.salto || 0;
  const cuello = torsoPunto(RIG.cuelloLocal, est.torso, salto);
  const ang = est.torso.inclina + est.cabeza.inclina;
  return `translate(${cuello[0] + est.cabeza.dx} ${cuello[1] + est.cabeza.dy}) rotate(${-ang}) scale(${est.cabeza.sx} ${est.cabeza.sy}) translate(0 -625)`;
};

// Tadeo entero a partir de un estado de acting.estado(). Coordenadas del rig.
export const TadeoPartes = ({ est, uid = "t" }) => {
  const salto = est.piernas.salto || 0;
  const brazo = (lado) => <Brazo key={lado} lado={lado} brazo={est[`brazo${lado}`]} torso={est.torso} salto={salto} />;
  const detras = ["I", "D"].filter((l) => est[`brazo${l}`].capa === "detras");
  const delante = ["I", "D"].filter((l) => est[`brazo${l}`].capa !== "detras");
  return (
    <g>
      <Cola cola={est.cola} />
      {detras.map(brazo)}
      <Pierna lado="I" piernas={est.piernas} />
      <Pierna lado="D" piernas={est.piernas} />
      <Torso torso={est.torso} salto={salto} extra={est.extra} />
      <g transform={cabezaTransform(est)}>
        <CabezaPartes cabeza={est.cabeza} cara={est.cara} mirada={est.mirada} orejas={est.orejas} mechon={est.mechon} uid={uid} />
      </g>
      {delante.map(brazo)}
    </g>
  );
};

export { bezierQ };
