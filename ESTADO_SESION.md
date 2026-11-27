# Estado de sesión — dónde quedamos

**Para qué existe:** Fabián trabaja con dos sesiones de Claude en paralelo (para
estirar tokens). Este archivo es el traspaso entre ellas: lo último que se hizo,
lo que quedó a medias, y qué sigue. Se lee al empezar y se actualiza al terminar.

**Reglas de uso:**
- Solo el estado ACTUAL. Lo histórico va a `HISTORIAL_MEJORAS.md`, no aquí.
- Sobrescribir, no acumular. Si crece más de una pantalla, sobra texto.
- **Riesgo real de las dos sesiones en paralelo:** si ambas editan el mismo
  archivo, la segunda pisa a la primera sin avisar. Antes de tocar código que
  la otra sesión pudo haber cambiado, `git diff` primero.

---

## Actualizado: 27 nov 2026 — trazador de láminas de Tadeo construido (misión 0006)

**Rama `feat/trazador-laminas`**, PR abierto. Reporte completo en `misiones/0006-trazador-laminas.md`.

- `kx_lamina.py` traza las 9 láminas + `pointing`: el cuerpo copia su lámina con IoU 0,994–0,998 y
  tinta ~100 %. La cabeza la pone el rig, anclada por el antifaz.
- **Pasan 5 de 9** (`decidido`, `confundido`, `orgulloso`, `explicando`, `asombro`) tras dos decisiones de Fabian del
  27 nov (proporción solo con `pie` + `panza` + anillos; `T_OSCURO: 0.69` en `TADEO_TONE`) y la regeneración (12
  llamadas, 0,432 USD; solo `asombro` mejoró). No pasan: `estafado`, `grito` y `codicia` (el peto queda tapado, `panza`
  no medible), `triunfo` (8 anillos por la pierna). Siguiente: decidir si `panza` tapada bloquea o se integra.
- Las trazas son candidatas (`misiones/evidencia/0006/trazas/`): ninguna entra en el rig hasta pasar.
- Siguiente: las decisiones → re-correr `py kx_lamina.py` (gratis) → regenerar las que fallen →
  integrar `traza_<pose>.js` en `Tadeo.jsx`.

---

## Actualizado: 17 ago 2026 — canal reordenado, calendario fijo y dos Shorts programados

**Otra sesión.** El grueso del día no fue producir: fue descubrir que medíamos mal.

- **CORRECCIÓN QUE MANDA SOBRE TODO:** el gancho SÍ es el cuello. "Se quedaron a
  mirar" está en **27,1%** (banda sana 70-90%). La curva de `youtube_api.py
  retention` viene normalizada y NO ve a los que se van: ese dato solo está en
  Studio > vídeo > Participación. Detalle e hipótesis en `HISTORIAL_MEJORAS.md`;
  reglas en `RETENTION_CHECKLIST.md` y `GANCHO_SHORTS_2026.md` (investigación
  EN/ES/JA/KO/ZH con las aperturas reescritas).
- **Público: hispanos en EE.UU.**, español con la voz de siempre pero productos
  gringos y dólares. El keyword research va con `country: US`.
- **Calendario fijo** en `CALENDARIO_PUBLICACION.md`: Shorts martes, jueves y
  sábado 19:00 MX (sábado 11:00), y **un largo todos los domingos**.
- **Programados**: `AkENgCh4Klo` (pay in 4) el 19 ago 01:00 UTC y `WD4xyKgPEew`
  (Pelando cable #2) el 21 ago 01:00 UTC. Ambos privados con `publishAt`.
- **Canal optimizado**: banner nuevo (arte de Flow con la hoja madre + texto en
  la zona segura), bio sin las acotaciones de guion que estaban públicas,
  keywords al día, país US, trailer para no suscritos, 4 playlists con keyword
  por título y 16 descripciones enlazando a su playlist (antes: cero).
- **El largo está muerto de distribución, no de calidad**: 6 impresiones en 3
  días. Un largo sin audiencia previa solo entra por búsqueda, y su tema no
  responde a ninguna. Ver `ESCUELA_ROMUALD.md` con la demanda medida.
- **Wan 2.2 en local funcionando**: 7m41s por clip a 480x832. Se mete al vídeo
  con `pipeline.py --wan-hero <clip> --reusar-imagenes`, NO con `korex_animate`.
  Ver `INSTALACION_WAN.md`.

### Pendiente inmediato

1. **Guion `scripts/korex-historial-invisible.json` escrito y sin producir** —
   el de "te negaron la tarjeta" (crédito, competencia 12,2). Falta tu visto
   bueno final; iba para el sábado 11:00.
2. **El largo de los domingos no tiene tema elegido.** El candidato con datos es
   "cómo salir de deudas sin ganar más" (8.020 búsquedas/mes).
3. El vídeo "Deja de pelar: el secreto de los lacras" rechaza toda edición de
   metadatos con un 400 de YouTube. Sin resolver.
4. Ocho vídeos promo antiguos de KOREXF quedaron fuera de las playlists a
   propósito: romperían la reproducción encadenada.

---

## 13 ago 2026 — largo de KOREX publicado (no listado) y miniaturas

**Sesión de Claude.** Lo terminado hoy, en orden:

- **Primer vídeo LARGO de KOREX subido**: `output/2026-08-12-dos-sueldos/`,
  8m47s, 1080p, 104 cortes sobre 52 imágenes.
  [CnVXxp-Ca_Y](https://youtube.com/watch?v=CnVXxp-Ca_Y) — **no listado**, con
  miniatura puesta, ya en `video_log.csv`. Falta decidir si se publica.
- **`korex_largo.py` (nuevo)**: el montador del largo. El corte lo manda la
  frase, medida con whisper sobre la voz ya sintetizada (1.273 palabras, la
  última cae en 526,3 de 526,8 s). Sin subtítulos quemados ni cierre. Música:
  las cuatro pistas CC0 encadenadas.
- **`guion_lint.py` (nuevo)**: redundancia DENTRO de un guion. Nació del
  feedback de Fabián ("repite una y otra vez lo mismo"), que era medible: casa
  24 veces, rebusca 24, mano 13 en 1.273 palabras. Los Shorts pasan limpios.
  Regla escrita en `EDICION_GUIONES.md` §4.
- **`MINIATURAS_LARGO_2026.md` (nuevo)**: investigación EN/ES/JA/KO/ZH. Lo que
  más cambió el trabajo salió de bajar las miniaturas reales de `@Zenn0009` y
  `@ecomonos` (`assets/referencia/miniaturas/`): **ninguna es gris**.
- **Ropa permitida en Tadeo** (decisión de Fabián): se quitó la prohibición de
  `CHARACTER_LOCK`; lo que se juzga ahora es la cara. Los secundarios no tienen
  que parecerse a él.
- **`youtube_api.py`**: `upload --thumbnail`. Antes no había forma de subir la
  miniatura con el vídeo.

### Flow cambió de build a mitad de la tanda (13 ago, ~20:19)

Rompió tres cosas a la vez, ya arregladas en `flow_automation.py`: aviso de
derechos al subir (autorizado a aceptar), su backdrop huérfano comiéndose los
clicks, y el input oculto que ahora sube a la biblioteca global mientras el
selector solo lista el proyecto. **Si una tanda se queda muda, mirar esto
primero.** Y nunca lanzar una tanda con `| grep | tail`: no suelta una línea
hasta el final, y por eso se tardó hora y media en ver el fallo.

### Pendiente / siguiente

1. **Pestaña Personajes de Flow (build nuevo) — a probar en el próximo vídeo.**
   Flow ya trae personajes reutilizables nativos: nombre, "Información del
   personaje" que usa su agente para construir escenas, **"Crear cuerpo"**
   (turnaround automático desde una lámina) y hasta una voz. Es, nativo, lo que
   montamos a mano con hoja madre + `CHARACTER_LOCK` + láminas de referencia.
   Probado hasta subir a Tadeo; **no queda guardado si no se pulsa "Listo"**.
   Decisión pendiente: migrar o seguir con las láminas.
2. Decidir si el largo pasa a público; si se publica, `post_question_comment.py`.
3. Activar **Test & Compare** cuando haya 2-3 largos: elige por tiempo de
   visualización, no por CTR, y es gratis.
4. Los 5 Shorts subidos siguen con títulos en pregunta que los datos
   desaconsejan (ver conflicto en `INDEX.md`). No tocados: son decisión suya.
