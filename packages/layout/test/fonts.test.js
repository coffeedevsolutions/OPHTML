// The font surface a stranger meets: one manifest for both tools, and
// an error that says what to do when the metrics are not there.
//
// WHY THIS EXISTS. `DEFAULT_FONT_DIR` was three levels up from
// `src/`, which is the repository root in a checkout and nothing at
// all in an installed package. Phase 4's exit gate is "a stranger with
// npm, pip and a TTF", and that stranger met a bare ENOENT on a path
// pointing outside the package they installed. Nobody here could see
// it, because in a checkout the path resolves.
//
// It was found by writing the tutorial and running the first command.

import test from 'node:test';
import assert from 'node:assert/strict';

import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync }
  from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { FontContext, compile } from '../src/index.js';

const REPO_FONTS = fileURLToPath(new URL('../../../fonts', import.meta.url));
const BIN = fileURLToPath(new URL('../bin/ps2ui-layout.js', import.meta.url));

function scratch() {
  return mkdtempSync(join(tmpdir(), 'ps2ui-fonts-'));
}

test('a fonts.json manifest loads the same faces as the directory', () => {
  const dir = scratch();
  writeFileSync(join(dir, 'fonts.json'), JSON.stringify({
    regular: { ttf: ['/nonexistent.ttf'],
               metrics: join(REPO_FONTS, 'default.metrics.json') },
    bold: { ttf: ['/nonexistent.ttf'],
            metrics: join(REPO_FONTS, 'default-bold.metrics.json') },
  }));
  const viaManifest = FontContext.fromManifest(join(dir, 'fonts.json'));
  const viaDir = FontContext.fromDir(REPO_FONTS);
  // `ttf` is deliberately bogus: only the baker rasterizes, so the
  // layout half must not care whether the TTF is even there.
  for (const w of [400, 700]) {
    const a = viaManifest.resolve(w), b = viaDir.resolve(w);
    assert.equal(a.weight, b.weight);
    assert.equal(a.family, b.family);
    // Compared over the whole advance table, not one letter: two faces
    // agreeing on 'A' and nowhere else is exactly the divergence two
    // font configurations for one set of fonts used to permit.
    assert.deepEqual(a.advances, b.advances);
    assert.deepEqual(a.kerning, b.kerning);
  }
});

test('a manifest missing a face names ps2ui-fontgen and the weight', () => {
  const dir = scratch();
  writeFileSync(join(dir, 'fonts.json'), JSON.stringify({
    regular: { metrics: join(REPO_FONTS, 'default.metrics.json') },
  }));
  assert.throws(() => FontContext.fromManifest(join(dir, 'fonts.json')),
    (e) => /no "bold" face/.test(e.message)
        && /ps2ui-fontgen/.test(e.message)
        && /700/.test(e.message));
});

test('missing metrics say what to generate, not ENOENT', () => {
  // The failure the exit gate's stranger would have met. It must name
  // both filenames, the generator, and both ways to point at them.
  assert.throws(() => FontContext.fromDir(join(scratch(), 'absent')),
    (e) => /default\.metrics\.json/.test(e.message)
        && /default-bold\.metrics\.json/.test(e.message)
        && /ps2ui-fontgen/.test(e.message)
        && /--font-dir/.test(e.message)
        && /--fonts/.test(e.message));
});

test('-o creates its output directory', () => {
  // The first command in the tutorial, and it failed with an ENOENT
  // naming the OUTPUT path -- which reads as a missing input. Every
  // build.sh mkdir -p's first, so the scripts hid it.
  const dir = scratch();
  writeFileSync(join(dir, 'p.html'), '<screen name="s"><div>Hi</div></screen>');
  writeFileSync(join(dir, 'p.css'), 'div { color: #fff; }');
  const out = join(dir, 'deep', 'nested', 'ui.json');
  execFileSync(process.execPath,
    [BIN, join(dir, 'p.html'), join(dir, 'p.css'), '-o', out,
     '--font-dir', REPO_FONTS], { encoding: 'utf8', stdio: 'pipe' });
  assert.ok(existsSync(out), 'ps2ui-layout did not create build/');
  assert.equal(JSON.parse(readFileSync(out, 'utf8')).version, 1);
});

// ---------------------------------------------------------------------
// A `data-` typo is SILENT: the parser keeps the attribute, nothing
// reads it, the document compiles. Two were made writing the tutorial.

const fonts = FontContext.fromDir(REPO_FONTS);
const compileDoc = (html) => compile(html,
  'screen { display: flex; flex-direction: column; }\n'
  + '.r { color: #fff; background: #000; }\n'
  + '.cover { width: 16px; height: 16px; }', { fonts });

test('an unknown data- attribute is warned about, not swallowed', () => {
  // data-focus="x" for `focusable`: the document compiled with ZERO
  // focusables and no navigation at all, silently.
  const ir = compileDoc(
    '<screen name="s"><div class="r" data-focus="row">Hi</div></screen>');
  const w = ir.warnings.filter((x) => /unknown attribute/.test(x));
  assert.equal(w.length, 1, ir.warnings.join('\n'));
  assert.match(w[0], /data-focus is not read by anything/);
  assert.match(w[0], /line 1/);
  // No confident guess here: the answer is the `focusable` attribute,
  // not a data- one, so it lists what it knows instead.
  assert.match(w[0], /known: /);
});

test('a near miss names the attribute that was meant', () => {
  // data-capacity for data-slot-capacity, five edits apart. Compared
  // past the shared prefix on a WORD boundary, it is unambiguous.
  for (const [typo, meant] of [
    ['data-capacity', 'data-slot-capacity'],
    ['data-slotcapacity', 'data-slot-capacity'],
    ['data-tex', 'data-tex-slot'],
    ['data-reepat', 'data-repeat'],
    ['data-keeping', 'data-keep'],
  ]) {
    const ir = compileDoc(
      `<screen name="s"><div class="r" ${typo}="1">Hi</div></screen>`);
    const w = ir.warnings.find((x) => /unknown attribute/.test(x));
    assert.ok(w, `${typo}: no warning`);
    assert.match(w, new RegExp(`did you mean ${meant}\\?`),
      `${typo}: got ${w}`);
  }
});

test('a typo inside a repeat warns once, not once per row', () => {
  // data-repeat copies the element before the check runs, so six rows
  // meant six identical warnings with the same line number.
  const ir = compileDoc(
    '<screen name="s"><div class="r" data-repeat="6" id="r-{i}" '
    + 'data-capacity="8">Hi</div></screen>');
  assert.equal(
    ir.warnings.filter((x) => /unknown attribute/.test(x)).length, 1,
    ir.warnings.join('\n'));
});

test('every attribute the compiler acts on is exempt', () => {
  // The set has to track the code. A `data-` attribute that IS read
  // and is not listed would warn on every correct document.
  const ir = compileDoc(
    '<screen name="s">'
    + '<div class="r" data-repeat="2" id="r-{i}" data-keep data-nocontrast>'
    + '<span class="r" data-slot="s-{i}" data-slot-capacity="8">x</span>'
    + '</div>'
    + '<img class="cover" data-tex-slot="cover">'
    + '</screen>');
  assert.deepEqual(ir.warnings.filter((x) => /unknown attribute/.test(x)), []);
});

