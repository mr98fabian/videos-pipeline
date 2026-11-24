import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
  Easing,
  random,
} from "remotion";

// ============================================================================
// KOREX MOTION (nov 2026) — camino unico de produccion de KOREX.
// Reemplaza a Flow (imagenes por escena) y a Wan (animacion de la escena 0):
// el video es DATOS (manifest generado por korex_motion.py desde el guion)
// sobre una biblioteca fija de plantillas, con la misma direccion de arte en
// todos los videos. La version anterior de este motor (KorexVideo.jsx, 3 ago)
// usaba acentos de color por villano: el canal es estrictamente B/N, asi que
// esta composicion pasa TODO por grayscale(1) en la raiz -- cero color por
// construccion, no por disciplina.
//
// Plantillas: hook · tadeo · concept · hero · twist · close (+ overlay CTA).
// Capas permanentes: mundo con parallax 2.5D, karaoke, grano/vineta/parpadeo.
// ============================================================================

const W = 1080;
const H = 1920;
const INK = "#0c0c0c";
const PAPER = "#f2f2f2";
const GREY = "#8a8a8a";
const LINE = "#3a3a3a";
const DISPLAY = "'Arial Black', 'Arial Bold', Impact, sans-serif";
const CONDENSED = "Impact, 'Arial Black', sans-serif";

const OVERSHOOT = Easing.bezier(0.18, 1.6, 0.35, 1);
const SLAM = Easing.bezier(0.2, 0.9, 0.3, 1);
const SMOOTH = Easing.bezier(0.45, 0, 0.2, 1);

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };
const lerp = (f, a, b, x, y, ease = SMOOTH) =>
  interpolate(f, [a, b], [x, y], { ...clamp, easing: ease });

// ----------------------------------------------------------------------------
// Camara del mundo: cada corte de escena desplaza el mundo en X con un whip de
// 8 frames. Las capas lo siguen a velocidades distintas -> parallax 2.5D.
// ----------------------------------------------------------------------------
const WHIP = 8;
const worldX = (frame, scenes) => {
  let x = 0;
  for (let i = 1; i < scenes.length; i++) {
    const t = scenes[i].from;
    x += lerp(frame, t - WHIP / 2, t + WHIP / 2, 0, 640, SMOOTH);
  }
  return x;
};

const Grid = ({ offset, size, color, opacity }) => (
  <AbsoluteFill
    style={{
      opacity,
      backgroundImage: `linear-gradient(${color} 2px, transparent 2px), linear-gradient(90deg, ${color} 2px, transparent 2px)`,
      backgroundSize: `${size}px ${size}px`,
      backgroundPosition: `${-offset}px ${offset * 0.15}px`,
    }}
  />
);

// Doodles rubber-hose flotando en la capa media: estrellas, monedas, signos.
const Doodle = ({ kind, size }) => {
  const s = { stroke: "#5c5c5c", strokeWidth: 5, fill: "none", strokeLinecap: "round" };
  if (kind === 0)
    return (
      <svg width={size} height={size} viewBox="0 0 100 100">
        <path d="M50 8 L61 38 L93 40 L68 60 L77 92 L50 74 L23 92 L32 60 L7 40 L39 38 Z" {...s} />
      </svg>
    );
  if (kind === 1)
    return (
      <svg width={size} height={size} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="38" {...s} />
        <path d="M50 26 L50 74 M62 36 C56 30 38 30 38 42 C38 54 62 48 62 60 C62 72 42 72 36 64" {...s} />
      </svg>
    );
  return (
    <svg width={size} height={size} viewBox="0 0 100 100">
      <path d="M10 50 Q30 20 50 50 T90 50" {...s} />
    </svg>
  );
};

const World = ({ scenes }) => {
  const frame = useCurrentFrame();
  const x = worldX(frame, scenes);
  const drift = frame * 0.6;
  const doodles = Array.from({ length: 14 }, (_, i) => ({
    kind: i % 3,
    bx: random(`dx${i}`) * 2600,
    by: 120 + random(`dy${i}`) * 1650,
    size: 70 + random(`ds${i}`) * 90,
    rot: random(`dr${i}`) * 360,
  }));
  return (
    <AbsoluteFill style={{ background: INK }}>
      {/* lejos: plano de blueprint, 0.25x */}
      <Grid offset={x * 0.25 + drift * 0.3} size={120} color="#1c1c1c" opacity={1} />
      <Grid offset={x * 0.25 + drift * 0.3} size={30} color="#151515" opacity={0.8} />
      {/* medio: doodles, 0.6x */}
      {doodles.map((d, i) => {
        const px = (((d.bx - x * 0.6 - drift) % 2600) + 2600) % 2600 - 400;
        const bob = Math.sin((frame + i * 13) / 22) * 14;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: px,
              top: d.by + bob,
              opacity: 0.5,
              transform: `rotate(${d.rot + Math.sin((frame + i * 7) / 30) * 8}deg)`,
            }}
          >
            <Doodle kind={d.kind} size={d.size} />
          </div>
        );
      })}
      {/* piso: linea de horizonte, 1.0x */}
      <div
        style={{
          position: "absolute",
          left: -40,
          right: -40,
          top: 1300,
          height: 6,
          background: "#2a2a2a",
          transform: `translateX(${-(x % 200)}px)`,
        }}
      />
    </AbsoluteFill>
  );
};

// Lineas de velocidad durante el whip: la capa mas cercana (1.6x).
const WhipLines = ({ scenes }) => {
  const frame = useCurrentFrame();
  let strength = 0;
  for (let i = 1; i < scenes.length; i++) {
    const d = Math.abs(frame - scenes[i].from);
    if (d < WHIP / 2) strength = Math.max(strength, 1 - d / (WHIP / 2));
  }
  if (strength <= 0) return null;
  return (
    <AbsoluteFill style={{ opacity: strength * 0.85 }}>
      {Array.from({ length: 18 }, (_, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            top: random(`wl${i}`) * H,
            left: random(`wx${i}${Math.floor(frame / 2)}`) * W - 300,
            width: 300 + random(`ww${i}`) * 600,
            height: 4 + random(`wh${i}`) * 8,
            background: "#d8d8d8",
            borderRadius: 4,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------------------
// Tadeo vivo: una pose recortada (PNG con alfa de kx_cast) animada por codigo.
// Entrada con squash & stretch, balanceo continuo, respiracion de goma,
// "parpadeo" de squash cada ~2.5 s y desplazamientos con easing.
// Nada generativo: no hay forma de que se deforme en otra cosa.
// ----------------------------------------------------------------------------
const RubberTadeo = ({ src, x = 540, base = 1300, h = 860, local, enter = true, flip = false, energy = 1, seed = 0 }) => {
  if (!src) return null;
  const w = h * 0.558;
  const inT = enter ? local : 99;
  const rise = enter ? lerp(inT, 0, 9, 320, 0, SLAM) : 0;
  // squash al aterrizar (f 7-10), stretch de rebote (f 10-14), asentado
  const sq = enter
    ? interpolate(inT, [0, 6, 9, 13, 18], [1.18, 1.1, 0.8, 1.08, 1], { ...clamp })
    : 1;
  const bob = Math.sin((local + seed * 17) / 7) * 9 * energy;
  const sway = Math.sin((local + seed * 11) / 13) * 2.6 * energy;
  const breath = 1 + Math.sin((local + seed * 5) / 5) * 0.018 * energy;
  const blinkPhase = (local + seed * 23) % 75;
  const blink = blinkPhase < 3 ? 0.965 : 1;
  const sy = sq * breath * blink;
  const sx = (1 / sq) * (2 - breath);
  return (
    <div
      style={{
        position: "absolute",
        left: x - w / 2,
        top: base - h + rise + bob,
        width: w,
        height: h,
        transformOrigin: "50% 100%",
        transform: `rotate(${sway}deg) scale(${flip ? -sx : sx}, ${sy})`,
      }}
    >
      {/* sombra de contacto, sigue el rebote */}
      <div
        style={{
          position: "absolute",
          left: w * 0.15,
          bottom: -18 - bob,
          width: w * 0.7,
          height: 30,
          borderRadius: "50%",
          background: "rgba(0,0,0,0.55)",
          filter: "blur(6px)",
          transform: `scaleX(${1 - bob / 90})`,
        }}
      />
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
    </div>
  );
};

// Camara local de escena: push-in lento + golpe opcional.
const SceneCam = ({ local, dur, punch = 0, children }) => {
  const push = lerp(local, 0, dur, 1.0, 1.06, Easing.linear);
  const hit = punch ? interpolate(local, [0, 3, 10], [1 + punch, 1 + punch * 0.4, 1], clamp) : 1;
  const shake = punch && local < 8 ? (random(`sh${local}`) - 0.5) * 18 * punch * 5 : 0;
  return (
    <AbsoluteFill style={{ transform: `translate(${shake}px, ${shake * 0.6}px) scale(${push * hit})` }}>
      {children}
    </AbsoluteFill>
  );
};

const Title = ({ text, local, top = 180, size = 104, stagger = 2 }) => {
  const words = text.split(" ");
  return (
    <div
      style={{
        position: "absolute",
        top,
        left: 60,
        right: 60,
        textAlign: "center",
        fontFamily: DISPLAY,
        fontSize: size,
        lineHeight: 1.02,
        color: PAPER,
        textTransform: "uppercase",
        WebkitTextStroke: "3px #000",
        textShadow: "0 8px 0 #000",
      }}
    >
      {words.map((w, i) => {
        const t = local - i * stagger;
        const s = interpolate(t, [-1, 0, 5], [1, 1.25, 1], { ...clamp, easing: OVERSHOOT });
        return (
          <span key={i} style={{ display: "inline-block", margin: "0 12px", transform: `scale(${s})` }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

// --- plantilla HOOK ---------------------------------------------------------
// Texto completo de la promesa visible desde el frame 0 (la decision de
// quedarse pasa antes del segundo 1) y Tadeo ya moviendose en el frame 1.
const HookScene = ({ scene, local, hook, frozen = false }) => {
  const f = frozen ? 0 : local;
  return (
    <SceneCam local={f} dur={scene.dur}>
      <Title text={hook || ""} local={f + 6} top={170} size={100} stagger={0} />
      <RubberTadeo src={scene.pose} local={f + 20} enter={false} h={900} seed={1} energy={1.3} />
    </SceneCam>
  );
};

// --- plantilla TADEO (escena de personaje) -----------------------------------
const TadeoScene = ({ scene, local }) => (
  <SceneCam local={local} dur={scene.dur} punch={scene.beat ? 0.06 : 0}>
    <RubberTadeo src={scene.pose} local={local} h={scene.pose && scene.pose.includes("bruja") ? 960 : 880} seed={scene.i} flip={scene.i % 2 === 1} />
    {scene.keyword ? <Keyword text={scene.keyword} local={local} /> : null}
  </SceneCam>
);

const Keyword = ({ text, local }) => {
  const s = lerp(local, 4, 12, 0, 1, OVERSHOOT);
  return (
    <div
      style={{
        position: "absolute",
        top: 250,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        transform: `scale(${s}) rotate(-3deg)`,
      }}
    >
      <div
        style={{
          background: PAPER,
          color: INK,
          fontFamily: CONDENSED,
          fontSize: 92,
          padding: "6px 36px",
          border: "6px solid #000",
          boxShadow: "10px 10px 0 #000",
          textTransform: "uppercase",
        }}
      >
        {text}
      </div>
    </div>
  );
};

// --- plantilla CONCEPTO: grafico blueprint, UN elemento resaltado ------------
const draw = (local, from, len) => lerp(local, from, from + len, 1, 0, SMOOTH);

const Glyph = ({ c, local }) => {
  const stroke = { stroke: "#9c9c9c", strokeWidth: 8, fill: "none", strokeLinecap: "round", strokeLinejoin: "round" };
  const hi = { stroke: PAPER, strokeWidth: 12, fill: "none", strokeLinecap: "round", strokeLinejoin: "round" };
  const pulse = 1 + Math.sin(local / 4) * 0.06;
  const type = c.type || "line";
  if (type === "bars") {
    const vals = c.values || [3, 6, 2, 8, 4];
    const hiIdx = c.highlight ?? vals.indexOf(Math.max(...vals));
    const order = c.reorder ? [...vals.keys()].sort((a, b) => vals[b] - vals[a]) : [...vals.keys()];
    const t = c.reorder ? lerp(local, 14, 30, 0, 1, OVERSHOOT) : 0;
    return (
      <svg width={900} height={700} viewBox="0 0 900 700">
        <line x1="40" y1="640" x2="860" y2="640" {...stroke} />
        {vals.map((v, i) => {
          const slot0 = i;
          const slot1 = order.indexOf(i);
          const slot = slot0 + (slot1 - slot0) * t;
          const hgt = v * 66 * lerp(local, 2 + i * 2, 12 + i * 2, 0, 1, OVERSHOOT);
          const isHi = i === hiIdx;
          return (
            <rect
              key={i}
              x={80 + slot * 160}
              y={640 - hgt}
              width={110}
              height={hgt}
              fill={isHi ? PAPER : "#4a4a4a"}
              stroke="#000"
              strokeWidth={6}
            />
          );
        })}
      </svg>
    );
  }
  if (type === "toggle") {
    const on = lerp(local, 16, 24, 0, 1, OVERSHOOT);
    return (
      <svg width={900} height={700} viewBox="0 0 900 700">
        <rect x="170" y="230" width="560" height="240" rx="120" {...stroke} strokeDasharray="1800" strokeDashoffset={1800 * draw(local, 0, 12)} />
        <circle cx={290 + on * 320} cy="350" r="92" fill={on > 0.5 ? PAPER : "#4a4a4a"} stroke="#000" strokeWidth="8" />
        <text x="450" y="600" textAnchor="middle" fontFamily={CONDENSED} fontSize="110" fill={on > 0.5 ? PAPER : GREY}>
          {on > 0.5 ? (c.on || "ON") : (c.off || "OFF")}
        </text>
      </svg>
    );
  }
  if (type === "doc") {
    const r = lerp(local, 18, 32, 0, 1, SMOOTH);
    return (
      <svg width={900} height={760} viewBox="0 0 900 760">
        <rect x="210" y="40" width="480" height="640" {...stroke} strokeDasharray="2300" strokeDashoffset={2300 * draw(local, 0, 12)} />
        {[0, 1, 2, 3, 4, 5].map((k) => (
          <line key={k} x1="260" y1={130 + k * 70} x2={620 - (k % 2) * 80} y2={130 + k * 70} stroke="#5a5a5a" strokeWidth="8" strokeDasharray="400" strokeDashoffset={400 * draw(local, 4 + k * 2, 8)} />
        ))}
        <path d="M480 600 q20 -30 40 0 t40 0 t40 -10" {...hi} />
        <circle cx="540" cy="600" r={110 * pulse} {...hi} strokeDasharray="700" strokeDashoffset={700 * (1 - r)} />
      </svg>
    );
  }
  if (type === "check") {
    const rows = c.rows || 4;
    return (
      <svg width={900} height={720} viewBox="0 0 900 720">
        {Array.from({ length: rows }, (_, k) => {
          const y = 80 + k * 160;
          const isHi = k === (c.highlight ?? rows - 1);
          return (
            <g key={k}>
              <rect x="120" y={y} width="110" height="110" {...(isHi ? hi : stroke)} />
              <path d={`M140 ${y + 55} l30 30 l50 -70`} {...(isHi ? hi : stroke)} strokeDasharray="200" strokeDashoffset={200 * draw(local, 6 + k * 6, 6)} />
              <line x1="280" y1={y + 55} x2={isHi ? 780 : 680} y2={y + 55} stroke={isHi ? PAPER : "#5a5a5a"} strokeWidth="14" strokeLinecap="round" />
            </g>
          );
        })}
      </svg>
    );
  }
  // "line": serie que sube (o baja con c.down) y un punto resaltado al final
  const pts = c.down ? [[60, 160], [220, 220], [380, 200], [540, 380], [700, 420], [840, 600]] : [[60, 600], [220, 540], [380, 560], [540, 380], [700, 330], [840, 120]];
  const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
  const last = pts[pts.length - 1];
  const dot = lerp(local, 20, 26, 0, 1, OVERSHOOT);
  return (
    <svg width={900} height={700} viewBox="0 0 900 700">
      <line x1="40" y1="660" x2="880" y2="660" stroke="#4a4a4a" strokeWidth="6" />
      <line x1="40" y1="40" x2="40" y2="660" stroke="#4a4a4a" strokeWidth="6" />
      <path d={d} {...stroke} strokeDasharray="1600" strokeDashoffset={1600 * draw(local, 0, 22)} />
      <circle cx={last[0]} cy={last[1]} r={34 * dot * pulse} fill={PAPER} stroke="#000" strokeWidth="6" />
    </svg>
  );
};

const ConceptScene = ({ scene, local, sidekick }) => {
  const c = scene.concept || {};
  const lab = lerp(local, 8, 16, 0, 1, OVERSHOOT);
  return (
    <SceneCam local={local} dur={scene.dur}>
      <div style={{ position: "absolute", top: 330, left: 90, width: 900, display: "flex", justifyContent: "center" }}>
        <Glyph c={c} local={local} />
      </div>
      {c.label ? (
        <div
          style={{
            position: "absolute",
            top: 130,
            left: 50,
            right: 50,
            textAlign: "center",
            fontFamily: DISPLAY,
            fontSize: 76,
            color: PAPER,
            textTransform: "uppercase",
            transform: `scale(${lab})`,
            WebkitTextStroke: "2px #000",
            textShadow: "0 6px 0 #000",
          }}
        >
          {c.label}
        </div>
      ) : null}
      {/* Tadeo sigue vivo en la esquina, mirando el grafico */}
      <RubberTadeo src={sidekick} x={930} base={1330} h={330} local={local} seed={scene.i} flip energy={1.4} />
    </SceneCam>
  );
};

// --- plantilla NUMERO HEROE --------------------------------------------------
const HeroScene = ({ scene, local, sidekick }) => {
  const hero = scene.hero || {};
  const raw = String(hero.text || "");
  const num = parseFloat(raw.replace(/[^0-9.]/g, ""));
  const count = isNaN(num) ? null : Math.round(lerp(local, 0, 14, 0, num, Easing.out(Easing.cubic)));
  const shown = count === null ? raw : raw.replace(/[0-9][0-9,.]*/, count.toLocaleString("en-US"));
  const s = interpolate(local, [0, 6, 12], [2.6, 0.92, 1], { ...clamp, easing: OVERSHOOT });
  const flash = interpolate(local, [0, 4], [1, 0], clamp);
  const size = raw.length <= 3 ? 400 : raw.length <= 5 ? 330 : 250;
  return (
    <SceneCam local={local} dur={scene.dur} punch={0.08}>
      {hero.label_top ? (
        <div style={{ position: "absolute", top: 330, left: 0, right: 0, textAlign: "center", fontFamily: DISPLAY, fontSize: 70, color: GREY, textTransform: "uppercase" }}>
          {hero.label_top}
        </div>
      ) : null}
      <div
        style={{
          position: "absolute",
          top: 430,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: CONDENSED,
          fontSize: size,
          lineHeight: 1,
          color: PAPER,
          transform: `scale(${s})`,
          WebkitTextStroke: "6px #000",
          textShadow: "0 16px 0 #000, 0 0 60px rgba(255,255,255,0.25)",
        }}
      >
        {shown}
      </div>
      {hero.label ? (
        <div style={{ position: "absolute", top: 430 + size + 30, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ background: PAPER, color: INK, fontFamily: DISPLAY, fontSize: 64, padding: "4px 28px", border: "6px solid #000", textTransform: "uppercase", transform: `rotate(-2deg) scale(${lerp(local, 8, 14, 0, 1, OVERSHOOT)})` }}>
            {hero.label}
          </div>
        </div>
      ) : null}
      <RubberTadeo src={sidekick} x={830} base={1320} h={440} local={local + 4} seed={scene.i} flip energy={1.6} />
      <AbsoluteFill style={{ background: "#fff", opacity: flash * 0.9 }} />
    </SceneCam>
  );
};

// --- plantilla GIRO ---------------------------------------------------------
// El acento visual mas fuerte del video: inversion a blanco, golpe de camara,
// la frase del giro en barras invertidas y el personaje entrando con stretch.
const TwistScene = ({ scene, local, twist }) => {
  const inv = local < 5;
  const spot = lerp(local, 0, 10, 0, 1, SMOOTH);
  const words = (twist || "").split(" ");
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: spot,
          background: "radial-gradient(circle at 50% 62%, rgba(255,255,255,0.16) 0%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.75) 80%)",
        }}
      />
      <SceneCam local={local} dur={scene.dur} punch={0.14}>
        <RubberTadeo src={scene.pose} local={local} h={980} seed={scene.i} energy={1.5} />
        <div style={{ position: "absolute", top: 150, left: 50, right: 50, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 14 }}>
          {words.map((w, i) => {
            const t = local - 3 - i * 3;
            const s = interpolate(t, [0, 4], [0, 1], { ...clamp, easing: OVERSHOOT });
            return (
              <span
                key={i}
                style={{
                  background: PAPER,
                  color: INK,
                  fontFamily: CONDENSED,
                  fontSize: 104,
                  lineHeight: 1.05,
                  padding: "0 18px",
                  border: "6px solid #000",
                  boxShadow: "8px 8px 0 #000",
                  textTransform: "uppercase",
                  transform: `scale(${s}) rotate(${(i % 2 ? 2 : -2)}deg)`,
                }}
              >
                {w}
              </span>
            );
          })}
        </div>
      </SceneCam>
      {inv ? <AbsoluteFill style={{ mixBlendMode: "difference", background: "#fff" }} /> : null}
    </AbsoluteFill>
  );
};

// --- plantilla CIERRE EN BUCLE ----------------------------------------------
// Escena de personaje normal que en sus ultimos LOOP frames se funde con el
// frame 0 del hook: al reiniciar el Short no hay costura.
const LOOP = 14;
const CloseScene = ({ scene, local, first, hook }) => {
  const m = lerp(local, scene.dur - LOOP, scene.dur, 0, 1, SMOOTH);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: 1 - m }}>
        <TadeoScene scene={scene} local={local} />
      </AbsoluteFill>
      <AbsoluteFill style={{ opacity: m }}>
        <HookScene scene={first} local={0} hook={hook} frozen />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// --- overlay CTA (a mitad de video, nunca narrado) --------------------------
const CTA = ({ cta }) => {
  const frame = useCurrentFrame();
  const local = frame - cta.from;
  if (local < 0 || local > cta.dur) return null;
  const inS = lerp(local, 0, 8, 0, 1, OVERSHOOT);
  const out = lerp(local, cta.dur - 6, cta.dur, 0, 1, SMOOTH);
  const lines = String(cta.text || "").split("|");
  return (
    <div
      style={{
        position: "absolute",
        top: 1090,
        left: 0,
        right: 120,
        display: "flex",
        justifyContent: "center",
        transform: `translateX(${out * 1100}px) scale(${inS}) rotate(-3deg)`,
      }}
    >
      <div style={{ background: PAPER, border: "8px solid #000", boxShadow: "14px 14px 0 #000", padding: "14px 40px", textAlign: "center" }}>
        {lines.map((l, i) => (
          <div key={i} style={{ fontFamily: i ? CONDENSED : DISPLAY, fontSize: i ? 96 : 52, color: INK, textTransform: "uppercase", lineHeight: 1.05 }}>
            {l}
          </div>
        ))}
      </div>
    </div>
  );
};

// --- karaoke palabra por palabra (dentro de la composicion) ------------------
const Captions = ({ groups }) => {
  const frame = useCurrentFrame();
  const g = groups.find((x) => frame >= x.from && frame < x.to);
  if (!g) return null;
  const local = frame - g.from;
  const s = interpolate(local, [0, 3], [0.9, 1], { ...clamp, easing: OVERSHOOT });
  return (
    <div style={{ position: "absolute", top: 1360, left: 50, right: 50, textAlign: "center", transform: `scale(${s})` }}>
      {g.words.map((w, i) => {
        const active = frame >= w.s && frame < w.e + 2;
        const said = frame >= w.s;
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              margin: "0 10px",
              fontFamily: DISPLAY,
              fontSize: active ? 84 : 78,
              color: said ? PAPER : "#7a7a7a",
              WebkitTextStroke: "4px #000",
              paintOrder: "stroke fill",
              textShadow: "0 6px 0 #000",
              textTransform: "uppercase",
              transform: active ? "translateY(-6px)" : "none",
            }}
          >
            {w.w}
          </span>
        );
      })}
    </div>
  );
};

// --- pelicula: grano, vineta y parpadeo (encima de todo) ---------------------
const FilmFX = () => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={W} height={H} style={{ position: "absolute", opacity: 0.13, mixBlendMode: "overlay" }}>
        <filter id={`g${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed} />
        </filter>
        <rect width={W} height={H} filter={`url(#g${seed})`} />
      </svg>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)" }} />
      {random(`sc${seed}`) < 0.12 ? (
        <div style={{ position: "absolute", top: 0, bottom: 0, left: random(`sx${seed}`) * W, width: 2, background: "rgba(255,255,255,0.18)" }} />
      ) : null}
    </AbsoluteFill>
  );
};

const SceneSwitch = ({ scene, manifest, sidekick }) => {
  const frame = useCurrentFrame();
  const local = frame;
  const { hook, twist, scenes } = manifest;
  if (scene.kind === "hook") return <HookScene scene={scene} local={local} hook={hook} />;
  if (scene.kind === "twist") return <TwistScene scene={scene} local={local} twist={twist} />;
  if (scene.kind === "hero") return <HeroScene scene={scene} local={local} sidekick={sidekick} />;
  if (scene.kind === "concept") return <ConceptScene scene={scene} local={local} sidekick={sidekick} />;
  if (scene.kind === "close") return <CloseScene scene={scene} local={local} first={scenes[0]} hook={hook} />;
  return <TadeoScene scene={scene} local={local} />;
};

export const KorexMotion = ({ manifest }) => {
  const frame = useCurrentFrame();
  const flicker = 0.97 + random(`fl${Math.floor(frame / 2)}`) * 0.05;
  const scenes = manifest.scenes || [];
  return (
    <AbsoluteFill style={{ background: INK, filter: `grayscale(1) contrast(1.06) brightness(${flicker})` }}>
      <World scenes={scenes} />
      {scenes.map((sc) => (
        <Sequence key={sc.i} from={sc.from} durationInFrames={sc.dur}>
          <SceneSwitch scene={sc} manifest={manifest} sidekick={sc.sidekick} />
        </Sequence>
      ))}
      <WhipLines scenes={scenes} />
      {manifest.cta ? <CTA cta={manifest.cta} /> : null}
      <Captions groups={manifest.captions || []} />
      <FilmFX />
    </AbsoluteFill>
  );
};
