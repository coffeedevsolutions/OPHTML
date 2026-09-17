---
id: getting-started/installation
title: Installation
description: Install both packages, prove them with --version, generate font metrics, and know when the console half needs ps2dev.
section: getting-started
order: 1
version: 0.7.0
sources: [packages/baker/pyproject.toml, packages/layout/package.json, packages/baker/ps2ui_bake/fontgen.py, packages/baker/ps2ui_bake/ps2ui.py, fonts/fonts.json, .github/workflows/registry.yml, docs/tutorial-uc3.md, docs/site/ARCHITECTURE.md]
---

# Installation

## What it is

OPHTML installs as two separate packages. `ophtml` on PyPI carries the
Python baker: `ps2ui`, `ps2ui-bake`, `ps2ui-check` and `ps2ui-fontgen`.
`@ophtml/layout` on npm carries the Node compiler: `ps2ui-layout` and
`ps2ui-dev`. Install both. `ps2ui` shells out to `ps2ui-layout` to compile
HTML and CSS, then calls the baker directly for everything else.

Nothing here needs a PS2 or an emulator. Building a `.uib` blob and
checking it run entirely on the host. Only the console half, compiling and
running the C runtime on real hardware, needs the ps2dev toolchain.

## Minimal example

Install both packages, then prove each is on PATH.

```sh
pip install ophtml
npm install -g @ophtml/layout
```

```sh
$ ps2ui --version
ps2ui 0.7.0
$ ps2ui-layout --version
ps2ui-layout 0.7.0
```

`ps2ui --version` proves the Python half; `ps2ui-layout --version` proves
the Node half. `ps2ui-layout` is an npm bin, not a Python entry point, so
only the second command exercises the compiler directly.

## What you need

| need | minimum | why |
|---|---|---|
| Python | 3.9 or newer | `requires-python` in `packages/baker/pyproject.toml` |
| Pillow | 9 or newer | `dependencies` in `packages/baker/pyproject.toml`; the baker and `ps2ui-fontgen` both import it |
| Node.js | 18 or newer | `engines.node` in `packages/layout/package.json` |
| Raqm and fribidi in Pillow | present | `ps2ui fontgen` refuses to write metrics without Raqm |
| ps2dev toolchain | only for the console half | the Python and Node halves never touch it |

The full platform matrix, including the host C compiler and the pinned
gsKit headers, is in
[compatibility](page:reference/compatibility#platforms-table).

## Behaviour

### Install the packages

The two installs are independent and order does not matter. `pip install
ophtml` resolves against PyPI's stable releases; `npm install -g
@ophtml/layout` resolves against npm's `latest` dist-tag. A prerelease publishes under
`next` on npm, never `latest`; this tree carries `0.8.0.dev0`, a
prerelease, so it is pinned to `next` and would not take `latest`. Pip excludes a prerelease from a plain install while a
stable release exists. A plain install of either command therefore always
lands on a released version, not a prerelease.

### Verify

`ps2ui --version` and `ps2ui-layout --version` are the two checks in the
minimal example above. Run `which ps2ui` to confirm the resolved path.

```sh
$ which ps2ui
/usr/local/bin/ps2ui
```

A missing `ps2ui-layout` does not fail at install time. `ps2ui build`
finds it by checking `$PS2UI_LAYOUT`, then `ps2ui-layout` on PATH, then a
sibling checkout. Pointing `$PS2UI_LAYOUT` at a program that always fails
proves the search stops at the override rather than falling through:

```sh
$ PS2UI_LAYOUT=/bin/false ps2ui build
ps2ui: ps2ui-layout failed on ui/library.html (exit 1)
```

### Fonts

Generate font metrics before building a project. `ps2ui fontgen
<regular.ttf> <bold.ttf> [-o DIR]` writes `default.metrics.json`,
`default-bold.metrics.json` and `fonts.json` into `fonts/` by default. It
needs Raqm to measure kerning and refuses to write anything without it. See
[ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen) for every argument and
output file.

### If fontgen refuses

`ps2ui fontgen` checks `features.check("raqm")` before opening a font.
Without it, it prints the Pillow version, the platform, and whether
fribidi is present, then a remedy that matches what it found.

| platform | first thing to try | then |
|---|---|---|
| macOS | `brew install fribidi` | `brew install libraqm`, set `PKG_CONFIG_PATH` from `brew --prefix`, `pip install --no-binary pillow --force-reinstall pillow` |
| Debian, Ubuntu | `apt install libfribidi0` | `pip install --no-binary pillow --force-reinstall pillow` |
| Fedora | `dnf install fribidi` | `pip install --no-binary pillow --force-reinstall pillow` |

The package-manager fix runs first only when Pillow reports fribidi
missing. When fribidi is already present, the tool skips straight to the
rebuild column. Verify with `features.check('raqm')`, not pip's exit
status; a Pillow build without libraqm still exits 0 and silently omits
the feature.

Both macOS Pillow wheels compile Raqm into the binary and load fribidi
from the system at run time. A Mac with Homebrew installed for a while
usually clears this with the fribidi line alone. A clean runner does not.
This machine's Pillow reports Raqm and fribidi both present:

```sh
$ python3 -c "from PIL import features; print(features.check('raqm'), features.check('fribidi'))"
True True
```

so the refusal below is quoted from a mocked test run, not a live refusal.

```
ps2ui-fontgen: this Pillow has no Raqm layout engine, so kerning cannot be extracted; refusing to write a metrics file without it.
The Pillow you have (12.3.0, linux/x86_64) reports no Raqm, and no fribidi either.
Raqm is compiled into Pillow's binary and fribidi is loaded from your system at run time, so the missing piece is probably fribidi alone. Try that first, it needs no rebuild:
    brew install fribidi          # macOS
    apt install libfribidi0       # Debian/Ubuntu
    dnf install fribidi           # Fedora
...
If it is still false, rebuild Pillow against both:
    pip install --no-binary pillow --force-reinstall pillow
Use --no-binary pillow, not --no-binary :all: -- the bare form source-builds every dependency and spends tens of minutes bootstrapping CMake.
```

### From a checkout

A checkout runs each tool through its module or script instead of the
installed name.

| installed command | checkout spelling |
|---|---|
| `ps2ui` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui` |
| `ps2ui-layout` | `node packages/layout/bin/ps2ui-layout.js` |

`pip install -e packages/baker` puts the four Python commands on PATH,
resolved outside the checkout tree:

```sh
$ which ps2ui
/usr/local/bin/ps2ui
```

The remaining checkout spellings, and the full command table, are on
[ps2ui](page:cli/ps2ui#from-a-checkout).

### The console half

Installing and verifying `ophtml` and `@ophtml/layout` never touches
ps2dev. The ps2dev toolchain matters only once a `.uib` blob is ready and
the C runtime needs to compile against real gsKit and PS2SDK headers.
`ps2ui vendor-runtime` copies the two runtime files and prints the
toolchain notes; nothing about it runs during a package install. Full
setup, the cross-compile image, and the sample Makefile are on
[integrating the runtime](page:runtime/integrating#the-cross-toolchain).

## Limits and errors

Without Raqm, `ps2ui fontgen` refuses outright and writes nothing; see
[If fontgen refuses](#if-fontgen-refuses) for the remedy per platform.

`ps2ui-fontgen`'s usage line names the checkout spelling,
`python -m ps2ui_bake.fontgen`, even when the installed `ps2ui-fontgen`
binary is the one that printed it. A missing or unreadable TTF, or a
non-numeric weight, raises an uncaught Python traceback rather than a
one-line message. Neither blocks installation; both are worth knowing
before scripting around either command's exit code.

A plain `npm install -g @ophtml/layout` never installs a prerelease by
accident: this tree's version publishes to the `next` dist-tag, and
`latest` stays on the newest stable release. The same protection holds on
PyPI for as long as a stable `ophtml` release exists.

## Related pages

- [Quick start](page:getting-started/quickstart#what-you-get) runs the eight
  commands from a TTF to a served preview.
- [ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen) covers every fontgen
  argument, output file and exit code.
- [Integrating the runtime](page:runtime/integrating#the-cross-toolchain)
  covers the cross toolchain and the sample Makefile.
- [Compatibility](page:reference/compatibility#platforms-table) covers
  every supported version and platform.
