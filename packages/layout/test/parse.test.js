// Parser-level tests: HTML tree building, CSS cascade, value parsing.

import test from 'node:test';
import assert from 'node:assert/strict';

import { parseHTML } from '../src/html.js';
import {
  parseStylesheet, computeStyle, INITIAL_STYLE, parseSelector, selectorMatches,
} from '../src/css.js';
import { parseColor, parseLength } from '../src/values.js';

// ------------------------------------------------------------------ html

test('html: element tree with attrs and text', () => {
  const root = parseHTML('<div class="a b" id="x"><p>hi <span>there</span></p></div>');
  assert.equal(root.tag, 'div');
  assert.deepEqual(root.classes, ['a', 'b']);
  assert.equal(root.id, 'x');
  const p = root.children[0];
  assert.equal(p.tag, 'p');
  assert.equal(p.children[0].type, 'text');
  assert.equal(p.children[0].text, 'hi ');
  assert.equal(p.children[1].tag, 'span');
});

test('html: whitespace collapses, entities decode, comments vanish', () => {
  const root = parseHTML('<div>a&amp;b   \n  c<!-- no -->&#215;</div>');
  assert.equal(root.children.length, 1);
  assert.equal(root.children[0].text, 'a&b c×');
});

test('html: html/body wrappers are transparent, head is skipped', () => {
  const root = parseHTML(
    '<!doctype html><html><head><style>junk {</style></head><body><div id="d">x</div></body></html>',
  );
  assert.equal(root.tag, 'div');
  assert.equal(root.id, 'd');
});

test('html: mismatched close tag is a hard error with line info', () => {
  assert.throws(() => parseHTML('<div>\n<p>text</div>'), /line 2|<p>/);
});

test('html: unclosed element is a hard error', () => {
  assert.throws(() => parseHTML('<div><p>text'), /never closed/);
});

test('html: boolean attributes parse', () => {
  const root = parseHTML('<div focusable autofocus id="z">x</div>');
  assert.ok('focusable' in root.attrs);
  assert.ok('autofocus' in root.attrs);
});

// ---------------------------------------------------------------- values

test('values: color forms', () => {
  assert.deepEqual(parseColor('#fff'), [255, 255, 255, 255]);
  assert.deepEqual(parseColor('#0a0e1a'), [10, 14, 26, 255]);
  assert.deepEqual(parseColor('#11162400'), [17, 22, 36, 0]);
  assert.deepEqual(parseColor('rgb(1, 2, 3)'), [1, 2, 3, 255]);
  assert.deepEqual(parseColor('rgba(10, 20, 30, 0.5)'), [10, 20, 30, 128]);
  assert.equal(parseColor('bogus'), null);
});

test('values: lengths', () => {
  assert.deepEqual(parseLength('12px'), { unit: 'px', value: 12 });
  assert.deepEqual(parseLength('50%'), { unit: '%', value: 50 });
  assert.deepEqual(parseLength('1.3'), { unit: 'number', value: 1.3 });
  assert.deepEqual(parseLength('auto'), { unit: 'auto', value: 0 });
  assert.equal(parseLength('12em'), null);
});

// ------------------------------------------------------------------- css

test('css: specificity and source order decide the cascade', () => {
  const sheet = parseStylesheet(
    'div { color: #111111 } .a { color: #222222 } #x { color: #333333 } .a { background: #444444 }',
  );
  const el = parseHTML('<div class="a" id="x">t</div>');
  const { style } = computeStyle(el, sheet, null, null, []);
  assert.deepEqual(style.color, [0x33, 0x33, 0x33, 255]); // id wins
  assert.deepEqual(style.background, [0x44, 0x44, 0x44, 255]);
});

test('css: descendant combinator matches ancestors, not siblings', () => {
  const sel = parseSelector('.outer .inner');
  const tree = parseHTML('<div class="outer"><div><div class="inner">x</div></div><div class="inner2">y</div></div>');
  const inner = tree.children[0].children[0];
  assert.equal(selectorMatches(sel, inner), true);
  assert.equal(selectorMatches(sel, tree), false);
});

test('css: bug #1 — padding-top on one element never leaks into the next', () => {
  const sheet = parseStylesheet('.padded { padding-top: 9px }');
  const a = parseHTML('<div class="padded">a</div>');
  const b = parseHTML('<div class="plain">b</div>');
  const sa = computeStyle(a, sheet, null, null, []).style;
  const sb = computeStyle(b, sheet, null, null, []).style;
  assert.deepEqual(sa.padding, [9, 0, 0, 0]);
  assert.deepEqual(sb.padding, [0, 0, 0, 0]);
  assert.deepEqual(INITIAL_STYLE.padding, [0, 0, 0, 0]);
  assert.ok(Object.isFrozen(INITIAL_STYLE.padding), 'initial padding array frozen');
});

test('css: bug #2 — unitless line-height stays a multiplier', () => {
  const sheet = parseStylesheet('p { line-height: 1.3; font-size: 20px }');
  const el = parseHTML('<p>x</p>');
  const { style } = computeStyle(el, sheet, null, null, []);
  assert.deepEqual(style.lineHeight, { unit: 'number', value: 1.3 });
});

test('css: :focus changing geometry is a compile error', () => {
  const sheet = parseStylesheet('.b { width: 40px } .b:focus { width: 60px }');
  const el = parseHTML('<div class="b" focusable>x</div>');
  assert.throws(
    () => computeStyle(el, sheet, null, null, []),
    /paint-only delta/,
  );
});

test('css: :focus paint delta computes a separate focus style', () => {
  const sheet = parseStylesheet('.b { color: #101010 } .b:focus { color: #f0f0f0 }');
  const el = parseHTML('<div class="b" focusable>x</div>');
  const { style, focusStyle, focusDeclared } = computeStyle(el, sheet, null, null, []);
  assert.equal(focusDeclared, true);
  assert.notEqual(style, focusStyle);
  assert.deepEqual(style.color, [16, 16, 16, 255]);
  assert.deepEqual(focusStyle.color, [240, 240, 240, 255]);
});

test('css: :focus compound only matches focusable elements', () => {
  const sel = parseSelector('.tile:focus .title');
  const focusable = parseHTML('<div class="tile" focusable><p class="title">x</p></div>');
  const plain = parseHTML('<div class="tile"><p class="title">x</p></div>');
  assert.equal(selectorMatches(sel, focusable.children[0]), true);
  assert.equal(selectorMatches(sel, plain.children[0]), false);
});

test('css: unknown properties warn instead of erroring', () => {
  const warnings = [];
  const sheet = parseStylesheet('.a { box-shadow: 0 0 4px #000000; color: white }');
  const el = parseHTML('<div class="a">x</div>');
  const { style } = computeStyle(el, sheet, null, null, warnings);
  assert.deepEqual(style.color, [255, 255, 255, 255]);
  assert.match(warnings.join('\n'), /box-shadow/);
});

test('css: inherited vs reset properties', () => {
  const sheet = parseStylesheet('.parent { color: #ababab; background: #123456; font-size: 20px }');
  const parent = parseHTML('<div class="parent"><div class="child">x</div></div>');
  const ps = computeStyle(parent, sheet, null, null, []).style;
  const cs = computeStyle(parent.children[0], sheet, ps, null, []).style;
  assert.deepEqual(cs.color, [0xab, 0xab, 0xab, 255]); // inherits
  assert.equal(cs.fontSize, 20);                        // inherits
  assert.equal(cs.background, null);                    // does not
});

test('css: shorthand box expansion', () => {
  const sheet = parseStylesheet('.a { padding: 1px 2px 3px 4px; margin: 5px 6px }');
  const el = parseHTML('<div class="a">x</div>');
  const { style } = computeStyle(el, sheet, null, null, []);
  assert.deepEqual(style.padding, [1, 2, 3, 4]);
  assert.deepEqual(style.margin, [5, 6, 5, 6]);
});

test('css: at-rules are skipped with a warning, not a parse failure', () => {
  const { rules, warnings } = parseStylesheet('@media screen { .a { color: red } } .b { color: white }');
  assert.equal(rules.length, 1);
  assert.match(warnings[0], /@media/);
});

// ------------------------------------------------------------------ var()
//
// The mechanism P3b's design settled on: a role is the NAME the author
// wrote, not the value it resolves to and not the site it was written at.
// docs/design-p3b-theming.md 9.2 has the argument.

test('var: :root collects custom properties as colors', () => {
  const sheet = parseStylesheet(':root { --panel: #123456; --ring: rgba(1,2,3,0.5) }');
  assert.equal(sheet.vars.get('--panel').rgba.join(','), '18,52,86,255');
  assert.equal(sheet.vars.get('--ring').rgba.join(','), '1,2,3,128');
  // :root is a declaration site, not a selector -- it must not become a
  // rule that something could match.
  assert.equal(sheet.rules.length, 0);
  assert.deepEqual(sheet.warnings, []);
});

test('var: a use site resolves and keeps the name', () => {
  const sheet = parseStylesheet(':root{--ink:#ffeedd}\n.a{color:var(--ink)}');
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  const { style } = computeStyle(el, sheet, INITIAL_STYLE, null, []);
  assert.deepEqual(style.color, [255, 238, 221, 255]);
  assert.equal(style.colorVar, '--ink');
});

test('var: a literal resolves with NO name, which is what keeps it unthemed', () => {
  // The other half of the design: a colour the author did not name is one
  // they did not offer to a theme. It must not acquire a name by accident.
  const sheet = parseStylesheet('.a{color:#ffeedd}');
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  const { style } = computeStyle(el, sheet, INITIAL_STYLE, null, []);
  assert.deepEqual(style.color, [255, 238, 221, 255]);
  assert.equal(style.colorVar, null);
});

test('var: one name across three properties is one role', () => {
  const sheet = parseStylesheet(
    ':root{--x:#102030}\n.a{color:var(--x);background:var(--x);border:1px solid var(--x)}',
  );
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  const { style } = computeStyle(el, sheet, INITIAL_STYLE, null, []);
  assert.equal(style.colorVar, '--x');
  assert.equal(style.backgroundVar, '--x');
  // The border shorthand splits on spaces, so var() has to be recognised
  // there too and not only in `border-color`.
  assert.equal(style.borderColorVar, '--x');
});

test('var: colorVar inherits with color', () => {
  // If it did not, a child would be value-keyed under a role-keyed parent
  // and a theme would recolour the parent and leave the child behind.
  const sheet = parseStylesheet(':root{--ink:#010203}\n.p{color:var(--ink)}');
  const parent = { type: 'element', tag: 'div', classes: ['p'], id: null, children: [] };
  const { style: pStyle } = computeStyle(parent, sheet, INITIAL_STYLE, null, []);
  const child = { type: 'element', tag: 'span', classes: [], id: null, children: [] };
  const { style } = computeStyle(child, sheet, pStyle, null, []);
  assert.deepEqual(style.color, [1, 2, 3, 255]);
  assert.equal(style.colorVar, '--ink');
});

test('var: an undefined name is refused, not silently dropped', () => {
  const sheet = parseStylesheet('.a{color:var(--nope)}');
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  assert.throws(
    () => computeStyle(el, sheet, INITIAL_STYLE, null, []),
    /--nope is not defined in :root/,
  );
});

test('var: a fallback is refused, because a role has one value per theme', () => {
  const sheet = parseStylesheet(':root{--a:#111}\n.a{color:var(--a, #222)}');
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  assert.throws(
    () => computeStyle(el, sheet, INITIAL_STYLE, null, []),
    /has a fallback/,
  );
});

test('var: a non-color custom property is refused at the definition', () => {
  assert.throws(
    () => parseStylesheet(':root{--gap:4px}'),
    /is not a color/,
  );
});

test('var: a custom property outside :root warns and does not define', () => {
  const sheet = parseStylesheet('.a{--panel:#123456}');
  assert.equal(sheet.vars.size, 0);
  assert.match(sheet.warnings.join('\n'), /outside :root is ignored/);
  assert.equal(sheet.warnings.length, 1);
  // AND NO SECOND, WRONG DIAGNOSTIC. The declaration still reaches
  // applyDeclaration during computeStyle, where the default branch would
  // call it "not supported on this target" -- true of no custom property
  // and confusing next to the accurate warning above. Checked on the
  // array computeStyle writes to, which is a DIFFERENT array from the
  // sheet's: asserting only on sheet.warnings would have proved nothing
  // about the path that produces the duplicate.
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  const runtimeWarnings = [];
  computeStyle(el, sheet, INITIAL_STYLE, null, runtimeWarnings);
  assert.deepEqual(runtimeWarnings, []);
});

test('var: ordinary declarations inside :root warn rather than apply', () => {
  const sheet = parseStylesheet(':root{color:#fff;--a:#111}');
  assert.match(sheet.warnings.join('\n'), /:root \{ color: \.\.\. \}" is ignored/);
  assert.equal(sheet.vars.size, 1);
});
