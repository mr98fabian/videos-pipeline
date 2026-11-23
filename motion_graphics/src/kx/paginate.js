// Paginación del karaoke KoreX. Sin React ni fuentes: la importan el
// componente y la prueba de paridad con kx_captions.paginate (Python).
import { createTikTokStyleCaptions } from "@remotion/captions";
import { CAPTIONS } from "./tokens";

const SENT = /[.!?…:]["”»)]?$/;
const CLAUSE = /[.!?…:;,]["”»)]?$/;
export const ends = (t) => SENT.test(t.text.trim());
const MIN = CAPTIONS.minWords;
const MAX = CAPTIONS.maxWords;

const compositions = (n, k) => {
  if (k === 1) return n >= MIN && n <= MAX ? [[n]] : [];
  const out = [];
  for (let s = MIN; s <= MAX; s++) for (const r of compositions(n - s, k - 1)) out.push([s, ...r]);
  return out;
};

// Cláusula de >4 palabras → trozos de 2-4, cortando donde createTikTokStyleCaptions
// detectó una pausa (inicio de su página) y, a igualdad, lo más parejo posible.
const splitClause = (toks) => {
  if (toks.length <= MAX) return [toks];
  let best = null;
  for (let k = Math.ceil(toks.length / MAX); k <= Math.ceil(toks.length / MIN) && !best; k++) {
    for (const sizes of compositions(toks.length, k)) {
      let pos = 0;
      let pauses = 0;
      for (let i = 0; i < sizes.length - 1; i++) {
        pos += sizes[i];
        if (toks[pos].pause) pauses++;
      }
      const score = pauses * 10 - (Math.max(...sizes) - Math.min(...sizes));
      if (!best || score > best.score) best = { score, sizes };
    }
  }
  let pos = 0;
  return best.sizes.map((s) => toks.slice(pos, (pos += s)));
};

// Exportado para el modo animatic. Gemelo exacto de kx_captions.paginate (Python):
// la QA compara contra las mismas páginas que se ven en pantalla.
export const paginate = (captions) => {
  const { pages } = createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: CAPTIONS.combineTokensWithinMilliseconds,
  });
  const toks = pages.flatMap((p) =>
    p.tokens.map((t, i) => ({ text: t.text.trim(), fromMs: t.fromMs, toMs: t.toMs, pause: i === 0 })),
  );
  // 1) cláusulas: nunca se cruza un punto, coma, dos puntos o punto y coma
  const chunks = [];
  let cur = [];
  for (const t of toks) {
    cur.push(t);
    if (CLAUSE.test(t.text)) {
      chunks.push(...splitClause(cur));
      cur = [];
    }
  }
  if (cur.length) chunks.push(...splitClause(cur));
  // 2) una palabra suelta que no cierra oración ("Y", "Sí,") se pega a la
  //    siguiente página; si no cabe, a la anterior; si tampoco, se queda sola.
  const out = [];
  let carry = [];
  const canJoinPrev = (n) => out.length && !ends(out[out.length - 1].at(-1)) && out[out.length - 1].length + n <= MAX;
  for (const c of chunks) {
    let p = [...carry, ...c];
    if (p.length > MAX) {
      if (canJoinPrev(carry.length)) out[out.length - 1].push(...carry);
      else out.push(carry);
      p = [...c];
    }
    carry = [];
    if (p.length === 1 && !ends(p[0])) carry = p;
    else out.push(p);
  }
  if (carry.length) {
    if (canJoinPrev(carry.length)) out[out.length - 1].push(...carry);
    else out.push(carry);
  }
  return out.map((tokens) => ({
    text: tokens.map((t) => t.text).join(" "),
    startMs: tokens[0].fromMs,
    endMs: tokens[tokens.length - 1].toMs,
    tokens,
  }));
};
