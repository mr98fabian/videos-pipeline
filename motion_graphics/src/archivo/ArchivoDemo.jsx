import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import {
  Board,
  Backdrop,
  Cutout,
  PhotoScrap,
  CensorBar,
  RedString,
  ImpactFlash,
  Kinetic,
  Stamp,
  makeCamera,
} from "./components";

// ============================================================================
// DEMO TIER 1 — 12s: censura que se arranca + hilo rojo + zoom-evidencia +
// impact frames + entradas flip 3D. Misma historia Dollfuss del proof.
// ============================================================================

export const ArchivoDemo = () => {
  const CUT = 180; // corte duro a los 6s

  // Tablero A: zoom-evidencia al pin de Viena en f120 (tras conectar el hilo)
  const camA = makeCamera(
    [
      { frame: 118, scale: 1.5, x: -430, y: 330, dur: 7 }, // clavarse en el mapa (arriba-der)
      { frame: 162, scale: 1.06, x: 0, y: 0, dur: 10 }, // volver antes del corte
    ],
    [
      { frame: 56, amp: 8 }, // rip de la censura
      { frame: 96, amp: 9 }, // sello
    ]
  );

  // Tablero B (frames LOCALES: la Sequence resetea el reloj a 0)
  const camB = makeCamera(
    [
      { frame: 66, scale: 1.55, x: 30, y: 260, dur: 7 }, // zoom-evidencia cara central
      { frame: 120, scale: 1.06, x: 0, y: 0, dur: 10 },
    ],
    [
      { frame: 0, amp: 8 }, // aterrizaje foto
      { frame: 34, amp: 9 }, // rip censura B
      { frame: 52, amp: 8 }, // sello DISGUISED
    ]
  );

  return (
    <AbsoluteFill style={{ background: "#1a1208" }}>
      {/* ============ TABLERO A (0-180) ============ */}
      <Sequence durationInFrames={CUT}>
        <Board camera={camA}>
          <Backdrop src={staticFile("proof/scene0_bg.png")} sceneDur={CUT} />
          {/* canciller entra con flip 3D */}
          <Cutout src={staticFile("proof/scene0_fg.png")} from={2} x={60} y={240} w={960} h={1080} fromDir="bottom" rot={-2} />
          {/* CENSURA sobre su cara -> se ARRANCA en f56 */}
          <CensorBar x={250} y={430} w={580} h={190} from={16} revealFrame={56} label="CLASSIFIED" />
          <Kinetic words={["The", "man", "the", "Nazis", "wanted", "DEAD"]} from={20} bottom={520} size={78} />
          {/* mapa + HILO ROJO conectando al canciller con Viena */}
          <MapScrapDemo from={70} />
          <RedString from={{ x: 540, y: 560 }} to={{ x: 905, y: 340 }} drawFrame={84} sag={70} />
          <Stamp text="JULY 25, 1934" from={96} x={110} y={1180} rot={-9} />
        </Board>
      </Sequence>

      {/* ============ TABLERO B (180-360) ============ */}
      <Sequence from={CUT}>
        <Board camera={camB}>
          <Backdrop src={staticFile("proof/scene1_bg.png")} sceneDur={180} />
          <PhotoScrap src={staticFile("proof/scene1_bg.png")} from={0} x={55} y={330} w={970} h={1040} fromDir="right" rot={1.8} />
          {/* censura sobre los uniformes -> rip en frame local 34 */}
          <CensorBar x={180} y={640} w={720} h={170} from={8} revealFrame={34} label="WHO ARE THEY?" />
          <Kinetic words={["150", "SS", "men", "dressed", "as", "POLICE"]} from={40} wordDur={8} size={80} bottom={470} />
          <Cutout src={staticFile("proof/sticker.png")} from={20} x={730} y={200} w={240} h={240} fromDir="top" rot={7} driftAmp={7} />
          <RedString from={{ x: 850, y: 330 }} to={{ x: 540, y: 700 }} drawFrame={58} sag={60} />
          <Stamp text="DISGUISED" from={52} x={120} y={300} rot={-7} />
        </Board>
      </Sequence>

      {/* flashes de impacto globales (frames absolutos) */}
      <ImpactFlash frames={[56, 96, 180, 214, 232]} />

      {/* ============ SFX ============ */}
      <Sequence from={2} durationInFrames={22}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.5} /></Sequence>
      <Sequence from={55} durationInFrames={24}><Audio src={staticFile("proof/rip.mp3")} volume={0.6} /></Sequence>
      <Sequence from={70} durationInFrames={20}><Audio src={staticFile("proof/paper.mp3")} volume={0.4} /></Sequence>
      <Sequence from={95} durationInFrames={18}><Audio src={staticFile("proof/impact.mp3")} volume={0.32} /></Sequence>
      <Sequence from={117} durationInFrames={18}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.4} /></Sequence>
      <Sequence from={CUT} durationInFrames={20}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.55} /></Sequence>
      <Sequence from={213} durationInFrames={22}><Audio src={staticFile("proof/rip.mp3")} volume={0.6} /></Sequence>
      <Sequence from={231} durationInFrames={18}><Audio src={staticFile("proof/impact.mp3")} volume={0.32} /></Sequence>
      <Sequence from={245} durationInFrames={18}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.4} /></Sequence>
    </AbsoluteFill>
  );
};

// --- mapa Austria (version demo, misma del proof aprobado) -------------------
import { interpolate as _i, useCurrentFrame as _f, Easing as _E } from "remotion";
import { INK, RED, pop as _pop } from "./components";

const MapScrapDemo = ({ from }) => {
  const frame = _f();
  const local = frame - from;
  if (local < 0) return null;
  const p = _pop(local, 9);
  const pinBeat = 1 + 0.18 * Math.abs(Math.sin(local / 6));
  return (
    <div
      style={{
        position: "absolute", left: 620, top: 190, width: 430, height: 330,
        rotate: `${3 - 1.5 * p}deg`, scale: `${p}`,
        background: "#EFE3C4", border: `6px solid ${INK}`,
        boxShadow: "12px 14px 0 rgba(26,18,8,0.5)", overflow: "hidden",
      }}
    >
      <svg width="430" height="330" viewBox="0 0 430 330">
        <path
          d="M 22 186 Q 30 172 48 176 L 74 168 Q 88 158 104 164 L 128 154 Q 150 140 176 146 L 210 132 Q 248 118 288 124 L 330 118 Q 368 112 396 128 Q 412 140 404 158 L 410 176 Q 414 194 396 202 L 372 214 Q 344 228 312 222 L 270 232 Q 234 240 200 230 L 162 236 Q 130 240 108 226 L 76 222 Q 52 220 40 206 Q 24 200 22 186 Z"
          fill="#DECBA0" stroke={INK} strokeWidth="7" strokeLinejoin="round"
        />
        <text x="120" y="205" fontFamily="Arial Black" fontWeight="900" fontSize="42" fill={INK} opacity="0.85">AUSTRIA</text>
        <circle cx="352" cy="150" r={13 * pinBeat} fill={RED} stroke={INK} strokeWidth="5" />
        <line x1="352" y1="150" x2="330" y2="106" stroke={RED} strokeWidth="5" />
        <text x="252" y="96" fontFamily="Arial Black" fontWeight="900" fontSize="32" fill={RED}>VIENNA</text>
      </svg>
    </div>
  );
};
