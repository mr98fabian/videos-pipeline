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

## Actualizado: 13 ago 2026 — largo de KOREX publicado (no listado) y miniaturas

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
