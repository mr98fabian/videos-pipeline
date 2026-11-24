// Karaoke KoreX con el patrón del template-tiktok de Remotion:
// Caption[] → createTikTokStyleCaptions → páginas → token activo resaltado.
// Encima de la agrupación por tiempo se fuerzan dos reglas de la biblia:
// 2-4 palabras por página y ninguna página cruza un fin de oración.
import React, { useMemo } from "react";
import { paginate } from "./paginate";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { INK, PAPER, SAFE, TYPE } from "./tokens";
import { DISPLAY_FAMILY } from "./fonts";

const Page = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowMs = page.startMs + (frame / fps) * 1000;
  return (
    <div
      style={{
        fontFamily: DISPLAY_FAMILY,
        fontWeight: TYPE.captionWeight,
        fontSize: TYPE.captionSize,
        lineHeight: TYPE.captionLineHeight,
        textAlign: "center",
        textTransform: "uppercase",
        color: INK,
        width: SAFE.width,
        // las palabras nunca se parten; la página envuelve a 2 líneas entre palabras
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        columnGap: 8,
        rowGap: 4,
      }}
    >
      {page.tokens.map((t, i) => {
        const active = nowMs >= t.fromMs && nowMs < t.toMs;
        const said = nowMs >= t.toMs;
        return (
          <span
            key={i}
            style={{
              whiteSpace: "nowrap",
              padding: "0 12px",
              borderRadius: 10,
              opacity: active || said ? 1 : 0.32,
              background: active ? INK : "transparent",
              color: active ? PAPER : INK,
            }}
          >
            {t.text}
          </span>
        );
      })}
    </div>
  );
};

// `bandTop`/`bandHeight` ubican la franja dentro de la zona segura; por
// defecto, el tercio inferior de la caja (y 1008-1248).
export const KxCaptions = ({ captions, bandTop = SAFE.bottom - 240, bandHeight = 240 }) => {
  const { fps } = useVideoConfig();
  const pages = useMemo(() => paginate(captions), [captions]);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {pages.map((page, i) => {
        const next = pages[i + 1];
        const from = Math.round((page.startMs / 1000) * fps);
        const until = next ? Math.round((next.startMs / 1000) * fps) : Math.round((page.endMs / 1000) * fps) + fps;
        if (until <= from) return null;
        return (
          <Sequence key={i} from={from} durationInFrames={until - from} layout="none">
            <div
              style={{
                position: "absolute",
                left: SAFE.left,
                width: SAFE.width,
                top: bandTop,
                height: bandHeight,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Page page={page} />
            </div>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
