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
    'div { }',
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
    'div {}',
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
    `.screen { background: #202020 }
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
