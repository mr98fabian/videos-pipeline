# MISIÓN NNNN — <título corto>

Estado: pendiente · Rama: `<tipo>/<slug>` · Autor: Mijo · Ejecutor: —

## Objetivo
Qué debe ser verdad cuando termine, en una o dos frases.

## Contexto
Por qué se hace ahora, qué se sabe, qué ya se intentó. Enlaces a la bitácora o
a misiones previas.

## Criterios de aceptación ejecutables
_(OBLIGATORIO y lleno ANTES de producir o codificar. Sin esta sección la misión
no se toma.)_ Cada criterio es algo que se ejecuta o se mira y da sí/no:
1. `<comando>` → `<salida o exit code esperado>`
2. `<archivo generado>` (hoja de contacto, gate.json…) muestra `<qué>`
3. …

## Trabajo
Pasos o piezas concretas. Lo que queda fuera de alcance, explícito.

## Aceptación
Comprobaciones verificables (comandos, archivos, hojas de contacto) que Mijo
usará para auditar. Si una regla de la casa aplica, nombrarla.

## Reporte
_(lo escribe el ejecutor al terminar)_
- Qué se hizo:
- **Auto-verificación, un artefacto por criterio** (obligatorio):
  | # | Criterio | Artefacto (comando + salida pegada, o ruta del archivo) | ✅/❌ |
  |---|---|---|---|
  | 1 | … | … | … |
- `py scripts/verify.py` → salida pegada (debe ser VERDE para pasar a `en-auditoria`)
- Fallos encontrados y su arreglo:
- Qué queda pendiente:
- Rama / PR:
