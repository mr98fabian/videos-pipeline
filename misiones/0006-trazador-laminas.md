# MISIÓN 0006 — Construir el trazador de láminas de pose de Tadeo

Rama `feat/trazador-laminas` · PR contra master · estado: **en-auditoria**.
Fuente de verdad: `misiones/2026-11-25-diseno-trazador-laminas.md` (aprobado por Fabian el 25 nov 2026).
Orden de Fabian del 27 nov 2026: «constrúyelo». La ejecutó Claude (Fable/Opus) sin misión escrita
por Mijo, así que este archivo hace de misión y de reporte a la vez.

## Reporte

**Resumen:** el trazador existe (`kx_lamina.py`) y **copia bien las 11 imágenes**: el cuerpo trazado
coincide con su lámina con IoU de 0,994 a 0,998 y tinta del 99,9–100 % en los dos sentidos. Lo que
**no** funciona es parte del instrumento que el diseño fijó para aprobarlas: el tono cuantizado a
`TADEO_TONE` no llega al umbral de error tonal en 5 de 11, y de las 6 marcas de proporción solo
`pie` y `panza` son estables. Con las reglas tal cual pasaba 1 de 9 (`explicando`); con las dos decisiones del 27 nov (abajo: marcas estables y `T_OSCURO`) **pasan 4: `decidido`, `confundido`, `orgulloso` y `explicando`**. Según la
sección 4 del diseño no he aflojado ningún umbral: los números van abajo, **decide Fabian**.
Ninguna traza entra en el rig: quedan como candidatas en `misiones/evidencia/0006/trazas/`.

### Lo que hace

`py kx_lamina.py` (≈ 3 min) por lámina: antifaz → escala y cabeza; pies → origen; barbilla; cabeza
de la lámina fuera; huecos de papel; cola; guantes; marcas; traza (relleno por tonos planos + tinta
copiada como isolínea, R1); medición 3.1; prueba de sólido. Después calibra (sección 4) y escribe
`informe.json`, `contacto_trazos.png` (lámina | trazo + cabeza de la madre) y las trazas.
`--debug` añade `segmentacion.png`; `--invariancia` y `--determinismo` corren las pruebas 2 y 6.

Paso 1 del plan (sin cambio de comportamiento): las funciones de apoyo de `kx_trazo.py` se movieron a
`kx_trazolib.py`. `traza.js` sale idéntico byte a byte y `parecido.json` solo cambia de huella.

### Criterios de aceptación (sección 6 del diseño)

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Identidad: la madre como lámina, IoU ≥ 0,98 | **cumple**: IoU 0,9943, tinta 100/100 % | `informe.json` → `medidas.madre` |
| 2 | Invariancia (desplazada, ×0,7–×1,4, ±3°) | **parcial**: desplazada y ×1,4 cumplen; ×0,7 da área −2,0 %; ±3° mueve el centroide 3,8–4,1 % | `invariancia.json` |
| 3 | Calibración: regla de separación | **NO cumple** (abajo) | `informe.json` → `calibracion` |
| 4 | Cada lámina pasa o se rechaza con motivo | **cumple**: las 11 se miden; el malo natural se rechaza («antifaz: no hay dos lóbulos») | `salida.txt` |
| 5 | Cuerpo sólido (0 huecos de 4–399 px) | **9 de 11**: fallan `grito` (10 rendijas) y `asombro` (1) | `informe.json` → `medidas.*.solido` |
| 6 | Determinismo | **cumple**: dos corridas dan `traza_grito.js` idéntico (SHA-1 `cd7bec1e7b0b42c5`) | `py kx_lamina.py --determinismo` |
| 7 | CI sin OpenCV | **cumple**: `tests/test_kx_lamina.py`, 27 tests; los 2 que necesitan cv2 se saltan | |
| 8 | `verify` verde; sin tocar hoja madre, rig ni guiones; sin Flow ni Wan | **cumple**: `verify: VERDE · 126 passed, 1 xfailed` | |

### Medición 3.1 (trazo contra su lámina), las 11

| Lámina | IoU | Tinta lám→trazo / trazo→lám | Área tinta | Tono medio / sup. > 0,08 | Sólido |
|---|---|---|---|---|---|
| madre | 0,9943 | 1,000 / 1,000 | 1,019 | 0,0285 / **11,2 %** | sí |
| decidido | 0,9970 | 1,000 / 1,000 | 1,000 | 0,0215 / 3,1 % | sí |
| confundido | 0,9949 | 1,000 / 1,000 | 0,997 | **0,0335** / 3,3 % | sí |
| orgulloso | 0,9976 | 1,000 / 1,000 | 1,001 | 0,0280 / 2,9 % | sí |
| estafado | 0,9972 | 1,000 / 1,000 | 0,994 | 0,0261 / 3,7 % | sí |
| grito | 0,9968 | 1,000 / 1,000 | 0,998 | 0,0199 / 3,5 % | **no** |
| explicando | 0,9950 | 1,000 / 1,000 | 0,997 | 0,0247 / 3,6 % | sí |
| codicia | 0,9977 | 1,000 / 1,000 | 0,999 | 0,0251 / 2,8 % | sí |
| asombro | 0,9951 | 1,000 / 1,000 | 0,996 | **0,0438 / 5,2 %** | **no** |
| triunfo | 0,9943 | 1,000 / 1,000 | 0,998 | **0,0315 / 6,1 %** | sí |
| pointing | 0,9965 | 1,000 / 1,000 | 0,995 | **0,0383** / 4,6 % | sí |

Umbrales (sin tocar): IoU ≥ 0,98 · tinta ≥ 97 % · área 0,97–1,03 · tono ≤ 0,030 y ≤ 5 %.

### Lo que hay que decidir (Fabian)

1. **Tono: dos reglas del diseño chocan.** §2.3 obliga a cuantizar a los 6 tonos de `TADEO_TONE`
   («ningún hex nuevo») y §3.1 exige error tonal ≤ 0,030. La API pinta pies y anillos de la cola en gris
   82–90; el tono más oscuro disponible (`T_MASK`) da 102: error 0,05–0,08 en el 11–14 % de la figura.
   En `asombro`, además, el peto es 219 y el tono más cercano da 230. Opciones: (a) añadir un tono
   oscuro a `TADEO_TONE` (≈ 0,70), que cambia también el rig; (b) aceptar el error tonal en pies y cola;
   (c) regenerar esas láminas pidiendo pies y anillos más claros. La madre misma falla la superficie
   (11,2 %) porque tiene sombreado que los tonos planos no copian.
2. **Marcas: solo `pie` y `panza` sirven.** Desviaciones de los buenos contra la madre:
   `pie` −6,1 % a +6,1 %; `panza` −3,1 % a −0,6 % (no medible en 4: manos o brazos tapan el peto);
   `brazo_grosor` −5,9 % a **+19,2 %** (no medible en 5: brazo pegado al cuerpo o junto a la cabeza);
   `brazo_largo` **−38,9 % a +22,2 %** (el codo de `confundido` acorta el tubo). `cola_ancho` no tiene
   referencia: de frente, el guante de la madre tapa su cola (0,22 A contra 0,36–0,47 en las láminas).
   Con la regla de la sección 4, `brazo_*` sube al tope del 15 % y aun así deja fuera a `decidido`,
   `confundido` y `asombro`. **Propuesta:** aprobar con `pie` + `panza` + anillos. Con esa regla pasarían
   la 3.2 `decidido`, `confundido`, `orgulloso`, `explicando` y `asombro` (campo `pasa_32_solo_estables`).
3. **La regla de separación no se cumple ni con esas dos.** `pie` deja a los buenos 1,9 puntos de margen
   (pide 2; el diseño ya lo anticipaba). Los malos fabricados caen, pero por una sola marca, no dos:
   cabeza ×1,3 → `pie` −23,9 %; cuerpo aplastado ×0,8 → `brazo_grosor` −22,0 %. Cuerpo ×1,25 y el
   malo natural se rechazan antes de medir. «Brazos al 70 %» **no se fabricó**: adelgazar un tubo
   redibujando su tinta exige un editor de láminas que no existe.
4. **Anillos de cola 5–7:** `triunfo` y `pointing` cuentan 8 (cuento las bandas oscuras y las medias).
   Puede ser el criterio o la lámina; no lo he cambiado.
5. **Invariancia al giro (±3°) contradice la normalización del diseño**, que solo escala y traslada.
   Enderezar por la línea de los pies lo arregla, pero inclinaba 1,2–4° a `orgulloso`, `estafado`,
   `asombro` y `pointing`, que tienen un pie más adelantado. Lo quité. ×0,7 pierde un 2 % de área
   por resolución: esas láminas no se generan a ese tamaño.
6. **Rendijas de sólido** en `grito` (manos junto a las mejillas) y `asombro`: la cabeza de la lámina
   es algo mayor que la de la madre junto a una mano, y al quitarla queda papel de hasta 23 px.
   Encaja en la reserva que ya tenía `grito` («guantes rozando el antifaz»). Candidatas a regenerar.

### Decisión de Fabian (27 nov 2026): solo marcas estables

Aprobó la propuesta del punto 2: la 3.2 decide con `pie` + `panza` + anillos (`DECIDEN` en `kx_lamina.py`).
`brazo_grosor`, `brazo_largo` y `cola_ancho` se siguen midiendo en `marcas_informativas`, sin decidir.

| Lámina | 3.1 | 3.2 | Sólido | Pasa | Lo que la frena |
|---|---|---|---|---|---|
| decidido | sí | sí | sí | **sí** | — |
| orgulloso | sí | sí | sí | **sí** | — |
| explicando | sí | sí | sí | **sí** | — |
| confundido | no | sí | sí | no | tono medio 0,0335 |
| asombro | no | sí | no | no | tono 0,0438 / 5,2 %; 1 rendija |
| estafado | sí | no | sí | no | panza no medible (brazos sobre el peto) |
| grito | sí | no | no | no | panza no medible (manos); 10 rendijas |
| codicia | sí | no | sí | no | panza no medible (manos sobre el peto) |
| triunfo | no | no | sí | no | tono 0,0315 / 6,1 %; 8 anillos |
| pointing | no | no | sí | no | tono; 3/4: ninguna marca que decida es medible |

**Coste de la decisión:** con solo `pie` y `panza`, el malo fabricado «cuerpo aplastado ×0,8» ya **no se
detecta** (lo cazaba `brazo_grosor`), y «cabeza ×1,3» cae por una sola marca (`pie` −23,9 %). La regla de
separación sigue sin cumplirse. Sigue pendiente el punto 1 (tono).

### Decisión de Fabian (27 nov 2026): tono oscuro nuevo

`TADEO_TONE` gana `T_OSCURO: 0.69` (`tokens.js` y `kx_trazolib.TONOS`): el gris de pies y anillos de las
láminas mide 0,664–0,724 (mediana 0,682, 52 regiones) y `T_MASK` (0,64) no llegaba. **El rig no cambia**:
regenerado `traza.js`, solo se añade la entrada a su tabla `tonos`; la madre no usa el tono nuevo, y
`parecido.json` solo cambia de huella.

| Lámina | Tono medio / sup. > 0,08 (antes → ahora) | Pasa | Lo que la frena |
|---|---|---|---|
| decidido | 0,0215 → 0,0147 / 3,5 % | **sí** | — |
| confundido | 0,0335 → 0,0270 / 3,7 % | **sí** | — |
| orgulloso | 0,0280 → 0,0244 / 3,4 % | **sí** | — |
| explicando | 0,0247 → 0,0201 / 3,9 % | **sí** | — |
| estafado | 0,0261 → 0,0236 / 3,3 % | no | panza no medible |
| grito | 0,0199 → 0,0199 / 3,5 % | no | panza no medible; 10 rendijas |
| codicia | 0,0251 → 0,0229 / 3,1 % | no | panza no medible |
| asombro | 0,0438 → **0,0355** / 4,3 % | no | tono (peto 219 contra `T_CREAM` 230); 1 rendija |
| triunfo | 0,0315 → 0,0220 / 3,0 % | no | 8 anillos (pide 5–7) |
| pointing | 0,0383 → **0,0301** / 3,6 % | no | tono por 0,0001; 3/4 sin marcas que decidan |

### Decisiones y desviaciones del diseño (declaradas)

1. **Barbilla = la del rig, colocada por el antifaz**, no el «punto más bajo de la región cara».
   Medido en las 11: la cara y el peto son **una sola región**, sin tinta entre ellas (también en la
   madre), así que el corte topológico no existe. La barbilla de la madre (`kx_trazo`) cae 0,34 A bajo el
   antifaz. El estrechamiento propio de cada lámina queda como diagnóstico (`barbilla_propia_A`,
   0,30–0,39).
2. **La cabeza de la lámina se recorta con la silueta de la cabeza de la madre** puesta por el antifaz
   (+6 % de margen). Hombros, brazos y manos que suben junto a la cabeza quedan fuera porque sus regiones
   caen fuera. Lo que la cabeza de la lámina saca de más (orejas más altas: 24 663 px en `estafado`) se
   quita si no se une a nada bajo la barbilla.
3. **Pieza `delante`:** la parte de los guantes que pisa la cabeza (`grito`, 0,196 A²) va aparte, para
   pintarla encima de la cabeza del rig (sección 8).
4. **Huecos de papel** entre brazo y torso (`codicia`, `orgulloso`…): región blanca rodeada de pelaje.
   Salen de la silueta: antes los tomaba por guantes.
5. **3.1 excluye la cabeza más 12 u alrededor**, no el semiplano sobre la barbilla: así las manos
   alzadas (`triunfo`, `asombro`) sí se miden.
6. **3.1 se mide rasterizando la traza en Python** (fillPoly ×4, even-odd), no con Remotion: el rig
   aún no lee `traza_<pose>.js`. La hoja de contacto pone la cabeza de la madre en píxeles como
   aproximación de la del rig.
7. **Cola y tapón se ensanchan 2 px por debajo de la pieza de delante**, y el tapón va detrás del cuerpo.
   Sin el solape quedaban rendijas de 1 px entre polígonos vecinos.

### Lo que NO se hizo

- Integración en el rig (`Tadeo.jsx` leyendo `traza_<pose>.js`, transición entre poses de la §8): es la
  misión siguiente, y además la sección 7 prohíbe meter trazas que no pasan.
- Regenerar láminas (0 USD gastados en esta misión).
- La sección 2.2 de la especificación de las 9 láminas sigue sin corregir: la corrige la decisión del
  punto 2 de arriba.

### Para cerrar

1. Fabian mira `misiones/evidencia/0006/contacto_trazos.png` y decide los puntos 1–3.
2. Con esas decisiones, se ajusta el criterio y se vuelve a correr `py kx_lamina.py` (sin coste).
3. Las láminas que sigan fallando se regeneran (≈ 0,036 USD cada una) y se integra en el rig.
