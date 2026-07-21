# Guía de gancho para ImPixxel (LoL con skin Roblox) -- complemento de RETENTION_CHECKLIST.md

Los guiones de ImPixxel siempre se escriben a mano (no via `generate_script()`, que
tiene un prompt hardcodeado de canal de finanzas en inglés -- no aplica acá). Todo lo
de abajo hay que aplicarlo manualmente al escribir cada guion nuevo, no es automático.

## `hook_card` para ImPixxel: 2 variantes según el tipo de video

ImPixxel tiene dos formatos de contenido bien distintos -- el `hook_card` debe escribirse
distinto para cada uno.

### A. Lore serio (Kayn, Senna, Viego, Thresh, etc.)

El card debe ser la premisa como curiosity gap, en tono serio, SIN spoilear el giro
emocional del guion. Nunca copiar la primera oración textual.

- Guion Kayn (script actual): "Kayn no sabe si todavía es él quien controla el arma."
  (esto ya es la oración de apertura -- el hook_card NO debe repetirla igual).
  **hook_card sugerido**: "Un arma que susurra promesas. Un campeón que ya no está seguro
  de quién gana la pelea." -- misma idea, ángulo distinto, retiene el desenlace (que la
  pelea interna sigue sin resolverse).
- Formato general: `"[objeto/entidad] + [consecuencia ambigua/amenaza latente]"` -- 2
  oraciones cortas, tono místico, nunca nombrar el resultado final.

### B. Humor/meme (gg ez, camper, gastó 500 dólares, etc.)

El card debe funcionar como el texto de meme que ya se ve en TikTok/Reels de gaming --
corto, directo, casi como un titular de meme, no como misterio narrativo.

- Guion "gg ez" (script actual): el hook_card NO debe ser "Esto es League of Legends" (la
  apertura literal). **hook_card sugerido**: "El enemigo se derrotó solo. Él se llevó el
  crédito." -- resume la premisa cómica sin arruinar el remate (que lo repite 3 veces).
- Formato general: `"[situación absurda en 4-6 palabras]"` -- more meme caption que
  narración, casi siempre con tono de burla/ironía.

## Loop narrativo para ImPixxel

La regla de "cerrar recontextualizando la apertura" (no solo repetirla) aplica igual que
en HiddenFacts. Ejemplo ya usado correctamente en el guion de Kayn: abre "Kayn no sabe si
todavía es él quien controla el arma" y cierra "...o si el arma ya ganó hace tiempo" --
la MISMA pregunta pero con la respuesta insinuada, no solo repetida. Mantener este patrón
en todo guion de lore nuevo.

Para humor: el loop es más simple -- repetir la frase de remate (ya lo hacen, ej. "gg ez"
x3) funciona porque la REPETICIÓN ES el chiste, no hace falta recontextualizar el
significado como en lore.

## Regla de sync search_terms = oraciones (ya aplica automático)

El lint de `_check_script_lint()` en `pipeline.py` ya avisa si el conteo no coincide --
aplica a cualquier guion, ImPixxel incluido, sin cambios necesarios.

## `--hook-max` y `--wan-hero`: ya transfieren gratis

Correr los guiones de ImPixxel con `--hook-max` (default desde el 19 jul) da el mismo
stinger/flash/wipe/zoom que en HiddenFacts, sin ningún cambio -- son agnósticos de estilo.
`--wan-hero` también funciona igual (animar la escena 0 con un clip local en vez de imagen
estática), aunque para personajes con estilo Roblox voxel conviene revisar que Wan 2.2 no
"suavice" el estilo blocky (ver memoria estilo-roblox-nanobanana sobre el mismo problema
con Nano Banana).
