// Value parsing shared by the CSS cascade and the flexbox solver.
//
// Lengths resolve to integer-friendly CSS pixels. The Graphics Synthesizer
// draws on an integer (well, 12.4 fixed point) grid and glyph advances are
// integral, so the compiler keeps fractional values only inside the flex
// solver and rounds once at paint time.

export const KEYWORD = Symbol('keyword');

const NAMED_COLORS = {
  black: [0, 0, 0, 255],
  white: [255, 255, 255, 255],
  red: [255, 0, 0, 255],
  green: [0, 128, 0, 255],
  blue: [0, 0, 255, 255],
  gray: [128, 128, 128, 255],
  grey: [128, 128, 128, 255],
  transparent: [0, 0, 0, 0],
};

// Shared with the baker: half-up rounding, NOT banker's rounding.
// Python's round() rounds half to even; the baker mirrors this exact
// floor(x + 0.5) so glyph advances agree between the two hosts.
export function roundHalfUp(x) {
  return Math.floor(x + 0.5);
}

/**
 * Parse a CSS length into {unit, value}.
 * unit is one of 'px' | '%' | 'auto' | 'number' (unitless).
 * Returns null when the token is not a length.
 */
export function parseLength(tok) {
  if (tok == null) return null;
  const s = String(tok).trim();
  if (s === 'auto') return { unit: 'auto', value: 0 };
  let m = /^(-?\d*\.?\d+)px$/.exec(s);
  if (m) return { unit: 'px', value: parseFloat(m[1]) };
  m = /^(-?\d*\.?\d+)%$/.exec(s);
  if (m) return { unit: '%', value: parseFloat(m[1]) };
  m = /^(-?\d*\.?\d+)$/.exec(s);
  if (m) return { unit: 'number', value: parseFloat(m[1]) };
  return null;
}

/** Resolve a parsed length against a container size. 'auto' resolves to null. */
export function resolveLength(len, containerSize) {
  if (len == null) return null;
  switch (len.unit) {
    case 'px': return len.value;
    case 'number': return len.value; // callers decide: line-height multiplies, flex-grow is raw
    case '%':
      if (containerSize == null) return null;
      return (len.value / 100) * containerSize;
    case 'auto': return null;
    default: return null;
  }
}

/**
 * Parse a CSS color into [r, g, b, a] with every channel 0-255.
 * Alpha stays in the CSS 0-255 domain here; the baker converts to the
 * GS 0-128 domain exactly once. Supports #rgb #rgba #rrggbb #rrggbbaa,
 * rgb()/rgba() and a small named set.
 */
export function parseColor(tok) {
  if (tok == null) return null;
  const s = String(tok).trim().toLowerCase();
  if (s in NAMED_COLORS) return NAMED_COLORS[s].slice();
  let m = /^#([0-9a-f]{3,4})$/.exec(s);
  if (m) {
    const h = m[1];
    const out = [];
    for (let i = 0; i < h.length; i++) out.push(parseInt(h[i] + h[i], 16));
    if (out.length === 3) out.push(255);
    return out;
  }
  m = /^#([0-9a-f]{6}|[0-9a-f]{8})$/.exec(s);
  if (m) {
    const h = m[1];
    const out = [];
    for (let i = 0; i < h.length; i += 2) out.push(parseInt(h.slice(i, i + 2), 16));
    if (out.length === 3) out.push(255);
    return out;
  }
  m = /^rgba?\(([^)]*)\)$/.exec(s);
  if (m) {
    const parts = m[1].split(',').map((p) => p.trim());
    if (parts.length !== 3 && parts.length !== 4) return null;
    const rgb = parts.slice(0, 3).map((p) => {
      if (p.endsWith('%')) return roundHalfUp(parseFloat(p) * 2.55);
      return roundHalfUp(parseFloat(p));
    });
    if (rgb.some((v) => Number.isNaN(v))) return null;
    let a = 255;
    if (parts.length === 4) {
      const af = parseFloat(parts[3]);
      if (Number.isNaN(af)) return null;
      a = roundHalfUp(Math.min(Math.max(af, 0), 1) * 255);
    }
    return [...rgb.map((v) => Math.min(Math.max(v, 0), 255)), a];
  }
  return null;
}

/** Split a whitespace-separated shorthand ("1px 2px") respecting parens. */
export function splitSpaces(s) {
  const out = [];
  let depth = 0;
  let cur = '';
  for (const ch of s) {
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (/\s/.test(ch) && depth === 0) {
      if (cur) out.push(cur);
      cur = '';
    } else {
      cur += ch;
    }
  }
  if (cur) out.push(cur);
  return out;
}

/** Expand a 1-4 value box shorthand into [top, right, bottom, left]. */
export function expandBox(parts) {
  switch (parts.length) {
    case 1: return [parts[0], parts[0], parts[0], parts[0]];
    case 2: return [parts[0], parts[1], parts[0], parts[1]];
    case 3: return [parts[0], parts[1], parts[2], parts[1]];
    case 4: return [parts[0], parts[1], parts[2], parts[3]];
    default: return null;
  }
}
