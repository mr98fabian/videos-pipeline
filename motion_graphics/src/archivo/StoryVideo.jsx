import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  Img,
  Audio,
  staticFile,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { KineticTimed, HookText, GOLD, RED, INK } from "./components";

// ============================================================================
// STORY VIDEO — motor Remotion para el formato "historia sobre gameplay a
// pantalla completa" (Mind Checkpoint), hermano de ArchivoVideo pero para
// fondo de VIDEO continuo en vez de collage de fotos recortadas.
//
// Reemplaza el `-filter_complex` de FFmpeg escrito a mano video a video desde
// el 1 ago 2026: el zoom de entrada, los subtitulos, la hook card, el contador
// y los golpes dramaticos pasan a ser componentes reales con `spring()` en vez
// de rampas lineales (interpolate plano), que es el defecto de "se ve a
// maquina" diagnosticado el 3 ago 2026 -- confirmado en el codigo: cero usos
// de spring() en toda la cadena de FFmpeg.
//
// props = {
//   gameplaySrc: "story/<slug>/gameplay.mp4",   -- ya viene pre-cortado/concatenado
//   voiceSrc, musicSrc: "story/<slug>/...",
//   words: [{t, w}]                              -- FRAMES globales (30fps)
//   redWords: ["sold","same",...],               -- caption_keywords en mayus
//   hookCardSrc: "story/<slug>/hookcard.png",
//   hook: "texto del hook_card (para el fallback JSX si no hay PNG)",
//   counter: {label, total, keys: [[frame, valor], ...]} | null,
//   beats: [{frame, dur}],                       -- pausas dramaticas: seg oscurece
//   musicVolume: 0.09, voiceVolume: 1,
//   durationInFrames,
// }
// ============================================================================

const HOOKCARD_FRAMES = 81; // 2.7s @ 30fps, mismo limite que la version FFmpeg
const ZOOM_FRAMES = 24; // 0.8s: el frame 0 tiene que moverse, nunca quedarse quieto

// --- grano de pelicula: SVG feTurbulence, cero asset externo -----------------
const FilmGrain = ({ opacity = 0.05 }) => (
  <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "overlay", opacity }}>
    <svg width="100%" height="100%">
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  </AbsoluteFill>
);

// --- fondo: video con zoom de ENTRADA en resorte, no rampa lineal ------------
const Background = ({ src, beats = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // spring() decelera como algo real (lo que faltaba); antes era min(1,t/0.8).
  const zoom = spring({ frame, fps, config: { damping: 14, mass: 0.6 }, durationInFrames: ZOOM_FRAMES });
  const scale = interpolate(zoom, [0, 1], [1.13, 1.0]);

  // beat mas cercano ya pasado/actual: desatura + oscurece unos frames, con
  // recuperacion en resorte -- sustituye el eq=saturation puntual de FFmpeg.
  let sat = 1, bright = 1;
  for (const b of beats) {
    const local = frame - b.frame;
    if (local >= -2 && local <= (b.dur ?? 15) + 10) {
      const dip = spring({ frame: local, fps, config: { damping: 10 }, durationInFrames: b.dur ?? 15 });
      sat = Math.min(sat, interpolate(dip, [0, 1], [1, 0.15]));
      bright = Math.min(bright, interpolate(dip, [0, 1], [1, 0.86]));
    }
  }

  return (
    <AbsoluteFill style={{ overflow: "hidden", background: INK }}>
      <div style={{
        width: "100%", height: "100%", transform: `scale(${scale})`,
        filter: `saturate(${sat}) brightness(${bright})`,
      }}>
        <OffthreadVideo src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
    </AbsoluteFill>
  );
};

// --- contador HUD: el mismo goal-gradient de counter_overlay.py, en JSX ------
const Counter = ({ label, total, keys, frame }) => {
  // No se pinta antes de su propia primera clave -- por diseno esa clave ya
  // cae despues de que la hook card se apague (t=3.2s tras los 2.7s de card),
  // pero sin esta guarda el contador aparecia SOBRE la card durante ese hueco
  // (bug real, visto renderizando: 3 ago 2026).
  if (!keys || !keys.length || frame < keys[0][0]) return null;
  let val = keys[keys.length - 1][1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [t0, v0] = keys[i], [t1, v1] = keys[i + 1];
    if (frame < t0) { val = v0; break; }
    if (frame >= t0 && frame < t1) { val = Math.floor(interpolate(frame, [t0, t1], [v0, v1])); break; }
  }
  const done = frame >= keys[keys.length - 1][0];
  const digits = String(total).length;
  const text = `${label} ${String(val).padStart(digits, "0")}/${total}`;
  return (
    <div style={{
      position: "absolute", left: "50%", top: 205, transform: "translateX(-50%)",
      background: "rgba(0,0,0,0.72)", padding: "10px 22px", borderRadius: 8,
      fontFamily: "Consolas, monospace", fontWeight: 700, fontSize: 44,
      color: done ? GOLD : "#FFF", letterSpacing: 1,
      textShadow: "0 3px 0 rgba(0,0,0,0.9)",
      whiteSpace: "nowrap",
    }}>{text}</div>
  );
};

// --- hook card: imagen real (el diseno tipo post social ya generado) --------
const HookCard = ({ src }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame > HOOKCARD_FRAMES) return null;
  const enter = spring({ frame, fps, config: { damping: 12 }, durationInFrames: 10 });
  const fadeOut = interpolate(frame, [HOOKCARD_FRAMES - 8, HOOKCARD_FRAMES], [1, 0], { extrapolateLeft: "clamp" });
  const scale = interpolate(enter, [0, 1], [0.92, 1]);
  return (
    <div style={{
      position: "absolute", left: "50%", top: 60, transform: `translateX(-50%) scale(${scale})`,
      opacity: Math.min(enter, fadeOut), transformOrigin: "top center",
    }}>
      <Img src={staticFile(src)} style={{ width: 1040, display: "block" }} />
    </div>
  );
};

export const StoryVideo = ({
  gameplaySrc, voiceSrc, musicSrc, words = [], redWords = [], hookCardSrc, hook,
  counter, beats = [], musicVolume = 0.09, voiceVolume = 1, durationInFrames,
}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Background src={gameplaySrc} beats={beats} />

      <KineticTimed words={words} redWords={redWords} />
      {hookCardSrc ? <HookCard src={hookCardSrc} /> : <HookText text={hook} dur={HOOKCARD_FRAMES} />}
      {counter ? <Counter label={counter.label} total={counter.total} keys={counter.keys} frame={frame} /> : null}

      <FilmGrain opacity={0.045} />

      {voiceSrc ? <Audio src={staticFile(voiceSrc)} volume={voiceVolume} /> : null}
      {musicSrc ? (
        <Audio
          src={staticFile(musicSrc)}
          volume={(f) => {
            // fade in/out global + ducking en cada beat, igual que el
            // sidechaincompress de FFmpeg pero como envolvente conocida
            const fadeIn = interpolate(f, [0, 60], [0, 1], { extrapolateRight: "clamp" });
            const fadeOut = interpolate(f, [durationInFrames - 60, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
            let duck = 1;
            for (const b of beats) {
              const local = f - b.frame;
              if (local >= -5 && local <= (b.dur ?? 15) + 10) {
                duck = Math.min(duck, 0.35);
              }
            }
            return musicVolume * Math.min(fadeIn, fadeOut) * duck;
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
