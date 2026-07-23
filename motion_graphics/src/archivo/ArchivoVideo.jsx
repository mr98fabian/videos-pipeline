import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, interpolate, useCurrentFrame } from "remotion";
import {
  Board,
  Backdrop,
  Cutout,
  PhotoScrap,
  CensorBar,
  ImpactFlash,
  Stamp,
  Typewriter,
  CaseAnnotations,
  ColdOpen,
  SubscribeStamp,
  CaseClosed,
  ShareCard,
  WrinkledMap,
  KineticTimed,
  makeCamera,
  LANES,
} from "./components";

// ============================================================================
// ARCHIVO VIVO — composicion COMPLETA manifest-driven.
// pipeline.py --archivo genera el manifest (escenas + recortes cacheados +
// timestamps reales del TTS + beats) y renderiza esto. Ver visual_cache.py.
//
// manifest = {
//   durationInFrames, coldOpen?: {src,label,tag,frames},
//   scenes: [{from, dur, bg, fg?, treatment: "sticker"|"photo", enterDir,
//             beats?: {stamp?:{text,at}, censor?:{x,y,w,h,at,reveal,label},
//                      zoom?:{at,scale,x,y}, typewriter?:{text,at,x,y}}}],
//   words: [{t, w}],   // frames globales (del TTS real)
//   close: {from, series, caseNo, share1, share2}
// }
// ============================================================================

const BurnFlash = ({ at }) => {
  // aproximacion de film-burn: barrido calido 8 frames en el corte al cierre
  const frame = useCurrentFrame();
  const local = frame - at;
  if (local < 0 || local > 8) return null;
  const p = local / 8;
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${20 + p * 60}% 50%, rgba(255,190,80,${0.85 * (1 - p)}) 0%, rgba(200,80,20,${0.5 * (1 - p)}) 35%, transparent 70%)`,
        pointerEvents: "none",
      }}
    />
  );
};

const SceneBlock = ({ scene, index }) => {
  const b = scene.beats || {};
  const shakes = [{ frame: 2, amp: 6 }];
  if (b.stamp) shakes.push({ frame: b.stamp.at, amp: 8 });
  if (b.censor) shakes.push({ frame: b.censor.reveal, amp: 8 });
  const beats = [];
  if (b.zoom) {
    beats.push({ frame: b.zoom.at, scale: b.zoom.scale ?? 1.35, x: b.zoom.x ?? 0, y: b.zoom.y ?? 0, dur: 7 });
    beats.push({ frame: b.zoom.at + 36, scale: 1.04, x: 0, y: 0, dur: 10 });
  }
  const cam = makeCamera(beats, shakes);
  const alt = index % 2 === 0;
  const dir = scene.enterDir || (alt ? "bottom" : "right");
  return (
    <Board camera={cam}>
      <Backdrop src={staticFile(scene.bg)} sceneDur={scene.dur} />
      {scene.treatment === "sticker" && scene.fg ? (
        <>
        <GroundCard index={index} hasSticker={(b.stickers || []).length > 0} />
        <Cutout
          src={staticFile(scene.fg)}
          from={0}
          x={50}
          y={LANES.safeTop + 90}
          w={980}
          h={1080}
          fromDir={dir}
          rot={alt ? -2 : 2}
        />
        </>
      ) : (
        <PhotoScrap
          src={staticFile(scene.bg)}
          from={0}
          x={55}
          y={LANES.safeTop + 150}
          w={970}
          h={1010}
          fromDir={dir === "bottom" ? "right" : dir}
          rot={alt ? 1.8 : -1.8}
        />
      )}
      {(b.stickers || []).map((st, k) => (
        <LibSticker key={k} src={staticFile(st.src)} from={st.at} side={k % 2 === 0 ? (index % 2 === 0 ? "right" : "left") : (index % 2 === 0 ? "left" : "right")} />
      ))}
      {b.numstamp ? <Stamp text={b.numstamp.text} from={b.numstamp.at} x={index % 2 === 0 ? 700 : 90} y={1120} rot={index % 2 === 0 ? 7 : -7} /> : null}
      {b.censor ? (
        <CensorBar x={b.censor.x} y={b.censor.y} w={b.censor.w} h={b.censor.h} from={b.censor.at ?? 6} revealFrame={b.censor.reveal} label={b.censor.label || "CLASSIFIED"} />
      ) : null}
      {b.stamp ? <Stamp text={b.stamp.text} from={b.stamp.at} x={90} y={280} rot={-8} /> : null}
      {b.typewriter ? <Typewriter text={b.typewriter.text} from={b.typewriter.at} x={b.typewriter.x ?? 120} y={b.typewriter.y ?? 210} /> : null}
    </Board>
  );
};

export const ArchivoVideo = ({ manifest }) => {
  const m = manifest;
  const coldFrames = m.coldOpen ? m.coldOpen.frames ?? 22 : 0;

  // flashes globales: cold open + reveals + stamps + corte al cierre
  const flashes = [];
  for (const s of m.scenes) {
    const b = s.beats || {};
    if (b.censor) flashes.push(s.from + b.censor.reveal);
    if (b.stamp) flashes.push(s.from + b.stamp.at);
  }
  flashes.push(m.close.from);

  return (
    <AbsoluteFill style={{ background: "#1a1208" }}>
      {/* escenas */}
      {m.scenes.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.dur}>
          <SceneBlock scene={s} index={i} />
        </Sequence>
      ))}

      {/* cierre: mapa vivo + share card + case closed + subscribe */}
      <Sequence from={m.close.from}>
        <Board camera={makeCamera([], [{ frame: 10, amp: 8 }, { frame: 34, amp: 7 }])}>
          <WrinkledMap src={staticFile("proof/europe_map.jpg")} opacity={0.55} />
          <ShareCard line1={m.close.share1} line2={m.close.share2} from={4} />
          <CaseClosed series={m.close.series} caseNo={m.close.caseNo} from={26} />
          <SubscribeStamp from={44} x={60} y={1560} />
        </Board>
      </Sequence>

      {/* cold open al frente de todo */}
      {m.coldOpen ? (
        <Sequence from={0} durationInFrames={coldFrames}>
          <ColdOpen src={staticFile(m.coldOpen.src)} label={m.coldOpen.label} tag={m.coldOpen.tag} durationInFrames={coldFrames} />
        </Sequence>
      ) : null}

      {/* captions con timestamps reales del TTS (por encima de las escenas) */}
      <KineticTimed words={m.words} endFrame={m.close.from} />

      {/* flashes + burn del cierre */}
      <ImpactFlash frames={flashes} />
      <BurnFlash at={m.close.from} />

      {/* ============ SFX del motor (frame-exactos) ============ */}
      {m.coldOpen ? (
        <Sequence from={0} durationInFrames={40}>
          <Audio src={staticFile("proof/sting.wav")} volume={0.5} />
        </Sequence>
      ) : null}
      {m.scenes.map((s, i) => (
        <Sequence key={`sw-${i}`} from={s.from} durationInFrames={20}>
          <Audio src={staticFile("proof/whoosh.mp3")} volume={0.45} />
        </Sequence>
      ))}
      {m.scenes.flatMap((s, i) => {
        const b = s.beats || {};
        const out = [];
        if (b.censor)
          out.push(
            <Sequence key={`rip-${i}`} from={s.from + b.censor.reveal - 1} durationInFrames={22}>
              <Audio src={staticFile("proof/rip.mp3")} volume={0.55} />
            </Sequence>
          );
        if (b.stamp)
          out.push(
            <Sequence key={`imp-${i}`} from={s.from + b.stamp.at - 1} durationInFrames={16}>
              <Audio src={staticFile("proof/impact.mp3")} volume={0.3} />
            </Sequence>
          );
        return out;
      })}
      <Sequence from={m.close.from} durationInFrames={20}>
        <Audio src={staticFile("proof/whoosh.mp3")} volume={0.55} />
      </Sequence>
      <Sequence from={m.close.from + 25} durationInFrames={16}>
        <Audio src={staticFile("proof/impact.mp3")} volume={0.32} />
      </Sequence>
      <Sequence from={m.close.from + 43} durationInFrames={16}>
        <Audio src={staticFile("proof/impact.mp3")} volume={0.3} />
      </Sequence>
    </AbsoluteFill>
  );
};


// --- sticker de biblioteca en mini-tarjeta de papel (densidad automatica v2) --
import { PAPER_LIGHT, INK, pop as _pop } from "./components";
import { useCurrentFrame as _ucf, Img as _Img } from "remotion";

const LibSticker = ({ src, from, side }) => {
  const frame = _ucf();
  const local = frame - from;
  if (local < 0) return null;
  const p = _pop(local, 8);
  const drift = Math.sin(local / 12) * 6;
  const x = side === "right" ? 738 : 62;
  return (
    <div
      style={{
        position: "absolute", left: x, top: 260 + drift, width: 280, height: 280,
        rotate: `${(side === "right" ? 6 : -6) + Math.sin(local / 15) * 2}deg`,
        scale: `${p}`,
        background: PAPER_LIGHT, border: `6px solid ${INK}`, borderRadius: 10,
        boxShadow: "10px 12px 0 rgba(26,18,8,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
    >
      <_Img src={src} style={{ width: "82%", height: "82%", objectFit: "contain", filter: "sepia(0.55) saturate(0.85)" }} />
    </div>
  );
};

// --- tarjeta que ancla al recorte principal: nunca mas "cabeza flotante" -----
const GroundCard = ({ index, hasSticker = false }) => {
  const frame = _ucf();
  const p = _pop(frame - 1, 9);
  return (
    <div
      style={{
        position: "absolute", left: 120, top: 300, width: 840, height: 940,
        rotate: `${index % 2 === 0 ? -2.5 : 2.5}deg`,
        scale: `${0.92 + 0.08 * p}`,
        background: PAPER_LIGHT, border: `5px solid ${INK}`,
        boxShadow: "14px 16px 0 rgba(26,18,8,0.45)",
        opacity: 0.96,
      }}
    >
      <CaseAnnotations from={10} index={index} hasSticker={hasSticker} />
    </div>
  );
};
