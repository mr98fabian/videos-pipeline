# MISIÓN 0002 — Oficina nivel KoreX (el mismo sistema operativo de trabajo)

Estado: en-auditoria · Rama: `chore/oficina-nivel-korex` · Autor: Mijo · Ejecutor: Claude Code

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
_(completo: 3/3 criterios; paso 5 documentado — el plan lo rechaza)_

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
  | 2 | PR rojo / PR verde | `misiones/evidencia/0002/ci_pr_rojo_y_verde.txt`: PR de prueba [#2](https://github.com/mr98fabian/videos-pipeline/pull/2) → `verify fail` con los 3 fallos nombrados; cerrado sin fusionar (`mergedAt: null`) y rama `test/ci-rojo-canario` borrada. PR real [#3](https://github.com/mr98fabian/videos-pipeline/pull/3) → `verify pass` | ✅ |
  | paso 5 | protección de `master` | `misiones/evidencia/0002/proteccion_master.txt`: branch protection y ruleset → HTTP 403 «Upgrade to GitHub Pro or make this repository public». No se forzó nada | ⚠️ plan |
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

- **Protección de `master` (paso 5):** el plan Free no la permite en repos
  privados, ni la clásica ni por rulesets (403 en ambas). Mientras tanto la
  oficina opera con CI visible (`verify` en cada push y PR) + disciplina de PR.
  Activarla de verdad exige GitHub Pro (~4 USD/mes) o repo público — decisión
  de Fabian, no del ejecutor. El JSON que se intentó (PR obligatorio, check
  `verify` estricto, sin force-push ni borrado, `enforce_admins`) queda listo
  para reaplicar tal cual.

- **Cómo preparar `feat/sistema-videos-korex` para heredar el hook** (medido
  con `validate_script` + `lint_enie` sobre sus 13 guiones sin commitear):
  la premisa «13 en rojo por falta de beat» era más gruesa que la realidad:
  **7 ya pasan** (30-por-ciento-secreto, dos-tadeos, historial-invisible,
  muela-babilonia, sobregiro-cortesia, tarjeta-gratis-si-sabes-usarla,
  venezuela-dame-dos) y **6 fallan, no todos por el beat**:
  | Guion | Fallo | Arreglo |
  |---|---|---|
  | `korex-bono-1648` | 0 beats | marcar con `*` la pose de la escena del `twist_phrase` |
  | `korex-botas-baratas` | 0 beats | ídem |
  | `korex-pay-in-4` | 0 beats | ídem |
  | `korex-fiado` | 0 beats + `twist_phrase` no literal | beat + copiar el giro tal cual está en `script` |
  | `korex-deuda-eeuu-vs-tuya` | 16 search_terms para 14 oraciones | partir 2 oraciones o fundir 2 términos (corte a mitad de frase si no) |
  | `korex-cinco-libros-sin-historial` | giro al 24 % (banda 25-75 %) | mover el giro 1-2 frases más tarde |
  Orden recomendado: (1) fusionar primero esta misión en `master` (orden de
  Fabian); (2) en `feat`, `git merge master`; (3) antes de cerrar ese turno,
  `py scripts/verify.py` y arreglar los 6 de la tabla — el hook no deja cerrar
  hasta entonces (o libera una vez para reportar, por el antibucle); (4) los
  guiones ya publicados no se tocan: si alguno de los 6 ya está subido, se
  saca del árbol de trabajo en vez de editarlo (regla 3).
  Ojo: la puerta solo mira lo que está sin commitear o cambiado frente a la
  base, así que commitear los 6 sin arreglar no los esconde — la CI del PR los
  pondría en rojo igual.

- Qué queda pendiente: auditoría de Mijo; merge de #3 por orden de Fabian;
  decisión de Fabian sobre GitHub Pro para la protección real.
- Rama / PR: `chore/oficina-nivel-korex` → [#3](https://github.com/mr98fabian/videos-pipeline/pull/3), CI verde, sin fusionar.
