// Fase 2 de la Misión 0001: la prueba del rig de Tadeo (KxTadeo, 10-15 s) y
// la hoja de poses (KxTadeoHoja, un still). No son plantillas de producción.
import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from "remotion";
import { INK, PAPER, SAFE } from "./tokens";
import { DISPLAY_FAMILY } from "./fonts";
import { FilmGrain } from "./texture";
import { Tadeo } from "./tadeo/Tadeo.jsx";
import { CabezaPartes, TadeoPartes } from "./tadeo/partes.jsx";
import { estado } from "./tadeo/acting.js";

export const KxTadeo = ({ linea }) => {
  const frame = useCurrentFrame();
  const cur = [...linea].reverse().find((c) => frame >= c.t0) || linea[0];
  return (
    <AbsoluteFill style={{ background: PAPER }}>
      <div style={{ position: "absolute", left: SAFE.left, top: SAFE.top + 16, width: SAFE.width, textAlign: "center",
        fontFamily: DISPLAY_FAMILY, fontWeight: 800, fontSize: 56, color: INK }}>
        {`${cur.beat ? "*" : ""}tadeo/${cur.pose}`}
      </div>
      <Tadeo linea={linea} semilla={3} uid="kxt" />
      <FilmGrain />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------ hoja de poses
const Rotulo = ({ children, size = 30, style }) => (
  <div style={{ fontFamily: DISPLAY_FAMILY, fontWeight: 800, fontSize: size, color: INK, textAlign: "center", ...style }}>{children}</div>
);

// Un Tadeo estático en una celda: pies abajo al centro.
const Celda = ({ pose, w, h, escala, silueta = false, uid }) => {
  const est = estado({ desde: pose, frame: 0, conIdle: false, agenda: [] });
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      {silueta ? (
        <filter id={`${uid}-sil`}>
          <feFlood floodColor={INK} />
          <feComposite in2="SourceAlpha" operator="in" />
        </filter>
      ) : null}
      <g filter={silueta ? `url(#${uid}-sil)` : undefined}>
        <g transform={`translate(${w / 2} ${h - 8}) scale(${escala} ${-escala})`}>
          <TadeoPartes est={est} uid={uid} />
        </g>
      </g>
    </svg>
  );
};

const CeldaCabeza = ({ expr, mirada, w, h, escala, uid }) => {
  const est = estado({ desde: "neutro", exprDesde: expr, miradaDesde: mirada, frame: 0, conIdle: false, agenda: [] });
  return (
    <svg width={w} height={h}>
      <g transform={`translate(${w / 2} ${h / 2}) scale(${escala} ${-escala}) translate(0 -800)`}>
        <CabezaPartes cabeza={est.cabeza} cara={est.cara} mirada={est.mirada} orejas={est.orejas} uid={uid} />
      </g>
    </svg>
  );
};

export const KxTadeoHoja = ({ celdas, hojaMadre }) => {
  const { poses, cabezas, siluetas, comparacion, expresiones, miradas } = celdas;
  const PW = 250;
  const PH = 360;
  const PS = 0.3;
  const HW = 230;
  const HH = 190;
  const HS = 0.36;
  return (
    <AbsoluteFill style={{ background: PAPER, padding: 40 }}>
      <Rotulo size={56} style={{ textAlign: "left" }}>Tadeo · rig vectorial · hoja de poses (Misión 0001 · Fase 2)</Rotulo>
      <div style={{ display: "flex", gap: 40, marginTop: 24, alignItems: "flex-start" }}>
        <div>
          <Rotulo style={{ textAlign: "left" }}>hoja madre (referencia)</Rotulo>
          <Img src={staticFile(hojaMadre)} style={{ width: 1376, height: 768, border: `3px solid ${INK}` }} />
        </div>
        <div>
          <Rotulo style={{ textAlign: "left" }}>vigilancia 1 · orgulloso (suficiencia) vs codicia (avaricia)</Rotulo>
          <div style={{ display: "flex", gap: 20 }}>
            {comparacion.map((id) => (
              <div key={id} style={{ border: `3px solid ${INK}` }}>
                <Celda pose={id} w={520} h={640} escala={0.6} uid={`cmp-${id}`} />
                <Rotulo size={36}>{id}</Rotulo>
              </div>
            ))}
            <div style={{ border: `3px solid ${INK}` }}>
              <CeldaCabeza expr="codicia" mirada="camara" w={420} h={360} escala={0.8} uid="cmp-cara" />
              <Rotulo size={30}>expr codicia (las dos)</Rotulo>
            </div>
          </div>
        </div>
      </div>

      <Rotulo style={{ textAlign: "left", marginTop: 30 }}>14 poses · expresión y mirada por defecto</Rotulo>
      <div style={{ display: "flex", flexWrap: "wrap", width: PW * 14 }}>
        {poses.map((id) => (
          <div key={id} style={{ width: PW }}>
            <Celda pose={id} w={PW} h={PH} escala={PS} uid={`p-${id}`} />
            <Rotulo size={26}>{id}</Rotulo>
          </div>
        ))}
      </div>

      <Rotulo style={{ textAlign: "left", marginTop: 20 }}>vigilancia 3 · siluetas en negro macizo</Rotulo>
      <div style={{ display: "flex", width: PW * 14 }}>
        {siluetas.map((id) => (
          <div key={id} style={{ width: PW }}>
            <Celda pose={id} w={PW} h={PH} escala={PS} silueta uid={`s-${id}`} />
            <Rotulo size={26}>{id}</Rotulo>
          </div>
        ))}
      </div>

      <Rotulo style={{ textAlign: "left", marginTop: 20 }}>10 expresiones × 4 miradas (vigilancia 2: ¿el antifaz envuelve los ojos?)</Rotulo>
      <div style={{ display: "flex" }}>
        <div style={{ width: 140 }} />
        {expresiones.map((e) => <Rotulo key={e} size={26} style={{ width: HW }}>{e}</Rotulo>)}
      </div>
      {miradas.map((m) => (
        <div key={m} style={{ display: "flex", alignItems: "center" }}>
          <Rotulo size={26} style={{ width: 140, textAlign: "right", paddingRight: 10 }}>{m}</Rotulo>
          {expresiones.map((e) => {
            const c = cabezas.find((k) => k.expr === e && k.mirada === m);
            return c ? <CeldaCabeza key={e} expr={e} mirada={m} w={HW} h={HH} escala={HS} uid={`h-${e}-${m}`} /> : <div key={e} style={{ width: HW }} />;
          })}
        </div>
      ))}
    </AbsoluteFill>
  );
};

// Molde de parecido: el neutro del rig, sin boil, idle ni grano, dibujado en
// la MISMA rejilla de píxeles que la vista frontal de la hoja madre (×4), para
// que kx_parecido.py mida solape y marcas píxel a píxel.
export const KxTadeoMolde = ({ xc, suelo, s }) => {
  const est = estado({ desde: "neutro", frame: 0, conIdle: false, agenda: [] });
  return (
    <AbsoluteFill style={{ background: PAPER }}>
      <svg width="100%" height="100%">
        <g transform={`translate(${xc} ${suelo}) scale(${s} ${-s})`}>
          <TadeoPartes est={est} uid="molde" />
        </g>
      </svg>
    </AbsoluteFill>
  );
};
