// Text measurement and greedy line breaking.
//
// Layout runs in Node; rasterization runs in Python. The two share a
// metrics JSON (fonts/*.metrics.json, produced by ps2ui-fontgen) and one
// rounding rule:
//
//     advance_px = floor(units * size / 1000 + 0.5)
//
// The GS has no subpixel glyph positioning, so advances must be integral
// and must be computed identically on both sides — half a pixel of
// disagreement per glyph adds up to text escaping its measured box.

import { readFileSync } from 'node:fs';
import { roundHalfUp } from './values.js';

export class Font {
  constructor(metrics) {
    this.family = metrics.family;
    this.weight = metrics.weight ?? 400;
    this.unitsPerEm = metrics.unitsPerEm; // metrics are normalized to 1000
    this.ascent = metrics.ascent;   // font units, 1000/em
    this.descent = metrics.descent; // font units, positive
    this.advances = metrics.advances; // { codepoint(string): units }
    this.kerning = metrics.kerning ?? {}; // { "cp1,cp2": units }
    this.missing = metrics.missing ?? metrics.advances['63'] ?? 500; // '?'
  }

  advanceUnits(cp) {
    return this.advances[String(cp)] ?? this.missing;
  }

  /** Pixel advance of one glyph at a given px size. */
  glyphAdvance(cp, size) {
    return roundHalfUp(this.advanceUnits(cp) * size / 1000);
  }

  /**
   * Pixel kern applied *before* `cp` because `prevCp` precedes it.
   *
   * Rounded on its own, by the same rule as an advance, so every pen
   * position stays integral — the GS has no subpixel glyph placement,
   * and a fractional pen would have to be rounded somewhere anyway.
   * A consequence worth knowing: kerning is a sub-em adjustment, so it
   * rounds to zero at small sizes and only appears once the text is
   * large. "To" is -170 units, which is -5px at 32px and 0px at 11px.
   * That is the correct outcome, not a bug to compensate for.
   */
  kernPx(prevCp, cp, size) {
    if (prevCp === null || prevCp === undefined) return 0;
    const units = this.kerning[`${prevCp},${cp}`];
    return units === undefined ? 0 : roundHalfUp(units * size / 1000);
  }

  /**
   * Lay a string out: the integral pen x of every glyph, and the width.
   *
   * The single pen walk. measure(), wrapText() and ellipsize() all go
   * through it, because three separate accumulations of "advance, then
   * spacing, then kern" is exactly how they drift apart — and a drift
   * of one pixel per glyph is text escaping the box that was measured
   * for it. The baker's pen and the runtime's pen mirror this loop.
   */
  layout(str, size, letterSpacing = 0) {
    const glyphs = [];
    let x = 0;
    let prev = null;
    for (const ch of str) {
      const cp = ch.codePointAt(0);
      if (prev !== null) x += letterSpacing + this.kernPx(prev, cp, size);
      glyphs.push({ cp, x });
      x += this.glyphAdvance(cp, size);
      prev = cp;
    }
    return { glyphs, width: Math.max(x, 0) };
  }

  /** Pixel width of a string. */
  measure(str, size, letterSpacing = 0) {
    return this.layout(str, size, letterSpacing).width;
  }

  ascentPx(size) { return roundHalfUp(this.ascent * size / 1000); }
  descentPx(size) { return roundHalfUp(this.descent * size / 1000); }
}

/** First / last codepoint of a non-empty string, surrogate-aware. */
function firstCp(s) { return s.codePointAt(0); }
function lastCp(s) { const a = [...s]; return a[a.length - 1].codePointAt(0); }

const fontCache = new Map();

export function loadFont(path) {
  if (!fontCache.has(path)) {
    fontCache.set(path, new Font(JSON.parse(readFileSync(path, 'utf8'))));
  }
  return fontCache.get(path);
}

export function clearFontCache() {
  fontCache.clear();
}

/**
 * Greedy word wrap. Returns an array of lines:
 *   { text, width }
 *
 * Break opportunities are spaces only (this target renders Latin UI
 * strings; CJK line breaking is future work and is called out in the
 * linter when non-Latin codepoints appear).
 *
 * A single word wider than maxWidth is not broken: it becomes its own
 * overflowing line and the caller decides (clip / ellipsis / lint).
 */
export function wrapText(str, font, size, maxWidth, letterSpacing = 0) {
  const words = str.split(' ').filter((w) => w !== '');
  const lines = [];
  let cur = '';
  let curW = 0;
  // What joining `cur` and `word` with a space costs: the space's own
  // advance, spacing on both sides of it, and the two kerns the space
  // makes with its neighbours. Written out rather than approximated as
  // a constant space width, because that constant is what would make
  // an accumulated line width disagree with measure() of the same
  // text — and the caller uses one to size the box and the other to
  // place the glyphs. `wrapping agrees with measure` proves it.
  const joinCost = (left, right) =>
    font.kernPx(lastCp(left), 32, size)
    + font.glyphAdvance(32, size)
    + font.kernPx(32, firstCp(right), size)
    + 2 * letterSpacing;
  for (const word of words) {
    const wordW = font.measure(word, size, letterSpacing);
    if (cur === '') {
      cur = word; curW = wordW;
      continue;
    }
    const join = joinCost(cur, word);
    if (curW + join + wordW <= maxWidth) {
      cur += ' ' + word;
      curW += join + wordW;
    } else {
      lines.push({ text: cur, width: curW });
      cur = word; curW = wordW;
    }
  }
  if (cur !== '') lines.push({ text: cur, width: curW });
  if (lines.length === 0) lines.push({ text: '', width: 0 });
  return lines;
}

/**
 * Truncate a single line to maxWidth, appending an ellipsis.
 * Used for white-space: nowrap; text-overflow: ellipsis.
 *
 * O(n^2): it re-measures a shrinking candidate string whole, because
 * the ellipsis kerns against whatever glyph the cut leaves last. Fine
 * at build time on UI strings; do not reach for it on a paragraph.
 * The runtime pen deliberately uses a one-pass greedy fit instead.
 */
export function ellipsize(str, font, size, maxWidth, letterSpacing = 0) {
  const full = font.measure(str, size, letterSpacing);
  if (full <= maxWidth) return { text: str, width: full };
  const ell = '…';
  const chars = [...str];
  // Longest prefix whose *rendered* width with the ellipsis attached
  // fits. The ellipsis has to be measured attached rather than added
  // as a constant: it kerns against whatever glyph the truncation
  // leaves last, so its cost depends on where the cut falls.
  for (let n = chars.length - 1; n >= 0; n--) {
    // Don't end on a space before the ellipsis; "Shadow …" reads
    // better than "Shadow  …" and saves a glyph.
    const out = chars.slice(0, n).join('').replace(/ +$/, '');
    const w = font.measure(out + ell, size, letterSpacing);
    if (w <= maxWidth) return { text: out + ell, width: w };
  }
  // Even the bare ellipsis overflows; the caller's box is too small
  // and the linter has already said so. Return it anyway rather than
  // an empty string, so the text reads as truncated rather than absent.
  return { text: ell, width: font.measure(ell, size, letterSpacing) };
}

/** Resolve line-height (px or unitless multiplier) to integral px. */
export function resolveLineHeight(lineHeight, fontSize) {
  if (lineHeight.unit === 'px') return roundHalfUp(lineHeight.value);
  // unitless: multiplier of the font size (bug #2 regression)
  return roundHalfUp(lineHeight.value * fontSize);
}
