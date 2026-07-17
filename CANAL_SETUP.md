# Setup del canal ImPixxel — checklist de una tarde

Solo los 4 huecos que los otros documentos no cubren. Todo lo demás (contenido,
guiones, algoritmo, humor) ya está en ROADMAP.md, HUMOR_GAMER.md e INVESTIGACION_MACK.md.

---

## 1. Configuración del canal (30 min)

- [ ] **Banner**: propuesta de valor en una frase + cadencia. Ejemplo:
  *"Gameplay, memes y la historia detrás de los videojuegos — nuevos videos cada semana"*.
  Generarlo con Nano Banana en el estilo pixel art del canal (2048x1152, zona segura
  central de 1235x338 que es lo único visible en móvil).
- [ ] **Bio ("Acerca de")**: primeras 2 líneas con keywords — es lo que indexa búsqueda.
  Ejemplo: *"Gaming en español: gameplay de LoL y más, memes de la vida gamer con Skick,
  y explainers de la historia de los videojuegos."* + mail de contacto.
- [ ] **Foto de perfil**: ya tienes la de pixel art — coherente, no tocar.
- [ ] **Playlists por pilar** (señal de estructura al algoritmo + sube tiempo de sesión):
  - "Gameplay con los panas" (clips actuales)
  - "Skick — memes de la vida gamer" (los Shorts nuevos)
  - "La historia de los videojuegos" (futuros long-form, crearla desde ya aunque esté vacía)
- [ ] **Trailer del canal** (para no suscritos): cuando exista el primer long-form, usarlo.
  Mientras tanto, el mejor Short de Skick.
- [ ] **Links**: si tienes TikTok/IG/Discord, agregarlos. Si no, omitir — no inventar redes vacías.

## 2. Miniaturas long-form (cuando arranque la Opción B)

Irrelevante para Shorts (usan el primer frame). Para los explainers estilo Mack:

- **Fórmula verificada en el canal de Mack**: pregunta corta en amarillo ALL CAPS con
  borde negro (arriba) + personaje expresivo reaccionando (Skick) + 1 elemento de contexto.
  Máximo 3 elementos.
- Generable con Nano Banana + plantilla de texto en FFmpeg (`drawtext`) — se automatiza
  en el modo --long del pipeline.
- Probar A/B nativo de YouTube (Studio lo permite con 3 variantes) desde el video 1.
- Métrica: CTR ≥4% aceptable, ≥6% bueno para canal chico.

## 3. Tarjetas y pantallas finales — el funnel Shorts → long-form

El mecanismo concreto de monetización (ROADMAP 6.4 + INVESTIGACION_MACK opción B):

- [ ] **En cada Short de Skick**: mencionar el long-form relacionado cuando exista
  ("la historia completa está en el canal") + video relacionado configurado en Studio.
- [ ] **En cada long-form**: pantalla final (últimos 20s) con 2 elementos — el siguiente
  explainer + suscribirse. El guion debe dejar espacio muerto visual para esto (nota
  para el modo --long: outro de 15-20s sin información crítica).
- [ ] **Tarjetas**: 1-2 por long-form, en los momentos donde el guion menciona otro tema
  que ya tenga video ("como vimos en el video del lag...").
- [ ] **Comentario fijado** en cada video: pregunta polarizante (genera hilo) + link al
  video hermano. El pipeline ya genera la pregunta en description.txt — copiarla ahí.

## 4. Colaboraciones — el hallazgo Mack

Mack creció en red (Explain In Paint + 2 más), no solo. Réplica a tu escala:

- [ ] **Mapear 10-15 canales gamer ES de 1K-50K subs** que suban constante (no muertos,
  no gigantes). Buscar: "memes gamer español", "lore videojuegos español", "historia
  videojuegos". Guardarlos en una lista.
- [ ] **Empezar por intercambio de comentarios/menciones**, no por pedir colab de una:
  comentar sus videos como el canal (con personalidad, no spam) las primeras 2-3 semanas.
- [ ] **Propuesta de colab concreta cuando haya 3-5 long-form publicados**: cameo de
  personajes (Skick aparece en su video / su personaje en el tuyo — costo cero con
  Nano Banana), o video conjunto de tema compartido con mención cruzada.
- [ ] **Regla**: colaborar con canales del MISMO tamaño o hasta 5x — los grandes no
  responden y los muertos no aportan.

---

## Orden de ejecución

1. Hoy: sección 1 completa (30 min) + crear las 3 playlists.
2. Esta semana: lista de 15 canales (sección 4, primer paso) + empezar a comentar.
3. Cuando arranque el modo --long: secciones 2 y 3 se activan con el primer explainer.

## Métricas de éxito del setup (revisar en 30 días)

| Qué | Señal buena |
|---|---|
| Vistas desde "canal" (no feed) | Aparece >0 — la gente entra al canal y ve más |
| Suscripciones desde página de canal | >0 — el banner/bio convierten |
| CTR long-form | ≥4% |
| Tráfico desde tarjetas/pantallas finales | Crece mes a mes |
