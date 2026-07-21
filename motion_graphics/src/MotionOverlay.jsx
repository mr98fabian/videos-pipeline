import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

// Paleta consistente con el estilo sepia vintage-toon del canal (ver
// estilo-historias-hiddenfacts.md): dorado #E8C468, rojo acento #C0392B,
// contorno negro grueso -- nada de colores modernos saturados.
const GOLD = "#E8C468";
const RED = "#C0392B";
const INK = "#1a1208";

function BouncyIcon({ emoji, popFrame, x, y, size = 220 }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - popFrame;
  if (local < 0) return null;

  // spring() con overshoot -- exactamente la curva "elastic/back-ease-out"
  // que se ve en los 4 videos de referencia (rebote de icono al aparecer).
  const scale = spring({
    frame: local,
    fps,
    config: { damping: 9, stiffness: 140, mass: 0.6 },
  });

  // pequeno balanceo continuo tras el rebote inicial, sutil (no "elaborate
  // animation" -- ver investigacion: la elaboracion excesiva rinde peor).
  const wiggle = local > 15 ? Math.sin((local - 15) / 8) * 4 : 0;

  return (
    <div
      style={{
        position: "absolute",
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
        transform: `scale(${scale}) rotate(${wiggle}deg)`,
        transformOrigin: "center center",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.62,
        filter: `drop-shadow(4px 4px 0px ${INK})`,
      }}
    >
      {emoji}
    </div>
  );
}

function KineticKeyword({ text, popFrame, y }) {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const local = frame - popFrame;
  if (local < 0) return null;

  const scale = spring({
    frame: local,
    fps,
    config: { damping: 10, stiffness: 160, mass: 0.5 },
  });
  const opacity = interpolate(local, [0, 6], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: y,
        width,
        textAlign: "center",
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: "center center",
      }}
    >
      <span
        style={{
          fontFamily: "Arial Black, Arial, sans-serif",
          fontWeight: 900,
          fontSize: 88,
          color: GOLD,
          WebkitTextStroke: `6px ${INK}`,
          paintOrder: "stroke fill",
          textShadow: `6px 6px 0px ${INK}`,
        }}
      >
        {text}
      </span>
    </div>
  );
}

export function MotionOverlay({ keyword, iconEmoji, popFrame }) {
  const { width, height } = useVideoConfig();
  return (
    <div style={{ width, height, position: "relative" }}>
      <BouncyIcon emoji={iconEmoji} popFrame={popFrame} x={width / 2} y={height * 0.32} />
      <KineticKeyword text={keyword} popFrame={popFrame + 6} y={height * 0.44} />
    </div>
  );
}
