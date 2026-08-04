import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, staticFile, interpolate, useCurrentFrame, Easing } from "remotion";
import { makeCamera, parallaxDepth, pop, POP_EASE, SLAM_EASE } from "../archivo/components";

// ============================================================================
// KOREX — motor visual del canal de finanzas satiricas (Tadeo el mapache).
//
// POR QUE EXISTE APARTE DE "ARCHIVO VIVO" (3 ago 2026): Archivo Vivo es la piel
// de HiddenFacts -- expediente de misterio: polaroid "REAL", sello "EXHIBIT B",
// numero de caso, anotaciones rojas de detective. Esa piel se aplicaba a TODO lo
// que pasara por --archivo, asi que el primer video de Tadeo salio siendo un
// mapache comico metido dentro de un expediente policial. No era un fallo de
// tecnica de edicion: era el disfraz equivocado.
//
// REGLAS DE ESTA PLANTILLA (derivadas de Cuphead / Kurzgesagt / Duolingo-Titmouse,
// investigado 3 ago 2026 -- ver skill explainer-parallax):
//
//  1. UN SET FIJO, no un fondo nuevo por escena. Lo que separa "pieza artistica
//     intencional" de "imagenes de IA cosidas" es que el mundo sea el MISMO y la
//     profundidad venga de capas con parallax, no de una imagen nueva a sangre
//     cada 4 segundos.
//  2. PALETA CERRADA de 3 tonos: linea negra, crema, y UN acento por villano.
//     Ningun otro color entra en cuadro. El grade se aplica al video entero para
//     que cada imagen generada no traiga su propio balance de blancos.
//  3. TIPOGRAFIA anclada SIEMPRE en la misma zona (sin rebotar), resaltado
//     karaoke unicamente en el acento del villano de esa escena.
//  4. CORTES DUROS sobre golpe de foley; 3 wipes de la era rubber-hose (iris,
//     barrido, match-cut) rotando. Cero disolvencias lentas.
//  5. MOVIMIENTO: push-in lento de camara + squash-stretch del personaje sobre
//     las silabas. Nada de punch-zooms aleatorios.
//
// manifest = {
//   durationInFrames,
//   scenes: [{from, dur, bg, fg?, accent?, dataBeat?}],
//   words: [{t, w}],
//   hook, openerWords
// }
//
// DATA BEAT (3 ago 2026, prestado de @craftedbycm / estilo Vox, ver el chat):
// dataBeat = { type: "chartUp"|"chartDown"|"arrow"|"circle", from, dur }.
// Vox anota sobre FOTOS a color + scans desaturados -- eso rompe la regla 1
// (set fijo) y la regla 2 (paleta cerrada) de esta plantilla, asi que esa
// parte NO se copia. Lo unico que si transfiere es la linea de dato dibujada
// a mano sobre el cuadro (grafico/flecha/circulo), y encaja mejor aqui que en
// Vox porque el canal ES de finanzas: se dibuja en el acento de la escena, se
// traza progresivo (nunca aparece de golpe) y vive sobre el set fijo, no lo
// reemplaza. Ver DataAnnotation mas abajo.
// ============================================================================

// --- paleta cerrada (regla 2) -----------------------------------------------
export const KX_INK = "#141414";      // linea
export const KX_CREAM = "#EFE7D6";    // base del set
export const KX_CREAM_DEEP = "#DBCEB5";
// acentos: uno por villano, nunca dos a la vez en cuadro
export const KX_ACCENTS = {
  witch: "#8FBF4D",   // Bruja del Banco: verde enfermizo
  tycoon: "#D4A22B",  // Mapache Millonario: dorado
  neutral: "#C7472F", // Tadeo solo / explicacion: rojo teja
};

const FPS = 30;

// ============================================================================
// SET FIJO — el "escenario" que NO cambia entre escenas (regla 1).
// Papel crema con viñeta entintada a mano y un suelo sugerido. Se dibuja en SVG
// para que sea nitido a cualquier escala y no dependa de ningun asset generado.
// ============================================================================
const Stage = ({ camera, accent, set }) => {
  const frame = useCurrentFrame();
  const par = parallaxDepth(camera, frame, 0.10); // capa MAS lejana
  // respiracion muy lenta del suelo: sin esto el set se lee digital y muerto
  const horizon = 1180 + Math.sin(frame / 110) * 6;

  // Escenario GENERADO (kx_assets.py): cacheado por clave semantica y compartido
  // entre videos, asi que sigue siendo "un set fijo" -- solo que ahora el set
  // corresponde a lo que se narra (bolsa, fabrica, casa de empeno) en vez del
  // papel crema vacio. El personaje se compone aparte, encima.
  if (set) {
    return (
      <AbsoluteFill style={{ background: KX_CREAM, overflow: "hidden" }}>
        <AbsoluteFill style={{ scale: `${1.06 * par.sc}`, translate: `${par.tx}px ${par.ty}px` }}>
          <Img src={staticFile(set)}
               style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
        {/* halo de foco en el acento, igual que en el set dibujado: es lo que
            despega al personaje del fondo cuando el fondo tiene detalle */}
        <AbsoluteFill style={{
          background: `radial-gradient(ellipse 46% 26% at 50% ${(horizon - 210) / 19.2}%, ${accent}2E, transparent 70%)`,
        }} />
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ background: KX_CREAM, overflow: "hidden" }}>
      <AbsoluteFill style={{ scale: `${1.06 * par.sc}`, translate: `${par.tx}px ${par.ty}px` }}>
        <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          {/* pared / fondo */}
          <rect x="0" y="0" width="1080" height="1920" fill={KX_CREAM} />
          {/* suelo sugerido con una sola linea gruesa entintada */}
          <rect x="0" y={horizon} width="1080" height={1920 - horizon} fill={KX_CREAM_DEEP} opacity="0.55" />
          <path d={`M -20 ${horizon} L 1100 ${horizon - 8}`} stroke={KX_INK} strokeWidth="7"
                strokeLinecap="round" fill="none" opacity="0.85" />
          {/* halo de foco detras del personaje, en el acento de la escena */}
          <ellipse cx="540" cy={horizon - 210} rx="430" ry="360" fill={accent} opacity="0.12" />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ============================================================================
// GRADE + TEXTURA GLOBAL — se aplica ENCIMA de todo (regla 2). Es lo que unifica
// imagenes generadas en llamadas distintas: sin esto cada escena trae su propio
// blanco y el video parece un collage de fuentes ajenas.
// ============================================================================
const FilmGrade = () => {
  const frame = useCurrentFrame();
  // parpadeo de proyector de la era: MUY sutil, 1-2% o se vuelve mareante
  const flicker = 0.975 + Math.sin(frame * 1.9) * 0.012 + Math.sin(frame * 0.7) * 0.008;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* unificador de color: gris neutro en multiply, NO crema -- el tinte
          calido es lo que lee "sepia" en vez de "TV vieja" (3 ago 2026,
          pedido explicito: mas B&N que sepia). El resto del desature real
          lo hace OldTV mas abajo, en el nivel de pantalla. */}
      <AbsoluteFill style={{ background: "#CFCDC4", mixBlendMode: "multiply", opacity: 0.14 }} />
      {/* viñeta entintada */}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 52%, rgba(20,20,20,0.42) 100%)" }} />
      {/* parpadeo de proyector */}
      <AbsoluteFill style={{ background: "#000", opacity: (1 - flicker) * 0.9 }} />
    </AbsoluteFill>
  );
};

// grano de pelicula procedural (sin asset externo)
const Grain = ({ amount = 0.06 }) => {
  const frame = useCurrentFrame();
  const seed = frame % 7; // 7 patrones que rotan -> "hervor" de grano real
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "overlay", opacity: amount }}>
      <svg width="100%" height="100%">
        <filter id={`kxgrain${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed={seed} />
        </filter>
        <rect width="100%" height="100%" filter={`url(#kxgrain${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

// ============================================================================
// PERSONAJE — recorte con squash-stretch atado a las silabas (regla 5).
// depth alto = capa cercana, se mueve y crece mas que el set.
// ============================================================================
const Character = ({ src, from, camera, words = [], flip = false }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  const par = parallaxDepth(camera, frame, 1.0);

  // entrada: sube desde abajo con overshoot, 10 frames. Corta, nunca lenta.
  const enter = pop(local, 10);

  // squash-stretch sobre la silaba hablada: se busca la palabra viva y se
  // deforma en su ataque. Esto es lo que hace que el personaje "hable" sin rig.
  let sq = 1, st = 1;
  for (const wd of words) {
    const wl = frame - wd.t;
    if (wl >= 0 && wl < 6) {
      const k = interpolate(wl, [0, 2, 6], [0, 1, 0], { extrapolateRight: "clamp", easing: POP_EASE });
      sq = 1 - 0.045 * k;   // se aplasta en X
      st = 1 + 0.055 * k;   // se estira en Y
      break;
    }
  }
  // balanceo de vida constante (nunca una pose totalmente quieta)
  const sway = Math.sin(frame / 26) * 1.1;
  const bob = Math.sin(frame / 19) * 7;

  return (
    <AbsoluteFill style={{ translate: `${par.tx}px ${par.ty}px`, scale: `${par.sc}` }}>
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 470 }}>
        <Img
          src={src}
          style={{
            width: 820,
            objectFit: "contain",
            transform: `translateY(${(1 - enter) * 260 + bob}px) rotate(${sway}deg) scaleX(${(flip ? -1 : 1) * sq}) scaleY(${st})`,
            transformOrigin: "bottom center",
            opacity: enter,
            // B&N FORZADO (regla 2): el modelo de imagen devuelve color por mucho
            // que el prompt pida blanco y negro (el primer render salio marron
            // entero). El unico color del cuadro debe ser el acento del villano,
            // asi que la desaturacion se impone aqui, no se le pide a la IA.
            filter: "grayscale(1) contrast(1.15) drop-shadow(10px 16px 0 rgba(20,20,20,0.28))",
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// escena sin personaje (los INSERT infograficos): la imagen se clava como
// lamina sobre el mismo set, con margen -- nunca a sangre, o rompe el mundo.
const Plate = ({ src, from, camera }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  const par = parallaxDepth(camera, frame, 0.7);
  const enter = pop(local, 8);
  return (
    <AbsoluteFill style={{ translate: `${par.tx}px ${par.ty}px`, scale: `${par.sc}` }}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{
          width: 880, height: 880, background: "#FFF", border: `8px solid ${KX_INK}`,
          transform: `scale(${enter}) rotate(-1.2deg)`, overflow: "hidden",
          boxShadow: "14px 18px 0 rgba(20,20,20,0.25)",
        }}>
          <Img src={src} style={{ width: "100%", height: "100%", objectFit: "cover",
                                   filter: "grayscale(1) contrast(1.12)" }} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ============================================================================
// DATA ANNOTATION — grafico/flecha/circulo dibujado a mano sobre el cuadro
// cuando Tadeo dice una cifra. El trazo se revela progresivo (strokeDashoffset
// animado con la misma easing de pop() que ya usa Character/Plate) en vez de
// aparecer completo de golpe, que es lo que lo distingue de un sticker estatico.
// Nunca introduce un color nuevo: siempre el acento de la escena.
// ============================================================================
const DataAnnotation = ({ variant, from = 0, dur = 22, accent }) => {
  const frame = useCurrentFrame();
  const local = frame - from;
  if (local < 0 || local > dur + 20) return null;
  const draw = interpolate(local, [0, dur], [0, 1], { extrapolateRight: "clamp", easing: POP_EASE });
  const fade = interpolate(local, [dur + 10, dur + 20], [1, 0], { extrapolateLeft: "clamp" });
  const common = { fill: "none", stroke: accent, strokeLinecap: "round", strokeLinejoin: "round" };

  if (variant === "chartUp" || variant === "chartDown") {
    // sube = la codicia del villano crece; baja = lo que pierde la victima.
    const pts = variant === "chartUp"
      ? "60,180 240,120 420,150 600,40 780,70"
      : "60,40 240,90 420,60 600,170 780,140";
    const len = 900;
    return (
      <AbsoluteFill style={{ pointerEvents: "none", opacity: fade }}>
        <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          <polyline {...common} points={pts} strokeWidth="9" transform="translate(150, 220)"
                    strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />
        </svg>
      </AbsoluteFill>
    );
  }

  if (variant === "arrow") {
    const len = 260;
    return (
      <AbsoluteFill style={{ pointerEvents: "none", opacity: fade }}>
        <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          <path {...common} d="M 260 340 Q 420 280 560 420" strokeWidth="9"
                strokeDasharray={len} strokeDashoffset={len * (1 - draw)} />
          <polygon points="560,420 535,398 545,442" fill={accent} opacity={draw} />
        </svg>
      </AbsoluteFill>
    );
  }

  // circle: rodea una cifra (el Plate infografico) para enfasis
  const r = 130;
  const c = 2 * Math.PI * r;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: fade }}>
      <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
        <circle {...common} cx="540" cy="960" r={r} strokeWidth="9"
                strokeDasharray={c} strokeDashoffset={c * (1 - draw)}
                transform="rotate(-90 540 960)" />
      </svg>
    </AbsoluteFill>
  );
};

// ============================================================================
// TRANSICIONES rubber-hose (regla 4): iris, barrido de tinta, match-cut blanco.
// Duras y cortas. Nada de fundidos.
// ============================================================================
const KX_TRANSITIONS = ["iris", "inkSweep", "flashCut"];

const Transition = ({ at, variant, dur = 12 }) => {
  const frame = useCurrentFrame();
  const local = frame - at;
  if (local < 0 || local > dur) return null;
  const t = interpolate(local, [0, dur], [0, 1]);

  if (variant === "iris") {
    // iris clasico: cierra y abre sobre el corte
    const r = local < dur / 2
      ? interpolate(local, [0, dur / 2], [80, 0], { easing: Easing.in(Easing.quad) })
      : interpolate(local, [dur / 2, dur], [0, 80], { easing: Easing.out(Easing.quad) });
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <svg width="100%" height="100%">
          <defs>
            <mask id="kxiris">
              <rect width="100%" height="100%" fill="#fff" />
              <circle cx="540" cy="900" r={`${r}%`} fill="#000" />
            </mask>
          </defs>
          <rect width="100%" height="100%" fill={KX_INK} mask="url(#kxiris)" />
        </svg>
      </AbsoluteFill>
    );
  }

  if (variant === "inkSweep") {
    const pos = interpolate(t, [0, 1], [-30, 130]);
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{
          background: `linear-gradient(100deg, transparent ${pos - 30}%, ${KX_INK} ${pos - 8}%, ${KX_INK} ${pos + 8}%, transparent ${pos + 30}%)`,
        }} />
      </AbsoluteFill>
    );
  }

  // flashCut: golpe blanco de 1 frame util, el corte mas seco del catalogo
  const o = interpolate(local, [0, 2, dur], [0, 0.92, 0], { extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ background: "#FFF", opacity: o, pointerEvents: "none" }} />;
};

// ============================================================================
// CAPTIONS — ancladas SIEMPRE en la misma zona (regla 3). Resaltado unicamente
// en el acento de la escena; el resto en tinta sobre una banda crema, que sobre
// un set claro se lee mejor que blanco con borde negro.
// ============================================================================
const CAPTION_Y = 1500;

const Captions = ({ words, scenes = [], endFrame = Infinity, openerCount = 0 }) => {
  const frame = useCurrentFrame();
  if (frame >= endFrame) return null;
  // acento de la escena que cubre este frame (las captions son globales, ver
  // el comentario en KorexVideo sobre por que no van dentro de un Sequence)
  const cur = scenes.find((s) => frame >= s.from && frame < s.from + s.dur);
  const accent = KX_ACCENTS[cur?.accent] || KX_ACCENTS.neutral;

  const chunks = [];
  let rest = words;
  if (openerCount > 0 && words.length > openerCount) {
    chunks.push(words.slice(0, openerCount));
    rest = words.slice(openerCount);
  }
  let buf = [];
  for (const wd of rest) {
    buf.push(wd);
    if (buf.length >= 3 || buf.map((b) => b.w).join(" ").length >= 18) {
      chunks.push(buf);
      buf = [];
    }
  }
  if (buf.length) chunks.push(buf);

  const hasOpener = openerCount > 0 && words.length > openerCount;
  let chunk = null, next = null;
  for (let i = 0; i < chunks.length; i++) {
    const startsAt = hasOpener && i === 0 ? 0 : chunks[i][0].t;
    if (frame >= startsAt) { chunk = chunks[i]; next = chunks[i + 1] || null; }
  }
  if (!chunk) return null;
  if (next && frame >= next[0].t) return null;

  const activeIdx = chunk.reduce((acc, wd, i) => (frame >= wd.t ? i : acc), 0);
  const isOpener = hasOpener && chunk === chunks[0];

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{
        position: "absolute", left: 0, right: 0, top: CAPTION_Y,
        display: "flex", flexWrap: "wrap", justifyContent: "center",
        gap: "6px 14px", padding: "0 70px",
      }}>
        {chunk.map((wd, i) => {
          if (!isOpener && frame < wd.t) return null;
          const p = isOpener ? 1 : pop(frame - wd.t, 5);
          const isActive = i === activeIdx;
          return (
            <span key={i} style={{
              fontFamily: "Arial Black, sans-serif", fontWeight: 900,
              fontSize: isOpener ? 66 : (isActive ? 84 : 70),
              color: isActive ? accent : KX_INK,
              background: isActive ? "transparent" : "transparent",
              scale: `${p}`, display: "inline-block", letterSpacing: "-0.5px",
              textShadow: `3px 3px 0 ${KX_CREAM}, -2px -2px 0 ${KX_CREAM}, 2px -2px 0 ${KX_CREAM}, -2px 2px 0 ${KX_CREAM}`,
            }}>
              {wd.w.toUpperCase()}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// promesa legible desde el frame 0 (misma regla que Archivo Vivo: la decision
// de quedarse se toma antes del segundo 1 y hace falta algo entero que leer)
const Hook = ({ text, dur = 46 }) => {
  const frame = useCurrentFrame();
  if (!text || frame > dur) return null;
  const o = interpolate(frame, [0, 4, dur - 8, dur], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: o }}>
      <div style={{
        position: "absolute", left: 60, right: 60, top: 250,
        fontFamily: "Arial Black, sans-serif", fontWeight: 900, fontSize: 78,
        lineHeight: 1.05, color: KX_INK, textAlign: "center",
        textShadow: `4px 4px 0 ${KX_CREAM}, -3px -3px 0 ${KX_CREAM}, 3px -3px 0 ${KX_CREAM}, -3px 3px 0 ${KX_CREAM}`,
      }}>
        {text.toUpperCase()}
      </div>
    </AbsoluteFill>
  );
};

// ============================================================================
// OLD TV — pedido explicito 3 ago 2026: "granulado y los colores mas tirando
// a blanco y negro que sepia". Vive en el nivel MAS externo (envuelve TODO,
// incluidos FilmGrade/Grain) porque es un filtro de PANTALLA, no de escena:
// un grayscale a mitad de camino desatura tambien el tinte calido de
// FilmGrade, y las scanlines/el roll tienen que verse sobre el grano y la
// vineta, no debajo. NO se lleva a grayscale(1) puro -- eso mataria el unico
// acento de color permitido por la regla 2 (el villano de la escena), y sin
// el acento el video pierde la unica pista de "quien es el malo ahora".
// ============================================================================
const OldTV = ({ children }) => {
  const frame = useCurrentFrame();
  // salto de tubo: rarisimo (1 de cada ~3.2s) y muy corto, para que se lea
  // como un artefacto de TV vieja y no como un tic nervioso de la camara.
  const cycle = frame % 97;
  const roll = cycle < 4
    ? interpolate(cycle, [0, 2, 4], [0, 5, 0], { easing: Easing.inOut(Easing.quad) })
    : 0;
  return (
    <div style={{
      width: "100%", height: "100%", position: "relative",
      filter: "grayscale(0.6) contrast(1.12) brightness(0.97)",
      transform: `translateY(${roll}px)`,
    }}>
      {children}
      {/* scanlines: lineas horizontales de 1px repetidas, muy sutiles */}
      <AbsoluteFill style={{
        pointerEvents: "none", mixBlendMode: "multiply", opacity: 0.5,
        backgroundImage: "repeating-linear-gradient(to bottom, rgba(0,0,0,0.18) 0px, rgba(0,0,0,0.18) 1px, transparent 2px, transparent 3px)",
      }} />
    </div>
  );
};

// ============================================================================
export const KorexVideo = ({ manifest }) => {
  const m = manifest;
  const scenes = m.scenes || [];
  const words = m.words || [];
  const endFrame = m.durationInFrames || FPS * 60;

  return (
    <OldTV>
    <AbsoluteFill style={{ background: KX_CREAM }}>
      {scenes.map((s, i) => {
        const accent = KX_ACCENTS[s.accent] || KX_ACCENTS.neutral;
        // camara: SOLO push-in lento (regla 5). Los beats de zoom-punch de
        // Archivo Vivo se dejan fuera a proposito.
        const camera = makeCamera([], []);
        const sceneWords = words.filter((w) => w.t >= s.from && w.t < s.from + s.dur);
        return (
          <Sequence key={i} from={s.from} durationInFrames={s.dur}>
            <Stage camera={camera} accent={accent} set={s.set} />
            {s.fg ? (
              <Character src={staticFile(s.fg)} from={0} camera={camera}
                          words={sceneWords.map((w) => ({ ...w, t: w.t - s.from }))}
                          flip={s.flip} />
            ) : s.bg ? (
              <Plate src={staticFile(s.bg)} from={0} camera={camera} />
            ) : null}
            {s.dataBeat ? (
              <DataAnnotation variant={s.dataBeat.type} from={s.dataBeat.from ?? 0}
                              dur={s.dataBeat.dur} accent={accent} />
            ) : null}
          </Sequence>
        );
      })}

      {/* transiciones sobre cada corte (no en el primero) */}
      {scenes.slice(1).map((s, i) => (
        <Transition key={`tr-${i}`} at={s.from} variant={KX_TRANSITIONS[i % KX_TRANSITIONS.length]} />
      ))}

      {/* CAPTIONS: una sola instancia GLOBAL, nunca una por escena.
          Bug real del primer render (3 ago 2026): estaban dentro de un
          <Sequence> por escena, y como Sequence reinicia el frame local a 0
          mientras las palabras traen timestamps GLOBALES, cada escena volvia a
          pintar la primera palabra del video -- se veia "TADEO" sobre la Bruja.
          El acento se resuelve mirando que escena cubre el frame actual. */}
      <Captions words={words} scenes={scenes} openerCount={m.openerWords || 0}
                endFrame={endFrame} />

      <Hook text={m.hook} />

      {/* grade + grano SIEMPRE al final: unifican todo lo de arriba */}
      <FilmGrade />
      <Grain />

      {/* SFX de corte, emparejado al caracter de cada transicion */}
      {scenes.slice(1).map((s, i) => {
        const v = KX_TRANSITIONS[i % KX_TRANSITIONS.length];
        const sfx = v === "iris" ? { src: "proof/whoosh.mp3", vol: 0.4 }
                  : v === "inkSweep" ? { src: "proof/paper.mp3", vol: 0.42 }
                  : { src: "proof/impact.mp3", vol: 0.38 };
        return (
          <Sequence key={`sfx-${i}`} from={s.from} durationInFrames={18}>
            <Audio src={staticFile(sfx.src)} volume={sfx.vol} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
    </OldTV>
  );
};
