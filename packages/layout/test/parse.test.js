// Parser-level tests: HTML tree building, CSS cascade, value parsing.

import test from 'node:test';
import assert from 'node:assert/strict';

import { parseHTML } from '../src/html.js';
import {
  parseStylesheet, computeStyle, INITIAL_STYLE, parseSelector, selectorMatches,
  applyDeclaration,
} from '../src/css.js';
import { parseColor, parseLength } from '../src/values.js';
import { compile, FontContext } from '../src/index.js';

const fonts = FontContext.fromDir();

/** The error a call threw. `assert.throws` returns nothing, and these
 * tests are about the error's contents rather than its message alone. */
function thrown(fn) {
  try { fn(); } catch (e) { return e; }
  return assert.fail('expected a throw, got none');
}

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

test('css: every value the keyword table accepts actually compiles', () => {
  // THE INVERSE BUG, AND THE REASON THIS TEST IS FIRST. A validator is
  // a list of strings, and a typo in the list rejects valid CSS -- the
  // failure the eight properties below could not have before, bought
  // with the one they could. So the table is driven against the parser
  // rather than eyeballed: every value it claims to take is compiled.
  const OK = {
    'flex-direction': ['row', 'row-reverse', 'column', 'column-reverse'],
    'flex-wrap': ['nowrap', 'wrap', 'wrap-reverse'],
    'justify-content': ['flex-start', 'flex-end', 'center', 'space-between',
                        'space-around'],
    'align-items': ['flex-start', 'flex-end', 'center', 'stretch'],
    'align-self': ['auto', 'flex-start', 'flex-end', 'center', 'stretch'],
    'text-align': ['left', 'center', 'right'],
    'white-space': ['normal', 'nowrap'],
    'text-overflow': ['clip', 'ellipsis'],
  };
  let n = 0;
  for (const [prop, values] of Object.entries(OK)) {
    for (const v of values) {
      const warnings = [];
      assert.doesNotThrow(
        () => {
          const sheet = parseStylesheet(`.a { ${prop}: ${v} }`);
          computeStyle(parseHTML('<div class="a">x</div>'), sheet, null, null,
                       warnings);
        },
        `${prop}: ${v} is in the accepted set and did not compile`,
      );
      // ...and it is APPLIED, not merely tolerated: a property that
      // stopped reaching the style object would pass the line above.
      assert.equal(warnings.length, 0, `${prop}: ${v} warned: ${warnings}`);
      n++;
    }
  }
  assert.equal(n, 28, 'the accepted sets changed size; update this count');
});

test('css: a misspelled keyword is an error, not a different layout', () => {
  // EVERY ONE OF THE EIGHT, because this defect was invisible property
  // by property: each consumer ends in a `default:` meaning "the
  // initial value", so a typo fell through to a DIFFERENT LAYOUT at
  // exit 0 rather than to an error. Testing one would say nothing
  // about the other seven, which is how `flex-wrap` stayed broken
  // while `flex-direction` was being looked at.
  const TYPOS = {
    'flex-direction': 'rows',
    'flex-wrap': 'wrapp',
    'justify-content': 'space_between',
    'align-items': 'centre',
    'align-self': 'strech',
    'text-align': 'centre',
    'white-space': 'no-wrap',
    'text-overflow': 'elipsis',
  };
  for (const [prop, bad] of Object.entries(TYPOS)) {
    assert.throws(
      () => {
        const sheet = parseStylesheet(`.a { ${prop}: ${bad} }`);
        computeStyle(parseHTML('<div class="a">x</div>'), sheet, null, null, []);
      },
      (err) => {
        assert.match(err.message, new RegExp(`${prop}: unknown value "${bad}"`));
        // The remedy is in the message: a reader who misspelled a
        // value needs the spelling, and an error that only says "no"
        // sends them to the source.
        assert.match(err.message, new RegExp(`${prop} takes `));
        return true;
      },
      `${prop}: ${bad} did not throw`,
    );
  }
});

test('css: real CSS this target lacks says so, and says what it would have done', () => {
  // A DIFFERENT FACT FROM A TYPO, and only one of the two is the
  // author's mistake. `baseline` is not misspelled; it is absent. The
  // message names the layout the value would silently have produced,
  // because that is the thing the author was about to not notice.
  const CASES = [
    ['justify-content', 'space-evenly', /packed from main-start/],
    ['align-items', 'baseline', /aligned to cross-start/],
    ['align-self', 'baseline', /aligned to cross-start/],
    ['text-align', 'justify', /left-aligned/],
    ['white-space', 'pre', /wrapped like normal/],
    ['white-space', 'pre-wrap', /wrapped like normal/],
    ['white-space', 'pre-line', /wrapped like normal/],
    ['white-space', 'break-spaces', /wrapped like normal/],
  ];
  for (const [prop, value, consequence] of CASES) {
    assert.throws(
      () => {
        const sheet = parseStylesheet(`.a { ${prop}: ${value} }`);
        computeStyle(parseHTML('<div class="a">x</div>'), sheet, null, null, []);
      },
      (err) => {
        assert.match(err.message, /is real CSS that this target does not implement/);
        assert.match(err.message, consequence);
        assert.doesNotMatch(err.message, /unknown value/,
                            `${prop}: ${value} was reported as a typo`);
        return true;
      },
      `${prop}: ${value} did not throw`,
    );
  }
});

test('css: a bad flex-direction no longer satisfies the must-declare check', () => {
  // THE FENCE THIS TYPO USED TO DEFEAT. box.js requires every
  // multi-child container to state flex-direction, and asks whether a
  // declaration EXISTS, not whether its value parses -- so
  // `flex-direction: rows` set flexDirectionDeclared, passed the one
  // check over this family, and laid out as a column. Validating
  // before the flag is set is what closes it, so the flag must still
  // be false after the throw.
  const style = { ...INITIAL_STYLE };
  assert.throws(() => applyDeclaration(style, 'flex-direction', 'rows', 1, [], null));
  assert.equal(style.flexDirectionDeclared, false,
               'a refused value still marked the direction as declared');
  assert.equal(style.flexDirection, INITIAL_STYLE.flexDirection,
               'a refused value reached the style object');

  // And the accepted spelling still does set it.
  const good = { ...INITIAL_STYLE };
  applyDeclaration(good, 'flex-direction', 'row', 1, [], null);
  assert.equal(good.flexDirectionDeclared, true);
  assert.equal(good.flexDirection, 'row');
});

test('css: :focus may not set a property that is read from the base style', () => {
  // A DIFFERENT DEFECT FROM GEOMETRY, AND A DIFFERENT MESSAGE. These
  // three ask for nothing impossible: they are simply never read on the
  // focus side, so the declaration parsed, applied to focusStyle, and
  // vanished. No error, no warning, no effect -- the worst of the three
  // outcomes a value can have.
  for (const prop of ['letter-spacing', 'text-align', 'text-overflow']) {
    const value = prop === 'letter-spacing' ? '2px'
      : prop === 'text-align' ? 'right' : 'ellipsis';
    assert.throws(
      () => {
        const sheet = parseStylesheet(`.a:focus { ${prop}: ${value} }`);
        const el = parseHTML('<div class="a" focusable>x</div>');
        computeStyle(el, sheet, null, null, []);
      },
      (err) => {
        assert.match(err.message, new RegExp(`:focus may not change "${prop}"`));
        // Not the geometry wording: these are not two-layout requests,
        // and telling the author to "move the geometry" would send them
        // looking for geometry they never wrote.
        assert.match(err.message, /read from the base style/);
        assert.doesNotMatch(err.message, /paint-only delta/);
        return true;
      },
      `${prop} under :focus did not throw`,
    );
  }
});

test('css: :focus may still change font-weight, which is measured for', () => {
  // THE ONE THAT STAYS. Bolding the focused row is the most ordinary
  // thing a console UI does, and the guard's principle -- one baked
  // layout for both states -- is satisfied by sizing that layout for
  // the heavier face rather than by forbidding the lighter one. The
  // measurement half is in layout.test.js; this pins that it is not an
  // error, so a later tightening cannot quietly take it away.
  const sheet = parseStylesheet('.a:focus { font-weight: bold }');
  const el = parseHTML('<div class="a" focusable>x</div>');
  const { focusStyle } = computeStyle(el, sheet, null, null, []);
  assert.equal(focusStyle.fontWeight, 700);
});

test('css: a :focus rule that can never apply is a warning, not silence', () => {
  // THE WARNING THAT EXISTED AND COULD NOT FIRE. box.js asked
  // `focusDeclared && scope === null`, and those cannot both hold --
  // compoundMatches drops the rule upstream, so focusDeclared is false
  // exactly when scope is null. Asking there asked at the one place
  // that can no longer tell. Here the failed match is still in hand.
  //
  // Both selector shapes, because they fail in different places: the
  // rightmost compound for `.panel:focus`, the ancestor walk for
  // `.tile:focus .title`.
  const sheet = parseStylesheet(
    '.panel:focus { color: red } .tile:focus .title { color: red }',
  );
  const root = parseHTML(
    '<div><div class="panel">a</div><div class="panel">b</div>'
    + '<div class="tile"><div class="title">c</div></div></div>',
  );
  const warnings = [];
  const walk = (el, parent) => {
    if (el.type !== 'element') return;
    computeStyle(el, sheet, parent, null, warnings);
    for (const c of el.children) walk(c, null);
  };
  walk(root, null);

  const dead = warnings.filter((w) => /can never show/.test(w));
  assert.equal(dead.length, 2,
               `expected one warning per rule, got ${dead.length}: ${dead}`);
  assert.ok(dead.some((w) => w.includes('.panel:focus')));
  assert.ok(dead.some((w) => w.includes('.tile:focus .title')));
  // Keyed on the rule, not the element: two .panel elements, one
  // mistake. A per-element warning would print this twice.
  assert.equal(dead.filter((w) => w.includes('.panel:focus')).length, 1);
  // And the remedy, since a warning that only says "no" sends the
  // reader to the source.
  assert.ok(dead.every((w) => /focusable/.test(w)));
});

test('css: a :focus rule that CAN apply warns about nothing', () => {
  // The false-positive half. Without this the warning above passes by
  // firing on everything, which is the same bug one direction over.
  const sheet = parseStylesheet('.panel:focus { color: red }');
  const el = parseHTML('<div class="panel" focusable>a</div>');
  const warnings = [];
  computeStyle(el, sheet, null, null, warnings);
  assert.deepEqual(warnings.filter((w) => /can never show/.test(w)), []);
});

test('css: a :focus rule for some other element is not this one\'s problem', () => {
  // THE HOLE THE FIRST DRAFT LEFT, found by sabotage rather than by
  // reading. Relaxing the condition to "any :focus rule that did not
  // match" passed every test above: the positive one still counted two
  // warnings, because they are deduped per rule, and the one below it
  // used a rule that DOES match and so never reached the branch at all.
  //
  // The claim is narrow and has to be tested narrowly: warn only when
  // the missing `focusable` attribute is the ONLY reason the rule did
  // not match. A rule naming a class this element does not carry is an
  // ordinary non-match and must stay silent, or every sheet warns
  // about every focusable rule in it.
  const sheet = parseStylesheet('.somewhere-else:focus { color: red }');
  const el = parseHTML('<div class="panel">a</div>');
  const warnings = [];
  computeStyle(el, sheet, null, null, warnings);
  assert.deepEqual(warnings.filter((w) => /can never show/.test(w)), [],
                   'warned about a :focus rule that never named this element');
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

// ---------------------------------------------------------------- @theme
//
// P3b-4. A theme is a second value for every name, and the shape that
// makes it safe is that a use site gets back the WHOLE VECTOR rather
// than a resolved colour: every fold downstream runs over all rows at
// once, so no code path can move one theme's value and not another's.

test('@theme: a use site gets one colour per theme, root first', () => {
  const sheet = parseStylesheet(
    ':root{--panel:#112233}\n@theme light{--panel:#eeddcc}\n'
    + '.a{background:var(--panel)}',
  );
  assert.deepEqual(sheet.themeNames, ['root', 'light']);
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  const { style } = computeStyle(el, sheet, INITIAL_STYLE, null, []);
  assert.deepEqual(style.background, [17, 34, 51, 255]);
  assert.deepEqual(style.backgroundThemes, [
    [17, 34, 51, 255], [238, 221, 204, 255],
  ]);
});

test('@theme: a literal gets a full-width vector of itself', () => {
  // Not a shorter vector and not null. One shape for one concept, or a
  // consumer ends up handling only the shape it was written against.
  const sheet = parseStylesheet(
    ':root{--x:#111111}\n@theme light{--x:#eeeeee}\n.a{background:#0a0b0c}',
  );
  const el = { type: 'element', tag: 'div', classes: ['a'], id: null, children: [] };
  const { style } = computeStyle(el, sheet, INITIAL_STYLE, null, []);
  assert.equal(style.backgroundVar, null);
  assert.deepEqual(style.backgroundThemes, [[10, 11, 12, 255], [10, 11, 12, 255]]);
});

test('@theme: a theme that omits a key says so', () => {
  const sheet = parseStylesheet(
    ':root{--a:#111;--b:#222}\n@theme light{--a:#eee}',
  );
  assert.equal(sheet.warnings.length, 1);
  assert.match(sheet.warnings[0], /@theme light does not set --b/);
  // And it keeps :root's value rather than becoming undefined.
  assert.deepEqual(sheet.vars.get('--b').themes, [[34, 34, 34, 255], [34, 34, 34, 255]]);
});

test('@theme: a name :root does not define is refused', () => {
  // It could never be drawn: a use site only reaches a name through
  // :root, so this is a theme value with nothing to apply it to.
  assert.throws(
    () => parseStylesheet(':root{--a:#111}\n@theme light{--b:#222}'),
    /@theme light defines --b, which :root does not/,
  );
});

test('@theme: a duplicate theme name is refused', () => {
  assert.throws(
    () => parseStylesheet(':root{--a:#111}\n@theme light{--a:#222}\n@theme light{--a:#333}'),
    /@theme light is declared twice/,
  );
});

test('@theme: a theme cannot set anything but a custom property', () => {
  assert.throws(
    () => parseStylesheet(':root{--a:#111}\n@theme light{padding:4px}'),
    /a theme supplies custom properties and nothing else/,
  );
});

test('@theme: a sheet with no @theme has exactly one theme', () => {
  const sheet = parseStylesheet(':root{--a:#111}\n.a{color:var(--a)}');
  assert.deepEqual(sheet.themeNames, ['root']);
  assert.deepEqual(sheet.vars.get('--a').themes, [[17, 17, 17, 255]]);
});

test('@theme: a bare literal warns, but only once a theme exists', () => {
  // A literal is a legitimate choice -- the author declining to offer a
  // colour to a theme -- so this must not fire on an unthemed sheet, or
  // it is a permanent false alarm on every stylesheet in the repo.
  const unthemed = parseStylesheet(':root{--a:#111}\n.x{color:#8b94a7}');
  assert.equal(unthemed.warnings.filter((w) => w.includes('literal')).length, 0);

  const themed = parseStylesheet(
    ':root{--a:#111}\n@theme light{--a:#eee}\n'
    + '.x{color:#8b94a7;border:2px solid #202839}',
  );
  const lit = themed.warnings.filter((w) => w.includes('is a literal'));
  assert.equal(lit.length, 2, 'the colour AND the border shorthand token');
  assert.ok(lit.every((w) => w.includes('line 3')));
});

test('@theme: one warning per authored line, not per matching element', () => {
  // computeStyle runs applyDeclaration once per matching element, so a
  // rule matching twelve rows would warn twelve times about one line.
  // Emitted from parseStylesheet for exactly that reason.
  const sheet = parseStylesheet(
    ':root{--a:#111}\n@theme light{--a:#eee}\n.row{background:#101623}',
  );
  assert.equal(sheet.warnings.filter((w) => w.includes('is a literal')).length, 1);
});

test('@theme: the border shorthand finds a colour with spaces inside its parens', () => {
  // `d.value.split(/\s+/)` tore `rgb(255, 0, 0)` into three fragments,
  // none of which parse as a colour -- so the canonical spelling of the
  // one notation people write by hand was the single form that escaped
  // this warning. `rgb(255,0,0)` warned; the same colour with spaces
  // did not, and the border painted red either way.
  const spellings = ['#ff0000', 'red', 'rgb(255,0,0)', 'rgb(255, 0, 0)'];
  for (const c of spellings) {
    const sheet = parseStylesheet(
      `:root{--a:#111}\n@theme light{--a:#eee}\n.x{border:2px solid ${c}}`);
    const lit = sheet.warnings.filter((w) => w.includes('is a literal'));
    assert.equal(lit.length, 1, `border: 2px solid ${c} should warn`);
    assert.ok(lit[0].includes(c), `the warning should name ${c}`);
  }
});

// ------------------------------------------------- every error in one pass

test('css: a sheet with three mistakes reports three, in line order', () => {
  // THE ROW THIS CLOSES, IN ITS OWN FIXTURE. A stylesheet carrying a
  // gradient, a `:hover` and a `display: grid` took THREE builds to
  // clear: each reported one error and stopped, so a normal sheet was
  // a build-fix-build loop (F37a). The compiler reaches all three in
  // one pass now -- the gradient and the grid through computeStyle's
  // sink, the selector by skipping the rule it heads, which could not
  // have applied to anything anyway.
  const css = [
    '.card {',                                  // 1
    '  width: 200px;',                          // 2
    '  background: linear-gradient(#fff,#000);',  // 3
    '}',                                        // 4
    '.card:hover {',                            // 5
    '  color: #f00;',                           // 6
    '}',                                        // 7
    '.label {',                                 // 8
    '  display: grid;',                         // 9
    '}',                                        // 10
  ].join('\n');
  const err = thrown(() => compile(
    '<div class="card"><span class="label">x</span></div>', css, { fonts }));
  assert.equal(err.cssErrors.length, 3, err.message);
  assert.deepEqual(err.cssErrors.map((m) => /^css: line (\d+):/.exec(m)[1]),
                   ['3', '5', '9']);
  assert.match(err.cssErrors[0], /background: bad color/);
  assert.match(err.cssErrors[1], /:focus is the only pseudo-class/);
  assert.match(err.cssErrors[2], /display: only "flex" and "none"/);
  // And `message` carries all of it, for a caller that knows nothing
  // about the `cssErrors` property.
  assert.equal(err.message, err.cssErrors.join('\n'));
});

test('css: the same mistake on twenty elements is reported once', () => {
  const html = `<div>${'<span class="t">x</span>'.repeat(20)}</div>`;
  const err = thrown(() => compile(html, '.t { display: grid }', { fonts }));
  assert.equal(err.cssErrors.length, 1);
});

test('css: a layout refusal with a clean sink is not dressed as a CSS error', () => {
  // WHAT THIS DOES AND DOES NOT FENCE. The compile wraps a crash in
  // the collected CSS errors only when there ARE some, because a tree
  // built from declarations that were recorded and not applied can
  // fail in its own right and the CSS is then the cause. With a clean
  // sink the failure is its own, and this is that half.
  //
  // The other half -- that the sink takes `css: ` messages only -- is
  // the test below it.
  const err = thrown(() => compile(
    '<div style="x"></div>', 'div { display: none }', { fonts }));
  assert.equal(err.cssErrors, undefined);
  assert.match(err.message, /^layout: root element is display: none/);
});

test('css: a crash inside the property code is not reported as bad CSS', () => {
  // THE SINK TAKES `css: ` MESSAGES AND NOTHING ELSE. Everything
  // applyDeclaration raises about a stylesheet begins that way, so a
  // TypeError out of it is a defect in the compiler -- and collecting
  // it would print a crash as `error: css: ...`, telling the author
  // their sheet is wrong when it is not, with no stack to debug from.
  //
  // Nothing a stylesheet can SAY reaches that branch: every value the
  // parser produces is a string, and the property code stringifies
  // whatever it does not recognise. So the declaration is built by
  // hand, which is the shape only a bug in the parser could hand it.
  const sheet = parseStylesheet('.b { color: #fff }');
  sheet.rules[0].declarations = [
    { prop: 'width', value: Object.create(null), line: 1 },
  ];
  const el = parseHTML('<div class="b">x</div>');
  const errs = [];
  const err = thrown(() => computeStyle(el, sheet, null, null, [], errs));
  assert.equal(err.constructor.name, 'TypeError');
  assert.deepEqual(errs, []);
});

test('css: computeStyle with no sink still throws on the first', () => {
  // Every caller outside the compiler keeps the old contract, which is
  // what makes the sink an addition rather than a rewrite: the sink is
  // opt-in and `parse.test.js` above calls computeStyle without one.
  const sheet = parseStylesheet('.b { display: grid; color: nonsense }');
  const el = parseHTML('<div class="b">x</div>');
  assert.throws(() => computeStyle(el, sheet, null, null, []),
                /display: only "flex" and "none"/);
});

// ------------------------------------------------ the line of a declaration

test('css: a declaration is reported at its own line, not the rule\'s', () => {
  // `background` is physically on line 5 and reported line 1, the line
  // `.card {` opens on, because every declaration was stamped with the
  // RULE's line. In a two-line rule that is a near miss; in a fifteen-
  // line rule it sends the reader to the wrong end of it (F37b).
  const css = '.card {\n  width: 200px;\n  height: 100px;\n'
            + '  padding: 4px;\n  background: linear-gradient(#fff,#000);\n}';
  const err = thrown(() => compile('<div class="card">x</div>', css, { fonts }));
  assert.match(err.cssErrors[0], /^css: line 5: background: bad color/);
});

test('css: a comment inside a rule does not shift the lines under it', () => {
  // THE CASE THAT RULES OUT COUNTING NEWLINES IN THE BODY. The reader
  // SKIPS a comment rather than keeping it, so the body string is
  // three lines shorter than the file and every declaration under the
  // comment would be reported three lines high. The line is recorded
  // per character as the body is read instead.
  const css = '.card {\n  width: 200px;\n  /* one\n     two\n     three */\n'
            + '  display: grid;\n}';
  const err = thrown(() => compile('<div class="card">x</div>', css, { fonts }));
  assert.match(err.cssErrors[0], /^css: line 6: display:/);
});

// ------------------------------------------------------- the pseudo-class

test('css: an unsupported pseudo-class names the one that exists', () => {
  // The old message was `unsupported selector syntax near ":"`, which
  // is true of the character and silent about the mistake: the reader
  // wrote a state this target does not have, and no punctuation fixes
  // that. It also carried no line, alone among the CSS errors (F37c).
  const err = thrown(() => compile(
    '<div class="card">x</div>', '.a { color: #fff }\n.card:hover { color: #f00 }',
    { fonts }));
  const msg = err.cssErrors[0];
  assert.match(msg, /^css: line 2: /);
  assert.match(msg, /:hover does not exist on this target/);
  assert.match(msg, /:focus is the only pseudo-class/);
  // The selector it was written in, so a long sheet says which one.
  assert.match(msg, /"\.card:hover"/);
});

test('css: a bad selector drops its rule and the pass continues', () => {
  // The rule could not have applied to anything, so skipping it loses
  // nothing -- and it is what lets the declarations BELOW it be
  // reached in the same pass. Structural failures are not recoverable
  // this way and still stop the parse.
  assert.throws(() => parseStylesheet('.a { color: #fff'), /unterminated block/);
  const errs = [];
  const sheet = parseStylesheet('.a:hover { color: #fff }\n.b { color: #000 }', errs);
  assert.equal(errs.length, 1);
  assert.equal(sheet.rules.length, 1);
  assert.equal(sheet.rules[0].selector.source, '.b');
});
