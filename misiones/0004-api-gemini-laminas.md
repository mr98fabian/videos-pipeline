# MISIÓN 0004 — API de Gemini para láminas de pose (Nano Banana)

Rama `feat/api-gemini-laminas` · PR contra master · estado: **en-auditoria, bloqueada en la prueba de humo** (ver Reporte).

Contexto, alcance y criterios: los de la misión pegada por Fabian (herramienta `scripts/generar_lamina.py`
+ 1 prueba «pointing»; las 9 láminas de producción NO se generan aquí; ni Flow ni Wan; el rig no se toca).

## Reporte

### Criterios de aceptación

| Criterio | Estado | Artefacto |
|---|---|---|
| `py scripts/generar_lamina.py --pose pointing` genera `pointing_api.png` con costo registrado | **BLOQUEADO** | La API respondió **HTTP 429** (ver abajo). La herramienta llega hasta la llamada y falla limpio; no hay imagen ni fila de costo |
| Lado a lado `pointing_api.png` vs lámina «pointing» existente + nota de estilo | **BLOQUEADO** | Depende de la imagen anterior |
| `grep` no encuentra la llave; `.env` sigue ignorado | cumple | `tests/test_generar_lamina.py::test_ninguna_llave_en_archivos_commiteados` y `::test_env_sigue_ignorado_por_git` (escanean los archivos de `git ls-files` con la llave real de `.env` y con las formas `AIza…`/`AQ.…`) |
| Sin llave y con llave inválida falla limpio, sin filtrar la llave | cumple | 10 tests sin red en `tests/test_generar_lamina.py` (sin llave, llave rechazada con eco de la llave en el cuerpo del error, error de red, tope, éxito con costo) |
| `scripts/verify.py` verde; PR con CI verde | ver PR | — |

### Lo que bloquea la prueba (decisión de Fabian)

La llave es válida: `GET /v1beta/models` la acepta y lista los modelos de imagen. Pero `generateContent`
devuelve 429 con `generate_content_free_tier_requests, limit: 0` para `gemini-nano-banana-2.1`.
**El proyecto de esa llave está en el Free Tier, donde los modelos de imagen tienen cuota 0.**
El paso 0 de la misión pedía un proyecto con facturación activada: o la llave se creó en un proyecto
sin facturación, o la facturación todavía no se ha vinculado. Hay que activarla en
Google AI Studio → la llave → «Set up billing» (o crear la llave en un proyecto con facturación) y
volver a correr el mismo comando. No hay nada más que cambiar en el repo.

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

### Para cerrar la misión

1. Fabian activa la facturación del proyecto de la llave.
2. `py scripts/generar_lamina.py --pose pointing` (≈ 0,03 USD) → `misiones/evidencia/0004/pointing_api.png` y
   fila en `costos.csv`.
3. Lado a lado contra `assets/kx_cast/tadeo/_hojas/Cartoon_character_pointing_forward_*.jpeg` (local, ignorada
   por git) y la nota de estilo en esta sección.
