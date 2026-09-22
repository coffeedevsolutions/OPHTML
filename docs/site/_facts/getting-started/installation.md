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
- `python3 -m unittest discover -s tests -p test_baker.py -k TestFontgenRefusesWithoutRaqm -v`
  from `packages/baker`.

Line numbers were re-located by symbol in this session.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| install.commands | `pip install ophtml` and `npm install -g @ophtml/layout` install the four Python commands and the two Node commands. `ps2ui --version` prints `ps2ui 0.7.0`; `ps2ui-layout --version` prints `ps2ui-layout 0.7.0`. | packages/baker/pyproject.toml:17-24 (`[project.scripts]`); packages/layout/package.json:11-14 (`bin`); .github/workflows/registry.yml:269-270 runs the same two install lines against a plain registry checkout | this session the tree's own commands printed `ps2ui 0.8.0.dev0` and `ps2ui-layout 0.8.0-dev.0`, the prerelease this tree carries; the versions in the fact are what the registries hand a reader, which is what this row is about. The two install lines were not run here (forbidden this run); they are read from the manifests and from the CI job that runs them. Restates parent facts `cli.ps2ui.version`, `cli.ps2ui.entry-point`, `compat.versions` | verified |
| install.requirements | Node.js needs 18 or newer, Python needs 3.9 or newer, Pillow needs 9 or newer. Raqm and fribidi are needed only for `ps2ui fontgen`. The ps2dev toolchain is needed only for the console half. | packages/layout/package.json:22 (`engines.node`); packages/baker/pyproject.toml:11-12 (`requires-python`, `dependencies`) | read directly from both manifests in this session. Restates parent fact `compat.platforms` verbatim for Node/Python/Pillow; restates `compat.platforms.macos-fribidi` for Raqm/fribidi; restates `integrate.vendor.behaviour` and `integrate.toolchain` for the ps2dev line | verified |
| install.raqm.check | This machine's Pillow reports Raqm and fribidi both present, so `ps2ui fontgen` never refuses here. | packages/baker/ps2ui_bake/fontgen.py:382 (`features.check("raqm")`) | `python3 -c "from PIL import features; print(features.check('raqm'), features.check('fribidi'))"` printed `True True` | verified |
| install.raqm.remedy | `_raqm_remedy()` reports the Pillow version, platform and machine, asks `features.check("fribidi")` separately, and leads with `brew install fribidi` / `apt install libfribidi0` / `dnf install fribidi` when fribidi alone is missing. On Windows it adds a paragraph naming the DLLs Pillow looks for (`fribidi-0.dll`, `libfribidi-0.dll`, `fribidi.dll`) and the requirement that their directory is on PATH. If fribidi is already present, or the package-manager fix does not clear it, `_escalation()` gives the next step per platform: on macOS and Linux a Pillow rebuild against Raqm (`brew install libraqm` plus a `PKG_CONFIG_PATH` from `brew --prefix` on macOS, then `pip install --no-binary pillow --force-reinstall pillow`), and on Windows never a rebuild -- a still-false check after installing the DLL is named as a PATH-ordering or bitness problem, and fribidi present with Raqm absent is named as a Pillow that is not PyPI's wheel, answered with `pip install --force-reinstall --only-binary :all: pillow`. | packages/baker/ps2ui_bake/fontgen.py:103-227 (`_raqm_remedy`), 229-286 (`_escalation`), 288-327 (`_windows_fribidi_hint`), 330-366 (`_rebuild_hint`) | `python3 -m unittest discover -s tests -p test_baker.py -k TestFontgenRefusesWithoutRaqm -v` from packages/baker: 8 tests, OK. `test_main_exits_nonzero_and_writes_nothing` printed the mocked refusal verbatim, pasted on the page. This machine has Raqm (`install.raqm.check`), so the unmocked tool never takes this path here; marked code-only for that reason, verified for the mocked text the test printed | code-only (unmocked run); verified (the printed remedy text, from the test in this session) |
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
