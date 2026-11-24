// Texturas reutilizables: grano de película, boiling line y el candado de
// paleta para rasters (personajes). Todas respetan la paleta: el grano es
// acromático y se multiplica, así un píxel PAPER/INK sigue sobre la recta
// INK→PAPER y la QA de color no lo cuenta como fuera de paleta.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { BOIL, GRAIN, INK, PAPER } from "./tokens";

const hexToUnit = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
};

export const FilmGrain = ({ opacity = GRAIN.opacity }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "multiply", opacity }}>
      <svg width="100%" height="100%">
        <filter id="kx-grain">
          <feTurbulence
            type="fractalNoise"
            baseFrequency={GRAIN.baseFrequency}
            numOctaves="2"
            seed={frame % 97}
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#kx-grain)" />
      </svg>
    </AbsoluteFill>
  );
};

// Semilla del boil: cambia cada BOIL.step frames y cicla entre BOIL.variants
// dibujos, como una animación a mano "on threes".
export const useBoilSeed = (offset = 0) => {
  const frame = useCurrentFrame();
  return (Math.floor(frame / BOIL.step) + offset) % BOIL.variants;
};

// <BoilDefs id> define el filtro; cualquier SVG o HTML lo usa con
// filter: url(#id). Separado de <Boil> para que un SVG grande lo declare una vez.
export const BoilDefs = ({ id, offset = 0, scale = BOIL.scale }) => {
  const seed = useBoilSeed(offset);
  return (
    <svg width="0" height="0" style={{ position: "absolute" }}>
      <filter id={id} x="-5%" y="-5%" width="110%" height="110%">
        <feTurbulence
          type="fractalNoise"
          baseFrequency={BOIL.baseFrequency}
          numOctaves="2"
          seed={seed * 7 + 1}
          result="n"
        />
        <feDisplacementMap in="SourceGraphic" in2="n" scale={scale} />
      </filter>
    </svg>
  );
};

export const Boil = ({ id, offset = 0, scale, style, children }) => (
  <div style={{ ...style, filter: `url(#${id})` }}>
    <BoilDefs id={id} offset={offset} scale={scale} />
    {children}
  </div>
);

// Candado de paleta para rasters: luminancia → recta INK…PAPER (duotono).
// Un PNG con blanco puro o negro puro queda fuera de paleta sin esto.
export const PaletteLockDefs = ({ id = "kx-palette-lock" }) => {
  const ink = hexToUnit(INK);
  const paper = hexToUnit(PAPER);
  const table = (c) => `${ink[c]} ${paper[c]}`;
  return (
    <svg width="0" height="0" style={{ position: "absolute" }}>
      <filter id={id} colorInterpolationFilters="sRGB">
        <feColorMatrix type="saturate" values="0" />
        <feComponentTransfer>
          <feFuncR type="table" tableValues={table(0)} />
          <feFuncG type="table" tableValues={table(1)} />
          <feFuncB type="table" tableValues={table(2)} />
        </feComponentTransfer>
      </filter>
    </svg>
  );
};
