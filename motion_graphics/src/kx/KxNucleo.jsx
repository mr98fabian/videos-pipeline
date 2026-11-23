// Composición de prueba de la Fase 1: aplica los tokens (paleta, 2 fuentes,
// grano, boiling line, candado de paleta en el raster) y el karaoke sobre
// un tramo real de la voz qw_korex. No es una plantilla de producción.
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { DEBT, INK, PAPER, SAFE, TYPE } from "./tokens";
import { DISPLAY_FAMILY, MARKER_FAMILY } from "./fonts";
import { Boil, BoilDefs, FilmGrain, PaletteLockDefs } from "./texture";
import { KxCaptions } from "./KxCaptions";

const Underline = ({ id, width, color, progress }) => (
  <svg width={width} height={40} viewBox={`0 0 ${width} 40`} style={{ display: "block", filter: `url(#${id})` }}>
    <BoilDefs id={id} />
    <path
      d={`M6 26 C ${width * 0.3} 14, ${width * 0.6} 34, ${width - 6} 18`}
      stroke={color}
      strokeWidth={11}
      strokeLinecap="round"
      fill="none"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - progress}
    />
  </svg>
);

export const KxNucleo = ({ voice, pose, captions, heroMs, charBox }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const heroFrame = Math.round((heroMs / 1000) * fps);
  const heroIn = spring({ frame: frame - heroFrame, fps, config: { damping: 11, stiffness: 170 } });
  const heroLine = interpolate(frame, [heroFrame + 6, heroFrame + 20], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const underline = interpolate(frame, [8, 26], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bob = Math.sin((frame / fps) * Math.PI * 1.1) * 8;
  const squash = 1 + Math.sin((frame / fps) * Math.PI * 2.2) * 0.015;

  return (
    <AbsoluteFill style={{ background: PAPER }}>
      {voice ? <Audio src={staticFile(voice)} /> : null}
      <PaletteLockDefs />

      <Boil id="kx-title-boil" style={{ position: "absolute", left: SAFE.left, top: SAFE.top + 8, width: SAFE.width, textAlign: "center" }}>
        <div style={{ fontFamily: DISPLAY_FAMILY, fontWeight: TYPE.titleWeight, fontSize: TYPE.titleSize, color: INK, letterSpacing: -2 }}>
          SOBREGIRO
        </div>
      </Boil>

      {/* Caja del personaje: la QA exige 0 píxeles de color dentro. */}
      <div
        style={{
          position: "absolute", left: charBox.x, top: charBox.y, width: charBox.w, height: charBox.h,
          display: "flex", alignItems: "flex-end", justifyContent: "center",
        }}
      >
        <Img
          src={staticFile(pose)}
          style={{
            maxWidth: "100%", maxHeight: "100%", objectFit: "contain",
            filter: "url(#kx-palette-lock)",
            transform: `translateY(${bob}px) scale(${1 / squash}, ${squash})`,
            transformOrigin: "50% 100%",
          }}
        />
      </div>

      <div style={{ position: "absolute", left: 500, top: 470, width: SAFE.right - 500 }}>
        <div style={{ fontFamily: MARKER_FAMILY, fontSize: TYPE.markerSize * 0.8, color: INK, lineHeight: 1 }}>cortesía</div>
        <Underline id="kx-ul-boil" width={300} color={INK} progress={underline} />
      </div>

      {frame >= heroFrame ? (
        <div
          style={{
            position: "absolute", left: 500, top: 620, width: SAFE.right - 500, textAlign: "center",
            transform: `scale(${heroIn})`, transformOrigin: "50% 60%",
          }}
        >
          <div style={{ fontFamily: DISPLAY_FAMILY, fontWeight: TYPE.heroWeight, fontSize: 160, color: DEBT, lineHeight: 0.9, letterSpacing: -6 }}>
            $35
          </div>
          <div style={{ display: "flex", justifyContent: "center" }}>
            <Underline id="kx-hero-boil" width={300} color={DEBT} progress={heroLine} />
          </div>
        </div>
      ) : null}

      <KxCaptions captions={captions} />
      <FilmGrain />
    </AbsoluteFill>
  );
};
