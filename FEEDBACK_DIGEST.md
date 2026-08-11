# Feedback digest datos -> prompt — 2026-08-10

Corpus: 35 videos con >= 30 vistas. Generado por `feedback_digest.py` sobre `performance_report.csv`. Regla del corpus: nuestros datos medidos ganan sobre benchmarks externos.

## 3. Palabras del guion -> rendimiento

| Banda | n | Vistas mediana | Shares/1000 mediana |
|---|---|---|---|
| ultra (<25) | 3 | 1,403 | n/d |
| corto (25-80) | 1 | 245 | n/d |
| medio (80-120) | 5 | 1,086 | n/d |
| largo (120+) | 26 | 711 | n/d |

**Accion:** comparar contra el sweet spot medido (80-120 palabras, `ANALISIS_OUTLIERS_PROPIOS.md` §1); si la banda ganadora cambio, ajustar el largo objetivo del prompt.

## 4. Pendientes del loop

- Retencion segmentada 0-6s y 6-10%: la Analytics API no entrega curvas por segundo; bajar el CSV de retencion de YouTube Studio (Analytics > Contenido > video > Retencion) para los outliers y guardarlo como `retencion_<video_id>.json` en la carpeta de output.
- Revisar este digest el primer lunes del mes y tocar SOLO una regla del prompt a la vez (si se cambian dos, la atribucion se pierde -- ver `experiments.py`).
