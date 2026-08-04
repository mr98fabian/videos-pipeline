# Plan: atacar la fuga del segundo 5,5 al 10

Escrito el 1 ago 2026 con la curva real de `-79EJI_BSsE` (884 vistas, 92s).

## El dato

| Tramo | Retención | Qué pasa |
|---|---|---|
| seg 0,9 | **129,7%** | Por encima de 100% = hay rewatches. El loop funciona. |
| seg 0,9 → 4,6 | 129,7 → 116,2% | Pierde ~3 pts/s. Normal. |
| **seg 5,5 → 10,1** | **104,9 → 59,4%** | **−45,5 pts en 4,6s. Pierde ~10 pts/s.** |
| seg 12 → 92 | 56,1 → 29,2% | −27 pts en **80 segundos**. Sanísimo. |

Swipe inmediato: **35,6%** (569 engaged de 884). Umbral del canal: <25% sano,
>40% roto. Estamos en medio.

**El gancho no es el problema y el cuerpo tampoco.** Todo el daño cabe en 4,6
segundos, y le ocurre a gente que ya había decidido quedarse.

## La causa

Mapeando el guion sobre el eje de tiempo a 4,5 palabras/segundo:

```
 0,0- 4,0s  What would you do if the family that threw you away came back...
 4,0- 5,8s  My name doesn't matter, but my story does.      <-- CERO informacion
 5,8- 9,8s  When I was sixteen, my stepdad told my mom it was him or me...
```

La frase de relleno ocupa **4,0-5,8s** y la caída arranca en **5,5s**. Un
segundo y medio de desfase, que es exactamente lo que tarda alguien en decidir
y deslizar. La hemorragia sigue durante la frase siguiente porque quien ya
decidió irse, se va.

Segunda causa, visual: extraídos los frames de esa ventana, el fondo es una
toma de manos en un torno de alfarería, marrón sobre marrón, desenfocada y sin
sujeto legible. No hay nada que mirar mientras no hay nada que oír.

Tercera causa, estructural: **acantilado de estímulos en el segundo 2,7**. La
hook card, el zoom de entrada, la pokebola y el fade de la música TERMINAN
TODOS antes del segundo 3. A partir de ahí no aparece ningún estímulo nuevo.

## CONFIRMADO con n=2 (1 ago, curva del 30 jul ya procesada)

El vídeo del 30 jul repite la caída **en la misma ventana**, y es de otra
duración y otro contenido:

| | 29 jul (92s) | 30 jul (39s) |
|---|---|---|
| seg 1 | 129,4% | 123,8% |
| seg 5,5 | 105,0% | 85,7% |
| seg 10 | 59,9% | 45,3% |
| **caída 5,5→10** | **−45,1** | **−40,4** |
| mayor caída suelta | seg 6,4 | seg 5,5 |
| swipe inmediato | 35,7% | 38,3% |
| % visto | 43,4% | 44,5% |
| subs | 1 | 0 |

Dos consecuencias:

**La fuga es estructural, no del guion concreto.** Dos vídeos distintos, dos
duraciones distintas, misma ventana, misma magnitud. Eso valida el plan.

**Y mata la recomendación de "20-35 segundos".** El de 39s es peor que el de
92s en TODAS las métricas: arranca más bajo, cae igual, termina en 21,3% frente
a 29,1%, tiene más swipe y cero subs. Acortar no arregla nada — coincide con
que el comparable de 1,6M dura 180s.

Los dos siguen empezando **por encima del 100%** en el segundo 1, así que las
rewatches ocurren y la regla del loop funciona en ambos.

## Aviso de validez

- **Ninguno de los dos lleva los cambios de hoy.** Confirman el PROBLEMA, no
  la solución. La primera prueba real sigue siendo publicar el
  `storage-headstone`.
- **Y no es el formato actual**: ese vídeo usa stock de vídeos satisfactorios,
  no el gameplay a pantalla completa. La causa del relleno se traslada; la del
  fondo marrón ilegible puede que no.
- Los del 30 y 31 jul tendrán curva en 24-48h. **Antes de tocar nada más,
  mirar si repiten la caída en el mismo sitio.** Si no la repiten, este plan
  sobra.

## Las intervenciones, por relación impacto/coste

### 1. Prohibir el relleno en los primeros 10 segundos — GRATIS, IMPACTO ALTO

Ninguna frase antes del segundo 10 puede existir sin aportar un hecho nuevo.
Fuera: "mi nombre no importa", "esta es mi historia", "para que entiendas",
"déjame que te cuente", "todo empezó cuando". Son preámbulo disfrazado de
narración, y el espectador los detecta en menos de dos segundos.

Implementado como `_check_relleno_inicial()`. Avisa, no bloquea.

### 2. Un premio entre el segundo 5 y el 10 — GRATIS, IMPACTO ALTO

La regla 9f pide premios repartidos, pero no fija ninguno en la ventana que se
desangra. El `visitor-log` tiene premios en el **3,2 y luego en el 20,1**: el
hueco de 16,9s aterriza justo encima de la zona de muerte. Es el peor sitio
posible y lo escribí sin saberlo.

Corrección de la regla 9f: **premio obligatorio entre el segundo 5 y el 10**,
además del reparto general.

### 3. Romper el acantilado del segundo 2,7 — BARATO, IMPACTO MEDIO

Que no termine todo a la vez. Escalonar: la hook card sale a los 2,7s pero
entra otra cosa entre el 4 y el 7 — el contador arrancando, un corte de plano,
un golpe de sonido, un stamp. Cualquier cosa que diga "esto sigue vivo".

Referencia externa: cambio visual cada 1,5-2s; por encima de 2,5s la retención
cae por falta de densidad de estímulo. Nuestro gameplay a pantalla completa
tiene **cero cortes en 84 segundos**.

### 4. Fondo legible en los primeros 10 segundos — BARATO, IMPACTO POR VERIFICAR

Elegir el tramo de gameplay de forma que los primeros 10 segundos tengan
sujeto claro y contraste, no un pasillo marrón. Se puede automatizar: medir
contraste y varianza de los primeros 300 frames del candidato y descartar los
tramos planos.

### 5. Bajar el swipe del 35,6% — SIN TOCAR HASTA TENER MÁS DATOS

Está en tierra de nadie y no es lo que más sangra. Atacarlo ahora es gastar
esfuerzo en el sitio equivocado.

## Cómo se comprueba

El siguiente vídeo lleva 1, 2 y 3 aplicados a la vez. **No aísla nada** — es a
propósito: primero hay que ver si la caída desaparece, y sólo entonces vale la
pena separar cuál de las tres la arregló.

Criterio de éxito, escrito antes: **la pérdida entre el segundo 5 y el 10 baja
de 45 puntos a menos de 20.** Si sigue por encima de 35, la causa no era el
relleno y hay que volver a mirar.

Criterio de fracaso que NO cuenta como éxito: que suba la media general. La
media puede subir por otras razones; lo que se está probando es la pendiente
de esa ventana concreta.
