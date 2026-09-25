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

test('the bins print every CSS error, one `error: ` line each', () => {
  // THE LAST STEP OF THE ONE-PASS CHANGE IS THE ONE A READER SEES.
  // compile() carries the whole list on `err.cssErrors`; a bin that
  // printed `err.message` alone would still show all of it, and a bin
  // that printed its first line would silently put the loop back. Both
  // are spawned for real, because the printing is the bin's and a
  // library-level test cannot see it.
  const dir = mkdtempSync(join(tmpdir(), 'ps2ui-css-errors-'));
  const html = join(dir, 'page.html');
  const css = join(dir, 'page.css');
  writeFileSync(html, '<screen><div class="card">'
    + '<span class="label">x</span></div></screen>\n');
  writeFileSync(css, [
    'screen { background: #000000; }',        // 1
    '.card {',                                // 2
    '  background: linear-gradient(#fff,#000);',  // 3
    '}',                                      // 4
    '.card:hover {',                          // 5
    '  color: #f00;',                         // 6
    '}',                                      // 7
    '.label {',                               // 8
    '  display: grid;',                       // 9
    '}',                                      // 10
  ].join('\n'));
  const fontDir = fileURLToPath(new URL('../../../fonts', import.meta.url));

  for (const [name, prefix] of [['ps2ui-layout.js', 'error: '],
                                ['ps2ui-dev.js', 'layout error: ']]) {
    const out = join(dir, name === 'ps2ui-dev.js' ? 'out' : 'out.json');
    const r = spawnSync(process.execPath,
      [bin(name), html, css, '-o', out, '--font-dir', fontDir,
       ...(name === 'ps2ui-dev.js' ? ['--once'] : [])],
      { encoding: 'utf8' });
    const err = r.stderr.replace(/\x1b\[[0-9;]*m/g, '');
    assert.equal(r.status, 1, err);
    const lines = err.split('\n').filter((l) => l.startsWith(prefix));
    assert.equal(lines.length, 3, err);
    assert.match(lines[0], /line 3: background: bad color/);
    assert.match(lines[1], /line 5: .*:focus is the only pseudo-class/);
    assert.match(lines[2], /line 9: display: only "flex" and "none"/);
  }
});


test('both bins screen --limit the same way, and answer with exit 2', () => {
  // TWO FINDINGS FROM REVIEW OF #166, AND THEY ARE THE SAME FINDING.
  //
  // `ps2ui-layout --limit noodles=5` printed
  // `error: limits: unknown limit "noodles"` and exited 1: the name
  // was never screened here, so it fell through to resolveLimits and
  // reached the terminal through the generic handler, while
  // `--limit depth=0` one line away exited 2. diagnostics.cli.usage
  // says this family answers a malformed command line with exit 2 and
  // no `error:` prefix, and a misspelt cap was the one argument in
  // either bin that did neither.
  //
  // `ps2ui-dev` did not take `--limit` at all, so the flag `ps2ui dev`
  // forwards from a project's "limits" object landed in positional and
  // every such project got a bare usage dump. That is the defect that
  // broke `ps2ui check` in this same change, one command over.
  //
  // Both bins now read one parser, and this asserts them TOGETHER
  // rather than once each, so a fix that reaches one of them fails.
  const dir = mkdtempSync(join(tmpdir(), 'ps2ui-limit-'));
  const html = join(dir, 'page.html');
  const css = join(dir, 'page.css');
  writeFileSync(html, '<screen><div class="b">x</div></screen>\n');
  writeFileSync(css,
    'screen { background: #000000; }\n'
    + '.b { width: 200px; height: 60px; color: #ffffff; }\n');
  const fontDir = fileURLToPath(new URL('../../../fonts', import.meta.url));

  for (const [name, prog] of [['ps2ui-layout.js', 'ps2ui-layout'],
                              ['ps2ui-dev.js', 'ps2ui-dev']]) {
    const dev = name === 'ps2ui-dev.js';
    const run = (...extra) => {
      const r = spawnSync(process.execPath,
        [bin(name), html, css, '-o', join(dir, dev ? 'out' : 'out.json'),
         '--font-dir', fontDir, ...(dev ? ['--once'] : []), ...extra],
        { encoding: 'utf8' });
      return { status: r.status, err: r.stderr.replace(/\x1b\[[0-9;]*m/g, '') };
    };

    // A cap this compiler does not have. The name, not the value.
    const unknown = run('--limit', 'noodles=5');
    assert.equal(unknown.status, 2,
      `${prog} --limit noodles=5 exited ${unknown.status}: ${unknown.err}`);
    assert.match(unknown.err, new RegExp(`^${prog}: --limit: unknown cap`, 'm'));
    assert.doesNotMatch(unknown.err, /^error: /m,
      `${prog} used the library's error: prefix for a command-line fault`);

    // A cap this compiler does have, with a value it cannot.
    const zero = run('--limit', 'depth=0');
    assert.equal(zero.status, 2, zero.err);
    assert.match(zero.err,
      new RegExp(`^${prog}: --limit depth takes a positive integer`, 'm'));

    // Not name=value at all.
    const shapeless = run('--limit', 'depth');
    assert.equal(shapeless.status, 2, shapeless.err);
    assert.match(shapeless.err, new RegExp(`^${prog}: --limit takes NAME=N`, 'm'));

    // AND THE ACCEPTING CASE, which is what ps2ui dev forwards. Without
    // it the three refusals above would all pass on a bin that refuses
    // every --limit, which is what ps2ui-dev used to do.
    const ok = run('--limit', 'nodes=40000', '--limit', 'depth=128');
    assert.equal(ok.status, 0,
      `${prog} refused a valid --limit: ${ok.err}`);

    // AND THE VALUE REACHES THE COMPILER, which accepting it does not
    // prove. Falsification found this hole in the first version of
    // this test: deleting `options.limits = limits` from ps2ui-dev
    // left every assertion above green, because a flag parsed into a
    // variable nothing reads is still parsed. That is the shape D9
    // named in this same bin, where --strict and --min-font-size were
    // accepted and inert. A cap of 1 on a screen with two elements has
    // to be refused BY THE CAP.
    const tight = run('--limit', 'nodes=1');
    assert.equal(tight.status, 1,
      `${prog} ignored --limit nodes=1: ${tight.err}`);
    assert.match(tight.err, /more than 1 elements after data-repeat/);
  }
});


test('every page that quotes a usage line quotes the one the bin prints', () => {
  // THE FLAG REACHED --help AND NOT THE PAGES THAT QUOTE --help.
  // `--limit` went into ps2ui-layout's usage line in 48f1884 and
  // ps2ui-dev's in a9e24d4. Two pages copy those lines verbatim --
  // cli/ps2ui-layout.md as the synopsis, reference/diagnostics.md as the
  // exit-2 row -- and both kept the older string for a release and a
  // half. check-site-pages could not see it: it pins CITATIONS to line
  // numbers and has nothing that ties a quoted string to the program
  // that prints it. Review of #166 found the layout half, having missed
  // it once itself, and the dev half was new.
  //
  // So the quote is held to the output. Any future flag that reaches a
  // usage line fails here until the pages that reproduce it are updated,
  // which is the only direction that matters: a page can be behind the
  // tool, never ahead of it.
  const pages = [
    'docs/site/cli/ps2ui-layout.md',
    'docs/site/reference/diagnostics.md',
  ];
  const root = fileURLToPath(new URL('../../../', import.meta.url));
  // A usage line inside a markdown table has its pipes escaped as `\|`,
  // which is a faithful quote in a different spelling. Unescaping is the
  // one difference this allows; a missing flag still fails.
  const text = pages.map((p) => readFileSync(join(root, p), 'utf8')
    .replace(/\\\|/g, '|'));
  let quoted = 0;
  for (const [name, prog] of [['ps2ui-layout.js', 'ps2ui-layout'],
                              ['ps2ui-dev.js', 'ps2ui-dev']]) {
    // No arguments is the usage path for both, and it exits 2.
    const r = spawnSync(process.execPath, [bin(name)], { encoding: 'utf8' });
    assert.equal(r.status, 2, r.stderr);
    const line = r.stderr.split('\n').find((l) => l.startsWith(`usage: ${prog} `));
    assert.ok(line, `${prog} printed no usage line: ${r.stderr}`);
    // The flags the line names, which is the part a page gets wrong.
    const flags = line.match(/--[a-z][a-z-]*/g);
    assert.ok(flags.includes('--limit'),
      `${prog}'s usage line has no --limit, so this test would pass vacuously`);
    for (const [i, p] of pages.entries()) {
      if (!text[i].includes(`usage: ${prog} `)) continue;
      quoted += 1;
      assert.ok(text[i].includes(line.trim()),
        `${p} quotes a ${prog} usage line that is not the one ${prog} prints.\n`
        + `  prints: ${line.trim()}\n`
        + `  the page has a different string; paste this one over it.`);
    }
  }
  // Not vacuous: both pages really do quote at least one of the two.
  assert.ok(quoted >= 3, `only ${quoted} quoted usage line(s) were checked`);
});
