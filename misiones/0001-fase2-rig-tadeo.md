# MISIÓN 0001 — Fase 2: Rig vectorial de Tadeo

Estado: en-curso (Parte A — diseño — entregada; Parte B — construcción — pendiente) ·
Rama: `feat/sistema-videos-korex-fase2` · Autor: Mijo · Diseño: Fable · Construcción y crítica: Opus

## Objetivo
Un Tadeo vectorial por partes, animado por código en Remotion, que se
reconozca como el de la hoja madre (`assets/kx_cast/tadeo/_hojas/model_sheet.png`)
y actúe con reglas medibles. Las 34 poses raster son referencia de acting, no el rig.

## Criterios de aceptación ejecutables
1. `misiones/evidencia/0001-fase2/hoja_de_poses.png` existe y cubre **toda** la
   biblioteca de este diseño: 14 poses + rejilla 10 expresiones × 4 miradas,
   con la hoja madre al lado. Lo comprueba un test: `py -m pytest tests/test_tadeo_lib.py`
   → la lista de celdas renderizadas == la biblioteca exportada por `poses.js`.
2. `py kx_tadeo.py` (composición de prueba de 10-15 s) → gate de la Fase 1 en
   verde: `palette.off_palette_max ≤ 0,0005`, `safe_zone = 0` y
   `char_color_fraction = 0` en `misiones/evidencia/0001-fase2/gate.json`.
3. Ningún archivo de `motion_graphics/src/kx/tadeo/` importa `DEBT`:
   `grep -rn "DEBT" motion_graphics/src/kx/tadeo/` → sin salida.
4. Reglas de acting medidas por test sobre las funciones puras del rig (sin
   render): orden de arranque mirada < cabeza < torso < brazos < cola; parpadeo
   42/58; `sx·sy = 1 ± 0,001` en todo frame; holds ≥ 10 frames.
5. `python scripts/verify.py` → VERDE; PR con el check `verify` en verde.

## ⏸ Puerta dura
Fabian aprueba la hoja de poses antes de la Fase 3. Si no se parece a la hoja
madre, se itera el rig.

---

## PARTE A — Diseño del personaje (Fable)

### A0. Qué hace que Tadeo sea Tadeo (lo que el rig no puede perder)
Leído de la hoja madre, por orden de peso en el reconocimiento:
1. **Cabeza más ancha que alta**, con mechones de mejilla que la ensanchan
   hacia abajo: silueta de «limón acostado» con dos orejas triangulares.
2. **Antifaz oscuro de dos lóbulos** unidos sobre el puente de la nariz, que
   se afila hacia las mejillas. Los ojos viven DENTRO del antifaz.
3. **Ojos de óvalo alto**, blancos, pupila negra grande con un brillo arriba
   a la izquierda. Sin iris.
4. **Hocico crema corto** con nariz negra pequeña (triángulo redondeado),
   boca en curva bajo la nariz y 3 pecas por lado.
5. **Guantes blancos de 4 dedos con puño enrollado**, grandes (casi el
   tamaño del hocico).
6. **Panza crema** en forma de pera, con mechón «w» en el pecho.
7. **Cola anillada** gruesa, asomando por su izquierda (derecha de pantalla).
8. Proporción **≈2,7 cabezas** de alto, piernas cortas, pies oscuros ovalados.

Lo que NO es Tadeo: sin ropa, sin colores, sin iris, sin dientes salvo en
`risa`/`grito`, sin cejas flotando fuera de la frente.

### A1. Tonos (todos sobre la recta INK→PAPER; cero color)
El gate cuenta como neutro lo que cae en la recta INK→PAPER, así que los
grises del modelo se definen como **mezclas** de los dos tokens, no como hex
nuevos. Van a `tokens.js` como `TADEO_TONE` (fracción de INK sobre PAPER):

| Token | INK | Uso |
|---|---|---|
| `T_WHITE` | 0,00 | guantes, blanco del ojo, dientes, brillo de pupila |
| `T_CREAM` | 0,07 | hocico, panza, interior de oreja |
| `T_FUR` | 0,46 | pelaje de cabeza, torso, brazos, piernas, anillos claros de la cola |
| `T_MASK` | 0,72 | antifaz, pies, anillos oscuros de la cola, lengua |
| `T_INK` | 1,00 | línea, nariz, pupilas, interior de boca |

Línea: contorno exterior **7 u**, líneas interiores **4,5 u**, pecas y
mechones **3,5 u** (u = unidad del rig, ver A2), extremos y uniones redondos.
El grupo entero pasa por el `Boil` de la Fase 1 (un solo filtro para todo el
personaje: las partes hierven juntas, no cada una por su cuenta).

### A2. Proporciones (espacio del rig: alto total = 1000 u, origen en el suelo, centro x = 0)
Medidas sobre la vista frontal de la hoja madre (alto orejas→suelo = 406 px).

| Parte | Medida (u) | Notas |
|---|---|---|
| Alto total | 1000 | de punta de oreja a suelo |
| Cráneo | 500 ancho × 290 alto, centro y = 770 | elipse achatada; el ancho incluye mechones de mejilla (2 picos por lado, 35 u) |
| Orejas | triángulo redondeado 120 base × 130 alto, centros x = ±165, base y = 880 | interior `T_CREAM` inset 22 u; giran ±12° |
| Mechón de coronilla | 3 picos, 90 ancho × 30 alto, y = 918 | sigue a la cabeza con retraso |
| Antifaz | 2 lóbulos 150 × 150, centros x = ±88, y = 775; puente de 60 de alto | las puntas exteriores llegan a x = ±215, y = 745 |
| Ojos | óvalo 78 ancho × 112 alto, centros x = ±82, y = 782 | blanco `T_WHITE`, contorno 4,5 u |
| Pupila | óvalo 40 × 58 | recorrido máx. ±16 u en x, ±20 u en y; brillo 12 u arriba-izq |
| Cejas | arco 70 largo, 9 u grosor, 20 u sobre el ojo | DENTRO de la frente: nunca flotan |
| Hocico | elipse 250 × 130, centro y = 690 | `T_CREAM`; se solapa con el borde bajo del antifaz |
| Nariz | 46 × 32, y = 715 | triángulo redondeado, brillo 8 u |
| Boca | ancla y = 668, ancho 60-150 según expresión | línea de filtrum de 22 u desde la nariz |
| Pecas | 3 por lado, r = 4, en x = ±(70, 88, 78), y = (700, 692, 680) | |
| Cuello | no existe | la cabeza se apoya sobre el torso con solape de 30 u |
| Torso | pera: 250 ancho arriba (y = 610), 370 ancho abajo (y = 300), base y = 215 | pivote de inclinación y squash en y = 215 |
| Panza | pera 215 × 330, centro y = 400 | `T_CREAM`; mechón «w» en y = 560; ombligo: arco de 60 u en y = 330 |
| Hombros | anclas x = ±128, y = 585 | |
| Brazos | tubo de 52 u de grosor, largo en reposo 330 u | rubber hose: Bézier cuadrática, sin codo |
| Guantes | 130 ancho × 180 alto (abierta) | puño enrollado 120 × 38; 3 dedos + pulgar |
| Caderas | anclas x = ±85, y = 235 | |
| Piernas | tubo de 78 u, largo 175 u | |
| Pies | óvalo 215 × 75, 3 dedos marcados | `T_MASK`; apuntan 12° hacia fuera |
| Cola | tubo que engorda de 90 a 150 u, largo 420 u, 5 anillos | nace en x = +95, y = 250; se dibuja DETRÁS del torso |

Orden de capas (de atrás adelante): cola → pierna/pie lejanos → torso → panza →
piernas/pies → brazo lejano → cabeza (orejas → cráneo → antifaz → hocico → ojos →
cejas → nariz/boca → mechón) → brazos y guantes delante.
Excepción: un brazo con `capa: "detras"` se dibuja antes del torso.

Tamaño en pantalla por defecto: **alto 640 px** (1 u = 0,64 px), pies en
y = 1180 → todo el personaje dentro de la zona segura (288-1248) con 60 px
para el rebote del spring.

### A3. Rubber hose: cómo se dibuja un miembro
Un brazo es una curva, no dos huesos:
- `P0` = hombro, `P2` = muñeca (`mano: [x, y]` de la pose).
- `P1` = punto medio + perpendicular × `curva` × largo × 0,38, con
  `curva ∈ [-1, 1]` (signo = hacia qué lado se arquea).
- Grosor constante 52 u, extremos redondos, contorno de 7 u (se dibuja la
  curva dos veces: INK a 52 + 14, luego `T_FUR` a 52).
- Puede estirarse: largo válido **0,75×–1,35×** el reposo. Fuera de ese
  rango la pose es inválida (el test de la biblioteca lo comprueba).
- El guante rota con la tangente final de la curva + `giro` de la pose.

Piernas: igual, con `curva` limitada a ±0,35 (son cortas).
Cola: Bézier cúbica; `rizo ∈ [-1, 1]` mueve los dos puntos de control;
los anillos son 5 franjas `T_MASK` repartidas por longitud de arco.

### A4. El objeto Pose
```js
{
  id: "asombro",
  expr: "asombro",            // expresión por defecto (el guion puede sobrescribirla)
  mirada: "camara",           // mirada por defecto
  cabeza: { inclina: -4, gira: 0.15, dx: 0, dy: 18 },   // grados, [-1,1], u, u
  torso:  { inclina: -6, sy: 1.06 },                    // sx se deriva: 1/sy
  brazoI: { mano: [-250, 640], curva: -0.5, guante: "abierta", giro: -20, capa: "delante" },
  brazoD: { mano: [ 250, 640], curva:  0.5, guante: "abierta", giro:  20, capa: "delante" },
  piernas:{ apertura: 1.0, flexion: 0, pieI: 12, pieD: 12 },
  cola:   { rizo: 0.6, alza: 30 },                      // [-1,1], grados
  orejas: { i: 8, d: -8 },                              // grados
  extra:  null                                           // ver «bolsillos»
}
```
- `I`/`D` son la izquierda y derecha **de pantalla**.
- `gira` es un falso 3/4: desplaza por paralaje nariz y hocico (×1,0), ojos y
  antifaz (×0,6) y orejas (×−0,3), y estrecha el ojo lejano hasta ×0,8. Rango
  útil ±0,6. No hay perfil ni espalda en esta fase.
- Guantes (5): `abierta`, `puno`, `senala`, `palma` (stop, de frente),
  `agarra` (pinza, para papeles y billetes).
- Interpolar dos poses = interpolar cada número; `guante`, `capa` y `expr`
  cambian en el punto medio de la transición, tapados por el parpadeo.

### A5. Biblioteca FINITA
**14 poses** — las 12 que ya usan los `character_terms` (frecuencia medida en
los guiones) + 2 de servicio. El guion escribe `tadeo/<id>`; el `*` de beat
no cambia la pose, la **refuerza** (ver A7).

| id | usos | Cuerpo | Brazos | expr / mirada |
|---|---|---|---|---|
| `neutro` | — | recto, peso centrado | caídos, guantes abiertos (la hoja madre) | sonrisa / camara |
| `confundido` | 42 | cabeza ladeada +10°, hombros arriba | encogido: manos a x = ±270, y = 560, palmas arriba | confundido / camara |
| `decidido` | 41 | inclinado +5° hacia delante, pies abiertos 1,2 | I en puño a la cadera; D puño al frente y = 520 | decidido / camara |
| `explicando` | 34 | recto, cabeza gira 0,2 | D abierta arriba y = 650 (presenta); I abierta baja | sonrisa / camara |
| `estafado` | 33 | hundido: sy 0,93, cabeza dy −25 | colgando, curva hacia dentro, guantes abiertos lacios | estafado / abajo |
| `orgulloso` | 22 | pecho fuera: inclinado −5°, sy 1,04 | puños en las caderas, codos fuera (curva ±0,8) | codicia (ojos entornados, sonrisa ancha: aquí se lee como suficiencia) / camara |
| `grito` | 19 | adelante +8°, sy 1,08 | manos haciendo bocina a los lados del hocico | grito / camara |
| `senalando` | 15 | cabeza gira 0,35 al lado que señala | D `senala` estirado 1,3× a x = 400, y = 600; I en puño atrás | decidido / der |
| `triunfo` | 12 | sy 1,10, pies despegan 20 u | los dos puños arriba y = 930 | risa / camara |
| `codicia` | 11 | encorvado +6°, cabeza dy −10 | manos frotándose al centro y = 470 (`agarra`) | codicia / abajo |
| `bolsillos` | 9 | cabeza ladeada −8° | manos a x = ±240, y = 300, palmas fuera; `extra: "bolsillos"` | triste / abajo |
| `asombro` | 9 | hacia atrás −6°, sy 1,06, orejas arriba | abiertas a los lados y = 640, dedos separados | asombro / camara |
| `picaro` | 8 | ladeado +6°, cabeza gira −0,25 | I en puño a la cadera; D `senala` hacia arriba junto a la cara | guino / camara |
| `pensando` | — | cabeza ladeada −6° | D `agarra` bajo el hocico; I cruza la panza sujetando el codo | confundido / izq |

`extra: "bolsillos"`: dos lengüetas `T_WHITE` con contorno, de 70 × 90 u, que
salen de las caderas — es la única pieza que no es anatomía.

**10 expresiones** (las 6 de la hoja madre + 4 que los guiones ya piden):

| id | Cejas | Párpados | Boca | Origen |
|---|---|---|---|---|
| `sonrisa` | arco suave | abiertos | curva hacia arriba, 110 u | hoja madre 1 |
| `asombro` | altas +14 u, arqueadas | muy abiertos (ojo ×1,08) | «o» pequeña 34 × 44, descentrada | hoja madre 2 |
| `triste` | en «/ \\» (interiores arriba 16°) | caídos 25 % | curva hacia abajo, 80 u | hoja madre 3 |
| `decidido` | en «\\ /» (interiores abajo 18°), bajas | recortan el ojo 30 % por arriba | recta apretada con comisura baja | hoja madre 4 |
| `guino` | una alta, una baja | ojo D cerrado en arco «^» | sonrisa ladeada, comisura I arriba | hoja madre 5 |
| `risa` | altas y relajadas | los dos cerrados en arco «^» | abierta ancha 150 × 80, dientes arriba, lengua `T_MASK` | hoja madre 6 |
| `grito` | en «\\ /», muy bajas | muy abiertos, pupila ×0,8 | abierta alta 110 × 130, dientes arriba | raster `grito` |
| `confundido` | una alta +16 u, otra baja | uno 100 %, otro 75 % | línea ondulada corta, 60 u | raster `confundido` |
| `codicia` | bajas y arqueadas hacia fuera | entornados 40 % | sonrisa ancha cerrada, comisuras muy arriba | raster `codicia` |
| `estafado` | como `triste`, 22° | caídos 35 %, **lágrima** `T_WHITE` con contorno en el borde de cada ojo | temblorosa hacia abajo | raster `estafado` |

La lágrima es blanca con línea INK: no hay azul.

**4 miradas** (desplazamiento de pupila, en fracción del recorrido máximo):
`camara` (0, 0) · `izq` (−1, 0) · `der` (+1, 0) · `abajo` (0, −0,8).
Las dos pupilas se mueven siempre juntas (nunca bizco). Con `izq`/`der` la
cabeza acompaña con `gira ±0,15` añadido.

Toda combinación pose × expresión × mirada es válida por construcción (la
cara y el cuerpo no comparten parámetros), así que la hoja de poses no
dibuja las 560: dibuja **las 14 poses** con su expresión por defecto y una
**rejilla 10 × 4 de cabezas** (expresión × mirada). Eso cubre cada elemento
de la biblioteca una vez.

### A6. Reglas de acting (medibles)
Todas son funciones puras de `frame`: se testean sin renderizar.

1. **La mirada lidera.** En un cambio de pose que empieza en el frame `t0`,
   cada capa arranca con retraso fijo:
   pupilas `t0` · cejas/boca `t0+1` · cabeza `t0+3` · torso `t0+6` ·
   brazos `t0+8` · orejas `t0+10` · cola `t0+12` · mechón `t0+13`.
2. **Parpadeo asimétrico 42/58.** Dura 6 frames: cierre 2,5 (42 %),
   apertura 3,5 (58 %); curva de cierre ease-in, apertura ease-out. Se dispara:
   (a) en cada cambio de pose o de expresión, centrado en `t0+1` (tapa el
   cambio de boca y guante); (b) en reposo, cada 84-156 frames (2,8-5,2 s) con
   semilla = índice de escena; (c) nunca dos en menos de 20 frames; (d) nunca
   durante `risa`, `guino` (ojo ya cerrado) ni dentro de los 8 primeros frames
   de un `grito`.
3. **Idle = dos senos inconmensurables.**
   respiración: `torso.sy = 1 + 0,012·sin(2π·0,0125·f)` (un ciclo cada 2,7 s);
   vaivén: `torso.inclina += 0,8°·sin(2π·0,0047·f + 1,3)` (un ciclo cada 7,1 s),
   y la cabeza lo contrarresta al 60 % con 4 frames de retraso. La cola
   oscila `rizo ± 0,08` con la frecuencia del vaivén desfasada π/2. Las
   frecuencias (0,0125 y 0,0047 ciclos/frame) están dentro de 0,004-0,02 y no
   son múltiplos: el bucle no se repite a la vista.
4. **Holds.** Una pose clave se sostiene **10-15 frames (0,33-0,5 s)** como
   mínimo: durante el hold solo se mueve el idle. Dos cambios de pose a menos
   de 10 frames son un error de la escena (lo valida el constructor de la
   línea de tiempo).
5. **Squash que conserva volumen.** `sx = 1/sy` siempre; `sy ∈ [0,85, 1,15]`;
   pivote en la base del torso. La cabeza recibe el 35 % del squash del torso.
6. **Anticipación.** Antes de un cambio grande (mano que viaja > 250 u), 3
   frames hacia el lado contrario al 8 % del recorrido.
7. **Follow-through.** Orejas, mechón y cola usan el preset con más masa y
   llegan los últimos (ver retrasos de la regla 1): rebasan y asientan.
8. **Beat `*`.** La escena marcada usa la misma pose con: entrada por
   `ACENTO` en vez de `POP`, escala del personaje ×1,12 (cabe en la zona
   segura por el margen de A2) y hold mínimo de 15 frames.
9. **Tadeo nunca queda congelado**: sin idle no hay frame (lo testea el gate
   comparando dos frames consecutivos de la caja del personaje: difieren).

### A7. Presets de spring de la casa (van a `tokens.js` como `SPRING`)
| Preset | Config | Para qué |
|---|---|---|
| `POP` | damping 12 · stiffness 200 · mass 0,5 (pupilas, cejas) / 0,6 (cabeza, brazos) / 0,8 (torso, cola, orejas) | cambios de pose de la mascota |
| `SUAVE` | damping 200 (stiffness 100 · mass 1) | entradas y salidas de escena, sin rebote |
| `ACENTO` | damping 8 · stiffness 200 · mass 0,6 | beats `*`, manos de `grito`/`senalando`/`triunfo` |

El rebote de `ACENTO` sobrepasa ~25 %: toda mano que lo use debe caber con
ese exceso dentro de la zona segura (lo comprueba el test de la biblioteca
con la caja envolvente de la pose × 1,25 en las manos).

### A8. Contrato con el resto del sistema
- `motion_graphics/src/kx/tadeo/`: `partes.jsx` (SVG por partes), `poses.js`
  (biblioteca: `POSES`, `EXPRESIONES`, `MIRADAS`, exportada también como JSON
  para el test), `acting.js` (funciones puras de A6), `Tadeo.jsx`
  (`<Tadeo pose expr mirada desde hacia t0 escala x y semilla beat />`).
- `tadeoBox(pose, x, y, escala)` devuelve la caja envolvente en píxeles: el
  gate la usa como `char_boxes` y las plantillas de la Fase 4 la usan para
  **no poner rojo deuda dentro de la caja + 24 px**.
- Ningún archivo de `tadeo/` importa `DEBT` ni escribe un hex: solo
  `INK`, `PAPER` y `TADEO_TONE`.
- `kx_cast.strip_beat`/`is_beat` siguen siendo la lectura del guion; un
  `character_term` que no esté en la biblioteca hace fallar el constructor de
  la escena (no cae a `neutro` en silencio).

### A9. Qué mirar en la hoja de poses (para Opus al criticar y para Fabian al aprobar)
1. Tapando el cuerpo: ¿la cabeza sola se reconoce como la de la hoja madre?
2. ¿El antifaz envuelve los ojos en las 10 expresiones, o alguna ceja/párpado
   se sale de él?
3. ¿Las 14 siluetas en negro macizo se distinguen entre sí? (`confundido` vs
   `asombro` y `decidido` vs `orgulloso` son los pares con riesgo.)
4. ¿Algún brazo parece tener codo? Si sí, falta curva.
5. ¿Los guantes siguen siendo el punto más claro de la figura?

## PARTE B — Construcción (Opus)
_(pendiente: se construye sobre este diseño, en sesión de Opus)_

## Reporte
_(lo escribe el ejecutor al terminar la Parte B)_
