# Oficina de Videos — cómo se trabaja

Esta oficina es **solo del pipeline de videos** (`Proyectos_Software/Videos`).
La de la app CoreX-SF es otra: nunca se cruzan misiones, prompts ni ramas entre
los dos repos.

## Flujo de una misión

1. **Mijo escribe la misión** en `misiones/NNNN-<slug>.md` con la plantilla
   (`plantilla-mision.md`) y la anota en `cola.md` como `pendiente`.
2. **El ejecutor la toma**: la marca `en-curso` en `cola.md` y trabaja en una
   rama propia (`feat/…`, `fix/…`, `chore/…`), nunca sobre `master`.
3. **El ejecutor escribe el Reporte** al final del mismo archivo de misión: qué
   hizo, cómo lo verificó, qué falló y qué queda. Abre PR (o deja el Reporte
   listo si no hay remoto) y marca la misión `en-auditoria`.
4. **Mijo audita** contra la sección *Aceptación* y anota el resultado.
5. **Fabian aprueba** y ordena el merge. Nadie mergea sin esa orden.

## Reglas de la oficina (Misión 0002, igual que CoreX-SF)

- **Criterios antes que código.** La sección «Criterios de aceptación
  ejecutables» se llena antes de producir; una misión sin ella no se toma.
- **Artefacto por criterio.** El Reporte pega, por cada criterio, el comando y
  su salida o la ruta del archivo generado. «Lo probé» no es evidencia.
- **La puerta es `scripts/verify.py`.** Corre sola al cerrar cada turno de
  Claude Code (Stop hook en `.claude/settings.json`) y en la CI de GitHub en
  cada push y PR. Con el árbol sucio y la puerta en rojo, el turno no cierra.
- **Merges solo por PR con CI verde.** Nada se empuja directo a `master`.
- **La regla de oro: todo error que se repita se convierte en test o en
  bloqueo automático** (`tests/` o un chequeo nuevo de `verify.py`), no en una
  nota más en un `.md`.
- El ejecutor reporta y deja `en-auditoria`; Mijo audita; Fabian aprueba los
  merges.

Estados válidos en `cola.md`: `pendiente` · `en-curso` · `en-auditoria` ·
`aprobada` · `rechazada` · `bloqueada`.

## Reglas de la casa (no negociables)

1. **Ningún video se produce sin el guion aprobado por Fabian en el chat.** Un
   mensaje ambiguo no es aprobación.
2. **Antes de cualquier llamada a vidIQ, se revisa el saldo de créditos**
   (`vidiq_balance`, gratis). Sin saldo, se avisa y no se arranca.
3. **Los videos ya publicados no se rehacen ni se tocan.** Las mejoras empiezan
   con el siguiente guion.
4. **Se publica siempre por API, nunca a mano en Studio.** Mínimo **58 s** por
   Short (guarda de `youtube_api.upload_video`).
5. **Se verifica el ARTEFACTO, no la palabra del generador**: hoja de contacto
   (`korex_qa.py`) antes de dar nada por bueno.
6. **Nada de capturas de periódicos falsas ni citas falsas de medios reales.**
   La prensa se captura de la fuente real.
7. **Google Flow y Wan son LEGADO en la ruta KOREX**: no se invocan sin orden
   expresa (`pipeline.py --korex-legacy`).
8. **La voz real de Fabian nunca va en contenido público.**
9. **Los secretos jamás entran al repo**: `client_secret*.json`, `token*.json`,
   `.env`, `*key*.txt`, `*.pickle`, llaves y sesiones de navegador
   (`.flow_profile/`). Están en `.gitignore`; antes de cada commit, `git status`
   y revisar que nada de eso aparezca.

## Dónde vive el contexto

`ESTADO_SESION.md` (relevo entre sesiones), `INDEX.md` (mapa de la
documentación), `HISTORIAL_MEJORAS.md` (bitácora: toda misión que cambie la
salida de un video deja entrada aquí), `CLAUDE.md` (arquitectura).
