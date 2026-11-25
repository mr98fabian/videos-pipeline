# MISIÓN 0005 — Generar las 9 láminas de pose de Tadeo

Rama `feat/laminas-9-poses` · PR contra master · estado: **en-auditoria, a medias** (ver «Qué falta»).
Fuente de verdad: `misiones/2026-11-25-especificacion-9-laminas.md` (aprobada por Fabian el 25 nov 2026).

## Reporte

**Resumen:** las 9 láminas están generadas y pasan las comprobaciones de píxel de la sección 5 de la
especificación. **No están trazadas ni medidas contra la hoja madre.** Eso, que es el criterio de aceptación
principal de la misión, no se puede hacer con las herramientas que hay hoy (ver «Qué falta»).

### Criterios de aceptación

| Criterio | Estado |
|---|---|
| Las 9 láminas generadas, PNG, con el nombre de la especificación | **cumple** (tabla de abajo) |
| Cada una pasa solape ≥ 0,95 y marcas dentro de tolerancia | **NO medido**: no hay trazador de láminas de pose |
| Paso 0: calibrar la tolerancia ±8 % con `pointing_api.png` | **NO hecho**, por lo mismo |
| `scripts/verify.py --ci --base origin/master` en verde | cumple en local; la CI, en el PR |

### Qué falta, y por qué

1. **`kx_trazo.py` y `kx_parecido.py` no están en master.** Viven en la rama de la Fase 2 (PR #7, sin fusionar). Esta
   rama sale de master, así que ni siquiera los tiene.
2. **Aunque estuvieran, no sirven para estas láminas.** `kx_trazo.py` está escrito para UNA imagen: recorta la vista
   frontal de `model_sheet.png` (`FRENTE`), calibra con la nariz y corta con cinco medidas fijas de esa hoja (bases
   de oreja, coronilla, barbilla, axilas). Trazar una pose arbitraria exige un trazador nuevo: segmentar cabeza,
   torso, cada brazo, cada guante y la cola sin esas constantes. Es la mayor pieza del método «una pose = un dibujo»
   y hay que diseñarla antes de construirla: qué devuelve, cómo se mide el solape de una pose contra su propia
   lámina y cómo se calibra la tolerancia lámina-madre.
3. **Por eso el Paso 0 no se pudo hacer.** Medir «solape y desviación de marcas» de `pointing_api.png` contra la
   madre requiere ese mismo trazador. La tolerancia ±8 % sigue siendo una propuesta sin calibrar.

Lo que sí se midió: `scripts/medir_lamina.py` (nuevo, con 5 pruebas que distinguen una lámina buena de una mala)
comprueba lo de la sección 5 de la especificación que se puede medir en el píxel: figura única, fondo blanco,
nada recortado y sin color.

### Las 9 láminas

Medidas de `misiones/evidencia/0005/medidas.json` (`py scripts/medir_lamina.py`). Fondo = luminancia mínima del
borde (≥ 245); figuras = piezas separadas (1 = una sola); margen = fracción libre hasta el borde (umbral 0,015);
color = % de píxeles de la figura con croma > 10 (umbral 0,4 %). USD = suma de todos los intentos de esa pose.

| Pose | Imagen | Tamaño | Fondo | Figuras | Margen | Color | USD | Revisión visual (spec, sección 4) |
|---|---|---|---|---|---|---|---|---|
| `decidido` | `misiones/evidencia/0005/decidido_api.png` | 896×1200 | 251 | 1 | 0.047 | 0.00 % | 0.0359 | cumple: puño izquierdo en la cadera, puño derecho alzado a la altura del hombro sin tocar la cara, cejas bajas, boca firme |
| `confundido` | `misiones/evidencia/0005/confundido_api.png` | 896×1200 | 250 | 1 | 0.037 | 0.00 % | 0.0359 | cumple: encogimiento de hombros simétrico, dos palmas arriba a la misma altura fuera del torso, cabeza algo ladeada |
| `orgulloso` | `misiones/evidencia/0005/orgulloso_api.png` | 896×1200 | 251 | 1 | 0.044 | 0.00 % | 0.0359 | cumple: dos guantes en las caderas, codos fuera con hueco blanco a cada lado, ojos entornados, sonrisa ancha |
| `estafado` | `misiones/evidencia/0005/estafado_api.png` | 896×1200 | 251 | 1 | 0.050 | 0.15 % | 0.0718 | cumple (2.º intento): brazos lacios con los dedos hacia abajo, cabeza baja, cola en el suelo. Menos hundido de lo especificado |
| `grito` | `misiones/evidencia/0005/grito_api.png` | 896×1200 | 251 | 1 | 0.064 | 0.00 % | 0.0718 | cumple con reserva (2.º intento): manos en bocina a los lados de las mejillas; los guantes rozan el borde del antifaz, sin tapar boca ni nariz. Torso erguido, no inclinado |
| `explicando` | `misiones/evidencia/0005/explicando_api.png` | 896×1200 | 251 | 1 | 0.026 | 0.27 % | 0.0718 | cumple (2.º intento): brazo derecho alzado con la palma arriba y espacio libre a su lado, brazo izquierdo bajo, no señala con el dedo |
| `codicia` | `misiones/evidencia/0005/codicia_api.png` | 896×1200 | 251 | 1 | 0.074 | 0.37 % | 0.0359 | cumple: manos vacías frotándose al centro del pecho, sonrisa ladina, sin objetos |
| `asombro` | `misiones/evidencia/0005/asombro_api.png` | 896×1200 | 252 | 1 | 0.022 | 0.00 % | 0.0718 | cumple (2.º intento): brazos abiertos con palmas al frente y dedos separados, boca «o»; figura pequeña en el cuadro |
| `triunfo` | `misiones/evidencia/0005/triunfo_api.png` | 896×1200 | 250 | 1 | 0.102 | 0.00 % | 0.0359 | cumple: pies despegados, dos puños sobre la cabeza sin tapar las orejas, ojos cerrados riendo |

Hoja de contacto: `misiones/evidencia/0005/contacto_9_laminas.png`. Costo total de la misión: **0.4668 USD**
en 13 llamadas (9 primeras y 4 repeticiones), registrado en `misiones/evidencia/0005/costos.csv`. Crédito de
partida: 9,61 USD.

### Decisiones y desviaciones (declaradas)

1. **Bloque de estilo y 9 párrafos de pose** copiados de las secciones 3.1 y 4 de la especificación a
   `scripts/generar_lamina.py` (`ESTILO`, `POSES`). `pointing` conserva su párrafo de la misión 0004 (3/4), que ahora
   contradice el bloque común «de frente»: no se regenera.
2. **Relación de aspecto:** se añadió `--aspecto` (`imageConfig.aspectRatio`). La API acepta `3:4`, que da 896 × 1200
   vertical; era el riesgo que la especificación dejaba abierto (apartado 3.2).
3. **Cuatro repeticiones** (`estafado`, `grito`, `asombro`, `explicando`). Las primeras salieron con tinte crema en
   vientre y mejillas (24–29 % de la figura; la especificación pide solo grises) o con la mano a menos de 3 % del
   borde. Se repitieron con este añadido al prompt: «Every gray must be a pure neutral gray: the belly patch and the
   cheeks are LIGHT NEUTRAL GRAY or white, never cream, beige, yellow or any warm tint. Draw the character noticeably
   smaller so that at least 8% of empty white margin remains on every side». El color se corrigió; el margen no del todo.
4. **Umbral de margen 0,015, no 0,03.** Mi primer umbral (3 %) era una heurística mía, no de la especificación.
   `asombro` (0,022) y `explicando` (0,026) lo incumplían incluso tras repetir, pero no tienen nada recortado, que es
   lo que pide la regla 3. Lo bajé a 1,5 % y lo declaro: esas dos láminas quedan al límite del cuadro.
5. **Reservas visuales:** `grito` tiene el torso erguido (la especificación pedía inclinado) y los guantes rozan el
   antifaz; `estafado` está menos hundido de lo especificado. Ninguna impide trazar el cuerpo, pero Fabian debe verlas.
6. `tests/test_medir_lamina.py` se salta sin cv2/numpy (la CI solo tiene pytest).

### Para cerrar

1. Fabian mira `contacto_9_laminas.png` y aprueba o pide repetir alguna (≈ 0,036 USD cada una).
2. Se diseña el trazador de láminas de pose (misión de diseño, Fable) y se construye; con él se hace el Paso 0 y se
   miden las 9 (solape y marcas). Hasta entonces la Fase 3 no arranca.
3. Si el trazador se construye sobre `kx_trazo.py`, el PR #7 (Fase 2) debe fusionarse antes.
