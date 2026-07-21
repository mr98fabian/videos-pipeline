# Plan de acción exacto: ImPixxel vs los canales que sí convierten

Basado en: datos reales de tu YouTube Studio (10 jul 2026), análisis en vivo del canal Kerios (643K subs, tu benchmark ES de LoL), los canales que ve tu público (BekindXP, MisrraVB 267K, itero.gg 40K, Th3Antonio 178K) y benchmarks 2026 de Shorts.

## ACCIÓN URGENTE (20 jul 2026)

**Cortar el gasto en ads ya mismo.** El usuario fijó la regla el 16 jul de parar promociones al llegar a 1,000 subs; el canal está en 1,080 y el % de tráfico pagado subió (22%→36.8%) en vez de bajar. Ver `PROGRESO_CANAL.md` fila 20 jul para el detalle completo (incluye un salto anómalo de suscriptores 11-17 jul sin causa confirmada, no extrapolable).

## Diagnóstico en una línea

**El algoritmo ya te encontró (31.3K vistas, 10.6K únicos/mes); nadie sabe quién eres cuando el video termina.** 99.6% público nuevo, 97.1% del watch time de no-suscritos, retorno "Bajo" en TODOS tus videos.

## Qué hacen ellos que tú no (verificado, no teoría)

| Ellos | Tú | Impacto |
|---|---|---|
| **Kerios: su cara/reacción en CADA Short** — el clip es la excusa, la personalidad es el producto | Clips de gameplay donde tu facecam es pequeña o incidental | Es LA razón por la que su viewer vuelve y el tuyo no: se suscriben a personas, no a jugadas |
| **Kerios: marca de agua "KICK.com/KERIOS" quemada en todos los videos** | Sin marca visual — tus clips son anónimos, indistinguibles de cualquier otro canal | Cada Short tuyo que se viraliza regala 1.9K vistas sin dejar rastro de quién eres |
| **Kerios: títulos en su voz** ("ou yeah papi", "DETONADA A CASSIO", "Tanques :D") — consistentes con cómo habla en el video | Títulos tuyos ✅ ya tienen voz ("¡Me llevó pa' Somalia!") pero las **descripciones son relleno genérico de IA** ("la emoción y la locura se desatan...") sin CTA | La descripción es tu único espacio de conversión y hoy está vacía de intención |
| **Kerios: funnel claro** — Shorts → directos en Kick → videos largos editados del stream | Shorts sueltos sin destino: ni playlist, ni video relacionado consistente, ni "más de esto aquí" | El viewer que quiere más no tiene a dónde ir |
| **Canales 24K-267K de tu nicho: cadencia diaria con formato reconocible** (misma estructura de video repetida) | Subes ráfagas (3 el 8 jul, 3 el 10 jul) con formatos mezclados + duplicados ("El peor camuflaje" x3) | El algoritmo y el viewer no pueden formar el hábito "ya sé qué es esto" |

## Benchmarks a monitorear ([shortimize](https://www.shortimize.com/blog/youtube-shorts-retention-rate), [miraflow](https://miraflow.ai/blog/youtube-shorts-best-practices-2026-complete-guide))

- Retención ≥65% en Shorts <30s (o ≥50% en 30-60s) para que YouTube te empuje más amplio. Tu "Somalia" con 58% está cerca; el promedio del canal (42.6%) no.
- Hook en <2s = +30% de duración promedio de vista. Loop (rewatch >100% AVD) es la señal más fuerte — tu "Somalia" ya lo logra (0:18 en video de 0:16).
- Responder los primeros comentarios en <2h amplifica el reach durante la ventana de prueba del algoritmo.

## PLAN — en orden de impacto

### HOY (30 min, sin grabar nada)
1. **Borra los duplicados** ("El peor camuflaje" x2 de más y cualquier re-upload). Deja el de más vistas.
2. **Reemplaza TODAS las descripciones genéricas** con esta plantilla (5 min por video):
   ```
   [Qué pasó, en tu voz: "Me tiré el 1v9 y el chat no lo creía"]
   [Pregunta específica: "¿Tú también le habrías dado?"]
   Sígueme que subo jugadas así todos los días 👇
   #leagueoflegends #lol #shorts
   ```
3. **Comentario fijado en cada video** con la pregunta polarizante (ya lo genera el pipeline en description.txt — úsalo).

### ESTA SEMANA (setup de identidad, una vez)
4. **Marca de agua en todos los videos futuros**: "ImPixxel" pequeño, esquina superior, quemado en el video (el pipeline lo puede añadir automático con drawtext — 1 línea de FFmpeg). Es lo que hace Kerios con su Kick.
5. **Tu cara/reacción más grande en los clips de gameplay**. Si el momento es tuyo, tu reacción ES el contenido. Facecam a ~35-40% de pantalla en el momento clave, no miniatura de esquina.
6. **CTA hablado o en texto en los últimos 2s de cada Short**: "sígueme pa' más" — corto, en tu voz, no rogado. Los guiones de Skick lo incorporan a partir de ahora (línea final del script).
7. **Playlists por formato** (jugadas / Skick / fails) + "video relacionado" configurado en cada Short apuntando al mejor video del mismo formato.

### ESTE MES (hábito y formato)
8. **Cadencia fija: 1/día a la misma hora** (12-2 PM funciona para gaming según datos 2026) en vez de ráfagas de 3. Con el pipeline + Task Scheduler ya montado, es sostenible.
9. **Un formato reconocible que se repita**: elige 1-2 moldes (ej. "jugada + tu reacción con título en tu voz" y "Skick meme semanal") y repítelos con variación. Los canales de 24K-267K de tu nicho son reconocibles al tercer video; tú todavía no.
10. **Responde comentarios en las primeras 2h** de publicar (señal fuerte 2026 + es donde nace la comunidad que vuelve).
11. **Revisa a los 30 días**: usuarios ocasionales >2% y suscritos >5% del watch time = el funnel empieza a funcionar. Si sigue en 99% nuevos, el problema pasa a ser formato, no conversión.

## Qué NO cambiar

- El contenido/gameplay: retención de "Somalia" (58%, con rewatch) prueba que los clips funcionan.
- Los títulos: ya tienen voz propia, mejor que muchos canales medianos.
- La cadencia de producción con pipeline: la ventaja es tuya, solo hay que ordenarla.

## Fuentes
- Datos propios: YouTube Studio ImPixxel, 10 jul 2026 (Analytics 28 días + video "Somalia").
- [Kerios /shorts y /videos](https://www.youtube.com/@Kerios/shorts) — patrón verificado en vivo esta sesión.
- [Shortimize — retention benchmarks](https://www.shortimize.com/blog/youtube-shorts-retention-rate) · [Miraflow — Shorts best practices 2026](https://miraflow.ai/blog/youtube-shorts-best-practices-2026-complete-guide) · [OpusClip — ideal length/format](https://www.opus.pro/blog/ideal-youtube-shorts-length-format-retention)
