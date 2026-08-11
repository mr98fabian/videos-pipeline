# Serie KOREX: "Pelando cable" — 5 episodios

Creada: 10 ago 2026, a partir del hallazgo del Short ganador
**"Cómo salir de deudas y dejar de 'pelar cable' este 2026 🔥"**
(`youtube.com/shorts/wjBlLC3whJE`), el primer video KoreX práctico/buscable.

**Por qué serie y no videos sueltos:** la investigación de algoritmo 2026
(`MINIATURAS_SHORTS_2026.md` §4, fuentes coreanas) — el algoritmo premia la
cobertura en profundidad de una keyword (5+ episodios del mismo universo) por
encima de videos aislados. Y `SERIES_LORE_PERSONAJES.md`: las series generan
suscripción y binge.

**Fórmula de título (todos los episodios):**
`[Búsqueda evergreen: "Cómo X" / "Qué pasa si X"] + [slang local que autoidentifica] + [ancla temporal opcional]`
Keyword dicha en voz alta en los primeros 3 s (indexación IA). Slang por
episodio: pelar cable, quincena, el fiado, caerse la renta, guardadito.

**Anti-slop:** cada episodio varía la estructura (apertura, orden de beats,
cierre), no solo el dato — el check `_check_antislop_similarity` del pipeline
avisa si dos guiones consecutivos comparten ≥10% de shingles de 5 palabras.

---

| # | Archivo | Título | Búsqueda evergreen (autocomplete YT verificado 10 ago 2026) | Giro | Villano |
|---|---|---|---|---|---|
| 1 | `output/2026-08-10-tu-quincena-no-se-va-en-la-renta-se-va-e/` ✅ **ya renderizado 10 ago** (sesión de Claude, del guion de quincena de Kimi; pendiente de publicar, no está en `video_log.csv`) | Tu quincena no se va en la renta (se va en esto) | "como ahorrar dinero si ganas poco" | se desangra en doscientas heridas chiquitas (gasto hormiga) | Bruja del Banco |
| 2 | `scripts/korex-tarjeta-minimo.json` ✅ listo | Qué pasa si solo pagas el mínimo de la tarjeta (la Bruja te lo agradece) | "que pasa si no pago la tarjeta de credito" | el pago mínimo es una suscripción: compras el derecho a seguir debiendo | Bruja del Banco |
| 3 | `scripts/korex-fiado.json` | Cómo decir que no cuando te piden plata prestada (sin quedar mal) | "prestar plata a familia" | prestar plata que necesitas no es ayudar, es cambiar de deudor | Mapache Millonario (primo que "emprende") |
| 4 | `scripts/korex-arriendo.json` | Qué pasa si no te alcanza para el arriendo este mes | "que pasa si no pago la renta" | negociar ANTES del vencimiento vale 10 veces más que esconderse | Bruja del Banco (casera) |
| 5 | `scripts/korex-fondo-emergencia.json` | Cómo armar tu guardadito ganando poco (empezando con 20 pesos) | "como ahorrar dinero si ganas poco" | el fondo no se arma con lo que sobra, se arma primero y se vive con el resto | Mapache Millonario |

**Reglas de producción por episodio:**
1. Guion a mano con los 3 campos de la regla 11 (`target_emotion`,
   `twist_phrase`, `comment_cta`) — el lint `_check_giro_posicion` los exige.
2. Giro en banda 25-75% (ideal 30-60%).
3. Cierre en bucle: última frase enlaza con la primera.
4. `comment_cta` de elección (A o B), nunca hablado.
5. Publicar numerados ("Pelando cable #2") en la descripción, no en el título
   (el título es para la keyword, no para la serie).
6. Medir `shares_per_1000_views` por episodio (KPI nuevo de
   `performance_report.py`) — si el ep. 1 baja de la mediana del ganador,
   revisar la fórmula antes de seguir con el 2.

**Validación de la fórmula:** el video original es n=1. Esta serie es el test:
3-5 videos con la misma fórmula de título. Si la mediana de vistas de los 5
supera claramente la de los KoreX históricos, la fórmula pasa a estándar del
canal; si no, se descarta y se anota en `ANALISIS_OUTLIERS_PROPIOS.md`.
