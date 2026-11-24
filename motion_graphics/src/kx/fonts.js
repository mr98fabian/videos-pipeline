// Las dos tipografías de KoreX, ambas OFL/Apache vía @remotion/google-fonts.
// loadFont bloquea el render (delayRender) hasta que la fuente está lista,
// así ningún frame sale con la fuente de respaldo.
import { loadFont as loadArchivo } from "@remotion/google-fonts/Archivo";
import { loadFont as loadMarker } from "@remotion/google-fonts/PermanentMarker";

export const { fontFamily: DISPLAY_FAMILY } = loadArchivo("normal", {
  weights: ["800", "900"],
  subsets: ["latin", "latin-ext"],
});

export const { fontFamily: MARKER_FAMILY } = loadMarker("normal", {
  weights: ["400"],
  subsets: ["latin"],
});
