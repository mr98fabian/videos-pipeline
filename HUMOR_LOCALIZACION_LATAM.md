# Localización del humor: qué hace gracia en LATAM, España y EE.UU.

Investigación multiidioma — agosto 2026
Idiomas consultados: español, inglés

> Aplica sobre todo al canal **ImPixxel (ES, pausado)** y a cualquier expansión a mercados hispanos; también sirve como checklist de localización si HiddenFacts genera versiones en español.

---

## 1. Marco teórico: los 4 estilos de humor y su distribución cultural

Estudio de referencia: Jiang et al. 2019 (PMC6361813, autoridad académica alta) — adaptación transcultural del Humor Styles Questionnaire. Los 4 estilos:

| Estilo | Qué es | Riesgo/beneficio |
|---|---|---|
| **Afiliativo** | Bromas para unir, "reírnos juntos" | Seguro en todas las culturas |
| **De auto-mejora** | Reírse de uno mismo para sobrellevar | Muy seguro, genera empatía |
| **Agresivo** | Sarcasmo, ridiculizar al otro | Funciona en Occidente; riesgoso en Oriente |
| **Auto-derrotista** | Ponerse a uno mismo de blanco de la burla | Entretiene pero desgasta la "autoridad" del canal si se abusa |

Hallazgo clave: **Occidente usa significativamente más humor agresivo; Oriente más afiliativo**. El estilo no es intercambiable: un guion gracioso en EE.UU. por burla puede caer cruel en México, y uno chino basado en juego fonético no sobrevive la traducción.

## 2. Qué hace gracia por cultura (síntesis de las fuentes)

| Cultura | Motor de la risa | Ejemplos / notas |
|---|---|---|
| **México** | Estereotipos y personajes (Pepito), albures (doble sentido), "resiliencia optimista" | Humor como celebración de aguantar; reírse de la propia desgracia |
| **LATAM en general** | Humor de resiliencia: optimismo ante la adversidad | Más afiliativo que agresivo; el "reírnos juntos de la vida" |
| **España** | Expresividad + sarcasmo e ironía directos | Más tolerancia al humor ácido que LATAM |
| **EE.UU.** | Ridiculizar la vanidad, la política, lo pretencioso | Sátira de estatus; roast culture |
| **China** | Juegos de pronunciación, homófonos, absurdidad cotidiana | El humor fonético NO se traduce: exige re-escritura local |
| **Rusia** | Humor oscuro | Referencia de contraste |

## 3. Los memes son pan-culturales en estructura (Yus, U. Alicante)

Francisco Yus (Universidad de Alicante) demuestra que los memes en español usan **las mismas estrategias inferenciales** que en inglés: el remate no está en el texto sino en lo que el espectador debe *inferir*. La estructura cognitiva del meme es pan-cultural; lo que cambia por cultura es **el contenido que se considera "benigno"**.

## 4. Conexión con la Teoría de la Violación Benigna (BVT)

McGraw & Warren: la risa ocurre cuando algo es simultáneamente una **violación** (de una norma, expectativa o decoro) y es percibido como **benigno** (seguro, lejano, "es broma").

La clave transcultural: **lo "benigno" depende de la distancia social y cultural del espectador**:
- Burlarse del jefe: benigno en EE.UU./España, incómodo en culturas de alta distancia de poder.
- Humor oscuro sobre desgracias: benigno en Rusia/México (resiliencia), chocante en Alemania.
- Auto-burla del narrador: benigno en casi todas partes → **el estilo más exportable**.

**Implicación para el pipeline**: el estilo de humor por defecto para contenido multi-mercado debe ser **afiliativo + auto-burla del narrador/personaje**, con la "violación" dirigida a cosas (absurdos del mundo, datos raros) y no a grupos de personas.

## 5. Reglas de localización de guiones cómicos (checklist)

1. **Nunca traducir un chiste: re-escribir el remate local.** La estructura (setup → violación → remate benigno) se conserva; el contenido del remate cambia por mercado.
2. **LATAM**: burla hacia uno mismo/hacia la situación, no hacia el otro. Tono de celebración y resiliencia, nunca de superioridad.
3. **España**: se permite más ironía y sarcasmo directo que en LATAM; se puede subir un escalón la acidez.
4. **EE.UU.**: ridiculizar la pretensión y la vanidad funciona; la política divide (evitar en canal de datos curiosos).
5. **Evitar humor fonético/juegos de palabras** en el formato Shorts automatizado: no escalan entre idiomas y rompen la reutilización del pipeline.
6. **Auto-burla como seguro universal**: un narrador/personaje que se equivoca, se sorprende o confiesa torpeza funciona en los 4 mercados (ver `SERIES_LORE_PERSONAJES.md`).

## Aplicación concreta al proyecto

- **ImPixxel (ES)**: guiones con humor afiliativo de resiliencia ("el mundo está loco pero mira qué dato tan bueno") + auto-burla del personaje narrador. Cero sarcasmo hacia grupos.
- **HiddenFacts (EN)**: la sátira de vanidad/pretensión es segura; la política no. El humor de "dato absurdo + remate seco" (estilo dry) es el más compatible con TTS.
- **Checklist en el generador de guiones**: campo `estilo_humor` ∈ {afiliativo, auto-mejora, agresivo-suave} — prohibido agresivo-fuerte y auto-derrotista sostenido en canal automatizado (erosiona la voz de marca).
- **Test BVT por guion**: ¿qué norma viola el remate? ¿es benigno para el público objetivo? Si la violación toca identidades (nacionalidad, clase, género), descartar.

## Fuentes consultadas

- Jiang, T. et al. (2019) — Humor Styles Questionnaire transcultural, PMC6361813 — EN (autoridad académica S)
- Yus, F. (Universidad de Alicante) — inferencia y memes en español, estrategias pan-culturales — ES
- Compilaciones comparativas de humor por cultura (México/Pepito, EE.UU./sátira, China/fonética, Rusia/oscuro, España/ironía) — EN/ES
- McGraw & Warren — Benign Violation Theory — EN
- Análisis de humor LATAM como resiliencia optimista — ES
