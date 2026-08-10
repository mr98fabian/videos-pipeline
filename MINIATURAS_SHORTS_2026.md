# Miniaturas en Shorts 2026: dónde importan y dónde son invisibles

Investigación multiidioma — agosto 2026
Idiomas consultados: inglés, coreano (한국어, bonus sobre algoritmo)

> Hallazgo central, respaldado por un A/B test de más de 1 millón de impresiones: **en el feed de Shorts la miniatura tiene 0% de impacto; en Browse features (página de inicio) sube el CTR +140%; en búsqueda +85%**. Diseñar miniaturas "para el feed" es optimizar para una superficie donde nadie las ve.

---

## 1. El dato que cambia la estrategia (joyspace.ai, A/B test 1M+ impresiones)

| Superficie | ¿Se ve la miniatura? | Impacto medido |
|---|---|---|
| Feed de Shorts (swipe vertical) | No (autoplay directo) | **0%** |
| Browse / página de inicio | Sí | **+140% CTR** con buena miniatura |
| Búsqueda | Sí | **+85% CTR** con miniatura de texto legible |
| Página del canal / grid | Sí | Consistencia visual de marca |

Conclusión estratégica: la miniatura de un Short trabaja para **descubrimiento fuera del feed** — búsqueda, inicio, canal. Si el canal depende 100% del feed, la miniatura es casi irrelevante; si queremos tráfico de búsqueda y canal (long-tail), es una palanca enorme.

## 2. Qué funciona en la miniatura (notelm.ai, 127 tests)

| Elemento | Efecto sobre CTR |
|---|---|
| Expresión facial intensa | +42% |
| Añadir una cara (vs no cara) | +47% |
| Hook de texto legible en la imagen | +34% |
| Miniatura ganadora promedio vs perdedora | +37% CTR |

Notas operativas:
- **Test & Compare nativo de YouTube Studio** elige el ganador por **watch time, no por CTR** — útil porque premia la miniatura que atrae al espectador correcto, no solo clicks.
- En búsqueda, el texto de la miniatura debe ser legible en tamaño pequeño (móvil): máx. 3-4 palabras, contraste alto.

## 3. La restricción técnica que hay que conocer (2026)

- En Shorts, la miniatura **se bloquea al publicar**: no se puede cambiar después.
- **Solo se puede elegir un frame desde la app móvil** (selector de frame al subir). A junio 2026, el escritorio **no permite miniatura personalizada** en Shorts.
- **El truco del gremio**: "hornear" (bake) un frame-miniatura limpio en 9:16 **al final del propio video** — 1-2 frames con la composición deseada (cara/texto/elemento clave) — y seleccionarlo con el selector de frame de la app al publicar.
  - Esto es **implementable en `pipeline.py`**: añadir al final del render un frame diseñado (composición + texto) antes del último corte.

## 4. Bonus coreano: hacia dónde va el algoritmo 2026 (KO)

De fuentes coreanas de crecimiento en YouTube:

- **YouTube analiza voz, subtítulos y contenido visual con IA** para clasificar y recomendar — el "SEO" ya no es solo título/tags: lo que dice el TTS y lo que aparece en pantalla alimenta la indexación. Implicación: los subtítulos quemados del pipeline deben ser textualmente fieles y ricos en la keyword del tema.
- **Series de 5+ episodios por keyword**: el algoritmo premia la cobertura en profundidad de un tema (varios videos sobre la misma keyword/universo) por encima de videos aislados. Conecta con `SERIES_LORE_PERSONAJES.md`.
- **Política anti "AI slop" 2026**: exclusión de monetización para canales masivos y repetitivos con poca variación entre videos. Nuestro pipeline debe garantizar variación real (guiones únicos, estructura distinta), no solo cambiar el dato.

## 5. Síntesis operativa

| Situación | Acción |
|---|---|
| Short para feed puro | Miniatura: esfuerzo mínimo; invertir el tiempo en hook 0-3 s |
| Short con potencial de búsqueda (dato "googleable") | Frame-miniatura horneado al final + texto de 3-4 palabras |
| Grid del canal | Paleta/estilo consistente por canal (marca visual) |
| Testing | Usar Test & Compare en videos long-form; en Shorts, decidir antes de publicar (bloqueo) |
| Indexación IA | Subtítulos fieles + keyword pronunciada por la voz en los primeros segundos |

## Aplicación concreta al pipeline

1. **`pipeline.py`**: añadir generación de **frame-final 9:16 diseñado** (imagen compuesta: elemento clave + texto corto, misma tipografía del canal) insertado en los últimos 0.2 s del render. Coste: bajo; beneficio: control total de la miniatura vía selector de frame móvil.
2. **`youtube_api.py` / flujo de publicación**: documentar que la publicación de Shorts debe hacerse (o verificarse) desde la app móvil para fijar el frame elegido antes de publicar.
3. **Plantilla de texto de miniatura**: 3-4 palabras máx., alto contraste, sin bordes finos.
4. **Política anti-AI-slop**: añadir check de variación entre guiones consecutivos (similitud de estructura) antes de encolar publicaciones.
5. **Medición**: separar en `performance_report` el tráfico por fuente (feed vs búsqueda vs canal) cuando la API lo permita, para saber si la miniatura está trabajando.

## Fuentes consultadas

- joyspace.ai — A/B test 1M+ impresiones: impacto de miniaturas por superficie (feed 0%, browse +140%, búsqueda +85%) — EN
- notelm.ai — 127 tests: cara +47%, expresión +42%, texto hook +34%, ganador medio +37% — EN
- Documentación/comunidad sobre Test & Compare (optimiza por watch time) y bloqueo de miniatura en Shorts; selector de frame solo móvil — EN
- Fuentes coreanas de algoritmo YouTube 2026: análisis IA de voz/subs/visual, series 5+ episodios por keyword, política anti "AI slop" — KO
