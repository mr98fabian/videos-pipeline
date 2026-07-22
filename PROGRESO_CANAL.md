# Progreso del canal ImPixxel — histórico de auditorías

Registro de cada corrida de `/canal audit`. Comparar siempre contra la fila anterior, no solo el número absoluto.

| Fecha | Vistas/28d | Horas reproducción | Suscriptores totales | Δ subs/28d | % usuarios nuevos | % watch time suscritos | % tráfico publicidad | Notas |
|---|---|---|---|---|---|---|---|---|
| 09 jul 2026 | 31.3K | 82.8h | 23 | +21 | 99.6% | 2.9% | 0% (sin promo) | Primera auditoría. Contenido funciona (retención "Somalia" 58%), conversión a suscriptor casi nula. Descripciones genéricas de IA sin CTA. |
| 10 jul 2026 | 34.4K | 96.3h | 76 | +24 | 99.7% | 2.8% | 6.6% (2 videos promocionados) | El salto de suscriptores es volumen (más vistas), no mejor conversión — % usuarios nuevos y watch time suscritos se mantuvieron iguales o empeoraron. La promoción pagada NO movió la retención de fondo. |
| 11 jul 2026 | 36.1K | 105.9h | 118 | +101 | 99.7% | **5.7%** | 10.3% (sigue la promo activa) | Suscriptores casi se duplicaron (76→118) pero % usuarios nuevos NO bajó — sigue siendo volumen, no mejor tasa de conversión por view. Señal real y positiva: watch time de suscritos SUBIÓ de 2.8%→5.7% (x2), primera mejora de fondo desde que se aplicaron descripciones con CTA. Publicidad ahora es 10.3% del tráfico (subió, la promo sigue corriendo) — igual sigue siendo minoría, 86.4% es Feed orgánico. Retención inicial sin cambios (42.9%, igual que ayer). |
| 16 jul 2026 | 43.9K (28d) | 121.6h | — (no medido esta corrida) | — | — (no medido) | **5.4%** (391/(391+6908) min) | **22.0%** (9,670/43,876 views, subió de 10.3%→22.0%) | La promo casi se DUPLICÓ en % de tráfico y el watch time de suscritos se mantuvo IGUAL o bajó levemente (5.7%→5.4%) — más dinero gastado, misma conversión de fondo. Confirma otra vez la lectura del 10 jul: comprar vistas no mejora retención/lealtad, solo volumen. Top 15 videos por vistas siguen siendo TODOS clips crudos de gameplay con títulos genéricos de julio 1-12 — **los duplicados de título que MEJORAS_CANAL.md pedía borrar el 10 jul siguen sin limpiarse**: "El peor camuflaje" aparece x3 (1709/1408/1158 vistas), "El momento más épico de la partida" x2 (1450/1361). Ninguno de los nuevos videos serie Roblox (Garen/Shaco/Sylas/Yasuo/Darius/sweat) entra al top 15 — son de 1-2 días, todavía no es comparación justa; además Yasuo/Darius/sweat/lag fueron borrados por el usuario antes de acumular señal, así que **no hay datos aún sobre si el formato Roblox nuevo funciona mejor que el clip crudo**. |
| 20 jul 2026 | 60.1K (28d, Data API) / 60.0K (vidIQ, ventana hasta 17 jul) | ~8.6K min (28d) | **1,080** | +1,690 (28d) | — (no medido) | — (no medido) | **36.8%** (22,079/60,042 views, ventana vidIQ) | **Regla propia incumplida: el usuario fijó "cortar ads al llegar a 1000 subs" el 16 jul y el canal ya está en 1,080 — el % de tráfico pagado en vez de bajar SUBIÓ de 22.0%→36.8%.** Además se detectó un salto anómalo de suscriptores el 11-17 jul (111/82/243/221/332/287/384 subs/día, ~1,660 en 7 días) que no es tendencia sostenible ni fue explicado — no se sabe si fue una campaña puntual más agresiva o un video viral real; no extrapolar ese ritmo a futuro sin confirmar la causa. Proyección a 4 semanas entregada con dos escenarios (conservador ~+70/semana vs. sostenido, matemáticamente poco realista) — ver detalle en la sesión del 20 jul. |

## Qué mirar en la próxima auditoría

- **Regla del usuario (16 jul): cortar las promociones pagadas al llegar a 1,000 suscriptores.** No gastar más en ads mientras tanto tampoco — van 3 auditorías seguidas donde subir el gasto no mueve el watch time de suscritos.
- **Duplicados limpiados (16 jul):** borrados `BF_iqiwIwx8` (1408v, "de la historia") y `OdwF60y4mr0` (1158v) del grupo "El peor camuflaje" — quedó solo `H7I43mX-_7s` (1709v). Borrado `OkdRdNYliUk` (1361v) del grupo "El momento más épico de la partida" — quedó solo `tlBOlFzphkQ` (1450v). Revisar en la próxima auditoría si las vistas del sobreviviente subieron al dejar de competir consigo mismo.
- Dejar que Garen/Shaco/Sylas (serie Roblox, vivos) acumulen 4-5 días antes de comparar contra los clips crudos — a 1-2 días de vida no es lectura justa.
- Si se vuelve a generar contenido de prueba (ej. el experimento de polarización), evitar borrarlo antes de al menos 48h — si se borra antes de acumular vistas, no deja señal utilizable para la próxima auditoría.

## Auditoría HiddenFacts (GetHiddenFacts) — 22 jul 2026

Primera auditoría formal de este canal (nació 14 jul, 8 días de vida real).

| Métrica | Valor |
|---|---|
| Suscriptores | 37 |
| Vistas totales | 32,426 |
| Videos publicados | 70 (58 tras limpieza) |
| Vistas/día (Analytics oficial, única semana completa disponible) | 637 / 6,095 / 4,688 / **6,529 (pico, 18 jul)** / 4,756 |
| % tráfico Shorts feed | 97%+ |

**Hallazgo crítico y causa raíz identificada:** 12 videos con duración real de 5.4-7.2s
(deberían durar ~50-60s) se generaron y publicaron TODOS en el mismo segundo
(2026-07-18T18:01) — guiones de guion de **solo 15 palabras** (una oración) en vez
de las ~150 normales. 10 de los 12 flopearon (2-14 vistas); 2 tuvieron
`breakoutScore` inflado (274, 428) por el artefacto de "loop instantáneo" de
clips ultra-cortos, no por audiencia real. El pico del canal (6,529 vistas)
fue justo el día que se publicó este batch — plausible que la señal de
calidad promedio dañada haya frenado el alcance de los días siguientes.

**Acción tomada (22 jul):** los 12 se pasaron a privado. Se encontraron 3
MÁS con el mismo bug programados para publicarse el mismo 22 jul (10:45/13:45/
16:45 UTC) — se cancelaron (privado sin `publishAt`) antes de salir al aire.

**Pendiente de código:** no existe ningún guardrail que bloquee la subida de
un video con duración final por debajo del mínimo de 60s — `_check_pacing()`
solo avisa ANTES de generar el TTS, nada verifica el video FINAL. Este es el
fix de raíz para que el bug no se repita.

**No hay señal de "breakout" real todavía** (ningún video llega a 5-10x el
promedio del resto de forma genuina, descontando los 2 inflados por el bug).
