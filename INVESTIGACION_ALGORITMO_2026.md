# Investigacion profunda: algoritmo Shorts 2026 + tecnicas nuevas a probar

Complementa `RETENTION_CHECKLIST.md` (sistema de gancho ya construido) y
`CREATOR_RANT_IDEAS.md` (canal Creator Rant). Fuentes: busqueda web
(Shortimize, vidIQ, Virvid, OutlierKit, estudios citados de Loewenstein/
Zeigarnik, benchmark 2025 de retencion). Todo lo de abajo es investigacion,
nada esta implementado todavia.

## 1. Umbral real del algoritmo 2026 (el dato mas importante)

- Shorts <30s: necesitan **~65% de retencion** para que el algoritmo empuje
  mas fuerte.
- Shorts 30-60s (nuestro rango, 45-50s): el umbral baja a **~50%**.
- Una vista de 6s en un short de 60s ahora es señal NEGATIVA fuerte (antes solo
  contaba como "no fue swipe").
- Si el short pasa el umbral, YouTube lo empareja con un cluster de tema
  especifico y puede seguir ganando vistas 3-6 semanas si el match es limpio.

**Lectura clave para nosotros**: nuestro promedio de canal (50.5%) esta
justo en el filo del umbral de 50% para nuestra duracion -- eso explica el
estancamiento: la mitad de los videos caen apenas debajo del umbral (sin
empuje) y la otra mitad apenas arriba (empuje modesto). No necesitamos
duplicar la retencion, necesitamos consistentemente cruzar ese filo.

## 2. Loop / rewatch como señal de ranking (NO estaba en nuestro sistema)

- Las repeticiones (loops) cuentan como vistas adicionales desde 2025 y son
  señal fuerte de engagement -- un short "loopeable" puede pasar de 100% de
  duracion promedio vista (la gente lo ve mas de una vez).
- Dos tipos de loop, ambos aplicables a guion+edicion sin rehacer el pipeline:
  - **Loop visual**: el ultimo frame se parece al primero (corte imperceptible
    al repetirse). Dificil de aplicar bien a nuestro formato narrativo (no es
    un video de accion circular), pero SI aplicable a la miniatura/primer
    frame de la escena 1 si coincide visualmente con el frame final.
  - **Loop narrativo** (mucho mas facil para nosotros): la ULTIMA linea del
    guion reformula/recontextualiza la PRIMERA linea, dandole un significado
    nuevo -- el viewer vuelve a sentir curiosidad por la frase de apertura y
    la relee/rewatchea. Ya tenemos la estructura base ("un rey sobrevivio a un
    arma de 25 canos" al inicio y al final) -- falta CAMBIAR el significado en
    el cierre, no solo repetir la frase igual.

**Accion concreta de guion**: en vez de repetir la linea de apertura tal cual
al final (lo que ya hacemos en varios guiones), reescribirla para que la
MISMA frase se sienta distinta despues de conocer el desenlace. Ejemplo real
del guion Fieschi: apertura "Un rey sobrevivio a un arma con 25 canos, y 18
personas a su alrededor no." -- cierre actual repite casi igual. Version con
recontextualizacion: "Un rey sobrevivio a un arma con 25 canos construida para
matarlo -- y camino con apenas una marca." (mismo hecho, pero el cierre
reencuadra la apertura como algo casi milagroso en vez de solo repetirla).

## 3. Info gap / curiosity gap: base cientifica real, con numero concreto

- Estudio VidIQ 2023: los videos con "open loops" (bucles de informacion sin
  cerrar) muestran **+32% en watch time**.
- Estudio clasico (trivia, respuesta demorada vs inmediata): el grupo que
  esperaba reporto **+42% de curiosidad** y **+28% de retencion de la
  informacion** una vez que recibio la respuesta.
- Teoria de base (Loewenstein 1994): la curiosidad aparece especificamente
  cuando la persona percibe un GAP entre lo que sabe y lo que quiere saber --
  ya es la base teorica de nuestro `hook_card`, esto la respalda con numeros.

**Lectura**: el hook_card (premise card) que ya construimos este chat esta
alineado exactamente con la tecnica que mas evidencia cuantitativa tiene
(+32% watch time). Vale la pena priorizar terminar de testearlo en A/B real
antes de sumar tecnicas nuevas.

## 4. Kinetic typography / texto animado (nuevo, no lo teniamos)

- 70-85% de las vistas en Shorts/Reels/TikTok son SIN SONIDO -- el texto en
  pantalla carga la mayoria del mensaje, no es decorativo.
- Cifras clave dichas EN VOZ ALTA y tambien mostradas en texto aumentan el
  recall un **+40% vs solo audio**.
- Tecnicas de 2026 mas citadas: texto palabra-por-palabra con la palabra clave
  en color distinto (ya lo hacemos en el modo caption con rojo/blanco),
  titulos grandes centrados en negrita, texto que "pulsa"/escala en sync con
  golpes de audio (beat-synced punch text).

**Accion concreta**: nuestros subtitulos karaoke ya cubren "palabra por
palabra", pero no tenemos el "punch" (escala/pulso) sincronizado con los SFX
-- es exactamente la idea de Remotion que discutimos antes (kinetic numbers +
shake en sfx), y ahora tiene respaldo de que compensa el 70-85% de vistas sin
sonido.

## 5. Faceless / IA: riesgo real de politica que hay que vigilar

- YouTube en 2026 renombro su regla de "contenido repetitivo" a **"contenido
  inautentico"**, y ahora evalua el CANAL completo (no solo el video):
  patrones de formato identico repetido en decenas de videos + narracion
  sintetica sin "huella editorial humana" son señal de riesgo.
- Enero 2026: 16 canales grandes (4.7 mil millones de vistas combinadas)
  perdieron el Partner Program por esto.
- Regla de disclosure: hay que marcar "contenido alterado o sintetico" SOLO
  si el contenido podria confundirse con metraje real de una persona/lugar/
  evento real. Contenido con estilo ilustrado/cartoon (como el nuestro, sepia
  vintage toon) generalmente NO cae en esa categoria porque nadie lo
  confundiria con footage real.
- Canales que combinan IA con un "angulo humano" (voz propia, investigacion
  original, edicion unica) mantienen la monetizacion sin problema.

**Lectura para nosotros**: bajo riesgo directo por el estilo (obviamente
ilustrado, no fotorrealista), pero SI hay que vigilar la "huella editorial
humana" -- esto refuerza lo que ya vimos en Creator Rant sobre el "conflict
radius": el angulo/analisis debe sentirse propio, no solo el hecho narrado.

## 6. Estadisticas de referencia (para calibrar expectativas, no para copiar directo)

- Benchmark general 2025: promedio de retencion en YouTube es solo 23.7%; solo
  1 de cada 6 videos supera el 50%. Nuestro 50.5% de canal ya esta MEJOR que
  el promedio general de la plataforma, aunque estemos estancados respecto a
  nuestro propio techo (70.6%).
- Canales faceless con voiceover/avatar IA: **+58% de retencion** reportado
  vs faceless sin ese formato (cifra de fuente de marketing, tomar con
  pinzas -- no es un estudio controlado, es un promedio de casos de exito
  reportados).

## Resumen de acciones nuevas sugeridas (ninguna implementada aun)

1. Recontextualizar el cierre del guion en vez de repetir la apertura igual
   (loop narrativo) -- cambio de escritura, cero costo de pipeline.
2. Terminar el A/B del hook_card (ya construido) -- es la tecnica con mas
   respaldo cuantitativo (+32% watch time citado).
3. Sumar "punch" visual (escala/pulso) sincronizado a los SFX via Remotion o
   filtro ffmpeg directo -- compensa el 70-85% de vistas sin sonido.
4. Vigilar que cada guion tenga un angulo/dato que NO este ya cubierto (conecta
   con el "conflict radius" de Creator Rant) -- mas relevante para
   DISTRIBUCION que para retencion en si.

---

## Estimacion de mejora (con honestidad sobre la incertidumbre)

**Esto es una estimacion razonada, no una medicion.** Ningun numero de abajo
viene de un test controlado sobre TU canal especifico -- son inferencias a
partir de: (a) donde estamos hoy (50.5% promedio, 70.6% techo), (b) los
umbrales de algoritmo citados arriba, y (c) los porcentajes reportados en la
investigacion para tecnicas individuales similares.

| Palanca | Impacto esperado en retencion | Confianza |
|---|---|---|
| Sistema de gancho ya construido (visual+auditivo+texto, `--hook-max`) | +3 a +8 puntos | Media (logica solida, sin dato propio aun) |
| Loop narrativo en el cierre del guion | +2 a +5 puntos | Media (tecnica barata, efecto modesto pero real) |
| Punch visual sincronizado a SFX (kinetic) | +2 a +4 puntos | Media-baja (compensa vistas sin sonido, no un gancho nuevo) |
| Disciplina de angulo nuevo por guion | +0 a +3 puntos en retencion, pero potencialmente mucho mas en DISTRIBUCION/alcance total | Baja para retencion, alta logica para alcance |

**Estimado combinado (no es una simple suma, los efectos se solapan)**:
subir el promedio del canal de **~50% a un rango de 60-68%** es razonable si
se implementan las 4 palancas juntas y se sostiene en el tiempo -- eso
equivale a una mejora relativa de **~20% a ~35%** sobre el promedio actual, y
nos pondria consistentemente por ENCIMA del umbral de empuje del algoritmo
(50% para nuestra duracion) en vez de rondarlo.

Lo que NO puedo estimar con honestidad: cuanto de eso se traduce en vistas
totales, porque eso depende ademas de distribucion/matching de topico, que es
un mecanismo distinto a la retencion (seccion "conflict radius"). Es
razonable esperar que el efecto en vistas totales sea IGUAL o MAYOR al efecto
en retencion, dado que cruzar el umbral desbloquea 3-6 semanas de empuje
sostenido en vez de un empuje plano.
