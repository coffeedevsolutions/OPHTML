// CSS parser and cascade.
//
// Supported selector grammar: type, .class, #id, compound (div.a#b),
// descendant combinator (whitespace), and a single :focus pseudo-class
// on the rightmost compound. Specificity is the usual (id, class, type)
// triple with source order as the tiebreak.
//
// The property set is the subset a build-time flexbox target needs.
// Unknown properties are collected as warnings, not errors: dropping a
// box-shadow should not break a build, but it should be visible.

import {
  parseLength, parseColor, splitSpaces, expandBox,
} from './values.js';

// Properties that change geometry. A :focus rule may not touch these:
// both focus states share one layout, so a geometry delta would be a
// silent no-op at best and a desync between preview and console at worst.
export const GEOMETRY_PROPS = new Set([
  'display', 'flex-direction', 'flex-wrap', 'justify-content', 'align-items',
  'align-self', 'flex-grow', 'flex-shrink', 'flex-basis', 'gap', 'row-gap',
  'column-gap', 'width', 'height', 'min-width', 'min-height', 'max-width',
  'max-height', 'padding', 'padding-top', 'padding-right', 'padding-bottom',
  'padding-left', 'margin', 'margin-top', 'margin-right', 'margin-bottom',
  'margin-left', 'border-width', 'font-size', 'line-height', 'white-space',
  'overflow', 'position',
]);

const INHERITED_PROPS = new Set([
  'color', 'fontSize', 'fontWeight', 'lineHeight', 'textAlign', 'whiteSpace',
  'letterSpacing',
]);

// The initial style. Frozen — see bug #1 in docs/architecture.md: padding
// was once shared by reference and a single padding-top declaration leaked
// into every element compiled after it. Object.freeze makes that class of
// bug throw in strict mode instead of corrupting the build.
export const INITIAL_STYLE = Object.freeze({
  display: 'flex',
  // No meaningful initial value: a container whose direction is
  // observable must state it (box.js enforces). This is what the
  // solver falls back to for the cases where direction cannot change
  // the result — a single child, or none.
  flexDirection: 'column',
  flexDirectionDeclared: false,
  flexWrap: 'nowrap',
  justifyContent: 'flex-start',
  alignItems: 'stretch',
  alignSelf: 'auto',
  flexGrow: 0,
  flexShrink: 1,
  flexBasis: { unit: 'auto', value: 0 },
  rowGap: 0,
  columnGap: 0,
  width: { unit: 'auto', value: 0 },
  height: { unit: 'auto', value: 0 },
  minWidth: null,
  minHeight: null,
  maxWidth: null,
  maxHeight: null,
  padding: Object.freeze([0, 0, 0, 0]),
  margin: Object.freeze([0, 0, 0, 0]),
  borderWidth: 0,
  borderColor: null,
  borderRadius: 0,
  background: null,
  color: Object.freeze([255, 255, 255, 255]),
  fontSize: 16,
  fontWeight: 400,
  lineHeight: { unit: 'number', value: 1.25 },
  textAlign: 'left',
  whiteSpace: 'normal',
  textOverflow: 'clip',
  letterSpacing: 0,
  overflow: 'visible',
  opacity: 1,
});

/** Deep-ish clone: arrays and plain objects copied, so no element ever
 * mutates a value shared with INITIAL_STYLE or a sibling. */
export function cloneStyle(style) {
  const out = {};
  for (const [k, v] of Object.entries(style)) {
    if (Array.isArray(v)) out[k] = v.slice();
    else if (v && typeof v === 'object') out[k] = { ...v };
    else out[k] = v;
  }
  return out;
}

// ---------------------------------------------------------------- selectors

function parseCompound(src) {
  // e.g. "div.tile#first:focus"
  const compound = { tag: null, id: null, classes: [], focus: false };
  const re = /([a-zA-Z][a-zA-Z0-9-]*|\*)|\.([a-zA-Z_-][a-zA-Z0-9_-]*)|#([a-zA-Z_-][a-zA-Z0-9_-]*)|:(focus)|(.)/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    if (m[1]) compound.tag = m[1] === '*' ? null : m[1].toLowerCase();
    else if (m[2]) compound.classes.push(m[2]);
    else if (m[3]) compound.id = m[3];
    else if (m[4]) compound.focus = true;
    else throw new Error(`css: unsupported selector syntax near "${m[5]}" in "${src}"`);
  }
  return compound;
}

export function parseSelector(src) {
  const parts = src.trim().split(/\s+/).map(parseCompound);
  let a = 0, b = 0, c = 0;
  for (const p of parts) {
    if (p.id) a++;
    b += p.classes.length + (p.focus ? 1 : 0);
    if (p.tag) c++;
  }
  // :focus may sit on any compound: ".tile:focus .title" styles a
  // descendant of the focused scope. Either way the rule lands in the
  // focus pass of whatever element the full selector matches.
  const focus = parts.some((p) => p.focus);
  return { parts, focus, specificity: [a, b, c], source: src.trim() };
}

function compoundMatches(compound, el) {
  if (el.type !== 'element') return false;
  if (compound.tag && compound.tag !== el.tag) return false;
  if (compound.id && compound.id !== el.id) return false;
  // A compound carrying :focus can only match a focus scope root, i.e.
  // an element with the focusable attribute — at build time "may be
  // focused" is a static property of the element.
  if (compound.focus && !('focusable' in el.attrs)) return false;
  const cls = el.classes;
  for (const c of compound.classes) if (!cls.includes(c)) return false;
  return true;
}

/** Match ignoring :focus (focus is a paint state, not a tree state). */
export function selectorMatches(sel, el) {
  const parts = sel.parts;
  if (!compoundMatches(parts[parts.length - 1], el)) return false;
  let pi = parts.length - 2;
  let node = el.parent;
  while (pi >= 0 && node) {
    if (compoundMatches(parts[pi], node)) pi--;
    node = node.parent;
  }
  return pi < 0;
}

export function compareSpecificity(x, y) {
  for (let i = 0; i < 3; i++) {
    if (x[i] !== y[i]) return x[i] - y[i];
  }
  return 0;
}

// ------------------------------------------------------------ stylesheet

class SheetReader {
  constructor(src) { this.src = src; this.pos = 0; this.line = 1; }
  eof() { return this.pos >= this.src.length; }
  peek() { return this.src[this.pos]; }
  advance(n = 1) {
    for (let i = 0; i < n && !this.eof(); i++) {
      if (this.src[this.pos] === '\n') this.line++;
      this.pos++;
    }
  }
  skipWsAndComments() {
    for (;;) {
      while (!this.eof() && /\s/.test(this.peek())) this.advance();
      if (this.src.startsWith('/*', this.pos)) {
        const end = this.src.indexOf('*/', this.pos + 2);
        if (end === -1) throw new Error(`css: line ${this.line}: unterminated comment`);
        this.advance(end + 2 - this.pos);
      } else return;
    }
  }
  readUntil(chars) {
    let out = '';
    while (!this.eof() && !chars.includes(this.peek())) {
      if (this.src.startsWith('/*', this.pos)) {
        const end = this.src.indexOf('*/', this.pos + 2);
        if (end === -1) throw new Error(`css: line ${this.line}: unterminated comment`);
        this.advance(end + 2 - this.pos);
        continue;
      }
      out += this.peek();
      this.advance();
    }
    return out;
  }
}

/**
 * Parse a stylesheet into a list of rules:
 *   { selector, declarations: [{prop, value, line}], line }
 * Each comma-separated selector becomes its own rule sharing declarations.
 */
export function parseStylesheet(src) {
  const r = new SheetReader(src);
  const rules = [];
  const warnings = [];
  for (;;) {
    r.skipWsAndComments();
    if (r.eof()) break;
    if (r.peek() === '@') {
      // No at-rules: no media queries on a fixed 640x448 target, no
      // imports in a build with explicit inputs. Skip the block, warn.
      const line = r.line;
      const head = r.readUntil('{;');
      if (r.peek() === ';') { r.advance(); warnings.push(`css: line ${line}: at-rule "${head.trim()}" ignored`); continue; }
      let depth = 0;
      do {
        if (r.peek() === '{') depth++;
        if (r.peek() === '}') depth--;
        r.advance();
      } while (!r.eof() && depth > 0);
      warnings.push(`css: line ${line}: at-rule "${head.trim().split(/\s/)[0]}" ignored`);
      continue;
    }
    const line = r.line;
    const selText = r.readUntil('{');
    if (r.eof()) throw new Error(`css: line ${line}: selector without a block`);
    r.advance(); // {
    const body = r.readUntil('}');
    if (r.eof()) throw new Error(`css: line ${line}: unterminated block`);
    r.advance(); // }
    const declarations = [];
    for (const decl of body.split(';')) {
      const d = decl.trim();
      if (!d) continue;
      const colon = d.indexOf(':');
      if (colon === -1) throw new Error(`css: line ${line}: malformed declaration "${d}"`);
      declarations.push({
        prop: d.slice(0, colon).trim().toLowerCase(),
        value: d.slice(colon + 1).trim(),
        line,
      });
    }
    for (const one of selText.split(',')) {
      if (!one.trim()) continue;
      rules.push({ selector: parseSelector(one), declarations, line });
    }
  }
  return { rules, warnings };
}

// ------------------------------------------------------------- declarations

function lengthOrThrow(value, prop, line) {
  const l = parseLength(value);
  if (!l) throw new Error(`css: line ${line}: ${prop}: "${value}" is not a length`);
  return l;
}

function pxOrThrow(value, prop, line) {
  const l = lengthOrThrow(value, prop, line);
  if (l.unit === 'number' && l.value !== 0) {
    throw new Error(`css: line ${line}: ${prop}: unitless "${value}" — write "${value}px"`);
  }
  if (l.unit !== 'px' && !(l.unit === 'number' && l.value === 0)) {
    throw new Error(`css: line ${line}: ${prop}: only px supported, got "${value}"`);
  }
  return l.value;
}

const SIDE_INDEX = { top: 0, right: 1, bottom: 2, left: 3 };

/**
 * Apply one declaration to a computed-style object (mutates).
 * Returns true when the property was understood.
 */
export function applyDeclaration(style, prop, value, line, warnings) {
  const px = () => pxOrThrow(value, prop, line);
  switch (prop) {
    case 'display':
      if (value !== 'flex' && value !== 'none') {
        throw new Error(`css: line ${line}: display: only "flex" and "none" exist on this target (got "${value}")`);
      }
      style.display = value; return true;
    case 'flex-direction':
      style.flexDirection = value;
      // Recorded, not inferred from the value: a container that says
      // `column` and one that merely defaults to it produce identical
      // styles, and only one of them is something the author decided.
      // box.js refuses the second when the choice is observable.
      style.flexDirectionDeclared = true;
      return true;
    case 'flex-wrap':
      style.flexWrap = value; return true;
    case 'justify-content':
      style.justifyContent = value; return true;
    case 'align-items':
      style.alignItems = value; return true;
    case 'align-self':
      style.alignSelf = value; return true;
    case 'flex-grow':
      style.flexGrow = parseFloat(value); return true;
    case 'flex-shrink':
      style.flexShrink = parseFloat(value); return true;
    case 'flex-basis':
      style.flexBasis = lengthOrThrow(value, prop, line); return true;
    case 'flex': {
      // flex: <grow> [<shrink>] [<basis>] — the common shorthands.
      const parts = splitSpaces(value);
      if (value === 'none') { style.flexGrow = 0; style.flexShrink = 0; style.flexBasis = { unit: 'auto', value: 0 }; return true; }
      style.flexGrow = parseFloat(parts[0]);
      style.flexShrink = parts.length > 1 && !parts[1].match(/px|%|auto/) ? parseFloat(parts[1]) : 1;
      const basisTok = parts.find((p, i) => i > 0 && /px|%|auto/.test(p));
      style.flexBasis = basisTok ? lengthOrThrow(basisTok, prop, line) : { unit: 'px', value: 0 };
      return true;
    }
    case 'gap': {
      const parts = splitSpaces(value).map((v) => pxOrThrow(v, prop, line));
      style.rowGap = parts[0];
      style.columnGap = parts.length > 1 ? parts[1] : parts[0];
      return true;
    }
    case 'row-gap': style.rowGap = px(); return true;
    case 'column-gap': style.columnGap = px(); return true;
    case 'width': style.width = lengthOrThrow(value, prop, line); return true;
    case 'height': style.height = lengthOrThrow(value, prop, line); return true;
    case 'min-width': style.minWidth = lengthOrThrow(value, prop, line); return true;
    case 'min-height': style.minHeight = lengthOrThrow(value, prop, line); return true;
    case 'max-width': style.maxWidth = lengthOrThrow(value, prop, line); return true;
    case 'max-height': style.maxHeight = lengthOrThrow(value, prop, line); return true;
    case 'padding': {
      const parts = expandBox(splitSpaces(value).map((v) => pxOrThrow(v, prop, line)));
      if (!parts) throw new Error(`css: line ${line}: padding: 1-4 values`);
      style.padding = parts; return true;
    }
    case 'padding-top': case 'padding-right': case 'padding-bottom': case 'padding-left': {
      // Clone before writing — the style may still hold the frozen
      // INITIAL_STYLE array (regression: bug #1).
      style.padding = style.padding.slice();
      style.padding[SIDE_INDEX[prop.slice(8)]] = px();
      return true;
    }
    case 'margin': {
      const parts = expandBox(splitSpaces(value).map((v) => pxOrThrow(v, prop, line)));
      if (!parts) throw new Error(`css: line ${line}: margin: 1-4 values`);
      style.margin = parts; return true;
    }
    case 'margin-top': case 'margin-right': case 'margin-bottom': case 'margin-left': {
      style.margin = style.margin.slice();
      style.margin[SIDE_INDEX[prop.slice(7)]] = px();
      return true;
    }
    case 'border': {
      // border: <width> solid <color>
      const parts = splitSpaces(value);
      for (const p of parts) {
        const len = parseLength(p);
        if (len && len.unit === 'px') { style.borderWidth = len.value; continue; }
        if (p === 'solid' || p === 'none') continue;
        const col = parseColor(p);
        if (col) { style.borderColor = col; continue; }
        throw new Error(`css: line ${line}: border: unsupported token "${p}" (only solid borders exist)`);
      }
      return true;
    }
    case 'border-width': style.borderWidth = px(); return true;
    case 'border-color': {
      const col = parseColor(value);
      if (!col) throw new Error(`css: line ${line}: border-color: bad color "${value}"`);
      style.borderColor = col; return true;
    }
    case 'border-radius': style.borderRadius = px(); return true;
    case 'background': case 'background-color': {
      if (value === 'none' || value === 'transparent') { style.background = null; return true; }
      const col = parseColor(value);
      if (!col) throw new Error(`css: line ${line}: ${prop}: bad color "${value}" (flat colors only — gradients are a texture you bake yourself)`);
      style.background = col; return true;
    }
    case 'color': {
      const col = parseColor(value);
      if (!col) throw new Error(`css: line ${line}: color: bad color "${value}"`);
      style.color = col; return true;
    }
    case 'font-size': style.fontSize = px(); return true;
    case 'font-weight':
      style.fontWeight = value === 'bold' ? 700 : value === 'normal' ? 400 : parseInt(value, 10);
      return true;
    case 'line-height': {
      // Bug #2 regression: "line-height: 1.3" is a multiplier, never 1.3px.
      const l = lengthOrThrow(value, prop, line);
      if (l.unit === '%') { style.lineHeight = { unit: 'number', value: l.value / 100 }; return true; }
      style.lineHeight = l; return true;
    }
    case 'text-align': style.textAlign = value; return true;
    case 'white-space': style.whiteSpace = value; return true;
    case 'text-overflow': style.textOverflow = value; return true;
    case 'letter-spacing': style.letterSpacing = px(); return true;
    case 'overflow':
      if (value !== 'visible' && value !== 'hidden') {
        throw new Error(`css: line ${line}: overflow: only visible|hidden (there is no scrolling on a memory card browser)`);
      }
      style.overflow = value; return true;
    case 'opacity': {
      const v = parseFloat(value);
      if (Number.isNaN(v)) throw new Error(`css: line ${line}: opacity: bad value`);
      style.opacity = Math.min(Math.max(v, 0), 1);
      return true;
    }
    default:
      warnings.push(`css: line ${line}: property "${prop}" not supported on this target; ignored`);
      return false;
  }
}

/**
 * Compute base and :focus styles for an element.
 *
 * Returns { style, focusStyle, focusDeclared }. focusStyle === style
 * (same reference) when no :focus rule matches. When one does, the two
 * are computed independently and a geometry-property difference is a
 * compile error (see docs/architecture.md, ":focus is a paint-only delta").
 */
export function computeStyle(el, sheet, parentStyle, parentFocusInherit, warnings) {
  const matched = [];
  for (let i = 0; i < sheet.rules.length; i++) {
    const rule = sheet.rules[i];
    if (selectorMatches(rule.selector, el)) matched.push({ rule, index: i });
  }
  matched.sort((a, b) => {
    const c = compareSpecificity(a.rule.selector.specificity, b.rule.selector.specificity);
    return c !== 0 ? c : a.index - b.index;
  });

  const makeBase = (inheritFrom) => {
    const s = cloneStyle(INITIAL_STYLE);
    if (inheritFrom) {
      for (const p of INHERITED_PROPS) {
        const v = inheritFrom[p];
        s[p] = Array.isArray(v) ? v.slice() : (v && typeof v === 'object' ? { ...v } : v);
      }
    }
    return s;
  };

  const style = makeBase(parentStyle);
  const focusDeclProps = [];
  for (const { rule } of matched) {
    if (rule.selector.focus) {
      for (const d of rule.declarations) focusDeclProps.push(d);
      continue;
    }
    for (const d of rule.declarations) applyDeclaration(style, d.prop, d.value, d.line, warnings);
  }

  const focusDeclared = focusDeclProps.length > 0;
  if (!focusDeclared && !parentFocusInherit) {
    return { style, focusStyle: style, focusDeclared: false };
  }

  // Focus pass: inherit from the parent's *focus* style (a focused tile
  // may change color; its text children must see the focused color), then
  // replay base declarations, then the :focus declarations on top.
  const focusStyle = makeBase(parentFocusInherit ?? parentStyle);
  for (const { rule } of matched) {
    if (rule.selector.focus) continue;
    for (const d of rule.declarations) applyDeclaration(focusStyle, d.prop, d.value, d.line, warnings);
  }
  for (const d of focusDeclProps) {
    if (GEOMETRY_PROPS.has(d.prop)) {
      throw new Error(
        `css: line ${d.line}: :focus may not change "${d.prop}" — focus is a paint-only delta. `
        + 'Both states share one baked layout; move the geometry to the base rule.',
      );
    }
    applyDeclaration(focusStyle, d.prop, d.value, d.line, warnings);
  }
  return { style, focusStyle, focusDeclared };
}
