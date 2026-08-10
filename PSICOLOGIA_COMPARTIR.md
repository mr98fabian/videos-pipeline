# Psicología del compartir: por qué la gente reenvía un Short (o no)

Investigación multiidioma — agosto 2026
Idiomas consultados: inglés, español, chino (中文), japonés (日本語)

> Contexto del proyecto: en nuestros datos propios (`performance_report.csv`, 51 videos con métricas) la **mediana de shares es 0 en TODAS las bandas de duración**. La señal que más pesa en el algoritmo 2026 está completamente sin explotar. Este documento explica la ciencia detrás del "compartir" y cómo convertirla en prompts de guion.

---

## 1. El modelo base: STEPPS de Jonah Berger (EN)

Jonah Berger (Wharton, *Contagious: Why Things Catch On*) resumió en 6 principios por qué un contenido se vuelve contagioso:

| Principio | Qué significa | Traducción a guion de Short |
|---|---|---|
| **Social Currency** (moneda social) | Compartimos lo que nos hace ver bien | El dato que el espectador puede "soltar" en una conversación para quedar de listo/interesante |
| **Triggers** (disparadores) | Compartimos lo que está arriba en la mente | Conectar el dato con algo cotidiano (comida, dinero, sueño) para que se active en la vida diaria |
| **Emotion** (emoción) | Lo que sentimos, lo compartimos | Ver tabla de activación abajo |
| **Public** (público) | Imitamos lo que vemos | Formatos reconocibles y repetibles (series, plantillas) |
| **Practical Value** (valor práctico) | Compartimos para ayudar | "Guárdatelo para cuando te pase X" |
| **Stories** (historias) | Los datos viajan dentro de relatos | Mini-arco: situación → giro → resolución |

Berger & Milkman analizaron ~7.000 artículos del New York Times y encontraron que la variable que mejor predecía el "más enviado por email" no era la utilidad ni la positividad por sí solas, sino la **activación fisiológica** de la emoción que provocaba el texto.

## 2. La tabla de activación emocional (el hallazgo más accionable)

| Emoción | Activación | ¿Se comparte? |
|---|---|---|
| Asombro / awe | Alta | ✅ Mucho (la #1 en el estudio NYT) |
| Diversión / humor | Alta | ✅ Mucho |
| Ira / indignación | Alta | ✅ Mucho |
| Ansiedad | Alta | ✅ Bastante |
| **Sorpresa** | Alta | ✅ **#1 en estudios específicos de video viral** (Dobele 2007; Teixeira 2012) |
| Entusiasmo | Alta | ✅ |
| Tristeza | Baja | ❌ |
| Contentamiento / calma | Baja | ❌ |

**Regla operativa**: cada guion debe diseñarse para provocar UNA emoción de alta activación identificable. Si el guion "informa" sin provocar asombro, risa o indignación, está diseñado para morir.

## 3. Moneda social: compartir es autopresentación (ZH + EN)

El artículo de 心理学报 (Acta Psychologica Sinica, el journal de psicología de referencia en China) sobre el mecanismo psicológico del 分享 (compartir) viral lo formula así: **la gente no comparte contenido, comparte una versión de sí misma**. Compartir es un acto de gestión de impresión: "mira lo que yo encontré" = "mira qué tipo de persona soy".

El reporte de Bilibili sobre psicología de interacción llega a la misma conclusión desde los datos de su plataforma: el 转发 (reenvío) cumple dos funciones — moneda social y **expresión de identidad** ("esto representa mi tribu / mis valores").

**Implicación directa para HiddenFacts**: el espectador comparte cuando el video le da un rol social deseable:
- "El que sabe datos raros que nadie más sabe" → funciona bien en nuestro nicho
- "El que se ríe de lo absurdo del mundo" → abre la vía humor (ver `HUMOR_LOCALIZACION_LATAM.md`)
- Pregunta de diseño por guion: *"¿Qué dice de mí reenviar esto a mi grupo de WhatsApp?"*

## 4. Sorpresa como mecanismo #1 (EN)

Los estudios específicos de video viral (Dobele et al. 2007; Teixeira 2012 sobre ads virales) encontraron que la **sorpresa es la emoción más potente para disparar el reenvío**, por encima incluso del humor. Mecanismo: la sorpresa rompe la predicción → el cerebro marca el estímulo como relevante → la necesidad de procesarla se resuelve compartiéndola (contagio emocional, Rimé: las emociones intensas generan una necesidad casi fisiológica de hablarlas con alguien).

**Fórmula de guion**: plantar una predicción fuerte en el espectador y romperla en el segundo 30-60% del video. En HiddenFacts esto ya existe parcialmente ("dato curioso con giro"), pero el giro debe ser *inequívoco*: si el espectador ya adivina el remate, no hay sorpresa y no hay share.

## 5. El dato incómodo: 93% del boca a boca es offline

Berger documenta que solo ~7% del word-of-mouth ocurre online. El share dentro de la app es solo la punta visible; el objetivo real es que el video se convierta en **tema de conversación presencial** ("¿sabías que...?"). Esto refuerza la vía de moneda social + triggers cotidianos: el dato debe ser *reenarrable en una frase* por alguien que lo vio una vez.

Test práctico por guion: **"¿Puede un espectador recontar este dato en una frase en una cena?"** Si no, simplificar.

## 6. Prueba social y psicología de masas (JA)

El artículo japonés sobre psicología de masas aplicada a contenido recupera a Le Bon y la prueba social de Cialdini: la gente comparte lo que otros ya comparten. Mecanismo operativo en Shorts: el contador de shares visible y los comentarios actúan como prueba social. Refuerza la importancia de los primeros shares (semilla) y de comentarios fijados que inviten al reenvío (ver `COMENTARIOS_ENGAGEMENT.md`).

---

## Aplicación concreta al pipeline

1. **Checklist emocional en el prompt de guion** (`korex_*.py` / generador): exigir que cada guion declare `emocion_objetivo` ∈ {asombro, sorpresa, humor, indignación suave} y `momento_giro` (segundo estimado). Rechazar guiones sin emoción de alta activación.
2. **Test de moneda social**: añadir al scoring de guiones la pregunta "¿qué dice del espectador compartir esto?" — los que no pasen el test, reescribir.
3. **Giro inequívoco**: posicionar la sorpresa en el 30-60% del video, no al final (los datos propios muestran caída de retención fuerte en el segundo 6-10% y final plano; el giro tardío nadie lo ve).
4. **Reenarrable en una frase**: el dato central debe caber en una frase de ≤15 palabras (condición de boca a boca offline).
5. **Métrica a vigilar**: shares/1000 vistas por video, no solo mediana. Objetivo inicial: sacar la mediana de 0 (cualquier video con >5 shares ya es outlier interno y debe entrar al análisis de outliers).

## Fuentes consultadas

- Berger, J. — *Contagious* / STEPPS; Berger & Milkman, "What Makes Online Content Viral?" (~7.000 artículos NYT) — EN
- Dobele et al. (2007); Teixeira (2012) — emociones en video viral, sorpresa como #1 — EN
- 心理学报 (Acta Psychologica Sinica) — mecanismo psicológico del 分享 viral — ZH
- Reporte Bilibili — psicología de la interacción 转发 (moneda social + identidad) — ZH
- Artículo japonés sobre psicología de masas (Le Bon, prueba social de Cialdini) — JA
- Rimé, B. — contagio/compartir emocional — base teórica EN/FR
- Berger — 93% del word-of-mouth es offline — EN
