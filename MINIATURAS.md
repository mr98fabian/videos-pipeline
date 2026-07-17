# Miniaturas de YouTube — por qué funcionan (foco gameplay/LoL)

Investigación con fuentes reales, marcada ✅ verificado (estudio/fuente citada) o ⚠️ plausible-sin-fuente dura (consenso de la industria sin paper detrás). Todo en función de aplicarlo YA a las miniaturas del canal de LoL/gameplay.

---

## 1. Fundamentos: qué pasa en los primeros 150ms

El cerebro decide si sigue mirando una miniatura antes de que exista pensamiento consciente:

- El cerebro evalúa contraste de color, caras y anomalías visuales en **~100-150ms**, antes de la decisión deliberada. ⚠️ (consenso repetido en múltiples fuentes de industria, sin paper primario citado) — [tubeanalytics.net](https://www.tubeanalytics.net/blog/youtube-thumbnail-design-psychology)
- Consecuencia práctica: la miniatura se juzga **como un blob borroso primero, como imagen nítida después**. Si el mensaje central no sobrevive a desenfocar el ojo (o reducir a 160px, tamaño real en el feed de móvil), no funciona. Esto es lo que rompía nuestras v1-v2: texto de 3 líneas + fondo detallado = ruido a tamaño móvil.
- **Regla operativa**: una idea por miniatura. Un elemento debe ganar el 80% del peso visual; todo lo demás es soporte. Los tests de mercado confirman que el over-clutter reduce CTR porque el ojo no resuelve "de qué trata esto" en el tiempo que tiene — [1of10](https://1of10.com/blog/why-your-youtube-thumbnails-arent-working-and-how-to-fix-them/), [DGM News](https://dgmnews.com/posts/10-common-youtube-thumbnail-mistakes-that-are-killing-your-views/)

### Jerarquía visual (de qué se agarra el ojo, en orden)
1. Cara humana con emoción legible (si existe)
2. Objeto/color que rompe con el fondo (alto contraste)
3. Texto grande (2-4 palabras máx)
4. Todo lo demás

---

## 2. Psicología del clic: los mecanismos concretos

### 2.1 Caras y emoción — por qué funcionan específicamente
- El cerebro tiene una estructura dedicada, el **fusiform face area**, que procesa caras más rápido y con más recursos que cualquier otro estímulo visual. ✅ (neurociencia establecida, aplicada a thumbnails por [tubeanalytics.net](https://www.tubeanalytics.net/blog/youtube-thumbnail-design-psychology))
- Miniaturas con cara humana superan a las que no la tienen por **25-30%** en CTR, según A/B testing extensivo. ⚠️ (cifra repetida en múltiples blogs de industria sin estudio primario público)
- Caras con emoción fuerte y legible (sorpresa, shock, confusión) superan a expresiones neutras por **25-40%**. ⚠️ misma fuente de industria — [tubeanalytics.net](https://www.tubeanalytics.net/blog/youtube-thumbnail-design-psychology)
- **Por qué importa el género**: en gaming/reacción, la cara vende "algo le pasó a esta persona, quiero saber qué". En documentales/explainers, la cara vende menos que el objeto/pregunta (por eso Mack no usa su cara — ver `INVESTIGACION_MACK.md`).

### 2.2 El "curiosity gap" (Paddy Galloway, consultor detrás de MrBeast/Airrack)
- La psicología detrás del clic importa **más** que el diseño gráfico. Cita textual: *"la psicología para incitar el clic > los colores, el diseño o la belleza. Una de las mejores personas que conozco en thumbnails es mediocre en Photoshop"* ✅ — [Paddy Galloway en X](https://x.com/PaddyG96/status/1564326373170319360)
- Mecanismo: **"unpausing the viewer"** — la miniatura + título crean un loop abierto en el cerebro (algo va a pasar, hay peligro, hay un objeto increíble) que el viewer necesita cerrar dando clic. ✅ — [Paddy Galloway breakdown](https://www.youtube.com/watch?v=B6H2KE3kNdI)
- Fórmula: **simplicidad + exageración, sin cruzar a clickbait engañoso.** El balance es la habilidad real, no el Photoshop.
- Aplicado a gameplay: el prop (arma, ítem, stat) actúa como el "objeto increíble" que abre el loop — "¿por qué tiene eso? ¿qué pasó con +9000 HP?"

### 2.3 Contraste de color — el mecanismo, no solo la regla
- Colores contrastantes (complementarios: verde/rojo, amarillo/morado, naranja/azul) generan **hasta 30% más CTR** en un estudio de Vidooly 2023. ⚠️ (citado en múltiples fuentes secundarias, no verifiqué el estudio primario)
- Contraste alto en general mejora CTR entre **20-40%**. ⚠️ misma cadena de fuentes — [tubeanalytics.net](https://www.tubeanalytics.net/blog/youtube-thumbnail-design-psychology)
- **Por qué funciona técnicamente**: los colores complementarios están en polos opuestos del círculo cromático — sus valores de brillo están lo más lejos posible entre sí, así que a 160px (tamaño real en feed) siguen siendo dos manchas separables. Colores análogos (verde/azul, rojo/naranja) se funden en una sola mancha borrosa a ese tamaño.
- Colores cálidos (rojo/naranja/amarillo) = urgencia/excitación. Colores fríos (azul/verde) = calma/confianza. Gaming casi siempre usa cálidos para el texto sobre fondo frío/oscuro — es el patrón exacto que vimos en el screenshot de referencia del usuario (amarillo/verde sobre fondos oscuros saturados).

---

## 3. Cómo lo hacen los canales grandes de LoL/gaming

Basado en el screenshot que Fabián compartió (canales reales del feed recomendado de LoL en español: *"¡El NUEVO Olaf Vampiro ADC con +196% ROBO DE VIDA les hace llorar!"*, *"+9000 HP MUNDO SER INMORTAL"*, *"1000 CARGAS EL TERROR DE LA TOPLANE"*, *"NUEVO RAMMUS DR. DOOM"*) más patrones consistentes en el nicho MOBA/gaming ES:

### La fórmula observable (✅ verificado en el screenshot real del usuario)
1. **Splash art o render del campeón/ítem a tamaño grande**, ocupando 40-60% del frame — nunca screenshot de gameplay borroso.
2. **Número o stat gigante como prop central**: "+9000 HP", "1000 CARGAS", "+196%". El número ES el gancho — cuantifica la exageración y es procesable en milisegundos (un número no necesita "leerse", se reconoce como forma).
3. **Texto corto en amarillo/verde neón con borde negro grueso**, 1-4 palabras, nunca una oración completa. La miniatura no cuenta la historia — la insinúa.
4. **Alto contraste y saturación elevada** respecto al gameplay real del juego — el color se empuja más allá de lo natural a propósito (esto rompe la regla "sé fiel al juego" que Fabián me dio para los guiones, pero es correcto para miniaturas: la miniatura no es el contenido, es el anzuelo).
5. **Composición asimétrica**, no split 50/50 rígido: el elemento hero (personaje o ítem) generalmente ocupa una diagonal o domina un lado, dejando "aire" para el texto — exactamente lo opuesto de lo que hicimos en `nocturne_tabis_v1.png` (split rígido, dos mitades iguales, se ve genérico y de plantilla).

### Por qué el número/stat exagerado es el elemento más importante en este nicho
Conecta directo con el mecanismo de Paddy Galloway (2.2): el número es el "loop abierto". *"+9000 HP"* es imposible en el juego real → el viewer necesita saber cómo. Es el mismo mecanismo que "boliches Tabi (obvio)" — la miniatura promete una respuesta absurda/graciosa a una pregunta implícita.

### Consistencia de marca
Los canales grandes repiten: misma fuente, mismo color de borde, misma posición del logo/marca de agua en todos los videos — señal de reconocimiento instantáneo en el feed (el ojo aprende "esa mancha amarilla con esa tipografía = mi canal favorito") incluso antes de leer. ⚠️ (patrón observado, no cuantificado con estudio).

---

## 4. Por qué fracasan las miniaturas — incluido nuestro propio caso

### Errores genéricos documentados
- **Sobrecarga de elementos**: intentar meter demasiada información reduce el CTR porque el viewer no resuelve "de qué trata" en el tiempo que tiene. Regla: "one idea per thumbnail" — [1of10](https://1of10.com/blog/why-your-youtube-thumbnails-arent-working-and-how-to-fix-them/)
- **Bajo contraste texto/fondo**: mata la legibilidad, especialmente en móvil (>60% del tráfico de YouTube es móvil). Texto fino o sutil que se ve bien en monitor grande desaparece en pantalla de teléfono. ✅ — [Mention](https://mention.com/en/blog/youtube-thumbnails-design/)
- **Fondos generados por IA demasiado detallados**: se ven bien en pantalla grande pero se convierten en "ruido borroso" en móvil — mencionado específicamente como fallo de miniaturas con IA. ✅ — [ReelMind](https://reelmind.ai/blog/bad-youtube-thumbnails-why-they-fail)

### Caso de estudio propio: `nocturne_tabis_v1.png` y v2
Con el marco de arriba, los fallos concretos fueron:
1. **Split 50/50 rígido** — composición de plantilla genérica, sin asimetría ni jerarquía (rompe 3.5).
2. **Render de Nocturne generado por IA (Nano Banana)** en vez de splash art oficial de Riot — el viewer de LoL reconoce el arte oficial en <150ms; un render genérico no dispara ese reconocimiento inmediato, rompe la promesa de "esto es sobre MI juego".
3. **Ícono de botas Tabi pixelado (64px nativo, escalado)** — viola la regla de contraste/nitidez a tamaño móvil; se ve como error técnico, no como elección de diseño.
4. **Texto redundante con la imagen**: "BOTAS TABI" en texto Y las botas dibujadas — no hay necesidad de decir lo que ya se ve. El texto debería aportar el ángulo/gancho (ej. un stat falso o "(obvio)" solo, dejando que el ícono cargue el peso informativo) en vez de repetir el sustantivo.
5. **Sin número/stat gigante** — el elemento #2 de la fórmula ganadora del nicho (sección 3) estaba ausente. Sin él, la miniatura no tiene el "loop abierto" que dispara el clic.

---

## 5. Tendencias 2024→2026: qué cambió

- **De cluttered a minimalista**: las miniaturas densas en información que antes atraían atención ahora la diluyen — el feed está saturado de ese estilo, así que lo simple destaca por contraste con el resto del feed. ⚠️ — [YouTube Thumbnail Trends 2025](https://www.brandmag.net/youtube-thumbnail-trends-2025-what-gets-clicks/)
- **Autenticidad ganando terreno en nichos no-gaming**: fotos ligeramente imperfectas, "detrás de cámaras", superan al arte demasiado pulido en credibilidad — pero esto aplica más a vlogs/lifestyle. **Gaming/MOBA sigue funcionando con estilo saturado/exagerado** porque compite en un feed de otros gaming channels igual de saturados — bajar la saturación ahí te hace invisible, no auténtico.
- **"Quality CTR" (2026)**: YouTube ahora evalúa qué pasa en los 30 segundos después del clic, no solo si hubo clic. Miniaturas con alto CTR pero mala retención dañan el posicionamiento del video — el algoritmo detecta y penaliza el engaño. ✅ — [Cliptics](https://cliptics.com/blog/youtube-algorithm-2026-what-changed-how-to-adapt/)
- **Consecuencia directa**: la miniatura debe prometer algo que el video **cumple**. Para el video de Nocturne, "(obvio)" + botas Tabi debe llevar a contenido que explique/muestre por qué son obvias — si el video no entrega esa payoff en los primeros segundos, el algoritmo penaliza aunque el CTR inicial sea bueno.
- **Impresiones cambiaron de definición en 2026**: solo cuentan si la miniatura estuvo visible ≥1.5 segundos en pantalla — antes bastaba con aparecer brevemente. Esto sube el estándar real de calidad porque las impresiones "basura" (scroll rápido) ya no cuentan. ✅ — [Cliptics / dataslayer.ai](https://cliptics.com/blog/youtube-algorithm-2026-what-changed-how-to-adapt/)

---

## 6. Algoritmo y feed: por qué el contexto importa tanto como la miniatura en sí

- **CTR no se juzga en el vacío** — se juzga contra las miniaturas vecinas en el feed en ese momento. Una miniatura "buena" rodeada de otras 5 igual de saturadas no gana; necesita un elemento diferenciador (el número gigante, un color que nadie más usa en ese feed).
- **Relación inversa impresiones↔CTR**: mientras más impresiones (audiencia más amplia y menos afín), menor CTR esperado — es normal que el CTR baje cuando el video escala a audiencias frías. ✅ — [dataslayer.ai vía Cliptics](https://cliptics.com/blog/youtube-algorithm-2026-what-changed-how-to-adapt/)
- **Benchmarks de CTR 2026**: promedio general 4-6%, >7% es bueno, >10% es excelente. Con adyacencia temática fuerte (recomendado dentro del mismo nicho), el CTR sugerido esperado ronda 9.5%. ✅ — [Humble & Brag](https://humbleandbrag.com/blog/youtube-ctr-benchmarks), [thumbmagic.co](https://www.thumbmagic.co/blog/youtube-thumbnail-ctr-benchmarks)
- **A/B testing nativo (Experimentos de YouTube Studio)**: hasta 3 variantes de título+miniatura simultáneas. Ganador se decide por **watch time share**, no solo clics — refuerza que el algoritmo ya integra el principio de "Quality CTR" en el propio test. Necesita ~2,000-5,000 impresiones por variante para 85-95% de confianza, normalmente 1-2 semanas. Testear solo 1 variable a la vez (ej. solo cambiar la expresión facial, no todo el diseño) para resultados atribuibles. Resolución mínima 1280x720 o se downscalea a 480p. ✅ — [Google/YouTube Help oficial](https://support.google.com/youtube/answer/16391400?hl=en-US), [OutlierKit](https://outlierkit.com/resources/youtube-ab-testing-3-variants-guide-2026/)

---

## 7. Checklist operativo — aplicar ya al canal de LoL/gameplay

### Plantilla de composición (basada en la fórmula verificada de sección 3)
1. **Fondo**: splash art oficial de Riot (Data Dragon `ddragon.leagueoflegends.com/cdn/img/champion/splash/`) o loading screen — nunca render de IA ni screenshot de gameplay sin editar. Alto contraste/saturación aplicado (+15-25% sobre el original).
2. **Prop central**: ítem/campeón en grande, asimétrico (no split 50/50) — usar el ícono oficial de Riot solo si se puede mostrar a tamaño donde no pixele (≤200px de origen se ve mal escalado a >300px; si hace falta más grande, usar el modelo 3D/splash del ítem si Riot lo publica, o un render fiel de mayor resolución).
3. **Número/stat gigante**: el elemento que más CTR aporta en este nicho según el patrón observado — un stat real o exagerado a propósito ("+9000 HP", "1 vida", "0 muertes"), en fuente bold, color que contraste al máximo con el fondo.
4. **Texto de apoyo**: 1-4 palabras, nunca repetir lo que ya muestra la imagen. Amarillo o verde neón con borde negro grueso (8-12px a esta resolución).
5. **Cara (opcional, solo si aporta)**: si se usa, expresión exagerada y legible (shock/orgullo/burla), nunca neutra — o mejor omitirla si el gancho ya lo carga el número+ítem (como hacen los 4 canales del screenshot, ninguno usa facecam en la miniatura).

### Antes de publicar
- [ ] ¿Se entiende el mensaje central en <1 segundo mirándolo a 160px (tamaño real de feed móvil)?
- [ ] ¿Hay un solo elemento que domina, o compiten 3+ cosas por atención?
- [ ] ¿El contraste principal usa colores complementarios (no análogos)?
- [ ] ¿El texto aporta información nueva o repite lo que ya se ve?
- [ ] ¿El video cumple la promesa/payoff de la miniatura en los primeros 15-30s? (Quality CTR, sección 5)
- [ ] Subir en 1280x720 mínimo (evita downscale automático a 480p si luego se activa A/B testing).

### Explotar el A/B testing nativo desde el video 1
Crear 2-3 variantes que cambien **una sola variable** (ej. con/sin número gigante, dos colores de texto distintos) y dejar correr el experimento nativo de YouTube Studio 1-2 semanas antes de fijar ganador — ya recomendado en `CANAL_SETUP.md` sección 2, este documento confirma el mecanismo y el porqué.

---

## Fuentes citadas
- [tubeanalytics.net — YouTube Thumbnail Design Psychology](https://www.tubeanalytics.net/blog/youtube-thumbnail-design-psychology)
- [Paddy Galloway en X — psicología sobre diseño](https://x.com/PaddyG96/status/1564326373170319360)
- [Paddy Galloway — Truth about Thumbnails (video)](https://www.youtube.com/watch?v=B6H2KE3kNdI)
- [1of10 — Why your thumbnails aren't working](https://1of10.com/blog/why-your-youtube-thumbnails-arent-working-and-how-to-fix-them/)
- [Mention — Mistakes to avoid in thumbnail design](https://mention.com/en/blog/youtube-thumbnails-design/)
- [ReelMind — Bad YouTube thumbnails, why they fail](https://reelmind.ai/blog/bad-youtube-thumbnails-why-they-fail)
- [DGM News — 10 common thumbnail mistakes](https://dgmnews.com/posts/10-common-youtube-thumbnail-mistakes-that-are-killing-your-views/)
- [Cliptics — YouTube Algorithm 2026](https://cliptics.com/blog/youtube-algorithm-2026-what-changed-how-to-adapt/)
- [Humble & Brag — CTR Benchmarks 2026](https://humbleandbrag.com/blog/youtube-ctr-benchmarks)
- [thumbmagic.co — CTR benchmarks / A/B testing guide](https://www.thumbmagic.co/blog/youtube-thumbnail-ctr-benchmarks)
- [Google/YouTube Help — A/B test titles and thumbnails (oficial)](https://support.google.com/youtube/answer/16391400?hl=en-US)
- [OutlierKit — A/B testing 3 variantes guía completa](https://outlierkit.com/resources/youtube-ab-testing-3-variants-guide-2026/)
- Screenshot del feed de LoL en español provisto por Fabián (fuente primaria propia, canales reales verificados visualmente en la sesión)
