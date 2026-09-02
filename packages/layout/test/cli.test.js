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
