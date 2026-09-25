# facts: getting-started/installation

Session commands behind the rows below, run from the repository root unless
noted. `pip install`, `npm install` and `npm link` were not run in this
session; the editable install (`pip install -e packages/baker`) and the
`npm link` in `packages/layout` were already done by the environment and are
reused as-is.

- `ps2ui --version`
- `ps2ui-layout --version`
- `which ps2ui`
- `python3 -c "from PIL import features; print(features.check('raqm'), features.check('fribidi'))"`
- `PS2UI_LAYOUT=/bin/false ps2ui build`, run inside a scratch copy of
  `examples/memcard` made with `cp -r examples/memcard <scratch>/` and
  `rm -rf <scratch>/memcard/build`. Nothing under `examples/memcard/build/`
  was touched.
- `python3 -m unittest discover -s tests -p test_baker.py -k TestFontgenNeedsNoRaqm`
  from `packages/baker` (3 tests, OK), after F47 replaced
  `TestFontgenRefusesWithoutRaqm`; 0.8.0's remedy is sourced from the
  CHANGELOG and `registry.yml` run 35809073289 instead.

Line numbers were re-located by symbol in this session.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| install.commands | `pip install ophtml` and `npm install -g @ophtml/layout` install the four Python commands and the two Node commands. `ps2ui --version` prints `ps2ui 0.9.0`; `ps2ui-layout --version` prints `ps2ui-layout 0.9.0`. | packages/baker/pyproject.toml:17-24 (`[project.scripts]`); packages/layout/package.json:11-14 (`bin`); .github/workflows/registry.yml:181-182 runs the same two install lines against a plain registry checkout | measured from the registries after 0.9.0 was published: a fresh venv's `pip install --no-cache-dir ophtml` printed `ps2ui 0.9.0` and `npm install @ophtml/layout@latest` printed `ps2ui-layout 0.9.0`, and `registry.yml` run 35817721457 ran the same two install lines on ubuntu-24.04, macos-15, macos-15-intel and windows-2025. The tree's own commands print `ps2ui 0.10.0.dev0` and `ps2ui-layout 0.10.0-dev.0`, a prerelease on neither registry, which is why this row's claim names the release and not the tree. Restates parent facts `cli.ps2ui.version`, `cli.ps2ui.entry-point`, `compat.versions` | verified |
| install.requirements | Node.js needs 18 or newer, Python needs 3.9 or newer, Pillow needs 9 or newer. The baker also needs `uharfbuzz` 0.51.7 or newer, a declared dependency pip installs with the package, so nothing comes from the system; Raqm and fribidi were needed only by 0.8.0 and earlier. The ps2dev toolchain is needed only for the console half. | packages/layout/package.json:22 (`engines.node`); packages/baker/pyproject.toml:11-12 (`requires-python`, `dependencies`) | read directly from both manifests in this session. Restates parent fact `compat.platforms` verbatim for Node/Python/Pillow; restates `compat.platforms.macos-fribidi` for Raqm/fribidi; restates `integrate.vendor.behaviour` and `integrate.toolchain` for the ps2dev line | verified |
| install.raqm.remedy | Only 0.8.0 and earlier refuse: they measured kerning through Pillow's Raqm engine, which loads a fribidi no Pillow wheel bundles, so a stock Mac or Windows box printed `ps2ui-fontgen: this Pillow has no Raqm layout engine` and wrote nothing, followed by a remedy for the platform it found. `pip install --upgrade ophtml` is the fix: 0.9.0 measures through `uharfbuzz`, never asks Pillow about Raqm, and writes the same tables byte for byte. | CHANGELOG.md:178 (0.9.0's F47 entry); CHANGELOG.md:468-533 (0.8.0: the per-platform remedy), 1342-1369 (0.6.0: fribidi asked about separately) | `registry.yml` run 35809073289 against the published 0.8.0: both `macos-plain` arms and `windows-plain` logged `ok - refused, naming Raqm`. Against this tree: `TestFontgenNeedsNoRaqm.test_the_tables_come_out_whole_on_a_pillow_with_no_raqm` passed, and the rehearsed 0.9.0 wheel's `ps2ui fontgen` on the vendored faces wrote tables identical to the committed ones | verified |
| install.layout-discovery.override-failure | With `PS2UI_LAYOUT` pointing at a program that always fails, `ps2ui build` reports the compiler failure and exits 1, rather than falling through to another discovery step. | packages/baker/ps2ui_bake/ps2ui.py:37-58 (`layout_command`) | in a scratch copy of `examples/memcard` (build/ removed first), `PS2UI_LAYOUT=/bin/false ps2ui build` printed `ps2ui: ps2ui-layout failed on ui/library.html (exit 1)`, exit 1. Identical to parent fact `cli.ps2ui.layout-discovery`'s own run of the same command | verified |
| install.checkout.editable | `pip install -e packages/baker` puts `ps2ui`, `ps2ui-bake`, `ps2ui-check` and `ps2ui-fontgen` on PATH, resolved outside the checkout. | packages/baker/pyproject.toml:17-24 | `which ps2ui` printed `/usr/local/bin/ps2ui` in this session (the editable install was already in place; not re-run here) | verified |
| install.console-half | Nothing about installing or verifying the two packages touches the ps2dev toolchain. The console half needs it only when vendoring and building the C runtime. | packages/baker/ps2ui_bake/vendor.py:238-253 (the toolchain notes `ps2ui vendor-runtime` prints) | restates parent fact `integrate.vendor.behaviour` and `integrate.toolchain`, both verified in `_facts/runtime/integrating.md` by scratch `ps2ui vendor-runtime` runs. No new command run here | verified |

## findings

- `packages/baker/tests/test_baker.py` is not importable as a plain module
  (`python3 -m unittest tests.test_baker...` fails with
  `ModuleNotFoundError: No module named 'fonts_available'`) because it
  resolves `fonts_available` relative to the `tests/` directory only. The
  working invocation is `python3 -m unittest discover -s tests -p
  test_baker.py -k <name>` from `packages/baker`. ARCHITECTURE.md's
  follow-ups table already records the same shape of defect for
  `test_serve.py`, attributed to `cli/previewer`; this is a second instance,
  in `test_baker.py`, not previously listed.
