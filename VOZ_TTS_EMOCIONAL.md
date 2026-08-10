# Voz y TTS emocional: la voz como factor de retención

Investigación multiidioma — agosto 2026
Idiomas consultados: inglés, japonés (日本語), chino (中文)

> La narración es lo primero que el espectador juzga en un canal faceless: una voz monótona mata el watch time en los primeros segundos; una voz con emoción correcta sostiene la retención. Datos clave de esta investigación: **+18% de completion rate** con etiquetas de emoción (caso ElevenLabs medido en Japón) y **scroll-stop rate 1.5×** con Audio Tags en Shorts.

---

## 1. El efecto medido: emoción sí mueve la aguja (JA)

De AI PICKS Japón (junio 2026) y comparativas japonesas de TTS:

- Caso documentado: narración de video de producto con la etiqueta emocional `<excited>` de ElevenLabs vs la misma narración sin emoción → **+18% de tasa de visualización completa**.
- En Shorts (15-60 s), ElevenLabs v3 con **Audio Tags** (`[whispers]`, `[excited]`, `[laughs]`) produce una mejora de **scroll-stop rate de ~1.5×** reportada por operadores de canales automatizados japoneses.
- **Trampa frecuente: la sobre-aplicación de emoción.** Subir demasiado la intensidad genera gritos artificiales o alegría excesiva que produce rechazo. La emoción correcta en dosis medida > emoción máxima.
- Advertencia relevante: el control emocional en **japonés es aún menos preciso que en inglés** (2026); para español esperar una situación intermedia. Probar, no asumir.

## 2. Panorama de motores 2026 (JA + EN, precios de referencia)

| Motor | Precio ref. | Emoción | Idiomas | Uso ideal |
|---|---|---|---|---|
| **ElevenLabs v3** | $5-22+/mes (suscripción) | ◎ Audio Tags, clonación 30 s | 32-70+ | Narración principal con emoción |
| **OpenAI TTS** | $15/1M chars (tts-1) / $30 HD | △ limitada (instrucciones de estilo) | Multi | Volumen alto a bajo coste (~$0.12-0.30/video de 10 min) |
| **Google Cloud TTS (Chirp 3 HD)** | $16-30/1M chars (1M gratis/mes estándar) | ◯ SSML avanzado | 40+ | Versiones multiidioma del mismo video |
| **MAI-Voice-1** | $22/1M chars | ◯ control por turnos | Solo EN | Clonación rápida (120 s de muestra) |
| VOICEVOX / AivisSpeech | Gratis | Limitada | JA | Nicho japonés "yukkuri" |

Coste real para nuestro volumen: un guion de 80-120 palabras ≈ 500-800 caracteres → **OpenAI TTS sale a ~$0.01 por Short**; ElevenLabs encaja si el plan actual cubre el volumen mensual.

## 3. Los 3 parámetros que quitan lo "robot" (ZH, Tencent Cloud)

Artículo de Tencent Cloud Developer (B): el "sonido a máquina" casi nunca es culpa del modelo sino de 3 parámetros mal puestos:

1. **Selección de timbre**: el timbre debe casar con el contenido (voz dulce para hard-tech destruye credibilidad; voz grave para lifestyle suena paródica). **Y nunca cambiar de voz dentro del mismo canal**: la audiencia cree que "cambió el dueño del canal". La voz ES la marca.
2. **Intensidad emocional**: narración neutral vs alta emoción son productos distintos. Pregunta de diseño por guion: *¿este video tiene emoción?* Si tiene (sorpresa, giro, indignación), usar voz emocional; si es dato plano, neutral bien ejecutada.
3. **Ritmo y pausas (断句)**: el TTS no conoce tu contenido; hay que "enseñarle" con puntuación, pausas explícitas y diccionario de pronunciación (nombres propios, números, extranjerismos). Las pausas de 0.2-0.5 s entre bloques temáticos conectan con el sound design (`SOUND_DESIGN_RETENCION.md`).

Valor de marca medido en China: **clonar una voz propia y usarla siempre sube completion y conversión a follow** porque "el público recuerda esa voz" — la voz como activo de IP (conecta con `SERIES_LORE_PERSONAJES.md`).

## 4. Monetización y política YouTube 2025-2026 (EN)

- **Las voces AI están permitidas y monetizan** si el contenido es original, aporta valor y hay supervisión editorial humana.
- La actualización de julio 2025 renombró "repetitious content" a **"inauthentic content"**: el objetivo son plantillas masivas indistinguibles entre sí, no el uso de TTS como herramienta.
- **Riesgo real para nuestro pipeline**: N videos con estructura idéntica, misma voz, mismo formato y mínima variación = patrón de "AI slop". La defensa es variación editorial real (temas, estructuras, giros), no cosmética.
- **Clonar la voz de otra persona** = "medios alterados" → etiqueta de divulgación obligatoria; riesgo de desmonetización si se omite. Clonar nuestra propia voz: sin problema.

## 5. Regla de los 7 segundos y la voz (EN)

El "7 second rule": si el espectador se va en los primeros 7 segundos, el algoritmo reduce recomendaciones. La voz es un componente directo de ese juicio inicial: **la primera frase debe entrar con energía/contenido, no con saludo ni rampa**. Coherente con nuestras curvas propias (caída decisiva en el 14% inicial, `ANALISIS_OUTLIERS_PROPIOS.md`).

---

## Aplicación concreta al pipeline

1. **Una voz por canal, para siempre**: fijar el voice ID por canal (HiddenFacts EN, ImPixxel ES) en configuración; tratar el cambio de voz como cambio de marca (requiere decisión explícita).
2. **Guiones con marcas de entrega**: añadir al formato de guion campos opcionales por frase: `emocion` (neutral/sorpresa/énfasis) y `pausa_despues` (0.2-0.5 s en cambios de bloque). Mapearlos a Audio Tags (ElevenLabs) o instrucciones de estilo/SSML según el motor activo.
3. **Dosis de emoción**: máximo 2-3 puntos emocionales marcados por Short; el resto neutral. Evita el efecto "grito artificial".
4. **Diccionario de pronunciación**: lista por canal de nombres propios/números/siglas frecuentes con su pronunciación corregida (Fonética SSML o pronunciation editor).
5. **Test A/B pendiente**: mismo guion, voz neutral vs voz con 2 puntos emocionales → comparar retención 0-7 s y completion en la próxima tanda (validar el +18% externo contra nuestros datos).
6. **Compliance**: nunca clonar voces ajenas; si se clona una voz propia en el futuro, activar la etiqueta de divulgación de contenido alterado donde aplique.

## Fuentes consultadas

- AI PICKS (Japón) — glosario Emotional TTS: caso ElevenLabs `<excited>` +18% completion; costes $4-30/1M chars; advertencia de sobre-emoción y precisión JA — JA
- oishillc.jp — comparativa 5 motores TTS (mayo 2026): tabla precios/latencia/emoción; Audio Tags y scroll-stop 1.5× en Shorts — JA
- Tencent Cloud Developer — "3 parámetros que quitan lo robot": timbre, intensidad emocional, ritmo/断句; voz clonada como activo de marca (25 元/timbre) — ZH
- narrationbox.com — guía de voz AI para YouTube: política de monetización 2025 ("inauthentic content"), regla de 7 segundos — EN
- reelforgeai.io — comparativa ElevenLabs / OpenAI TTS / Google Cloud TTS con precios 2026 — EN
- elevenlabs.io — biblioteca de voces emocionales (moody) — ZH/EN
