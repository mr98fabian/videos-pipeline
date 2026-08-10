import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  Easing,
} from "remotion";

// ============================================================================
// PRUEBA 2.0 — "ARCHIVO VIVO": collage documental punchy
//   - CERO blur: profundidad por capas de papel + sombras duras
//   - Tablero de pergamino nítido; todo entra como recorte con física
//   - Acento rojo marcador (color selectivo sobre sepia evolucionado)
//   - Punch-zooms de cámara + cortes duros; algo pasa cada ~2s
//   - SFX en cada golpe
// ============================================================================

const INK = "#1a1208";
const GOLD = "#FFD700";
const RED = "#D7263D"; // acento saturado: marcador de archivo
const PAPER_BASE = "#E6D7B8";

// --- util: spring-pop rapido (overshoot) ------------------------------------
const pop = (local, dur = 8) =>
  interpolate(local, [0, dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.18, 1.65, 0.35, 1),
  });

// --- Tablero de pergamino NITIDO (sin blur jamas) ---------------------------
const Board = ({ children, camera }) => {
  const frame = useCurrentFrame();
  const cam = camera ? camera(frame) : { scale: 1, x: 0, y: 0 };
  return (
    <AbsoluteFill style={{ background: PAPER_BASE, overflow: "hidden" }}>
      {/* manchas de edad (nitidas, radiales) */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 20% 15%, rgba(122,90,44,0.18) 0%, transparent 40%)," +
            "radial-gradient(circle at 85% 70%, rgba(122,90,44,0.15) 0%, transparent 35%)," +
            "radial-gradient(circle at 60% 25%, rgba(90,60,20,0.10) 0%, transparent 30%)," +
            "radial-gradient(ellipse at center, transparent 60%, rgba(60,40,12,0.35) 100%)",
        }}
      />
      {/* fibra de papel via turbulencia estatica */}
      <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.08 }}>
        <filter id="paper">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" seed="7" />
        </filter>
        <rect width="100%" height="100%" filter="url(#paper)" />
      </svg>
      {/* camara: punch-zooms + deriva */}
      <AbsoluteFill
        style={{
          scale: `${cam.scale}`,
          translate: `${cam.x}px ${cam.y}px`,
        }}
      >
        {children}
      </AbsoluteFill>
      {/* grano vivo sutil */}
      <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.06, pointerEvents: "none" }}>
        <filter id={`g-${frame % 5}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={frame % 5} stitchTiles="stitch" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#g-${frame % 5})`} />
      </svg>
    </AbsoluteFill>
  );
};

// --- Recorte troquelado: borde blanco die-cut + sombra dura -----------------
const DIE_CUT =
  [0, 45, 90, 135, 180, 225, 270, 315]
    .map((deg) => {
      const r = 6;
      const dx = (Math.cos((deg * Math.PI) / 180) * r).toFixed(1);
      const dy = (Math.sin((deg * Math.PI) / 180) * r).toFixed(1);
      return `drop-shadow(${dx}px ${dy}px 0px #F7F1E1)`;
    })
    .join(" ") + " drop-shadow(14px 18px 0px rgba(26,18,8,0.55))";

const Cutout = ({ src, from, x, y, w, h, fromDir = "bottom", rot = -2, driftAmp = 5 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 9);
  const offX = fromDir === "right" ? 700 * (1 - p) : fromDir === "left" ? -700 * (1 - p) : 0;
  const offY = fromDir === "bottom" ? 800 * (1 - p) : fromDir === "top" ? -800 * (1 - p) : 0;
  const drift = Math.sin(local / 13) * driftAmp;
  const tilt = rot + Math.sin(local / 17) * 1.6;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y + drift,
        width: w,
        height: h,
        translate: `${offX}px ${offY}px`,
        rotate: `${tilt}deg`,
        scale: `${0.85 + 0.15 * p}`,
      }}
    >
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "contain", filter: DIE_CUT }} />
    </div>
  );
};

// --- Palabras cineticas punchy (jitter de rotacion, pop 6f) -----------------
const Kinetic = ({ words, from, wordDur = 7, size = 76, bottom = 560 }) => {
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
          const jit = ((i * 37) % 7) - 3; // rotacion determinista por palabra
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

// --- Subrayado de marcador ROJO que se dibuja solo --------------------------
const MarkerUnderline = ({ from, x, y, w, tilt = -1.5 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const drawn = interpolate(local, [0, 7], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.3, 0, 0.2, 1),
  });
  return (
    <svg
      width={w}
      height={40}
      style={{ position: "absolute", left: x, top: y, rotate: `${tilt}deg`, overflow: "visible" }}
    >
      <path
        d={`M 4 22 Q ${w * 0.3} 12, ${w * 0.55} 20 T ${w - 6} 18`}
        stroke={RED}
        strokeWidth={14}
        fill="none"
        strokeLinecap="round"
        style={{ clipPath: `inset(0 ${(1 - drawn) * 100}% 0 0)`, opacity: 0.92 }}
      />
    </svg>
  );
};

// --- Sello que GOLPEA (scale 2.2 -> 1 en 4 frames) --------------------------
const Stamp = ({ text, from, x, y, rot = -8, color = RED }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const s = interpolate(local, [0, 4], [2.3, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.2, 0.9, 0.3, 1),
  });
  const o = interpolate(local, [0, 3], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        rotate: `${rot}deg`,
        scale: `${s}`,
        opacity: o * 0.95,
        border: `9px solid ${color}`,
        borderRadius: 10,
        padding: "10px 26px",
        boxShadow: `0 0 0 3px ${PAPER_BASE}, 0 0 0 6px ${color}`,
      }}
    >
      <span
        style={{
          fontFamily: "Arial Black, sans-serif",
          fontWeight: 900,
          fontSize: 54,
          color,
          letterSpacing: 4,
        }}
      >
        {text}
      </span>
    </div>
  );
};

// --- Fondo "impresion lavada": la escena como print desvanecido en el papel --
// (NITIDO — opacidad baja + multiply, nunca blur; da contexto sin competir)
const Backdrop = ({ src }) => {
  const frame = useCurrentFrame();
  const s = interpolate(frame, [0, 150], [1.06, 1.12]);
  return (
    <AbsoluteFill style={{ scale: `${s}` }}>
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

// --- Foto enmarcada: escena COMPLETA como recorte de archivo clavado --------
// (para planos anchos/grupales donde el recorte rembg no sirve: la imagen
// entera entra como "foto de archivo" con marco de papel, cinta y sombra dura)
const PhotoScrap = ({ src, from, x, y, w, h, fromDir = "right", rot = 2 }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 9);
  const offX = fromDir === "right" ? 800 * (1 - p) : fromDir === "left" ? -800 * (1 - p) : 0;
  const drift = Math.sin(local / 15) * 4;
  const tilt = rot + Math.sin(local / 19) * 1.2;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y + drift,
        width: w,
        height: h,
        translate: `${offX}px 0px`,
        rotate: `${tilt}deg`,
        scale: `${0.9 + 0.1 * p}`,
        background: "#F7F1E1",
        padding: 18,
        boxShadow: "16px 20px 0 rgba(26,18,8,0.5)",
        border: `4px solid ${INK}`,
      }}
    >
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover", border: `3px solid ${INK}` }} />
      {/* cinta adhesiva en las esquinas */}
      <div style={{ position: "absolute", left: -26, top: -14, width: 120, height: 42, background: "rgba(214,196,150,0.85)", rotate: "-38deg", boxShadow: "0 2px 6px rgba(26,18,8,0.25)" }} />
      <div style={{ position: "absolute", right: -26, bottom: -14, width: 120, height: 42, background: "rgba(214,196,150,0.85)", rotate: "-38deg", boxShadow: "0 2px 6px rgba(26,18,8,0.25)" }} />
    </div>
  );
};

// --- Mapa de Austria estilizado (papel + tinta) con pin que late ------------
const MapScrap = ({ from, x, y }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const p = pop(local, 9);
  const pinBeat = 1 + 0.18 * Math.abs(Math.sin(local / 6));
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: 430,
        height: 330,
        rotate: `${3 - 1.5 * p}deg`,
        scale: `${p}`,
        background: "#EFE3C4",
        border: `6px solid ${INK}`,
        boxShadow: "12px 14px 0 rgba(26,18,8,0.5)",
        overflow: "hidden",
      }}
    >
      <svg width="430" height="330" viewBox="0 0 430 330">
        {/* Austria con su forma real (simplificada): mango angosto al oeste
            (Vorarlberg/Tirol), cuerpo ancho al este, Viena al noreste */}
        <path
          d="M 22 186
             Q 30 172 48 176 L 74 168 Q 88 158 104 164 L 128 154
             Q 150 140 176 146 L 210 132 Q 248 118 288 124 L 330 118
             Q 368 112 396 128 Q 412 140 404 158 L 410 176
             Q 414 194 396 202 L 372 214 Q 344 228 312 222 L 270 232
             Q 234 240 200 230 L 162 236 Q 130 240 108 226 L 76 222
             Q 52 220 40 206 Q 24 200 22 186 Z"
          fill="#DECBA0"
          stroke={INK}
          strokeWidth="7"
          strokeLinejoin="round"
        />
        <text x="120" y="205" fontFamily="Arial Black" fontWeight="900" fontSize="42" fill={INK} opacity="0.85">
          AUSTRIA
        </text>
        {/* pin de Viena (noreste real) que late en ROJO */}
        <circle cx="352" cy="150" r={13 * pinBeat} fill={RED} stroke={INK} strokeWidth="5" />
        <line x1="352" y1="150" x2="330" y2="106" stroke={RED} strokeWidth="5" />
        <text x="252" y="96" fontFamily="Arial Black" fontWeight="900" fontSize="32" fill={RED}>
          VIENNA
        </text>
      </svg>
    </div>
  );
};

// ============================ COMPOSICION ====================================
export const Proof2 = () => {
  const CUT = 150; // corte duro a los 5s

  // camaras por tablero: punch-zooms en los beats
  const camA = (f) => {
    const punch = interpolate(f, [52, 56], [0, 0.09], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.2, 0.9, 0.3, 1) });
    const drift = interpolate(f, [0, CUT], [0, 0.025]);
    return { scale: 1.02 + punch + drift, x: interpolate(f, [0, CUT], [0, -14]), y: interpolate(f, [0, CUT], [0, -8]) };
  };
  const camB = (f) => {
    const local = f - CUT;
    const punch = interpolate(local, [58, 62], [0, 0.1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.2, 0.9, 0.3, 1) });
    const drift = interpolate(local, [0, 150], [0, 0.03]);
    return { scale: 1.02 + punch + drift, x: interpolate(local, [0, 150], [0, 12]), y: 0 };
  };

  return (
    <AbsoluteFill style={{ background: INK }}>
      {/* ---------- TABLERO A: el canciller (0 - 150) ---------- */}
      <Sequence durationInFrames={CUT}>
        <Board camera={camA}>
          <Backdrop src={staticFile("proof/scene0_bg.png")} />
          <Cutout
            src={staticFile("proof/scene0_fg.png")}
            from={2}
            x={40}
            y={210}
            w={1000}
            h={1150}
            fromDir="bottom"
            rot={-2}
          />
          <MapScrap from={54} x={600} y={190} />
          <Stamp text="JULY 25, 1934" from={92} x={110} y={330} rot={-9} />
          <Kinetic
            words={["The", "first", "time", "Hitler", "tried", "to", "steal", "a", "country"]}
            from={10}
            bottom={480}
          />
          {/* subrayado rojo bajo la zona de HITLER (aprox centro del bloque) */}
          <MarkerUnderline from={38} x={330} y={1385} w={420} />
        </Board>
      </Sequence>

      {/* ---------- TABLERO B: los falsos policias (150 - 300) ---------- */}
      <Sequence from={CUT}>
        <Board camera={camB}>
          <Backdrop src={staticFile("proof/scene1_bg.png")} />
          <PhotoScrap
            src={staticFile("proof/scene1_bg.png")}
            from={0}
            x={55}
            y={300}
            w={970}
            h={1080}
            fromDir="right"
            rot={1.8}
          />
          <Cutout
            src={staticFile("proof/sticker.png")}
            from={30}
            x={700}
            y={230}
            w={260}
            h={260}
            fromDir="top"
            rot={7}
            driftAmp={7}
          />
          <Stamp text="DISGUISED" from={62} x={120} y={280} rot={-7} />
          <Kinetic
            words={["150", "SS", "men", "dressed", "as", "POLICE"]}
            from={8}
            wordDur={8}
            size={82}
            bottom={470}
          />
          <MarkerUnderline from={56} x={330} y={1395} w={460} tilt={1} />
        </Board>
      </Sequence>

      {/* ---------- SFX: golpe por cada entrada ---------- */}
      <Sequence from={1} durationInFrames={24}>
        <Audio src={staticFile("proof/whoosh.mp3")} volume={0.5} />
      </Sequence>
      <Sequence from={53} durationInFrames={22}>
        <Audio src={staticFile("proof/paper.mp3")} volume={0.4} />
      </Sequence>
      <Sequence from={91} durationInFrames={20}>
        <Audio src={staticFile("proof/whoosh.mp3")} volume={0.42} />
      </Sequence>
      <Sequence from={CUT} durationInFrames={22}>
        <Audio src={staticFile("proof/whoosh.mp3")} volume={0.55} />
      </Sequence>
      <Sequence from={CUT + 29} durationInFrames={20}>
        <Audio src={staticFile("proof/paper.mp3")} volume={0.4} />
      </Sequence>
      <Sequence from={CUT + 61} durationInFrames={18}>
        <Audio src={staticFile("proof/whoosh.mp3")} volume={0.42} />
      </Sequence>
    </AbsoluteFill>
  );
};
