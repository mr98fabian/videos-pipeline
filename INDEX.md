# INDEX — el mapa de los 48 documentos

**Para qué existe (12 ago 2026):** había 48 archivos `.md` en la raíz y **cero
enlaces entre ellos**. Sin índice, cada sesión abre los tres que recuerda y se
pierde los otros cuarenta y cinco. El coste no es teórico, pasó el 12 de agosto:

- Se cambiaron los títulos a pregunta por una memoria vieja, y horas después los
  datos propios demostraron lo contrario (ver [[ESTUDIO_REFERENTES]]).
- Se escribió [[INVESTIGACION_ALGORITMO_LONGFORM]] sin saber que ya existía
  [[INVESTIGACION_ALGORITMO_2026]].
- Se estudiaron dos canales referentes sin consultar [[INVESTIGACION_MACK]], que
  era exactamente el mismo trabajo hecho el 8 de julio.

**Cómo se usa:** se entra por aquí, se salta al grupo del tema y **solo** se
abren los dos o tres que aplican. Este archivo se actualiza cuando nace un
documento nuevo; un `.md` que no esté enlazado aquí es un archivo que nadie va a
leer nunca.

---

## 0. Antes de tocar nada

| Documento | Cuándo leerlo |
|---|---|
| [[ESTADO_SESION]] | **Siempre, lo primero.** Qué se hizo, qué quedó a medias, qué sigue. Dos sesiones en paralelo escriben aquí |
| [[CLAUDE]] | Las reglas del repo y del pipeline. Es el esquema del agente |
| [[README]] | Qué es el proyecto y los comandos base |
| [[ROADMAP]] | Mapa de mejoras pendientes del canal |
| [[HISTORIAL_MEJORAS]] | Bitácora investigación → cambio → dónde se publicó. **Se escribe aquí cada vez que un cambio afecta al vídeo** |

## 1. KOREX — el canal activo (Tadeo)

| Documento | Cuándo leerlo |
|---|---|
| [[BRANDING_KOREX]] | Identidad del canal, voz oficial, reglas de marca |
| [[IDIOMA_KOREX]] | **El diccionario mapache y la firma de título.** Obligatorio antes de escribir un guion |
| [[ESTUDIO_REFERENTES]] | Los Ecomonos y Zenn medidos con la API. **Manda sobre cualquier consejo genérico de títulos** |
| [[STORYBOARD_KOREX]] | Cómo se planifica cada plano: 絵コンテ, sincronía, jerarquía de planos |
| [[PERSONAJE_MODEL_SHEET]] | Cómo se mantiene a Tadeo idéntico. Leer antes de generar cualquier lámina |
| [[SERIES_PELAR_CABLE]] | La serie de episodios en marcha |
| [[STORYBOARD_DOS_SUELDOS]] | El storyboard del primer largo: 104 planos sobre 30 imágenes |
| [[INVESTIGACION_COSTE_ANIMACION]] | Qué cuesta animar y por qué solo se anima la apertura |

## 2. Cómo decide YouTube (distribución)

| Documento | Cuándo leerlo |
|---|---|
| [[INVESTIGACION_ALGORITMO_LONGFORM]] | **Formato largo.** Señales 2026, el dato de los 2,5 min, clickbait penalizado |
| [[INVESTIGACION_ALGORITMO_2026]] | **Shorts.** Umbrales de retención y técnicas a probar |
| [[PALANCAS_2026]] | Título+miniatura como paquete, voz, puente Shorts→largo, RPM por mercado |
| [[POLITICAS_YOUTUBE]] | Lo que puede desmonetizar o tumbar el canal |
| [[MINIATURAS_SHORTS_2026]] | Dónde importa la miniatura y dónde es invisible |
| [[MINIATURAS]] | Miniaturas de gameplay/LoL — contexto ImPixxel, **no aplica a KOREX** |

## 3. Guion y retención

| Documento | Cuándo leerlo |
|---|---|
| [[RETENTION_CHECKLIST]] | Las reglas duras de guion. El paso 0 (outliers) vive aquí |
| [[INVESTIGACION_GUION_BUCLES]] | Bucles de curiosidad: 3-5 en tres niveles, y por qué la promesa sin pago frustra |
| [[PSICOLOGIA_SEGUNDO_0]] | Qué dispara la curiosidad en el primer segundo |
| [[PLAN_SEGUNDO_6]] | La fuga medida entre el segundo 5,5 y el 10 |
| [[RETENCION_PSICOLOGIA]] | Psicología de la retención en formato vertical |
| [[EDICION_GUIONES]] | Edición, ritmo dopaminérgico y redundancia dentro del guion (§4, lint con `guion_lint.py`) |
| [[giros_ganadores]] | Catálogo de ESTRUCTURAS de giro (G1-G6), no de temas |
| [[PROMPT_MAESTRO]] | Cómo y por qué HiddenFacts escribe sus guiones |
| [[FORMATOS_A_PROBAR]] | Los 20 formatos pendientes de probar |

## 4. Audio

| Documento | Cuándo leerlo |
|---|---|
| [[VOZ_TTS_EMOCIONAL]] | La voz como factor de retención |
| [[SOUND_DESIGN_RETENCION]] | Ducking, SFX, silencios, LUFS |

## 5. Psicología del espectador

| Documento | Cuándo leerlo |
|---|---|
| [[PSICOLOGIA_COMPARTIR]] | Por qué se reenvía un vídeo (STEPPS, emociones de alta activación) |
| [[COMENTARIOS_ENGAGEMENT]] | Comentarios como combustible; CTA de elección |
| [[CONTENIDO_POLARIZANTE]] | Contenido emocional y viralidad, con sus riesgos |
| [[SERIES_LORE_PERSONAJES]] | Convertir un canal faceless en IP de personaje |
| [[HUMOR_LOCALIZACION_LATAM]] | Qué hace gracia en LATAM, España y EE. UU. |

## 6. Nuestros datos medidos (mandan sobre todo lo demás)

| Documento | Cuándo leerlo |
|---|---|
| [[ANALISIS_OUTLIERS_PROPIOS]] | Los 51 vídeos medidos. Sweet spot de palabras, mediana de shares |
| [[ESTUDIO_REFERENTES]] | Incluye los datos reales de KOREX por vídeo (vistas y retención) |
| [[INVESTIGACION_MACK]] | @MackExplains7 verificado a mano — canal referente |
| [[CREATOR_RANT_IDEAS]] | Ideas de la fuente validada (John Scott) |
| [[FEEDBACK_DIGEST]] | Datos → prompt, digest automático |
| [[PROGRESO_CANAL]] | Histórico de auditorías |

## 7. Otros canales (pausados o secundarios)

| Documento | Cuándo leerlo |
|---|---|
| [[MEJORAS_CANAL]] · [[CANAL_SETUP]] · [[PROGRESO_CANAL]] | ImPixxel |
| [[FORMATOS_IMPIXXEL]] · [[GUIONES_SKICK]] · [[IMPIXXEL_HOOK_GUIDE]] · [[HUMOR_GAMER]] | ImPixxel, canal **pausado** |
| [[GAMEPLAY_FORMATOS]] | Pilar de gameplay |
| [[MEJORAS_CODIGO]] | Deuda técnica conocida |
| [[INVESTIGACION_MULTIIDIOMA_2026]] | Síntesis madre del corpus del 9 ago |

---

## Conflictos conocidos (léelos antes de decidir)

Esto es lo que más falta hacía. Cuando dos documentos se contradicen, **gana el
que tiene datos medidos**, y aquí queda escrito cuál es:

| Tema | Dice A | Dice B | Gana |
|---|---|---|---|
| Títulos: ¿pregunta o afirmación? | memoria vieja y regla 9: pregunta | [[ESTUDIO_REFERENTES]]: 4% de preguntas en el referente, y nuestro ganador es una promesa | **B** |
| Duración de plano en largo | [[INVESTIGACION_ALGORITMO_LONGFORM]]: 10-12 s | [[STORYBOARD_KOREX]]: 6-8 s (絵コンテ) | **B** |
| Velocidad de narración | blogs: 160-190 wpm | [[ESTUDIO_REFERENTES]]: el comparable va a 144-153 | **B** |
| Subtítulos quemados en largo | principio de redundancia: restan | Zenn los usa con 7,8 M | **B**, con matiz en [[STORYBOARD_KOREX]] |
| Música de fondo | [[SOUND_DESIGN_RETENCION]]: parámetros de ducking | [[PALANCAS_2026]]: no hay efecto medido en retención | Ambos: es marca, no palanca |
| Miniaturas | [[MINIATURAS_SHORTS_2026]]: irrelevantes en el feed de Shorts | [[PALANCAS_2026]]: decisivas en largo | Depende del formato |

**Regla de oro del proyecto:** los datos propios ganan a cualquier benchmark
externo. Si un documento externo contradice [[ANALISIS_OUTLIERS_PROPIOS]] o los
números de [[ESTUDIO_REFERENTES]], se ignora el externo.
