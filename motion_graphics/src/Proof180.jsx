import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";
import { TransitionSeries, springTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";

// ============================================================================
// PRUEBA 180 VISUAL — una escena del video Dollfuss reconstruida "estilo AE":
//   1. Parallax 2.5D (fondo desenfocado lento + personaje recortado nítido)
//   2. Caption cinético word-by-word con overshoot (identidad amarilla actual)
//   3. Transición de escena con dirección (slide + spring)
//   4. Sticker de papel que entra con física + deriva viva
//   5. Grano de película + viñeta + flicker sepia (identidad vintage)
//   6. SFX en el frame exacto de cada movimiento
// ============================================================================

const GOLD = "#FFD700";
const INK = "#1a1208";
const PAPER = "#EDDFC0";

// --- Grano + viñeta + flicker: la capa "película vieja" sobre todo ----------
const FilmLayer = () => {
  const frame = useCurrentFrame();
  // flicker de exposición sutil (2-4% de variación, aleatorio determinista)
  const flick = 0.97 + 0.03 * Math.abs(Math.sin(frame * 1.7) * Math.cos(frame * 0.9));
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* vineta */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(26,18,8,0.55) 100%)",
        }}
      />
      {/* grano animado via SVG turbulence (seed distinto por frame) */}
      <svg width="100%" height="100%" style={{ position: "absolute", opacity: 0.09 }}>
        <filter id={`grain-${frame % 7}`}>
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.9"
            numOctaves="2"
            seed={frame % 7}
            stitchTiles="stitch"
          />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${frame % 7})`} />
      </svg>
      {/* flicker de exposición */}
      <AbsoluteFill style={{ background: "#000", opacity: 1 - flick }} />
    </AbsoluteFill>
  );
};

// --- Escena con parallax 2.5D ----------------------------------------------
// bg: imagen completa, escalada +, desenfocada levemente, deriva lenta.
// fg: recorte del personaje (rembg), nítido, deriva opuesta más rápida + zoom.
// El diferencial de velocidad es lo que el ojo lee como "profundidad real".
const ParallaxScene = ({ bg, fg, drift = 1, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = frame / durationInFrames; // 0..1 dentro de la escena

  const bgX = interpolate(t, [0, 1], [0, -28 * drift]);
  const fgX = interpolate(t, [0, 1], [0, 34 * drift]);
  const bgScale = interpolate(t, [0, 1], [1.18, 1.24]);
  const fgScale = interpolate(t, [0, 1], [1.02, 1.1]);
  const fgRot = interpolate(t, [0, 1], [0, 0.8 * drift]);

  return (
    <AbsoluteFill style={{ background: INK }}>
      <AbsoluteFill style={{ translate: `${bgX}px 0px`, scale: `${bgScale}` }}>
        <Img
          src={bg}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "blur(6px) brightness(0.82)",
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{ translate: `${fgX}px 0px`, scale: `${fgScale}`, rotate: `${fgRot}deg` }}
      >
        <Img
          src={fg}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "drop-shadow(0 18px 40px rgba(26,18,8,0.65))",
          }}
        />
      </AbsoluteFill>
      {children}
    </AbsoluteFill>
  );
};

// --- Caption cinético: palabras que POP con overshoot, activa en amarillo ---
const KineticCaption = ({ words, startFrame = 0, wordDur = 11 }) => {
  const frame = useCurrentFrame();
  const local = frame - startFrame;
  if (local < 0) return null;
  const activeIdx = Math.min(Math.floor(local / wordDur), words.length - 1);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 620,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "10px 16px",
          maxWidth: 880,
        }}
      >
        {words.map((w, i) => {
          const wStart = i * wordDur;
          const p = interpolate(local - wStart, [0, 7], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.2, 1.6, 0.4, 1), // overshoot = el "pop"
          });
          if (local < wStart) return null;
          const isActive = i === activeIdx;
          return (
            <span
              key={i}
              style={{
                fontFamily: "Arial Black, sans-serif",
                fontSize: isActive ? 84 : 72,
                fontWeight: 900,
                color: isActive ? GOLD : "#FFFFFF",
                scale: `${p}`,
                display: "inline-block",
                textShadow:
                  "0 0 14px rgba(0,0,0,0.9), 4px 4px 0 #1a1208, -3px -3px 0 #1a1208, 3px -3px 0 #1a1208, -3px 3px 0 #1a1208",
                letterSpacing: 1,
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

// --- Sticker de papel con física + deriva viva ------------------------------
const PaperSticker = ({ src, from }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0) return null;
  const enter = interpolate(local, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.2, 1.7, 0.35, 1),
  });
  const drift = Math.sin(local / 11) * 6;
  const tilt = -8 + Math.sin(local / 14) * 3;
  return (
    <div
      style={{
        position: "absolute",
        left: 96,
        top: 300 + drift,
        width: 250,
        height: 250,
        scale: `${enter}`,
        rotate: `${tilt}deg`,
        background: PAPER,
        border: `8px solid ${INK}`,
        borderRadius: 8,
        boxShadow: `12px 12px 0px ${INK}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      <Img src={src} style={{ width: "88%", height: "88%", objectFit: "contain" }} />
    </div>
  );
};

// --- Composición principal ---------------------------------------------------
export const Proof180 = () => {
  const S1 = 160; // frames escena 1
  const S2 = 160; // frames escena 2
  const TR = 18; // transición

  return (
    <AbsoluteFill style={{ background: INK }}>
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={S1}>
          <ParallaxScene
            bg={staticFile("proof/scene0_bg.png")}
            fg={staticFile("proof/scene0_fg.png")}
            drift={1}
          >
            <KineticCaption
              words={["The", "first", "time", "Hitler", "tried", "to", "steal", "a", "country"]}
              startFrame={8}
            />
          </ParallaxScene>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({ direction: "from-right" })}
          timing={springTiming({ config: { damping: 16, stiffness: 130 }, durationInFrames: TR })}
        />

        <TransitionSeries.Sequence durationInFrames={S2}>
          <ParallaxScene
            bg={staticFile("proof/scene1_bg.png")}
            fg={staticFile("proof/scene1_fg.png")}
            drift={-1}
          >
            <KineticCaption
              words={["a", "hundred", "fifty", "SS", "men", "dressed", "as", "police"]}
              startFrame={10}
            />
            <PaperSticker src={staticFile("proof/sticker.png")} from={26} />
          </ParallaxScene>
        </TransitionSeries.Sequence>
      </TransitionSeries>

      {/* capa película: grano + viñeta + flicker sobre TODO, incluida la transición */}
      <FilmLayer />

      {/* SFX sincronizado: whoosh en la transición, papel en el pop del sticker */}
      <Sequence from={S1 - TR} durationInFrames={30}>
        <Audio src={staticFile("proof/whoosh.mp3")} volume={0.5} />
      </Sequence>
      <Sequence from={S1 - TR + 26} durationInFrames={25}>
        <Audio src={staticFile("proof/paper.mp3")} volume={0.35} />
      </Sequence>
    </AbsoluteFill>
  );
};
