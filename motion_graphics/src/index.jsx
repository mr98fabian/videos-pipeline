import { registerRoot } from "remotion";
import { Composition } from "remotion";
import { MotionOverlay } from "./MotionOverlay";
import { PageFlip } from "./PageFlip";
import { AutoOverlay } from "./AutoOverlay";
import { RealCollage } from "./RealCollage";
import { Proof180 } from "./Proof180";
import { Proof2 } from "./Proof2";
import { ArchivoDemo } from "./archivo/ArchivoDemo";
import { ArchivoDemo2 } from "./archivo/ArchivoDemo2";
import { ArchivoVideo } from "./archivo/ArchivoVideo";
import { StoryVideo } from "./archivo/StoryVideo";
import { KorexVideo } from "./korex/KorexVideo";

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
        id="Proof180"
        component={Proof180}
        durationInFrames={160 + 160 - 18}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="Proof2"
        component={Proof2}
        durationInFrames={300}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="ArchivoVideo"
        component={ArchivoVideo}
        durationInFrames={FPS * 60}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ manifest: { scenes: [], words: [], close: { from: 0, series: "WWII Secrets", caseNo: 1, share1: "", share2: "" } } }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props.manifest && props.manifest.durationInFrames) || FPS * 60,
          fps: FPS,
          width: WIDTH,
          height: HEIGHT,
        })}
      />
      {/* STORY VIDEO — Mind Checkpoint, formato historia sobre gameplay a
          pantalla completa. Hermano de ArchivoVideo pero con fondo de VIDEO
          continuo en vez de collage de fotos recortadas. */}
      <Composition
        id="StoryVideo"
        component={StoryVideo}
        durationInFrames={FPS * 90}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ gameplaySrc: "", words: [], redWords: [], beats: [], durationInFrames: FPS * 90 }}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames || FPS * 90,
          fps: FPS,
          width: WIDTH,
          height: HEIGHT,
        })}
      />
      {/* KOREX — piel propia del canal de finanzas satiricas (Tadeo). NO
          comparte plantilla con ArchivoVideo: ese es el expediente de
          HiddenFacts y sobre un mapache comico se lee absurdo. */}
      <Composition
        id="KorexVideo"
        component={KorexVideo}
        durationInFrames={FPS * 60}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ manifest: { scenes: [], words: [], hook: "", durationInFrames: FPS * 60 } }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props.manifest && props.manifest.durationInFrames) || FPS * 60,
          fps: FPS,
          width: WIDTH,
          height: HEIGHT,
        })}
      />
      <Composition
        id="ArchivoDemo2"
        component={ArchivoDemo2}
        durationInFrames={360}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
      <Composition
        id="ArchivoDemo"
        component={ArchivoDemo}
        durationInFrames={360}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
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
