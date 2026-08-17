// Display-list generation.
//
// Walks the placed box tree in paint order (parents before children,
// document order between siblings — no z-index on this target) and emits
// a flat command list. Every command carries:
//
//   state:   'always' | 'unfocused' | 'focused'
//   focusId: the focus scope it belongs to (null outside scopes)
//
// Both focus states of the whole screen live in this one list; the
// runtime filters by (state, focusId) per frame. When the base and focus
// paints of a box are identical the command is emitted once as 'always',
// so the common case costs nothing extra.

import { walkBoxes } from './box.js';

function paintOfBox(box, style) {
  // The paint-relevant attributes of an element box under a given style,
  // normalized so invisible differences (a border-color with zero width,
  // a fully transparent fill) can never split an 'always' command into a
  // focused/unfocused pair.
  const alpha = (c) => (c ? [c[0], c[1], c[2], Math.round(c[3] * style.opacity)] : null);
  const fill = alpha(style.background);
  let borderColor = style.borderWidth > 0 ? alpha(style.borderColor) : null;
  if (borderColor && borderColor[3] === 0) borderColor = null;
  return {
    fill: fill && fill[3] > 0 ? fill : null,
    borderWidth: borderColor ? style.borderWidth : 0,
    borderColor,
    radius: style.borderRadius,
  };
}

function textPaint(style) {
  return {
    color: [
      style.color[0], style.color[1], style.color[2],
      Math.round(style.color[3] * style.opacity),
    ],
    fontWeight: style.fontWeight,
  };
}

function samePaint(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function emitRect(cmds, box, paint, state) {
  if (!paint.fill && !(paint.borderWidth > 0 && paint.borderColor)) return;
  cmds.push({
    op: 'rect',
    x: box.x, y: box.y, w: box.width, h: box.height,
    fill: paint.fill,
    borderWidth: paint.borderWidth > 0 && paint.borderColor ? paint.borderWidth : 0,
    borderColor: paint.borderWidth > 0 ? paint.borderColor : null,
    radius: Math.min(paint.radius, Math.floor(Math.min(box.width, box.height) / 2)),
    state,
    focusId: box.focusId,
  });
}

function emitTextLines(cmds, box, paint, state) {
  const s = box.style;
  for (const line of box.lines) {
    if (line.text === '') continue;
    cmds.push({
      op: 'text',
      x: line.x,
      // Half-leading: the glyph box sits centered in the line box.
      y: line.y + Math.floor(line.leading / 2),
      text: line.text,
      size: s.fontSize,
      weight: paint.fontWeight,
      letterSpacing: s.letterSpacing,
      color: paint.color,
      state,
      focusId: box.focusId,
    });
  }
}

/**
 * Build the display list for a placed box tree.
 * Returns { commands, focusables } where focusables maps focusId to the
 * scope root box (used by the focus solver).
 */
export function buildDisplayList(root) {
  const commands = [];
  const focusables = new Map();
  const slots = [];

  const visit = (box) => {
    const inScope = box.focusId !== null && box.focusStyle !== box.style;

    if (box.parent?.slot && box.isText()) {
      // Placeholder text of a data-slot: becomes a slot descriptor, not
      // static text commands. One line, enforced here.
      if (box.lines.length !== 1) {
        throw new Error(
          `layout: data-slot "${box.parent.slot.name}" placeholder wraps to `
          + `${box.lines.length} lines — slots are single-line; add white-space: `
          + 'nowrap or widen the box',
        );
      }
      const line = box.lines[0];
      const parent = box.parent;
      const pb = parent.style.borderWidth;
      const base = textPaint(box.style);
      const foc = textPaint(box.focusStyle);
      slots.push({
        name: parent.slot.name,
        placeholder: line.text,
        x: parent.x + parent.style.padding[3] + pb,
        textY: line.y + Math.floor(line.leading / 2),
        w: parent.width - parent.style.padding[1] - parent.style.padding[3] - 2 * pb,
        size: box.style.fontSize,
        weight: base.fontWeight,
        lineHeight: line.lineHeight,
        align: box.style.textAlign,
        ellipsis: box.style.textOverflow === 'ellipsis',
        capacity: parent.slot.capacity,
        focusId: box.focusId,
        colorBase: base.color,
        colorFocus: foc.color,
      });
      return; // no static commands for slot text
    }

    if (box.isText()) {
      const base = textPaint(box.style);
      if (inScope) {
        const foc = textPaint(box.focusStyle);
        if (samePaint(base, foc)) emitTextLines(commands, box, base, 'always');
        else {
          emitTextLines(commands, box, base, 'unfocused');
          emitTextLines(commands, box, foc, 'focused');
        }
      } else {
        emitTextLines(commands, box, base, 'always');
      }
    } else {
      if (box.focusable) focusables.set(box.id, box);
      const base = paintOfBox(box, box.style);
      if (inScope) {
        const foc = paintOfBox(box, box.focusStyle);
        if (samePaint(base, foc)) emitRect(commands, box, base, 'always');
        else {
          emitRect(commands, box, base, 'unfocused');
          emitRect(commands, box, foc, 'focused');
        }
      } else {
        emitRect(commands, box, base, 'always');
      }
    }

    if (box.image) {
      // The image fills the content box; chrome (background/border)
      // was already emitted above. No focus variant: image pixels are
      // identical in both states, so 'always' keeps the state filter
      // free for the chrome around it.
      const b = box.style.borderWidth;
      commands.push({
        op: 'image',
        x: box.x + box.style.padding[3] + b,
        y: box.y + box.style.padding[0] + b,
        w: box.width - box.style.padding[1] - box.style.padding[3] - 2 * b,
        h: box.height - box.style.padding[0] - box.style.padding[2] - 2 * b,
        src: box.image.src,
        palettize: box.image.palettize,
        state: 'always',
        focusId: box.focusId,
      });
    }

    const clip = !box.isText() && box.style.overflow === 'hidden';
    if (clip) {
      commands.push({
        op: 'scissor_push',
        x: box.x, y: box.y, w: box.width, h: box.height,
        state: 'always', focusId: null,
      });
    }
    for (const c of box.children) visit(c);
    if (clip) {
      commands.push({ op: 'scissor_pop', state: 'always', focusId: null });
    }
  };
  visit(root);
  const seen = new Set();
  for (const s of slots) {
    if (seen.has(s.name)) {
      throw new Error(`layout: duplicate data-slot name "${s.name}"`);
    }
    seen.add(s.name);
  }
  return { commands, focusables, slots };
}
