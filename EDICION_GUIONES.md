# Investigación: Edición de video y guiones dopaminérgicos

Para los canales del proyecto (Skick / finanzas / lore). Julio 2026.
Complementa a ROADMAP.md (algoritmo y competencia) y HUMOR_GAMER.md (contenido cómico).

**Marcas:** ✅ = respaldado por dato/estudio citable. ⚠️ = práctica establecida de la
industria sin estudio único citable (consenso de practicantes).

---

## PARTE 1 — EDICIÓN PARA MÁXIMO ENGAGEMENT

### 1.1 El principio rector (el dato que ordena todo lo demás)

Estudios de eye-tracking (2024-2025) ✅ muestran que la retención en video corto colapsa
entre el segundo 1.5 y el 3.5 si el ojo no tiene "una siguiente cosa" que mirar. Todo lo
demás de esta sección son formas distintas de darle al ojo esa siguiente cosa.

Los umbrales que hay que ganar (algoritmo Shorts 2026 ✅): retención >65% en videos <30s,
>50% en 30-60s; la decisión de swipe ocurre en el primer segundo; solo cuentan vistas
completas y rewatches.

### 1.2 Cortes y transiciones

| Técnica | Qué es | Cuándo usarla | Métrica/regla |
|---|---|---|---|
| Beat visual constante ✅ | Algo cambia en pantalla cada 1.5-2.5s | Siempre en Shorts | Nunca >3 frases el mismo encuadre |
| Jump cut ⚠️ | Cortar los espacios muertos dentro de una misma toma | Narración hablada | Cero pausas >0.4s |
| Corte en el beat ⚠️ | El cambio de plano cae EXACTO en el golpe del guion | Punchlines, revelaciones | El corte ES parte del chiste |
| Zoom punch ⚠️ | Zoom brusco de 5-10% en un frame | Énfasis, sorpresa, giro | 1-3 por video; se devalúa si se abusa |
| Whip pan / barrido ⚠️ | Transición veloz con desenfoque de movimiento | Cambio de escena en comedia | Marca "cambio de acto" |
| Ken Burns (zoom lento) ⚠️ | Movimiento sutil sobre imagen fija | Todo clip estático (ya en nuestro pipeline) | Alternar in/out entre clips |
| J-cut / L-cut ⚠️ | El audio de la siguiente escena entra antes que su imagen (o al revés) | Fluidez narrativa | Evita la sensación de "diapositivas" |
| Crash de ritmo ✅ | Frenar todo de golpe (quietud tras caos) | Justo antes del payoff/CTA | El contraste señala "presta atención AHORA" |

El modelo MrBeast documentado ✅: ritmo variable (no velocidad constante — aceleraciones y
frenadas deliberadas), mini-recompensas y cliffhangers cada 30-60s, y cero momentos
muertos: toda espera se cubre con overlay de texto, reacción, imagen o SFX. Su equipo
analiza gráficas de retención segundo a segundo — la lección replicable no es el
presupuesto, es el hábito de mirar la gráfica de retención y editar contra ella.

### 1.3 Texto en pantalla y gráficos

- **Subtítulos word-by-word** ✅: crean un punto de fijación nuevo cada 250-400ms y fuerzan
  a leer al ritmo del narrador — el único ritmo donde el punchline cae bien. Superan a los
  subtítulos estáticos en retención. (Ya implementado en el pipeline.)
- **Palabra clave resaltada en color** ⚠️: una palabra por bloque en amarillo/verde dirige
  el ojo al concepto. (Pendiente 4.4 del ROADMAP.)
- **Mute-proof** ✅: 85%+ de las vistas en social empiezan sin sonido — el primer frame debe
  contar el chiste/promesa en 3-6 palabras grandes.
- **Números y datos como gráfico, no como palabra** ✅: 86% de los motion graphics
  financieros que convierten abstraen las cifras en tipografía cinética. Un "$1,847"
  gigante en pantalla vale más que decirlo. (Pendiente 4.2 del ROADMAP.)
- **Regla de sobriedad** ⚠️: máximo 2 elementos animados simultáneos (subtítulo + 1 gráfico).
  Más = ruido que compite con el punchline.

### 1.4 Audio

| Elemento | Práctica | Detalle |
|---|---|---|
| Loudness ✅ | Normalizar a -14 LUFS | Estándar YouTube; en FFmpeg: `loudnorm=I=-14:TP=-1.5` |
| Música de fondo ⚠️ | -20 a -24dB bajo la voz, con ducking | Sostiene energía en pausas; NO trending (bonus de audio original 2026 ✅) |
| SFX como puntuación ✅ | Whoosh en transición, pop en texto, "ding" en dato | El swoosh/pop funciona como marcador de recompensa; 4-8 por Short |
| Silencio estratégico ⚠️ | Cortar TODA la música 0.5s antes del punchline | El silencio es el subrayado más barato que existe |
| Voz ✅ | Consistencia vocal entre videos = +58% retención en faceless | Una voz por canal, siempre la misma |
| Ritmo de voz ⚠️ | +8-15% de velocidad sobre habla natural | Percepción de energía sin perder claridad |

### 1.5 Estructura de planos (vertical 9:16)

- Duración de plano: 1.5-3s en comedia/entretenimiento; hasta 4-5s en educativo cuando el
  texto en pantalla está trabajando ⚠️.
- Composición: sujeto en el tercio superior-central; subtítulos al 65-70% de altura (nunca
  abajo: la UI de la plataforma los tapa); márgenes seguros ~120px abajo, ~200px derecha
  (botones de like/share) ⚠️.
- Variación: alternar plano general → medio → detalle. En nuestro pipeline con imágenes:
  alternar composiciones en los prompts (personaje entero / cara / objeto) ⚠️.
- El primer frame es el thumbnail del Short: diseñarlo como tal (hook text + imagen más
  fuerte) ✅.

### 1.6 Herramientas

| Nivel | Herramienta | Para qué |
|---|---|---|
| Gratis | **CapCut** | El estándar de facto en shorts; auto-captions, plantillas, efectos. Rápido pero: es de ByteDance, marca de agua en algunas funciones pro |
| Gratis | **DaVinci Resolve** | Calidad profesional real gratis; curva de aprendizaje media; color grading superior |
| Gratis | **FFmpeg** (nuestro pipeline) | Automatización total; sin UI; ya hace el 90% de esta lista solo |
| Gratis | **Audacity** | Limpieza de voz puntual |
| Pago | **Premiere Pro + After Effects** | Estándar de industria; After Effects para motion graphics serios |
| Pago | **DaVinci Studio** ($295 única vez) | Todo Resolve + efectos de ruido/deflicker |

**Nuestro caso:** el pipeline FFmpeg ya automatiza cortes, subtítulos, zoom y audio. CapCut
o Resolve solo se justifican para videos "hero" puntuales con edición manual fina.

### 1.7 Referentes que dominan estas técnicas

- **MrBeast** ✅ — el canon del ritmo variable y la retención medida al segundo (long-form).
- **Alan Becker** ✅ (Animator vs. Animation) — **el referente directo para Skick**: stick
  figures + gaming + comedia física sin diálogo, 25M+ subs. Estudiar cómo comunica emoción
  con 6 líneas y 2 puntos por cara, y cómo su timing cómico es 100% visual.
- **Zack D. Films** ⚠️ — shorts educativos con una imagen fuerte por frase; el modelo de
  "cada oración tiene su visual".
- **penguinz0 / Cr1TiKaL** ⚠️ — deadpan gamer: la entrega seca como estilo. Referente de
  tono para guiones de Skick.
- **Ibai / ElRubius** ⚠️ — el registro del humor gamer en español: velocidad, exageración
  cariñosa, vocabulario regional sin filtro.

---

## PARTE 2 — GUIONES DOPAMINÉRGICOS

### 2.1 La neurociencia en 4 piezas (lo que de verdad está detrás del "dopamine editing")

1. **La dopamina responde a la anticipación, no a la recompensa** ✅ (Schultz, error de
   predicción de recompensa): el pico dopaminérgico ocurre ante la *señal* de recompensa
   posible, y es máximo cuando la recompensa es *incierta*. Traducción: la promesa abierta
   retiene más que la entrega. Por eso el hook es una pregunta, no una respuesta.
2. **Recompensa variable** ✅ (Skinner): recompensas impredecibles en tiempo y tamaño
   generan el engagement más persistente (es la mecánica de las slot machines — y del
   feed). Traducción: los golpes del guion no deben ser equidistantes ni del mismo tamaño;
   alternar chiste pequeño / chiste grande / giro.
3. **La brecha de curiosidad** ✅ (Loewenstein, information gap theory, 1994): la curiosidad
   es el dolor de una brecha entre lo que sé y lo que quiero saber. Se activa con
   información *parcial*: "hay 3 errores que…" duele más que "te explico los errores".
4. **Tensión → resolución en micro-ciclos** ⚠️: cada 5-8 segundos, abrir una micro-tensión
   y resolverla (o escalarla). El video completo es una cadena de estos ciclos, no un solo
   arco.

### 2.2 El hook (el primer segundo, no los primeros 3)

La decisión de swipe es refleja y ocurre a ~1s ✅; los mejores Shorts retienen 70-90% en el
primer segundo ✅. Plantillas probadas (de mayor a menor agresividad):

1. **Resultado primero**: mostrar el final ("así terminé baneado") y rebobinar.
2. **Afirmación audaz**: "Yasuo mató a su propio maestro." (nuestro video — funciona).
3. **POV**: "POV: dijiste una partida más." — contrato instantáneo con el espectador;
   ideal para humor de identificación (Skick).
4. **Pregunta directa**: solo si la respuesta duele ("¿por qué sigues siendo Plata?").
5. **Patrón interrumpido**: empezar a mitad de la acción, sin contexto — el cerebro odia
   entrar tarde y se queda a reconstruir.

Reglas: primera frase ≤8 palabras; el primer frame la muestra en texto grande; nada de
contexto previo ("hola chicos" es asesinato de retención).

### 2.3 Ritmo narrativo: cuándo acelerar y cuándo frenar

- **Acelerar**: en el setup (información conocida), en las listas, en la escalada. La
  velocidad comunica "esto ya lo entiendes, vamos a lo bueno".
- **Frenar**: justo antes del giro o punchline (medio segundo de aire), y en EL dato/gag
  central del video. Frenar una sola vez por video — el freno es un recurso escaso.
- **Micro-loops cada 5-8s** ✅: "pero aquí viene lo peor…", "y entonces…" — resetean el
  reloj de atención antes de cada caída.
- **Terminar EN el payoff** ✅: cero despedida, cero "so yeah". La última frase idealmente
  es un eco del hook (loop → rewatch → la señal #1 del algoritmo 2026).

### 2.4 CTAs que no estorban

El dato clave del 2026 ✅: los comentarios pesan más que las suscripciones en el feed de
Shorts, y en Reels el "sends per reach" (compartidos por DM) es la métrica reina.

| CTA | Forma | Por qué funciona |
|---|---|---|
| Pregunta polarizante ⚠️ | "¿Team ranked o team casual?" | Genera comentarios sin pedir comentarios |
| Etiqueta implícita ⚠️ | "Mándaselo al amigo que hace esto" | Diseña el video como mensaje personal (la métrica de Reels) |
| El loop ✅ | El final conecta con el inicio | El mejor CTA de Shorts es el rewatch, y no se pide: se construye |
| Identificación ⚠️ | "Si te dolió, ya sabes por qué" | La autoselección del espectador hace el trabajo |
| **Nunca** ⚠️ | "Dale like y suscríbete" a mitad del video | Interrumpe el ciclo de tensión; en Shorts es veneno para retención |

### 2.5 Diferencias por plataforma ✅

| | TikTok | YouTube Shorts | Instagram Reels |
|---|---|---|---|
| Algoritmo | Interest graph (intereses) | Búsqueda + recomendación híbrida | Social graph (amigos) |
| Qué premia | Tendencia, native feel, caos controlado | Claridad, serialidad, contenido buscable | "Sends per reach" — que se comparta por DM |
| Vida del video | Días | **Semanas/meses (aparece en Google)** | Días |
| Sweet spot duración | 15-35s tolera más | 30-45s | 20-35s |
| Implicación para nosotros | Reusar el video tal cual; el humor gamer es nativo aquí | Nuestra base: series + SEO ("lore de Yasuo") | Diseñar para "esto ERES tú" → DM |

El mismo video funciona en las tres si se diseña para la más exigente (Shorts) con alma de
compartible (Reels). El humor de identificación de Skick es *exactamente* contenido de DM.

### 2.6 Ejemplo desglosado: nuestro guion "Una partida más"

```
[HOOK ≤1s]      "Son las once de la noche."         ← contexto mínimo, promesa implícita
[SETUP]         "Dices: una partida más."            ← el contrato POV: esto eres tú
[GOLPE 1]       "Tu equipo pierde 0 a 5."            ← primera recompensa (risa de dolor)
[GOLPE 2]       "Alguien te culpa por el ping."      ← variable: golpe más chico, más ácido
[MICRO-LOOP]    "Lo dices otra vez. Una partida más." ← re-hook, escalada
[GIRO]          "De repente son las 3 de la mañana."  ← salto temporal = sorpresa
[CLÍMAX]        "Tu mamá abre la puerta. Cierras la   ← el golpe grande (recompensa mayor,
                laptop como un criminal."               timing: aquí va el freno + SFX)
[REMATE]        "'Estaba durmiendo', dices, a todo    ← absurdo confesional
                volumen, bien despierto."
[LOOP]          "Cinco minutos después. Una partida   ← eco del hook → rewatch
                más."
```

Estructura subyacente: hook → 2 golpes de tamaño variable → re-hook → giro → clímax →
remate → loop. Es replicable para cualquier arquetipo del catálogo de HUMOR_GAMER.md.

---

## PARTE 3 — INTEGRACIÓN EDICIÓN + GUION

### 3.1 El principio: el corte es parte del chiste

El guion define DÓNDE están los picos; la edición los hace FÍSICOS. La sincronización
concreta:

| Momento del guion | Acción de edición |
|---|---|
| Hook | Imagen más fuerte del video + texto grande + primer beat de música |
| Golpe cómico | Corte de plano EXACTO en la palabra del golpe + SFX |
| Micro-loop / re-hook | Cambio de escena (whip pan o corte) |
| Giro | Zoom punch + cambio de música o silencio |
| Clímax | El freno: medio segundo de quietud ANTES, luego el golpe con todo |
| Remate | Plano nuevo, ritmo seco |
| Loop final | Cortar EN el payoff; idealmente el último frame rima con el primero |

En nuestro pipeline esto se traduce en una mejora concreta pendiente (ROADMAP 5.1): cortar
los clips en los límites de frase usando los timestamps de palabra que ya tenemos, en vez
de duración fija. Es la mejora de integración de mayor impacto disponible.

### 3.2 Mapa de energía (herramienta práctica)

Antes de editar (o de generar), marcar el guion con niveles de energía 1-5 por frase.
Regla: la curva debe variar (dopamina = cambio, no nivel); nunca más de 3 frases seguidas
en el mismo nivel; el 5 se usa una sola vez (el clímax); el video termina en 4-5, jamás
en 1-2 (nada de fade out suave: el final débil mata el rewatch).

### 3.3 Errores comunes que rompen la atención

1. **Intro antes del hook** ("hola, hoy vamos a ver…") — el error #1 y el más letal.
2. **Explicar el chiste después del punchline** — mata el remate y insulta al espectador.
3. **Cortes aleatorios no alineados al habla** — se siente "hecho por máquina" (nuestro
   riesgo actual con segmentos de duración fija).
4. **Música que compite con la voz** — sin ducking, la voz pierde y el viewer se va.
5. **CTA a mitad del video** — interrumpe el ciclo de tensión.
6. **El final que se apaga** — despedidas, logos, "gracias por ver": el video debe cortar
   en seco en el payoff.
7. **Sobrecarga visual** — 3+ elementos animados a la vez: el ojo no sabe dónde mirar y
   elige irse.
8. **Meme muerto como hook** — (ver HUMOR_GAMER.md): pérdida de credibilidad instantánea
   con el in-group.

### 3.4 Qué aplica a cada género nuestro

| Técnica | Skick (humor) | Finanzas (educativo) | Lore (narrativo) |
|---|---|---|---|
| Beat visual 1.5-2.5s | Sí, agresivo | Moderado (el texto trabaja) | Sí |
| Zoom punch | En cada golpe cómico | Solo en el dato central | En el giro de la historia |
| Silencio pre-punchline | Herramienta central | Rara vez | En la revelación |
| SFX cómicos | 6-8 por video | 2-3 sobrios | 3-4 atmosféricos |
| Kinetic typography de cifras | Poco | **Central** (ROADMAP 4.2) | Poco |
| Loop hook-final | Siempre | Siempre | Siempre |
| CTA de comentario polarizante | "¿Tú también o solo yo?" | "¿Team X o team Y?" | "¿De qué personaje quieres el lore?" |
