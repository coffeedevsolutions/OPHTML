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

// THE FOLD RUNS OVER THE WHOLE VECTOR, WHICH IS THE POINT.
//
// `opacity` multiplies into a colour's alpha, and the colour that
// reaches the baker is the folded one, not the declaration. So a role
// is not a function of its name: var(--panel) at two opacities is two
// painted colours and two tint entries, both of which a theme has to
// move (see the comment on _tint in uib.py, and #77).
//
// The way that stays true is to never compute a theme's colour from
// another theme's. Every theme's value goes through this same line,
// so a fold that reaches one reaches all of them, and a fold added
// later cannot be added to only the default row -- there is no code
// path here that names a row.
function foldAlpha(vec, opacity) {
  if (!vec) return null;
  return vec.map((c) => [c[0], c[1], c[2], Math.round(c[3] * opacity)]);
}

// A NAME WITHOUT A VECTOR IS THE FAILURE THIS GUARDS. The vectors are
// set in five places in css.js and inherited through a list in a sixth,
// and "one of those was missed" is the shape of every colour-seam bug
// this project has had. Missing one would otherwise be silent: the base
// colour is still right, so every screenshot, every unit test and the
// previewer all agree, and only the second theme row is wrong.
function vectorOf(themes, rgba, varName, nThemes, what) {
  if (themes) {
    if (themes.length !== nThemes) {
      throw new Error(`layout: internal: ${what} has ${themes.length} theme `
        + `values, expected ${nThemes}`);
    }
    return themes;
  }
  if (varName) {
    throw new Error(`layout: internal: ${what} carries the name ${varName} but `
      + `no per-theme values -- a themed colour resolved through a path that `
      + `did not carry the vector`);
  }
  // Never went through a declaration: `color`'s initial white is the
  // only colour that reaches here. Same value in every theme.
  return rgba ? Array.from({ length: nThemes }, () => rgba.slice()) : null;
}

function paintOfBox(box, style, nThemes) {
  // The paint-relevant attributes of an element box under a given style,
  // normalized so invisible differences (a border-color with zero width,
  // a fully transparent fill) can never split an 'always' command into a
  // focused/unfocused pair.
  //
  // NORMALIZATION READS THE DEFAULT THEME AND ONLY THE DEFAULT THEME.
  // Whether a command exists is structure, and a theme moves colour,
  // not structure -- a theme that could delete a command by taking a
  // fill to zero alpha would make the command list depend on the row
  // selected at runtime, which the format cannot express. So the live/
  // dead decision is theme 0's, and every row follows it.
  const fillVec = foldAlpha(
    vectorOf(style.backgroundThemes, style.background, style.backgroundVar,
             nThemes, 'background'),
    style.opacity);
  const fill = fillVec ? fillVec[0] : null;
  let borderVec = style.borderWidth > 0
    ? foldAlpha(vectorOf(style.borderColorThemes, style.borderColor,
                         style.borderColorVar, nThemes, 'border-color'),
                style.opacity)
    : null;
  if (borderVec && borderVec[0][3] === 0) borderVec = null;
  const borderColor = borderVec ? borderVec[0] : null;
  const live = fill && fill[3] > 0 ? fill : null;
  return {
    fill: live,
    fillThemes: live ? fillVec : null,
    // The var() name travels WITH the colour and is normalized the same
    // way: a fill that ends up invisible carries no name either, or two
    // boxes that differ only in the name of a colour neither of them
    // paints would split into a focused/unfocused pair for nothing.
    fillVar: live ? (style.backgroundVar ?? null) : null,
    borderWidth: borderColor ? style.borderWidth : 0,
    borderColor,
    borderColorThemes: borderVec,
    borderColorVar: borderColor ? (style.borderColorVar ?? null) : null,
    radius: style.borderRadius,
  };
}

function textPaint(style, nThemes) {
  const vec = foldAlpha(
    vectorOf(style.colorThemes, style.color, style.colorVar, nThemes, 'color'),
    style.opacity);
  return {
    color: vec[0],
    colorThemes: vec,
    colorVar: style.colorVar ?? null,
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
    fillVar: paint.fillVar,
    fillThemes: paint.fillThemes,
    borderWidth: paint.borderWidth > 0 && paint.borderColor ? paint.borderWidth : 0,
    borderColor: paint.borderWidth > 0 ? paint.borderColor : null,
    borderColorVar: paint.borderWidth > 0 ? paint.borderColorVar : null,
    borderColorThemes: paint.borderWidth > 0 ? paint.borderColorThemes : null,
    radius: Math.min(paint.radius, Math.floor(Math.min(box.width, box.height) / 2)),
    state,
    focusId: box.focusId,
    // Only emitted when set: an absent key means the same thing as
    // false to every consumer, and writing it on every command would
    // grow the IR for one attribute almost nobody uses.
    ...(box.keep ? { keep: true } : {}),
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
      colorVar: paint.colorVar,
      colorThemes: paint.colorThemes,
      state,
      focusId: box.focusId,
      ...(box.nocontrast ? { nocontrast: true } : {}),
    });
  }
}

/**
 * Build the display list for a placed box tree.
 * Returns { commands, focusables } where focusables maps focusId to the
 * scope root box (used by the focus solver).
 */
export function buildDisplayList(root, nThemes = 1) {
  const commands = [];
  const focusables = new Map();
  const slots = [];
  // SLOT TEXT, AS THE LINTER NEEDS TO SEE IT.
  //
  // A data-slot emits no static commands -- its glyphs are drawn on the
  // console from the slot table -- so it was invisible to lintDocument
  // entirely. Same colour, same background, same geometry as static
  // text, and the only difference was the attribute: contrast and
  // min-font-size simply never ran on it. opl-env is 127 slots, which
  // is every title, count and telemetry line in the environment.
  //
  // Spliced at the index the text WOULD have occupied, not appended,
  // because lintDocument accumulates backgrounds in paint order: a rect
  // drawn after this point is on top of the slot, not behind it, and
  // appending would let it into the contrast chain.
  //
  // Two commands per slot, base and focus. A slot has two colour
  // vectors and the focused one sits on a different background -- the
  // seam that has been the gap in #70, #72 and #74. One command here
  // would check the state nobody looks at while focused.
  const lintCommands = [];

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
      const base = textPaint(box.style, nThemes);
      const foc = textPaint(box.focusStyle, nThemes);
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
        // The pen that draws this text runs on the console, so every
        // input to the pen must travel with the slot. Leaving spacing
        // behind meant layout measured the box with it while the
        // runtime drew without it: 44px of divergence over 12 glyphs
        // at letter-spacing: 4px, and centering misplaced by half.
        letterSpacing: box.style.letterSpacing,
        ellipsis: box.style.textOverflow === 'ellipsis',
        capacity: parent.slot.capacity,
        focusId: box.focusId,
        colorBase: base.color,
        colorFocus: foc.color,
        // With their names. A slot is text, so this is `color` and its
        // colorVar -- the same pair the static text commands carry, and
        // for the same reason: a theme keyed on names in the command
        // list and on values in the slot table would recolour every
        // panel and leave every score, label and dialog line baked.
        colorBaseVar: base.colorVar ?? null,
        colorFocusVar: foc.colorVar ?? null,
        colorBaseThemes: base.colorThemes,
        colorFocusThemes: foc.colorThemes,
      });
      // The linter's view of what the console will draw here. Kept
      // out of the IR: it is not a paint command, and the baker must
      // never see one.
      const at = commands.length;
      const mk = (colour, themes, state) => ({
        op: 'text',
        x: parent.x + parent.style.padding[3] + pb,
        y: line.y + Math.floor(line.leading / 2),
        text: line.text,
        size: box.style.fontSize,
        weight: base.fontWeight,
        letterSpacing: box.style.letterSpacing,
        color: colour,
        colorThemes: themes,
        state,
        focusId: box.focusId,
        ...(box.nocontrast ? { nocontrast: true } : {}),
      });
      const same = JSON.stringify(base.color) === JSON.stringify(foc.color)
        && JSON.stringify(base.colorThemes) === JSON.stringify(foc.colorThemes);
      if (box.focusId === null || same) {
        lintCommands.push([at, mk(base.color, base.colorThemes, 'always')]);
      } else {
        lintCommands.push([at, mk(base.color, base.colorThemes, 'unfocused')]);
        lintCommands.push([at, mk(foc.color, foc.colorThemes, 'focused')]);
      }
      return; // no static commands for slot text
    }

    if (box.isText()) {
      const base = textPaint(box.style, nThemes);
      if (inScope) {
        const foc = textPaint(box.focusStyle, nThemes);
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
      const base = paintOfBox(box, box.style, nThemes);
      if (inScope) {
        const foc = paintOfBox(box, box.focusStyle, nThemes);
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
        ...(box.image.streamed
          ? { streamed: true, name: box.image.name }
          : { src: box.image.src, palettize: box.image.palettize }),
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
  // Merge the slot views into paint order. Built here rather than in
  // compile() so nothing has to reconstruct where a slot sat.
  const forLint = [];
  let li = 0;
  const pend = lintCommands.slice().sort((a, b) => a[0] - b[0]);
  for (let i = 0; i <= commands.length; i++) {
    while (li < pend.length && pend[li][0] === i) forLint.push(pend[li++][1]);
    if (i < commands.length) forLint.push(commands[i]);
  }
  return { commands, focusables, slots, forLint };
}
