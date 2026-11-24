// Tadeo vectorial por partes (Misión 0001, Fase 2). Las piezas NO son
// primitivas: son los contornos TRAZADOS de la hoja madre (traza.js, generado
// por kx_trazo.py). El rig solo las separa en capas y las mueve.
// Todo en el espacio del rig (u, y hacia arriba): el grupo exterior voltea y.
// Colores: solo INK, PAPER y mezclas TADEO_TONE de la recta INK→PAPER.
import React from "react";
import { INK, PAPER, TADEO_TONE, tone } from "../tokens.js";
import { RIG, brazoCurva, colaAngulo, hombros, manoMundo, piernaPuntos, tangenteFinal, torsoPunto } from "./poses.js";
import { TRAZA } from "./traza.js";

const C = {
  white: PAPER,
  cream: tone(TADEO_TONE.T_CREAM),
  fur: tone(TADEO_TONE.T_FUR),
  mask: tone(TADEO_TONE.T_MASK),
  ink: INK,
};
const TONO = { T_WHITE: C.white, T_CREAM: C.cream, T_FUR: C.fur, T_MASK: C.mask, T_INK: C.ink };
const L = RIG.linea;
const pt = (p) => `${p[0].toFixed(2)},${p[1].toFixed(2)}`;
const lineProps = { stroke: C.ink, strokeLinejoin: "round", strokeLinecap: "round" };

// polígonos trazados → atributo d
const cerrado = (polys) => polys.map((p) => `M ${p.map(pt).join(" L ")} Z`).join(" ");
const abierto = (polys) => polys.map((p) => `M ${p.map(pt).join(" L ")}`).join(" ");
const caja = (polys) => {
  const q = polys.flat();
  const xs = q.map((v) => v[0]);
  const ys = q.map((v) => v[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};

// Pieza trazada: relleno + contorno (o contorno parcial si la pieza continúa en otra capa).
const Pieza = ({ polys, fill, ancho = L.exterior, trazo = null }) => (
  <g>
    <path d={cerrado(polys)} fill={fill} stroke={trazo ? "none" : C.ink} strokeWidth={ancho} strokeLinejoin="round" />
    {trazo ? <path d={abierto(trazo)} fill="none" strokeWidth={ancho} {...lineProps} /> : null}
  </g>
);
const Tinta = ({ polys, color = C.ink }) => <path d={cerrado(polys)} fill={color} />;

// ------------------------------------------------------------ guantes
// Local: muñeca en el origen, dedos hacia +x. `abierta` es el guante TRAZADO
// de cada lado; los demás tipos se construyen a su misma escala.
const cap = (a, b, w) => ({ t: "cap", a, b, w });
const ell = (cx, cy, rx, ry) => ({ t: "ell", cx, cy, rx, ry });
const cir = (cx, cy, r) => ({ t: "ell", cx, cy, rx: r, ry: r });
const FORMAS = {
  palma: [ell(76, 0, 52, 58), cap([92, 32], [156, 66], 32), cap([98, 6], [178, 14], 32), cap([94, -24], [166, -42], 32), cap([56, 46], [74, 104], 32)],
  puno: [ell(70, 0, 54, 58), cir(112, 34, 22), cir(120, 0, 23), cir(112, -34, 22), cap([62, 44], [104, 22], 30)],
  senala: [ell(70, 0, 54, 58), cap([96, -28], [196, -30], 32), cir(112, 12, 22), cir(106, 42, 20), cap([60, 46], [100, 30], 30)],
  agarra: [ell(70, 0, 54, 58), cap([92, -30], [152, -18], 30), cap([62, 46], [146, 4], 30), cir(104, -50, 18)],
};
const INTERIOR = {
  palma: ["M 52 -20 Q 76 -6 96 -22", "M 50 18 Q 70 30 84 12"],
  puno: ["M 100 18 L 130 16", "M 100 -18 L 130 -16"],
  senala: ["M 98 28 L 124 26"],
  agarra: ["M 96 -6 Q 120 0 140 -8"],
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
  if (tipo === "abierta" || !FORMAS[tipo]) {
    // trazado: cada lado trae su propio dibujo, ya orientado (sin espejo)
    const g = TRAZA.guantes[lado];
    return (
      <g transform={`translate(${x} ${y}) rotate(${angulo})`}>
        <Pieza polys={g.forma} fill={C.white} />
        <Tinta polys={g.lineas} />
      </g>
    );
  }
  const fs = FORMAS[tipo];
  const k = ESCALA_GUANTE;
  const e = L.exterior / k;
  return (
    <g transform={`translate(${x} ${y}) rotate(${angulo}) scale(${k} ${k * espejo})`}>
      <rect x={-6} y={-60 - e} width={38 + 2 * e} height={120 + 2 * e} rx={19 + e} fill={C.ink} />
      {fs.map((f, i) => formaSVG(f, e, C.ink, `o${i}`))}
      {fs.map((f, i) => formaSVG(f, 0, C.white, `f${i}`))}
      <rect x={1} y={-60} width={38} height={120} rx={19} fill={C.white} stroke={C.ink} strokeWidth={L.interior / k} />
      {(INTERIOR[tipo] || []).map((d, i) => <path key={i} d={d} fill="none" strokeWidth={L.fina / k} {...lineProps} />)}
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

// El guante trazado se midió con la tangente del brazo trazado: el ángulo de
// reposo es la tangente final; `giro` lo desvía (en espejo I/D).
export const Brazo = ({ lado, brazo, torso, salto, parte = "todo" }) => {
  const h = hombros(torso, salto)[lado];
  const mano = manoMundo(brazo.mano, torso, salto);
  const pts = brazoCurva(h, mano, brazo.curva);
  const espejo = lado === "D" ? -1 : 1;
  const giro = lado === "D" ? brazo.giro : -brazo.giro;
  return (
    <g>
      {parte !== "guante" ? <Tubo pts={pts} grosor={RIG.brazo.grosor} /> : null}
      {parte !== "tubo" ? <Guante tipo={brazo.guante} lado={lado} x={mano[0]} y={mano[1]} angulo={tangenteFinal(pts) + giro} espejo={espejo} /> : null}
    </g>
  );
};

const Pierna = ({ lado, piernas }) => {
  const pts = piernaPuntos(lado, piernas);
  const s = lado === "I" ? -1 : 1;
  const t = pts[2];
  const ang = s * ((piernas[lado === "I" ? "pieI" : "pieD"] ?? 12) - 12); // 12° = el pie del dibujo
  const pie = TRAZA.pies[lado];
  return (
    <g>
      <Tubo pts={pts} grosor={RIG.pierna.grosor} />
      <g transform={`translate(${t[0]} ${t[1]}) rotate(${-ang})`}>
        <Pieza polys={pie.forma} fill={C.mask} />
        <Tinta polys={pie.lineas} />
      </g>
    </g>
  );
};

// ------------------------------------------------------------ cola
export const Cola = ({ cola }) => {
  const [bx, by] = RIG.cola.base;
  return (
    <g transform={`rotate(${colaAngulo(cola)} ${bx} ${by})`}>
      <Pieza polys={TRAZA.cola.forma} fill={C.fur} />
      <Pieza polys={TRAZA.cola.bandas} fill={C.mask} ancho={L.interior} />
    </g>
  );
};

// ------------------------------------------------------------ torso
export const Torso = ({ torso, salto, extra }) => {
  const [px, py] = RIG.torsoPivote;
  const tr = `translate(0 ${salto}) translate(${px} ${py}) rotate(${-torso.inclina}) scale(${torso.sx} ${torso.sy}) translate(${-px} ${-py})`;
  return (
    <g transform={tr}>
      <Pieza polys={TRAZA.torso.forma} fill={C.fur} />
      <Pieza polys={TRAZA.panza.forma} trazo={TRAZA.panza.trazo} fill={C.cream} ancho={L.interior} />
      <Tinta polys={TRAZA.detalles_torso} />
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
// Boca de cada expresión: las 6 de la hoja madre se trazan; las otras 4 se
// derivan transformando una trazada (mismo trazo, otra forma).
const BOCAS = {
  sonrisa: { de: "frente" },
  o: { de: "asombro" },
  triste: { de: "triste" },
  apretada: { de: "decidido" },
  ladeada: { de: "guino" },
  risa: { de: "risa" },
  grito: { de: "risa", sx: 0.82, sy: 1.55 },
  ondulada: { de: "decidido", sx: 0.7, sy: 1.0, rot: -7 },
  ancha: { de: "frente", sx: 1.12, sy: 1.3 },
  temblorosa: { de: "triste", sx: 0.92, sy: 1.25, rot: 4 },
};

// Risa y grito: en la hoja madre la risa está dibujada en 3/4 y no encaja en
// la cara frontal. Se derivan de la sonrisa TRAZADA del frente: mismas
// comisuras y misma curva de arriba; debajo, la boca abierta.
const bocaAbiertaGeo = (tipo, m) => {
  const [fx0, , fx1] = caja(EXPR.frente.boca);
  const cx = (fx0 + fx1) / 2;
  const hw = ((fx1 - fx0) / 2) * (tipo === "grito" ? 0.62 : 0.86);
  const nariz = caja(TRAZA.nariz.forma)[1];
  const top = nariz - 26; // las comisuras de la sonrisa trazada, bajo la nariz
  const mid = top - 22;
  const H = 35 + 1.5 * m; // la mandíbula baja con la boca
  return { cx, hw, top, mid, H };
};

// La quijada que asoma bajo la barbilla cuando la boca se abre (va DETRÁS del
// cráneo: solo se ve lo que baja del mentón).
const Mandibula = ({ tipo, m, x }) => {
  const { cx, hw, top, H } = bocaAbiertaGeo(tipo, m);
  const chin = RIG.cuelloLocal[1];
  const fondo = top - H - 16;
  const cy = (chin + 50 + fondo) / 2;
  const ry = (chin + 50 - fondo) / 2;
  return <ellipse cx={cx + x} cy={cy} rx={hw + 34} ry={ry} fill={C.cream} stroke={C.ink} strokeWidth={L.exterior} />;
};

const BocaAbierta = ({ tipo, x, uid, m }) => {
  const { cx, hw, top, mid, H } = bocaAbiertaGeo(tipo, m);
  const d = `M ${cx - hw} ${top} Q ${cx} ${mid - 8} ${cx + hw} ${top} C ${cx + hw} ${top - H * 0.8} ${cx + hw * 0.45} ${top - H} ${cx} ${top - H} C ${cx - hw * 0.45} ${top - H} ${cx - hw} ${top - H * 0.8} ${cx - hw} ${top} Z`;
  const id = `${uid}-boca`;
  return (
    <g transform={`translate(${x} 0)`}>
      <clipPath id={id}><path d={d} /></clipPath>
      <path d={d} fill={C.ink} />
      <g clipPath={`url(#${id})`}>
        <rect x={cx - hw} y={mid - 30} width={2 * hw} height={34} fill={C.white} />
        <ellipse cx={cx} cy={top - H} rx={hw * 0.55} ry={H * 0.33} fill={C.mask} />
      </g>
      <path d={d} fill="none" strokeWidth={L.interior} {...lineProps} />
    </g>
  );
};

const area = (p) => Math.abs(p.reduce((a, q, i) => { const r = p[(i + 1) % p.length]; return a + q[0] * r[1] - r[0] * q[1]; }, 0)) / 2;

const ABIERTAS = new Set(["risa", "grito"]);
const Boca = ({ tipo, x, uid }) => {
  if (ABIERTAS.has(tipo)) return null; // se dibuja fuera del recorte del cráneo
  const def = BOCAS[tipo] || BOCAS.sonrisa;
  const src0 = EXPR[def.de];
  if (!src0 || !src0.boca.length) return null;
  // la «o» de asombro: solo la pieza mayor (el resto es pelo de la mejilla en 3/4)
  const src = tipo === "o" ? { ...src0, boca: [src0.boca.reduce((a, b) => (area(b) > area(a) ? b : a))], boca_relleno: [] } : src0;
  const [x0, y0, x1, y1] = caja(src.boca);
  const cx = (x0 + x1) / 2;
  // las cabezas de la hoja no están todas de frente (guiño y risa vienen en
  // 3/4): cada boca se recoloca sobre la sonrisa del frente. Las abiertas
  // cuelgan de su borde de arriba; las de línea, de su centro.
  const [fx0, fy0, fx1, fy1] = caja(EXPR.frente.boca);
  const abierta = ["o", "risa", "grito"].includes(tipo);
  const dx = (fx0 + fx1) / 2 - cx + (tipo === "o" ? 18 : 0);
  const dy = abierta ? fy1 - y1 - 4 : (fy0 + fy1) / 2 - (y0 + y1) / 2;
  const tr = `translate(${x + dx} ${dy}) translate(${cx} ${y1}) rotate(${def.rot || 0}) scale(${def.sx || 1} ${def.sy || 1}) translate(${-cx} ${-y1})`;
  return (
    <g transform={tr}>
      {src.boca_relleno.map((r, i) => <Tinta key={i} polys={r.forma} color={TONO[r.tono]} />)}
      <Tinta polys={src.boca} />
    </g>
  );
};

// Ceja trazada (la neutra) movida por los parámetros de la expresión:
// interior/exterior suben o bajan cada extremo (u); arco la curva un poco.
const Ceja = ({ lado, ceja, dx }) => {
  const c = TRAZA.cejas[lado];
  const s = lado === "I" ? 1 : -1; // en I el extremo interior es el derecho
  const ang = (Math.atan2((ceja.interior - ceja.exterior) * s, c.largo) * 180) / Math.PI;
  const dy = (ceja.interior + ceja.exterior) / 2;
  const sy = 1 + ((ceja.arco ?? 8) - 8) * 0.03;
  const [cx, cy] = c.centro;
  return (
    <g transform={`translate(${dx} ${dy}) rotate(${ang} ${cx} ${cy}) translate(${cx} ${cy}) scale(1 ${sy}) translate(${-cx} ${-cy})`}>
      <Tinta polys={c.forma} />
    </g>
  );
};

const Ojo = ({ lado, uid, ancho, escala, pupila, mirada, parpado, cerrado: estaCerrado, lagrima, cerradoTrazado, dx }) => {
  const o = TRAZA.ojos[lado];
  const [cx, cy] = o.centro;
  const s = lado === "I" ? -1 : 1;
  const tr = `translate(${dx} 0) translate(${cx} ${cy}) scale(${ancho * escala} ${escala}) translate(${-cx} ${-cy})`;
  if (estaCerrado) {
    if (cerradoTrazado && cerradoTrazado.length) {
      const [a0, b0, a1, b1] = caja(cerradoTrazado);
      return (
        <g transform={`translate(${dx + cx - (a0 + a1) / 2} ${cy - (b0 + b1) / 2})`}>
          <Tinta polys={cerradoTrazado} />
        </g>
      );
    }
    return <path transform={`translate(${dx} 0)`} d={`M ${cx - 32} ${cy - 6} Q ${cx} ${cy + 30} ${cx + 32} ${cy - 6}`} fill="none" strokeWidth={10} {...lineProps} />;
  }
  const p = o.pupila;
  const px = p.centro[0] + mirada.x * 16;
  const py = p.centro[1] + mirada.y * 20;
  const ry = o.ry;
  const lidY = cy + ry - parpado * 2 * ry;
  const id = `${uid}-ojo${lado}`;
  return (
    <g>
      <g transform={tr}>
        <clipPath id={id}><path d={cerrado(o.forma)} /></clipPath>
        <path d={cerrado(o.forma)} fill={C.white} />
        <g clipPath={`url(#${id})`}>
          <ellipse cx={px} cy={py} rx={p.rx * pupila} ry={p.ry * pupila} fill={C.ink} />
          <circle cx={px - p.rx * 0.35} cy={py + p.ry * 0.45} r={p.rx * 0.32} fill={C.white} />
          {parpado > 0.01 ? (
            <g>
              <rect x={cx - o.rx - 8} y={lidY} width={2 * o.rx + 16} height={2 * ry + 16} fill={C.mask} />
              <path d={`M ${cx - o.rx - 8} ${lidY + 3} Q ${cx} ${lidY - 6} ${cx + o.rx + 8} ${lidY + 3}`} fill="none" strokeWidth={L.interior + 1} {...lineProps} />
            </g>
          ) : null}
        </g>
        <path d={cerrado(o.forma)} fill="none" stroke={C.ink} strokeWidth={L.interior} />
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
  const oreja = (lado) => {
    const o = TRAZA.orejas[lado];
    const ang = lado === "I" ? orejas.i : -orejas.d;
    const [px, py] = o.pivote;
    return (
      <g key={lado} transform={`translate(${-0.3 * G} 0) rotate(${ang} ${px} ${py})`}>
        <Pieza polys={o.forma} fill={C.fur} />
        <Tinta polys={o.interior} color={C.cream} />
      </g>
    );
  };
  const [mx, my] = TRAZA.mechon.pivote;
  return (
    <g>
      <clipPath id={clip}><path d={cerrado(TRAZA.craneo.forma)} /></clipPath>
      {oreja("I")}
      {oreja("D")}
      <g transform={`rotate(${-mechon} ${mx} ${my})`}>
        <Pieza polys={TRAZA.mechon.forma} fill={C.fur} />
      </g>
      {ABIERTAS.has(cara.boca) ? <Mandibula tipo={cara.boca} m={Math.max(20, cara.mandibula)} x={0.9 * G} /> : null}
      <Pieza polys={TRAZA.craneo.forma} fill={C.fur} trazo={TRAZA.craneo.trazo} />
      <g clipPath={`url(#${clip})`}>
        <g transform={`translate(${0.5 * G} 0)`}><Tinta polys={TRAZA.crema_cara} color={C.cream} /></g>
        <Tinta polys={TRAZA.detalles_cabeza} />
        <g transform={`translate(${ex} 0)`}>
          <Pieza polys={TRAZA.antifaz.I} fill={C.mask} ancho={L.interior} />
          <Pieza polys={TRAZA.antifaz.D} fill={C.mask} ancho={L.interior} />
        </g>
        <Ojo lado="I" uid={uid} dx={ex} ancho={anchoI} escala={cara.ojo} pupila={cara.pupila} mirada={mirada}
          parpado={cara.parpadoI} cerrado={cara.cerradoI} lagrima={cara.lagrima} cerradoTrazado={fc && fc.cerrado.I} />
        <Ojo lado="D" uid={uid} dx={ex} ancho={anchoD} escala={cara.ojo} pupila={cara.pupila} mirada={mirada}
          parpado={cara.parpadoD} cerrado={cara.cerradoD} lagrima={cara.lagrima} cerradoTrazado={fc && fc.cerrado.D} />
        <Ceja lado="I" ceja={cara.cejaI} dx={ex} />
        <Ceja lado="D" ceja={cara.cejaD} dx={ex} />
        <g transform={`translate(${G} 0)`}>
          <Tinta polys={TRAZA.nariz.forma} />
          <Tinta polys={TRAZA.nariz.brillo} color={C.white} />
        </g>
        <Boca tipo={cara.boca} x={0.9 * G} uid={uid} />
      </g>
      {ABIERTAS.has(cara.boca) ? <BocaAbierta tipo={cara.boca} m={Math.max(20, cara.mandibula)} x={0.9 * G} uid={uid} /> : null}
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
