// Box tree construction.
//
// The element tree plus computed styles becomes a tree of boxes the flex
// solver understands. Text nodes become *anonymous boxes*: they carry
// their parent's inherited text properties (font, size, color) but NOT
// its decoration. Bug #4 was exactly this — an anonymous box inheriting
// `background` and `border` repainted its parent's chrome on top of
// itself, doubling every panel's border.

import { resolve, isAbsolute } from 'node:path';

import { computeStyle, cloneStyle, INITIAL_STYLE } from './css.js';
import { readPngSize } from './image.js';

let nextBoxId = 1;

export function resetBoxIds() { nextBoxId = 1; }

export class Box {
  constructor(kind, el, style, focusStyle) {
    this.id = nextBoxId++;
    this.kind = kind;           // 'element' | 'text'
    this.el = el;               // source Element (or parent element for text)
    this.style = style;
    this.focusStyle = focusStyle; // === style when no focus delta applies
    this.children = [];
    this.parent = null;
    this.text = null;           // for text boxes
    this.image = null;          // for <img>: { src, w, h } (intrinsic px)
    this.slot = null;           // for data-slot: { name, capacity }
    this.keep = false;          // data-keep: exempt from the dead-geometry trim
    this.nocontrast = false;    // data-nocontrast: exempt from the contrast lint
    // Filled by the solver:
    this.x = 0; this.y = 0; this.width = 0; this.height = 0;
    this.lines = null;          // laid-out text lines
    // Focus:
    this.focusable = false;
    this.focusId = null;        // set on the focus scope root and descendants
  }

  isText() { return this.kind === 'text'; }
}

function anonymousTextStyle(parentStyle) {
  // Inherit text properties only. Everything decorative resets to the
  // initial value — an anonymous box has no chrome of its own.
  const s = cloneStyle(INITIAL_STYLE);
  s.color = parentStyle.color.slice();
  // With the colour, not without it. An anonymous box inheriting the
  // resolved rgba alone would be value-keyed under a role-keyed parent,
  // and a theme would recolour the parent's text and not this run of it.
  s.colorVar = parentStyle.colorVar;
  // And the per-theme vector with the name. This list is hand-written
  // and was one entry short the first time paint.js's guard ran against
  // it: colorVar was here, colorThemes was not, so the text kept its
  // role and lost every theme's value for it. Silent without the guard
  // -- the default theme is still right, so nothing rendered wrong.
  s.colorThemes = parentStyle.colorThemes
    ? parentStyle.colorThemes.map((c) => c.slice())
    : null;
  s.fontSize = parentStyle.fontSize;
  s.fontWeight = parentStyle.fontWeight;
  s.lineHeight = { ...parentStyle.lineHeight };
  s.textAlign = parentStyle.textAlign;
  s.whiteSpace = parentStyle.whiteSpace;
  s.textOverflow = parentStyle.textOverflow;
  s.letterSpacing = parentStyle.letterSpacing;
  s.background = null;
  s.backgroundVar = null;
  s.backgroundThemes = null;
  s.borderWidth = 0;
  s.borderColor = null;
  s.borderColorVar = null;
  s.borderColorThemes = null;
  return s;
}

/**
 * Build the box tree for an element.
 *
 * focusScope: the focusId currently in effect (null outside any focusable
 * subtree). An element with the `focusable` attribute opens a scope; every
 * box inside carries that focusId so the baker can tag paint deltas.
 */
export function buildBoxTree(el, sheet, parentStyle, parentFocusStyle, warnings, focusScope = null, env = {}) {
  const { style, focusStyle, focusDeclared } = computeStyle(
    el, sheet, parentStyle,
    // Inside a focus scope, children inherit from the parent's focus style
    // so e.g. a focused tile's color reaches its text.
    focusScope !== null && parentFocusStyle !== parentStyle ? parentFocusStyle : null,
    warnings,
  );
  if (style.display === 'none') return null;

  const box = new Box('element', el, style, focusStyle);
  // data-keep: exempt this element's geometry from the baker's
  // dead-geometry trim. The one case that wants it is deliberate
  // observability -- the bring-up probe needs a quad that provably
  // cannot draw, so that a television showing it means the scissor is
  // not being applied.
  box.keep = 'data-keep' in el.attrs;

  // data-nocontrast: exempt this element's text from the contrast lint.
  //
  // Same shape of exemption as data-keep, for the same reason. The trim
  // deletes geometry that cannot draw, and data-keep exists for the one
  // case where a quad that cannot draw IS the instrument. The contrast
  // rule warns about text a viewer cannot read, and this exists for the
  // one case where text a viewer cannot read is the instrument: bring-up
  // steps 4 and 5 paint glyphs the exact colour of the block behind them,
  // so that a correct console renders nothing and "can you see letters
  // here" replaces a judgement of shade that no photograph can support.
  //
  // Deliberately scoped to the contrast rule alone rather than a blanket
  // data-nolint. A general escape hatch gets reached for; a rule-specific
  // one has to be argued for each time.
  box.nocontrast = 'data-nocontrast' in el.attrs;
  if ('data-slot' in el.attrs) {
    // Dynamic text (backlog F2): the element's text is a build-time
    // placeholder; the console composes the real string at runtime
    // from a baked glyph table. Geometry, font, colors and alignment
    // are still all compile-time.
    const name = el.attrs['data-slot'];
    if (!name) {
      throw new Error(`layout: <${el.tag}> line ${el.line}: data-slot needs a name`);
    }
    const onlyText = el.children.length === 1 && el.children[0].type === 'text';
    if (!onlyText) {
      throw new Error(
        `layout: <${el.tag}> line ${el.line}: a data-slot element must contain `
        + 'exactly one text node (the placeholder), no child elements',
      );
    }
    box.slot = {
      name,
      capacity: parseInt(el.attrs['data-slot-capacity'] ?? '63', 10),
    };
  }
  if (el.tag === 'img') {
    // A streamed slot: the app supplies the texels at runtime, so
    // there is no file to read and nothing to bake. The blob carries
    // geometry, a name and a reservation (uib format v6).
    const texSlot = el.attrs['data-tex-slot'];
    if (texSlot !== undefined) {
      // Trimmed, not truthy. `""` was already caught; `"cover "` was
      // not, and it bakes cleanly — then ps2ui_tex_set(ctx, gs,
      // "cover", …) returns ERR_NOT_STREAMED, the same code as a name
      // that does not exist at all, with nothing anywhere to suggest
      // the blob holds a near-identical string. The runtime compares
      // these bytes with strcmp, so a difference the author cannot see
      // in their own markup has to fail here or not at all. Refused
      // rather than trimmed: guessing which name was meant is the kind
      // of ambiguity every other check on this element rejects.
      if (texSlot.trim() !== texSlot || !texSlot) {
        throw new Error(
          `layout: <img> on line ${el.line}: data-tex-slot needs a name `
          + 'with no leading or trailing whitespace — it is how the app '
          + 'addresses the slot at runtime, matched byte for byte, and '
          + `${JSON.stringify(texSlot)} would not match what it reads here`,
        );
      }
      if (el.attrs.src) {
        throw new Error(
          `layout: <img> on line ${el.line}: data-tex-slot="${texSlot}" and `
          + 'src are mutually exclusive — a slot is either baked from a file '
          + 'or filled at runtime, and carrying both would leave it ambiguous '
          + 'which one the console draws',
        );
      }
      if ('palettize' in el.attrs) {
        throw new Error(
          `layout: <img> on line ${el.line}: palettize is not supported on a `
          + 'streamed slot — quantizing needs the art, which does not exist '
          + 'until runtime. Supply PSMCT32 texels to ps2ui_tex_set',
        );
      }
      box.image = { streamed: true, name: texSlot, w: null, h: null,
                    palettize: false };
      box.streamedTex = texSlot;
    } else {
    const src = el.attrs.src;
    if (!src) {
      throw new Error(
        `layout: <img> on line ${el.line} has no src attribute `
        + '(or data-tex-slot, for a slot the app fills at runtime)',
      );
    }
    let resolved;
    if (isAbsolute(src)) {
      resolved = src;
    } else if (env.assetDir) {
      // The convention: assets live next to the HTML that names them
      // (ui/assets/*.png), resolved relative to the document.
      resolved = resolve(env.assetDir, src);
    } else {
      throw new Error(
        `layout: <img src="${src}"> on line ${el.line}: relative path but no `
        + 'asset base — compile from files (compileFiles) or pass options.assetDir',
      );
    }
    const size = readPngSize(resolved);
    // palettize: opt-in PSMT8+CLUT quantization at bake time — 8 bits
    // per texel instead of 32, for art that fits in 256 colors.
    box.image = {
      src: resolved, w: size.w, h: size.h,
      palettize: 'palettize' in el.attrs,
    };
    }
  }
  const focusable = 'focusable' in el.attrs;
  if (focusable && focusScope !== null) {
    throw new Error(
      `layout: <${el.tag}> line ${el.line}: nested focusable inside another focusable — `
      + 'the D-pad model has one focus ring; flatten the hierarchy.',
    );
  }
  const scope = focusable ? box.id : focusScope;
  box.focusable = focusable;
  box.focusId = scope;
  if (focusDeclared && scope === null) {
    warnings.push(
      `css: :focus styles matched <${el.tag}> line ${el.line} but no enclosing element `
      + 'has the focusable attribute; the delta can never show',
    );
  }

  for (const child of el.children) {
    if (child.type === 'text') {
      const tbox = new Box('text', el, anonymousTextStyle(style), null);
      // The lines live on this anonymous child, not on the element box,
      // so the exemption has to come down with them or it never reaches
      // the command that carries the colour. data-keep needs no such
      // hop: rects are emitted from the element box itself.
      tbox.nocontrast = box.nocontrast;
      // Text inside a focus scope needs the focus-state text style too.
      tbox.focusStyle = focusStyle !== style ? anonymousTextStyle(focusStyle) : tbox.style;
      tbox.text = child.text;
      tbox.focusId = scope;
      tbox.parent = box;
      box.children.push(tbox);
    } else {
      const cbox = buildBoxTree(child, sheet, style, focusStyle, warnings, scope, env);
      if (cbox) {
        cbox.parent = box;
        box.children.push(cbox);
      }
    }
  }

  // A container laying out two or more children must say which way.
  //
  // There is no good default here. CSS's initial value is `row`; this
  // compiler shipped `column`, undocumented, so every author who knew
  // CSS got the opposite of what they wrote — and the two shipped
  // examples had already worked around it, stating `row` twenty times
  // against `column` four. Picking either default silently teaches
  // one group of authors the wrong model. So neither: state it, and
  // the question cannot come back.
  //
  // Only when the choice is observable. One child, or none, lays out
  // identically either way, so a leaf, a text box, or a single-child
  // wrapper is never asked.
  if (box.children.length >= 2 && !style.flexDirectionDeclared) {
    // Collected, not thrown. Migrating a document written against the
    // old implicit default trips this once per container, and throwing
    // on the first turns that into one edit-compile cycle each. The
    // caller reports them together.
    (env.undirected ??= []).push({
      line: el.line,
      text: `  <${el.tag}> line ${el.line} (${box.children.length} children)`,
    });
  }
  return box;
}

/** Depth-first traversal of the box tree. */
export function walkBoxes(box, fn) {
  fn(box);
  for (const c of box.children) walkBoxes(c, fn);
}
