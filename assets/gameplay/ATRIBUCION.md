# Gameplay de fondo — licencia y atribución OBLIGATORIA

Estos clips se usan como panel inferior del formato split (historia arriba,
gameplay abajo). **No son de dominio público**: están bajo Creative Commons
Attribution (CC-BY), que permite uso comercial y monetizado **a cambio de dar
crédito**. Sin el crédito, el uso deja de estar licenciado.

Licencia verificada con `yt-dlp --print "%(license)s"` antes de descargar; el
campo devolvió literalmente *"Creative Commons Attribution license (reuse
allowed)"* en los dos casos.

## Crédito a pegar en la descripción de CADA vídeo que los use

```
Background gameplay: Orbital - No Copyright (CC BY)
https://www.youtube.com/watch?v=hJcv2nZ8x84
https://www.youtube.com/watch?v=-lVgihPljuI

Background gameplay: Improvised Gameplay (CC BY)
https://www.youtube.com/watch?v=7GHdJvsErg0
```

Background gameplay: Dope Gameplays (CC BY)
https://www.youtube.com/watch?v=f8zPKHty_1I
https://www.youtube.com/watch?v=N1nnCsqS8vg
https://www.youtube.com/watch?v=4k-mphFrEFU
```

(Basta con listar el o los que realmente se usaron en ese vídeo.)

## Inventario

| Archivo | Juego | Fuente | Duración | Resolución | Licencia |
|---|---|---|---|---|---|
| `hJcv2nZ8x84_*.mp4` | Subway Surfers | [YouTube](https://www.youtube.com/watch?v=hJcv2nZ8x84) | ~76 min | 1080x1920 | CC-BY |
| `-lVgihPljuI_*.mp4` | Minecraft parkour | [YouTube](https://www.youtube.com/watch?v=-lVgihPljuI) | ~65 min | 1080x1920 | CC-BY |
| `7GHdJvsErg0_daysgone.mp4` | Days Gone, exploracion y moto | [YouTube](https://www.youtube.com/watch?v=7GHdJvsErg0) | ~10 min | 1920x1080 | CC-BY |
| `roblox_f8zPKHty_1I.mp4` | Roblox parkour | [YouTube](https://www.youtube.com/watch?v=f8zPKHty_1I) | ~26 min | 3840x2160 @60 | CC-BY |
| `roblox_N1nnCsqS8vg.mp4` | Roblox parkour (NO USAR, ver abajo) | [YouTube](https://www.youtube.com/watch?v=N1nnCsqS8vg) | ~21 min | 3840x2160 @60 | CC-BY |
| `roblox_4k-mphFrEFU.mp4` | Roblox parkour | [YouTube](https://www.youtube.com/watch?v=4k-mphFrEFU) | ~13 min | 3840x2160 @60 | CC-BY |

**Roblox, 1 ago 2026.** Los tres son del canal `Dope Gameplays`, que sube todo su
catalogo bajo CC-BY (verificado con `yt-dlp --print "%(license)s"` uno por uno).
Un solo credito cubre los tres. Son horizontales 4K, asi que al recortar a 9:16
quedan 2160x3840 de fuente para un destino de 1080x1920 -- sobra resolucion y
ademas se puede elegir QUE parte del encuadre se recorta, cosa que con el
Minecraft vertical nativo no se podia.

Aviso de licencia que no aplica al Minecraft: los juegos de Roblox los crea la
comunidad, asi que quien sube el gameplay solo puede licenciar SU grabacion, no
la experiencia grabada. Mojang publica guias comerciales explicitas; Roblox no
es igual de claro sobre terceros reutilizando la grabacion de otro. El credito
CC-BY se cumple igual, pero conviene saber que la cobertura no es identica.

## Notas de uso

- **Audio del juego en mute.** El panel inferior va siempre sin su audio: encima
  va la narración y nuestra música. Además, la música dentro del juego es la
  causa más común de reclamación de Content ID en gameplay.
- Son verticales 1080x1920 nativos, así que recortados a 1080x960 para el panel
  inferior no pierden nitidez.
- Duran más de una hora cada uno: hay material para cortar segmentos distintos
  en muchos vídeos sin repetir el mismo tramo.

## Descartado

`PxY4uK1ytqI` (Fox - No Copyright, 60 min, modo Horde Assault): licencia CC-BY
correcta, pero el metraje trae el color quemado desde el origen (verdes/amarillos
neon, no es como se ve el juego) y HUD de modo puntuacion encima -- contador,
cronometro, "0/10 SWARMER KILLED". Verificado que no es un problema de conversion
HDR: el archivo declara bt709 normal. Borrado.


## Descartado para fondo: `roblox_N1nnCsqS8vg.mp4`

Licencia CC-BY correcta, pero trae la **interfaz del juego quemada en todo el
metraje**: boton SKIP STAGE, contador de fase y cronometro en la franja
superior. Comprobado en los segundos 300, 600, 900 y 1150 -- no es un tramo, es
el video entero. Esa franja es justo donde va el contador HUD nuestro, asi que
choca. Se queda en disco por si alguna vez se usa recortando la parte de arriba,
pero no entra en la rotacion de fondos.

Los otros dos (`f8zPKHty_1I` y `4k-mphFrEFU`) estan limpios de interfaz,
verificado en varios puntos.
