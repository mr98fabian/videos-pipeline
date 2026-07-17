# Guiones de Skick — cómo escribir humor que identifique de verdad

Regla de decisión fijada por Fabián (13 jul 2026): **70% LoL específico / 30% gamer universal, jerga LATAM neutra gamer** (tiltear, feedear, manco, tryhard — sin modismos de un solo país), situaciones sacadas de **memes actuales del nicho + clásicos universales bien ejecutados**.

## El diagnóstico: por qué los guiones anteriores se sentían genéricos

El guion de la promo decía "tu compañero se va solo y muere". Eso le pasa a *cualquier* jugador de *cualquier* juego — es humor de brocha gorda. La versión que identifica dice: "tu jungla pasa por tu lane con full vida, ve al enemigo con 100 de vida, y se va a farmear lobos". El que juega LoL **ha vivido exactamente eso** y el detalle (lobos, full vida, 100 de vida) es la prueba de que quien escribió esto también lo vivió.

## La regla central (de la teoría real de comedia observacional)

**El detalle correcto está justo debajo del umbral de percepción**: ✅ ([fuente](https://zanyzune.com/relatablejokes/observational-humor-explained))
- Demasiado obvio → no da risa ("los junglas no gankean" — todo el mundo lo dice, es un lugar común).
- Demasiado oscuro → no conecta (un chiste sobre el cooldown exacto de un hechizo nivel 3).
- El punto dulce → lo que TODOS han vivido pero NADIE ha dicho en voz alta ("el jungla que te dice 'está warded' sin haber mirado el mapa").

**Test rápido antes de aprobar un guion:** ¿el chiste funciona si cambias "LoL" por "Fortnite"? Si sí → es genérico, falta especificidad. El guion de la comida ("ya voy, mentira") pasa el test al revés: funciona porque lo universal ERA el punto. El de la promo no: era una historia de LoL sin nada de LoL.

## Banco de situaciones específicas de LoL (validadas como memes vivos de la comunidad)

Confirmadas como contenido activo en la comunidad ES ✅ (TikTok/YouTube LoL LATAM, ej. MisrraVB — canal que tu propio público ya mira):

- **Jungle diff / culpar al jungla**: los 4 laners perdiendo sus lanes pero el reporte es para el jungla. El meme más universal del juego.
- **ff15**: el que pide rendición al minuto 15 porque murió una vez. Y su opuesto: el "no ff" con el nexo a 100 de vida.
- **"Está warded"**: negarse a gankear con la excusa eterna.
- **0/10 powerspike**: el que dice "tranquilos, mi campeón escala" yendo 0/10.
- **El flash al muro**: flashear contra la pared en el momento más crítico, con testigos.
- **"GG izi" del que fue 2/8**: el peor de la partida hablando al final.
- **El smurf que "solo está probando el rol"** y va 15/0.
- **Robo de barón/dragón con smite** — éxtasis o tragedia, sin punto medio.
- **"Mi support me robó un minion"** → guerra civil en bot lane.
- **El honor**: 4 reportes reales vs 1 honor de lástima.
- **La promo**: TODO lo malo pasa junto justo en la promo (afk, troll, lag) — el juego "sabe".
- **"Último pick or feed"**: el que pide mid o amenaza con feedear.

Universales que sí valen (el 30%): mamá + nombre completo (ya validado con "la comida está lista"), el "ya voy" mentiroso, la luz que se va en ranked, el hermanito que toca la puerta, "una partida más" a las 3am.

## Actualización 13 jul: por qué "coherente" no bastaba — faltaba que fuera GRACIOSO

Feedback real: los guiones ya eran específicos y causales, pero "no dan ganas de quedarse viendo". Diagnóstico con el usuario: 4 causas a la vez — chiste predecible, voz sin entonación cómica, poca energía visual, sensación genérica. Investigación aplicada:

### La regla de tres (✅ técnica de comedia establecida, no propia)
El cerebro reconoce patrones: dos elementos similares crean la expectativa de un tercero que siga el patrón — **el chiste real es que el tercero lo traicione** (subversión), no que lo confirme. — [Plus Comedy](https://pluscomedy.com/the-rule-of-three-comedy%C2%92s-magic-formula/), [Buddy On Stage](https://buddyonstage.com/blogs/rule-of-3-in-comedy)

**Nuestro error:** el guion del 0/10 hacía 0/1 → 0/3 → 0/6 → 0/10, todo el mismo patrón sin quiebre — es escalada realista, no chiste. Arreglo: dos beats que construyen el patrón + un tercero que lo rompe de forma absurda/exagerada.

### Exageración con freno (✅)
Ampliar el premise a algo más grande de lo real — pero sin pasarse tanto que se sienta forzado. El punto dulce está entre "muy seguro/aburrido" y "tan exagerado que se nota el esfuerzo". — [CreativeStandUp](https://creativestandup.com/comedic-conflict-the-mechanics-of-comedy/)

### Pausa antes del remate (✅ dato con estudios reales)
Un silencio de **500-800ms justo antes de la palabra clave** genera el pico de risa más fuerte — la pausa construye la anticipación, la palabra suelta la tensión. — [Buddy On Stage — timing](https://buddyonstage.com/blogs/timing-in-stand-up-how-pauses-make-jokes-funnier)

**Implementado:** escribe `...` en el guion justo antes del remate — el sintetizador de voz (Kokoro, `tools/kokoro_tts/synth.py`) ahora corta ahí e inserta 650ms de silencio real (no simulado con puntuación, silencio de verdad en el audio).

### La palabra graciosa va al final de la frase (✅)
"El tamaño de la brecha entre lo esperado y lo real es el tamaño de la risa" — y esa brecha se siente más si el remate cae en la última palabra, no en medio de la oración. — [CreativeStandUp — joke structure guide](https://creativestandup.com/wp-content/uploads/manual/joke-structure-guide.pdf)

### Golpe visual en el remate (✅ implementado)
La escena de la penúltima línea (donde suele caer el giro/remate) ahora usa un zoom "golpe": queda quieta y de golpe hace un zoom rápido — acento visual sincronizado con el momento cómico, no el Ken Burns lento parejo de siempre. Automático en `pipeline.py::acquire_media` (`punch_index`), no hay que pedirlo.

### Checklist nuevo antes de aprobar un guion
- [ ] ¿Hay un patrón de 2 (regla de tres) que el remate traiciona, o es solo "cada vez peor" en línea recta?
- [ ] ¿El remate exagera lo suficiente para sorprender, sin sentirse forzado?
- [ ] ¿Hay un `...` puesto a propósito justo antes de la palabra/frase clave del remate?
- [ ] ¿La palabra más graciosa/inesperada está al final de la oración, no enterrada en medio?
- [ ] (sigue vigente) ¿Pasa el test Fortnite? ¿Jerga LATAM neutra? ¿Causalidad clara?

## Fórmula de guion coherente (estructura obligatoria)

1. **Setup en 1ª línea = situación reconocible YA** ("Tu jungla llega a robarte el farm de tu lane"). Nada de contexto lento.
2. **Escalada con detalles específicos en orden causal** — cada línea consecuencia de la anterior, no lista de eventos sueltos. Mínimo 2-3 detalles "de insider" (nombres de cosas reales del juego: lobos, ward, smite, minion de caster).
3. **Re-hook a mitad** ("pero espera / y ahí fue cuando") — ya estándar del pipeline.
4. **Giro final que reencuadra todo** — la revelación de que era sabotaje, de que el manco eras tú, de que mañana repites.
5. **Última línea = loop con la primera** (rewatch).

## Coherencia: el checklist anti-"sin sentido"

Antes de generar el video, leer el guion y verificar:
- [ ] ¿Cada evento tiene causa en el evento anterior? (no "pasó X, luego pasó Y" inconexos)
- [ ] ¿Quién hace qué está claro en cada línea? (el guion de la promo original confundía: ¿quién se fue bot? ¿quién escribió en el chat?)
- [ ] ¿Los números/tiempos son consistentes? (si dijiste minuto 2, lo que sigue no puede ser "primera sangre" si ya hubo una muerte antes)
- [ ] ¿Pasa el test Fortnite? (si el 70% es LoL, debe haber ≥2 referencias que solo un jugador de LoL entiende)
- [ ] ¿La jerga es LATAM neutra? (tiltear, feedear, manco, tryhard sí; modismos de un solo país no)

## Fuentes
- [ZanyZune — observational humor explained](https://zanyzune.com/relatablejokes/observational-humor-explained) · [Be More Funny — quick guide](https://bemorefunny.com/how-to-write-observational-comedy-a-quick-guide/) — la regla de especificidad.
- Memes LoL comunidad ES verificados vía TikTok/YouTube (MisrraVB y related) ✅.
- `HUMOR_GAMER.md` — taxonomía previa del proyecto (sigue vigente, este doc la especializa para Skick).
