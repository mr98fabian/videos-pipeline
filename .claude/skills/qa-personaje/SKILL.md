---
name: qa-personaje
description: Revisar imágenes generadas antes de montar un vídeo y garantizar que el personaje (Tadeo, la Bruja del Banco) sea el mismo en todas. Úsala SIEMPRE después de generar imágenes con Flow y antes de ensamblar, y cuando Fabián diga que "el personaje se ve raro", que "hay Tadeos que no son Tadeo" o que una imagen no corresponde a lo que se narra.
---

# Puerta de calidad de imágenes

Ninguna imagen entra al montaje sin pasar por aquí. El motivo no es teórico:
el 12 ago 2026 se colaron un Tadeo con chaqueta, dos con otra cara, unos gatos
negros donde debía haber mapaches y **52 imágenes en 9:16 para un vídeo 16:9** —
todo detectado después de generarlas, no antes.

## El orden importa: primero la máquina, luego los ojos

```bash
py qa_personaje.py output/<carpeta>/storyboard --aspecto 16:9
```

Eso comprueba solo lo que no necesita criterio y suele ser lo que más escuece:

| Comprobación | Qué caza |
|---|---|
| formato | la tanda entera en vertical cuando el vídeo es horizontal |
| color | el canal es B/N y una imagen viene con tinte |
| lámina | fondo blanco = se coló una lámina de personaje en vez de una escena |
| repetida | dos escenas con la misma imagen |

Ojo con `lamina`: en los planos que explican se pide fondo liso a propósito, así
que un borde casi blanco ahí es correcto y no un fallo. Confírmalo mirando.

Luego genera **hojas de revisión de 6 imágenes a 340 px**. Ese tamaño no es
capricho: a 175 px una mano de más o un hocico distinto son invisibles, y así
fue como se colaron los tres brazos de la Bruja.

## Lo que hay que mirar, imagen a imagen

Comparar contra `assets/characters/tadeo/default_model_sheet.png`. Rechazar si:

1. **La cara no es la suya**: hocico alargado, antifaz distinto, ojos de otro
   tamaño, orejas puntiagudas. Si dudas, está fuera. **Este es el único criterio
   que importa de verdad** — el espectador reconoce a Tadeo por la cabeza.
   *La ropa está permitida* (decisión de Fabián, 13 ago 2026): puede llevar
   chaqueta o gorra si la escena lo pide. Lo que no puede es cambiar de cara.
   Y la regla vale solo para **él**: el vecino, la multitud y los secundarios no
   tienen por qué parecerse a Tadeo, solo ser mapaches del mismo estilo.
2. **No es un mapache**: han salido ardillas y gatos.
3. **Hay más de un protagonista** en el cuadro, o clones suyos de fondo.
5. **Manos o brazos de más.** Contarlos, literalmente: dos manos.
6. **Texto incrustado**, aunque sea un cartel de atrezo.
7. **La escena no corresponde** a la frase que suena (mirar el storyboard).

## Nunca dos trabajos de Flow a la vez

Todos los procesos comparten `.flow_profile`. Si lanzas una generación mientras
otra sigue viva, la segunda falla sin explicación y **parece que Flow se cayó o
que se agotó la cuota**. Pasó el 12 ago: se dio por caído el servicio y en
realidad era un trabajo propio en segundo plano. Antes de lanzar, comprobar que
no hay otro corriendo.

## Regenerar, y con qué

```bash
py qa_personaje.py output/<carpeta>/storyboard --rehacer 9,14,20
```

Borra esas y el generador vuelve a pedirlas. Antes de relanzar, aplicar lo que
ya está medido:

- **Prefijo `Tadeo character:`** al principio del prompt. Sin él salen mapaches
  genéricos.
- **La lámina limpia de cuerpo entero como referencia PRINCIPAL** y la hoja
  madre como segunda. Al revés falla: la hoja es un turnaround de figuras
  pequeñas y el modelo copia lo que ve grande.
- **"EXACTAMENTE UN mapache en el cuadro y es Tadeo"**, literal.
- En multitudes, lo contrario: **"mapaches genéricos, ninguno el protagonista"**,
  o saldrán clones. **Pero eso solo no basta:** esa rama necesita su propio
  mínimo —especie, nada de ropa, guantes de cuatro dedos— porque sin él se cuelan
  overoles y gatos negros. Medido el 13 ago: **15 de 19 rechazos** venían de ahí,
  no de los planos de Tadeo.
- **Las reglas van en TODOS los prompts, no solo en los que nombran al
  personaje.** Los planos de *objetos* —una red enrollada, una pila de platos,
  un calendario— no dicen ni "Tadeo" ni "mapache", así que caían en una tercera
  rama sin ninguna regla, y el modelo metía por su cuenta un mapache con
  sombrero. Da igual qué regla sea: si el prompt no la lleva, el estilo decide
  por ti.
- Si un plano falla tres veces seguidas, **cambiar el plano, no insistir**. La
  escena de las monedas falló seis veces hasta que se quitó la mano del prompt:
  el plano era de las monedas, no de quién las sostenía.

## Cuándo parar

Cuando el listado automático salga vacío **y** ninguna imagen te haga dudar al
mirarla. Un "casi" es un no: el espectador nota el cambio de personaje aunque no
sepa nombrarlo, y es exactamente lo que rompe la ilusión de canal.

Para el 100% literal solo hay un camino, y conviene decirlo: **pegar el PNG
aprobado**. La generación por referencia da parecido muy alto, nunca idéntico.
Reservarlo para el plano que se resista.
