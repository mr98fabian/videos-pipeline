import { useCurrentFrame, useVideoConfig, spring, interpolate, staticFile, Img, AbsoluteFill } from "remotion";

const GOLD = "#E8C468";
// halo dorado tipo "recorte de revista" para stickers de FOTO REAL (mismo
// truco que RealCollage.jsx: drop-shadow sigue el alpha del recorte, apilar
// varias en distintas direcciones simula un contorno grueso).
const PHOTO_HALO_FILTER = [0, 45, 90, 135, 180, 225, 270, 315]
  .map((deg) => {
    const r = 5;
    const dx = (Math.cos((deg * Math.PI) / 180) * r).toFixed(1);
    const dy = (Math.sin((deg * Math.PI) / 180) * r).toFixed(1);
    return `drop-shadow(${dx}px ${dy}px 0px ${GOLD})`;
  })
  .join(" ") + " drop-shadow(6px 6px 0px #1a1208)";

// Estilo "collage recortado": cada sfx_cue se dibuja como un STICKER de papel
// rotado (icono sobre tarjeta beige con borde de tinta) mas una FLECHA PUNTEADA
// que se dibuja sola apuntando al centro de la accion -- referencia visual que
// paso el usuario 21 jul 2026 (collage con recortes + flechas dibujadas a mano).
//
// Reemplaza la version anterior (icono + palabra kinetica centrados). Dos bugs
// reales que arregla, vistos en el render de prueba:
//   1) el slot "impar" caia en y=0.68*H, exactamente sobre la banda de
//      subtitulos karaoke (Style: Cap usa MarginV 640 con alignment 2, o sea
//      ocupa y~1050-1290 de 1920) -- texto sobre texto, ilegible.
//   2) la palabra kinetica repetia la MISMA palabra que el caption ya estaba
//      mostrando resaltada en ese instante ("RADIO" dos veces en pantalla).
// Por eso ahora: solo icono (sin texto duplicado) y todo confinado arriba.
const INK = "#1a1208";
const PAPER = "#EDDFC0";
const HOLD_FRAMES = 48; // cuanto se queda visible antes de empezar a desvanecer

// zona segura: por encima de la banda de subtitulos. El sticker nunca baja de
// aca, sin importar cuantos cues haya.
const SAFE_TOP = 0.16;
const SAFE_BOTTOM = 0.44;

function Sticker({ time, emoji, photo, index }) {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const popFrame = Math.round(time * fps);
  const local = frame - popFrame;
  if (local < 0 || local > HOLD_FRAMES + 18) return null;

  const enter = spring({ frame: local, fps, config: { damping: 9, stiffness: 140, mass: 0.6 } });
  const fadeOut = interpolate(local, [HOLD_FRAMES, HOLD_FRAMES + 18], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // deriva idle: el sticker nunca se queda 100% quieto (eso es lo que da la
  // sensacion de "collage vivo" de la referencia). Amplitud chica a proposito.
  const drift = Math.sin(local / 11) * 6;
  const tilt = (index % 2 === 0 ? -7 : 7) + Math.sin(local / 14) * 2.5;

  // alterna izquierda/derecha dentro de la franja segura de arriba, para que
  // dos cues seguidos no se pisen ni tapen el mismo punto de la imagen.
  const onLeft = index % 2 === 0;
  const cardW = 240;
  const cardH = 240;
  const cardX = onLeft ? width * 0.13 : width * 0.87 - cardW;
  const bandT = SAFE_TOP + ((index % 3) / 3) * (SAFE_BOTTOM - SAFE_TOP);
  const cardY = height * bandT + drift;

  // la flecha sale del sticker hacia el centro del frame (donde esta el sujeto
  // de la escena), igual que en la referencia. Se dibuja sola con
  // stroke-dashoffset animado -- tecnica estandar de SVG, no necesita libs.
  const aFrom = { x: cardX + (onLeft ? cardW + 14 : -14), y: cardY + cardH / 2 };
  const aTo = { x: width / 2 + (onLeft ? -110 : 110), y: cardY + cardH * 0.9 };
  const len = Math.hypot(aTo.x - aFrom.x, aTo.y - aFrom.y);
  const drawn = interpolate(local, [4, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // punta de flecha: dos trazos cortos girados respecto al angulo de la linea.
  const ang = Math.atan2(aTo.y - aFrom.y, aTo.x - aFrom.x);
  const head = 34;
  const headOpacity = interpolate(local, [18, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <>
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", left: 0, top: 0, opacity: fadeOut }}
      >
        <line
          x1={aFrom.x}
          y1={aFrom.y}
          x2={aTo.x}
          y2={aTo.y}
          stroke={INK}
          strokeWidth={11}
          strokeLinecap="round"
          strokeDasharray={`26 20`}
          // el truco de "se dibuja sola": un segundo dash gigante que tapa el
          // resto de la linea y se va corriendo con drawn 0->1.
          strokeDashoffset={0}
          style={{
            clipPath: `inset(0 ${(1 - drawn) * 100}% 0 0)`,
          }}
        />
        <g opacity={headOpacity}>
          <line
            x1={aTo.x}
            y1={aTo.y}
            x2={aTo.x - head * Math.cos(ang - 0.45)}
            y2={aTo.y - head * Math.sin(ang - 0.45)}
            stroke={INK}
            strokeWidth={11}
            strokeLinecap="round"
          />
          <line
            x1={aTo.x}
            y1={aTo.y}
            x2={aTo.x - head * Math.cos(ang + 0.45)}
            y2={aTo.y - head * Math.sin(ang + 0.45)}
            stroke={INK}
            strokeWidth={11}
            strokeLinecap="round"
          />
        </g>
      </svg>

      {photo ? (
        // sticker de FOTO REAL recortada (Wikimedia + rembg, ver
        // _photo_sticker() en pipeline.py) -- sin tarjeta de papel, el halo
        // dorado ya vende el look "recorte" directamente sobre la silueta.
        <div
          style={{
            position: "absolute",
            left: cardX,
            top: cardY,
            width: cardW,
            height: cardH,
            transform: `scale(${enter}) rotate(${tilt}deg)`,
            transformOrigin: "center center",
            opacity: fadeOut,
          }}
        >
          <Img
            src={staticFile(photo)}
            style={{ width: "100%", height: "100%", objectFit: "contain", filter: PHOTO_HALO_FILTER }}
          />
        </div>
      ) : (
        <div
          style={{
            position: "absolute",
            left: cardX,
            top: cardY,
            width: cardW,
            height: cardH,
            transform: `scale(${enter}) rotate(${tilt}deg)`,
            transformOrigin: "center center",
            opacity: fadeOut,
            background: PAPER,
            border: `7px solid ${INK}`,
            borderRadius: 6,
            boxShadow: `10px 10px 0px ${INK}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 132,
          }}
        >
          {emoji}
        </div>
      )}
    </>
  );
}

export function AutoOverlay({ cues }) {
  return (
    <AbsoluteFill>
      {(cues || []).map((c, i) => (
        <Sticker key={i} time={c.time} emoji={c.emoji} photo={c.photo} index={i} />
      ))}
    </AbsoluteFill>
  );
}
