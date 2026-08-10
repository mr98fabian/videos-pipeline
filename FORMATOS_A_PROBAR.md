# 20 formatos para probar uno por uno en HiddenFacts (niche banding)

Fuente: formatos virales generales 2026 (listicle, transformacion, pattern-break, POV,
true crime shorts) + reformateo cross-nicho de Creator Rant, todos adaptados al estilo
fijo del canal (sepia vintage toon, hecho real verificado). Casi no hay competencia
directa en HiddenFacts todavia, asi que el objetivo es probar 1 formato nuevo por
tanda (2-3 videos) y ver cual "revienta" antes de escalarlo.

Orden sugerido: probar del 1 al 20, anotar resultado en `video_log.csv`
(`outlier_reference`) con el numero de formato para poder comparar despues.

1. **"Nunca deberías tocar/usar/confiar en [X]"** -- objeto o institucion historica con
   advertencia directa. Ej: "Nunca deberías confiar en una foto de guerra sin verificar esto."
2. **Pattern-break (arranca como un genero, gira a mitad)** -- empieza como historia de
   guerra/heroismo y a mitad se revela que es sobre traicion/estafa, o al reves.
3. **"Antes de ser [famoso], era [Y]"** -- transformacion/reveal de identidad oculta (ya
   probado una vez con Roald Dahl -- formalizar como serie recurrente).
4. **Micro-listicle numerado**: "3 secretos que el gobierno ocultó sobre [X]" -- formato
   contable, cada punto una oracion corta.
5. **POV directo**: "POV: sos el soldado que acaba de descubrir que..." -- segunda persona,
   inmersivo, distinto a la narracion en tercera persona que usamos siempre.
6. **Dato sorprendente sin arco narrativo** -- una sola revelacion + visual fuerte, sin
   historia de "y entonces". Mas corto, mas directo.
7. **Resumen de caso de 60s (true crime formalizado)** -- ya probamos Markov/paraguas;
   convertirlo en sub-serie fija con intro/formato reconocible propio.
8. **Perfil psicologico de 1 minuto** -- enfocarse en la MENTE/motivacion de una figura
   historica, no en los hechos ("Por que Fieschi penso que este plan iba a funcionar").
9. **"Lo que ves vs lo que realmente paso"** -- contraste directo, dos mitades de pantalla
   o dos escenas encadenadas.
10. **Casos internacionales sin cobertura en ingles** -- historia oculta de Japon, Europa
    del Este, Latinoamerica, sudeste asiatico -- casi cero "conflict radius" porque nadie
    mas lo esta cubriendo en ingles todavia.
11. **Countdown de hechos shockeantes de UN SOLO evento** -- "5 datos que nadie te contó
    sobre [batalla/personaje]" en vez de una narrativa lineal.
12. **Version calma/lenta como inversion deliberada** -- contra nuestro tono siempre
    tenso/sepia-dramatico, probar UN video con narracion calma, casi documental BBC, para
    ver si el contraste de tono llama la atencion en el feed.
13. **Pregunta directa como GANCHO de apertura, no de cierre** -- "¿Vos hubieras hecho lo
    mismo?" como primera linea, no como CTA final.
14. **Arco de injusticia/redención como formato fijo** -- ya lo probamos con el angulo
    Katyn (injusticia emocional); formalizarlo como plantilla reusable para cualquier
    hecho con victima/culpable.
15. **Reversa cronologica**: arrancar por el FINAL/giro y retroceder a explicar como se
    llego ahi ("Terminó ejecutado en 6 meses. Todo empezó con 25 caños de metal.").
16. **Comparacion lado a lado (expectativa vs realidad historica)** -- ej. lo que la
    gente cree que paso en un evento vs lo que documentos reales muestran.
17. **Objeto cotidiano con origen oscuro** -- un objeto que la gente usa/conoce hoy con un
    origen historico oculto (ya parecido a Coca-Cola/cheese del gobierno, formalizar).
18. **"El error que nadie noto hasta X años despues"** -- foco en el descubrimiento tardio
    en si (el momento del hallazgo), no solo el hecho original.
19. **Enfrentamiento de dos figuras historicas opuestas** -- formato de contraste directo
    (ya validado con "nivel 1 vs nivel 18" en ImPixxel, portar la logica a HiddenFacts:
    "espia vs contraespia", "rey vs asesino").
20. **Doble-punchline explicito** -- guion escrito deliberadamente con el mecanismo del
    "giro + segundo micro-giro inmediato" (tecnica del guion viral de 5M vistas
    analizado), como estructura fija en vez de ocasional.
21. **Historia en 2 partes con cliffhanger real (patron Extra History, prioridad alta)** --
    UNA historia fuerte partida en 2 Shorts: la parte 1 corta en el punto de maxima
    tension ("Y lo que encontraron adentro... parte 2 mañana"), la parte 2 se publica
    24h despues, mismo horario. Es el motivo de suscripcion mas fuerte que existe
    (serializacion = razon de volver; asi construyo Extra History sus 4,59M subs con
    partes numeradas). Medir DISTINTO al resto: (a) subs ganados por la parte 1 vs
    promedio del canal, (b) vistas de la parte 2 como % de la parte 1 (retencion de
    serie), (c) comentarios pidiendo la parte 2. Si (a) supera 2x el promedio, formalizar
    como formato regular. Registrar como "FORMATO #21: 2 partes" en outlier_reference.

## Como registrar el experimento

Cada video que use uno de estos formatos: anotar en `outlier_reference` de
`video_log.csv` como `"FORMATO #N: <nombre corto>"`, mismo criterio que ya usamos con
los tests de angulo/duracion. A los 2-3 dias, comparar vistas/retencion contra el
promedio del canal y contra los otros formatos probados.
