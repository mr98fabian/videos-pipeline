# WanGP — animar escenas en local (Wan 2.2)

**Qué resuelve:** el imagen→vídeo de Flow está apagado desde el 3 ago 2026
porque cuesta ~100 créditos por clip y falla de forma intermitente (ver
[[INVESTIGACION_COSTE_ANIMACION]]). Wan 2.2 corre en la GPU de casa: el clip no
cuesta créditos, cuesta minutos. Eso cambia la decisión de fondo — con coste
cero por reintento se puede animar el vídeo entero, no solo la escena 1.

**Qué NO cambia:** las imágenes las sigue generando Flow. Wan parte de la imagen
ya aprobada, así que la consistencia de Tadeo la aporta el fotograma de partida,
no el modelo de vídeo. HiddenFacts no lo usa: su lenguaje son recortes sobre
papel, no vídeo.

## Estado (15 ago 2026)

Instalado y verificado en `../Wan2GP` (fuera del repo, no se versiona):

- PyTorch 2.10.0 + CUDA 13.0, `torch.cuda` activa sobre la RTX 4080 Laptop (12 GB)
- Triton 3.7.1 y SageAttention 2.2.0 (hasta ×2 en 40XX, pérdida de calidad mínima)
- venv propio de Python 3.11.14 vía uv, igual que `tools/kokoro_tts`
- Modo headless validado con `--dry-run`: 24/24 escenas de un KOREX real

**Falta una sola cosa: la descarga del modelo (~30 GB, una vez).** Ocurre sola en
la primera generación real. No se hizo aún porque satura la conexión.

No hizo falta instalar el toolkit CUDA aparte: las ruedas de torch traen su
propio runtime.

## Uso

```powershell
py wan_animate.py output/<carpeta>                  # anima lo que falte
py wan_animate.py output/<carpeta> --dry-run        # valida sin generar
py korex_animate.py output/<carpeta> --animar-todo  # monta con esos clips
```

`wan_animate.py` escribe `clips/fx_<i>.mp4`, que es exactamente lo que ya
consume `korex_animate.py`: el montaje no cambia ni una línea. Cada clip se
cachea (si se corta a la mitad, al relanzarlo solo genera lo que falta) y se
verifica contra su imagen con `clip_matches_source` — un mp4 válido que anima
otra escena es un fallo silencioso, y el mapeo de salidas es por orden.

## Decisiones de configuración

| Ajuste | Valor | Por qué |
|---|---|---|
| Modelo | `i2v_2_2_Enhanced_Lightning_v2` | 4 pasos en vez de 20. En 12 GB es la diferencia entre viable y no viable |
| Resolución | `720x1280` | 9:16 nativo. `480x832` si hace falta ir más rápido |
| Fotogramas | 81 (~5 s a 16 fps) | `korex_animate` clona el último frame si la escena dura más |
| Prompt | `search_term` + `MOTION_HINT` | El mismo texto que usaba Flow: cámara fija, movimiento solo dentro de la escena |

## El fallo que costó cuatro corridas (15 ago 2026)

**El modo headless NO mezcla los defaults del modelo; la web sí.** Pasarle un
JSON con modelo, prompt, imagen y pasos produce un clip de ruido de color: el
fotograma 0 es la imagen exacta y todo lo demás, basura. Un mp4 válido, de la
duración correcta — el fallo silencioso de siempre.

Lo que faltaba era `guidance_scale: 1`, `guidance2_scale: 1`, `flow_shift: 5`,
`guidance_phases: 2` y `switch_threshold: 900`. Lightning corre en 4 pasos con
guidance 1; con la genérica de 5 devuelve ruido. Medido sobre la misma escena
y semilla: diff 57-66 sin ellos, 21-34 con ellos.

`wan_animate.py` los lee ahora de `Wan2GP/defaults/<modelo>.json`, así que
cambiar de modelo no vuelve a romperlo.

Descartados por el camino, cada uno con una corrida: SageAttention (`--attention
sdpa` da el mismo ruido) y el dtype (`--bf16` da salida idéntica al píxel).
`--quantize-transformer` está en `docs/CLI.md` pero no existe en el argparse.

## Velocidad medida (RTX 4080 Laptop, 12 GB)

| Resolución | Tiempo por clip de 5 s |
|---|---|
| 720x1280 | 16 min 47 s |
| 480x832 | 7 min 41 s |

Incluye ~2-3 min de carga del modelo, que se paga una vez por corrida, no por
clip. **Aun así, 24 escenas a 480p son ~3 h de GPU.** Animar el vídeo entero es
una corrida de noche, no algo de sobremesa; para la apertura sola son 8 minutos.
