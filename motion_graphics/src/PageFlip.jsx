import { useCurrentFrame, useVideoConfig, interpolate, Easing, staticFile, Img } from "remotion";

// Transicion "paso de pagina" real (rotacion 3D sobre el eje Y, no un simple
// crossfade) -- aprovecha que el estilo del canal ya es sepia/pergamino, asi
// que una hoja "girando" encaja tematicamente. Basado en el patron de
// perspective + rotateY documentado en tutoriales de page-flip con CSS 3D
// (ver investigacion 21 jul 2026).
export function PageFlip({ imageA, imageB }) {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  const progress = frame / (durationInFrames - 1);

  // easing tipo "ease-in-out" para que el giro no sea lineal -- arranca y
  // termina mas lento, como una pagina real perdiendo/ganando momentum.
  const eased = Easing.bezier(0.45, 0, 0.55, 1)(progress);
  const angle = eased * 180; // 0 -> 180 grados

  const showingA = angle <= 90;
  // sombra que se oscurece hacia la mitad del giro (la pagina de canto,
  // recibe menos luz) -- vende la ilusion de volumen sin geometria real.
  const shade = 1 - Math.sin(eased * Math.PI) * 0.55;

  return (
    <div
      style={{
        width,
        height,
        perspective: 2400,
        background: "#0d0805",
      }}
    >
      <div
        style={{
          width,
          height,
          position: "relative",
          transformStyle: "preserve-3d",
          transform: `rotateY(${angle}deg)`,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            backfaceVisibility: "hidden",
            filter: `brightness(${showingA ? shade : 1})`,
          }}
        >
          <Img src={staticFile(imageA)} style={{ width, height, objectFit: "cover" }} />
        </div>
        <div
          style={{
            position: "absolute",
            inset: 0,
            backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
            filter: `brightness(${showingA ? 1 : shade})`,
          }}
        >
          <Img src={staticFile(imageB)} style={{ width, height, objectFit: "cover" }} />
        </div>
      </div>
    </div>
  );
}
