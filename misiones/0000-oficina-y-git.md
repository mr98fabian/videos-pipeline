# MISIÓN 0000 — Instalar la oficina y subir el repo a GitHub

Estado: en-auditoria · Rama: `chore/oficina-y-git` · Autor: Mijo · Ejecutor: Claude

## Objetivo
Dejar el pipeline de videos con oficina de misiones, escudo de secretos y repo
privado en GitHub. Solo orden: el sistema de motion graphics es la Misión 1.

## Contexto
Orden de Fabian del 22 nov 2026. La oficina de CoreX-SF es otra y no se cruza.

## Trabajo
1. Inventario (sin tocar). 2. Escudo de secretos en `.gitignore`. 3. Oficina en
`misiones/`. 4. Repo privado `Videos` en GitHub y push.

## Aceptación
- Ninguna credencial visible para git (`git status`, `git check-ignore`).
- Historial sin secretos, o misión detenida y reportada.
- `misiones/` con INSTRUCCIONES, plantilla y cola (#0 y #1).
- Repo privado con la rama empujada, o pasos exactos en el Reporte.

## Reporte

**El punto 4 no está hecho: hace falta una decisión de Fabian.** La misión daba
por hecho que no había repo. Sí lo hay, y ya está publicado:

- **Repo existente:** `https://github.com/mr98fabian/videos-pipeline`, que es
  **PÚBLICO**. Tiene 135 commits y su rama por defecto es `master`, no `main`.
  La rama de trabajo local es `claude/sticker-library-ai-vxifx9`, con 129
  commits que todavía no están en `master`.
- **No hice push.** Empujar esta rama o el trabajo nuevo lo haría público.
  Crear un repo privado `Videos` aparte tampoco resolvería nada: el código
  seguiría expuesto en `videos-pipeline`.
- **Opciones, a decidir por Fabian:**
  - **(a) Recomendada:** pasar `videos-pipeline` a privado con
    `gh repo edit mr98fabian/videos-pipeline --visibility private --accept-visibility-change-consequences`
    y luego `git push -u origin chore/oficina-y-git` + PR.
  - **(b)** Crear el privado nuevo con
    `gh repo create mr98fabian/Videos --private --source . --remote videos`
    y `git push videos master chore/oficina-y-git`. Después habría que decidir
    qué pasa con el público.
  - En cualquiera de las dos, el renombre `master`→`main` necesita su propia
    orden: cambia la rama por defecto del remoto y rompe los clones existentes.
- `gh` está autenticado como `mr98fabian`.

**Inventario**
- **Árbol sucio:** 48 entradas (21 modificadas y 27 sin trackear) del trabajo
  previo, entre ellas el prototipo de motion graphics de KOREX. Quedaron sin
  commitear y sin tocar: esta rama solo lleva la oficina y el `.gitignore`.
- **En disco:** unos 80 GB. Los más pesados son `tools/` (43 GB de pesos de
  ComfyUI/Wan), `output/` (17 GB de renders), `assets/` (15 GB) y
  `motion_graphics/` (3,6 GB, casi todo `node_modules`). Todo eso está
  ignorado: **git lleva solo 36,8 MB**.
- **`client_secret*.json`:** uno solo, `./client_secret.json`, con
  `project_id` = `gen-lang-client-0168614838`.

**Escudo de secretos**
- **Credenciales en el árbol (solo nombres):** `.env`, `client_secret.json`,
  `token.json`, `token_impixxel.json`, `token_korex.json`,
  `token_mindcheckpoint.json`, `token.json.bak`, `token_korex.json.bak`,
  `vidiq_key.txt`, la sesión del navegador `.flow_profile/` y
  `.claude/settings.local.json`.
- **Todas ya estaban ignoradas** antes de esta misión. Verificado archivo por
  archivo con `git check-ignore`.
- **Historial limpio:**
  - Ningún archivo de credenciales aparece en los 135 commits.
  - El contenido de todas las revisiones no tiene ningún patrón de clave:
    Anthropic `sk-ant-`, Google `AIza`/`GOCSPX-`/`ya29.`, refresh tokens,
    GitHub `ghp_`/`github_pat_`, Slack ni llaves privadas.
  - `.env.example` solo trae marcadores vacíos.
  - `.mcp.json` está en git, pero solo tiene tipo y URL de un servidor, sin
    cabeceras ni claves en ninguna de sus versiones.
  - No hizo falta detener la misión.
- **Añadido al `.gitignore`:**
  - Formatos de credencial que antes no cubría: `*client_secret*.json`,
    `*token*.json`, `credentials*.json`, `*.pickle`, `*.pem`, `*.key`, `*.p12`,
    `*.keystore`, `*.jks` y `.env.*` (con `!.env.example`).
  - Las cachés del motor nuevo: `motion_graphics/public/kxm/` y `*.npy`.
  - `.ruff_cache/`.
- **Aviso aparte (no es un secreto):**
  - `SFX Pack/` tiene 15 archivos de audio (660 KB) commiteados desde antes y
    hoy públicos. Conviene revisar su licencia.
  - Los guiones con "secret" en el nombre son temas de video, no credenciales.

**Oficina**
- `misiones/INSTRUCCIONES.md`: el flujo y las 9 reglas de la casa.
- `misiones/plantilla-mision.md`
- `misiones/cola.md`: esta misión como #0 `en-auditoria` y la #1 `pendiente`.
  Lleva una nota sobre el prototipo de motion graphics que ya existe sin
  commitear.

**Sin merge.** El merge lo ordena Fabian tras la auditoría de Mijo.
