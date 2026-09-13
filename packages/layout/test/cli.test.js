// The two shipped binaries answer `--version`, and answer with the
// manifest's version rather than a literal of their own.
//
// WHY THIS EXISTS. Every version claim in the repository agrees with
// every other one (tools/check-versions.py), and for a long while none
// of them was reachable from the command a person actually runs -- the
// one place someone filing a bug would look. Adding the flag creates
// the obvious next hazard: a hardcoded string in the bin that starts
// out right and drifts, which is the whole failure this project keeps
// finding. So the bins read package.json, and this spawns them for
// real and compares.

import test from 'node:test';
import assert from 'node:assert/strict';

import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const pkg = JSON.parse(
  readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const bin = (name) => fileURLToPath(new URL(`../bin/${name}`, import.meta.url));

for (const [name, prog] of [['ps2ui-layout.js', 'ps2ui-layout'],
                            ['ps2ui-dev.js', 'ps2ui-dev']]) {
  test(`${prog} --version prints the manifest version`, () => {
    for (const flag of ['--version', '-V']) {
      const out = execFileSync(process.execPath, [bin(name), flag],
                               { encoding: 'utf8' });
      assert.equal(out.trim(), `${prog} ${pkg.version}`);
    }
  });
}

test('the manifest version is the only version either bin knows', () => {
  // A literal that HAPPENS to equal the manifest today passes the test
  // above and drifts tomorrow, so the source is read as well as the
  // behaviour: neither bin may spell a version out.
  for (const name of ['ps2ui-layout.js', 'ps2ui-dev.js']) {
    const src = readFileSync(bin(name), 'utf8');
    // A version inside a message is still a version: anchoring the
    // digits to the quote let `'ps2ui-layout 0.2.0'` slide past.
    const literals = src.match(/["'`][^"'`\n]*\d+\.\d+\.\d+[^"'`\n]*["'`]/g) || [];
    assert.deepEqual(literals, [],
      `${name} spells out a version: ${literals.join(', ')}`);
  }
});

// ps2ui-dev's --strict and --min-font-size reach the linter. Both were
// accepted and inert for a release: the bin set options.strict and
// options.minFontSize, compile() reads lint overrides from options.lint
// only, and `ps2ui dev` forwarded a project's strict and minFontSize
// into that dead path. Run for real, on a page whose only warning is a
// font-size one; --strict fails before the bake, so no Python is needed.
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

test('ps2ui-dev --strict fails on warnings and --min-font-size moves the floor', () => {
  const dir = mkdtempSync(join(tmpdir(), 'ps2ui-dev-'));
  const html = join(dir, 'page.html');
  const css = join(dir, 'page.css');
  writeFileSync(html,
    '<screen><div class="box"><p class="small">tiny text</p></div></screen>\n');
  writeFileSync(css,
    'screen { background: #000000; flex-direction: column; }\n'
    + '.box { margin: 60px; padding: 20px; background: #000000; }\n'
    + '.small { font-size: 8px; color: #ffffff; }\n');
  const fontDir = fileURLToPath(new URL('../../../fonts', import.meta.url));
  const run = (...extra) => {
    const r = spawnSync(process.execPath,
      [bin('ps2ui-dev.js'), html, css, '-o', join(dir, 'out'),
       '--font-dir', fontDir, '--once', ...extra],
      { encoding: 'utf8' });
    return { status: r.status, err: r.stderr.replace(/\x1b\[[0-9;]*m/g, '') };
  };

  const strict = run('--strict');
  assert.equal(strict.status, 1, strict.err);
  assert.match(strict.err, /is 8px; below 14px/);
  assert.match(strict.err, /--strict: 1 warning\(s\)/);

  const floor = run('--strict', '--min-font-size', '11');
  assert.equal(floor.status, 1, floor.err);
  assert.match(floor.err, /is 8px; below 11px/);
  assert.doesNotMatch(floor.err, /below 14px/);

  const bad = run('--min-font-size', '0');
  assert.equal(bad.status, 2, bad.err);
  assert.match(bad.err, /positive integer/);
});
