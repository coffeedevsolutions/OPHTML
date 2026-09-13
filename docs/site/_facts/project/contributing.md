# facts: project/contributing

This page emits no new facts. It consolidates parent facts and repository
documents already verified elsewhere, plus five commands re-run in this
session exactly as CI runs them. The table lists the parent fact ids relied
on, each with its parent page as source, and the session commands that back
the page's own tables.

Session commands, all from the repository root unless noted:

- `cd packages/layout && npm test` : 122 tests, `pass 122`, `fail 0`, exit 0.
- `cd packages/baker && PS2UI_REQUIRE_CROSSCHECK=1 PS2UI_REQUIRE_EXAMPLES=1
  PS2UI_REQUIRE_FONTS=1 python3 -m unittest discover -s tests` : `Ran 277
  tests in 18.948s`, `OK`, exit 0.
- `./examples/memcard/build.sh` : builds the blob, then runs `make -C
  runtime UIB=<blob> test` inline (`PASS: 410 checks, 0 failure(s)`), then
  overwrites `examples/memcard/screenshots/{preview,saves,states}.png`. Exit
  0.
- `git diff --exit-code examples/memcard/screenshots` after the build above:
  no output, exit 0. The overwritten screenshots are byte-identical to the
  committed ones.
- `make -C runtime test` : 465 lines, `PASS: 410 checks, 0 failure(s)`, exit
  0.
- `make -C runtime syntax-check CC=clang` : 27 `ok -` lines, exit 0.
- `ls tools/` : lists every script named in the Checks table on the page,
  confirming each exists.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| integrate.test-targets | `runtime/Makefile` declares five targets: `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. No `test-compat` target exists. | runtime/integrating (parent) | `make -C runtime test` and `make -C runtime syntax-check CC=clang`, both re-run in this session, exit 0; `make -C runtime test-compat` was not re-run here (parent already recorded its failure) | verified |
| integrate.test.output | `make -C runtime test` prints `syntax-check`, `timing-check`, `test-narrow`, then `test_runtime`, ending `PASS: 5 checks` before `PASS: 410 checks`. | runtime/integrating (parent) | this session's `make -C runtime test` run, 465 lines, matches the parent's line count and both PASS lines | verified |
| integrate.syntax-check.dash-s | `syntax-check` compiles with `-S`, and `CC=clang` parses the sample's MIPS inline asm without an x86 assembler rejecting it. | runtime/integrating (parent) | this session's `make -C runtime syntax-check CC=clang` printed the same 27 `ok -` lines as the parent's run, exit 0 | verified |
| integrate.gskit.no-tfx | gsKit declares no per-texture TFX field; there is no `PS2UI_GSKIT_HAS_FUNCTION` macro and no second build arm gated on one. | runtime/integrating (parent) | restated on this page from the parent's `grep -n Function runtime/vendor/gsKit/*.h` (no match); not re-run here | code-only |
| compat.platforms | Node 18 or newer, Python 3.9 or newer, Pillow 9 or newer. | reference/compatibility (parent) | read directly from packages/layout/package.json and packages/baker/pyproject.toml by the parent; packages/layout/package.json re-read in this session and shows `"node": ">=18"` | verified |
| compat.platforms.host-compilers | The host suite compiles with the default `cc` and with `clang`; both produce the same 27 `syntax-check` lines. There is no `test-compat` target. | reference/compatibility (parent) | this session's own `make -C runtime syntax-check CC=clang` run reproduces the parent's claim | verified |
| cli.ps2ui.checkout | Checkout spellings exist for every installed command, used by `examples/*/build.sh` and CI. `ps2ui` in a checkout is `PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui`. | cli/ps2ui (parent) | restated for the link into `cli/ps2ui#from-a-checkout`; `examples/memcard/build.sh` in this session's tree uses exactly that spelling, confirmed by reading the script | verified |

## follow-up

- `tools/check-tutorial.py` targets `docs/tutorial-uc3.md` (its `DOC`
  constant), not `docs/site/getting-started/tutorial-game-browser.md`.
  `ARCHITECTURE.md`'s own verification block already anticipates this:
  its comment reads "pointed at getting-started/tutorial-game-browser.md
  once that page exists." Documented on the page as the current target,
  not a defect.
