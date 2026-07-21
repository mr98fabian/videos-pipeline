import { registerRoot } from "remotion";
import { Composition } from "remotion";
import { MotionOverlay } from "./MotionOverlay";
import { PageFlip } from "./PageFlip";
import { AutoOverlay } from "./AutoOverlay";
import { RealCollage } from "./RealCollage";

const WIDTH = 1080;
const HEIGHT = 1920;
const FPS = 30;

const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="MotionOverlay"
        component={MotionOverlay}
        durationInFrames={FPS * 4}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{
          keyword: "INTERCEPTED",
          iconEmoji: "🔓",
          popFrame: 8,
        }}
      />
      <Composition
        id="PageFlip"
        component={PageFlip}
        durationInFrames={Math.round(FPS * 0.55)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{
          imageA: "xf_a.png",
          imageB: "xf_b.png",
        }}
      />
      <Composition
        id="AutoOverlay"
        component={AutoOverlay}
        // duracion/fps/tamano dinamicos: pipeline.py pasa el valor real del
        // video vigente via --props (patron "dataset-render" de Remotion,
        // ver HISTORIAL_MEJORAS.md 21 jul 2026). Estos son solo fallback
        // para cuando se abre el Studio sin props.
        durationInFrames={FPS * 45}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ cues: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || FPS * 45,
          fps: props.fps || FPS,
          width: props.width || WIDTH,
          height: props.height || HEIGHT,
        })}
      />
      <Composition
        id="RealCollage"
        component={RealCollage}
        durationInFrames={Math.round(FPS * 2.4)}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ photo: "collage_photo.png", clipping: null, stampText: "DECLASSIFIED" }}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || Math.round(FPS * 2.4),
          fps: props.fps || FPS,
          width: props.width || WIDTH,
          height: props.height || HEIGHT,
        })}
      />
    </>
  );
};

registerRoot(RemotionRoot);
