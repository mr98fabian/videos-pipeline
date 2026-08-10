# Giros ganadores — registro de estructuras, no de temas

Creado el 2 ago 2026, inspirado en algo real de un vídeo de mentoría que analizamos
hoy (Pablo Sanjuan): llevan en Notion un registro de **ángulos que ya saben que
funcionan** y reciclan la estructura con una premisa de superficie distinta cada
vez, en vez de inventar desde cero en cada guion.

Adaptado a como escribimos: no registramos *temas* (eso lo sigue decidiendo el
oficio, guion a guion). Registramos **formas de giro** — la arquitectura
narrativa — para poder recombinarlas.

**Regla de honestidad, la misma de `hipotesis.json`:** ninguna estructura de aquí
está "confirmada" hasta que tenga una curva de retención real detrás. Todo lo de
abajo es **diseño aplicado, no dato**. Si algún día una estructura se mide y
falla, se marca DESMENTIDA y se borra de la lista de recomendadas — no se
reinterpreta para que parezca que funcionó.

## Estado real ahora mismo

**Cero estructuras de chisme tienen retención medida todavía**, aunque el estado
de publicación cambió sin que quedara registrado en la conversación: a fecha
3 ago, `christening-announcement` y `storage-unit-headstone` están **públicos**
(2-3 ago), `family-group-chat` está subido pero **en privado**, y solo
`wedding-photos-father` sigue sin subir. `actualizar_giros.py` (sin argumentos)
refresca este estado bajo demanda. Lo único medido hasta hoy (`visitor-log`,
`-79EJI_BSsE`, `Mp8flDaqtvE`) es un defecto de **montaje** (el acantilado de
estímulo en el segundo 2,7 + el hueco de premio en 5-10s) que aplica a los tres
sin importar qué estructura de giro llevaran dentro. Eso confunde cualquier
lectura de "qué guion retiene mejor" hasta que un vídeo sin ese defecto se mida.

**El storage-unit-headstone es la prueba pendiente** — ya lleva los dos arreglos
de montaje y ya está público. En cuanto Analytics procese su curva (48-72h desde
el 2 ago), `py actualizar_giros.py --escribir` compara automáticamente la caída
5,5-10s contra el criterio de éxito de `PLAN_SEGUNDO_6.md` (<20 puntos). Ninguno
de los cinco guiones tiene todavía un dato que diga algo sobre la ESTRUCTURA DE
GIRO en sí — solo sobre el montaje.

## Catálogo de estructuras usadas (sin medir, solo catalogadas)

### G1 — Cold-open + rebobinado
La primera frase es la consecuencia final; el resto explica cómo se llegó.
Deja un bucle abierto extra sobre "qué pasó" en vez de resolverlo de inmediato.

- Usado en: `the-visitor-log`, `wedding-photos-father`, `storage-unit-headstone`
- Por qué se adoptó: el único comparable real medido (1,6M vistas, `Story Mode
  On`) también abre así, no con un hecho llano.
- Riesgo conocido: si el "cómo se llegó" tarda en aportar nada nuevo, cae en
  relleno — es justo lo que la regla 9g existe para cazar.

### G2 — El narrador reencuadrado, no el acusado
El giro final no castiga más al "villano" de la historia — voltea el peso moral
sobre quien cuenta, o revela que el acusado tenía razones que nadie le dio
oportunidad de explicar.

- Usado en: `storage-unit-headstone` (la hermana no mintió nunca; él pagaría la
  mitad y por eso ella calló), `wedding-photos-father` (el padre pidió que lo
  sacaran del álbum para no eclipsar la boda)
- Por qué interesa: es lo que separa un giro de un simple "sorpresa" — el
  espectador tiene que revisar su propio juicio, no solo el dato.

### G3 — Giro fair-play con pistas plantadas
El giro no oculta información, la esconde a la vista. 1-5 pistas concretas
sembradas antes de la revelación, legibles en la segunda pasada.

- Usado en: `christening-announcement` (5 pistas: vino sola, el marido
  "aparcando", no cogió a la niña, el bolso con los dos brazos, se fue antes de
  comer), `storage-unit-headstone` (1 pista: nunca pidió dinero para el
  funeral)
- Regla técnica: la pista tiene que poder señalarse después sin reescribir el
  guion — si hace falta añadir texto nuevo para que la pista "cuadre", no era
  fair-play, era parche.

### G4 — Loop donde la apertura se revela mentira
Va un paso más allá de G1: la frase de cierre no solo conecta con la de
apertura — la reencuadra como la EXCUSA OFICIAL que el narrador repite,
convirtiendo el reinicio del vídeo en el propio personaje contando la mentira
otra vez.

- Usado en: `family-group-chat` — cierra en "le digo a la gente que me añadió
  por error", que es literalmente la primera frase del vídeo, ahora sabida
  falsa.
- Es la estructura más fuerte escrita hasta hoy, a falta de dato. Prioridad
  para repetir en cuanto haya confirmación de que el montaje ya no rompe la
  retención.

### G5 — Marco emocional en el seg. 0 + dato duro antes del seg. 3
Excepción de la regla 9 para el formato chisme: abre con la reacción/escándalo,
no con un hecho seco, pero mete la cifra o el nombre concreto dentro de los
primeros ~3 segundos para no perder el "prime" del hueco de información.

- Usado en: `christening-announcement`, `family-group-chat`
- Condición dura: sigue exigiendo el dato temprano. Sin él, el lint
  `_check_open_hook(..., formato="chisme")` avisa.

### G6 — Escalada en cifras contables, no en adjetivos
La tensión sube con números que se pueden sumar (dinero, minutos, años,
visitas), no con superlativos.

- Usado en todos los guiones desde `storage-unit-headstone` en adelante.
- Por qué: es el hueco medido contra el comparable real — su ganador de 1,6M
  tenía 16 menciones de dinero, nuestros primeros guiones tenían 1.

## Cómo se actualiza esto

Cuando un vídeo de este formato consiga curva de retención real:

1. Anotar aquí, bajo la estructura correspondiente, el resultado con fecha y
   vídeo — no solo "funcionó/no funcionó", el número.
2. Si dos o más vídeos con la MISMA estructura repiten resultado (bueno o
   malo), pasa de "catalogada" a **CONFIRMADA** o **DESMENTIDA** arriba del
   todo del bloque.
3. Las DESMENTIDAS se sacan de circulación para guiones nuevos — no se
   mantienen "por si acaso".
4. Nunca fabricar un resultado para rellenar esta tabla. Vacío es mejor que
   inventado.

## Pendiente de dato (actualizar aquí, no en otro sitio)

| Vídeo | Estructura(s) | Estado |
|---|---|---|
| `christening-announcement` | G1, G2, G3, G5, G6 | publico, Analytics sin procesar aun |
| `family-group-chat` | G1, G4, G5, G6 | private, sin datos publicos |
| `storage-unit-headstone` | G1, G2, G3, G6 | publico, Analytics sin procesar aun |
| `wedding-photos-father` | G1, G2, G6 | sin publicar |
| `the-visitor-log` | G1 (sin G3 en la ventana 5-10s — por eso motivó la 9g) | publico, Analytics sin procesar aun |
