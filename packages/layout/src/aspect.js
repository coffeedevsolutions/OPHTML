// Display aspect and pixel aspect ratio.
//
// The GS framebuffer is a pixel grid; the television decides how wide
// that grid is drawn. Those are different things, and on this hardware
// they disagree even in the ordinary case:
//
//   640x448 shown as 4:3   -> PAR 0.9333 (pixels taller than wide)
//   640x448 shown as 16:9  -> PAR 1.2444 (pixels wider than tall)
//
// PS2 widescreen is anamorphic. The framebuffer stays 640x448 and the
// panel stretches it, so a 16:9 UI is authored in the same pixel grid
// as a 4:3 one and every square in it comes out 1.33x wider. Nothing
// about that is visible in a square-pixel preview, which is why the
// authored display aspect travels with the document from here on.
//
// PAR = displayAspect / (canvasW / canvasH)

/** Parse "16:9" or "4:3" into [num, den]. Throws on anything else. */
export function parseAspect(text) {
  const m = /^(\d+):(\d+)$/.exec(String(text).trim());
  if (!m) {
    throw new Error(`aspect: "${text}" is not a ratio like 4:3 or 16:9`);
  }
  const num = parseInt(m[1], 10);
  const den = parseInt(m[2], 10);
  if (num <= 0 || den <= 0) {
    throw new Error(`aspect: "${text}" has a zero term`);
  }
  return [num, den];
}

/** Pixel aspect ratio: >1 means pixels draw wider than they are tall. */
export function pixelAspect(canvasW, canvasH, [num, den]) {
  return (num / den) / (canvasW / canvasH);
}

/**
 * Size of the frame as the panel shows it. Height is authoritative
 * because anamorphic stretching is horizontal, so this is derived from
 * the ratio directly rather than from the PAR float.
 */
export function displaySize(canvasW, canvasH, [num, den]) {
  return { w: Math.round(canvasH * (num / den)), h: canvasH };
}

/** Video-mode presets. Canvas is the framebuffer; aspect is the panel. */
export const MODES = {
  ntsc: { w: 640, h: 448, aspect: [4, 3] },
  ntsc16x9: { w: 640, h: 448, aspect: [16, 9] },
  pal: { w: 640, h: 512, aspect: [4, 3] },
  pal16x9: { w: 640, h: 512, aspect: [16, 9] },
};
