# Cómo decide YouTube en 2026, y qué de eso podemos mover

**Por qué existe (12 ago 2026):** decisión de llevar KOREX a formato largo
(9+ min, imágenes estáticas, Tadeo). Investigación en EN/ES/ZH/JA/KO sobre
cómo funciona hoy el sistema de recomendación y qué palancas tienen dato detrás.

**Primero, el reencuadre, porque cambia el plan:** el algoritmo no se hackea.
Es un predictor que estima, para cada espectador, la probabilidad de que haga
clic, de que se quede y de que **siga viendo YouTube después de ti**. No hay
truco de publicación, etiqueta ni palabra mágica: hay tres puertas en serie
—impresión → clic → retención → satisfacción— y cada una tiene su palanca.
"Que se haga viral" tampoco es una palanca; lo que se puede subir es el **suelo**
de cada vídeo y la **frecuencia de outliers**.

---

## 1. Qué mide el sistema en 2026 (coincidente en las cinco lenguas)

- **La duración media de visualización (AVD) es la señal más fuerte del formato
  largo.** No el porcentaje: los segundos absolutos.
- **El tiempo de sesión pesa más que tu propio vídeo**: cuánto YouTube sigue
  viendo esa persona *después* de ti. Es la señal peor entendida por creadores.
- **Febrero 2026**: el feed de inicio pasó de categorías temáticas a *clusters*
  de historial de visionado, y YouTube confirmó que las **encuestas de
  satisfacción pesan más que el watch time bruto**.
- **Enero 2026**: "Popularity" sustituye a "View Count" como métrica de orden.
  Un vídeo de 1M de vistas con 10 s de media queda por debajo de uno de 500k con
  50% de retención.
- **El CTR se pondera por origen**: el de audiencia fría se amplifica, el de tus
  propios suscriptores se descuenta.
- **"Quality CTR" (fuente japonesa) / 낚시성 썸네일 (coreana):** CTR alto con
  retención baja **recorta** la recomendación. El clickbait no es neutro: es
  negativo. Es la trampa más común y la que más rápido mata un canal nuevo.
- **Umbral chino de referencia: >50% de retención** = el sistema lo trata como
  contenido de calidad.
- **Corea, y esto nos toca directo:** el algoritmo de 2026 da peso extra a los
  canales que **conectan espectadores de Shorts hacia el formato largo**.

## 2. El dato que decide el diseño (y es incómodo)

Estudio de mercado hispanohablante 2026: en formato largo las **vistas medias
suben +76%** (3.404 → 5.985) mientras la **duración media de visualización cae
-37%, hasta 2,5 minutos**.

Traducido: en español, un vídeo de 9 minutos se verá **dos minutos y medio de
media**. Los 9 minutos no son el objetivo — son el envase. **El vídeo se gana o
se pierde en el minuto 3.** Todo el diseño de abajo sale de aquí.

## 3. Miniatura: la única puerta con cifras grandes

Datos agregados de terceros (no nuestros, y conviene tratarlos como orden de
magnitud, no como promesa):

| Cambio | Efecto medido en CTR |
|---|---|
| Cara con emoción clara vs. sin cara | ×2,3 |
| Añadir gancho de 3 palabras | +32% |
| Pasar a alto contraste | +23% |
| Mover el texto arriba-izquierda (fuera del timestamp) | +18% |
| Test & Compare de YouTube (A/B nativo) | +40-74% |

Orden correcto de prueba, una variable cada vez: cara → contraste → longitud del
texto → posición. Mínimo ~1.000 impresiones y 48-72 h por prueba.

**Para nosotros:** no tenemos cara humana, pero **sí un personaje con hoja de
expresiones** (la hoja madre de Tadeo trae seis). Esa es nuestra "cara con
emoción", y es una ventaja de marca: la misma cara reconocible en cada miniatura.

## 4. Narración: ya estamos en la banda buena, no tocar

- Documental clásico: ~120 wpm. **Alta retención en YouTube: 160-190 wpm
  percibidos**, logrado con velocidad real + recorte de silencios.
- **Por encima de 200 wpm cae la comprensión** de forma consistente.
- Nuestra voz Qwen va a ~2,7 palabras/s = **~162 wpm**. Estamos dentro de la
  banda por accidente afortunado. **No subir la velocidad.**

## 5. Música: no es palanca de retención

La evidencia académica es floja y mixta: en vídeo instructivo **no aparecen
diferencias significativas** de retención entre con música y sin ella, y donde
ayuda es cuando **no compite con la narración**. O sea: la música es identidad de
marca y textura emocional, no una herramienta de watch time. Ducking agresivo y
fuera en los momentos de dato.

## 6. Los primeros 30 segundos

Es el tramo donde más gente se va, y las fuentes japonesa y coreana coinciden en
lo mismo: **nada de saludo ni presentación de canal**. Se abre con la
consecuencia o con el plano más fuerte, y el problema se plantea explícito en
los primeros segundos.

---

## 7. Aplicación a KOREX largo (esto es lo que se hace)

**Estructura de 9 minutos, diseñada para ganar el minuto 3:**

1. **0:00-0:15 — Cold open sobre la consecuencia.** El final, sin resolverlo.
   Cero intro, cero logo, cero "hola a todos".
2. **0:15-0:40 — La promesa y el primer lazo abierto.** Qué se va a revelar y
   por qué el espectador no lo sabe todavía.
3. **Cinco o seis capítulos de ~90 s.** Cada uno cierra con un lazo abierto que
   solo se paga en el siguiente. Ese es el re-gancho: no es una frase, es
   estructura.
4. **El pago grande antes del minuto 6**, no en el 9. Si la media se va a los
   2,5 min, el premio no puede vivir al final.

**Producción (sin motor nuevo, como ya concluyó la investigación del 28 jul):**
- 45-55 planos a 10-12 s. Solo **20-25 imágenes generadas**: cada una se reusa
  2-3 veces con reencuadre distinto. Cortar dentro del plano es lo que hacen los
  canales de verdad, no una imagen por frase.
- Guion de **~1.450 palabras** (540 s × 2,7 p/s). Es un modo nuevo de guion:
  capítulos, no bucle. La regla del bucle de los Shorts **no aplica aquí**.
- Sin subtítulos quemados: en 9 minutos cansan y YouTube ya pone los suyos.

**Lo nuevo respecto a Shorts, y es obligatorio:**
- **Miniatura**, con Tadeo en una de sus seis expresiones + 3 palabras + alto
  contraste, y **Test & Compare desde el primer vídeo**.
- **Puente Shorts → largo**: los Shorts ya publicados enlazan al largo (pantalla
  final y comentario fijado). Es la palanca que el sistema premia explícitamente
  en 2026 y es la única que ya tenemos montada y sin usar.

**Cómo mediremos, sin engañarnos:** el objetivo no es "viral". Son dos números:
**AVD por encima del 50%** (umbral de calidad) y **CTR de audiencia fría**. Si el
CTR sube y la AVD baja, hemos hecho clickbait y el sistema nos va a recortar —
eso se revierte, no se celebra.
