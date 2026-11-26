# Diseño del trazador de láminas de pose de Tadeo

Diseño, 25 nov 2026. **No hay código ni láminas nuevas en este documento.** Fabian lo aprueba antes de construir.
Insumos: `misiones/2026-11-25-especificacion-9-laminas.md` (en master), las 9 láminas de la PR #10
(`misiones/evidencia/0005/`), `pointing_api.png` (misión 0004) y `kx_trazo.py` / `kx_parecido.py` de la rama de
la Fase 2 (PR #7, sin fusionar).

## 0. Decisiones que necesito de Fabian

1. **El trazador nuevo es un módulo aparte, pero PR #7 se fusiona primero** (sección 5). La cabeza del rig y sus
   40 expresiones salen de `traza.js`, que vive en esa rama: sin #7 no hay cabeza donde colocar el cuerpo.
2. **Cada pose sale en 3 piezas, no en 14** (sección 2): cuerpo (torso, brazos, guantes, piernas y pies, una sola
   pieza), cola y tapón de cuello. Se acaba la articulación por piezas: es lo que producía las costuras de la 3b.
   El precio: los brazos no se mueven por separado dentro de una pose; la respiración es una escala del cuerpo
   entero.
3. **La unidad de medida es el ancho del antifaz**, no la altura (sección 2.3): la altura depende de la pose.
4. **La tolerancia ±8 % del encargo no se sostiene tal cual.** La sonda de la sección 1 da una desviación de
   −6 % a +12 % en el largo del pie, y el largo del guante varía 70 % entre puño y mano abierta, así que ese
   «marca» no sirve. Propongo un juego de marcas distinto (sección 3.2) y una tolerancia que se calcula con
   datos en la misión de construcción, con una regla de separación fijada hoy (sección 4).
5. **`pointing_api.png` es la referencia buena, pero está en 3/4.** Sus marcas frontales se desvían +12 % de la
   madre; se usa para calibrar solo las marcas que no dependen de la vista (sección 4).

## 1. Lo que muestra una sonda en las láminas (medida, no supuesta)

Medí con un script desechable (OpenCV, sin guardar en el repo) tres cosas en la madre, las 9 láminas y `pointing_api`:
el ancho del antifaz `A` (los dos lóbulos oscuros del antifaz, medianas 70–130), el largo del guante (componente
casi blanco mayor bajo la cabeza) y el largo del pie (los dos oscuros mayores del 22 % inferior). Largos en
unidades de `A`.

| Lámina | A (px) | alto figura / A | guante / A | pie / A |
|---|---|---|---|---|
| madre (vista frontal) | 622 | 2,64 | 0,545 | 0,592 |
| decidido | 358 | 2,70 | 0,416 | 0,586 |
| confundido | 345 | 2,71 | no detecta | 0,556 |
| orgulloso | 361 | 3,00 | 0,366 | 0,623 |
| estafado | 343 | 3,04 | 0,602 | 0,567 |
| grito | 353 | 2,87 | no detecta | 0,629 |
| explicando | 383 | 2,69 | 0,355 | 0,581 |
| codicia | 383 | 2,62 | 0,424 | 0,589 |
| asombro | 307 | 2,84 | no detecta | 0,557 |
| triunfo | 300 | 3,07 | no detecta | 0,573 |
| pointing (3/4) | 246 | 3,12 | 0,387 | 0,664 |

Lecturas:

- **El antifaz se detecta en las 11 imágenes**: sirve de ancla de escala y de cabeza (sección 2.2).
- **El largo del guante no es una marca**: 0,355 (puño) a 0,602 (mano abierta en `estafado`). Depende de la pose.
- **El alto de la figura tampoco**: 2,62 a 3,12 en unidades de `A`, porque cambia con brazos arriba y piernas dobladas.
- **El largo del pie sí es estable**: 0,556 a 0,629 en las 9 frontales, es decir −6 % a +6 % de la madre; con una
  tolerancia de ±8 % queda un margen de solo 1,7 puntos. `pointing` (3/4) llega a +12 %.
- **La segmentación por umbral simple falla en 4 de 10 láminas** para los guantes (se pegan a la cara o a la tinta
  en `grito`, `confundido`, `asombro`, `triunfo`). Esto justifica una segmentación por topología de tinta
  (sección 2.2) en vez de por tono.

Límites de la sonda: es cruda (umbrales a mano), no midió grosor de brazo, ancho de panza ni anillos de cola, y la
madre se midió sobre su vista frontal recortada. Las cifras orientan el diseño; **no son la calibración**, que se hace
en la construcción con el procedimiento de la sección 4.

## 2. Qué devuelve el trazador por lámina

### 2.1 Salida

`traza_<pose>.js` (generado, igual que `traza.js`) con, en **unidades del rig** (alto 1000 u, suelo en y = 0,
eje x = 0 en el centro de los pies):

| Campo | Contenido |
|---|---|
| `cuerpo` | relleno (tono base), sombras planas y `tinta` copiada (R1) de torso + brazos + guantes + piernas + pies, **una sola pieza** con agujeros (huecos entre brazo y torso) |
| `cola` | pieza aparte (para el vaivén dentro de la pose): relleno, anillos con su tono y tinta, y su punto de apoyo |
| `tapon` | pelaje bajo la barbilla (sin tinta) que cierra el cuello cuando el rig mueve la cabeza |
| `anclas` | `pies` (punto medio entre los dos pies, a ras de suelo), `barbilla`, `eje_cabeza` (ángulo base), `A_px`, `escala_u_por_px` |
| `marcas` | las marcas de la sección 3.2 medidas en esa lámina |
| `fuente` | nombre, tamaño y huella (SHA-1) de la lámina |

La **cabeza de la lámina se descarta**: se recorta por la línea de la barbilla y todo lo que queda por encima
(cráneo, orejas, mechón, cara) no entra en `cuerpo`. Las manos que pasan por delante de la cabeza (`grito`) se
conservan en `cuerpo` y se pintan **sobre** la cabeza del rig (capa delantera, igual que los guantes hoy).

### 2.2 Segmentación, sin las constantes de la madre

No usa `FRENTE`, ni la calibración por la nariz, ni los cinco cortes fijos. Etapas, en este orden:

1. **Silueta y tinta**: papel exterior por relleno desde las esquinas; tinta = luminancia < 75 (como `kx_trazo`).
2. **Regiones libres**: componentes conexos del interior que la tinta no cruza (la técnica que ya usa `kx_trazo`).
3. **Antifaz = ancla de la cabeza**: los dos componentes medio-oscuros mayores en la mitad alta. Con ellos se
   obtienen `A_px`, el centro de la cabeza y su eje (la recta que une los lóbulos da la inclinación). Si no hay
   exactamente dos: la lámina **falla** (sección 7), no se adivina.
4. **Corte de cabeza**: barbilla = punto más bajo de la región «cara» (conexa con los lóbulos y hasta el primer
   estrechamiento de la silueta por debajo del hocico). Esa línea sustituye a las cinco constantes de la hoja.
5. **Pies**: los dos componentes más oscuros en el 22 % inferior de la silueta.
6. **Cola**: el componente de la silueta fuera del torso con ≥ 3 bandas alternas de tono; su punto de apoyo es donde
   toca el cuerpo.
7. **Guantes**: componentes casi blancos rodeados de tinta, por debajo de la barbilla **o** que solapan la cabeza.
8. **Brazos**: de cada guante, el esqueleto de la banda que lo une al torso (como `banda_miembro` hoy, pero con
   esqueleto en lugar de filas fijas). Solo se usan para **medir**; no se separan en la salida.
9. **Todo lo demás** del interior, menos cabeza y cola, es `cuerpo`.

### 2.3 Normalización

Una sola transformación por lámina: se escala para que **su antifaz mida lo que mide el de la madre en el rig
(≈ 379,5 u: 622 px de la rejilla ×4 entre 1,639 px por u)** y se traslada para que el punto medio de los pies quede
en el origen. En fórmula: `u = (px − pies) · 379,5 / A_px`. La cabeza del rig ya tiene ese tamaño, así que el cuerpo de la lámina
queda a su escala y cualquier desproporción real del cuerpo aparece como desviación de marca (no se «arregla» al
escalar).

**Peso de línea: se copia tal cual.** La API dibuja el contorno más fino que la madre (7,3 u). Re-pesarlo obligaría a
inventar tinta (R1 dice copiar). Se registra el grosor en `marcas` y no se exige. Si Fabian prefiere el peso de la
madre, se hace en la misión de construcción como un engrosado uniforme de la tinta, nunca por pieza.

**Tonos**: se cuantiza a `TADEO_TONE` (6 tonos + INK; ningún hex nuevo en `tadeo/`). El vientre crema o gris de la
API se mapea al tono más cercano de los seis; no hace falta que sea el de la madre.

## 3. Cómo se mide

Dos pruebas distintas, con umbrales distintos.

### 3.1 Trazo contra su propia lámina (¿trazaste bien lo que la API dibujó?)

Es la barra I2-3 de la Fase 2 aplicada a la zona del cuerpo. Se dibuja `cuerpo + cola + tapon` con el rig sobre la
**misma rejilla de píxeles** de la lámina reescalada a la unidad de la sección 2.3, y se mide con un solo código en
las dos imágenes (como `kx_parecido.py`). La cabeza se enmascara: queda fuera de las medidas todo lo que está por
encima de la barbilla, y la banda de 12 u bajo ella.

| Medida | Definición exacta | Umbral |
|---|---|---|
| IoU de silueta | (A ∩ B) / (A ∪ B), con silueta = lo que el papel exterior no alcanza | **≥ 0,98** (mínimo duro 0,95, que es el del encargo) |
| Tinta lámina → trazo | fracción de píxeles de tinta (luminancia < 60) de la lámina con tinta del trazo a ≤ 3,7 u | ≥ 97 % |
| Tinta trazo → lámina | simétrica | ≥ 97 % |
| Área de tinta trazo / lámina | cociente de píxeles de tinta | 0,97 – 1,03 |
| Error tonal | luminancia / papel sin tinta, suavizada σ = 6 px: media, y fracción con error > 0,08 | ≤ 0,030 y ≤ 5 % |

(3,7 u = los 6 px de la rejilla ×4 de la madre.) Los umbrales son los que el neutro ya cumple (IoU 0,9898,
tinta 99,3 / 98,8 %); un trazo que *copia* una imagen debe parecerse a ella tanto como el neutro a la madre.

### 3.2 Lámina contra la hoja madre (¿el personaje es el mismo?)

Marcas **adimensionales, en unidades de `A`**, de partes cuya forma no depende de la pose. Se calculan con el mismo
código en la madre (su vista frontal) y en la lámina:

| Marca | Definición | Por qué entra |
|---|---|---|
| `pie` | largo del pie (eje mayor del rectángulo mínimo) / `A` | medido: estable (−6 % a +6 %) |
| `panza` | ancho del torso a la altura media entre barbilla y cadera / `A` | el cuerpo es una pera constante |
| `brazo_grosor` | grosor mediano del brazo a lo largo de su esqueleto / `A` | brazo de goma de grosor constante |
| `brazo_largo` | largo del esqueleto de brazo, hombro a muñeca / `A` | longitud fija del tubo |
| `cola_ancho` | ancho máximo de la cola / `A` | proporción de la cola |
| `cola_anillos` | número de bandas visibles | se cuenta, no se mide; debe ser 5 a 7 |

**Marcas descartadas, con su motivo medido:** largo del guante (0,355 a 0,602), altura total (2,62 a 3,12) y
cabeza / alto total (depende del alto). La sección 2.2 de la especificación las listaba; **esa sección se corrige** en
la misión de construcción con esta tabla.

La salida de cada lámina es un vector de desviaciones `d_i = (marca_lámina − marca_madre) / marca_madre`.

## 4. Cómo se calibra la tolerancia

La tolerancia no se fija hoy: se calcula con datos, con una regla de separación que **sí** se fija hoy.

**Conjuntos**
- **Buenos**: las 9 láminas frontales aprobadas visualmente por Fabian. `pointing_api` es 3/4: se usa solo para las marcas
  que no dependen de la vista (`brazo_grosor`, `brazo_largo`, `cola_ancho`, `cola_anillos`); para `pie` y `panza`
  se reporta pero no entra (su +12 % en `pie` es un dato, no un error).
- **Malos, fabricados** (cada uno, a partir de una lámina buena frontal, con una orden de OpenCV registrada):
  1. cabeza ×1,3 (la deriva típica de la API): infla `A`, todas las marcas bajan ≈ 23 %;
  2. cuerpo estirado ×1,25 en horizontal sin tocar la cabeza;
  3. cuerpo aplastado ×0,8 en vertical;
  4. brazos adelgazados al 70 % (borrado morfológico de la tinta y el relleno del brazo).
- **Malo natural**: el cuerpo de la lámina vieja `Cartoon_character_pointing_forward_*.jpeg` (local, de otra familia).

**Procedimiento**
1. Medir los vectores `d` de los buenos y de los malos.
2. Para cada marca `i`: `tol_i = máx(8 %, 1,25 × máx |d_i| de los buenos)`, con tope en 15 %. Se parte de 8 % (el encargo) y
   solo sube si los buenos lo exigen.
3. **Regla de paso de una lámina:** todas sus marcas dentro de `tol_i`. Es estricta a propósito: una desproporción
   del cuerpo se nota en el vídeo.

**Regla de separación (la prueba de que la calibración sirve)**
- Todo bueno pasa con **≥ 2 puntos de margen** en cada marca (`|d_i| ≤ tol_i − 2 %`).
- Todo malo fabricado falla en **≥ 2 marcas**, y la peor excede su `tol_i` en **≥ 5 puntos**.
- Si no se cumple, **no se ajusta el umbral hasta que encaje**: se reporta el número y Fabian decide (como con la
  superficie tonal en la Fase 2).

**Lo que anticipa la sonda:** en `pie` los buenos llegan a ±6,3 %, lo que deja `tol = 8 %` con un margen de 1,7 puntos,
por debajo de los 2 exigidos. Es probable que la calibración suba `pie` a ~ 9 %. Se dice ahora para que no sorprenda.

## 5. Decisión: ¿sobre `kx_trazo.py` o desde cero?

**Módulo nuevo (`kx_lamina.py`), reutilizando las funciones de apoyo de `kx_trazo.py`, y PR #7 se fusiona antes.**

- **Se reutiliza** (≈ 20 funciones sin nada de la hoja madre): `contornos`, `poly_iso`, `poly_ccomp`, `componentes`,
  `fill_holes`, `Espina`, `catmull`, `perfil`, `fraccion_tono`, `cuantiza`, `to_u` y compañía; más todo el código de
  medida de `kx_parecido.py` (tinta, grosor, tono).
- **No se reutiliza `trazar()`**: es el trazador de la madre, y las cinco constantes (`FRENTE`, bases de oreja, coronilla,
  barbilla, axilas) no existen en una lámina. Parchearla para que acepte cualquier imagen acabaría con una función de
  200 líneas llena de condiciones por pose.
- **Por qué PR #7 debe ir antes, y no solo por las funciones:** el método nuevo conserva la cabeza del rig: su
  traza (`craneo`, `orejas`, `ojos`, 40 expresiones) está en `traza.js` de esa rama, y el trazador nuevo mide sus
  marcas contra la vista frontal que `kx_trazo` extrae de la madre. Sin #7, el trazador de láminas no tendría
  cabeza donde apoyar nada, y las funciones compartidas habría que copiarlas.
- **Primer paso de construcción**: mover las funciones de apoyo a `kx_trazolib.py` sin cambiar comportamiento
  (los tests de la Fase 2 deben pasar sin tocarse), y que `kx_trazo.py` y `kx_lamina.py` importen de ahí.
- **Lo que queda obsoleto de #7** (cuerpo por piezas: tubos, manguera, cola por espina, el test sin-hueco xfail) **no
  se borra al fusionar**: lo declara el reporte de la fusión como «reemplazado por el método de láminas»; se limpia en
  una misión posterior cuando las 9 poses estén trazadas.

## 6. Criterios de aceptación de la misión de construcción

Pruebas que distinguen un trazador bueno de uno malo, todas ejecutables:

1. **Identidad**: pasar la **vista frontal de la madre** como si fuera una lámina. El trazador debe devolver un cuerpo
   con IoU ≥ 0,98 contra ella y marcas = las de la madre ± 1 %. Si no reproduce a la madre, no se le confía una pose.
2. **Invariancia**: la misma lámina desplazada, escalada ×0,7 – ×1,4 y girada ± 3° da el mismo `cuerpo` en u
   (centroide y área ± 1 %, marcas ± 1 %).
3. **Calibración**: se cumple la regla de separación de la sección 4 (buenos con margen, malos fabricados y malo
   natural rechazados). El informe lista las 15 desviaciones por marca.
4. **Las 9 láminas y `pointing_api`**: cada una o pasa la sección 3.1 y 3.2, o se rechaza con un motivo concreto
   (antifaz no encontrado, no hay dos pies…). Nunca «pasa» sin medirse.
5. **Cuerpo sólido**: dibujar `cuerpo + cola + tapón` con la cabeza del rig en las dos escalas extremas de respiración
   (sy 1 ± 0,012) sobre silueta: **0 huecos de fondo entre 4 y 399 px** (la regla de la prueba sin-hueco de la
   Fase 2, que ahora sí es alcanzable porque no hay articulaciones).
6. **Determinismo**: dos corridas dan el mismo `traza_<pose>.js` byte a byte.
7. **CI**: la CI solo tiene pytest y Node (sin cv2 ni numpy): los tests comparan la huella de `traza_<pose>.js` y
   de la lámina contra un `parecido_<pose>.json` commiteado (el patrón de `test_tadeo_parecido.py`), y se saltan
   la medición si falta OpenCV.
8. `verify --ci` verde; sin tocar la hoja madre, el rig ni los guiones; sin Flow ni Wan.

### Plan de construcción en pasos (para Opus)

| # | Paso | Criterio |
|---|---|---|
| 1 | Mover las funciones de apoyo a `kx_trazolib.py` (requiere PR #7 fusionada) | tests de la Fase 2 en verde, sin cambios |
| 2 | Escala y anclas: antifaz, `A_px`, pies, barbilla, eje | prueba 1 (identidad) en anclas; `pointing` y `triunfo` detectan sus anclas |
| 3 | Segmentación: cola, guantes, esqueletos de brazo | las 11 imágenes segmentan o fallan con motivo |
| 4 | Marcas de la sección 3.2 | prueba 1 (marcas de la madre) y 2 (invariancia) |
| 5 | Trazo (R1: tinta copiada, R2: cortes sin trazo) y medición 3.1 | IoU y tinta ≥ umbral sobre `pointing_api` (la más fácil) y `triunfo` (la más difícil) |
| 6 | Calibración (sección 4) con los conjuntos de buenos y malos | regla de separación |
| 7 | Las 9 láminas + prueba 5 de cuerpo sólido | informe por lámina |

## 7. Qué pasa con las láminas que no pasan

Se decide según qué falló. La regla de fondo: **nunca se traza una lámina que no pasa y nunca se deforma su tinta
para que pase** (no hay corrección por partes).

| Fallo | Acción |
|---|---|
| Color, margen recortado, más de una figura, fondo no blanco (sección 5 de la especificación) | **Se regenera** con el añadido de prompt que corresponda; ≈ 0,036 USD por intento, máximo 4 por pose |
| Antifaz no encontrado o ≠ 2 componentes, sin dos pies, cabeza tapada | **Se regenera** pidiendo explícitamente lo que falta |
| Marcas fuera de tolerancia | **Se regenera** con el prompt reforzado en esa proporción («arms exactly as thick as…»); solo se usa la corrección global por escala, que ya hace la normalización |
| Falla 4 veces | **Se descarta la lámina** y Fabian decide: otra pose para ese gesto, retoque manual, o aceptar con la desviación declarada y su OK por escrito |
| Pasa las marcas pero la lectura visual falla (`grito`: guantes sobre el antifaz) | Decide Fabian con la hoja de contacto: el trazador no mide «se lee bien» |

Reservas ya conocidas en las láminas de la PR #10 (declaradas en su reporte): `grito` (torso erguido, guantes
rozando el antifaz) y `estafado` (poco hundido); `asombro` y `explicando` están al límite del cuadro (margen
2,2 % y 2,6 %). Las cuatro son las candidatas a repetirse primero.

## 8. Transición entre poses (lo que el trazador debe dejar listo)

El cambio de pose es un cambio de dibujo en 2 – 4 fotogramas, no una interpolación de miembros. Por eso cada
`traza_<pose>.js` trae las mismas anclas, en el mismo orden:

- **Origen común**: punto medio de los pies en el suelo → los pies no «patinan» al cambiar de dibujo.
- **Barbilla y eje de cabeza**: la cabeza del rig se apoya en la barbilla de la pose vigente; al cambiar de pose, el
  muelle de la capa `cabeza` (que ya existe en `acting.js`) la lleva de una barbilla a la otra.
- **Capas**: cola detrás, cuerpo, cabeza, y las manos que solapan la cabeza (`grito`, `asombro`) delante.
- **Respiración**: escala vertical del cuerpo entero alrededor del origen, ± 1,2 % (el `IDLE.amplitudSy` de hoy).
- El contrato de acting (retrasos, muelles, retención) **no cambia**; solo cambia qué se anima.

## 9. Lo que no sé

- La sonda es cruda: no midió grosor de brazo, ancho de panza ni anillos, así que esas tres marcas no tienen aún una
  desviación medida. Pueden resultar tan poco estables como el guante.
- No he medido si el esqueleto de brazo es estable en `confundido` o `grito` (brazo doblado; guante solapando la cara).
- La solidez del cuerpo (0 huecos) la doy por alcanzable porque no hay articulaciones, pero no se ha probado.
- La regla de separación (≥ 2 y ≥ 5 puntos) es una propuesta mía; si la calibración no la cumple, vuelve a Fabian.
