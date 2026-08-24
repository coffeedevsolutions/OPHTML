// The flexbox solver.
//
// A deliberate subset of CSS Flexible Box Layout Level 1, hand-written
// because the layout package must have zero dependencies (see
// docs/architecture.md). Everything is border-box: width/height include
// padding and border, which matches how console UI is actually specced.
//
// Two kinds of pass run through computeFlexLines:
//
//   measure (place=false) — answer "how big would this box like to be?"
//     Children are sized by their content; auto cross sizes are NOT
//     stretched. Bug #3 lived here: measurement used to stretch children
//     as if they were being placed, so an auto-sized item reported its
//     stretched size and its siblings shrank to nonsense.
//
//   place (place=true) — final geometry. Flexible lengths resolve, lines
//     align, children recurse with definite sizes, positions are set.
//
// The solver works in floats and rounds once when writing final geometry.

import { resolveLength } from './values.js';
import { wrapText, ellipsize, resolveLineHeight } from './text.js';
import { roundHalfUp } from './values.js';

const ROW = 0;
const COL = 1;

function axisOf(style) {
  return style.flexDirection === 'row' || style.flexDirection === 'row-reverse' ? ROW : COL;
}
function isReverse(style) {
  return style.flexDirection.endsWith('-reverse');
}

// Axis helpers: main/cross accessors over a {w, h} pair.
function mainOf(axis, w, h) { return axis === ROW ? w : h; }
function crossOf(axis, w, h) { return axis === ROW ? h : w; }

function paddingBorder(style) {
  const b = style.borderWidth;
  return {
    top: style.padding[0] + b,
    right: style.padding[1] + b,
    bottom: style.padding[2] + b,
    left: style.padding[3] + b,
  };
}

function marginMain(axis, style) {
  return axis === ROW ? style.margin[3] + style.margin[1] : style.margin[0] + style.margin[2];
}
function marginCross(axis, style) {
  return axis === ROW ? style.margin[0] + style.margin[2] : style.margin[3] + style.margin[1];
}
function marginMainStart(axis, style) { return axis === ROW ? style.margin[3] : style.margin[0]; }
function marginCrossStart(axis, style) { return axis === ROW ? style.margin[0] : style.margin[3]; }

function clampSize(v, min, max) {
  if (max != null) v = Math.min(v, max);
  if (min != null) v = Math.max(v, min);
  return v;
}

/**
 * Measure a text box: wrap (or ellipsize) into availW, return size.
 * Text layout is the leaf of the sizing recursion.
 */
function measureText(box, availW, fonts) {
  const s = box.style;
  const font = fonts.resolve(s.fontWeight);
  const lineH = resolveLineHeight(s.lineHeight, s.fontSize);
  let lines;
  if (s.whiteSpace === 'nowrap') {
    const width = font.measure(box.text, s.fontSize, s.letterSpacing);
    lines = [{ text: box.text, width }];
  } else {
    const max = availW == null ? Infinity : Math.max(availW, 0);
    lines = wrapText(box.text, font, s.fontSize, max, s.letterSpacing);
  }
  const w = Math.max(...lines.map((l) => l.width), 0);
  return { w, h: lines.length * lineH, lines, lineH, font };
}

/**
 * The hypothetical main size of a child before flexing:
 * flex-basis > explicit main size > content size.
 * Content sizing is a measure-pass recursion (place=false).
 */
function childBaseSize(child, axis, innerMain, innerCross, ctx) {
  const s = child.style;
  const basis = s.flexBasis;
  if (basis.unit !== 'auto') {
    const v = resolveLength(basis, innerMain);
    if (v != null) return v;
  }
  const mainProp = axis === ROW ? s.width : s.height;
  if (mainProp.unit !== 'auto') {
    const v = resolveLength(mainProp, innerMain);
    if (v != null) return v;
  }
  // Content-based: measure with the container's inner sizes as available
  // space, but without stretching (place=false).
  const m = measureNode(child, axis === ROW ? innerMain : innerCross, axis === ROW ? innerCross : innerMain, ctx);
  return mainOf(axis, m.w, m.h);
}

/**
 * Measure pass: how big is `box` given available space (either may be null
 * = unconstrained)? Returns {w, h} border-box.
 */
export function measureNode(box, availW, availH, ctx) {
  const s = box.style;
  const pb = paddingBorder(s);

  if (box.isText()) {
    const innerAvailW = availW == null ? null : availW - pb.left - pb.right;
    const t = measureText(box, innerAvailW, ctx.fonts);
    return {
      w: clampSize(t.w + pb.left + pb.right, resolveLength(s.minWidth, availW), resolveLength(s.maxWidth, availW)),
      h: clampSize(t.h + pb.top + pb.bottom, resolveLength(s.minHeight, availH), resolveLength(s.maxHeight, availH)),
    };
  }

  if (box.image) {
    // Replaced element: CSS size wins; a single specified axis keeps
    // the intrinsic aspect ratio; otherwise intrinsic pixels 1:1 —
    // the baker pre-scales to the laid-out size, so whatever comes
    // out of here is exactly what the GS draws.
    let w = resolveLength(s.width, availW);
    let h = resolveLength(s.height, availH);
    // A streamed slot has no file, so it has no intrinsic size to fall
    // back on: the author has to state both. Caught here rather than
    // later as a zero-sized quad the baker silently drops, which is
    // what happens to any image whose width or height computes to 0.
    if (box.image.streamed && (w == null || h == null)) {
      throw new Error(
        `layout: <img data-tex-slot="${box.image.name}"> needs an explicit `
        + 'width and height — a streamed slot has no file to take its '
        + 'intrinsic size from, and the reservation is sized from these',
      );
    }
    if (w == null && h == null) {
      w = box.image.w + pb.left + pb.right;
      h = box.image.h + pb.top + pb.bottom;
    } else if (h == null) {
      h = roundHalfUp((w - pb.left - pb.right) * box.image.h / box.image.w)
        + pb.top + pb.bottom;
    } else if (w == null) {
      w = roundHalfUp((h - pb.top - pb.bottom) * box.image.w / box.image.h)
        + pb.left + pb.right;
    }
    return {
      w: clampSize(w, resolveLength(s.minWidth, availW), resolveLength(s.maxWidth, availW)),
      h: clampSize(h, resolveLength(s.minHeight, availH), resolveLength(s.maxHeight, availH)),
    };
  }

  let w = resolveLength(s.width, availW);
  let h = resolveLength(s.height, availH);
  if (w != null && h != null) return { w, h };

  const axis = axisOf(s);
  const innerW = (w ?? availW) == null ? null : (w ?? availW) - pb.left - pb.right;
  const innerH = (h ?? availH) == null ? null : (h ?? availH) - pb.top - pb.bottom;
  const innerMain = axis === ROW ? innerW : innerH;
  const innerCross = axis === ROW ? innerH : innerW;

  const lines = computeFlexLines(box, innerMain, innerCross, false, ctx);
  const gapMain = axis === ROW ? s.columnGap : s.rowGap;
  const gapCross = axis === ROW ? s.rowGap : s.columnGap;

  let contentMain = 0;
  let contentCross = 0;
  for (const line of lines) {
    let lm = 0;
    for (const it of line.items) lm += it.baseSize + marginMain(axis, it.box.style);
    lm += gapMain * Math.max(line.items.length - 1, 0);
    contentMain = Math.max(contentMain, lm);
    contentCross += line.crossSize;
  }
  contentCross += gapCross * Math.max(lines.length - 1, 0);

  const contentW = axis === ROW ? contentMain : contentCross;
  const contentH = axis === ROW ? contentCross : contentMain;
  if (w == null) w = contentW + pb.left + pb.right;
  if (h == null) h = contentH + pb.top + pb.bottom;
  w = clampSize(w, resolveLength(s.minWidth, availW), resolveLength(s.maxWidth, availW));
  h = clampSize(h, resolveLength(s.minHeight, availH), resolveLength(s.maxHeight, availH));
  return { w, h };
}

/**
 * Collect children into flex lines.
 *
 * place=false: items carry base sizes and *content* cross sizes.
 * place=true:  flexible lengths resolve against innerMain and each line
 *              gets its used cross size.
 *
 * Bug #5 regression lives in the place branch: a single line in a
 * container with a definite cross size takes the full inner cross size —
 * otherwise align-items: center on the container's children silently
 * degrades to flex-start because the line hugs its content.
 */
export function computeFlexLines(container, innerMain, innerCross, place, ctx) {
  const s = container.style;
  const axis = axisOf(s);
  const gapMain = axis === ROW ? s.columnGap : s.rowGap;
  const wrap = s.flexWrap === 'wrap';

  const items = container.children.map((box) => ({
    box,
    baseSize: childBaseSize(box, axis, innerMain, innerCross, ctx),
    mainSize: 0,
    crossSize: 0,
    x: 0,
    y: 0,
  }));

  // Line breaking.
  const lines = [];
  let cur = { items: [], crossSize: 0 };
  let curMain = 0;
  for (const it of items) {
    const outer = it.baseSize + marginMain(axis, it.box.style);
    const withGap = cur.items.length > 0 ? gapMain + outer : outer;
    if (wrap && innerMain != null && cur.items.length > 0 && curMain + withGap > innerMain + 0.5) {
      lines.push(cur);
      cur = { items: [], crossSize: 0 };
      curMain = outer;
    } else {
      curMain += withGap;
    }
    cur.items.push(it);
  }
  if (cur.items.length > 0 || lines.length === 0) lines.push(cur);

  for (const line of lines) {
    if (place) resolveFlexibleLengths(line, axis, innerMain, gapMain, ctx);
    // Hypothetical cross sizes.
    for (const it of line.items) {
      const cs = it.box.style;
      const crossProp = axis === ROW ? cs.height : cs.width;
      const explicit = resolveLength(crossProp, innerCross);
      if (explicit != null) {
        it.crossSize = explicit;
      } else {
        const mainAvail = place ? it.mainSize : it.baseSize;
        const m = measureNode(
          it.box,
          axis === ROW ? mainAvail : null,
          axis === COL ? mainAvail : null,
          ctx,
        );
        it.crossSize = crossOf(axis, m.w, m.h);
      }
    }
    line.crossSize = Math.max(0, ...line.items.map(
      (it) => it.crossSize + marginCross(axis, it.box.style),
    ));
  }

  if (place && lines.length === 1 && innerCross != null) {
    // Bug #5: single line + definite container cross size ⇒ the line is
    // the container.
    lines[0].crossSize = innerCross;
  }

  return lines;
}

/**
 * The CSS "automatic minimum size" (flexbox 4.5): a flex item never
 * shrinks below its min-content main size unless min-width/min-height
 * says otherwise. Without this floor, an explicit `width: 128px`
 * sidebar caves in when a wrapping grid next to it reports its
 * max-content base size.
 */
function minContentSize(box, dim, ctx) {
  const s = box.style;
  const minProp = dim === 'w' ? s.minWidth : s.minHeight;
  const explicitMin = resolveLength(minProp, null);
  if (explicitMin != null) return explicitMin;
  const mainProp = dim === 'w' ? s.width : s.height;
  if (mainProp.unit === 'px') return mainProp.value;

  const pb = paddingBorder(s);
  const pbSum = dim === 'w' ? pb.left + pb.right : pb.top + pb.bottom;

  if (box.isText()) {
    if (dim === 'h') {
      return resolveLineHeight(s.lineHeight, s.fontSize) + pbSum;
    }
    // Widest unbreakable word. Ellipsizable nowrap text could go
    // narrower, but letting it collapse to the ellipsis alone makes
    // every tile title shrink to "…" the moment space gets tight.
    const font = ctx.fonts.resolve(s.fontWeight);
    let w = 0;
    for (const word of box.text.split(' ')) {
      w = Math.max(w, font.measure(word, s.fontSize, s.letterSpacing));
    }
    return w + pbSum;
  }

  const axis = axisOf(s);
  const queryIsMain = (axis === ROW) === (dim === 'w');
  const childMin = box.children.map((c) => {
    const m = c.style.margin;
    const mSum = dim === 'w' ? m[1] + m[3] : m[0] + m[2];
    return minContentSize(c, dim, ctx) + mSum;
  });
  if (childMin.length === 0) return pbSum;
  if (!queryIsMain) return Math.max(...childMin) + pbSum;
  if (s.flexWrap === 'wrap') return Math.max(...childMin) + pbSum;
  const gap = axis === ROW ? s.columnGap : s.rowGap;
  return childMin.reduce((a, b) => a + b, 0) + gap * (childMin.length - 1) + pbSum;
}

/** CSS 9.7, simplified: distribute free space by grow/shrink with min/max clamping. */
function resolveFlexibleLengths(line, axis, innerMain, gapMain, ctx) {
  const gaps = gapMain * Math.max(line.items.length - 1, 0);
  for (const it of line.items) it.mainSize = it.baseSize;
  if (innerMain == null) return;

  const outerSum = () => line.items.reduce(
    (a, it) => a + it.mainSize + marginMain(axis, it.box.style), 0,
  ) + gaps;

  let free = innerMain - outerSum();
  const frozen = new Set();

  for (let iter = 0; iter < 8 && Math.abs(free) > 0.25; iter++) {
    const grow = free > 0;
    const flexible = line.items.filter((it) => !frozen.has(it)
      && (grow ? it.box.style.flexGrow > 0 : it.box.style.flexShrink > 0));
    if (flexible.length === 0) break;

    if (grow) {
      const totalGrow = flexible.reduce((a, it) => a + it.box.style.flexGrow, 0);
      for (const it of flexible) it.mainSize += free * (it.box.style.flexGrow / totalGrow);
    } else {
      // Shrink weighted by (factor × base size) per spec, so a big box
      // gives up proportionally more.
      const totalScaled = flexible.reduce((a, it) => a + it.box.style.flexShrink * it.baseSize, 0);
      if (totalScaled <= 0) break;
      for (const it of flexible) {
        it.mainSize += free * ((it.box.style.flexShrink * it.baseSize) / totalScaled);
      }
    }
    // Clamp violations and freeze.
    for (const it of flexible) {
      const cs = it.box.style;
      let min = resolveLength(axis === ROW ? cs.minWidth : cs.minHeight, innerMain);
      if (min == null && !grow) {
        min = minContentSize(it.box, axis === ROW ? 'w' : 'h', ctx);
      }
      const max = resolveLength(axis === ROW ? cs.maxWidth : cs.maxHeight, innerMain);
      const clamped = clampSize(it.mainSize, min ?? 0, max);
      if (clamped !== it.mainSize) {
        it.mainSize = clamped;
        frozen.add(it);
      }
    }
    free = innerMain - outerSum();
  }
}

function justifyOffsets(justify, free, count, gapMain) {
  // Returns [leading, betweenExtra]; gaps always apply on top.
  if (free < 0) free = 0;
  switch (justify) {
    case 'flex-end': return [free, 0];
    case 'center': return [free / 2, 0];
    case 'space-between':
      return count > 1 ? [0, free / (count - 1)] : [0, 0];
    case 'space-around': {
      const around = free / count;
      return [around / 2, around];
    }
    default: return [0, 0]; // flex-start
  }
}

function alignOffset(align, lineCross, itemCross) {
  switch (align) {
    case 'flex-end': return lineCross - itemCross;
    case 'center': return (lineCross - itemCross) / 2;
    default: return 0; // flex-start, stretch (stretch resizes, offset 0)
  }
}

/**
 * Place pass: assign final geometry to `box` (already sized to w×h at
 * x,y) and recurse. Rounds to integers on write.
 */
export function placeNode(box, x, y, w, h, ctx) {
  box.x = roundHalfUp(x);
  box.y = roundHalfUp(y);
  box.width = roundHalfUp(w);
  box.height = roundHalfUp(h);

  const s = box.style;
  const pb = paddingBorder(s);

  if (box.isText()) {
    const innerW = box.width - pb.left - pb.right;
    const t = measureText(box, innerW, ctx.fonts);
    // Ellipsize overflowing nowrap lines when asked to.
    if (s.whiteSpace === 'nowrap' && s.textOverflow === 'ellipsis') {
      const font = ctx.fonts.resolve(s.fontWeight);
      t.lines = t.lines.map((l) => (l.width > innerW
        ? ellipsize(l.text, font, s.fontSize, innerW, s.letterSpacing)
        : l));
    }
    box.lines = t.lines.map((l, i) => {
      let lx = 0;
      if (s.textAlign === 'center') lx = (innerW - l.width) / 2;
      else if (s.textAlign === 'right') lx = innerW - l.width;
      return {
        text: l.text,
        x: box.x + pb.left + roundHalfUp(Math.max(lx, 0)),
        // Baseline = line top + ascent, with the half-leading split.
        y: box.y + pb.top + i * t.lineH,
        width: l.width,
        lineHeight: t.lineH,
        ascent: t.font.ascentPx(s.fontSize),
        leading: t.lineH - t.font.ascentPx(s.fontSize) - t.font.descentPx(s.fontSize),
      };
    });
    return;
  }

  const axis = axisOf(s);
  const innerW = box.width - pb.left - pb.right;
  const innerH = box.height - pb.top - pb.bottom;
  const innerMain = mainOf(axis, innerW, innerH);
  const innerCross = crossOf(axis, innerW, innerH);
  const gapMain = axis === ROW ? s.columnGap : s.rowGap;
  const gapCross = axis === ROW ? s.rowGap : s.columnGap;

  const lines = computeFlexLines(box, innerMain, innerCross, true, ctx);

  // Multi-line cross distribution: lines stack from cross-start.
  let crossPos = 0;
  for (const line of lines) {
    const used = line.items.reduce(
      (a, it) => a + it.mainSize + marginMain(axis, it.box.style), 0,
    ) + gapMain * Math.max(line.items.length - 1, 0);
    const [lead, extra] = justifyOffsets(s.justifyContent, innerMain - used, line.items.length, gapMain);

    let mainPos = lead;
    const ordered = isReverse(s) ? [...line.items].reverse() : line.items;
    for (let i = 0; i < ordered.length; i++) {
      const it = ordered[i];
      const cs = it.box.style;
      const align = cs.alignSelf !== 'auto' ? cs.alignSelf : s.alignItems;

      let itemCross = it.crossSize;
      const crossProp = axis === ROW ? cs.height : cs.width;
      // Deliberate CSS deviation: browsers stretch auto-cross images in
      // flex containers (distorting them); here a replaced element
      // keeps its intrinsic aspect unless the cross size is explicit.
      // Pixel art on a CRT beats spec fidelity on this one.
      if (align === 'stretch' && crossProp.unit === 'auto' && !it.box.image) {
        itemCross = line.crossSize - marginCross(axis, cs);
        const min = resolveLength(axis === ROW ? cs.minHeight : cs.minWidth, innerCross);
        const max = resolveLength(axis === ROW ? cs.maxHeight : cs.maxWidth, innerCross);
        itemCross = clampSize(itemCross, min, max);
      }
      const co = alignOffset(align, line.crossSize, itemCross + marginCross(axis, cs));

      const mainStart = mainPos + marginMainStart(axis, cs);
      const crossStart = crossPos + co + marginCrossStart(axis, cs);
      const cx = box.x + pb.left + (axis === ROW ? mainStart : crossStart);
      const cy = box.y + pb.top + (axis === ROW ? crossStart : mainStart);
      const cw = axis === ROW ? it.mainSize : itemCross;
      const ch = axis === ROW ? itemCross : it.mainSize;
      placeNode(it.box, cx, cy, cw, ch, ctx);

      mainPos += it.mainSize + marginMain(axis, cs) + gapMain + (i < ordered.length - 1 ? extra : 0);
    }
    crossPos += line.crossSize + gapCross;
  }
}

/** Entry point: lay out the root box into the fixed canvas. */
export function layoutTree(root, canvasW, canvasH, ctx) {
  placeNode(root, 0, 0, canvasW, canvasH, ctx);
}
