import { useCurrentFrame, useVideoConfig, spring, interpolate, staticFile, Img, AbsoluteFill } from "remotion";

// Escena de collage con FOTO REAL recortada -- estilo "recorte de periodico"
// pedido por el usuario 21 jul 2026 (referencia: collage de jugador de futbol
// con stickers/flechas). A diferencia de AutoOverlay (icono+SFX puntual sobre
// el video en curso), esto es una escena de PANTALLA COMPLETA para 1-2
// momentos clave (reveal / cierre), no continua -- si se usa en cada escena
// tapa los subtitulos y pierde impacto (ver advertencia en HISTORIAL_MEJORAS.md).
//
// La imagen ya llega procesada desde pipeline.py (recorte via rembg +
// halftone via PIL, ver _cutout_and_halftone()) como PNG con alpha. Esta
// composicion solo hace el LAYOUT y la ANIMACION: deriva horizontal continua
// (izquierda<->derecha, pedido explicito del usuario), recorte de "titular de
// prensa" real detras, sello DECLASSIFIED, y el mismo estilo de flecha
// punteada que AutoOverlay.
const INK = "#1a1208";
const GOLD = "#E8C468";
const STAMP_RED = "#8a1f11";

export function RealCollage({ photo, clipping, stampText }) {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 12, stiffness: 90, mass: 0.8 } });
  const outStart = durationInFrames - 12;
  const fadeOut = interpolate(frame, [outStart, durationInFrames - 1], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // deriva horizontal continua -- "movimiento corrido de izquierda a derecha"
  // pedido por el usuario. Amplitud chica, nunca se queda 100% quieto.
  const driftX = Math.sin(frame / 40) * 22;
  const tilt = -4 + Math.sin(frame / 55) * 2;

  const photoW = width * 0.62;
  const photoH = photoW * 1.15;

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {clipping && (
        <Img
          src={staticFile(clipping)}
          style={{
            position: "absolute",
            left: width * 0.08,
            top: height * 0.3,
            width: width * 0.5,
            opacity: 0.85 * enter,
            transform: `rotate(-8deg) scale(${enter})`,
            filter: "sepia(0.4) contrast(1.1)",
          }}
        />
      )}

      <div
        style={{
          position: "absolute",
          left: width / 2 - photoW / 2 + driftX,
          top: height * 0.28,
          width: photoW,
          height: photoH,
          transform: `scale(${enter}) rotate(${tilt}deg)`,
          transformOrigin: "center center",
        }}
      >
        <Img
          src={staticFile(photo)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            // halo dorado tipo "recorte de revista": drop-shadow sigue la
            // silueta del alpha, asi que apilar varias en direcciones
            // distintas con radio chico simula un contorno grueso (una sola
            // con offset 0 queda oculta detras de la imagen, no sirve).
            filter: [0, 45, 90, 135, 180, 225, 270, 315]
              .map((deg) => {
                const r = 7;
                const dx = (Math.cos((deg * Math.PI) / 180) * r).toFixed(1);
                const dy = (Math.sin((deg * Math.PI) / 180) * r).toFixed(1);
                return `drop-shadow(${dx}px ${dy}px 0px ${GOLD})`;
              })
              .join(" ") + ` drop-shadow(8px 8px 0px ${INK})`,
          }}
        />
      </div>

      {stampText && (
        <div
          style={{
            position: "absolute",
            right: width * 0.08,
            top: height * 0.14,
            padding: "10px 22px",
            border: `6px solid ${STAMP_RED}`,
            borderRadius: 10,
            color: STAMP_RED,
            fontFamily: "Arial Black, Arial, sans-serif",
            fontWeight: 900,
            fontSize: 40,
            letterSpacing: 2,
            transform: `rotate(12deg) scale(${enter})`,
            opacity: 0.85,
            mixBlendMode: "multiply",
          }}
        >
          {stampText}
        </div>
      )}
    </AbsoluteFill>
  );
}
