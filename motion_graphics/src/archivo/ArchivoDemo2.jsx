import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import {
  Board,
  Backdrop,
  CaseFile,
  Globe25D,
  CaseClosed,
  ShareCard,
  RedString,
  ImpactFlash,
  Kinetic,
  WrinkledMap,
  makeCamera,
} from "./components";

// ============================================================================
// DEMO TIER 2 — 12s: globo 2.5D + fichas de personaje + latido ambiente +
// cierre CASE #N CLOSED + tarjeta compartible + promesa de cadencia
// ============================================================================

export const ArchivoDemo2 = () => {
  const A = 170; // tablero investigacion
  const B = 190; // cierre

  const camA = makeCamera(
    [
      { frame: 120, scale: 1.28, x: -60, y: 140, dur: 7 },
      { frame: 152, scale: 1.04, x: 0, y: 0, dur: 10 },
    ],
    [
      { frame: 44, amp: 7 }, // ficha 1
      { frame: 78, amp: 7 }, // ficha 2
    ]
  );

  return (
    <AbsoluteFill style={{ background: "#1a1208" }}>
      {/* ============ TABLERO A: la investigacion (0-170) ============ */}
      <Sequence durationInFrames={A}>
        <Board camera={camA}>
          <Backdrop src={staticFile("proof/scene0_bg.png")} sceneDur={A} />
          {/* globo vintage gira hacia Europa y clava el pin */}
          <Globe25D mapSrc={staticFile("proof/worldmap.jpg")} from={4} x={300} y={170} size={480} />
          <Kinetic words={["1934.", "Europe", "holds", "its", "breath"]} from={12} bottom={520} size={74} />
          {/* fichas de los dos bandos */}
          <CaseFile
            photo={staticFile("proof/scene0_fg.png")}
            name="E. Dollfuss"
            role="The Target"
            from={42}
            x={80}
            y={880}
            w={360}
            rot={-5}
          />
          <CaseFile
            photo={staticFile("proof/sticker.png")}
            name="SS Regiment 89"
            role="The Killers"
            from={76}
            x={630}
            y={900}
            w={360}
            rot={4}
          />
          {/* hilo rojo conectando las fichas via el pin del globo */}
          <RedString from={{ x: 260, y: 1000 }} to={{ x: 640, y: 480 }} drawFrame={104} sag={50} />
          <RedString from={{ x: 640, y: 480 }} to={{ x: 810, y: 1020 }} drawFrame={116} sag={50} />
        </Board>
      </Sequence>

      {/* ============ TABLERO B: cierre de caso (170-360) ============ */}
      <Sequence from={A}>
        <Board camera={makeCamera([], [{ frame: 12, amp: 8 }, { frame: 40, amp: 7 }])}>
          {/* mapa antiguo VIVO de fondo (papel que respira + luz recorriendo) */}
          <WrinkledMap src={staticFile("proof/europe_map.jpg")} opacity={0.55} />
          <ShareCard line1="Mussolini stopped Hitler." line2="Yes. In 1934." from={4} />
          <CaseClosed series="WWII Secrets" caseNo={15} from={30} />
        </Board>
      </Sequence>

      <ImpactFlash frames={[46, 80, 182, 212]} />

      {/* ============ AUDIO: latido de tension + golpes ============ */}
      <Sequence from={0} durationInFrames={A}>
        <Audio src={staticFile("proof/heartbeat.wav")} volume={0.28} loop />
      </Sequence>
      <Sequence from={2} durationInFrames={22}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.5} /></Sequence>
      <Sequence from={44} durationInFrames={18}><Audio src={staticFile("proof/paper.mp3")} volume={0.4} /></Sequence>
      <Sequence from={78} durationInFrames={18}><Audio src={staticFile("proof/paper.mp3")} volume={0.4} /></Sequence>
      <Sequence from={103} durationInFrames={16}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.35} /></Sequence>
      <Sequence from={170} durationInFrames={20}><Audio src={staticFile("proof/whoosh.mp3")} volume={0.55} /></Sequence>
      <Sequence from={181} durationInFrames={18}><Audio src={staticFile("proof/impact.mp3")} volume={0.3} /></Sequence>
      <Sequence from={211} durationInFrames={18}><Audio src={staticFile("proof/impact.mp3")} volume={0.32} /></Sequence>
    </AbsoluteFill>
  );
};
