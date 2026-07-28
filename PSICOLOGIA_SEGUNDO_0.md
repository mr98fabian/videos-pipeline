# El segundo 0 — qué dispara curiosidad insaciable, visual y auditivamente

Investigación 28 jul 2026. Base científica + qué implica para el motor y el
prompt de HiddenFacts. Lo que ya está implementado va marcado; lo que no,
también.

---

## 1. La curiosidad no es placer, es hambre

Loewenstein la define como **privación cognitiva**: la conciencia de un hueco
entre lo que sabes y lo que quieres saber. Funciona como el hambre, no como el
disfrute — es un estado aversivo que empuja a cerrarlo. En fMRI se activan el
**núcleo caudado** y el **giro frontal inferior**, el mismo circuito de
recompensa del apetito.

Tres consecuencias que cambian cómo se escribe un gancho:

### 1.1 La dosis de cebado — la más importante y la que estás incumpliendo

> "Una pequeña cantidad de información sirve como dosis de cebado que aumenta
> enormemente la curiosidad."

**Sin información previa no hay hueco, y sin hueco no hay curiosidad.** Una
pregunta pelada no crea nada: crea indiferencia. La pregunta solo funciona
cuando el espectador **ya tiene el contexto** o se lo das en la misma frase.

Por eso funciona *"¿Por qué los animales no te atacan mientras duermes?"*: el
espectador ya sabe que duerme indefenso. El dato está precargado en su vida.
Y por eso una pregunta sobre un hecho histórico que no conoce no engancha
igual — no hay nada de lo que privarle.

**La forma fuerte es dato concreto + pieza que falta**, no pregunta sola:
- Débil: *"¿Qué esconde la Torre Eiffel?"* — cero cebado.
- Fuerte: *"La Torre Eiffel tiene agujeros de bala que nadie mira."* — el dato
  ceba, "nadie mira" abre el hueco.

### 1.2 La saciedad mata

Consumir información es recompensante **hasta que sacia**, y a partir de ahí
reduce la curiosidad. Es el argumento duro contra resolver pronto: cada dato
que sueltas antes de tiempo baja el impulso de seguir.

La regla de los re-ganchos cada 15s es correcta por esto — reabre el hueco
antes de que la saciedad llegue.

### 1.3 La curiosidad es máxima en conocimiento intermedio

Ni cero ni completo. Un tema del que no se sabe nada no genera hueco; uno que
se domina, tampoco. **El punto óptimo es "he oído de esto pero no lo entiendo"**
— que es exactamente la plantilla Black Tom: icono famoso (conocido) con
consecuencia que no sabías (hueco).

---

## 2. Visual: tienes 100 milisegundos

### 2.1 La ventana física

El colículo superior avisa al resto del cerebro de que ha ocurrido un evento, y
si el estímulo no alcanza ese objetivo dentro de una ventana de **~100 ms**,
sencillamente **no se percibe**. No es una metáfora de "atención corta": es el
tiempo de ciclo del detector.

A 30 fps, **100 ms son 3 fotogramas**. Lo que no esté resuelto en el fotograma
3 no cuenta.

### 2.2 El movimiento es el disparador más primitivo

En recién nacidos la atención se despliega **principalmente por movimiento**;
la orientación de la cara solo influye a partir de los 4 meses. El movimiento
es anterior a todo lo demás en el sistema.

✅ **Implementado**: la escena 1 abre a ×1,34 y se aleja en ~0,5s, así que hay
movimiento desde el fotograma 0 pase lo que pase con la imagen.

### 2.3 Las caras conocidas se separan de las desconocidas a los ~100 ms

El componente M100 detecta caras entre ruido, y hay **respuestas diferenciales
tempranas entre caras conocidas y desconocidas alrededor de los 100 ms**.

Esto es evidencia neural directa de la regla Black Tom: **un icono famoso es lo
único que el cerebro puede reconocer dentro de la ventana de decisión.** Una
cara desconocida no se identifica a tiempo — hay que presentarla, y presentar
cuesta segundos que no tienes.

---

## 3. Auditivo: manda el ataque, no el volumen

### 3.1 La respuesta de orientación es literalmente el pulgar parándose

La orientación es una respuesta rápida a estímulos **nuevos, inesperados o
impredecibles**, y funciona como detector de "¿qué es esto?". Su
manifestación conductual es **la detención de la actividad en curso** para
enfocar la atención.

Eso es exactamente lo que necesitas del espectador: que pare el scroll.

### 3.2 El ataque brusco importa más que la intensidad

Hallazgo aprovechable de inmediato: estímulos acústicos intensos **con inicio
súbito** disparan el reflejo de sobresalto, mientras que estímulos de
intensidad similar **pero con tiempo de subida largo** solo provocan una
respuesta cardíaca de defensa, no el sobresalto.

Traducido: **subir el volumen no sirve. Empezar de golpe, sí.** Un fundido de
entrada en la voz, por corto que sea, desactiva el mecanismo.

### 3.3 El tono amenazante orienta más rápido que el amable

A los **200 ms** post-estímulo, la orientación atencional es mayor para señales
vocales **amenazantes** que para las alegres. La voz de archivista cínico juega
a favor; una voz cálida y amable, en contra.

### 3.4 Los sonidos salientes deforman el tiempo

Un sonido saliente **distorsiona la percepción y la producción temporal**: el
momento se siente más denso. Útil para que los primeros segundos no se sientan
lentos.

---

## 4. Qué hacer con esto

### Ya está puesto
- Movimiento en el fotograma 0 (empuje de cámara).
- Nada antes de la voz — ni tarjeta, ni logo, ni música de entrada.
- Promesa completa escrita en pantalla desde el fotograma 0 (`HookText`).
- Icono famoso como ancla (Black Tom).
- Voz de archivista cínico, no amable.

### No está puesto, y sale de esta investigación
1. **El `hook_card` debe cebar, no solo preguntar.** La regla 9 actual pide
   "siempre pregunta sin resolver". La teoría dice que una pregunta sin dosis
   de cebado no genera hueco. Forma correcta: **dato concreto + pieza que
   falta**, que puede seguir siendo una pregunta pero nunca vacía.
2. **La voz debe atacar en seco.** Verificar que el MP3 no arranca con fundido
   y que la primera palabra empieza en consonante oclusiva (p/t/k/b/d/g), que
   da un transitorio brusco. Una vocal abierta sube despacio y desactiva el
   sobresalto.
3. **El primer plano debe ser el icono reconocible, no una escena de contexto.**
   Si el fotograma 0 es un pasillo o un documento, se pierde la ventana de los
   100 ms: no hay nada que reconocer.
4. **Sin fundido de entrada de imagen.** Cualquier fade cuesta más de 3
   fotogramas y se come la ventana entera.

---

## Fuentes

- [The Psychology and Neuroscience of Curiosity (Kidd & Hayden, Neuron)](https://pmc.ncbi.nlm.nih.gov/articles/PMC4635443/)
- [Curiosity, Information Gaps, and the Utility of Knowledge (Golman & Loewenstein, CMU)](https://www.cmu.edu/dietrich/sds/docs/golman/golman_loewenstein_curiosity.pdf)
- [Visual events have 100 milliseconds to hit brain target or go unnoticed (NIH / National Eye Institute)](https://www.nei.nih.gov/research-and-training/research-news/its-now-or-never-visual-events-have-100-milliseconds-hit-brain-target-or-go-unnoticed)
- [Face Orientation and Motion Differently Affect the Deployment of Visual Attention in Newborns](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4569357/)
- [Early Category-Specific Cortical Activation Revealed by Visual Stimulus Inversion (M100)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2566817/)
- [Prepulse Inhibition of the Auditory Startle Reflex (tiempo de subida vs intensidad)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7563436/)
- [Early spatial attention deployment toward and away from aggressive voices](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6318470/)
- [Salient sounds distort time perception and production](https://link.springer.com/article/10.3758/s13423-023-02305-2)
- [Orienting Response — overview (ScienceDirect)](https://www.sciencedirect.com/topics/psychology/orienting-response)
