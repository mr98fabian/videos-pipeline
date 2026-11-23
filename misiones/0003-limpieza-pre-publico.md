# MISIÓN 0003 — Limpieza antes de hacer público el repo

Estado: en-curso · Rama: `chore/limpieza-pre-publico` · Autor: Mijo · Ejecutor: Claude

## Objetivo
Que el árbol de `master` pueda hacerse público sin rutas con el usuario local ni configuración local de
Claude, y que los commits futuros salgan con el correo noreply de GitHub. Opción (a) aprobada por Fabian:
se arregla el árbol y el historial pasado se acepta tal cual.

## Contexto
La protección de `master` de la misión 0002 fue rechazada por el plan Free (403,
`misiones/evidencia/0002/proteccion_master.txt`); en un repo público sí se puede aplicar. Hacerlo público
es la etapa 2 y **solo** se ejecuta tras la auditoría de Mijo y la orden de merge de Fabian.

## Criterios de aceptación ejecutables
1. `git grep -n -i "Users[\\/]Khine"` → sin salida (exit 1).
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

## Reporte
_(lo escribe el ejecutor al terminar)_
