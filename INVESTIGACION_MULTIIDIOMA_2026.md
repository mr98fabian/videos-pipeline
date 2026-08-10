# INVESTIGACIÓN MULTIIDIOMA 2026 — Marketing, YouTube, Guiones, Humor, Retención y Caricaturas

Investigación compilada el 9 ago 2026 a partir de fuentes en **inglés, español, portugués y francés**.
Complementa (no reemplaza) lo ya medido en este proyecto: `RETENCION_PSICOLOGIA.md`, `HUMOR_GAMER.md`,
`INVESTIGACION_ALGORITMO_2026.md`, `PSICOLOGIA_SEGUNDO_0.md`, `PROMPT_MAESTRO.md` y las reglas medidas
que viven en `SCRIPT_PROMPT` de `pipeline.py`.

> **Regla de oro al leer esto:** cuando un benchmark genérico de internet contradice un dato
> medido en ESTE canal (ej. "los Shorts de <25s dominan" vs. nuestro `SHORTS_HARD_MIN = 15` y
> sweet spot 30-45s medido con datos propios), **gana el dato propio**. Los benchmarks externos
> son punto de partida, no ley.

---

## 1. Algoritmo de YouTube Shorts 2026 (EN/ES/PT)

### Lo nuevo y dominante: Señales de Satisfacción
El cambio más grande 2025→2026: YouTube pasó de optimizar **watch time bruto** a optimizar
**satisfacción del espectador**. Las señales que componen "satisfacción":

- **Encuestas directas** — YouTube pregunta a una muestra de usuarios cómo valoraron un video.
- **Repeticiones (rewatch)** — ver el video más de una vez. Refuerza lo que ya medimos: el loop
  invisible del guion es la palanca más fuerte que tenemos.
- **Continuación de sesión** — el espectador se QUEDA en YouTube después de tu Short.
- **Compartidos externos** — pesan 5-8× más que un like (el espectador pone su identidad en juego).
- **Señales negativas** — "No me interesa" / "No recomendar este canal" matan distribución activamente.

### El pipeline de distribución en 3 fases (confirmado por varias fuentes)
1. **Cold seeding** — cada Short se prueba con 50-500 espectadores, ~70% NO suscriptores en 2026
   (antes 50%). Coherente con nuestro dato: 96.7% del tráfico de HiddenFacts viene del feed.
2. **La puerta de watch time** — benchmarks externos: ~65% retención para <30s, ~50% para 30-60s.
   Por debajo, el video se deja de mostrar.
3. **Topic clustering** — los que pasan se emparejan con clusters temáticos y pueden seguir
   ganando vistas 3-6 semanas. **Por eso la consistencia temática importa**: canales que publican
   temas coherentes permiten a YouTube segmentar mejor la audiencia semilla.

### Datos operativos útiles
- 74% de las vistas de Shorts vienen de no suscriptores; 75% de fuera del país del creador.
- Los creadores top publican **18-22 Shorts/mes** (la media de plataforma es 7).
- Combinar Shorts + formato largo crece el canal 41% más rápido que solo largo.
- ~80% de las impresiones del primer mes llegan en las primeras 48-72h.
- Los primeros 30 segundos se elevaron de "métrica diagnóstica" a **input de ranking central**.
- Política 2026 endurecida: contenido "inesitablemente producido en masa con plantilla" puede
  perder monetización → nuestro pipeline necesita que cada video tenga guion, estilo y QA propios
  (ya lo hace: `korex_qa.py`, estilo fijo por canal, guion por Claude con reglas duras).

**Fuentes:** quso.ai/blog/youtube-shorts-algorithm · go-viral.app/es (guía ES muy completa) ·
outlierkit.com (B) · socialync.io · kompozy.io · schedulala.com/pt (PT, con 3 casos de estudio) ·
seoalgorithmrecovery.com · aibrify.com

---

## 2. Guiones: estructuras y hooks (EN/ES)

### La anatomía de 5 partes (consenso EN)
1. **Hook (0-10s)** — una sola misión: ganar los siguientes 30 segundos. Tres formatos que conviene
   escribir SIEMPRE antes de producir: afirmación audaz, problema específico, apertura
   contraintuitiva. Regla: el hook lo decide todo — escribir 3 variantes y elegir.
2. **Puente de retención (10-30s)** — expectativa clara de qué se lleva el espectador.
3. **Cuerpo en secciones** — cada sección con mini-hook propio y transición de **open loop**
   ("eso cubre X, pero lo que casi todos hacen mal es Y...").
4. **Pattern interrupts cada 60-90s** — cambio de energía/plano/ritmo que resetea la atención.
5. **Cierre + UN solo CTA específico** — nunca "like, comenta y suscríbete": una acción, una razón
   concreta. (En nuestro caso el diseño ya va más lejos: `CLOSE_TAIL = 0`, corte seco en la última
   palabra para el loop — medido como mejor que cualquier CTA.)

### Los 5 patrones de gancho que frenan el scroll (fuente ES, short.now)
1. **Vacío de curiosidad** — abre una pregunta que solo se cierra viendo.
2. **Afirmación audaz** — específica, no genérica ("añade este elemento a tu gancho y sube la
   finalización 40%" > "consigue más vistas").
3. **Promesa práctica** — "Cómo [resultado específico] en [plazo/pasos]".
4. **Arco narrativo** — abrir con el final ("En 90 días pasé de X a Y. Así es cómo.").
5. **Interrupción de patrón** — empezar a mitad de frase, en acción, con sonido/visual inesperado.

### Estructura viral ES de 5 bloques (panconpollo.com)
Gancho (3-5 palabras, sin explicar nada) → **Pico de interés** (frase contradictoria o mini
historia que dice "este video sí vale la pena") → **storytelling sensorial** (que el espectador
se vea reflejado, no explicar de más) → valor en pasos (recién aquí se enseña) → CTA con razón.

### Curiosity loops (la técnica de mayor apalancamiento, channel.farm)
Basada en la **information-gap theory de Loewenstein (1994)**: la curiosidad es un estado
AVERSIVO — una deuda que el cerebro necesita saldar. Tres niveles:
- **Macro loop** — se abre en los primeros 15-30s y se cierra al final ("al final sabrás X, pero
  solo funciona si entiendes las 3 bases primero").
- **Micro loops** — puentes de 2-4 min entre secciones; se colocan donde la curva cae.
- **Loops anidados** — abrir un segundo loop antes de cerrar el primero (avanzado).
- **Loops en cascada** — cada sección cierra el loop anterior Y abre uno nuevo: aplana la caída
  del medio del video. Es lo más cercano a nuestra regla medida de `_check_payoff_spacing`.

**Advertencia clave (creatorlanehq.com):** un loop abierto es una DEUDA. Si no se paga dentro del
mismo video, el espectador lo registra como traición — y por el efecto Zeigarnik la recuerda
entre videos. El clickbait no solo pierde un video: baja el techo de los siguientes diez.
→ Esto valida nuestra regla dura: el loop del guion cierra sobre las palabras del hook.

**Fuentes:** storyflow.so (B) · sumera.io · stratboost.ai · short.now/es · panconpollo.com ·
channel.farm · creatorlanehq.com · achalay.net (prompt ES con micro-peaks cada 3-5s)

---

## 3. Psicología del humor: cómo dar gracia con guiones (EN/ES, académico)

### Las tres familias teóricas (y qué aporta cada una al guion)
1. **Incongruencia** (Aristóteles → Kant → Schopenhauer → Raskin/Attardo): el humor nace de
   yuxtaponer dos elementos incompatibles y que la mente los reconcilie de golpe. Cicerón ya lo
   dijo: "esperamos una cosa y se dice otra; nuestra propia expectativa defraudada nos hace reír".
   → **Aplicación:** setup que construye una expectativa + remate que la rompe.
2. **Violación Benigna (BVT, McGraw & Warren 2010)** — la teoría dominante hoy: algo es gracioso
   cuando (a) viola una norma, (b) se percibe como benigno, y (c) ambas cosas OCURREN A LA VEZ.
   Si la violación pesa más → ofensa. Si lo benigno pesa más → aburrimiento. El punto dulce
   depende de la **distancia psicológica** (temporal, social, cultural).
   → **Aplicación directa al canal gamer:** el humor de "tu hermanito te carryó" funciona porque
   viola la norma del orgullo gamer pero es benigno (le pasó a todos). El humor que ataca al
   espectador sin distancia segura OFENDE y mata retención. Cuidado con la **asimetría de poder**:
   reírse "hacia arriba" (del tryhard, del whale) funciona; reírse "hacia abajo" sin complicidad, no.
3. **Superioridad / alivio** (Platón, Hobbes, Freud) — reírnos del tropiezo ajeno como alivio de
   tensión. Es la base del slapstick y del schadenfreude gamer ("ese Yasuo 0/10").

### Técnicas concretas de escritura de comedia (fuentes ES)
- **Premisa → remate:** la premisa pinta una imagen mental con expectativa lógica; el remate la
  rompe. El mejor remate SIEMPRE al final del bloque (estructura de stand-up, UANL).
- **Regla del tres** (cursosdeguion.com): elemento 1 presenta, elemento 2 valida el patrón,
  elemento 3 lo ROMPE. Dos antes de la ruptura porque con uno no hay patrón y con tres se amortigua.
  Variante **ascendente**: cada elemento más exagerado, el tercero absurdo.
  Variante **+1** (doble remate): solo si el cuarto elemento es MÁS gracioso que el tercero;
  si hay duda, no se hace, porque rompe el clímax.
- **La regla del tres no es solo para humor:** la misma estructura patrón-patrón-ruptura genera
  susto en terror, muestra evolución de personaje, y — clave para nosotros — **estructura el giro
  final de un Short histórico** (dos datos que establecen "lo que creías" + el tercero que lo voltea).
- **Callback:** referenciar al final un gag del principio. Refuerza cohesión y da la sensación de
  "todo estaba conectado" — y en nuestro formato, potencia el loop de rewatch.
- **Exageración, substitución, contraste, eufemismo, juego de palabras** — las 6 figuras retóricas
  base de la escritura cómica (Horton/Millar).
- **Tesis UA (comedia de situación):** 8 familias de estrategias humorísticas detectadas en guiones
  profesionales — verbal (6), situacional (1), visual (1). El humor VISUAL (exageración, deformidad,
  contraste) es el que mejor combina con nuestra capa de stickers/placas.

### Lo que el humor aporta a la retención
El humor es un **pattern interrupt emocional**: cada remate es una micro-recompensa dopaminérgica
que resetea la atención. Un guion con remates espaciados cada 10-15s sostiene la curva igual que
un open loop, pero además genera compartidos (la señal que más pesa en 2026).

**Fuentes:** McGraw & Warren (2010, PMC6593112 S) · Yale Law (S) · utoronto.scholaris.ca (A) ·
cursosdeguion.com · tesis UA rua.ua.es · UANL eprints · thecriticalcomic.com · merceclasca.com

---

## 4. Psicología de la retención humana (EN/ES/FR)

### Los mecanismos medidos
- **Efecto Zeigarnik (1927):** recordamos tareas interrumpidas ~90% mejor que las completadas.
  Un loop abierto es una deuda cognitiva que el cerebro exige cerrar. Por eso el cliffhanger y el
  video en loop funcionan — y por eso un loop SIN pago se recuerda como traición.
- **Information-gap (Loewenstein, 1994):** la curiosidad es un impulso aversivo proporcional al
  hueco entre lo que sabes y lo que quieres saber. Solo dispara cuando el espectador es consciente
  de un hueco ESPECÍFICO → el hook debe nombrar el hueco, no insinuarlo vagamente.
- **Dopamina por anticipación:** la dopamina no se libera con la recompensa sino con la
  ANTICIPACIÓN de resolver. Suspense + resolución = memorabilidad. Ritmo: abrir tensión, resolver,
  abrir otra.
- **Neuronas espejo y oxitocina:** las historias con personaje y conflicto generan empatía
  (oxitocina) que los datos fríos no generan. Un dato histórico contado como "lo que le pasó a
  una persona concreta" retiene más que el mismo dato como efeméride.
- **Procesamiento visual:** >50% del cerebro procesa lo visual; la imagen se procesa ~60.000× más
  rápido que el texto y se recuerda el 80% de lo visto vs 20% de lo leído. → cada frase del guion
  debe tener una imagen que la DUPLIQUE emocionalmente, no que la repita (regla `not_visible` de
  `viral_lab.py`, validada también por la investigación).
- **La economía de la atención (FR, Citton/CNRS):** la atención es un bien escaso disputado;
  el espectador decide en <1s. Refuerza nuestra regla medida: frame 0 con movimiento + promesa
  completa escrita en pantalla.

### Curva de retención: qué leer en Studio (guía oficial Google + aibrify)
- **Caída en los primeros 2-3s** → problema de hook/frame 0.
- **Caída escalonada en transiciones** → faltan micro loops entre secciones.
- **Meseta seguida de recuperación** → los loops funcionan.
- **Picos >100%** → rewatch en ese timestamp: algo ahí es oro; estudiarlo y replicarlo.
- Herramienta oficial: Key Moments del reporte de retención de Studio (support.google.com/youtube/answer/9314415).

**Fuentes:** creatorlanehq.com · autotext.app · secretagents.co · shotblastmedia.co.uk ·
mangomedia.ie · allgoodtales.com · laligue89.org/CNRS (FR) · Google Support

---

## 5. Caricaturas y personajes con IA: consistencia (EN/ES) — clave para KOREX

### El problema: character drift
Cada generación parte de cero y las variaciones se acumulan. El consenso 2026: **~85% de
consistencia es el techo realista** con el mejor workflow; no existe el 100%.

### Los 3 niveles que hay que bloquear (la mayoría solo bloquea el primero)
1. **Identidad** — cara/cuerpo reconocible.
2. **Estilo** — el rendering no puede derivar entre escenas (nuestro `HIDDENFACTS_STYLE` fijo ya
   resuelve esto por diseño: el estilo es constante de código, no output del modelo).
3. **Atributos** — detalles fijos (cicatriz, gafas, chaqueta) que se leen como "él".

### Métodos comparados (de menor a mayor esfuerzo)
| Método | Cómo | Esfuerzo | Consistencia |
|---|---|---|---|
| Referencia de personaje (img2img) | 1 imagen maestra como referencia en cada generación | Bajo | Alta |
| Turnaround sheet | vistas front/lado/back/¾ como referencias multi-ángulo | Bajo-medio | Alta |
| Prompt congelado + seed | bloque de identidad byte-por-byte idéntico | Bajo | Media |
| **LoRA entrenado** (15-50 imágenes) | modelo pequeño custom del personaje | Alto | Muy alta |
| Face swap post-hoc | generar libre y cambiar la cara después | Medio | Alta (solo cara) |

### El workflow de 4 pasos (consenso)
1. **Imagen héroe** — close-up ¾ bien iluminado hasta conseguir LA cara. Es la referencia maestra.
2. **Bloque de identidad congelado** — descripción fija que NUNCA se reedita; solo cambia la línea
   de escena. (Es exactamente el patrón de nuestras `CHARACTER_PLATE` en pipeline.py.)
3. **Referencia adjunta en cada generación** — la identidad la aporta la imagen, no el texto.
4. **Curar y re-anclar** — de cada lote quedarse con la más cercana; si deriva, la mejor imagen
   reciente se vuelve la nueva referencia.

### Dónde se rompe (para evitarlo en el pipeline)
- Ángulos extremos y perfiles completos → mantener ¾ o frontal hasta "bloquear" el personaje.
- Caras pequeñas (planos generales) → generar close-ups primero, re-usarlos como referencia.
- Mezclar estilos en un mismo set → jamás.
- Reescribir la línea de identidad → cada cambio de palabra es una oportunidad de cambiar la cara.

**Conexión con KOREX:** nuestro flujo ya hace lo esencial (Flow es el único generador con imagen de
referencia → placas de personaje → `kx_cast.py` cachea poses de por vida). Las mejoras que sugiere
la investigación: (a) **turnaround sheets multi-ángulo** por personaje para planos que no sean ¾;
(b) evaluar un **LoRA por personaje** (ComfyUI ya está montado en `tools/comfyui`) si un personaje
se vuelve recurrente; (c) el paso de **re-anclaje**: hoy `kx_cast` cachea la placa original para
siempre — la literatura sugiere re-anclar en la MEJOR salida reciente.

**Fuentes:** flick.art (comparativa 5 métodos) · ud.com.hk (workflow 4 pasos) ·
iprofesional.com (ES) · renderforest/capcut/animaker (herramientas ES todo-en-uno)

---

## 6. Marketing para canales faceless (EN/ES)

### Lo que distingue al canal que escala del que muere
- **Nicho estrecho con intención, no amplio por vibras.** Los que empiezan amplio + guiones
  genéricos de IA mueren. Un nicho, un espectador ideal, un formato, un SOP.
- **Automatización controlada, no autopiloto:** IA para ideación/borradores/voz/visuales; humano
  (o QA automático estricto) para selección de tema, hook, hechos y especificidad visual.
  → Nuestro `korex_qa.py` + guardarraíles de `youtube_api.py` son exactamente esto.
- **Estandarizar antes de escalar:** una voz, un brand kit, un preset de export, 3 plantillas de
  prompt antes de 30 videos. Batch solo DESPUÉS de bloquear el sistema.
- **Medir como operador, no como creador:** trackear tema, ángulo de título, variante de intro,
  AVD y turnaround por video. → Ya lo hace `track_video.py` + `performance_report.py`; la
  literatura lo confirma como LA diferencia entre "experimento de contenido" y "negocio".
- **Branding sin rostro:** nombre de marca (no personal), logo limpio de alto contraste para
  móvil, About con posicionamiento en la primera línea. Bonus: un canal "desbranded" es un activo
  vendible.
- **Errores que matan:** contenido IA copy-paste (riesgo de desmonetización 2026), clips con
  copyright, cero branding, subidas inconsistentes, ignorar analytics.
- **RPM por nicho (benchmarks 2026):** finanzas $15-45 CPM, IA/tech $8-20, motivación $6-15,
  historia/entretenimiento menor pero con volumen y longevidad (evergreen por búsqueda).

**Fuentes:** chillframe.com · saturaai.com · outlierkit.com (B) · sidehustlemastery.com ·
techymint.in · upstream.so · scriptdrop.ai

---

## 7. Síntesis: las 10 reglas accionables para ESTE proyecto

1. **Satisfacción > watch time:** rewatch, compartidos y sesión continuada son el input #1 de 2026.
   Nuestro loop léxico+visual ya ataca rewatch; falta atacar **compartidos** (ver investigación
   propuesta #3 abajo).
2. **El hook nombra el hueco específico** (Loewenstein): no "esto te va a sorprender" sino el dato
   concreto que falta. Escribir 3 variantes por guion SIEMPRE.
3. **Todo loop es deuda:** solo se abre lo que se paga en el mismo video. Ya validado por nuestro
   dato del loop 3.76 vs 0.95.
4. **Regla del tres como motor de giro:** dos elementos que establecen patrón + el tercero que
   rompe. Aplicable al giro final de cada Short histórico y a los remates gamer.
5. **Humor = violación benigna con distancia segura:** reírse hacia arriba (tryhard, whale,
   sistemas), nunca hacia abajo sin complicidad. El remate mejor va al final del bloque.
6. **Remate cada 10-15s como pattern interrupt emocional:** alternar tensión narrativa y
   recompensa cómica mantiene la curva plana.
7. **Personaje con 3 bloqueos:** identidad + estilo + atributos; imagen maestra, bloque congelado,
   curación con re-anclaje. Siguiente nivel: turnaround sheets y LoRA por personaje recurrente.
8. **Cada frase necesita imagen que duplique, no que repita** (`not_visible` ya lo codifica).
9. **Operador, no creador:** decisiones por datos de cohorte cada 7-14 días, no por intuición.
   Nuestro `performance_report.py` es la herramienta; hay que mirarlo con esa cadencia.
10. **Consistencia temática como señal:** el topic clustering de la fase 3 premia canales
    coherentes. Resistir la tentación de saltar de nicho.

---

## 8. Investigaciones profundas RECOMENDADAS (siguientes pasos)

Ordenadas por impacto esperado en el proyecto:

1. **Psicología del compartir ("por qué la gente comparte")** — Jonah Berger (STEPPS: Social
   Currency, Triggers, Emotion, Public, Practical Value, Stories). Los compartidos son la señal
   con más peso 2026 y es la que menos atacamos. Investigar qué hace compartible un Short
   histórico/gamer y codificarlo como regla en `SCRIPT_PROMPT`.
2. **Sound design y retención** — cómo la música/SFX afectan la curva (ducking, stingers,
   silencios estratégicos). Tenemos `rhythmic_sfx.py` y SFX por mood; falta evidencia de QUÉ
   patrones sonoros retienen (tempo, entradas, drops).
3. **Análisis de outliers propios** — estudio sistemático de los 10 videos con mejor y peor
   retención del canal (con `retencion_mindcheckpoint.json` + Studio): qué tienen en común los
   primeros 3 segundos de los ganadores. Es investigación con datos PROPIOS, vale 10× más que
   cualquier benchmark externo.
4. **Localización del humor LATAM vs España vs US** — la BVT dice que lo "benigno" depende de
   cultura y distancia social. Qué referentes, modismos y targets cómicos funcionan por región
   (relevante si ImPixxel vuelve o si HiddenFacts saca versión ES).
5. **Miniaturas para Shorts 2026** — tenemos `MINIATURAS.md`; actualizarlo: el rol de la miniatura
   cambió (Test & Compare nativo en Studio, feed vs búsqueda).
6. **Voz y TTS emocional** — benchmarks 2026 de retención por tipo de voz (IA con respiraciones/
   pausas vs humana); cuándo conviene voz humana clonada (ya tenemos Chatterbox/Qwen en `tools/`).
7. **Series y lore de personajes** — cómo las series con personajes recurrentes construyen
   "return visits within 7 days" (señal nueva de ranking). Directamente aplicable a KOREX y Skick.
8. **Comentarios como fuel del algoritmo** — estrategia de preguntas A/B (ya usamos
   `post_question_comment.py`) + qué tipo de pregunta genera más hilos según la literatura de
   engagement.

---

## Fuentes principales consultadas (por idioma)

**EN:** quso.ai, outlierkit.com, socialync.io, kompozy.io, seoalgorithmrecovery.com, aibrify.com,
prepublish.ai, storyflow.so, sumera.io, stratboost.ai, channel.farm, creatorlanehq.com,
autotext.app, secretagents.co, shotblastmedia.co.uk, mangomedia.ie, allgoodtales.com, flick.art,
ud.com.hk, chillframe.com, saturaai.com, sidehustlemastery.com, upstream.so, scriptdrop.ai,
theincomeinformer.com, thecriticalcomic.com, psychotricks.com, PMC6593112 (Kant & Norman),
Yale Law School (Laura Little), Clemson CI, philosophyofhumor.net

**ES:** goviral.es, go-viral.app/es, lenostube.com, short.now/es, panconpollo.com,
creaciondigital.website, willcodex.com, achalay.net, cursosdeguion.com, tesis doctoral UA
(Aliaga Aguza), UANL eprints, iprofesional.com, renderforest.es, capcut.com/es-es, animaker.es

**PT:** schedulala.com/pt (análisis de 500+ Shorts virales con casos de estudio)

**FR:** laligue89.org / CNRS — Le Journal (Yves Citton, "Pour une écologie de l'attention";
dossier "Dopamine: la course à l'attention", Réseau Canopé)

**Académicas (humor):** McGraw & Warren (2010) "Benign Violations: Making Immoral Behavior Funny";
Raskin (1985) Semantic Script Theory; Attardo & Raskin (1991) General Theory of Verbal Humor;
Loewenstein (1994) Information-Gap Theory; Zeigarnik (1927).
