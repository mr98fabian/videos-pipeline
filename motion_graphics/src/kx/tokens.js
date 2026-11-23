// Design tokens de KoreX — la única fuente de color, tipo, zona segura y texturas.
// Toda plantilla futura (Fases 2-4) importa de aquí; ningún componente escribe
// un hex o un tamaño de fuente propio. korex_qa.check_palette lee los mismos
// valores (PALETTE_RGB en korex_qa.py) — si cambias uno, cambia el otro.

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;

// Paleta cerrada. DEBT es el único color: solo pizarra y número héroe,
// nunca sobre un personaje, ≤8 % de los píxeles de cualquier frame.
export const INK = "#111111";
export const PAPER = "#F4F1EA";
export const DEBT = "#C8102E";
export const PALETTE = { INK, PAPER, DEBT };
export const DEBT_MAX_FRACTION = 0.08;

// Zona segura de Shorts: caja de 840×960. Fuera quedan la UI de YouTube
// arriba (288), abajo (672: título, descripción, barra), y la columna de
// botones a la derecha (192). Todo texto y todo número vive dentro.
export const SAFE = { left: 48, top: 288, width: 840, height: 960 };
SAFE.right = SAFE.left + SAFE.width; // 888
SAFE.bottom = SAFE.top + SAFE.height; // 1248

// Tipografías: exactamente dos (las carga fonts.js).
//  DISPLAY → números, títulos y karaoke. MARKER → la pizarra.
export const DISPLAY = "Archivo";
export const MARKER = "Permanent Marker";

export const TYPE = {
  captionSize: 72, // spec: 64-80 px
  captionWeight: 800,
  captionLineHeight: 1.08,
  titleSize: 96,
  titleWeight: 900,
  heroSize: 260,
  heroWeight: 900,
  markerSize: 84,
};

// Karaoke (patrón template-tiktok de Remotion).
export const CAPTIONS = {
  combineTokensWithinMilliseconds: 800,
  minWords: 2,
  maxWords: 4,
};

// Grano de película: sutil, acromático, cambia cada frame.
export const GRAIN = { opacity: 0.07, baseFrequency: 0.85 };

// Boiling line: el contorno "hierve" como animación dibujada a mano.
// Cambia de dibujo cada `step` frames y cicla entre `variants` dibujos
// (en vez de un ruido nuevo por frame, que se ve digital).
export const BOIL = { step: 3, variants: 3, scale: 2.6, baseFrequency: 0.018 };
