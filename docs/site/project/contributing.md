---
id: project/contributing
title: Contributing
description: Set up the tree, run the test suite CI runs, follow the five design rules, and see how a change is checked and admitted.
section: project
order: 71
version: 0.7.0
sources: [docs/site/ARCHITECTURE.md, CONTRIBUTING.md, .github/workflows/ci.yml, .github/ISSUE_TEMPLATE/bug.yml, .github/ISSUE_TEMPLATE/feature.yml, BACKLOG.md, docs/PLAN.md, packages/layout/package.json, examples/memcard/build.sh, tools/check-tutorial.py, tools/check-site-assets.py, tools/check-blobs.sh, tools/falsify.sh, tools/check-versions.py, tools/check-format-frozen.py, tools/check-runtime-shipped.py, tools/check-example-figures.py, tools/check-sweep-table.py, tools/check-deploying.py, tools/check-vram-model.py, tools/check-timing-probe.py, tools/check-findings.py, docs/site/runtime/integrating.md, docs/site/cli/ps2ui.md, docs/site/project/internals.md, docs/site/project/security-and-license.md, docs/site/_facts/runtime/integrating.md, docs/site/_facts/cli/ps2ui.md, docs/site/_facts/reference/compatibility.md]
---

## Setup

Install Node 18 or newer, Python 3.9 or newer with Pillow 9 or newer, and a
C compiler. Have DejaVu Sans on hand, or point `fonts/fonts.json` at a
different TTF pair. Nothing else. Keep the layout package free of runtime
dependencies and the baker limited to Pillow.

## Tests

Run all five before every pull request, from the repository root.

| command | covers |
|---|---|
| `cd packages/layout && npm test` | the layout compiler: HTML and CSS parsing, the box model, focus, themes, lists. 122 tests. |
| `cd packages/baker && PS2UI_REQUIRE_CROSSCHECK=1 PS2UI_REQUIRE_EXAMPLES=1 PS2UI_REQUIRE_FONTS=1 python3 -m unittest discover -s tests` | the baker, the previewer, the serve state machine, the arena cross-check against a compiled gsKit struct, the three shipped example blobs, and font metrics against DejaVu. 277 tests. The three env vars turn a skip into a failure when the fixture behind it is absent; set them only after the examples and fonts they require are in place. |
| `./examples/memcard/build.sh` | one project end to end: compiles both screens, bakes the blob, runs the C runtime suite over that exact blob, and refreshes the three committed screenshots. |
| `make -C runtime test` | the C runtime suite: `syntax-check`, `timing-check`, `test-narrow`, then the runtime test binary over five blobs. |
| `make -C runtime syntax-check CC=clang` | the same 27 sample and runtime compiles, under a second compiler. |

Tails from this session:

```sh
$ cd packages/layout && npm test
...
1..122
# tests 122
# suites 0
# pass 122
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

```sh
$ cd packages/baker && PS2UI_REQUIRE_CROSSCHECK=1 PS2UI_REQUIRE_EXAMPLES=1 PS2UI_REQUIRE_FONTS=1 python3 -m unittest discover -s tests
...
----------------------------------------------------------------------
Ran 277 tests in 18.948s

OK
```

```sh
$ ./examples/memcard/build.sh
...
1..410
PASS: 410 checks, 0 failure(s)
make: Leaving directory '/home/user/OPHTML/runtime'
ps2ui-bake: screenshots -> ./examples/memcard/screenshots/
memcard example: ./examples/memcard/build/ui.uib
```

```sh
$ git diff --exit-code examples/memcard/screenshots
$ echo $?
0
```

The build above overwrites `examples/memcard/screenshots/*.png`. The diff
above is empty, so this session's renderer wrote the same bytes as the
committed ones.

```sh
$ make -C runtime test
...
1..410
PASS: 410 checks, 0 failure(s)
make: Leaving directory '/home/user/OPHTML/runtime'
```

```sh
$ make -C runtime syntax-check CC=clang
make: Entering directory '/home/user/OPHTML/runtime'
ok - sample compiles: 
ok - sample compiles: -DPS2UI_SAMPLE_STATIC
...
ok - sample compiles: -DPS2UI_OPLENV_CYCLE_EVERY=300
make: Leaving directory '/home/user/OPHTML/runtime'
```

`make -C runtime test` prints its `PASS: 5 checks` line from `test-narrow`
before its `PASS: 410 checks` line from the full suite. Read the second
line as the suite's total, not the first. Both targets are covered on
[the runtime test targets](page:runtime/integrating#reference-table).
There is no `make -C runtime test-compat` target and no
`PS2UI_GSKIT_HAS_FUNCTION` macro anywhere in the tree.

`ps2ui`, `ps2ui-bake`, `ps2ui-check`, `ps2ui-fontgen`, `ps2ui-layout` and
`ps2ui-dev` are on `PATH` once the packages are installed. From a
checkout, without installing, every one of them has a
[checkout spelling](page:cli/ps2ui#from-a-checkout) built on
`PYTHONPATH=packages/baker python3 -m ...` or `node packages/layout/bin/...`.
`examples/memcard/build.sh` uses that spelling for `ps2ui build`.

The dev loop while working on a layout or baker change:

```sh
node packages/layout/bin/ps2ui-dev.js \
    examples/memcard/ui/library.html examples/memcard/ui/library.css \
    -o build/dev
```

## Rules

A pull request must hold to all five.

1. Everything moves to build time. The C runtime never parses HTML or CSS,
   never lays out a screen, never rasterizes a glyph, and never allocates
   past what the blob's header already sized.
2. A domain conversion crosses the layout to baker seam, or the baker to
   runtime seam, exactly once, with one owner: CSS alpha to GS 0 to 128,
   modulate RGB to the 0x80 identity, CLUT linear order to CSM1. Tests
   exist on both sides of every seam.
3. The layout compiler and the baker agree on glyph math bit for bit. The
   shared rounding rule is `floor(x + 0.5)`, never `round()`.
4. The previewer replays the baked blob, not the intermediate
   representation. A new command type teaches the previewer and the C
   runtime in the same pull request, and the format document for `.uib`
   bumps its version story.
5. `:focus` styling is paint-only. A geometry change under `:focus` is a
   compile error, not a warning.

## Checks

Every script below exists under `tools/`.

| script | holds |
|---|---|
| `tools/check-versions.py` | every version number in the tree agrees: the PyPI and npm package versions, the IR version, the `.uib` format version, and `PS2UI_VERSION`. |
| `tools/check-format-frozen.py` | the v7 `.uib` layout has not moved since the stability pledge. |
| `tools/check-runtime-shipped.py` | a built wheel carries `ps2ui.c` and `ps2ui.h`, and `ps2ui vendor-runtime` reads them from the installed package outside a checkout. |
| `tools/check-example-figures.py` | a shipped example's README figures match its built blob. |
| `tools/check-sweep-table.py` | the P3d content-sweep table is derived from the blob and the sample driver, not typed by hand. |
| `tools/check-deploying.py` | the deployment guide matches the source it describes. |
| `tools/check-tutorial.py` | runs `docs/tutorial-uc3.md` as a stranger would, every command block in order from an empty directory, and checks its stated output. It targets that document, not the site's `getting-started/tutorial-game-browser` page. |
| `tools/check-site-assets.py` | re-renders every `checked: true` entry in `docs/site/assets/assets.json` into a scratch directory and diffs the bytes against the committed PNG. |
| `tools/check-findings.py` | the findings graph in `docs/findings.yaml`: no cycle, no confirmed finding resting on an overturned one, no document citing an overturned finding unmarked. |
| `tools/check-vram-model.py` | the Python VRAM model against the gsKit function it ports, compiled and diffed over 45,000 sizes. |
| `tools/check-timing-probe.py` | the Phase 2 driver's frame timer measures work, not waiting, a source-level ordering check. |
| `tools/check-blobs.sh` | every baked blob against the runtime's assumptions, calling `ps2ui-check --strict` and naming each blob's exemptions in the script itself. |
| `tools/falsify.sh` | sabotages a file, runs a fence command against it, and restores the exact original bytes without calling `git checkout`. |

## Documentation changes

A change to `docs/tutorial-uc3.md` is checked by `tools/check-tutorial.py`:
it runs every ```` ```sh ```` block in the document in order, from an empty
scratch directory, and requires every non-empty line of a following
```` ```text ```` block to appear in the real output.

A change that touches a page under `docs/site/` and its rendered PNGs is
checked by `tools/check-site-assets.py`. It reads
`docs/site/assets/assets.json`, re-runs each `checked: true` entry's
command with `OUT` substituted for a temporary path, and diffs the result
byte for byte against the committed file. `checked: false` entries are
Playwright captures of the `ps2ui serve` page chrome; the script lists and
skips them, since browser text rendering is not byte-stable across
versions, and keeps the command only so the capture can be redone by hand.
CI runs this script as "Documentation site screenshots match the
renderer," after the memcard, channel6 and opl-env builds and the
streaming bench fixture, because its commands read those built blobs.

## Issues and admission

Open a bug with `.github/ISSUE_TEMPLATE/bug.yml`: name the stage (layout,
baker, runtime, or not sure), give a minimal HTML and CSS or IR and blob
reproduction, state expected versus actual, attach the previewer PNG for a
visual bug, and say whether hardware or an emulator agrees with the
preview.

Open a feature request with `.github/ISSUE_TEMPLATE/feature.yml`: state
the concrete UI the request is for, name the stage or stages it touches,
say whether it respects rule 1 above, and check `BACKLOG.md` first. Comment
on an existing item rather than filing a duplicate.

`BACKLOG.md` is a defect ledger and an idea archive, not a work queue.
Sequencing comes from the phase gates in
[PLAN.md](page:project/internals#decisions), and admission from the pull
rule: a feature enters when a real use case demands it, never because it
scores well. An item with no phase behind it sits in the pull lane and
enters only when a concrete use pulls it in. Read
[method.md](page:project/internals#method) before adding a test, a lint
rule, or a bench instrument; it names the seven ways a check can pass
without proving what it claims.

Every workflow [runs on a GitHub-hosted runner](page:project/security-and-license#ci)
with a read-only token. Never attach a self-hosted runner to this
repository.
