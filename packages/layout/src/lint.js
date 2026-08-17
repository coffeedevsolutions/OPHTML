// The CRT linter.
//
// A 2001 living-room television is a hostile output device: overscan
// eats the edges, interlacing makes single-pixel horizontal lines
// shimmer, and NTSC composite smears saturated reds. None of these are
// visible in a desktop browser preview, so the compiler checks for them
// statically. Lints are warnings, not errors — a homebrew author with an
// LCD and component cables may ignore all of them deliberately.

const DIRS = ['up', 'down', 'left', 'right'];

export const DEFAULT_LINT_OPTIONS = Object.freeze({
  canvasW: 640,
  canvasH: 448,
  // Title-safe area: 5% inset per side, derived from the canvas so PAL
  // (640x512) gets its own numbers (SMPTE ST 2046 is stricter; 5%
  // matches what PS2-era games actually shipped). Override with
  // explicit safeInsetX/safeInsetY when targeting a known display.
  safeInsetX: null,
  safeInsetY: null,
  minFontSize: 14,
  minContrast: 3.0,
});

function luminance([r, g, b]) {
  const lin = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrastRatio(a, b) {
  const la = luminance(a);
  const lb = luminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/** Composite `top` over `bottom` (both RGBA 0-255), returning RGB. */
function over(top, bottom) {
  const a = top[3] / 255;
  return [
    Math.round(top[0] * a + bottom[0] * (1 - a)),
    Math.round(top[1] * a + bottom[1] * (1 - a)),
    Math.round(top[2] * a + bottom[2] * (1 - a)),
  ];
}

/**
 * Lint a compiled document. Takes the display list plus focus graph and
 * returns an array of { rule, message } warnings.
 */
export function lintDocument(commands, focusGraph, options = {}) {
  const opt = { ...DEFAULT_LINT_OPTIONS, ...options };
  if (opt.safeInsetX == null) opt.safeInsetX = Math.round(opt.canvasW * 0.05);
  if (opt.safeInsetY == null) opt.safeInsetY = Math.round(opt.canvasH * 0.05);
  const warnings = [];
  const safe = {
    x0: opt.safeInsetX,
    y0: opt.safeInsetY,
    x1: opt.canvasW - opt.safeInsetX,
    y1: opt.canvasH - opt.safeInsetY,
  };

  // Track the nearest opaque background under each command for contrast.
  // Paint order means "last rect fully containing this command wins" is
  // a good approximation for flat UI.
  const bgStack = [];

  for (const cmd of commands) {
    if (cmd.op === 'rect') {
      if (cmd.fill && cmd.fill[3] > 0) bgStack.push(cmd);

      if (cmd.borderWidth === 1 || (cmd.fill && cmd.h === 1)) {
        warnings.push({
          rule: 'interlace-flicker',
          message: `1px line at (${cmd.x},${cmd.y}) will shimmer on an interlaced CRT; use 2px`,
        });
      }
      if (cmd.fill) {
        const [r, g, b] = cmd.fill;
        if (r > 200 && g < 80 && b < 80) {
          warnings.push({
            rule: 'ntsc-red-bleed',
            message: `saturated red fill rgb(${r},${g},${b}) at (${cmd.x},${cmd.y}) smears on composite video`,
          });
        }
      }
      continue;
    }
    if (cmd.op !== 'text') continue;

    // --- text lints ---
    if (cmd.size < opt.minFontSize) {
      warnings.push({
        rule: 'min-font-size',
        message: `"${cmd.text.slice(0, 24)}" is ${cmd.size}px; below ${opt.minFontSize}px is unreadable from a couch`,
      });
    }
    if (cmd.x < safe.x0 || cmd.y < safe.y0 || cmd.y + cmd.size > safe.y1) {
      warnings.push({
        rule: 'overscan',
        message: `text "${cmd.text.slice(0, 24)}" at (${cmd.x},${cmd.y}) leaves the title-safe area; a CRT may crop it`,
      });
    }
    for (const ch of cmd.text) {
      const cp = ch.codePointAt(0);
      if (cp > 0x24FF && !(cp >= 0x2000 && cp <= 0x206F)) {
        warnings.push({
          rule: 'charset',
          message: `codepoint U+${cp.toString(16).toUpperCase()} in "${cmd.text.slice(0, 24)}" — non-Latin text wrapping is untested`,
        });
        break;
      }
    }
    // Contrast against the innermost background containing the text.
    let bg = null;
    for (let i = bgStack.length - 1; i >= 0; i--) {
      const r = bgStack[i];
      if (cmd.x >= r.x && cmd.y >= r.y && cmd.x <= r.x + r.w && cmd.y <= r.y + r.h) {
        bg = r.fill;
        break;
      }
    }
    if (bg && cmd.color[3] > 0) {
      const fg = cmd.color[3] < 255 ? over(cmd.color, bg) : cmd.color.slice(0, 3);
      const ratio = contrastRatio(fg, bg.slice(0, 3));
      if (ratio < opt.minContrast) {
        warnings.push({
          rule: 'contrast',
          message: `"${cmd.text.slice(0, 24)}" contrast ${ratio.toFixed(2)}:1 < ${opt.minContrast}:1 — CRTs crush shadows harder than your monitor`,
        });
      }
    }
  }

  // Focus targets need visible extents for the couch test too.
  for (const node of focusGraph.nodes) {
    const [x, y, w, h] = node.rect;
    if (w < 24 || h < 24) {
      warnings.push({
        rule: 'focus-target-size',
        message: `focusable "${node.name}" is ${w}x${h}px; smaller than 24px is hard to see highlighted from 3 meters`,
      });
    }
    if (x + w > safe.x1 + opt.safeInsetX || y + h > safe.y1 + opt.safeInsetY) {
      warnings.push({
        rule: 'overscan',
        message: `focusable "${node.name}" extends past the action-safe area`,
      });
    }
  }

  return warnings;
}
