# Prompt maestro — cómo y por qué HiddenFacts escribe sus guiones

Versión legible de `SCRIPT_PROMPT` en [pipeline.py](pipeline.py). Sirve para
consultar el criterio sin leer código.

> **Si cambia una regla en `pipeline.py`, actualizar aquí también.** El 28 jul
> 2026 este documento ya iba por delante del código: describía el ángulo
> inmersivo en 2ª persona, que no estaba escrito en el prompt. Se corrigió al
> detectarlo.

## El prompt (lo que recibe la IA)

```
Create a viral YouTube Short script about: {topic}

Context: HiddenFacts channel — hidden history, hoaxes, and espionage for a
US/English-speaking audience. Assume 50% of viewers watch on mute (subtitles
are burned in). Target 60-65 seconds of spoken content, 190-200 words.

Role: you are a scriptwriter whose Shorts consistently retain viewers past
the 3-second mark.

Voice: third person, narrating real events — never "we" or "I", and never
second-person finance-style address. EXCEPCIÓN aprobada: si el ángulo es
INMERSIVO (pone al espectador dentro de la situación de un personaje real),
usar 2ª persona todo el guion ("you eat first, every day").

Tone — THE VOICE IS A CYNICAL ARCHIVIST: deadpan, acidic, punches up at
power, never down at victims. Escala inversa a la gravedad del tema.

Instructions:
1. Open with a curiosity gap, a bold claim, or a surprising number.
2. Deliver value with the "slippery slide": second-best point first.
3. 1-2 mini re-hooks every ~15s ("but here's the part nobody mentions...").
4. Close repeating the EXACT key word/phrase from the opening hook.
5. NEVER speak a call-to-action inside the script.
6. Short punchy visual beats, one image/moment per 1-2 sentences.
7. search_terms: exactamente uno por frase, mismo orden.
8. hook_card: caption de curiosity-gap aparte, no copia de la 1ª frase.
9. title Y hook_card: SIEMPRE pregunta sin resolver, nunca afirmación.

*** PLANTILLA ÚNICA: Black Tom ***
(1) icono FAMOSO reconocible al instante
(2) consecuencia que SIGUE VISIBLE HOY
(3) loop léxico y visual (última frase repite la palabra clave del hook,
    último search_term encadena con el primero)

Si el tema no tiene un icono con huella visible hoy, buscar otro ángulo del
mismo hecho antes de escribir.
```

## Por qué existe cada regla

| Regla | Por qué | Evidencia |
|---|---|---|
| **Pregunta, no afirmación**, en título y `hook_card` | Una afirmación cierra el vacío de información en el propio título: el cerebro no tiene nada pendiente. Una pregunta lo abre y obliga a mirar para cerrarlo | Short ajeno de depredadores/campamento: 560 → 27k vistas en un día con ese patrón |
| **Ángulo inmersivo en 2ª persona** (opcional) | Pone al espectador como protagonista, no como testigo: el riesgo se siente en su cuerpo, no en el de un tercero histórico | Aprobado 28 jul 2026 sobre el mismo vídeo de referencia |
| **Icono famoso + consecuencia visible hoy** (Black Tom) | El icono ahorra presentar al personaje; la consecuencia visible le da algo que puede ir a comprobar | Único vídeo con re-watch real: ratio 3,76 → 2,89 frente a Orden 227 (0,95) y Auschwitz (0,08) |
| **Loop léxico y visual** al cierre | El corte final→inicial debe sentirse invisible, no como "empieza otro vídeo". Eso dispara el rewatch | Mismo análisis |
| **Sin CTA hablado** | "Suscríbete" es la señal de que el vídeo acaba: caída dura justo ahí, antes del final real | Medido en el canal |
| **190-200 palabras / 60-65s** | edge-tts a +8% habla ~3,15 palabras/s. Por debajo de 60s el reparto cae y el guardrail de subida lo bloquea | Medido 27 jul 2026 |
| **Sin cold-open ni cierre de franquicia** | Quedarse o scrollear se decide antes del segundo 1; cualquier segundo antes de la voz es regalado. El cierre de marca (~3,7s tras la última palabra) anuncia "se acabó" donde el loop debe ser invisible | `COLD_FRAMES = 0`, `CLOSE_TAIL = 0` |
| **Tono cínico-archivista, ácido hacia arriba** | El humor sobre la absurdidad del poder es lo que se comparte; burlarse de víctimas mata la marca | Regla de marca, sin medición numérica todavía |

## Ángulo inmersivo — cuándo usarlo

No sustituye a Black Tom, **se combina** con él.

Úsalo cuando el tema tiene un personaje real y verificable cuya situación se
puede poner en 2ª persona **sin inventar nada** — la catadora de comida de
Hitler, no "un soldado cualquiera". Si el hecho no tiene un protagonista
individual claro, 3ª persona estándar.

## Reglas relacionadas que viven en otro sitio

- Umbrales de distribución de Shorts 2026 (mínimo duro de 15s, punto dulce
  30-45s, mejor hora): `youtube_api.py`, ver `CLAUDE.md`.
- Los 2 primeros segundos del motor visual (hook en el frame 0, movimiento
  desde el frame 0): `motion_graphics/src/archivo/`, ver `CLAUDE.md`.
- El estilo visual es una constante de código (`HIDDENFACTS_STYLE`), nunca lo
  decide el modelo.
