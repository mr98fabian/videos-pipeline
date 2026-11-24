# Al storyboard le falta corazón — diagnóstico y qué se añade

**Por qué existe (17 ago 2026):** Fabián vio un hilo sobre ChatGPT Image 2.0 +
Seedance 2.0 para storyboard de anime y señaló algo que no era sobre las
herramientas: **a nuestros storyboards les falta corazón antes de producir.**
Investigado con la técnica real del oficio (EN: beat boards de Pixar/Disney) y
verificado contra nuestros propios guiones, no solo teoría.

---

## El hallazgo, con nuestros propios datos

Miré los `character_terms` de los últimos guiones de KOREX:

```
tarjeta-minimo: grito, orgulloso, malvada, malvada, malvada, estafado,
                confundido, decidido, malvada, grito
torre-eiffel:   confundido, senalando, bolsillos, confundido, explicando,
                triunfo, decidido, codicia, picaro, confundido, grito, estafado
tulipanes:      grito, bolsillos, explicando, orgulloso, senalando, codicia,
                decidido, estafado, picaro, confundido, estafado, estafado,
                confundido, triunfo, explicando, grito
```

**Es la misma bolsa de 8-10 poses reciclada mecánicamente, escena tras escena,
sin distinguir cuál es EL momento del vídeo.** Cada frase recibe una pose
"correcta" para lo que dice —confundido si duda, estafado si lo timan— pero
ninguna escena está tratada como más importante que las demás. El giro (que
`_check_giro_posicion` ya sitúa entre el 25% y el 75%) cae sobre una pose
cualquiera del catálogo, igual que la escena de transición número 4.

Eso es exactamente la ilustración literal de la frase, que es lo contrario de
actuar la emoción — y es el síntoma que la investigación llama "falta de
corazón".

## Lo que dice el oficio: el beat board no es el storyboard

En Pixar y Disney, **antes** del storyboard escena-a-escena se hace un pase
distinto llamado *beat board*: una sola imagen fuerte por cada momento
emocional clave de la historia, pensada solo para transmitir el sentimiento de
ESE instante — sin cámara, sin coreografía, sin las demás escenas alrededor.
Sirve para comprobar, antes de dibujar nada más, si los momentos que importan
**se leen** por sí solos. El storyboard normal viene después y reparte el
trabajo de cámara y continuidad; el beat board es el que decide dónde está el
peso.

La traducción a nuestro proceso: **no todas las escenas pesan igual, y hoy
las tratamos como si pesara igual.**

## Qué se añade (sin tocar lo que ya funciona)

No es un paso nuevo en el pipeline ni una herramienta nueva — es una regla de
escritura, aplicable con lo que ya existe (`character_terms`, `twist_phrase`).

1. **Antes de escribir `character_terms`, marcar cuál es LA escena** —
   normalmente la del `twist_phrase` o la de cierre. Es el equivalente a
   decidir el beat board antes del storyboard completo.

2. **Esa escena se actúa distinto, no solo se etiqueta distinto**: primer
   plano cerrado, pose sostenida (nunca "de paso"), y una pose que **no se
   repite en ningún otro guion de las últimas 4-5 semanas** — si "estafado" ya
   fue el clímax de dos vídeos seguidos, esta vez el clímax necesita otra cara.
   El resto de escenas pueden seguir usando el catálogo normal.

3. **Máximo dos escenas seguidas con la misma pose.** Se ve en `tulipanes`:
   "estafado, estafado" repetido no es una elección, es la ausencia de una.

4. **La pregunta de control, antes de mandar a Flow:** *si solo pudiera
   enseñar UNA imagen de este vídeo para que alguien entienda de qué trata,
   ¿cuál sería?* Si la respuesta no es obvia mirando los `character_terms`, la
   escena candidata no está actuada con suficiente fuerza todavía.

## Lo que esto NO cambia

- El motor sigue siendo Flow + hoja madre + `CHARACTER_LOCK`. Nada de Seedance
  ni ChatGPT Image: ya resolvemos la consistencia de personaje con lo que hay.
- No añade coste ni tiempo de producción: es una decisión de guion, se toma al
  escribir `character_terms`, igual que hoy.
- No sustituye la regla de `RETENTION_CHECKLIST.md` sobre la frase 2 — son
  capas distintas: esa regla es del gancho (los primeros 15 segundos), esta es
  de todo el arco emocional del vídeo.

## La marca explícita (17 ago 2026, vista en un storyboard real de anime)

Un storyboard profesional de anime (@ucmulleryu, teaser de 10 min, ep. 1)
confirma la idea con una convención que a la regla de arriba le faltaba:
**cada corte lleva un borde de color según su peso** — naranja para el beat
(el primer plano de la reacción), rojo para los cortes importantes, sin borde
para la transición. Flechas de cámara aparte, hoja de personajes al margen. Se
lee cuál es la escena que importa sin leer el guion.

Traducido a texto plano, que es lo que usamos: **el beat lleva un asterisco**.

```
"character_terms": [
  "tadeo/confundido",
  "*tadeo/estafado",      <- EL beat: primer plano, pose no repetida
  "tadeo/decidido",
  ...
]
```

`kx_cast.resolve_scene_cast` debe ignorar el `*` al resolver el personaje (es
metadato de guion, no parte del nombre de pose) pero conservarlo para que
`korex_qa` pueda avisar si un guion no marca ningún beat, o marca más de uno.

## Próximo guion

El de la revisión de estadísticas del sábado (o el que sea el siguiente) es el
primero que aplica esta regla desde cero: marcar la escena del `twist_phrase`
como el beat, y comprobar que su pose no se repite con los últimos vídeos.
