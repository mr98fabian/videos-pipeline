// <Tadeo pose expr mirada desde hacia t0 escala x y semilla beat /> (A8).
//   pose:            pose fija (sin transición)
//   desde/hacia/t0:  una transición de pose que empieza en el frame t0
//   linea:           [{pose, t0, expr?, mirada?, beat?}] (varios cambios; se valida)
//   x, y:            punto de los pies en píxeles de pantalla
// Dibuja a pantalla completa: el boil es UN filtro para todo el personaje.
import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { BoilDefs } from "../texture";
import { INK } from "../tokens";
import { POSES, RIG } from "./poses.js";
import { agendaLinea, estado, estadoLinea, progresoCapa, validarLinea } from "./acting.js";
import { CuerpoLamina, TadeoPartes } from "./partes.jsx";
import { LAMINAS } from "./laminas/index.js";

// cuerpo="lamina" (misión 0006): la pose se dibuja con su lámina trazada si la hay
// (laminas/index.js). El cambio de pose es un cambio de dibujo a los CAMBIO_LAMINA
// frames de t0 (sección 8: 2-4 frames), no una interpolación de miembros.
// Una pose sin lámina cae al cuerpo por piezas. Por defecto: "piezas" (lo de siempre).
const CAMBIO_LAMINA = 3;

export const Tadeo = ({
  pose, expr, mirada, desde, hacia, t0 = 0, linea = null,
  escala = 1, x = RIG.pantalla.x, y = RIG.pantalla.y, semilla = 0, beat = false, conIdle = true, uid = "tadeo", silueta = false,
  cuerpo = "piezas",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const agenda = useMemo(() => {
    if (!linea) return null;
    validarLinea(linea); // dos cambios sin hold suficiente = error de la escena
    return agendaLinea(linea, durationInFrames, semilla);
  }, [linea, durationInFrames, semilla]);

  let est;
  let esBeat = beat;
  let tBeat = t0;
  if (linea) {
    est = estadoLinea(linea, frame, { semilla, duracion: durationInFrames, conIdle, agenda });
    const cur = [...linea].reverse().find((c) => frame >= c.t0) || linea[0];
    esBeat = !!cur.beat;
    tBeat = cur.t0;
  } else {
    const a = desde || pose;
    est = estado({
      desde: a, hacia: hacia || a, t0, frame, exprDesde: desde ? undefined : expr, exprHacia: expr,
      miradaDesde: desde ? undefined : mirada, miradaHacia: mirada, semilla, beat, conIdle, duracion: durationInFrames,
    });
  }
  // Beat «*»: la misma pose a ×1,12, entrando con ACENTO.
  const b = esBeat ? 1 + (RIG.beatEscala - 1) * progresoCapa("torso", frame, tBeat, { beat: true }) : 1;
  const s = (RIG.pantalla.alto / RIG.alto) * escala * b;
  const fid = `${uid}-boil`;
  // la pose que se DIBUJA (con lámina): la nueva a los CAMBIO_LAMINA frames del cambio
  let dibujo = null;
  if (cuerpo === "lamina") {
    if (linea) {
      const i = linea.findLastIndex((c) => frame >= c.t0);
      const cur = linea[Math.max(0, i)];
      const prev = i > 0 && frame < cur.t0 + CAMBIO_LAMINA ? linea[i - 1] : cur;
      dibujo = prev.pose;
    } else {
      dibujo = hacia && frame >= t0 + CAMBIO_LAMINA ? hacia : (desde || pose);
    }
  }
  const lam = dibujo ? LAMINAS[dibujo] : null;
  const figura = lam
    ? <CuerpoLamina t={lam} est={est} baseInclina={(POSES[dibujo]?.cabeza?.inclina) || 0} baseSy={(POSES[dibujo]?.torso?.sy) || 1} uid={uid} />
    : <TadeoPartes est={est} uid={uid} />;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <BoilDefs id={fid} offset={semilla} />
        {/* silueta: el personaje entero en INK macizo (test sin-hueco de la iteración 3) */}
        {silueta ? (
          <filter id={`${fid}-sil`}>
            <feFlood floodColor={INK} />
            <feComposite in2="SourceAlpha" operator="in" />
          </filter>
        ) : null}
        <g filter={silueta ? `url(#${fid}-sil)` : undefined}>
        <g filter={`url(#${fid})`}>
          <g transform={`translate(${x} ${y}) scale(${s} ${-s})`}>
            {figura}
          </g>
        </g>
        </g>
      </svg>
    </AbsoluteFill>
  );
};
