# Revisión semanal de estadísticas (sábados por la noche)

**Por qué existe (15 ago 2026):** mirar números sin pregunta fija termina en
"subieron las vistas" y ninguna decisión. Este documento fija **qué se pregunta,
en qué orden, y con qué se contesta cada pregunta**. La salida no es un resumen:
es *una regla nueva y una hipótesis falsable* anotadas en `HISTORIAL_MEJORAS.md`.

La rutina la ejecuta una tarea programada los sábados por la noche.

---

## Las 7 preguntas, en este orden

**1. ¿La curva cae o se aplana?**
La forma manda sobre el número. Una curva plana al 65% es mejor activo que una
que abre al 95% y se hunde al 40%: la plana indica que el contenido sostiene, la
otra que el gancho promete algo que el vídeo no paga.
*Se contesta con:* `youtube_api.py --account korex retention <id>`.

**2. ¿Dónde está el punto de caída colectiva, y qué frase suena ahí?**
No "cuánto" sino "cuándo y por qué". Se busca la mayor caída entre dos puntos
consecutivos y se cruza con el `script.json` de esa carpeta para leer la frase
exacta. Así se encontró el patrón *"Miren a Tadeo"* el 15 ago 2026.
*Se contesta con:* la curva + `script.json`, frase a frase.

**3. ¿Hay joroba? ¿Qué había ahí?**
Los tramos donde la curva sube (rebobinado o recompartido) son la única señal
*positiva* del gráfico, y casi nadie los mira. Lo que produce joroba se repite en
los siguientes guiones. Si la joroba está al final, ese contenido debe ir antes.

**4. ¿El vídeo con más vistas es de verdad el mejor activo?**
Vistas no es la moneda: un vídeo con más vistas y cero suscriptores ni
compartidos vale menos que uno con la mitad de vistas que convierte. Cruzar
siempre vistas × retención × subs × compartidos antes de decidir qué formato
repetir.
*Se contesta con:* `youtube_api.py --account korex top --start --end`.

**5. ¿Qué pasó con la hipótesis abierta de la semana pasada?**
La pregunta que da sentido a todas las demás. Cada entrada de
`HISTORIAL_MEJORAS.md` cierra con una hipótesis falsable; aquí se comprueba si se
cumplió, y **se anota también cuando falla**. Una hipótesis refutada vale igual
que una confirmada; lo que no vale es dejarla sin mirar.

**6. ¿De qué tipo es la caída: gancho, promesa o ritmo?**
Tres zonas, tres causas distintas y tres arreglos distintos:
- **0-3 s** — gancho: el primer fotograma y las primeras palabras no ganan la
  parada. Se arregla en la imagen 1 y en la frase 1.
- **5-15 %** — promesa: el vídeo se paró a dar contexto en vez de empezar a
  pagar. Se arregla en la frase 2. *(Es donde sangra KOREX hoy.)*
- **mitad** — ritmo: cadencia de plano o densidad. Se arregla cortando.

**7. ¿Qué NO se puede concluir todavía?**
Con dos o tres vídeos nuevos y pocas vistas, casi nada. Escribir explícitamente
qué queda sin datos evita construir una regla sobre ruido, que es el error más
caro porque después se propaga a todos los guiones.

**8. ¿n=1, o de verdad se repitió? ¿Y estaba aislada la variable?**
Añadida el 28 ago 2026, tras cazarme a mí mismo haciéndolo mal: comparé
"pagar en 4" contra los cuatro vídeos anteriores y escribí "se confirma la
hipótesis" — eligiendo la comparación **después** de ver el dato, que es el
mismo sesgo de *look-ahead* que la validación cruzada purgada existe para
bloquear en series temporales. Dos preguntas, no una:
- **¿Cuántos vídeos independientes sostienen esto?** Con uno solo no hay nada
  que confirmar, por bueno que se vea el número — es la versión de "un
  backtest de una sola operación no prueba la estrategia".
- **¿Cuántas cosas cambiaron a la vez en ese vídeo?** Si "pagar en 4" llevaba
  gancho reescrito + beat marcado + frame animado a la vez, un resultado bueno
  no dice CUÁL de los tres lo causó. Antes de promover algo a regla, revisar
  si el vídeo que lo sostiene aisló una sola variable o las mezcló todas.
Una hipótesis solo sube de "dato suelto" a "confirmado" cuando pasa las dos.

## Qué se entrega

Una entrada en `HISTORIAL_MEJORAS.md` con: la tabla de la semana, **un solo
cambio** (si hay más de uno no se sabrá cuál funcionó), dónde se aplica, y la
hipótesis falsable con su número concreto. Antes de escribir "se confirma",
pasar la pregunta 8. Y, si toca, la regla operativa en
`RETENTION_CHECKLIST.md`, que es el fichero que se lee al escribir.

---

## Lo que dicen fuera, en cinco idiomas (15 ago 2026)

Recogido para no reinventar el método. **Nuestros datos medidos mandan sobre
todo lo de aquí** — esto sirve para saber qué mirar, no qué concluir.

**Inglés.** La forma de la curva importa más que el número absoluto; una meseta
plana al 65% supera a una caída de 95% a 40%. La ubicación del desplome
diagnostica la causa: primeros segundos = gancho, mitad = ritmo, pico suelto =
problema puntual de contenido.

**Japonés.** Dos conceptos que aquí no teníamos nombrados: el **急落ポイント**
(punto de caída brusca) es "el momento en que la audiencia perdió el interés en
bloque" y es lo primero que hay que arreglar; y las **山** (jorobas por encima de
la media) marcan lo que la gente rebobinó — se reproduce ese elemento en otros
vídeos. Además plantean el embudo en cuatro escalones (retención → guardado y
compartido → visita al perfil → conversión) para saber *en qué escalón* se cae.

**Coreano.** Coincide con la ayuda oficial de YouTube: el informe de momentos
clave separa **인기 장면** (tramos donde casi nadie se va) de **급상승** (tramos
rebobinados o compartidos), y la recomendación explícita es que **si el mejor
tramo está al final, se mueve al principio**. La estrategia 2026 que citan pone
el foco en reducir el abandono en el feed antes que en el clic.

**Chino.** Ojo: esto es **Douyin, no YouTube**, y se anota como referencia de
método, no como regla aplicable. Interesa una cosa: analizar la curva por tramos
para localizar el punto de fuga, y **volver a medir la mejor hora de publicación
cada mes** en vez de fijarla una vez. Su orden de pesos (guardados por encima de
todo) es de otra plataforma y no se importa.

**Español.** Registrar la retención en marcas fijas (3 s, 6 s, 15 s, 30 s) para
poder comparar entre vídeos, y el recordatorio de que el vídeo más visto no es el
mejor activo si no genera suscripción ni sesión.

**Lo que ya sabíamos y esto no cambia:** que la caída de KOREX está en la frase 2
es dato propio, medido sobre nuestras cinco curvas. Ninguna de estas fuentes lo
dice, porque ninguna ha visto nuestros guiones.
