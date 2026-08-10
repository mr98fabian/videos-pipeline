# Políticas de YouTube que aplican a estos canales

Leído directamente de `support.google.com` el **4 ago 2026**. Lo de aquí es lo
que **verifiqué en la fuente**, no lo que recuerdo. Donde no pude leer la página
lo digo explícitamente en vez de rellenar.

Dos sistemas distintos y con consecuencias distintas:

- **Community Guidelines** → el vídeo se retira y puede caer un *strike*. Tres
  strikes en 90 días = canal borrado.
- **Políticas de monetización** → el vídeo (o el canal entero) deja de generar
  ingresos, sin retirarse. YouTube evalúa **canales completos**, no vídeos
  sueltos.

---

## 1. El riesgo estructural de KOREX (leer esto antes que nada)

La política de monetización dice, literal, que **no se monetizan los canales que
usan "personas generadas por IA para dar información sobre temas sensibles"**, y
nombra explícitamente la **orientación financiera** junto a la médica y la legal.

KOREX es exactamente eso: un personaje generado por IA explicando finanzas.

Esto **no es un problema de un vídeo**, es del formato. No lo arregla cambiar un
guion. Las salidas posibles, por orden de menos a más doloroso:

1. **Encuadrar como historia, no como consejo.** Contar lo que le pasó a una
   empresa real en pasado no es "orientación financiera". Lo que sí lo es:
   recomendar qué comprar, qué evitar, "cómo no perder tu plata", cualquier cosa
   en segunda persona sobre el dinero **del espectador**. La línea es
   *narrativa* vs *asesoría*.
2. **Que Tadeo no sea la voz de autoridad.** Personaje dentro de la historia, no
   presentador que explica al espectador lo que debe hacer.
3. Aceptar que la línea de finanzas no monetiza y usarla solo para crecer.

## 2. Inauthentic content (antes "repetitious") — julio 2025

No monetizable:

- Contenido **producido en masa o repetitivo**: plantilla con poca o ninguna
  variación entre vídeos, o "fácilmente replicable a escala".
- **Lecturas de material que no creaste** (texto de webs o feeds leído literal).
- **Presentaciones de imágenes** (slideshows).

**No es una prohibición de la IA.** Un canal que usa IA dentro de una producción
genuinamente original, con guion propio y decisiones editoriales reales, sigue
siendo elegible.

Traducción para este repo: el pipeline **es** una plantilla. Lo que separa esto
de "AI slop" es el guion y la investigación, no el motor. Y el motor KOREX/
Archivo Vivo, al ser animación compuesta, está más lejos del slideshow que un
Ken Burns sobre fotos.

## 3. Divulgación de contenido sintético

- **Hay que declararlo** cuando el contenido es **realista** y: hace que una
  persona real parezca decir o hacer algo que no hizo, altera imágenes de
  hechos o lugares reales, o genera escenas realistas que nunca ocurrieron.
- **No hace falta** en contenido claramente no realista: fantasía, **animación**,
  efectos evidentes. Tampoco para retoques menores, subtítulos, o ayuda de
  guion.
- Saltárselo de forma sostenida → etiquetado forzado, retirada, o expulsión del
  YPP.

Para estos canales: **KOREX no necesita declararlo** (dibujo animado evidente).
**HiddenFacts sí**, siempre que la imagen generada represente de forma realista
a una persona o un hecho histórico real. Se marca en Studio → Atributos → uso de
IA.

## 4. Spam y prácticas engañosas

Lo que roza este trabajo:

- **Metadatos engañosos**: título, miniatura o descripción que prometen algo que
  el vídeo no entrega. El gancho puede ocultar, **no puede mentir**.
- **Estafas**: prohibido promocionar esquemas de "hazte rico rápido". Ojo con
  la línea de finanzas.
- **Contenido raspado**: republicar material ajeno sin aportar comentario o
  edición transformadora. Aplica directo a `viral_lab.py`.
- **Producción masiva automatizada** con variaciones mínimas.

## 5. El catálogo completo de Community Guidelines

Para saber dónde mirar cuando llegue un aviso concreto:

| Grupo | Políticas |
|---|---|
| Spam y prácticas engañosas | spam, suplantación, enlaces externos, interacción falsa, playlists |
| Contenido sensible | desnudos y sexo, miniaturas, seguridad infantil, suicidio/autolesión/TCA, lenguaje vulgar |
| Contenido violento o peligroso | contenido dañino o peligroso, violento o gráfico, organizaciones criminales violentas, incitación al odio, acoso |
| Bienes regulados | venta de bienes ilegales o regulados, armas |
| Desinformación | desinformación general, electoral, médica |

**EDSA** (Educativo, Documental, Científico, Artístico) es la excepción que
permite material que de otro modo infringiría. **No es un salvoconducto**: la
propia política dice que no habilita a promocionar lo prohibido.

## Lo que NO pude verificar

No conseguí abrir la página de **organizaciones criminales violentas /
extremismo violento**, que es justo la que rige el material de nazis y de la
Segunda Guerra Mundial de HiddenFacts. Las dos veces el fetch devolvió otra
política. **Queda pendiente leerla en la fuente** antes de dar por buena
cualquier regla sobre ese material.

---

Sources:
- [YouTube's Community Guidelines](https://support.google.com/youtube/answer/9288567?hl=en)
- [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392?hl=en)
- [Spam & deceptive practices policy](https://support.google.com/youtube/answer/2801973?hl=en)
- [Disclosing altered or synthetic content](https://support.google.com/youtube/answer/14328491?hl=en)
- [Community Guidelines strike basics](https://support.google.com/youtube/answer/2802032?hl=en)
