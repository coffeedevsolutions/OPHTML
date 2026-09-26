---
id: getting-started/installation
title: Installation
description: Install both packages, prove them with --version, generate font metrics, and know when the console half needs ps2dev.
section: getting-started
order: 1
version: 0.10.0
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
checking it run entirely on the host. Only a console program of your own,
compiling and running the C runtime on real hardware, needs the ps2dev
toolchain. The ready-made console launcher needs none.

## Minimal example

Install both packages, then prove each is on PATH.

```sh
pip install ophtml
npm install -g @ophtml/layout
```

```sh
$ ps2ui --version
ps2ui 0.10.0
$ ps2ui-layout --version
ps2ui-layout 0.10.0
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
| uharfbuzz | 0.51.7 or newer | `dependencies` in `packages/baker/pyproject.toml`; `pip install ophtml` installs it as a wheel on every platform, so `ps2ui fontgen` needs nothing from the system |
| ps2dev toolchain | only for the console half | the Python and Node halves never touch it |

The full platform matrix, including the host C compiler and the pinned
gsKit headers, is in
[compatibility](page:reference/compatibility#platforms-table).

## Behaviour

### Install the packages

The two installs are independent and order does not matter. `pip install
ophtml` resolves against PyPI's stable releases; `npm install -g
@ophtml/layout` resolves against npm's `latest` dist-tag. A prerelease publishes under
`next` on npm, never `latest`: `publishConfig.tag` is `"next"` exactly while
the version is a prerelease, and `check-versions.py` holds that in both
directions. Pip excludes a prerelease from a plain install while a
stable release exists. A plain install of either command therefore always
lands on a released version, not a prerelease.

### If pip refuses to install

A current Homebrew, Debian or Ubuntu Python manages its own site
packages and declines a plain `pip install`:

```text
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try brew install
    xyz, where xyz is the package you are trying to install.

    If you wish to install a Python library that isn't in Homebrew,
    use a virtual environment:

    python3 -m venv path/to/venv
    source path/to/venv/bin/activate
```

That is [PEP 668](https://peps.python.org/pep-0668/) and it is not a
fault in your setup. A virtual environment is the shortest way through:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install ophtml
```

`pipx install ophtml` works too and keeps the commands on your `PATH`
without a shell to activate. Either way the Node half is unaffected:
npm has no equivalent rule.

### A TTF to start with

ps2ui bakes text at build time, so the first command needs a font file
and does not ship one. Any TTF works; the pair that produces the
numbers printed throughout this site is **DejaVu Sans** regular and
bold, which is also what the repository's own builds use.

A stock macOS carries almost no plain `.ttf`. `/System/Library/Fonts`
is mostly `.ttc` collections, and one of those does load: `fontgen`
hands the path to FreeType, which opens a collection at face 0. The
catch is that there is no way to reach any other face, so a `.ttc`
gives you the same weight twice and the `bold` argument buys nothing.
**Nothing downstream tells you.** Measured on a macOS collection: the
two metrics files come back with identical glyph and kerning tables
while still declaring `weight` 400 and 700, so the manifest says you
have a bold face, the bake accepts it, and every heading draws in the
regular one.
Get DejaVu from
[dejavu-fonts.github.io](https://dejavu-fonts.github.io/), or
`brew install --cask font-dejavu`, which lands them in
`~/Library/Fonts`. Most Linux distributions already have them under
`/usr/share/fonts/truetype/dejavu/`. On Windows, unzip the release and
install the two faces the usual way; a per-user install lands them in
`%LOCALAPPDATA%\Microsoft\Windows\Fonts`, which is one of the
candidates `fonts.json` carries.

The quickstart and the tutorial both spell the first command
`ps2ui fontgen "$TTF_REGULAR" "$TTF_BOLD"` and neither assigns the two
variables, so set them once for the shell you are working in:

```sh
# macOS, after `brew install --cask font-dejavu`
export TTF_REGULAR=~/Library/Fonts/DejaVuSans.ttf
export TTF_BOLD=~/Library/Fonts/DejaVuSans-Bold.ttf

# most Linux distributions
export TTF_REGULAR=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
export TTF_BOLD=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
```

On Windows the same two variables, in PowerShell:

```powershell
$env:TTF_REGULAR = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts\DejaVuSans.ttf"
$env:TTF_BOLD    = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts\DejaVuSans-Bold.ttf"
```

Unset, `fontgen` receives two empty paths and fails on the first.

The rest of this site spells its commands for a POSIX shell: the
quickstart and the tutorial both write files with `cat > f <<'EOF'`
heredocs, which `cmd` and PowerShell do not have. Git Bash or WSL runs
them as written; otherwise create the files with an editor and run only
the `ps2ui` lines. Nothing in the toolchain requires a POSIX shell:
`ps2ui` is a Python console script and `ps2ui-layout` an npm bin, and
both are ordinary commands on Windows. It is the *documents* that
assume one.

### Verify

`ps2ui --version` and `ps2ui-layout --version` are the two checks in the
minimal example above. Run `which ps2ui` to confirm the resolved path.

```sh
$ which ps2ui
/usr/local/bin/ps2ui
```

Inside a virtual environment it is an absolute path ending in
`.venv/bin/ps2ui` instead; what matters is that it resolves at all.

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
measures kerning with HarfBuzz through `uharfbuzz`, so it runs the same
on a stock macOS, Windows or Linux install. See
[ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen) for every argument and
output file.

### If fontgen refuses

Only 0.8.0 and earlier refuse. They measured kerning through Pillow's
Raqm engine, which loads a fribidi library no Pillow wheel bundles, so a
stock Mac or Windows box printed `ps2ui-fontgen: this Pillow has no Raqm
layout engine` and wrote nothing. Upgrading is the whole fix:

```sh
pip install --upgrade ophtml
```

0.9.0 measures through `uharfbuzz` and never asks Pillow about Raqm,
and it writes the same tables 0.8.0 did, byte for byte. If you have to
stay on 0.8.0, its refusal prints the remedy for the platform it finds.

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

`ps2ui fontgen` 0.8.0 and earlier refuse outright without Raqm; see
[If fontgen refuses](#if-fontgen-refuses).

`ps2ui-fontgen`'s usage line names the checkout spelling,
`python -m ps2ui_bake.fontgen`, even when the installed `ps2ui-fontgen`
binary is the one that printed it. A missing or unreadable TTF, or a
non-numeric weight, raises an uncaught Python traceback rather than a
one-line message. Neither blocks installation; both are worth knowing
before scripting around either command's exit code.

A plain `npm install -g @ophtml/layout` never installs a prerelease by
accident: a prerelease publishes to the `next` dist-tag, and `latest`
stays on the newest stable release. The same protection holds on
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
