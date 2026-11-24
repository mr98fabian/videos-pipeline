# Calendario de publicación KOREX — investigación EN/ES/JA/KO/ZH (17 ago 2026)

Qué publicar, en qué orden, qué día y a qué hora. Propuesta cerrada al final;
antes, lo que la sostiene.

---

## Lo que ya sabemos por dato propio (manda sobre todo lo demás)

- **Publicar en ráfaga mata el canal.** El 21 jul se subieron 10 vídeos en un día
  a mano desde Studio y el feed cayó un 93%. Por eso el código bloquea con
  **180 minutos mínimo entre públicos** y por eso se publica siempre por API.
- **No tenemos hora medida.** El informe de Studio "Horarios en que tus usuarios
  ingresan a YouTube" dice *"no hay suficientes datos"* (canal pequeño). Todo
  horario de aquí abajo es **razonado por huso horario, no medido**, y hay que
  volver a mirarlo cuando ese informe se llene.
- **Los Shorts son el motor y el largo no arranca solo**: 600-1.400 vistas por
  Short contra 6 impresiones del largo. El largo entra por búsqueda, no por
  cadencia (ver `ESCUELA_ROMUALD.md`).
- **Coste real de producción**: un Short son 19 imágenes de Flow (~30-40 min) más
  montaje; el largo son ~1.500 palabras y 30-50 imágenes, o sea horas. Cualquier
  calendario que ignore esto se abandona en dos semanas.

## Qué dicen fuera, en cinco idiomas

**Inglés.** Lo más accionable de todo el corpus: **tratar Shorts y largo como dos
calendarios separados, con horas distintas** — los canales que más crecen no los
mezclan. Largo a primera hora de la tarde; Shorts a mediodía o primera hora de
la noche. Cadencia sostenible: 1-2 largos por semana y 15-30 Shorts al mes.

**Español (estudio de Metricool).** Pone números al techo: **2-4 Shorts por
semana** es la banda eficiente, y **a partir de ~35 Shorts al mes la ventaja
desaparece** — publicar más deja de sumar. Añade el dato que nos importa:
publicar Shorts de forma constante se asocia a **mejor rendimiento del vídeo
largo**, y los Shorts son el formato de crecimiento sobre todo en canales
pequeños.

**Coreano.** La afirmación más relevante para nuestro cuello concreto: **la
retención de suscriptores correlaciona más con la CONSTANCIA que con la
frecuencia** — un canal que sube los martes a las 9:00 pierde menos suscriptores
que uno que sube todos los días de forma irregular. Su reparto recomendado:
largo 1/semana, Shorts 2-3/semana.

**Japonés.** Franjas concretas: Shorts entre semana de 17 a 20 h y fines de
semana de 10 a 12 h, 2-4 por semana. Y una idea de encaje: por la noche el
espectador está relajado y acepta contenido más largo y profundo.

**Chino.** Insisten en lo mismo por otra vía: **la estabilidad importa más que el
número**. 3-5 a la semana a hora fija hace que la plataforma lea la cuenta como
activa; el "día uno, uno" a lo loco no. Y separan objetivos por formato: en corto
se optimiza el 3-segundos y el completado; en largo, el tiempo de permanencia.

## Lo que converge

1. **Dos calendarios, no uno.** Shorts y largo no compiten si van en días y horas
   distintas.
2. **Constancia > volumen.** Mismo día, misma hora, siempre. Es lo único que las
   cinco fuentes repiten.
3. **3-4 Shorts por semana es el punto eficiente.** Más no suma; menos no
   construye el hábito.
4. **El largo va aparte y no necesita cadencia alta** — el nuestro además vive de
   búsqueda, que no caduca.

---

## El calendario (propuesta cerrada)

Horas en **hora de México (UTC−6)**, que es nuestro mercado principal.

| Día | Qué | Hora local | UTC | Por qué |
|---|---|---|---|---|
| **Martes** | Short | 19:00 | 01:00 mié | Franja de noche entre semana, la del corpus japonés |
| **Jueves** | Short | 19:00 | 01:00 vie | Mismo hueco, hábito semanal |
| **Sábado** | Short | 11:00 | 17:00 | Fin de semana por la mañana, la otra franja validada |
| **Domingo** | LARGO | 10:00 | 16:00 | Mañana de domingo, cuando hay tiempo para 9 minutos |

**Tres Shorts a la semana y un largo todos los domingos** (decisión de Fabián,
17 ago). Doce Shorts al mes: dentro de la banda eficiente (2-4/semana) y muy por
debajo del techo de 35 donde la ventaja desaparece. Un largo semanal es además
lo que recomiendan el corpus coreano (largo 1/semana + Shorts 2-3) y el inglés
(1-2 largos/semana), así que la cadencia semanal está mejor respaldada que la
quincenal que se propuso primero — y refuerza lo único en lo que coinciden las
cinco fuentes, que es la constancia.

**El cuello no es el algoritmo, es Flow.** Un largo son 30-50 imágenes y cada
Short 19: la semana completa pide ~110 imágenes, y Flow tiene cuota diaria (el
código ya cambia de modelo cuando se agota, ver `flow_automation.py`). Por eso
el largo del domingo **se produce entre semana**, nunca el mismo día que un
Short, y el guion se aprueba con días de antelación
(`guion-aprobado-antes-de-producir`). Si algún domingo no hay largo terminado,
se salta y se mantiene el resto: romper la hora fija cuesta más que faltar una
semana.

**El orden dentro de la semana importa**: el largo sale el domingo, y los Shorts
de esa semana lo enlazan en la descripción. Así el Short —que es lo que sí
recibe tráfico— alimenta al largo, que es lo que no lo recibe solo.

**Espaciado**: nunca dos públicos el mismo día. El guardarraíl de 180 minutos ya
lo impide, pero el calendario ni siquiera lo roza.

## Cómo se ejecuta

Se sube no listado y se **programa por API** con la hora exacta, nunca a mano
desde Studio (esa fue la causa del derrumbe del 21 jul):

```bash
py youtube_api.py --account korex update <video_id> --publish-at 2026-08-18T01:00:00Z
```

## Cuándo se revisa esto

- **Cuando el informe de horarios de Studio se llene** — entonces las horas dejan
  de ser razonadas y pasan a medidas, que es lo único que vale.
- En la revisión de los sábados (`ANALISIS_SEMANAL.md`), si un día de la semana
  rinde sistemáticamente peor que los otros dos.

**Lo que NO se puede concluir todavía.** Ninguna de estas horas está validada en
nuestro canal, y las fuentes se contradicen entre sí en las franjas concretas
(el estudio español da viernes 16-19 h; el japonés, noche entre semana). Lo que
sí coincide en las cinco es la **constancia**, así que eso es lo que se copia; la
hora exacta es una apuesta a revisar con datos propios.
