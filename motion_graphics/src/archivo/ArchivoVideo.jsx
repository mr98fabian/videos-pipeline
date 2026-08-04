import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, interpolate, useCurrentFrame, Easing } from "remotion";
import {
  Board,
  Backdrop,
  Atmosphere,
  Cutout,
  PhotoScrap,
  CensorBar,
  ImpactFlash,
  Stamp,
  Typewriter,
  CaseAnnotations,
  CTAStamp,
  HookText,
  EffectOverlay,
  ActionFX,
  EvidencePhoto,
  ColdOpen,
  SubscribeStamp,
  CaseClosed,
  ShareCard,
  WrinkledMap,
  KineticTimed,
  makeCamera,
  parallaxDepth,
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

// escenario del sujeto: la caja donde vivia el recorte entero. Las piezas del
// multi-recorte se mapean aqui con su geometria normalizada, asi la composicion
// original de la imagen se respeta (quien esta a la izquierda sigue a la izquierda).
const STAGE = { x: 50, y: LANES.safeTop + 90, w: 980, h: 1080 };
const PART_GROW = 1.15; // las piezas sueltas se leen chicas: se agrandan un poco

// TRANSICIONES DE CORTE (27 jul 2026) — CATALOGO ROTATIVO.
// Antes todos los cortes usaban el mismo barrido de luz, y con 10 escenas el
// ojo lo detecta como un tic mecanico. Ahora rota entre 6 variantes distintas
// segun el indice de escena, todas cortas (12-18f) y todas con la misma regla
// del canal: corte DURO, nunca fundido lento.
//
// Nota de implementacion: nada de "screen" blend. Las tarjetas del motor son de
// papel casi blanco y un blanco en screen sobre blanco no cambia nada (bug de
// la v1). Todas las variantes velan primero el cuadro con blend normal.
const TRANSITIONS = ["leakL", "burn", "leakR", "wipeDown", "flashShake", "wipeSide"];

const CutTransition = ({ at, variant = "leakL", dur = 16 }) => {
  const frame = useCurrentFrame();
  const local = frame - at;
  if (local < 0 || local > dur) return null;
  const half = dur / 2;
  const p = local < half
    ? interpolate(local, [0, half], [0, 1], { easing: Easing.out(Easing.cubic) })
    : interpolate(local, [half, dur], [1, 0], { easing: Easing.in(Easing.cubic) });
  const t = interpolate(local, [0, dur], [0, 1]);

  // 1. barrido de luz calido, izquierda -> derecha
  if (variant === "leakL" || variant === "leakR") {
    const pos = variant === "leakL"
      ? interpolate(t, [0, 1], [-20, 120])
      : interpolate(t, [0, 1], [120, -20]);
    const ang = variant === "leakL" ? 100 : 260;
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ background: `rgba(40,22,8,${0.28 * p})` }} />
        <AbsoluteFill style={{
          background: `linear-gradient(${ang}deg,
            transparent ${pos - 26}%,
            rgba(255,140,40,${0.55 * p}) ${pos - 12}%,
            rgba(255,246,225,${0.92 * p}) ${pos}%,
            rgba(255,140,40,${0.55 * p}) ${pos + 12}%,
            transparent ${pos + 26}%)`,
        }} />
      </AbsoluteFill>
    );
  }

  // 2. quemado de pelicula: mancha calida que se abre desde un lado
  if (variant === "burn") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ background: `rgba(30,16,6,${0.22 * p})` }} />
        <AbsoluteFill style={{
          background: `radial-gradient(circle at ${15 + t * 70}% ${40 + t * 20}%,
            rgba(255,250,230,${0.95 * p}) 0%,
            rgba(255,150,50,${0.7 * p}) ${8 + t * 22}%,
            rgba(120,50,10,${0.35 * p}) ${25 + t * 30}%,
            transparent 70%)`,
        }} />
      </AbsoluteFill>
    );
  }

  // 3. barrido de papel de arriba a abajo (borde duro, como pasar una hoja)
  if (variant === "wipeDown") {
    const y = interpolate(t, [0, 1], [-15, 115]);
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ background: `rgba(40,22,8,${0.25 * p})` }} />
        <AbsoluteFill style={{
          background: `linear-gradient(180deg,
            transparent ${y - 14}%,
            rgba(255,238,205,${0.88 * p}) ${y - 4}%,
            rgba(214,140,60,${0.6 * p}) ${y}%,
            transparent ${y + 12}%)`,
        }} />
      </AbsoluteFill>
    );
  }

  // 4. destello seco de impacto: sin barrido, solo un golpe de luz muy corto
  if (variant === "flashShake") {
    const punch = interpolate(local, [0, 2, 7], [0, 1, 0],
      { extrapolateRight: "clamp" });
    return (
      <AbsoluteFill style={{
        pointerEvents: "none",
        background: `rgba(255,244,222,${0.62 * punch})`,
      }} />
    );
  }

  // 5. barrido lateral oscuro (tinta), derecha -> izquierda
  const x = interpolate(t, [0, 1], [115, -15]);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{
        background: `linear-gradient(90deg,
          transparent ${x - 18}%,
          rgba(38,22,10,${0.75 * p}) ${x - 6}%,
          rgba(26,18,8,${0.85 * p}) ${x}%,
          transparent ${x + 14}%)`,
      }} />
    </AbsoluteFill>
  );
};

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

const SceneBlock = ({ scene, index, caseBase = 1, opening = false }) => {
  const b = scene.beats || {};
  const shakes = [{ frame: 2, amp: 6 }];
  if (b.stamp) shakes.push({ frame: b.stamp.at, amp: 8 });
  if (b.censor) shakes.push({ frame: b.censor.reveal, amp: 8 });
  // sacudida de camara al golpe de accion (impacto/explosion/derrumbe)
  if (b.action && ["explosion", "impact", "topple", "fall", "collapse", "shoot"].includes(b.action.type))
    shakes.push({ frame: b.action.at ?? 6, amp: 16, dur: 8 });
  const beats = [];
  if (b.zoom) {
    beats.push({ frame: b.zoom.at, scale: b.zoom.scale ?? 1.35, x: b.zoom.x ?? 0, y: b.zoom.y ?? 0, dur: 7 });
    beats.push({ frame: b.zoom.at + 36, scale: 1.04, x: 0, y: 0, dur: 10 });
  }
  // PRIMER FRAME EN MOVIMIENTO: un frame estatico es objetivo de scroll. La
  // escena 1 arranca cerrada y se abre de golpe en ~0,5s, asi que ya hay
  // movimiento en el frame 0 sin depender de que la imagen tenga accion.
  if (index === 0) beats.unshift({ frame: 0, scale: 1.34, x: 0, y: 0, dur: 1 },
                                 { frame: 1, scale: 1.0, x: 0, y: 0, dur: 15 });
  const cam = makeCamera(beats, shakes);
  const alt = index % 2 === 0;
  const dir = scene.enterDir || (alt ? "bottom" : "right");
  const parts = scene.parts || [];
  // centro (en px de lienzo) de la pieza que ACTUA -> ahi revienta el FX de comic
  const fxAt = parts.length
    ? { x: STAGE.x + parts[0].nx * STAGE.w, y: STAGE.y + parts[0].ny * STAGE.h }
    : { x: 540, y: 640 };
  return (
    <Board camera={cam}>
      <Backdrop src={staticFile(scene.bg)} sceneDur={scene.dur} camera={cam} depth={0.12} opening={opening} />
      {scene.treatment === "sticker" && scene.fg ? (
        <>
        <GroundCard index={index} caseBase={caseBase} camera={cam} />
        {parts.length >= 2 ? (
          // MULTI-RECORTE: cada figura/objeto es su propio sticker, colocado donde
          // estaba en la imagen original, con su propia profundidad y su propia
          // accion (uno actua, los otros reaccionan) -> interactuan entre si.
          parts.map((pt, k) => {
            const gw = Math.min(pt.nw * STAGE.w * PART_GROW, STAGE.w);
            const gh = Math.min(pt.nh * STAGE.h * PART_GROW, STAGE.h);
            // clamp al lienzo: una pieza que nacio pegada al borde de la imagen
            // fuente se saldria del cuadro al agrandarla (medido 25 jul 2026:
            // los oficiales de los extremos quedaban cortados)
            const clamp = (v, lo, hi) => Math.max(lo, Math.min(v, hi));
            return (
              <Cutout
                key={k}
                src={staticFile(pt.src)}
                from={opening ? 0 : pt.from ?? 0}
                opening={opening}
                x={clamp(STAGE.x + pt.nx * STAGE.w - gw / 2, 62, 1018 - gw)}
                y={clamp(STAGE.y + pt.ny * STAGE.h - gh / 2, LANES.safeTop, LANES.captionTop - gh * 0.62)}
                w={gw}
                h={gh}
                fromDir={pt.dir || dir}
                rot={k % 2 === 0 ? -2 : 2}
                driftAmp={4 + k}          // deriva desfasada: no respiran al unisono
                action={pt.action || null}
                camera={cam}
                depth={pt.depth ?? 1.0}
              />
            );
          })
        ) : (
        <Cutout
          src={staticFile(scene.fg)}
          video={scene.fgVideo ? staticFile(scene.fgVideo) : null}
          from={0}
          x={50}
          y={LANES.safeTop + 90}
          w={980}
          h={1080}
          fromDir={dir}
          rot={alt ? -2 : 2}
          action={b.action || null}
          camera={cam}
          depth={1.0}
          opening={opening}
        />
        )}
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
          camera={cam}
          depth={0.82}
          opening={opening}
        />
      )}
      <Atmosphere camera={cam} />
      {(b.stickers || []).map((st, k) => (
        <LibSticker key={k} src={staticFile(st.src)} from={st.at} side={k % 2 === 0 ? (index % 2 === 0 ? "right" : "left") : (index % 2 === 0 ? "left" : "right")} />
      ))}
      {b.numstamp ? <Stamp text={b.numstamp.text} from={b.numstamp.at} x={index % 2 === 0 ? 700 : 90} y={1120} rot={index % 2 === 0 ? 7 : -7} /> : null}
      {b.censor ? (
        <CensorBar x={b.censor.x} y={b.censor.y} w={b.censor.w} h={b.censor.h} from={b.censor.at ?? 6} revealFrame={b.censor.reveal} label={b.censor.label || "CLASSIFIED"} />
      ) : null}
      {b.stamp ? <Stamp text={b.stamp.text} from={b.stamp.at} x={90} y={280} rot={-8} /> : null}
      {b.typewriter ? <Typewriter text={b.typewriter.text} from={b.typewriter.at} x={b.typewriter.x ?? 120} y={b.typewriter.y ?? 210} /> : null}
      {b.action ? <ActionFX action={b.action} from={0} cx={fxAt.x} cy={fxAt.y} /> : null}
      {b.evidence ? <EvidencePhoto src={staticFile(b.evidence.src)} from={b.evidence.at} year={b.evidence.year} side={index % 2 === 0 ? "right" : "left"} /> : null}
      {b.cta ? <CTAStamp from={b.cta.at} caseNo={caseBase} dur={b.cta.dur ?? 46} label={b.cta.label} /> : null}
      {b.effect ? <EffectOverlay src={staticFile(b.effect.src)} category={b.effect.category}
        from={b.effect.at} dur={b.effect.dur ?? 70} opacity={b.effect.opacity ?? 0.85} /> : null}
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

  // corte de escena (no el primero: ahi no hay nada de que venir)
  const sceneCuts = m.scenes.slice(1).map((s) => s.from);

  return (
    <AbsoluteFill style={{ background: "#1a1208" }}>
      {/* escenas */}
      {m.scenes.map((s, i) => (
        <Sequence key={i} from={s.from} durationInFrames={s.dur}>
          <SceneBlock scene={s} index={i} caseBase={m.caseBase ?? 1} opening={i === 0 && !m.coldOpen} />
        </Sequence>
      ))}

      {/* CIERRE DESACTIVADO (27 jul 2026): la tarjeta CASE #N / share-card /
          SUBSCRIBE anunciaba el final justo donde el bucle tiene que ser
          invisible. Se renderiza solo si el manifest trae cola de cierre. */}
      {m.durationInFrames > m.close.from ? (
      <Sequence from={m.close.from}>
        <Board camera={makeCamera([], [{ frame: 10, amp: 8 }, { frame: 34, amp: 7 }])}>
          <WrinkledMap src={staticFile("proof/europe_map.jpg")} opacity={0.55} />
          <ShareCard line1={m.close.share1} line2={m.close.share2} from={4} />
          <CaseClosed series={m.close.series} caseNo={m.close.caseNo} from={26} />
          <SubscribeStamp from={44} x={60} y={1560} />
        </Board>
      </Sequence>
      ) : null}

      {/* cold open al frente de todo */}
      {m.coldOpen ? (
        <Sequence from={0} durationInFrames={coldFrames}>
          <ColdOpen src={staticFile(m.coldOpen.src)} label={m.coldOpen.label} tag={m.coldOpen.tag} durationInFrames={coldFrames} />
        </Sequence>
      ) : null}

      {/* captions con timestamps reales del TTS (por encima de las escenas) */}
      <KineticTimed words={m.words} endFrame={m.close.from} openerCount={m.coldOpen ? 0 : m.openerWords ?? 0} />
      {/* promesa legible desde el frame 0 */}
      <HookText text={m.hook} />

      {/* flashes + burn del cierre */}
      <ImpactFlash frames={flashes} />
      {/* cada corte con una transicion distinta del catalogo (rota por indice) */}
      {sceneCuts.map((t, i) => (
        <CutTransition key={`ct-${i}`} at={t} variant={TRANSITIONS[i % TRANSITIONS.length]} />
      ))}
            <BurnFlash at={m.close.from} />

      {/* ============ SFX del motor (frame-exactos) ============ */}
      {m.coldOpen ? (
        <Sequence from={0} durationInFrames={40}>
          <Audio src={staticFile("proof/sting.wav")} volume={0.5} />
        </Sequence>
      ) : null}
      {/* SFX de corte EMPAREJADO al caracter de la transicion visual, no un
          whoosh generico repetido -- monotono es lo que se lee como "AI slop"
          frente a un edit profesional donde cada entrada suena distinta
          (ver skill explainer-parallax, hallazgo del 3 ago 2026). */}
      {m.scenes.map((s, i) => {
        const variant = i === 0 ? null : TRANSITIONS[(i - 1) % TRANSITIONS.length];
        const CUT_SFX = {
          leakL: { src: "proof/whoosh.mp3", vol: 0.45 },
          leakR: { src: "proof/whoosh.mp3", vol: 0.45 },
          burn: { src: "proof/impact.mp3", vol: 0.4 },
          wipeDown: { src: "proof/paper.mp3", vol: 0.4 },
          flashShake: { src: "proof/impact.mp3", vol: 0.5 },
          wipeSide: { src: "proof/rip.mp3", vol: 0.4 },
        };
        const sfx = variant ? CUT_SFX[variant] : { src: "proof/whoosh.mp3", vol: 0.45 };
        return (
          <Sequence key={`sw-${i}`} from={s.from} durationInFrames={20}>
            <Audio src={staticFile(sfx.src)} volume={sfx.vol} />
          </Sequence>
        );
      })}
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
const GroundCard = ({ index, caseBase = 1, camera = null }) => {
  const frame = _ucf();
  const p = _pop(frame - 1, 9);
  const par = parallaxDepth(camera, frame, 0.55); // plano MEDIO
  return (
    <div
      style={{
        position: "absolute", left: 120 + par.tx, top: 300 + par.ty, width: 840, height: 940,
        rotate: `${index % 2 === 0 ? -2.5 : 2.5}deg`,
        scale: `${(0.92 + 0.08 * p) * par.sc}`,
        background: PAPER_LIGHT, border: `5px solid ${INK}`,
        boxShadow: "14px 16px 0 rgba(26,18,8,0.45)",
        opacity: 0.96,
      }}
    >
      <CaseAnnotations from={10} index={index} caseBase={caseBase} />
    </div>
  );
};
