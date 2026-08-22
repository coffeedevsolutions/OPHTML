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
  // Pixel aspect ratio; 1.0 is square. Anything else distorts shapes.
  par: 1.0,
  // Distortion a round shape can absorb before it reads as an ellipse.
  maxShapeDistortion: 0.08,
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

// Codepoints above the Latin range that are still safe to lay out: they
// are single glyphs with known advances and no line-breaking rules of
// their own. The charset lint exists to flag scripts whose wrapping the
// greedy breaker has never been tested against (CJK, Thai, Arabic), and
// warning about ○ or △ trains authors to ignore it, since every PS2
// footer carries face-button hints (backlog B13).
const SAFE_SYMBOL_RANGES = [
  [0x2000, 0x206F], // general punctuation: – — ' ' " " …
  [0x2190, 0x21FF], // arrows: D-pad hints
  [0x2200, 0x22FF], // mathematical operators: × ÷ ≤
  [0x25A0, 0x25FF], // geometric shapes: □ △ ○ ◇ face buttons
  [0x2700, 0x27BF], // dingbats: ✕ ✓
];

function isSafeSymbol(cp) {
  return SAFE_SYMBOL_RANGES.some(([lo, hi]) => cp >= lo && cp <= hi);
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

/** Paint `chain` (bottom-first RGBA fills) over `backdrop` RGB. */
/**
 * Can this rect and this text ever be on screen in the same frame?
 *
 * `:focus` is a paint-only delta: one command list carries both states
 * and the runtime draws whichever matches. So a node's focused
 * background and its unfocused text never coexist — compositing one
 * under the other invents a frame the console cannot produce. That is
 * how a chip whose focus fill is bright blue reported 1.11:1 against
 * its own unfocused grey text, a background that is only ever painted
 * when the text is white.
 *
 * Rects that belong to no focus node, or paint in every state, are
 * always present and always composited.
 */
function coexists(rect, cmd) {
  if (rect.state === 'always' || cmd.state === 'always') return true;
  if (rect.focusId == null || cmd.focusId == null) return true;
  // Same node: its two states are alternatives, never a stack.
  if (rect.focusId === cmd.focusId) return rect.state === cmd.state;
  // Different nodes, both painting their focused state. The runtime's
  // test is `c->focus == ctx->focus`, so exactly one node holds focus
  // per frame. Not reachable today: putting one focusable's rect under
  // another's text means nesting them, and box.js refuses that
  // outright ("the D-pad model has one focus ring"). This is forward
  // cover for `position: absolute`, which is the first thing that lets
  // two focusables overlap without nesting.
  if (rect.state === 'focused' && cmd.state === 'focused') return false;
  return true;
}

function compositeChain(chain, backdrop) {
  let out = backdrop;
  for (const fill of chain) out = over(fill, out);
  return out;
}

/**
 * How much of whatever is *under* the whole chain still shows through.
 * 0 means some fill in the chain is opaque and the backdrop cannot
 * matter; anything above 0 means the effective background depends on
 * content this compiler has never seen.
 */
function transmittance(chain) {
  let t = 1;
  for (const fill of chain) t *= 1 - fill[3] / 255;
  return t;
}

// A .uib is replayed over whatever the host app already drew, so when
// the stack under a run of text is translucent the true background is
// not knowable at compile time. Bracket it: black and white are the
// extremes any game frame lives between, so text that clears both
// clears everything, and text that fails either has a frame where it
// goes unreadable. Without this the rule reads the scrim's raw RGB and
// a 60%-opaque overlay lints exactly like an opaque background.
const BACKDROP_EXTREMES = [
  [0, 0, 0],
  [255, 255, 255],
];

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

  // Shapes meant to read as round come out elliptical when the panel
  // stretches the framebuffer. Flagged once per document, because the
  // fix is authoring rather than rendering: geometry is frozen at build
  // time, so a corner meant to look 6px round needs a smaller px radius
  // on a stretched display.
  if (Math.abs(opt.par - 1) > opt.maxShapeDistortion) {
    const rounded = commands.filter((c) => c.op === 'rect' && c.radius > 0).length;
    const images = commands.filter((c) => c.op === 'image').length;
    const pct = Math.round(Math.abs(opt.par - 1) * 100);
    const dir = opt.par > 1 ? 'wider' : 'narrower';
    if (rounded > 0) {
      warnings.push({
        rule: 'aspect-distortion',
        message: `${rounded} rounded corner(s) draw ${pct}% ${dir} than tall `
          + `at PAR ${opt.par.toFixed(4)}; divide the radius by ${opt.par.toFixed(3)} to look round`,
      });
    }
    if (images > 0) {
      warnings.push({
        rule: 'aspect-distortion',
        message: `${images} image(s) draw ${pct}% ${dir} than tall at PAR `
          + `${opt.par.toFixed(4)}; pre-squash the art or set an explicit width`,
      });
    }
  }

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
      if (cp > 0x24FF && !isSafeSymbol(cp)) {
        warnings.push({
          rule: 'charset',
          message: `codepoint U+${cp.toString(16).toUpperCase()} in "${cmd.text.slice(0, 24)}": non-Latin text wrapping is untested`,
        });
        break;
      }
    }
    // Contrast against every background containing the text, composited
    // in paint order. Taking only the innermost rect's raw RGB would
    // read a translucent scrim as though it were opaque.
    const chain = [];
    for (const r of bgStack) {
      if (!coexists(r, cmd)) continue;
      if (cmd.x >= r.x && cmd.y >= r.y && cmd.x <= r.x + r.w && cmd.y <= r.y + r.h) {
        chain.push(r.fill);
      }
    }
    // data-nocontrast: text whose unreadability is the point. Bring-up
    // steps 4 and 5 paint glyphs the exact colour of their block so a
    // correct console shows nothing; warning about that every build
    // would be four permanent false alarms, and a linter with permanent
    // false alarms is a linter people learn to skim past.
    if (chain.length && cmd.color[3] > 0 && !cmd.nocontrast) {
      const seeThrough = transmittance(chain) > 0;
      const backdrops = seeThrough ? BACKDROP_EXTREMES : [[0, 0, 0]];
      let worst = Infinity;
      let worstBg = null;
      for (const backdrop of backdrops) {
        const bg = compositeChain(chain, backdrop);
        const fg = cmd.color[3] < 255 ? over(cmd.color, bg) : cmd.color.slice(0, 3);
        const ratio = contrastRatio(fg, bg);
        if (ratio < worst) {
          worst = ratio;
          worstBg = backdrop;
        }
      }
      if (worst < opt.minContrast) {
        const where = seeThrough
          ? `, over a ${worstBg[0] ? 'bright' : 'dark'} frame showing through the `
            + `${Math.round(transmittance(chain) * 100)}%-transparent background`
          : '';
        warnings.push({
          rule: 'contrast',
          message: `"${cmd.text.slice(0, 24)}" contrast ${worst.toFixed(2)}:1 < ${opt.minContrast}:1${where} — CRTs crush shadows harder than your monitor`,
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
