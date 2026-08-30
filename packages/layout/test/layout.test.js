// Flexbox solver, text measurement, and the paint/focus/lint stages,
// exercised through the public compile() entry point.

import test from 'node:test';
import assert from 'node:assert/strict';

import { compile, FontContext, loadFont } from '../src/index.js';
import { wrapText, ellipsize } from '../src/text.js';
import { roundHalfUp } from '../src/values.js';

const fonts = FontContext.fromDir();
const font = fonts.resolve(400);

function compileCss(html, css) {
  return compile(html, css, { fonts });
}

/** First rect command matching a predicate. */
function rects(ir) { return ir.commands.filter((c) => c.op === 'rect'); }
function texts(ir) { return ir.commands.filter((c) => c.op === 'text'); }

// ------------------------------------------------------------------ text

test('text: the shared rounding rule is floor(units*size/1000 + 0.5)', () => {
  // 'i' in DejaVu Sans is 278/1000em. At 13px: 278*13/1000 = 3.614 -> 4.
  const units = font.advanceUnits('i'.codePointAt(0));
  assert.equal(units, 278);
  assert.equal(font.glyphAdvance(105, 13), roundHalfUp(278 * 13 / 1000));
  assert.equal(font.glyphAdvance(105, 13), 4);
});

test('text: measure sums integral advances, never float widths', () => {
  const w = font.measure('iii', 13);
  assert.equal(w, 12); // 3 * round(3.614) = 12, not round(10.842) = 11
});

test('text: greedy wrap breaks at spaces only', () => {
  const lines = wrapText('aaa bbb ccc', font, 16, font.measure('aaa bbb', 16) + 1);
  assert.equal(lines.length, 2);
  assert.equal(lines[0].text, 'aaa bbb');
  assert.equal(lines[1].text, 'ccc');
});

test('text: a single overlong word overflows as its own line', () => {
  const lines = wrapText('abc supercalifragilistic xyz', font, 16, 40);
  assert.ok(lines.some((l) => l.text === 'supercalifragilistic'));
  const long = lines.find((l) => l.text === 'supercalifragilistic');
  assert.ok(long.width > 40);
});

test('text: ellipsize truncates to fit and appends …', () => {
  const full = 'Shadow of the Colossus';
  const out = ellipsize(full, font, 14, 100);
  assert.ok(out.text.endsWith('…'));
  assert.ok(out.width <= 100);
  assert.ok(out.text.length < full.length);
});

// --------------------------------------------------------------- kerning

test('kerning: pairs from the metrics shift the pen, directionally', () => {
  // 'To' is the textbook pair. The metrics carry -170 units for it and
  // nothing for 'oT', because kerning is a property of the ordered pair.
  assert.equal(font.kernPx(0x54, 0x6f, 32), roundHalfUp(-170 * 32 / 1000));
  assert.equal(font.kernPx(0x54, 0x6f, 32), -5);
  assert.equal(font.kernPx(0x6f, 0x54, 32), 0);
  // An unkerned pair costs nothing, and neither does the first glyph.
  assert.equal(font.kernPx(0x69, 0x69, 32), 0);
  assert.equal(font.kernPx(null, 0x6f, 32), 0);
});

test('kerning: every kern is integral, and half-pixels round toward zero', () => {
  // Each kern is rounded on its own, by the same rule as an advance,
  // so a string of them can never leave the pen on a half pixel — the
  // GS cannot draw one, and both hosts must land on the same integer.
  for (const size of [8, 11, 13, 16, 24, 32, 48]) {
    for (const [a, b] of [[0x54, 0x6f], [0x41, 0x56], [0x50, 0x2e]]) {
      assert.ok(Number.isInteger(font.kernPx(a, b, size)));
    }
  }
  // floor(x + 0.5) is asymmetric about zero: +0.5 rounds away from it,
  // -0.5 rounds toward it. Kerns are almost all negative, so the tie
  // case under-applies the kern — text comes out a pixel wider than
  // ideal rather than a pixel narrower. That is the safe direction:
  // the measured box is never smaller than what gets drawn in it.
  const tie = new (Object.getPrototypeOf(font).constructor)({
    family: 'tie', unitsPerEm: 1000, ascent: 800, descent: 200,
    advances: { 65: 500, 66: 500 },
    kerning: { '65,66': -100, '66,65': 100 },
  });
  assert.equal(tie.kernPx(0x41, 0x42, 5), 0);   // -0.5 -> 0, not -1
  assert.equal(tie.kernPx(0x42, 0x41, 5), 1);   // +0.5 -> 1
  // Real pairs at the smallest size the CRT linter tolerates.
  assert.equal(font.kernPx(0x54, 0x6f, 8), -1); // -170 units -> -1.36px
  assert.equal(font.kernPx(0x41, 0x56, 8), -1); // -64 units -> -0.51px
});

test('kerning: measure is the pen walk, not the sum of advances', () => {
  const unkerned = font.glyphAdvance(0x54, 32) + font.glyphAdvance(0x6f, 32);
  assert.equal(font.measure('To', 32), unkerned + font.kernPx(0x54, 0x6f, 32));
  assert.ok(font.measure('To', 32) < unkerned);
});

test('kerning: every glyph lands on the width the previous ones sum to', () => {
  // The invariant the baker's pen and the runtime's pen both mirror:
  // glyph n sits at exactly measure(prefix of n glyphs) plus its kern.
  const { glyphs, width } = font.layout('Library of Colossus', 24);
  for (let i = 1; i < glyphs.length; i++) {
    assert.ok(glyphs[i].x > glyphs[i - 1].x, `glyph ${i} did not advance`);
  }
  assert.equal(width, glyphs[glyphs.length - 1].x
    + font.glyphAdvance(glyphs[glyphs.length - 1].cp, 24));
});

test('kerning: wrapping agrees with measure on every line it produces', () => {
  // wrapText accumulates a width incrementally; the caller sizes the
  // box from that and the baker places glyphs from measure(). If the
  // two ever disagree the text silently escapes its box, so this is
  // the load-bearing test for the whole pen.
  const corpus = [
    'To the Victor AWAY Ta Yo LT P. r. W. AV VA',
    'Shadow of the Colossus Traveller Wanderer',
    'A V T o P . W A T V A T o T',
  ];
  for (const text of corpus) {
    for (const size of [11, 16, 24, 32]) {
      for (const maxWidth of [40, 80, 160, 320]) {
        for (const ls of [0, 1, 2]) {
          for (const line of wrapText(text, font, size, maxWidth, ls)) {
            assert.equal(line.width, font.measure(line.text, size, ls),
              `${JSON.stringify(line.text)} at ${size}px ls=${ls}`);
          }
        }
      }
    }
  }
});

test('kerning: ellipsize measures the ellipsis where it actually lands', () => {
  // '…' kerns against whatever glyph the cut leaves last, so its cost
  // is not a constant that can be subtracted from the budget up front.
  for (const size of [13, 20, 32]) {
    for (const maxWidth of [30, 60, 100, 180]) {
      const out = ellipsize('Shadow of the Colossus TV', font, size, maxWidth);
      assert.equal(out.width, font.measure(out.text, size),
        `${JSON.stringify(out.text)} at ${size}px`);
      if (out.text !== '…') assert.ok(out.width <= maxWidth);
    }
  }
});

test('kerning: a font with no pairs behaves exactly as before', () => {
  // The escape hatch and the fail-safe: fontgen emits an empty table
  // when the shaper cannot do GPOS, and that must degrade to the plain
  // advance sum rather than to something subtly different.
  const bare = new (Object.getPrototypeOf(font).constructor)({
    family: font.family, weight: font.weight, unitsPerEm: 1000,
    ascent: font.ascent, descent: font.descent,
    advances: font.advances, missing: font.missing,
  });
  assert.deepEqual(bare.kerning, {});
  const s = 'To the Victor AWAY';
  let sum = 0;
  for (const ch of s) sum += bare.glyphAdvance(ch.codePointAt(0), 32);
  assert.equal(bare.measure(s, 32), sum);
  assert.ok(font.measure(s, 32) < sum);
});

test('flex: a container with two or more children must state its direction', () => {
  // There is no good default. CSS's initial value is `row`; this
  // compiler shipped `column`, undocumented, so anyone who knew CSS
  // got the opposite of what they wrote. Neither answer is right for
  // everyone, so the compiler declines to guess.
  assert.throws(
    () => compileCss(
      '<div class="s"><p class="t">a</p><p class="t">b</p></div>',
      '.s { gap: 4px } .t { font-size: 16px; color: #ffffff }',
    ),
    /without stating flex-direction/,
  );
  // Every offender at once, in document order: migrating a file
  // written against the old implicit default has one of these per
  // container, and reporting only the first makes that a queue of
  // single-line edit-compile cycles.
  assert.throws(
    () => compileCss(
      '<div class="a"><div class="b"><p class="t">x</p><p class="t">y</p></div>'
      + '<p class="t">z</p></div>',
      '.t { font-size: 16px; color: #ffffff }',
    ),
    (e) => {
      const lines = e.message.split('\n').filter((l) => l.startsWith('  <'));
      assert.equal(lines.length, 2);          // .a and .b, both offending
      assert.match(e.message, /^layout: 2 container\(s\)/);
      return true;
    },
  );
  // Either answer satisfies it, and they differ — which is the whole
  // point of asking.
  const asRow = compileCss(
    '<div class="s"><p class="t">a</p><p class="t">b</p></div>',
    '.s { flex-direction: row; gap: 4px } .t { font-size: 16px; color: #ffffff }',
  );
  const asCol = compileCss(
    '<div class="s"><p class="t">a</p><p class="t">b</p></div>',
    '.s { flex-direction: column; gap: 4px } .t { font-size: 16px; color: #ffffff }',
  );
  const ys = (ir) => texts(ir).map((c) => c.y);
  const xs = (ir) => texts(ir).map((c) => c.x);
  assert.equal(ys(asRow)[0], ys(asRow)[1]);      // side by side
  assert.notEqual(xs(asRow)[0], xs(asRow)[1]);
  assert.notEqual(ys(asCol)[0], ys(asCol)[1]);   // stacked
  assert.equal(xs(asCol)[0], xs(asCol)[1]);
});

test('flex: direction is only demanded where it could change anything', () => {
  // One child lays out identically either way, so a leaf, a text box
  // or a single-child wrapper is never asked. Requiring it there would
  // be noise on nearly every element in a document.
  const ir = compileCss(
    '<div class="s"><div class="w"><p class="t">only</p></div></div>',
    '.s { padding: 4px } .w { padding: 2px } .t { font-size: 16px; color: #ffffff }',
  );
  assert.equal(texts(ir).length, 1);
  // And a `display: none` child does not count toward the two, because
  // it never becomes a box at all.
  const hidden = compileCss(
    '<div class="s"><p class="t">shown</p><p class="gone">hidden</p></div>',
    '.s { padding: 4px } .t { font-size: 16px; color: #ffffff }'
    + ' .gone { display: none }',
  );
  assert.equal(texts(hidden).length, 1);
});

test('slots: letter-spacing travels with the slot descriptor', () => {
  // The pen that draws slot text runs on the console, so every input
  // to the pen must reach it. Leaving spacing behind meant layout
  // measured the box with a value the glyphs were never drawn with.
  const ir = compileCss(
    '<div class="s"><p class="t" data-slot="title">Hello</p></div>',
    '.s { padding: 4px; } .t { font-size: 16px; letter-spacing: 3px; }',
  );
  assert.equal(ir.slots.length, 1);
  assert.equal(ir.slots[0].letterSpacing, 3);
  // and zero when unstyled, so the baker's feature bit stays clear
  const plain = compileCss(
    '<div class="s"><p data-slot="t2">Hi</p></div>',
    '.s { padding: 4px; }',
  );
  assert.equal(plain.slots[0].letterSpacing, 0);
});

test('lint: data-nocontrast exempts text whose invisibility is the point', () => {
  // Bring-up steps 4 and 5 paint glyphs the exact colour of the block
  // behind them, so a correct console renders nothing and the operator
  // answers "can you see letters here" instead of judging a shade no
  // photograph can convey. The contrast rule is right to hate that, and
  // would emit a permanent false alarm on every build -- which is how a
  // linter teaches people to skim past it.
  const html = '<div class="blk"><p class="ink">MMMM</p></div>';
  const css = '.blk { background: #7a5c3e; height: 20px; } '
            + '.ink { color: #7a5c3e; font-size: 14px; }';

  // Without the attribute the rule must fire, or the test below proves
  // nothing: an exemption that silences a warning nobody was raising is
  // not an exemption.
  const loud = compileCss(html, css);
  assert.ok(loud.warnings.some((w) => w.startsWith('contrast:')),
            'identical ink and block must trip the contrast rule');

  const quiet = compileCss(
    '<div class="blk"><p class="ink" data-nocontrast>MMMM</p></div>', css);
  assert.equal(
    quiet.warnings.filter((w) => w.startsWith('contrast:')).length, 0,
    'data-nocontrast must silence it');

  // Scoped to the one rule. A blanket data-nolint gets reached for;
  // this one has to be argued for each time, so prove the others still
  // speak through it.
  const tiny = compileCss(
    '<div class="blk"><p class="ink" data-nocontrast>MMMM</p></div>',
    '.blk { background: #7a5c3e; height: 20px; } '
    + '.ink { color: #7a5c3e; font-size: 9px; }');
  assert.ok(tiny.warnings.some((w) => w.startsWith('min-font-size:')),
            'other rules must still fire on an exempted element');
});

test('lint: contrast never composites mutually exclusive focus states', () => {
  // `:focus` is a paint-only delta -- one command list carries both
  // states and the runtime draws whichever matches. A node's focused
  // background and its unfocused text therefore never share a frame,
  // and compositing one under the other invents a frame the console
  // cannot produce. A chip with a bright focus fill used to report
  // 1.11:1 against its own unfocused grey text, measured against a
  // background only ever painted when that text is white.
  const ir = compileCss(
    '<div class="s"><p class="chip" id="c" focusable autofocus>NET</p></div>',
    '.s { background: #0b0f16; padding: 20px; }'
    + '.chip { font-size: 16px; color: #8b94a7; background: #141a26;'
    + ' padding: 4px 10px; }'
    + '.chip:focus { background: #7c9be0; color: #0b0f16; }',
  );
  // warnings are formatted strings, not objects -- filtering them by a
  // `.rule` property silently matches nothing and passes whatever the
  // linter did.
  assert.equal(ir.warnings.filter((w) => w.startsWith('contrast:')).length, 0);

  // And the rule still fires when a state really is low contrast:
  // grey text on the same grey panel, in the state that draws it.
  const bad = compileCss(
    '<div class="s"><p class="chip" id="c" focusable autofocus>NET</p></div>',
    '.s { background: #0b0f16; padding: 20px; }'
    + '.chip { font-size: 16px; color: #202839; background: #141a26;'
    + ' padding: 4px 10px; }'
    + '.chip:focus { background: #141a26; color: #202839; }',
  );
  assert.ok(bad.warnings.some((w) => w.startsWith('contrast:')));
});

test('lint: the cross-node focused case is unreachable, and why', () => {
  // `coexists` also refuses to composite two *different* nodes' focused
  // states, since the runtime's `c->focus == ctx->focus` gives exactly
  // one focused node per frame. Reaching that in the chain needs one
  // focusable's rect to contain another's text — and today the only
  // way to overlap two focusables is to nest them, which the compiler
  // refuses outright. So the clause is forward cover for `position:
  // absolute` (F8), not a live path. Pinned here so that if this error
  // ever relaxes, someone is pointed at the lint clause that starts
  // mattering.
  assert.throws(
    () => compileCss(
      '<div class="row" id="r" focusable autofocus>'
      + '<p class="btn" id="b" focusable>GO</p></div>',
      '.row { background: #101623; padding: 6px; }'
      + '.btn { font-size: 16px; color: #dbe2ee; }',
    ),
    /nested focusable/,
  );
});

test('data-keep: the attribute reaches the IR, and only when present', () => {
  // The baker cannot exempt geometry from the trim unless layout tells
  // it which. Absent means absent -- not `keep: false` on every
  // command, which would grow the IR for an attribute almost nothing
  // uses.
  const ir = compileCss(
    '<div class="s"><div class="a" data-keep></div><div class="b"></div></div>',
    '.s { flex-direction: row; padding: 4px }'
    + '.a { width: 10px; height: 10px; background: #ff00ff }'
    + '.b { width: 10px; height: 10px; background: #00ff00 }',
  );
  const marked = rects(ir).filter((c) => c.keep === true);
  assert.equal(marked.length, 1);
  assert.deepEqual(marked[0].fill.slice(0, 3), [255, 0, 255]);
  // and the sibling carries no key at all
  const plain = rects(ir).find((c) => c.fill && c.fill[1] === 255);
  assert.equal('keep' in plain, false);
});

// ------------------------------------------------------------------ flex

test('flex: row places children left to right with gap', () => {
  const ir = compileCss(
    '<div class="r"><div class="a">x</div><div class="a">y</div></div>',
    '.r { flex-direction: row; gap: 10px } .a { width: 50px; height: 20px; background: #333333 }',
  );
  const [a, b] = rects(ir);
  assert.equal(b.x - (a.x + a.w), 10);
  assert.equal(a.y, b.y);
});

test('flex: flex-grow distributes free space proportionally', () => {
  const ir = compileCss(
    '<div class="o"><div class="r"><div class="a">x</div><div class="b">y</div></div></div>',
    `.r { flex-direction: row; width: 300px; height: 40px }
     .a { flex: 1; background: #111111 }
     .b { flex: 2; background: #222222 }`,
  );
  const [a, b] = rects(ir);
  assert.equal(a.w + b.w, 300);
  assert.ok(Math.abs(b.w - 2 * a.w) <= 1, `${b.w} should be ~2x ${a.w}`);
});

test('flex: bug #3 — auto-sized siblings are content-sized, not stretched', () => {
  const ir = compileCss(
    '<div class="row"><div class="fixed">x</div><div class="auto">hi</div></div>',
    `.row { flex-direction: row; }
     .fixed { width: 80px; height: 30px; background: #101010 }
     .auto { background: #202020; height: 30px }`,
  );
  const [fixed, auto] = rects(ir);
  assert.equal(fixed.w, 80);
  // "hi" at 16px is ~17px wide; a measurement-as-stretched bug would
  // report the whole remaining canvas width instead.
  assert.ok(auto.w < 40, `auto width ${auto.w} should hug content`);
});

test('flex: bug #5 — single line in a definite-height row centers its items', () => {
  const ir = compileCss(
    '<div class="o"><div class="row"><div class="item">x</div></div></div>',
    `.row { flex-direction: row; height: 100px; align-items: center }
     .item { width: 20px; height: 20px; background: #303030 }`,
  );
  const [item] = rects(ir);
  // Without the container-cross-size rule the line hugs the 20px item
  // and center degenerates to top (y = 0).
  assert.equal(item.y, 40);
});

test('flex: shrink respects the min-content floor of a fixed-width item', () => {
  const ir = compileCss(
    '<div class="row"><div class="side">x</div><div class="wide">y</div></div>',
    `.row { flex-direction: row }
     .side { width: 100px; height: 10px; background: #101010 }
     .wide { width: 900px; height: 10px; background: #202020 }`,
  );
  const [side] = rects(ir);
  assert.equal(side.w, 100, 'explicit width survives a shrinking sibling');
});

test('flex: justify-content space-between and center', () => {
  const ir = compileCss(
    '<div class="row"><div class="i">a</div><div class="i">b</div></div>',
    `.row { flex-direction: row; justify-content: space-between }
     .i { width: 50px; height: 10px; background: #101010 }`,
  );
  const [a, b] = rects(ir);
  assert.equal(a.x, 0);
  assert.equal(b.x + b.w, 640);
});

test('flex: wrap produces rows and respects gaps', () => {
  const ir = compileCss(
    '<div class="o"><div class="grid"><div class="c">1</div><div class="c">2</div><div class="c">3</div></div></div>',
    `.grid { flex-direction: row; flex-wrap: wrap; gap: 8px; width: 220px }
     .c { width: 100px; height: 30px; background: #101010 }`,
  );
  const cs = rects(ir);
  assert.equal(cs[0].y, cs[1].y);
  assert.ok(cs[2].y > cs[0].y, 'third cell wrapped');
  assert.equal(cs[2].y - cs[0].y, 38); // 30 row height + 8 row gap
});

test('flex: padding and border inset the content box (border-box model)', () => {
  const ir = compileCss(
    '<div class="o"><div class="p"><div class="c">x</div></div></div>',
    `.p { width: 200px; height: 100px; padding: 10px; border: 3px solid #444444; background: #111111 }
     .c { background: #222222 }`,
  );
  const all = rects(ir);
  const outer = all.find((r) => r.fill && r.fill[0] === 0x11);
  const inner = all.find((r) => r.fill && r.fill[0] === 0x22);
  assert.equal(outer.w, 200);
  assert.equal(inner.x - outer.x, 13);
  assert.equal(inner.w, 200 - 2 * 13);
});

test('flex: display:none removes the subtree entirely', () => {
  const ir = compileCss(
    '<div><div class="gone"><p>invisible</p></div><p>visible</p></div>',
    '.gone { display: none }',
  );
  assert.equal(texts(ir).length, 1);
  assert.equal(texts(ir)[0].text, 'visible');
});

// ----------------------------------------------------------------- paint

test('paint: bug #4 — anonymous text boxes repaint no parent chrome', () => {
  const ir = compileCss(
    '<div class="panel">hello</div>',
    '.panel { background: #202020; border: 2px solid #555555; padding: 8px }',
  );
  // One background fill + 4 border edges collapse to ONE rect command
  // here (borders are painted by the baker); the text adds text
  // commands, never another rect.
  assert.equal(rects(ir).length, 1);
  assert.equal(texts(ir).length, 1);
});

test('paint: focus delta emits paired unfocused/focused commands', () => {
  const ir = compileCss(
    '<div class="b" focusable id="btn">go</div>',
    '.b { background: #111111 } .b:focus { background: #333333 }',
  );
  const rs = rects(ir);
  assert.equal(rs.length, 2);
  assert.deepEqual(rs.map((r) => r.state).sort(), ['focused', 'unfocused']);
  assert.equal(rs[0].focusId, rs[1].focusId);
  // Identical geometry, different fill.
  assert.deepEqual([rs[0].x, rs[0].y, rs[0].w, rs[0].h], [rs[1].x, rs[1].y, rs[1].w, rs[1].h]);
  assert.notDeepEqual(rs[0].fill, rs[1].fill);
});

test('paint: unfocus-identical paint stays a single always command', () => {
  const ir = compileCss(
    '<div class="b" focusable>go</div>',
    '.b { background: #111111 } .b:focus { border-color: #ffffff }', // no border-width -> no visible change
  );
  const rs = rects(ir);
  assert.equal(rs.length, 1);
  assert.equal(rs[0].state, 'always');
});

test('paint: overflow hidden brackets children with a scissor pair', () => {
  const ir = compileCss(
    '<div class="clip"><p>long text that overflows</p></div>',
    '.clip { width: 60px; height: 20px; overflow: hidden }',
  );
  const ops = ir.commands.map((c) => c.op);
  const push = ops.indexOf('scissor_push');
  const pop = ops.lastIndexOf('scissor_pop');
  assert.ok(push !== -1 && pop !== -1 && push < pop);
  assert.ok(ops.slice(push + 1, pop).includes('text'));
});

// ----------------------------------------------------------------- focus

test('focus: grid neighbors resolve spatially', () => {
  const ir = compileCss(
    `<div class="o"><div class="grid">
       <div class="c" id="a" focusable>a</div><div class="c" id="b" focusable>b</div>
       <div class="c" id="c" focusable>c</div><div class="c" id="d" focusable>d</div>
     </div></div>`,
    `.grid { flex-direction: row; flex-wrap: wrap; gap: 10px; width: 230px }
     .c { width: 100px; height: 40px; background: #101010 }`,
  );
  const byName = Object.fromEntries(ir.focus.nodes.map((n) => [n.name, n]));
  const byId = Object.fromEntries(ir.focus.nodes.map((n) => [n.id, n]));
  assert.equal(byId[byName.a.right].name, 'b');
  assert.equal(byId[byName.a.down].name, 'c');
  assert.equal(byId[byName.d.up].name, 'b');
  assert.equal(byId[byName.d.left].name, 'c');
  assert.equal(byName.a.up, null);
});

test('focus: autofocus wins over document order', () => {
  const ir = compileCss(
    '<div><div id="one" focusable>1</div><div id="two" focusable autofocus>2</div></div>',
    'div { flex-direction: column }',
  );
  const initial = ir.focus.nodes.find((n) => n.id === ir.focus.initial);
  assert.equal(initial.name, 'two');
});

test('focus: --focus-wrap fills dead ends within the beam only', () => {
  const ir = compile(
    `<div class="o"><div class="grid">
       <div class="c" id="a" focusable>a</div><div class="c" id="b" focusable>b</div>
       <div class="c" id="c" focusable>c</div><div class="c" id="d" focusable>d</div>
     </div></div>`,
    `.grid { flex-direction: row; flex-wrap: wrap; gap: 10px; width: 230px }
     .c { width: 100px; height: 40px; background: #101010 }`,
    { fonts, focusWrap: true },
  );
  const byName = Object.fromEntries(ir.focus.nodes.map((n) => [n.name, n]));
  const byId = Object.fromEntries(ir.focus.nodes.map((n) => [n.id, n]));
  // Right off b wraps to a (same row), never to c or d.
  assert.equal(byId[byName.b.right].name, 'a');
  assert.equal(byId[byName.a.left].name, 'b');
  // Vertical wrap within the column beam.
  assert.equal(byId[byName.c.down].name, 'a');
  assert.equal(byId[byName.a.up].name, 'c');
});

test('focus: nested focusables are a compile error', () => {
  assert.throws(() => compileCss(
    '<div focusable><div focusable>x</div></div>', 'div { }',
  ), /nested focusable/);
});

test('image: <img> measures intrinsically and emits an image command', () => {
  const ir = compile(
    '<div class="row"><img src="badge.png"><p>x</p></div>',
    '.row { flex-direction: row }',
    { fonts, assetDir: fixtureDir() },
  );
  const img = ir.commands.find((c) => c.op === 'image');
  assert.ok(img, 'image command emitted');
  assert.equal(img.w, 8);
  assert.equal(img.h, 6);
  assert.match(img.src, /badge\.png$/);
  assert.equal(img.state, 'always');
});

test('streamed: data-tex-slot emits a named slot with no src', () => {
  const ir = compile(
    '<div><img data-tex-slot="cover"></div>',
    'img { width: 64px; height: 64px }',
    { fonts, assetDir: fixtureDir() },
  );
  const img = ir.commands.find((c) => c.op === 'image');
  assert.ok(img, 'image command emitted');
  assert.equal(img.streamed, true);
  assert.equal(img.name, 'cover');
  assert.equal(img.src, undefined, 'a streamed slot has no file');
  assert.equal(img.w, 64);
  assert.equal(img.h, 64);
});

test('streamed: needs an explicit width and height', () => {
  // No file means no intrinsic size. Without this the box computes to
  // 0x0 and the baker silently drops the quad -- a slot the app can
  // fill and nobody can see.
  assert.throws(() => compileCss(
    '<div><img data-tex-slot="cover"></div>', 'img { width: 64px }',
  ), /needs an explicit width and height/);
});

test('streamed: src and data-tex-slot are mutually exclusive', () => {
  assert.throws(() => compileCss(
    '<div><img data-tex-slot="cover" src="badge.png"></div>', 'img { }',
  ), /mutually exclusive/);
});

test('streamed: the slot needs a name to be addressable', () => {
  assert.throws(() => compileCss(
    '<div><img data-tex-slot=""></div>', 'img { }',
  ), /data-tex-slot needs a name/);
});

test('streamed: a padded name is refused, not silently trimmed', () => {
  // The hazard is not a name of pure spaces, it is a trailing one:
  // `data-tex-slot="cover "` bakes cleanly and then ps2ui_tex_set with
  // "cover" returns ERR_NOT_STREAMED, indistinguishable from a name
  // that was never baked at all.
  for (const name of ['cover ', ' cover', '   ', '\t']) {
    assert.throws(() => compileCss(
      `<div><img data-tex-slot="${name}"></div>`, 'img { }',
    ), /no leading or trailing whitespace/, `refuses ${JSON.stringify(name)}`);
  }
});

test('streamed: an interior space is a visible name and is allowed', () => {
  // The rule is about differences the author cannot see in their own
  // markup, not about a charset. This one is visible in both places.
  const ir = compile(
    '<div><img data-tex-slot="box art" style="x"></div>',
    'img { width: 8px; height: 8px }',
    { fonts, assetDir: fixtureDir() },
  );
  assert.equal(ir.commands.find((c) => c.op === 'image').name, 'box art');
});

test('streamed: palettize is refused, the art does not exist yet', () => {
  assert.throws(() => compileCss(
    '<div><img data-tex-slot="cover" palettize></div>', 'img { }',
  ), /palettize is not supported on a streamed slot/);
});

test('image: one specified axis keeps the intrinsic aspect ratio', () => {
  const ir = compile(
    '<div><img class="wide" src="badge.png"></div>',
    '.wide { width: 32px }',
    { fonts, assetDir: fixtureDir() },
  );
  const img = ir.commands.find((c) => c.op === 'image');
  assert.equal(img.w, 32);
  assert.equal(img.h, 24); // 32 * 6/8
});

test('image: missing src and missing files are compile errors', () => {
  assert.throws(
    () => compile('<div><img></div>', 'div {}', { fonts, assetDir: fixtureDir() }),
    /no src attribute/,
  );
  assert.throws(
    () => compile('<div><img src="nope.png"></div>', 'div {}', { fonts, assetDir: fixtureDir() }),
    /cannot read/,
  );
  assert.throws(
    () => compile('<div><img src="x.png"></div>', 'div {}', { fonts }),
    /no asset base/,
  );
});

test('slots: data-slot captures geometry, colors and placeholder', () => {
  const ir = compileCss(
    '<div class="wrap"><p class="count" data-slot="count" data-slot-capacity="15">6 titles</p></div>',
    `.wrap { padding: 20px }
     .count { font-size: 13px; color: #8b94a7; white-space: nowrap; text-overflow: ellipsis }`,
  );
  assert.equal(ir.slots.length, 1);
  const s = ir.slots[0];
  assert.equal(s.name, 'count');
  assert.equal(s.placeholder, '6 titles');
  assert.equal(s.capacity, 15);
  assert.equal(s.size, 13);
  assert.equal(s.ellipsis, true);
  assert.deepEqual(s.colorBase, [0x8b, 0x94, 0xa7, 255]);
  // No static text commands for the placeholder.
  assert.equal(texts(ir).length, 0);
});

test('slots: multi-line placeholders and duplicate names are errors', () => {
  assert.throws(() => compileCss(
    '<div class="o"><div class="w"><p data-slot="t">a very long placeholder that will definitely wrap</p></div></div>',
    '.w { width: 60px }',
  ), /single-line/);
  assert.throws(() => compileCss(
    '<div><p data-slot="t">a</p><p data-slot="t">b</p></div>',
    'div { flex-direction: column }',
  ), /duplicate data-slot/);
});

// ------------------------------------------------------------------ lint

test('lint: overscan, font size, flicker and contrast all fire', () => {
  const ir = compileCss(
    `<div class="screen">
       <p class="tiny">edge text</p>
       <div class="hair"></div>
       <p class="dim">low contrast</p>
     </div>`,
    `.screen { flex-direction: column; background: #202020 }
     .tiny { font-size: 10px }
     .hair { height: 1px; background: #ffffff; }
     .dim { font-size: 20px; color: #2a2a2a; margin-top: 40px; margin-left: 60px }`,
  );
  const all = ir.warnings.join('\n');
  assert.match(all, /min-font-size/);
  assert.match(all, /overscan/);
  assert.match(all, /interlace-flicker/);
  assert.match(all, /contrast/);
});

test('lint: contrast sees through a translucent scrim', () => {
  // A .uib is replayed over whatever the host app drew, so text sitting
  // on nothing but a translucent scrim has no compile-time background.
  // Reading the scrim's raw RGB made a 20%-opaque overlay lint exactly
  // like an opaque one, which is how a scrim retuned too thin reached a
  // console looking fine on every preview.
  const scrim = (alpha, color) => compileCss(
    '<div class="s"><p class="t">barely there</p></div>',
    `.s { background: #10141e${alpha} } .t { font-size: 20px; color: ${color} }`,
  ).warnings.filter((w) => w.startsWith('contrast'));

  // Pale text on a near-black scrim: fine when the scrim is opaque,
  // unreadable the moment a bright frame shows through it. The old rule
  // read the scrim's raw RGB and could not tell these two apart.
  assert.equal(scrim('ff', '#b8c0d0').length, 0);
  const pale = scrim('33', '#b8c0d0');
  assert.equal(pale.length, 1);
  assert.match(pale[0], /bright frame showing through the 80%-transparent/);

  // Dark text brackets the other way, so the rule has to try both ends
  // rather than assume the backdrop is bright.
  const dark = scrim('33', '#3b4252');
  assert.equal(dark.length, 1);
  assert.match(dark[0], /dark frame showing through the 80%-transparent/);
});

test('lint: an opaque panel over a scrim is judged on the panel alone', () => {
  // The counterpart rule the example is built around: the scrim sets the
  // mood, panels guarantee legibility. Once an opaque fill is in the
  // chain the backdrop cannot reach the text, so no warning.
  const ir = compileCss(
    '<div class="s"><div class="panel"><p class="t">legible</p></div></div>',
    `.s { background: #10141e99 }
     .panel { background: #12182a; padding: 8px }
     .t { font-size: 20px; color: #ffffff }`,
  );
  assert.equal(ir.warnings.filter((w) => w.startsWith('contrast')).length, 0);
});

test('lint: face-button glyphs do not trip the charset rule', () => {
  // Backlog B13: every PS2 footer carries these hints, so warning about
  // them trains authors to ignore the linter.
  const ir = compileCss(
    '<div class="s"><p class="hint">\u00d7 Launch \u25cb Back \u25b3 Options \u25a1 Sort</p></div>',
    '.s { background: #202020 } .hint { font-size: 16px; color: #ffffff }',
  );
  assert.equal(ir.warnings.filter((w) => w.startsWith('charset')).length, 0);
});

test('lint: real non-Latin script still warns', () => {
  const ir = compileCss(
    '<div class="s"><p class="hint">\u30bb\u30fc\u30d6\u30c7\u30fc\u30bf</p></div>',
    '.s { background: #202020 } .hint { font-size: 16px; color: #ffffff }',
  );
  assert.match(ir.warnings.join('\n'), /charset/);
});

test('aspect: PAR derives from canvas and display ratio', () => {
  // The GS framebuffer is not square-pixel even at 4:3.
  const four = compile('<div class="p">x</div>', '.p { background: #202020 }',
    { fonts, displayAspect: [4, 3] });
  assert.equal(four.canvas.par, 0.9333);
  assert.deepEqual(four.canvas.display, { w: 597, h: 448 });

  const wide = compile('<div class="p">x</div>', '.p { background: #202020 }',
    { fonts, displayAspect: [16, 9] });
  assert.equal(wide.canvas.par, 1.2444);
  assert.deepEqual(wide.canvas.display, { w: 796, h: 448 });

  // PAL 640x512 is a different framebuffer shape, so a different PAR.
  const pal = compile('<div class="p">x</div>', '.p { background: #202020 }',
    { fonts, canvasW: 640, canvasH: 512, displayAspect: [16, 9] });
  assert.equal(pal.canvas.par, 1.4222);
});

test('aspect: distortion lint fires at 16:9 and stays quiet at 4:3', () => {
  const css = '.p { background: #202020; border-radius: 8px; width: 90px; height: 40px }';
  const wide = compile('<div class="p">x</div>', css, { fonts, displayAspect: [16, 9] });
  assert.match(wide.warnings.join('\n'), /aspect-distortion.*24% wider/);
  const four = compile('<div class="p">x</div>', css, { fonts, displayAspect: [4, 3] });
  assert.equal(four.warnings.filter((w) => w.startsWith('aspect-distortion')).length, 0);
});

// ------------------------------------------------------- integration

test('integration: the memcard example compiles to the documented shape', () => {
  const ir = compile(
    readFixture('../../../examples/memcard/ui/library.html'),
    readFixture('../../../examples/memcard/ui/library.css'),
    { fonts },
  );
  assert.equal(ir.canvas.w, 640);
  assert.equal(ir.focus.nodes.length, 9);
  const initial = ir.focus.nodes.find((n) => n.id === ir.focus.initial);
  assert.equal(initial.name, 'nav-games');
  // Every tile got its focused border delta.
  const focused = ir.commands.filter((c) => c.state === 'focused' && c.op === 'rect');
  assert.ok(focused.length >= 9);
});

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
function readFixture(rel) {
  return readFileSync(join(dirname(fileURLToPath(import.meta.url)), rel), 'utf8');
}
function fixtureDir() {
  return join(dirname(fileURLToPath(import.meta.url)), 'fixtures');
}

// ---------------------------------------------------------------- repeat

test('repeat: data-repeat stamps N copies with {i} and {n} substituted', () => {
  const ir = compileCss(
    `<div class="s">
       <div class="row" data-repeat="3" id="row-{i}" focusable>
         <p class="t" data-slot="title-{i}" data-slot-capacity="8">Item {n}</p>
       </div>
     </div>`,
    '.s { flex-direction: column; gap: 4px; background: #0a0e1a }'
    + ' .row { background: #12182a; padding: 4px }'
    + ' .t { font-size: 16px; color: #dbe2ee }',
  );
  assert.deepEqual(ir.focus.nodes.map((n) => n.name), ['row-0', 'row-1', 'row-2']);
  assert.deepEqual(ir.slots.map((s) => s.name), ['title-0', 'title-1', 'title-2']);
  // {n} is 1-based, for the copy a human reads.
  assert.deepEqual(ir.slots.map((s) => s.placeholder), ['Item 1', 'Item 2', 'Item 3']);
});

test('repeat: copies lay out as if they had been typed out', () => {
  const css = '.s { flex-direction: column; background: #0a0e1a; gap: 4px }'
    + ' .row { background: #12182a; padding: 4px } .t { font-size: 16px; color: #dbe2ee }';
  const templated = compileCss(
    `<div class="s"><div class="row" data-repeat="3" id="r-{i}"><p class="t">Row {n}</p></div></div>`,
    css,
  );
  const written = compileCss(
    `<div class="s">
       <div class="row" id="r-0"><p class="t">Row 1</p></div>
       <div class="row" id="r-1"><p class="t">Row 2</p></div>
       <div class="row" id="r-2"><p class="t">Row 3</p></div>
     </div>`,
    css,
  );
  // The whole point: expansion happens before styles are computed, so
  // there is no such thing as a "repeated" box downstream.
  assert.deepEqual(templated.commands, written.commands);
});

test('repeat: a count that is not a whole number is a compile error', () => {
  assert.throws(
    () => compileCss('<div class="s"><p data-repeat="{count}">x</p></div>', '.s {}'),
    /data-repeat="\{count\}" is not a whole number/,
  );
});

test('repeat: an out-of-range count names the budget', () => {
  assert.throws(
    () => compileCss('<div class="s"><p data-repeat="0">x</p></div>', '.s {}'),
    /out of range 1\.\.256/,
  );
  assert.throws(
    () => compileCss('<div class="s"><p data-repeat="999">x</p></div>', '.s {}'),
    /out of range 1\.\.256/,
  );
});

test('repeat: nested repeats are refused rather than guessed at', () => {
  assert.throws(
    () => compileCss(
      '<div class="s"><div data-repeat="2"><p data-repeat="2">x</p></div></div>',
      '.s {}',
    ),
    /data-repeat inside data-repeat/,
  );
});

test('repeat: an index on a descendant attribute counts as an index', () => {
  // The shape the README recommends: {i} on a nested data-slot, nothing
  // on the row itself. This warned before the serialiser walked
  // descendant attributes, which is a warning crying wolf on the
  // documented pattern.
  const ir = compileCss(
    '<div class="s"><div class="row" data-repeat="3">'
    + '<p class="t" data-slot="title-{i}" data-slot-capacity="8">x</p></div></div>',
    '.s { flex-direction: column; background: #0a0e1a }'
    + ' .row { background: #12182a; padding: 4px }'
    + ' .t { font-size: 16px; color: #dbe2ee }',
  );
  assert.deepEqual(ir.slots.map((x) => x.name), ['title-0', 'title-1', 'title-2']);
  assert.equal(ir.warnings.filter((w) => /no \{i\} or \{n\}/.test(w)).length, 0);
});

test('repeat: copies with no index are a warning, and duplicate slots an error', () => {
  // Indistinguishable copies are legal but almost never intended.
  const ir = compileCss(
    '<div class="s"><p class="t" data-repeat="3">same</p></div>',
    '.s { flex-direction: column; background: #0a0e1a } .t { font-size: 16px; color: #dbe2ee }',
  );
  assert.ok(ir.warnings.some((w) => /no \{i\} or \{n\} anywhere inside/.test(w)));

  // Forgetting {i} on a data-slot is caught by the existing duplicate
  // check, which names the slot — a better error than any rename magic.
  assert.throws(
    () => compileCss(
      '<div class="s"><p class="t" data-repeat="2" data-slot="title">x</p></div>',
      '.s { flex-direction: column; background: #0a0e1a } .t { font-size: 16px; color: #dbe2ee }',
    ),
    /duplicate data-slot name "title"/,
  );
});

test('repeat: data-repeat never reaches the cascade as an attribute', () => {
  // It is consumed by the expansion pass. If it leaked through, an
  // attribute selector or the unknown-property path could see it.
  const ir = compileCss(
    '<div class="s"><p class="t" data-repeat="2" id="p-{i}">x</p></div>',
    '.s { flex-direction: column; background: #0a0e1a } .t { font-size: 16px; color: #dbe2ee }',
  );
  assert.equal(ir.warnings.filter((w) => /data-repeat/.test(w) && !/no \{i\}/.test(w)).length, 0);
});

// ---------------------------------------------------------------- themes

test('theme: the opacity fold runs over every row, not just the default', () => {
  // THE #77 CASE, END TO END. `opacity` multiplies into a colour's
  // alpha before the name is attached, so one role paints two colours.
  // The failure this pins is a fold applied to row 0 and not the rest:
  // the default theme would still be right, every screenshot would
  // agree, and only the light theme would have a panel at the wrong
  // transparency. Nothing else in the suite can see that.
  const ir = compileCss(
    '<div id="w"><div id="a"></div><div id="b"></div></div>',
    ':root{--panel:#336699}\n@theme light{--panel:#eeeeee}\n'
    + '#w{flex-direction:row}\n'
    + '#a{width:40px;height:20px;background:var(--panel)}\n'
    + '#b{width:40px;height:20px;background:var(--panel);opacity:0.5}',
  );
  assert.deepEqual(ir.themes, ['root', 'light']);
  const [opaque, half] = rects(ir);
  assert.equal(opaque.fillVar, '--panel');
  assert.equal(half.fillVar, '--panel');
  assert.deepEqual(opaque.fillThemes, [[51, 102, 153, 255], [238, 238, 238, 255]]);
  // Halved in BOTH rows. Same role, same fold, two rows.
  assert.deepEqual(half.fillThemes, [[51, 102, 153, 128], [238, 238, 238, 128]]);
});

test('theme: an anonymous text run carries the vector its parent has', () => {
  // box.js copies inherited text style by hand, and the copy was one
  // entry short when this was written: colorVar without colorThemes.
  // Silent -- the default row is right, so nothing renders wrong.
  const ir = compileCss(
    '<div id="p">hello</div>',
    ':root{--ink:#ffffff}\n@theme light{--ink:#111111}\n'
    + '#p{color:var(--ink);font-size:14px}',
  );
  const [t] = texts(ir);
  assert.equal(t.colorVar, '--ink');
  assert.deepEqual(t.colorThemes, [[255, 255, 255, 255], [17, 17, 17, 255]]);
});

test('theme: a fill that no theme paints does not exist in any row', () => {
  // Whether a command EXISTS is structure, and a theme moves colour,
  // not structure. A theme that could delete a command by taking a
  // fill to zero alpha would make the command list depend on the row
  // chosen at runtime, which the format cannot express -- so the
  // live/dead decision is row 0's and every row follows it.
  const ir = compileCss(
    '<div id="a">x</div>',
    ':root{--ghost:rgba(1,2,3,0)}\n@theme light{--ghost:#ff0000}\n'
    + '#a{width:10px;height:10px;background:var(--ghost);font-size:14px}',
  );
  assert.equal(rects(ir).length, 0);
});

test('theme: the lints run over every theme, not just the default row', () => {
  // THE GAP P3b-6 LEFT OPEN. contrast and ntsc-red-bleed read colours;
  // a theme moves colours. So a UI readable in :root can be unreadable
  // in @theme light with every check in the repository still passing --
  // the blob is right, the screenshots are right for the row they
  // render, and the failure is found on a television.
  const ir = compileCss(
    '<div id="w"><span id="t">hello there</span></div>',
    ':root{--panel:#101623;--ink:#f2f5fa}\n'
    + '@theme light{--panel:#f4f6fa;--ink:#ffffff}\n'
    + '#w{flex-direction:column;width:400px;height:40px;'
    + 'background:var(--panel);padding:8px}\n'
    + '#t{color:var(--ink);font-size:16px}',
  );
  const contrast = ir.warnings.filter((w) => w.includes('contrast:'));
  assert.equal(contrast.length, 1, 'readable in root, unreadable in light');
  assert.match(contrast[0], /^@theme light: contrast:/);
});

test('theme: a geometry lint is not repeated once per theme', () => {
  // The dedup, and it earns its place: the geometry lints produce
  // byte-identical strings in every row, so without it a two-theme UI
  // reports every overscan twice and a five-theme one five times. A
  // list with that much duplication is one people skim, which is the
  // same argument data-nocontrast makes in lint.js.
  const ir = compileCss(
    '<div id="w"><span id="t">x</span></div>',
    ':root{--ink:#ffffff}\n@theme light{--ink:#eeeeee}\n'
    + '#w{flex-direction:column}\n#t{color:var(--ink);font-size:9px}',
  );
  const small = ir.warnings.filter((w) => w.includes('min-font-size:'));
  assert.equal(small.length, 1);
  assert.ok(!small[0].startsWith('@theme'), 'reported once, unprefixed');
});

test('theme: slot text is linted, because a data-slot draws no command', () => {
  // PRE-EXISTING AND INVISIBLE. paint.js returns before emitting
  // anything for slot text, and compile() only ever handed `commands`
  // to lintDocument -- so contrast and min-font-size never ran on
  // dynamic text at all. Same colour, same background, same geometry as
  // static text; the only difference was the attribute. opl-env is 127
  // slots, which is every title, count and telemetry line in it.
  const css = ':root{--panel:#101623;--ink:#f2f5fa}\n'
    + '@theme light{--panel:#f4f6fa;--ink:#ffffff}\n'
    + '#w{flex-direction:column;width:400px;height:40px;'
    + 'background:var(--panel);padding:8px}\n'
    + '#t{color:var(--ink);font-size:16px}';
  const contrast = (ir) => ir.warnings.filter((w) => w.includes('contrast:'));

  const staticIr = compileCss('<div id="w"><span id="t">hello there</span></div>', css);
  const slotIr = compileCss(
    '<div id="w"><span id="t" data-slot="s">hello there</span></div>', css);

  assert.equal(contrast(staticIr).length, 1);
  assert.equal(contrast(slotIr).length, 1,
    'the same text behind data-slot must not become invisible to the linter');
  assert.match(contrast(slotIr)[0], /^@theme light: contrast:/);

  // AND ROW 0, WHICH IS A SEPARATE CALL. The check above only reaches
  // the per-theme loop; the default row goes through its own
  // lintDocument, and pointing that one back at `commands` passed
  // every test here. A sheet with no @theme at all is what covers it.
  const plain = ':root{--x:#808080}\n'
    + '#w{flex-direction:column;width:400px;height:40px;'
    + 'background:#808080;padding:8px}\n'
    + '#t{color:#858585;font-size:16px}';
  const plainStatic = compileCss(
    '<div id="w"><span id="t">hello there</span></div>', plain);
  const plainSlot = compileCss(
    '<div id="w"><span id="t" data-slot="s">hello there</span></div>', plain);
  assert.equal(contrast(plainStatic).length, 1);
  assert.equal(contrast(plainSlot).length, 1,
    'unreadable in row 0 and behind a data-slot: still a warning');
  assert.ok(!contrast(plainSlot)[0].startsWith('@theme'));
});

test('theme: a colour lint is reported per theme even when the message is identical', () => {
  // contrastRatio is SYMMETRIC in (foreground, background), so two
  // themes that swap the pair fail identically. Deduplicating colour
  // lints by message hid the second one entirely -- and 2dp rounding
  // widens that well past the symmetric case.
  const ir = compileCss(
    '<div id="w"><span id="t">hello there</span></div>',
    ':root{--panel:#808080;--ink:#858585}\n'
    + '@theme light{--panel:#858585;--ink:#808080}\n'
    + '#w{flex-direction:column;width:400px;height:40px;'
    + 'background:var(--panel);padding:8px}\n'
    + '#t{color:var(--ink);font-size:16px}',
  );
  const contrast = ir.warnings.filter((w) => w.includes('contrast:'));
  assert.equal(contrast.length, 2, 'both themes fail and both must be named');
  assert.ok(contrast.some((w) => w.startsWith('@theme light:')));
});
