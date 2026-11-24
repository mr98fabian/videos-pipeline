# MISIÓN 0003 — Limpieza antes de hacer público el repo

Estado: completada (etapa 1 fusionada en 432b0fa; etapa 2 ejecutada el 23 nov 2026) · Rama: `chore/limpieza-pre-publico` · Autor: Mijo · Ejecutor: Claude

## Objetivo
Que el árbol de `master` pueda hacerse público sin rutas con el usuario local ni configuración local de
Claude, y que los commits futuros salgan con el correo noreply de GitHub. Opción (a) aprobada por Fabian:
se arregla el árbol y el historial pasado se acepta tal cual.

## Contexto
La protección de `master` de la misión 0002 fue rechazada por el plan Free (403,
`misiones/evidencia/0002/proteccion_master.txt`); en un repo público sí se puede aplicar. Hacerlo público
es la etapa 2 y **solo** se ejecuta tras la auditoría de Mijo y la orden de merge de Fabian.

## Criterios de aceptación ejecutables
1. `git grep -n -i "<usuario-local>"` (el nombre de usuario de Windows, con o sin `Users\`) → sin salida (exit 1).
2. `scripts/run_ep2_once.bat` entra en la raíz del repo por su propia ubicación (`%~dp0..`): mismo
   directorio de trabajo que antes, desde cualquier ruta de checkout → `cmd /c` de la línea `cd` imprime la raíz del repo.
3. `git check-ignore -v .claude/settings.local.json` → lo ignora una regla de `.gitignore`.
4. `git config --local user.email` → el noreply `<id>+<login>@users.noreply.github.com` de la cuenta
   (`gh api user` da id y login); `git log -1 --format=%ae` de esta rama → ese noreply.
5. `py scripts/verify.py` → VERDE (exit 0).
6. `git diff --name-only origin/master...HEAD` → solo `scripts/run_ep2_once.bat`, `.gitignore`,
   `misiones/0003-limpieza-pre-publico.md`, `misiones/cola.md`.

## Trabajo
1. `.bat`: ruta relativa a su ubicación.
2. `.gitignore`: `.claude/settings.local.json`.
3. Git local del repo con el noreply.
4. verify.py, PR sin merge, `en-auditoria`.

Fuera de alcance: reescribir el historial; la etapa 2 (visibilidad pública y protección de `master`).

## Aceptación
Mijo comprueba los 6 criterios. Regla de la casa 9 (secretos fuera del repo): `git status` limpio de
credenciales antes del commit.

## Reporte — Etapa 1
_(los criterios los escribió otra sesión de Claude en `27356ca`; esta sesión
retomó la rama, que esa sesión había borrado en local, desde ese mismo commit)_

- Qué se hizo:
  - `scripts/run_ep2_once.bat`: `cd /d "%~dp0.."` en lugar de la ruta fija con
    el usuario local. `%~dp0` es la carpeta del `.bat` (`scripts\`), así que
    `..` es la raíz del repo: en el checkout principal es la misma carpeta
    `Videos` de antes, y además funciona en cualquier otro checkout.
  - `.gitignore`: `.claude/settings.local.json` (antes solo lo cubría el
    ignore global de la máquina).
  - `git config --local user.email` = noreply de la cuenta.

- **Auto-verificación, un artefacto por criterio**
  | # | Criterio | Artefacto | ✅/❌ |
  |---|---|---|---|
  | 1 | sin rutas con el usuario | `misiones/evidencia/0003/criterios_1_a_3.txt`: `git grep` → exit 1 | ✅ |
  | 2 | el `.bat` entra en la raíz | mismo archivo: sus líneas hasta el `cd`, lanzadas desde `C:\`, imprimen la raíz del checkout | ✅ |
  | 3 | ignorado por el repo | mismo archivo: `.gitignore:137:.claude/settings.local.json` | ✅ |
  | 4 | commits con noreply | `misiones/evidencia/0003/criterios_4_a_6.txt` | ✅ |
  | 5 | verify VERDE | mismo archivo | ✅ |
  | 6 | diff limitado a 4 archivos (+ evidencia) | mismo archivo | ✅ |

- Fallos encontrados y su arreglo: el `user.email` local con el noreply no
  estaba puesto (solo el global, con el gmail); se configuró aquí. El email
  que da `gh api user/emails` necesita el scope `user`, que el token no tiene:
  se construyó con el formato oficial `<id>+<login>@users.noreply.github.com`
  a partir de `gh api user` (igual al que muestra Settings → Emails).
- Desviación: el criterio 6 lista 4 archivos; el diff trae además
  `misiones/evidencia/0003/*.txt`, la evidencia que exige la plantilla.
- Qué queda pendiente: auditoría de Mijo → orden de merge de Fabian → Etapa 2
  (visibilidad pública + protección de `master`).

## Reporte — Etapa 2
Ejecutada tras la auditoría aprobada de Mijo y el merge squash del PR #4
(`master` = `432b0fa`). Evidencia: `misiones/evidencia/0003/etapa2_publico_y_proteccion.txt`.

| # | Paso | Artefacto | ✅/❌ |
|---|---|---|---|
| 0 | barrido previo sobre `432b0fa` | 0 archivos con el usuario local; 1 acierto de patrón fuerte = falso positivo (`0000-oficina-y-git.md:68` nombra el prefijo `GOCSPX-` en la lista de patrones, sin valor) | ✅ |
| 1 | visibilidad pública | `gh repo view` → `"visibility":"PUBLIC"` | ✅ |
| 2 | protección de `master` | `gh api .../branches/master/protection` → `required_checks: ["verify"]`, `strict: true`, `pr_required: true` (0 aprobaciones), `enforce_admins: true`, `force_pushes: false`, `deletions: false` | ✅ |

- No verificado: el rechazo real de un push directo a `master`. Se intentó con
  un commit vacío y el modo automático de Claude Code bloqueó la acción; la
  configuración que lo garantiza sí está confirmada por la API.
- Consecuencia operativa: desde ahora **nada entra a `master` sin PR con
  `verify` en verde**, tampoco para el admin (`enforce_admins`). Este mismo
  reporte entra por PR.
- Aceptado por orden de Fabian (opción a): el historial pasado y los 139
  commits con el correo personal como autor quedan públicos.
