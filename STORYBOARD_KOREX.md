# El storyboard: cómo lo hacen los profesionales y qué copiamos

**Por qué existe (12 ago 2026):** para el formato largo con imágenes fijas, la
calidad ya no depende del dibujo sino de **qué se ve exactamente mientras se
dice cada frase**. Investigación en JA (絵コンテ y コマ割り), ZH (分镜脚本), EN
(psicología del aprendizaje multimedia) y ES.

---

## 1. El 絵コンテ japonés: es un plano de obra, no arte

El storyboard de anime tiene cuatro columnas y ninguna es "dibujo bonito":

| カット | 絵 | セリフ | 秒数 |
|---|---|---|---|
| nº de corte | composición y ángulo | **diálogo/narración literal** | **segundos** |

Dos cosas que dicen las escuelas japonesas y que nos ahorran tiempo y dinero:

- **"No te obsesiones con el dibujo: el monigote basta. Lo importante es que se
  entienda."** El storyboard es el plano de obra; si se convierte en ilustración,
  deja de cumplir su función.
- **El corte básico dura ~3 segundos, y como mucho 5-6.** Ese es el estándar del
  oficio.

**Recalibración honesta:** yo propuse 10-12 s por plano para el formato largo.
El oficio dice 3-6. La diferencia es que ellos animan y nosotros ponemos una
imagen fija, que aguanta algo más — pero **10-12 s es demasiado**. Objetivo:
**6-8 s, nunca más de 8**. Para 9 minutos son ~70-80 cortes, con reutilización
y reencuadre de unas 25-30 imágenes distintas.

## 2. La sincronía tiene nombre: contigüidad temporal

Es un principio medido, no una opinión (Mayer, aprendizaje multimedia): **se
aprende más cuando la imagen y la narración van a la vez, no una después de
otra**. La razón es de memoria de trabajo: si la imagen llega tarde, el cerebro
tiene que sostener la frase mientras espera.

Traducido a reglas de producción, y esto es lo que pedías:

1. **Una frase = un plano.** La frase que suena es la que se está viendo.
2. **El corte cae EN la palabra clave**, no medio segundo después.
3. Si una frase necesita dos imágenes, se parte la frase. **Nunca una imagen
   para dos ideas.**

## 3. Los otros tres principios que sí aplican

- **Coherencia:** se aprende más cuando se quita lo decorativo. Y aquí tenemos un
  problema propio: nuestros fondos llevan muebles, cortinas, textura de papel y
  sombreado. Zenn pone **un color plano y nada más**. Lo bonito puede estar
  restando comprensión — en los planos que **explican** algo, el fondo se vacía.
- **Señalización:** destacar lo esencial libera capacidad mental. Es exactamente
  la **X roja gigante** que Zenn superpone a su propia ilustración, o una flecha,
  o un círculo. Barato, y es de lo poco que la evidencia respalda sin matices.
- **Segmentación:** partir lo complejo en partes progresivas. Un concepto no se
  explica en un plano: se explica en tres, y cada uno añade una pieza.

**La tensión que hay que decidir a sabiendas — subtítulos.** El principio de
redundancia dice que texto en pantalla que repite la narración **perjudica el
aprendizaje**. Pero Zenn los lleva grandes y centrados con 7,8 M de vistas, y
buena parte de YouTube se ve **en silencio**. No son la misma métrica:
laboratorio mide comprensión, YouTube mide permanencia. **Decisión: subtítulos
sí, pero por frase corta** (como Zenn), no palabra por palabra como en los
Shorts, y **fuera del plano cuando el plano ES la explicación** (un gráfico
tapado por texto no enseña nada).

## 4. Del manga: jerarquía de planos (メリハリ)

La teoría de コマ割り dice que la viñeta hace dos trabajos: **guiar la mirada** y
**poner en escena**. Y la regla que traduce mejor a vídeo es la del contraste:
**el tamaño del encuadre se cambia según la importancia** — viñeta grande para el
golpe, pequeñas para lo cotidiano; el ángulo torcido para tensión.

Si todos nuestros planos son el mismo plano medio de Tadeo en un cuarto, **no
hay jerarquía**: el espectador no sabe qué momento importa. Regla: **el primer
plano se reserva para el giro**. Si se usa en todas partes, no significa nada.

## 5. La tabla china (分镜脚本), que es la que hay que rellenar

El estándar chino de guion técnico son nueve columnas: nº de plano, **景别**
(tipo de plano), técnica, contenido visual, narración, música, efectos,
duración y notas. Es la versión operativa del 絵コンテ y encaja con lo que ya
tenemos a medias (`search_terms` + `motion_terms`).

**Plantilla para nuestros guiones largos** — sustituye a los dos campos sueltos:

```json
"storyboard": [
  {
    "n": 1,
    "seg": 7,
    "plano": "general",
    "imagen": "callejón de noche, Tadeo diminuto junto a un bote volcado",
    "narra": "<la frase literal que suena en este plano>",
    "ensena": "el punto de partida: no hay nada que repartir",
    "senal": null
  },
  {
    "n": 2,
    "seg": 6,
    "plano": "primer plano",
    "imagen": "la lata atascada en el hocico de Tadeo",
    "narra": "<frase>",
    "ensena": "la deuda: metiste la mano por lo bueno y ya no sacas la cabeza",
    "senal": "flecha roja señalando el borde de la lata"
  }
]
```

- **`narra` es la frase literal**, no un resumen. Es lo que garantiza la
  sincronía: si el campo está vacío o es un resumen, el plano no está atado a
  nada.
- **`ensena`** obliga a que cada plano tenga un trabajo. Si no se puede rellenar,
  el plano sobra.
- **`senal`** es la X roja / flecha / círculo. Solo en los planos que explican.
- **`plano`** fuerza la alternancia: si tres seguidos son "medio", hay que
  cambiar uno.

## 6. Resumen de reglas duras

1. Una frase, un plano. El corte cae en la palabra clave.
2. Plano de 6-8 s, nunca más de 8.
3. En planos que explican: fondo vacío y señal encima.
4. Primer plano reservado para el giro.
5. Cada plano declara qué enseña, o se elimina.
6. Subtítulo por frase corta, y nunca encima de lo que hay que mirar.
