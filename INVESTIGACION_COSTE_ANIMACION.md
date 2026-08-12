# Cuánto cuesta de verdad animar un vídeo de KOREX

**Por qué existe (12 ago 2026):** el primer clip animado por API costó **~$2 por
5 segundos**. A ese precio, animar los 24 planos de un vídeo son ~$48, y un
vídeo diario son ~$1.440 al mes. La pregunta no es "¿qué proveedor?", es "¿por
qué estamos pagando el modelo más caro de la casa para mover una lámina que ya
está dibujada?".

Fuentes en inglés, español, chino, japonés y coreano. Precios de agosto 2026;
todos bailan, así que lo que importa es el **orden de magnitud entre opciones**,
no el decimal.

---

## 1. El dato medido, y por qué duele

Usamos `seedance-2` (el buque insignia) a 720p. Tarifa publicada de PiAPI:
**$0,20 por segundo de salida**. Cinco segundos = $1,00 de tarifa, y el cargo
real observado fue ~$2. Sea cual sea la diferencia (mínimos, reintentos,
subidas), **el pedido estaba mal desde el principio**: pedimos el modelo tope
para hacer un empuje de cámara sobre un dibujo quieto.

## 2. La escalera de precios (por segundo, 720p salvo nota)

| Opción | $/segundo | Clip de 5s | 24 clips (120s) |
|---|---|---|---|
| `seedance-2` (lo que usamos) | 0,200 | $1,00 | $24,00 |
| `seedance-2-fast` | 0,128 | $0,64 | $15,36 |
| **`seedance-2-mini`** | **0,084** | **$0,42** | **$10,08** |
| Wan 2.6 (1080p nativo) | 0,050 | $0,25 | $6,00 |
| Kling 1.6 | 0,050 | $0,25 | $6,00 |
| Hailuo 2.3 | 0,020-0,040 | $0,10-0,20 | $2,40-4,80 |
| **Wan 2.2 local (ComfyUI)** | **0** | **0** | **0** |

Dos cosas que no se ven en la tabla y deciden:

- **El modo primer/último fotograma está en TODAS las variantes de Seedance**,
  también en `mini`. O sea que la receta de encajonar la deriva entre dos planos
  validados no obliga a pagar el buque insignia: es cambiar una cadena de texto
  (`task_type`) y el coste cae un 58%.
- **Higgsfield queda fuera por construcción.** Su plan Plus son $49/mes por
  1.000 créditos y Seedance ahí sale ~22-25 créditos por clip de 5s: ~$1,10 por
  clip *y* una suscripción fija encima. Compras un MCP cómodo, no precio.

## 3. La vía china: barata de verdad, cara en tiempo

En el mercado doméstico el mismo modelo se vende por suscripción, no por
segundo: **即梦 (Jimeng)** con pago anual sale a ~4,58 ¥ por vídeo de 15s (~$0,64),
y 小云雀 —producto interno de ByteDance— arranca en 39 ¥/mes, la mitad. Hay
además crédito gratis diario que da para un vídeo de 15s al día.

**Y aquí está la trampa, y es la misma que ya nos mordió con Flow:** en horas
punta la cola va de varias horas hasta diez, los créditos no la saltan, y todo
eso vive detrás de una interfaz web. Volveríamos exactamente al problema que
acabamos de quitarnos — automatizar un navegador con sesión, cuota invisible y
fallos silenciosos. **Barato en dólares, caro en tardes perdidas.**

## 4. La vía gratis: Wan 2.2 en local

Wan 2.2 es Apache 2.0 (uso comercial permitido) y corre en ComfyUI, que ya está
instalado en esta máquina. La GPU de aquí es una **RTX 4080 Laptop de 12 GB**:
el modelo de 5B entra con holgura y el de 14B no. Medido por terceros: ~3
minutos por clip de 5s en tarjetas de 8 GB, con techo práctico de 480p; con 12 GB
hay margen para subir algo la resolución.

Traducido a nuestro caso: **24 clips ≈ una hora de GPU y cero dólares**. Es lento
para iterar, pero el pipeline **ya tiene la puerta abierta** — el flag
`--wan-hero` de `pipeline.py` existe justo para esto (hero local en la escena 0).

## 5. Qué hacemos (aplicación al pipeline)

1. **Cambio inmediato, una línea:** `piapi_animate.py` pasa de `seedance-2` a
   **`seedance-2-mini`**. Mismo modo de dos extremos, misma calidad de
   movimiento para lo que pedimos (cámara lenta sobre dibujo quieto), **58%
   menos**. Clip de apertura: **$0,42** en vez de ~$1-2.
2. **Solo se anima la apertura.** Es el plano donde se decide el scroll; el
   resto lo mueve el motor gratis. Coste por vídeo ≈ $0,42, o sea ~$13/mes a
   vídeo diario.
3. **Si algún día se quiere el vídeo entero animado**, el camino NO es pagar
   más por segundo: es Wan 2.2 en local. Una hora de GPU por vídeo a cambio de
   $0. Antes de eso hay que medir si su calidad de movimiento aguanta el estilo
   entintado; hoy no está medido y no se decide por intuición.
4. **Higgsfield y la vía china quedan descartadas**, cada una por su motivo:
   suscripción fija sobre precio ya caro la primera; volver al navegador y a las
   colas la segunda.

**Lo que este documento NO afirma:** que `mini` se vea igual que el buque
insignia en cualquier plano. Para lo nuestro —empuje lento sobre una lámina ya
aprobada, donde el modelo mueve y no redibuja— la diferencia debería ser
invisible, pero eso hay que verlo en el primer clip que salga con `mini`, no
darlo por bueno.
