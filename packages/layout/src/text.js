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

  /** Pixel width of a string: sum of integral glyph advances + spacing. */
  measure(str, size, letterSpacing = 0) {
    let w = 0;
    for (const ch of str) {
      w += this.glyphAdvance(ch.codePointAt(0), size) + letterSpacing;
    }
    if (str.length > 0) w -= letterSpacing; // spacing is between glyphs
    return Math.max(w, 0);
  }

  ascentPx(size) { return roundHalfUp(this.ascent * size / 1000); }
  descentPx(size) { return roundHalfUp(this.descent * size / 1000); }
}

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
  const spaceW = font.glyphAdvance(32, size) + letterSpacing;
  const lines = [];
  let cur = '';
  let curW = 0;
  for (const word of words) {
    const wordW = font.measure(word, size, letterSpacing);
    if (cur === '') {
      cur = word; curW = wordW;
      continue;
    }
    if (curW + spaceW + wordW <= maxWidth) {
      cur += ' ' + word;
      curW += spaceW + wordW;
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
 */
export function ellipsize(str, font, size, maxWidth, letterSpacing = 0) {
  if (font.measure(str, size, letterSpacing) <= maxWidth) {
    return { text: str, width: font.measure(str, size, letterSpacing) };
  }
  const ell = '…';
  const ellW = font.glyphAdvance(0x2026, size);
  let w = 0;
  let out = '';
  for (const ch of str) {
    const a = font.glyphAdvance(ch.codePointAt(0), size) + letterSpacing;
    if (w + a + ellW > maxWidth) break;
    out += ch;
    w += a;
  }
  // Don't end on a space before the ellipsis; "Shadow …" reads better
  // than "Shadow  …" and saves a glyph.
  out = out.replace(/ +$/, '');
  w = font.measure(out, size, letterSpacing);
  return { text: out + ell, width: w + (out ? letterSpacing : 0) + ellW };
}

/** Resolve line-height (px or unitless multiplier) to integral px. */
export function resolveLineHeight(lineHeight, fontSize) {
  if (lineHeight.unit === 'px') return roundHalfUp(lineHeight.value);
  // unitless: multiplier of the font size (bug #2 regression)
  return roundHalfUp(lineHeight.value * fontSize);
}
