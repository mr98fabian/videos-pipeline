# MISIÓN 0002 — Oficina nivel KoreX (el mismo sistema operativo de trabajo)

Estado: en-curso · Rama: `chore/oficina-nivel-korex` · Autor: Mijo · Ejecutor: Claude Code

## Objetivo
Que este repo trabaje como CoreX-SF: misiones con criterios ejecutables antes
del código, verificación en origen que bloquea, CI con bloqueo real y merges
solo por PR, adaptado a las reglas de video.

## Criterios de aceptación ejecutables
1. `python scripts/verify.py` con el árbol sucio y todo en verde → exit 0; con
   un guion deliberadamente inválido → exit ≠ 0 y el resumen nombra el fallo.
   Canario borrado tras la prueba; ambas salidas pegadas en el Reporte.
2. Un PR de prueba con ese guion inválido muestra el check `verify` en ROJO; el
   PR real de esta misión lo muestra en VERDE. El PR de prueba se cierra sin
   fusionar y su rama se borra.
3. La plantilla exige «Criterios de aceptación ejecutables» antes del trabajo y
   el Reporte exige un artefacto por criterio.

## Trabajo
1. Plantilla e instrucciones (las 9 reglas de la casa intactas).
2. `scripts/verify.py`: (a) `lint_enie`, (b) formato de guion, (c) pytest,
   (d) escudo; caché por hash del árbol.
3. Stop hook en `.claude/settings.json` → `verify.py --hook`.
4. CI `.github/workflows/ci.yml`, job de nombre estable `verify`.
5. Protección de `master` (repo PRIVADO): intentarla y documentar la respuesta
   del plan de GitHub sin forzar nada. El renombre master→main queda fuera.

## Reporte
_(parcial: criterios 1 y 3 cerrados; el 2 y el paso 5 esperan el push)_

- Qué se hizo:
  - `scripts/verify.py`: la puerta. Solo mira lo que cambió (árbol frente a
    HEAD en local; rama frente a la base en CI), porque los guiones ya
    publicados no se tocan (regla 3) y no se les exige nada retroactivo.
  - `tests/test_verify.py`: 7 casos, uno por cada forma de guion inválido.
  - `.claude/settings.json`: Stop hook (exit 2 = el turno no cierra).
  - `.github/workflows/ci.yml`: job `verify` en push a toda rama y PR a master.
  - `plantilla-mision.md` + `INSTRUCCIONES.md`: criterios antes que código,
    tabla de artefactos por criterio, regla de oro, merges solo por PR.

- **Auto-verificación, un artefacto por criterio**
  | # | Criterio | Artefacto | ✅/❌ |
  |---|---|---|---|
  | 1 | verde con árbol sucio / rojo con canario | `misiones/evidencia/0002/verify_verde.txt` (exit 0) y `verify_canario_rojo.txt` (exit 1: «2 search_terms para 3 oraciones», «0 beats», «giro al 83 %»; tras borrar el canario, exit 0) | ✅ |
  | 2 | PR rojo / PR verde | pendiente del push | ⏳ |
  | 3 | plantilla exige criterios y artefactos | `misiones/plantilla-mision.md` (sección obligatoria + tabla) | ✅ |
  | extra | escudo + hook | `verify_escudo_y_hook.txt`: `token_canario.json` forzado con `git add -f` → exit 2 («prohibido por .gitignore (*token*.json)»); mismo estado sin cambios con `stop_hook_active` → exit 0 (antibucle); retirado → exit 0 | ✅ |

- Fallos encontrados y su arreglo:
  - El escudo salía VERDE con un token forzado: en Windows el modo texto de
    `subprocess` convertía `\n` en `\r\n` y `git check-ignore` no reconocía la
    ruta. Arreglado con `-z` y bytes; el canario lo demuestra.
  - En un worktree `.git` es un archivo: la caché usa `git rev-parse --git-path`.

- Qué quedó distinto de CoreX-SF y por qué (todo es de dominio de video):
  - **Solo lo cambiado se valida.** Los 178 guiones viejos incumplen reglas
    posteriores (ninguno marca beat `*`) y no se pueden rehacer (regla 3).
  - **No hay campo `sentences`**: el formato de la casa es `script` +
    `search_terms`; las oraciones se cuentan con la misma regex que
    `pipeline.py` (`(?<=[.!?])\s+`).
  - **Beat `*` solo cuando hay `character_terms`** (ahí lo pone
    `LATIDO_DEL_STORYBOARD.md` y lo lee `korex_motion`). Los largos sin escenas
    (`formato`, sin `search_terms`) no pasan por el 1:1.
  - **`twist_phrase` exacto** (distingue mayúsculas, como pidió la misión);
    `pipeline.py` solo avisa y compara en minúsculas.
  - **Escudo con excepción `misiones/evidencia/`**: allí se fuerzan a propósito
    las hojas de contacto (`*.png` está ignorado).
  - **Antibucle del hook**: si el turno ya se bloqueó por el mismo estado y
    nada cambió, se deja cerrar para que el ejecutor lo reporte en vez de girar
    sin fin.
  - **CI sin `requirements.txt`**: la puerta solo usa stdlib + pytest; instalar
    torch/whisper en cada push no verifica nada de esto.

- Riesgo para la #1: cuando `feat/sistema-videos-korex` traiga este hook, sus
  13 guiones nuevos sin commitear pondrán la puerta en rojo (0 beats `*`) hasta
  que se marquen. Es lo que la regla pide, pero hay que saberlo.

- Qué queda pendiente: push de la rama, PR de prueba rojo + PR real verde,
  protección de `master`.
- Rama / PR: `chore/oficina-nivel-korex` (local), PR pendiente.
