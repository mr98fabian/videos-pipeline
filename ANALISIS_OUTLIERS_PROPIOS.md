# Análisis de outliers propios: qué dicen nuestros 51 videos medidos

Análisis local con pandas sobre `performance_report.csv` (86 filas, 51 videos con métricas, todo cuenta `default`) y `retencion_mindcheckpoint.json` — agosto 2026

> **Regla del proyecto que rige todo este documento: nuestros datos medidos ganan sobre cualquier benchmark externo.** Cuando una guía de internet contradice lo que miden nuestros videos, creemos a nuestros videos.

---

## 1. Rendimiento por banda de longitud del guion (palabras)

| Banda | n | Vistas (mediana) | Retención (mediana) | Subs |
|---|---|---|---|---|
| Ultra (<25 palabras) | 12 | 4.5 | 124.7% | 0 |
| Corto (25-80) | 2 | 124 | 34.2% | — |
| **Medio (80-120)** | **5** | **1,086** | **70.9%** | — |
| Largo (120+) | 32 | 623 | 63.9% | 28 |

**Conclusiones:**

1. **El sweet spot es 80-120 palabras**: mediana de 1,086 vistas con retención sana del 70.9%. Los largos (120+) rinden peor (623 vistas, 63.9%).
2. **Los ultrashorts son una trampa de vanidad**: retención >100% (la gente loopea el video) pero **mediana de 4.5 vistas**. Retención alta ≠ distribución. Salvo 3 excepciones (ver §3), mueren todos en 2-10 vistas.
3. **Los largos son el motor de suscriptores** (28 subs concentrados ahí): el espectador que se queda 60-90 s con una historia se suscribe; el que loopea un clip de 8 s, no.

## 2. Shares: la señal sin explotar

- **Mediana de shares = 0 en TODAS las bandas.**
- Correlaciones: retención~vistas = -0.127; retención~shares = -0.071 → **la retención NO está correlacionada con éxito en nuestro corpus**. Perseguir retención por encima de X% no predice vistas ni shares.
- Implicación: la palanca no está en "retener más" sino en (a) distribución inicial / hook, y (b) generar la primera acción social (share/comentario). Ver `PSICOLOGIA_COMPARTIR.md` y `COMENTARIOS_ENGAGEMENT.md`.

## 3. Los 3 outliers que sí funcionaron (todos ultrashorts)

| Video | Vistas | Retención |
|---|---|---|
| "One Man Refused to Salute Hitler" | 1,242 | 148.9% |
| "Three Brothers Hid 1,200 Refugees" | 1,500 | 123.1% |
| "Cyclist's Bicycle Frame" | 1,403 | 126.3% |

Patrón común: **historia humana con tensión moral o visual fuerte** (desafío, rescate, proeza física), título que ya contiene el conflicto. El formato ultrashort SÍ funciona cuando el contenido es una historia completa con giro emocional, no un dato suelto. Esto replica a pequeña escala lo que las fuentes externas dicen de la sorpresa/emoción de alta activación (ver `PSICOLOGIA_COMPARTIR.md`).

## 4. Curvas de retención propias (`retencion_mindcheckpoint.json`)

- **Video de 39 s**: ratio fin/inicio = 0.17 → la caída decisiva ocurre en el **14% inicial** del video. El hook falla ahí o nada importa después.
- **Video de 92 s**: ratio fin/inicio = 0.22, con **caídas fuertes en los segundos 6-10%** (segunda criba tras el hook) y meseta descendente después.

Implicaciones:
1. Los primeros 5-6 segundos deciden ~80% del destino del video (consistente con la "regla de 7 segundos" externa, pero medida en casa).
2. Hay una segunda criba en el 6-10%: tras el hook, el espectador exige que el video "empiece ya". Relleno/saludo/introducción en ese tramo = muerte.
3. El final plano (0.17-0.22) indica que quien pasa el 15% tiende a quedarse: el problema es la entrada, no el cuerpo.

## 5. Decisiones de contenido derivadas (jerarquizadas)

| # | Decisión | Evidencia |
|---|---|---|
| 1 | Priorizar guiones de **80-120 palabras** para el canal principal | Banda media: 1,086 vistas mediana, 70.9% retención |
| 2 | Reservar ultrashort **solo** para historias humanas completas con giro (no datos sueltos) | 3 outliers vs 9 fracasos en la misma banda |
| 3 | Hook = conflicto/tensión ya en el título y el segundo 0-3; cero relleno hasta el 10% | Curvas de retención propias |
| 4 | Medir **shares/1000 vistas** como KPI nuevo; cualquier video >5 shares entra a análisis de outliers | Mediana shares = 0 |
| 5 | No optimizar retención por encima de ~70%: no correlaciona con vistas ni shares en nuestros datos | Correlaciones -0.127 / -0.071 |
| 6 | Los videos largos (120+ palabras) se mantienen como formato de **conversión a suscriptor**, no de alcance | 28 subs concentrados ahí |

## 6. Qué medir a partir de ahora (para el próximo análisis)

- `shares_per_1000_views` por video
- `subs_per_1000_views` por banda de palabras
- Retención en segundos 0-6 y 6-10% como métricas separadas (hoy solo tenemos curva agregada)
- Etiquetar cada video con `emocion_objetivo` y `momento_giro` (ver checklist de guiones) para correlacionar emoción → shares
- Muestra mínima: repetir este análisis cuando haya ≥100 videos con métricas

## Fuentes

- Datos primarios: `performance_report.csv`, `retencion_mindcheckpoint.json` (este proyecto)
- Benchmarks externos citados solo como contraste: regla de 7 segundos (narrationbox guide) — EN
