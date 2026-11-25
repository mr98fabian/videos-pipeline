# MISIÓN 0004 — API de Gemini para láminas de pose (Nano Banana)

Rama `feat/api-gemini-laminas` · PR contra master · estado: **en-auditoria** (prueba de humo hecha; falta el OK de Fabian al estilo).

Contexto, alcance y criterios: los de la misión pegada por Fabian (herramienta `scripts/generar_lamina.py`
+ 1 prueba «pointing»; las 9 láminas de producción NO se generan aquí; ni Flow ni Wan; el rig no se toca).

## Reporte

### Criterios de aceptación

| Criterio | Estado | Artefacto |
|---|---|---|
| `py scripts/generar_lamina.py --pose pointing` genera `pointing_api.png` con costo registrado | cumple | `misiones/evidencia/0004/pointing_api.png` (1200 × 896) y `costos.csv`: 1 341 tokens de entrada, 1 888 de salida, **0,0356 USD** (`gemini-nano-banana-2.1`) |
| Lado a lado `pointing_api.png` vs lámina «pointing» existente + nota de estilo | cumple | `misiones/evidencia/0004/pointing_lado_a_lado.png` (hoja madre · lámina existente · lámina de la API) y la nota de abajo |
| `grep` no encuentra la llave; `.env` sigue ignorado | cumple | `tests/test_generar_lamina.py::test_ninguna_llave_en_archivos_commiteados` y `::test_env_sigue_ignorado_por_git` (escanean los archivos de `git ls-files` con la llave real de `.env` y con las formas `AIza…`/`AQ.…`) |
| Sin llave y con llave inválida falla limpio, sin filtrar la llave | cumple | 10 tests sin red en `tests/test_generar_lamina.py` (sin llave, llave rechazada con eco de la llave en el cuerpo del error, error de red, tope, éxito con costo) |
| `scripts/verify.py` verde; PR con CI verde | ver PR | — |

### Historia de la prueba de humo

Tres respuestas distintas antes de generar, todas sin gasto: **429** (proyecto en Free Tier, cuota 0), **402**
(créditos prepagados a 0) y, tras el pago de Fabian, la llamada pasó a los pocos minutos (el pago tarda en
aplicarse). Costo total de la misión: **0,0356 USD**, una imagen.

### Nota de estilo: «pointing_api.png» frente a la lámina existente

- **Misma identidad y misma familia de estilo:** antifaz, ojos redondos con brillo, nariz negra, guantes
  blancos, cola anillada, gris plano de dibujo animado años 30 y contorno negro limpio. Pose pedida cumplida:
  señala con el índice a la izquierda, la otra mano en la cadera, postura abierta.
- **Mejor para trazar que la lámina existente:** un solo cuerpo completo sobre blanco puro, sin las cabezas,
  manos sueltas ni vistas extra alrededor; el cuerpo entero a 1200 × 896, con la mano y los dedos del gesto
  bien legibles.
- **Dónde se aparta de la hoja madre:** (1) el vientre es gris, no crema; (2) el contorno es algo más fino y
  uniforme que el de la madre; (3) la cabeza deriva: hocico más largo y cejas más marcadas, con aire de zorro
  y de «pillo». Esto último no importa para el método (la cabeza la sigue poniendo el rig, con las 40
  expresiones trazadas de la madre): de cada lámina solo se traza el cuerpo y los guantes.
- **Veredicto:** el método funciona para el cuerpo. Para las láminas de producción, el prompt tendría que
  pedir vientre crema y contorno de peso de la madre, y cada lámina pasar el gate de marcas (ancho y alto de
  cabeza, antifaz) antes de trazarla. Pendiente del OK de Fabian al estilo.

### Modelo (verificado el 25 nov 2026)

- **ID fijado: `gemini-nano-banana-2.1`** («Nano Banana 2.1»). La doc oficial lo marca «New» y lo
  recomienda para proyectos nuevos (`aistudio.google.com/docs/models` e `/image-generation`); la propia
  API lo lista con `generateContent` (`GET /v1beta/models`).
- Los otros candidatos también existen en la API: `gemini-3.1-flash-image` (Stable, «Nano Banana 2»),
  `gemini-3.1-flash-lite-image`, `gemini-3-pro-image`, `gemini-2.5-flash-image` (la doc lo da por legado y
  con cierre previsto el 15 mar 2027). Se cambia con `--modelo`.
- Precio usado para el log (página de precios, tier de pago): entrada 1,50 USD/1M tokens, imagen de salida
  30 USD/1M, ≈ 0,0336 USD por imagen de 1K. **Esas cifras las leí de un resumen de la doc, no del texto
  literal**: revisar en la página de precios antes de un lote.
- Formato: la doc de imagen documenta el endpoint nuevo `interactions`; el script usa `generateContent`
  (`inlineData` con la hoja madre + texto), que la API sigue ofreciendo para estos modelos. Si Google lo retira,
  hay que migrar `construir_cuerpo`/`llamar_api`/`extraer_imagen`.

### Seguridad de la llave

- Se lee de `GEMINI_API_KEY` (entorno o `.env` de la raíz). `redactar()` pasa por todo texto de salida (errores
  de la API incluidos) y tapa la llave actual y cualquier cosa con forma `AIza…`/`AQ.…`.
- Tope: más de 10 imágenes por ejecución se rechaza salvo `--lote`.
- La llave se pegó en el chat de la sesión; si ese hilo se comparte, regenerarla.
- Durante la construcción un test llegó a llevar un trozo de esa llave pegada en el chat; el escudo de la
  sesión lo bloqueó antes de escribirse y se sustituyó por llaves inventadas. Nada con la llave real está
  en el árbol (comprobado por el test de arriba).

### Para cerrar

Fabian aprueba el estilo de `pointing_api.png`. Las 9 láminas de producción vienen en otra misión, con la
especificación por pose de Fable.
