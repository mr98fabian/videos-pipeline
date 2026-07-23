import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  useCurrentFrame,
  Easing,
} from "remotion";

// ============================================================================
// ARCHIVO VIVO — libreria de componentes del motor visual (Tier 1)
// Estilo aprobado 23 jul 2026 (ver memoria estilo-archivo-vivo):
//   cero blur / tablero pergamino / troquelado vs foto clavada / rojo marcador
//   / punch-zooms / cortes duros / SFX por golpe / 3D de perspectiva sutil
// ============================================================================

export const INK = "#1a1208";
export const GOLD = "#FFD700";
export const RED = "#D7263D";
export const PAPER_BASE = "#E6D7B8";
export const PAPER_LIGHT = "#F7F1E1";

// --- easings de la casa ------------------------------------------------------
export const POP_EASE = Easing.bezier(0.18, 1.65, 0.35, 1); // overshoot punchy
export const SLAM_EASE = Easing.bezier(0.2, 0.9, 0.3, 1); // golpe seco

export const pop = (local, dur = 8) =>
  interpolate(local, [0, dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: POP_EASE,
  });

// ============================================================================
// CAMARA: beats de zoom-evidencia + shakes de impacto
//   beats:  [{frame, scale, x, y}]  — la camara viaja a ese objetivo en ~6f
//   shakes: [{frame, amp, dur}]     — sacudida de impacto (determinista)
// ============================================================================
export const makeCamera = (beats = [], shakes = []) => (frame) => {
  let scale = 1.02;
  let x = 0;
  let y = 0;
  for (const b of beats) {
    const p = interpolate(frame, [b.frame, b.frame + (b.dur ?? 6)], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: SLAM_EASE,
    });
    scale += (b.scale - 1.02) * p - (scale - 1.02) * p; // easa hacia el objetivo
    x += (b.x - x) * p;
    y += (b.y - y) * p;
  }
  for (const s of shakes) {
    const local = frame - s.frame;
    if (local >= 0 && local < (s.dur ?? 5)) {
      const decay = 1 - local / (s.dur ?? 5);
      x += Math.sin(local * 13.7) * (s.amp ?? 7) * decay;
      y += Math.cos(local * 11.3) * (s.amp ?? 7) * 0.7 * decay;
    }
  }
  return { scale, x, y };
};

// ============================================================================
// TABLERO de pergamino (nitido siempre) con perspectiva 3D sutil
// ============================================================================
export const Board = ({ children, camera, tilt3d = true }) => {
  const frame = useCurrentFrame();
  const cam = camera ? camera(frame) : { scale: 1.02, x: 0, y: 0 };
  // respiracion 3D del tablero: rotacion minima que vende "mesa fisica"
  const rx = tilt3d ? Math.sin(frame / 47) * 1.5 : 0;
  const ry = tilt3d ? Math.cos(frame / 53) * 1.9 : 0;
  return (
    <AbsoluteFill style={{ background: PAPER_BASE, overflow: "hidden", perspective: 1400 }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 20% 15%, rgba(122,90,44,0.18) 0%, transparent 40%)," +
            "radial-gradient(circle at 85% 70%, rgba(122,90,44,0.15) 0%, transparent 35%)," +
            "radial-gradient(circle at 60% 25%, rgba(90,60,20,0.10) 0%, transparent 30%)," +
            "radial-gradient(ellipse at center, transparent 60%, rgba(60,40,12,0.35) 100%)",
        }}
      />
      <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.08 }}>
        <filter id="paperfiber">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" seed="7" />
        </filter>
        <rect width="100%" height="100%" filter="url(#paperfiber)" />
      </svg>
      <AbsoluteFill
        style={{
          scale: `${cam.scale}`,
          translate: `${cam.x}px ${cam.y}px`,
          transform: `rotateX(${rx}deg) rotateY(${ry}deg)`,
        }}
      >
        {children}
      </AbsoluteFill>
      <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.06, pointerEvents: "none" }}>
        <filter id={`grainlive-${frame % 5}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={frame % 5} stitchTiles="stitch" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grainlive-${frame % 5})`} />
      </svg>
    </AbsoluteFill>
  );
};

// --- Fondo "impresion lavada" (nitido, multiply) ----------------------------
export const Backdrop = ({ src, sceneDur = 150 }) => {
  const frame = useCurrentFrame();
  const s = interpolate(frame, [0, sceneDur], [1.08, 1.15]);
  const px = Math.sin(frame / 41) * 14; // contrafase vs camara = paralaje
  const py = Math.cos(frame / 57) * 9;
  return (
    <AbsoluteFill style={{ scale: `${s}`, translate: `${px}px ${py}px` }}>
      <Img
        src={src}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.17,
          mixBlendMode: "multiply",
          filter: "contrast(1.15) saturate(0.7)",
        }}
      />
    </AbsoluteFill>
  );
};

// ============================================================================
// RECORTES con entrada FLIP 3D
// ============================================================================
const DIE_CUT =
  [0, 45, 90, 135, 180, 225, 270, 315]
    .map((deg) => {
      const r = 6;
      const dx = (Math.cos((deg * Math.PI) / 180) * r).toFixed(1);
      const dy = (Math.sin((deg * Math.PI) / 180) * r).toFixed(1);
      return `drop-shadow(${dx}px ${dy}px 0px ${PAPER_LIGHT})`;
    })
    .join(" ") + " drop-shadow(14px 18px 0px rgba(26,18,8,0.55))";

// ============================================================================
// CAPA DE ACCION — el recorte (pose fija) se transforma para ACTUAR el verbo
// que narra esa escena, sincronizado con la voz. Devuelve transform extra.
//   action = { type, at, dur }   (at = frame local en que dispara)
// ============================================================================
const actionMotion = (action, local) => {
  const z = { dx: 0, dy: 0, rot: 0, scale: 1, popZ: 0, origin: "center" };
  if (!action) return z;
  const al = local - (action.at ?? 6);
  if (al < 0) return z;
  const dur = action.dur ?? 16;
  const p = interpolate(al, [0, dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const decay = Math.max(0, 1 - al / 16);
  switch (action.type) {
    case "explosion":
    case "impact":
      z.dx = Math.sin(al * 9) * 30 * decay;
      z.dy = Math.cos(al * 11) * 18 * decay;
      z.scale = 1 + 0.06 * decay;
      z.popZ = 40 * decay; // salta hacia adelante en Z (3D visible)
      break;
    case "recoil":
      z.dx = interpolate(al, [0, 4, dur], [0, -70, 0], { extrapolateRight: "clamp", easing: SLAM_EASE });
      z.rot = interpolate(al, [0, 4, dur], [0, -12, 0], { extrapolateRight: "clamp" });
      break;
    case "topple":
    case "fall":
    case "collapse":
      z.rot = interpolate(al, [0, dur], [0, 82], { extrapolateRight: "clamp", easing: Easing.bezier(0.6, 0, 0.9, 0.35) });
      z.dy = interpolate(al, [0, dur], [0, 70], { extrapolateRight: "clamp" });
      z.origin = "bottom center";
      break;
    case "flee":
    case "escape":
      z.dx = interpolate(al, [0, dur + 8], [0, 980], { extrapolateRight: "clamp", easing: Easing.bezier(0.5, 0, 0.9, 0.4) });
      z.rot = 6;
      break;
    case "sink":
      z.dy = interpolate(al, [0, dur + 10], [0, 540], { extrapolateRight: "clamp", easing: Easing.in(Easing.quad) });
      z.scale = 1 - 0.28 * p;
      break;
    case "rise":
      z.dy = interpolate(al, [0, dur], [240, 0], { extrapolateRight: "clamp", easing: POP_EASE });
      break;
    case "shoot":
    case "lunge":
      z.scale = 1 + interpolate(al, [0, 4, 12], [0, 0.14, 0], { extrapolateRight: "clamp" });
      z.dx = interpolate(al, [0, 4, 12], [0, 26, 0], { extrapolateRight: "clamp" });
      z.popZ = interpolate(al, [0, 4, 12], [0, 30, 0], { extrapolateRight: "clamp" });
      break;
  }
  return z;
};

export const Cutout = ({ src, from, x, y, w, h, fromDir = "bottom", rot = -2, driftAmp = 5, action = null }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 9);
  const offX = fromDir === "right" ? 700 * (1 - p) : fromDir === "left" ? -700 * (1 - p) : 0;
  const offY = fromDir === "bottom" ? 800 * (1 - p) : fromDir === "top" ? -800 * (1 - p) : 0;
  const flip = (fromDir === "right" ? -55 : 55) * (1 - p); // 3D: gira al aterrizar
  const drift = Math.sin(local / 13) * driftAmp;
  const tilt = rot + Math.sin(local / 17) * 1.6;
  const a = actionMotion(action, local); // actua el verbo de la escena
  return (
    <div style={{ position: "absolute", left: x, top: y + drift, width: w, height: h, perspective: 1200 }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          translate: `${offX + a.dx}px ${offY + a.dy}px`,
          rotate: `${tilt + a.rot}deg`,
          scale: `${(0.85 + 0.15 * p) * a.scale}`,
          transform: `rotateY(${flip}deg) translateZ(${a.popZ}px)`,
          transformOrigin: a.origin,
        }}
      >
        <Img src={src} style={{ width: "100%", height: "100%", objectFit: "contain", filter: DIE_CUT }} />
      </div>
    </div>
  );
};

// FX de comic encima de la accion: estrella de impacto, palabra ("BOOM"),
// lineas de velocidad. Comunica el verbo al instante, estilo Nickelodeon.
const _ACTION_WORD = { explosion: "BOOM", impact: "BANG", shoot: "BANG", topple: "CRASH", fall: "CRASH", collapse: "CRASH" };
export const ActionFX = ({ action, cx = 540, cy = 640, from = 0 }) => {
  const frame = useCurrentFrame();
  if (!action) return null;
  const al = frame - from - (action.at ?? 6);
  if (al < 0 || al > 34) return null;
  const t = action.type;
  const burst = ["explosion", "impact", "shoot", "topple", "fall", "collapse"].includes(t);
  const streak = ["flee", "escape"].includes(t);
  const word = _ACTION_WORD[t];
  const rays = 12;
  const rBurst = interpolate(al, [0, 8], [10, 320], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: POP_EASE });
  const oBurst = interpolate(al, [4, 20], [0.95, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const wScale = interpolate(al, [0, 4], [2.4, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const wO = interpolate(al, [0, 3, 22, 30], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <svg width={1080} height={1920} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none", overflow: "visible" }}>
      {burst && oBurst > 0 && Array.from({ length: rays }).map((_, k) => {
        const ang = (k / rays) * Math.PI * 2 + (action.at ?? 0);
        const r0 = rBurst * 0.45, r1 = rBurst;
        return (
          <line key={k} x1={cx + Math.cos(ang) * r0} y1={cy + Math.sin(ang) * r0}
                x2={cx + Math.cos(ang) * r1} y2={cy + Math.sin(ang) * r1}
                stroke={GOLD} strokeWidth={10} strokeLinecap="round" opacity={oBurst} />
        );
      })}
      {streak && Array.from({ length: 6 }).map((_, k) => {
        const sp = interpolate(al, [0, 10], [0, 1], { extrapolateRight: "clamp" });
        const yy = cy - 160 + k * 60;
        const x1 = cx - 40 - sp * 520, x2 = x1 + 130;
        return <line key={k} x1={x1} y1={yy} x2={x2} y2={yy} stroke={RED} strokeWidth={9} strokeLinecap="round"
                     opacity={interpolate(al, [0, 4, 16], [0, 0.85, 0], { extrapolateRight: "clamp" })} />;
      })}
      {word && (
        <text x={cx} y={cy - 210} textAnchor="middle" fontFamily="Arial Black, sans-serif" fontWeight={900}
              fontSize={130} fill={RED} stroke={PAPER_LIGHT} strokeWidth={8} paintOrder="stroke"
              opacity={wO} transform={`rotate(-8 ${cx} ${cy - 210}) scale(${wScale})`}
              style={{ transformBox: "fill-box", transformOrigin: "center" }}>{word}</text>
      )}
    </svg>
  );
};

export const PhotoScrap = ({ src, from, x, y, w, h, fromDir = "right", rot = 2, children }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 9);
  const offX = fromDir === "right" ? 800 * (1 - p) : fromDir === "left" ? -800 * (1 - p) : 0;
  const flip = (fromDir === "right" ? -60 : 60) * (1 - p);
  const drift = Math.sin(local / 15) * 4;
  const tilt = rot + Math.sin(local / 19) * 1.2;
  return (
    <div style={{ position: "absolute", left: x, top: y + drift, width: w, height: h, perspective: 1200 }}>
      <div
        style={{
          width: "100%",
          height: "100%",
          translate: `${offX}px 0px`,
          rotate: `${tilt}deg`,
          scale: `${0.9 + 0.1 * p}`,
          transform: `rotateY(${flip}deg)`,
          background: PAPER_LIGHT,
          padding: 18,
          boxShadow: "16px 20px 0 rgba(26,18,8,0.5)",
          border: `4px solid ${INK}`,
        }}
      >
        <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", border: `3px solid ${INK}` }} />
        <div style={{ position: "absolute", left: -26, top: -14, width: 120, height: 42, background: "rgba(214,196,150,0.85)", rotate: "-38deg", boxShadow: "0 2px 6px rgba(26,18,8,0.25)" }} />
        <div style={{ position: "absolute", right: -26, bottom: -14, width: 120, height: 42, background: "rgba(214,196,150,0.85)", rotate: "-38deg", boxShadow: "0 2px 6px rgba(26,18,8,0.25)" }} />
        {children}
      </div>
    </div>
  );
};

// ============================================================================
// TIER 1.1 — BARRA CENSURADA que se ARRANCA en el reveal
// ============================================================================
export const CensorBar = ({ x, y, w, h, from = 0, revealFrame, label = "CENSORED" }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const enter = pop(local, 6);
  const ripLocal = frame - revealFrame;
  const ripping = ripLocal >= 0;
  // vuelo del arrancazo: sube-derecha girando, con "tiron" inicial
  const fly = ripping
    ? interpolate(ripLocal, [0, 11], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.4, 0, 0.9, 0.4),
      })
    : 0;
  const grab = ripping
    ? interpolate(ripLocal, [0, 2], [0, -6], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;
  if (fly >= 1) return null;
  const wob = Math.sin(local / 9) * 1.2;
  // borde rasgado: zigzag inferior via clip-path
  const jag =
    "polygon(0% 0%, 100% 0%, 100% 78%, 94% 88%, 87% 76%, 79% 90%, 71% 78%, 63% 92%, 55% 80%, 47% 90%, 39% 78%, 31% 92%, 23% 80%, 15% 90%, 7% 78%, 0% 88%)";
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y + grab,
        width: w,
        height: h,
        translate: `${fly * 620}px ${fly * -760}px`,
        rotate: `${wob + fly * -38}deg`,
        scale: `${enter}`,
        opacity: 1 - fly * 0.25,
        background: "#141210",
        clipPath: jag,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "8px 10px 0 rgba(26,18,8,0.4)",
      }}
    >
      <span
        style={{
          fontFamily: "Arial Black, sans-serif",
          fontWeight: 900,
          fontSize: Math.min(h * 0.42, 46),
          color: RED,
          letterSpacing: 6,
          border: `4px solid ${RED}`,
          padding: "4px 18px",
          rotate: "-3deg",
          opacity: 0.92,
        }}
      >
        {label}
      </span>
    </div>
  );
};

// ============================================================================
// TIER 1.2 — HILO ROJO de conspiracion entre dos pines
// ============================================================================
export const RedString = ({ from, to, drawFrame, sag = 55 }) => {
  const frame = useCurrentFrame();
  const local = frame - drawFrame;
  if (local < 0) return null;
  const drawn = interpolate(local, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.3, 0, 0.2, 1),
  });
  const pinP = pop(local, 5);
  const pin2P = pop(local - 8, 5);
  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2 + sag; // comba de cuerda real
  const path = `M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`;
  const Pin = ({ cx, cy, p }) => (
    <g style={{ scale: `${p}`, transformOrigin: `${cx}px ${cy}px` }}>
      <circle cx={cx} cy={cy} r={16} fill={RED} stroke={INK} strokeWidth={5} />
      <circle cx={cx - 5} cy={cy - 5} r={4} fill="#FF8B96" />
    </g>
  );
  return (
    <svg width="1080" height="1920" style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}>
      {/* sombra de la cuerda */}
      <path d={path} stroke="rgba(26,18,8,0.35)" strokeWidth={9} fill="none" strokeLinecap="round"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - drawn} style={{ translate: "4px 7px" }} />
      <path d={path} stroke={RED} strokeWidth={7} fill="none" strokeLinecap="round"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - drawn} />
      <Pin cx={from.x} cy={from.y} p={pinP} />
      <Pin cx={to.x} cy={to.y} p={pin2P} />
    </svg>
  );
};

// ============================================================================
// TIER 1.3 — FLASH de impacto (el shake vive en makeCamera)
// ============================================================================
export const ImpactFlash = ({ frames = [] }) => {
  const frame = useCurrentFrame();
  let o = 0;
  for (const f of frames) {
    const local = frame - f;
    if (local >= 0 && local < 3) o = Math.max(o, interpolate(local, [0, 2], [0.75, 0]));
  }
  if (o <= 0) return null;
  return <AbsoluteFill style={{ background: "#FFF8E7", opacity: o, pointerEvents: "none" }} />;
};

// ============================================================================
// Texto cinetico, sello, marcador (portados del proof aprobado)
// ============================================================================
export const Kinetic = ({ words, from, wordDur = 7, size = 76, bottom = 560 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const activeIdx = Math.min(Math.floor(local / wordDur), words.length - 1);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: bottom, pointerEvents: "none" }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px 14px", maxWidth: 900 }}>
        {words.map((w, i) => {
          const wStart = i * wordDur;
          if (local < wStart) return null;
          const p = pop(local - wStart, 6);
          const isActive = i === activeIdx;
          const jit = ((i * 37) % 7) - 3;
          return (
            <span
              key={i}
              style={{
                fontFamily: "Arial Black, sans-serif",
                fontWeight: 900,
                fontSize: isActive ? size + 14 : size,
                color: isActive ? GOLD : "#FFF",
                scale: `${p}`,
                rotate: `${jit * 0.4}deg`,
                display: "inline-block",
                textShadow:
                  "4px 4px 0 #1a1208, -3px -3px 0 #1a1208, 3px -3px 0 #1a1208, -3px 3px 0 #1a1208, 0 10px 24px rgba(0,0,0,0.5)",
              }}
            >
              {w.toUpperCase()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const Stamp = ({ text, from, x, y, rot = -8, color = RED }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const s = interpolate(local, [0, 4], [2.3, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const o = interpolate(local, [0, 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute", left: x, top: y, rotate: `${rot}deg`, scale: `${s}`, opacity: o * 0.95,
        border: `9px solid ${color}`, borderRadius: 10, padding: "10px 26px",
        boxShadow: `0 0 0 3px ${PAPER_BASE}, 0 0 0 6px ${color}`,
      }}
    >
      <span style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 54, color, letterSpacing: 4 }}>
        {text}
      </span>
    </div>
  );
};

// ============================================================================
// MARGINALIA DE EXPEDIENTE — llena el papel en blanco de la tarjeta con
// anotaciones de investigador dibujadas a mano (etiqueta + flecha al sujeto +
// circulo + "?"), que se trazan solas. Convierte el vacio en narrativa.
// Coordenadas relativas a la tarjeta 840x940 (se renderiza como hijo del card).
// ============================================================================
const _HANDWRITE = "'Segoe Print', 'Ink Free', 'Bradley Hand', 'Comic Sans MS', cursive";
const _CASE_LABELS = [
  "WHO?", "UNKNOWN", "SUSPECT", "NO FILE",
  "SEALED", "REDACTED", "AGENT ?", "OPEN",
];

// trazo animado generico (dibuja el path de 0 a 1 en [f0,f1])
const _Draw = ({ d, from, dur = 8, w = 7, delay = 0, dash = false }) => {
  const frame = useCurrentFrame();
  const drawn = interpolate(frame - from - delay, [0, dur], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: Easing.bezier(0.3, 0, 0.2, 1),
  });
  return (
    <path
      d={d} stroke={RED} strokeWidth={w} fill="none" strokeLinecap="round" strokeLinejoin="round"
      pathLength={1} strokeDasharray={dash ? "10 12" : 1} strokeDashoffset={1 - drawn}
      style={{ opacity: 0.9 }}
    />
  );
};

// sello de expediente compacto dentro del SVG (rect + texto), golpea al entrar
const _MiniStamp = ({ x, y, rot, text, from, delay = 0, size = 30 }) => {
  const frame = useCurrentFrame();
  const local = frame - from - delay;
  if (local < 0) return null;
  const s = interpolate(local, [0, 4], [2.1, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const o = interpolate(local, [0, 3], [0, 0.82], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const w = text.length * size * 0.62 + 26;
  const h = size + 20;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s})`} opacity={o}>
      <rect x={0} y={0} width={w} height={h} rx={6} fill="none" stroke={RED} strokeWidth={4} />
      <text x={w / 2} y={h / 2 + size * 0.36} textAnchor="middle" fontFamily="Arial Black, sans-serif"
            fontWeight={900} fontSize={size} fill={RED} style={{ letterSpacing: 2 }}>{text}</text>
    </g>
  );
};

export const CaseAnnotations = ({ from = 8, index = 0 }) => {
  const frame = useCurrentFrame();
  if (frame - from < 0) return null;
  const alt = index % 2 === 0;
  const label = _CASE_LABELS[index % _CASE_LABELS.length];
  // jitter idle sutil de tinta (todo respira)
  const j = Math.sin((frame - from) / 24) * 1.2;
  // TODA la marginalia va en las ESQUINAS del papel (extremas arriba, e inferiores):
  // zona fiablemente vacia (el sujeto se para centrado, cabeza/brazos al centro).
  // Asi nunca choca con el sujeto ni se sale del borde, angosto o ancho.
  const labelWrite = interpolate(frame - from, [0, 10], [0, label.length], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const arrow = "M 150 815 Q 250 720, 340 640";       // nota -> sujeto
  const head = "M 340 640 L 356 674 M 340 640 L 304 656";
  const qO = interpolate(frame - from, [10, 20], [0, 0.4], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const caseNo = `Nº 0${(index % 9) + 1}`;
  const exhibit = `EXHIBIT ${String.fromCharCode(65 + (index % 6))}`;
  const underlineDrawn = interpolate(frame - from - 12, [0, 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.3, 0, 0.2, 1) });
  const tallies = 3 + (index % 3);
  return (
    <svg
      viewBox="0 0 840 940" width="840" height="940"
      style={{ position: "absolute", left: 0, top: 0, overflow: "visible", transform: `translateY(${j}px)` }}
    >
      {/* sellos en las esquinas EXTREMAS superiores (casi siempre vacias) */}
      <_MiniStamp x={58} y={70} rot={-9} text={caseNo} from={from} delay={0} size={30} />
      <_MiniStamp x={560} y={78} rot={7} text={exhibit} from={from} delay={6} size={26} />
      {/* flecha corta desde la nota hacia el sujeto */}
      <_Draw d={arrow} from={from} dur={9} w={7} delay={4} />
      <_Draw d={head} from={from} dur={5} w={7} delay={11} />
      {/* marcas de conteo sobre la nota */}
      {Array.from({ length: tallies }).map((_, k) => (
        <line key={k} x1={64 + k * 22} y1={760} x2={72 + k * 22} y2={805}
              stroke={RED} strokeWidth={6} strokeLinecap="round"
              opacity={interpolate(frame - from - 14 - k * 2, [0, 3], [0, 0.85], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      ))}
      {/* "?" grande y tenue en la esquina inferior-derecha */}
      <text x={745} y={890} fontFamily={_HANDWRITE} fontSize={120} fontWeight="700" fill={RED} textAnchor="middle"
            opacity={qO} transform="rotate(9 745 890)">?</text>
      {/* nota manuscrita inferior-izquierda + subrayado que se dibuja */}
      <text x={55} y={895} fontFamily={_HANDWRITE} fontSize={56} fontWeight="700" fill={RED} textAnchor="start"
            transform={`rotate(${alt ? -4 : -6} 55 895)`} style={{ letterSpacing: 1 }}>
        {label.slice(0, Math.round(labelWrite))}
      </text>
      <path d={`M 52 916 Q ${52 + label.length * 17} 906, ${60 + label.length * 34} 914`}
            stroke={RED} strokeWidth={9} fill="none" strokeLinecap="round"
            pathLength={1} strokeDasharray={1} strokeDashoffset={1 - underlineDrawn}
            transform={`rotate(${alt ? -4 : -6} 55 895)`} style={{ opacity: 0.9 }} />
    </svg>
  );
};

export const MarkerUnderline = ({ from, x, y, w, tilt = -1.5 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const drawn = interpolate(local, [0, 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.3, 0, 0.2, 1) });
  return (
    <svg width={w} height={40} style={{ position: "absolute", left: x, top: y, rotate: `${tilt}deg`, overflow: "visible" }}>
      <path
        d={`M 4 22 Q ${w * 0.3} 12, ${w * 0.55} 20 T ${w - 6} 18`}
        stroke={RED} strokeWidth={14} fill="none" strokeLinecap="round"
        pathLength={1} strokeDasharray={1} strokeDashoffset={1 - drawn}
        style={{ opacity: 0.92 }}
      />
    </svg>
  );
};

// ============================================================================
// TIER 2.1 — FICHA DE PERSONAJE (expediente que se estampa)
// ============================================================================
export const CaseFile = ({ photo, name, role, from, x, y, w = 340, rot = -4 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 8);
  const stampP = interpolate(local - 8, [0, 4], [2.2, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const stampO = local >= 8 ? interpolate(local - 8, [0, 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  const drift = Math.sin(local / 16) * 4;
  const h = w * 1.32;
  return (
    <div style={{ position: "absolute", left: x, top: y + drift, width: w, height: h, perspective: 1100 }}>
      <div
        style={{
          width: "100%", height: "100%",
          rotate: `${rot + Math.sin(local / 21) * 1.4}deg`,
          scale: `${p}`,
          transform: `rotateY(${40 * (1 - p)}deg)`,
          background: PAPER_LIGHT, border: `5px solid ${INK}`,
          boxShadow: "12px 14px 0 rgba(26,18,8,0.5)", padding: 12,
        }}
      >
        <div style={{ width: "100%", height: "68%", border: `4px solid ${INK}`, overflow: "hidden", background: "#DECBA0" }}>
          <Img src={photo} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "sepia(0.35) contrast(1.05)" }} />
        </div>
        <div
          style={{
            marginTop: 10, fontFamily: "Courier New, monospace", fontWeight: 700,
            fontSize: w * 0.082, color: INK, textAlign: "center", letterSpacing: 1,
            borderBottom: `3px solid ${INK}`, paddingBottom: 4,
          }}
        >
          {name.toUpperCase()}
        </div>
        <div
          style={{
            position: "absolute", left: "6%", bottom: "4%", rotate: "-9deg",
            scale: `${stampP}`, opacity: stampO * 0.92,
            border: `6px solid ${RED}`, borderRadius: 8, padding: "3px 12px",
            fontFamily: "Arial Black, sans-serif", fontWeight: 900,
            fontSize: w * 0.1, color: RED, letterSpacing: 2,
            background: "rgba(247,241,225,0.6)",
          }}
        >
          {role.toUpperCase()}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// TIER 2.2 — GLOBO DE PAPEL 2.5D (mapa real girando dentro de esfera sombreada)
// mapSrc: staticFile del mapa equirectangular (el caller lo pasa)
// ============================================================================
// mapShift 420 + pin 46%/30% = frena con EUROPA bajo el pin (calibrado 23 jul)
export const Globe25D = ({ mapSrc, from, x, y, size = 460, spinFrames = 34, mapShift = 420, pinLeft = "46%", pinTop = "30%" }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 8);
  const spin = interpolate(local, [4, 4 + spinFrames], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: Easing.bezier(0.15, 0.6, 0.2, 1),
  });
  const pinP = pop(local - (6 + spinFrames), 6);
  const mapX = -mapShift * spin;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: size, height: size + 90, scale: `${p}` }}>
      <div
        style={{
          width: size, height: size, borderRadius: "50%", overflow: "hidden",
          border: `7px solid ${INK}`, boxShadow: "14px 16px 0 rgba(26,18,8,0.45)",
          position: "relative", background: "#D8C9A5",
        }}
      >
        <Img
          src={mapSrc}
          style={{
            position: "absolute", left: 0, top: 0, height: "100%", width: size * 2.6,
            objectFit: "cover", translate: `${mapX}px 0px`,
            filter: "sepia(0.85) contrast(1.05) brightness(0.98)",
          }}
        />
        <div
          style={{
            position: "absolute", inset: 0, borderRadius: "50%",
            background:
              "radial-gradient(circle at 32% 28%, rgba(255,248,225,0.35) 0%, transparent 34%)," +
              "radial-gradient(circle at 50% 50%, transparent 52%, rgba(26,18,8,0.5) 96%)",
          }}
        />
        <div
          style={{
            position: "absolute", left: pinLeft, top: pinTop, width: 30, height: 30,
            borderRadius: "50%", background: RED, border: `5px solid ${INK}`,
            scale: `${pinP * (1 + 0.15 * Math.abs(Math.sin(local / 6)))}`,
          }}
        />
      </div>
      <svg width={size} height={90} style={{ position: "absolute", left: 0, top: size - 8 }}>
        <path d={`M ${size * 0.5} 6 L ${size * 0.5} 34`} stroke={INK} strokeWidth={12} />
        <path d={`M ${size * 0.28} 76 Q ${size * 0.5} 40 ${size * 0.72} 76`} stroke={INK} strokeWidth={14} fill="none" strokeLinecap="round" />
      </svg>
    </div>
  );
};

// ============================================================================
// TIER 2.3 — CIERRE DE CASO (serie + CLOSED + promesa de cadencia)
// ============================================================================
export const CaseClosed = ({ series, caseNo, from }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 8);
  const stampP = interpolate(local - 10, [0, 4], [2.4, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const stampO = local >= 10 ? 0.95 : 0;
  const nextP = pop(local - 22, 8);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
      <div
        style={{
          scale: `${p}`, rotate: `${-2 + Math.sin(local / 18) * 1.2}deg`,
          background: PAPER_LIGHT, border: `6px solid ${INK}`,
          boxShadow: "16px 18px 0 rgba(26,18,8,0.5)", padding: "46px 60px",
          position: "relative", textAlign: "center",
        }}
      >
        <div style={{ fontFamily: "Courier New, monospace", fontWeight: 700, fontSize: 40, color: INK, letterSpacing: 6 }}>
          {series.toUpperCase()}
        </div>
        <div style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 96, color: INK, marginTop: 6 }}>
          CASE #{caseNo}
        </div>
        <div
          style={{
            position: "absolute", right: -40, top: -34, rotate: "12deg",
            scale: `${stampP}`, opacity: stampO,
            border: `8px solid ${RED}`, borderRadius: 10, padding: "8px 22px",
            fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 58,
            color: RED, letterSpacing: 4, background: "rgba(247,241,225,0.75)",
          }}
        >
          CLOSED
        </div>
      </div>
      <div
        style={{
          marginTop: 46, scale: `${nextP}`,
          fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 44,
          color: "#FFF", background: RED, padding: "12px 30px", rotate: "-2deg",
          boxShadow: "8px 10px 0 rgba(26,18,8,0.5)", letterSpacing: 2,
        }}
      >
        NEW CASE TOMORROW
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// TIER 2.4 — MAPA ANTIGUO VIVO de fondo (papel que respira, pedido usuario)
// 3 capas: mapa PD + ondulacion procedural (displacement) + banda de luz que
// recorre los pliegues. Sutil a proposito: el fondo se siente, no se mira.
// ============================================================================
export const WrinkledMap = ({ src, opacity = 0.5 }) => {
  const frame = useCurrentFrame();
  const breathe = 1.05 + Math.sin(frame / 38) * 0.015;
  const wobble = Math.sin(frame / 51) * 0.4;
  const dispScale = 16 + Math.sin(frame / 23) * 8; // el papel se tensa y afloja
  const lightX = interpolate(frame % 240, [0, 240], [-30, 130]);
  return (
    <AbsoluteFill style={{ overflow: "hidden", pointerEvents: "none" }}>
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <filter id="wrinkle">
          <feTurbulence type="fractalNoise" baseFrequency="0.012 0.02" numOctaves="3" seed="11" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale={dispScale} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>
      <AbsoluteFill style={{ scale: `${breathe}`, rotate: `${wobble}deg`, filter: "url(#wrinkle)" }}>
        <Img
          src={src}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity,
            mixBlendMode: "multiply",
            filter: "sepia(1) saturate(1.4) contrast(0.98) brightness(1.04)",
          }}
        />
      </AbsoluteFill>
      {/* pliegues fijos: sombras de doblez */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(100deg, transparent 31%, rgba(60,40,12,0.10) 33%, transparent 35.5%)," +
            "linear-gradient(96deg, transparent 61%, rgba(60,40,12,0.08) 63%, transparent 65.5%)," +
            "linear-gradient(8deg, transparent 44%, rgba(60,40,12,0.06) 46%, transparent 48.5%)",
        }}
      />
      {/* banda de luz recorriendo el papel */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(115deg, transparent ${lightX - 22}%, rgba(255,248,220,0.22) ${lightX}%, transparent ${lightX + 22}%)`,
        }}
      />
    </AbsoluteFill>
  );
};

// --- Tarjeta compartible (la frase que la gente screenshotea) ----------------
export const ShareCard = ({ line1, line2, from }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 9);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 240, pointerEvents: "none" }}>
      <div
        style={{
          scale: `${p}`, rotate: "1.5deg", maxWidth: 880,
          background: "#141210", border: `6px solid ${GOLD}`,
          padding: "34px 44px", textAlign: "center",
          boxShadow: "14px 16px 0 rgba(26,18,8,0.55)",
        }}
      >
        <div style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 56, color: "#FFF", lineHeight: 1.15 }}>
          {line1}
        </div>
        <div style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 56, color: GOLD, lineHeight: 1.15, marginTop: 8 }}>
          {line2}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// CARRILES DE LAYOUT (ajuste 23 jul: el caption nunca queda detras de nada)
// Elementos de tablero viven en y < CAPTION_TOP; captions en su franja propia.
// ============================================================================
export const LANES = { captionTop: 1330, captionBottom: 1690, safeTop: 110 };

// ============================================================================
// TIER 3.1 — COLD-OPEN CENSURADO: flash del climax con censura, siembra el reveal
// ============================================================================
export const ColdOpen = ({ src, label = "CLASSIFIED", tag = "IN 60 SECONDS...", durationInFrames = 22 }) => {
  const frame = useCurrentFrame();
  if (frame >= durationInFrames) return null;
  const jitterX = (frame % 3) * 4 - 4; // glitch nervioso
  const zoom = 1.12 + frame * 0.004;
  const flash = frame < 2 ? 0.5 : 0;
  return (
    <AbsoluteFill style={{ background: "#0D0B08", overflow: "hidden" }}>
      <AbsoluteFill style={{ scale: `${zoom}`, translate: `${jitterX}px 0px` }}>
        <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "contrast(1.2) sepia(0.4) brightness(0.8)" }} />
      </AbsoluteFill>
      <div
        style={{
          position: "absolute", left: "8%", top: "40%", width: "84%", height: 170,
          background: "#141210",
          clipPath: "polygon(0% 0%, 100% 0%, 100% 78%, 94% 88%, 87% 76%, 79% 90%, 71% 78%, 63% 92%, 55% 80%, 47% 90%, 39% 78%, 31% 92%, 23% 80%, 15% 90%, 7% 78%, 0% 88%)",
          display: "flex", alignItems: "center", justifyContent: "center",
          rotate: `${-2 + (frame % 4) * 0.5}deg`,
        }}
      >
        <span style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 60, color: RED, letterSpacing: 8, border: `5px solid ${RED}`, padding: "6px 24px", rotate: "-2deg" }}>
          {label}
        </span>
      </div>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: 420 }}>
        <span style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 52, color: "#FFF", background: RED, padding: "8px 26px", rotate: "-1.5deg", letterSpacing: 3 }}>
          {tag}
        </span>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "#FFF8E7", opacity: flash }} />
    </AbsoluteFill>
  );
};

// ============================================================================
// TIER 3.2 — MAQUINA DE ESCRIBIR: texto tipeandose en vivo sobre tira de papel
// ============================================================================
export const Typewriter = ({ text, from, x, y, size = 44, charDur = 2 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const chars = Math.min(Math.floor(local / charDur), text.length);
  const done = chars >= text.length;
  const cursorOn = Math.floor(local / 8) % 2 === 0;
  return (
    <div
      style={{
        position: "absolute", left: x, top: y,
        background: PAPER_LIGHT, border: `4px solid ${INK}`,
        boxShadow: "10px 12px 0 rgba(26,18,8,0.45)",
        padding: "14px 24px", rotate: "-1.2deg",
      }}
    >
      <span style={{ fontFamily: "Courier New, monospace", fontWeight: 700, fontSize: size, color: INK, letterSpacing: 2, whiteSpace: "pre" }}>
        {text.slice(0, chars)}
        {!done && cursorOn ? "▌" : done ? "" : " "}
      </span>
    </div>
  );
};

// ============================================================================
// TIER 3.3 — SELLO SUBSCRIBE (CTA visual al cierre, nunca hablado)
// ============================================================================
export const SubscribeStamp = ({ from, x = 330, y = 1180 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const s = interpolate(local, [0, 4], [2.4, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: SLAM_EASE });
  const o = interpolate(local, [0, 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const wiggle = local > 10 ? Math.sin(local / 5) * 1.6 : 0; // llama la atencion tras aterrizar
  return (
    <div
      style={{
        position: "absolute", left: x, top: y,
        rotate: `${-6 + wiggle}deg`, scale: `${s}`, opacity: o * 0.96,
        border: `8px solid ${RED}`, borderRadius: 12, padding: "10px 30px",
        background: "rgba(247,241,225,0.85)",
        boxShadow: "10px 12px 0 rgba(26,18,8,0.5)",
      }}
    >
      <span style={{ fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 62, color: RED, letterSpacing: 5 }}>
        SUBSCRIBE
      </span>
    </div>
  );
};

// ============================================================================
// CAPTIONS CON TIMESTAMPS REALES DE TTS (reemplaza el ASS quemado)
//   words: [{t: frameInicio, w: "palabra"}] en frames GLOBALES del video.
//   Agrupa en bloques de hasta 3 palabras / 18 chars (misma regla del pipeline),
//   activa en dorado + pop de escala, siempre dentro del carril de captions.
// ============================================================================
export const KineticTimed = ({ words, endFrame = Infinity, sizeActive = 92, sizeRest = 76 }) => {
  const frame = useCurrentFrame();
  if (frame >= endFrame) return null;
  // agrupar en bloques estilo pipeline (3 palabras / 18 chars)
  const chunks = [];
  let buf = [];
  for (const wd of words) {
    buf.push(wd);
    const joined = buf.map((b) => b.w).join(" ");
    if (buf.length >= 3 || joined.length >= 18) {
      chunks.push(buf);
      buf = [];
    }
  }
  if (buf.length) chunks.push(buf);

  // bloque visible: el ultimo cuyo primer word ya arranco
  let chunk = null;
  let next = null;
  for (let i = 0; i < chunks.length; i++) {
    if (frame >= chunks[i][0].t) {
      chunk = chunks[i];
      next = chunks[i + 1] || null;
    }
  }
  if (!chunk) return null;
  if (next && frame >= next[0].t) return null; // ya paso al siguiente

  const activeIdx = chunk.reduce((acc, wd, i) => (frame >= wd.t ? i : acc), 0);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 1920 - LANES.captionBottom, pointerEvents: "none" }}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px 16px", maxWidth: 940 }}>
        {chunk.map((wd, i) => {
          if (frame < wd.t) return null;
          const p = pop(frame - wd.t, 5);
          const isActive = i === activeIdx;
          return (
            <span
              key={i}
              style={{
                fontFamily: "Arial Black, sans-serif", fontWeight: 900,
                fontSize: isActive ? sizeActive : sizeRest,
                color: isActive ? GOLD : "#FFF",
                scale: `${p}`,
                display: "inline-block",
                textShadow: "4px 4px 0 #1a1208, -3px -3px 0 #1a1208, 3px -3px 0 #1a1208, -3px 3px 0 #1a1208, 0 10px 24px rgba(0,0,0,0.55)",
              }}
            >
              {wd.w.toUpperCase()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
