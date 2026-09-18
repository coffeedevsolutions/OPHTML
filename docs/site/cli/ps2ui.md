---
id: cli/ps2ui
title: ps2ui
description: The umbrella command over the toolchain: every subcommand, the project keys it forwards, what it writes and its exit codes.
section: cli
order: 30
version: 0.7.0
sources: [packages/baker/ps2ui_bake/ps2ui.py, packages/baker/ps2ui_bake/serve.py, packages/baker/ps2ui_bake/vendor.py, packages/baker/ps2ui_bake/project.py, packages/baker/ps2ui_bake/check.py, packages/baker/ps2ui_bake/__main__.py, packages/baker/pyproject.toml, packages/layout/package.json, packages/layout/bin/ps2ui-dev.js, packages/layout/src/index.js, packages/baker/tests/test_baker.py, packages/baker/tests/test_serve.py, examples/memcard/build.sh, examples/channel6/build.sh, README.md, CHANGELOG.md]
---

# ps2ui

`ps2ui` drives the whole toolchain from one project file. Each subcommand
reads `ps2ui.json`, turns its keys into flags, and runs the tool that owns
that stage. Read [the project file](page:authoring/project-file#reference-table)
for what the keys mean. This page states where each key goes.

```console
$ ps2ui --version
ps2ui 0.7.0
```

```console
$ ps2ui --help
usage: ps2ui [-h] [--version]
             {build,check,fontgen,serve,vendor-runtime,dev} ...

Compile, bake and check a ps2ui project.

positional arguments:
  {build,check,fontgen,serve,vendor-runtime,dev}
    build               compile every screen and bake one blob
    check               validate the blob the project builds
    fontgen             metrics and a manifest from two TTFs
    serve               preview the project in a browser
    vendor-runtime      write ps2ui.c and ps2ui.h into your project
    dev                 rebuild on every edit

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

A subcommand is required. A bare `ps2ui` prints the usage line and exits 2.

```console
$ ps2ui
usage: ps2ui [-h] [--version]
             {build,check,fontgen,serve,vendor-runtime,dev} ...
ps2ui: error: the following arguments are required: cmd
```

Every subcommand except `fontgen` and `vendor-runtime` changes directory into
the project root first. Paths in the output are relative to the project file,
not to the shell. Every command block below was run from inside a scratch copy
of `examples/memcard`, so the project argument is left off and defaults to
`ps2ui.json`.

## build

Compile every screen with `ps2ui-layout`, then bake the results into one blob
with `ps2ui-bake`.

### Synopsis

```sh
ps2ui build [project] [--mode MODE] [-o OUT]
            [--preview PNG] [--montage PNG] [--preview-display PNG]
```

`project` is a `ps2ui.json` or a directory holding one.

### Options

| flag | argument | default | effect |
|---|---|---|---|
| `--mode` | `MODE` | the project's `mode` | Replaces the video mode passed to the compiler. |
| `-o`, `--out` | `OUT` | the project's `out` | Moves the blob, and the intermediates with it. |
| `--preview` | `PNG` | the project's `preview` | Replaces the preview path. `none` suppresses it. |
| `--montage` | `PNG` | the project's `montage` | Replaces the montage path. `none` suppresses it. |
| `--preview-display` | `PNG` | the project's `previewDisplay` | Replaces the display preview path. `none` suppresses it. |

Each flag overrides one project key for one run. The suffix rule for `-o` is
on [the project file](page:authoring/project-file#the-output-path-moves-the-intermediates).

The compiler runs once per screen. These project keys become its flags.

| key | flag on ps2ui-layout |
|---|---|
| `fonts` | `--fonts` |
| `mode` | `--mode` |
| `canvas` | `--canvas` |
| `displayAspect` | `--display-aspect` |
| `strict` | `--strict` |
| `minFontSize` | `--min-font-size` |
| `focusWrap` | `--focus-wrap`, per screen |

Their meanings are on [ps2ui-layout](page:cli/ps2ui-layout#options). Point
`PS2UI_LAYOUT` at `/bin/echo` to see the argv for a given project. The run
below is a scratch project that sets every key.

```console
$ PS2UI_LAYOUT=/bin/echo ps2ui build
ui/library.html ui/library.css -o build/library.json --fonts fonts/fonts.json --mode ntsc16x9 --canvas 704x448 --display-aspect 16:9 --strict --min-font-size 11 --focus-wrap
```

The baker runs once over every IR file. These keys become its flags.

| key | flag on ps2ui-bake |
|---|---|
| `out` | `-o` |
| `fonts` | `--fonts` |
| `palettizeImages` | `--palettize-images` |
| `vramBudget` | `--vram-budget` |
| `preview` | `--preview` |
| `montage` | `--montage` |
| `previewDisplay` | `--preview-display` |

The transcript those flags produce is on [ps2ui-bake](page:cli/ps2ui-bake#output).

### Output

The compiler's warnings and summary come first, one block per screen. The
baker's transcript follows. Both go to stderr, and stdout stays empty.

```console
$ ps2ui build
warning: overscan: text "PS2" at (28,25) leaves the title-safe area; a CRT may crop it
warning: min-font-size: "MEMORY CARD" is 12px; below 14px is unreadable from a couch
...
ps2ui-layout: 89 paint commands, 9 focusables -> build/library.json
warning: overscan: text "PS2" at (28,25) leaves the title-safe area; a CRT may crop it
...
ps2ui-layout: 43 paint commands, 7 focusables -> build/saves.json
  runtime tables: 11 textures, 1 CLUTs, 6 slots, 2 screens
...
  textures 163840 B of 753664 B budget (21%)
ps2ui-bake: 2 screen(s), 1062 records, 11 textures (128 KiB baked), 1 CLUTs -> build/ui.uib
ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] __attribute__((aligned(16))))
ps2ui-bake: preview -> build/preview.png
ps2ui-bake: montage -> build/states.png
```

### Exit codes

| code | when |
|---|---|
| 0 | the bake succeeded |
| 1 | the project file is refused, the compiler failed on a screen, or the bake failed |
| 2 | argparse rejected the command line |

A compiler failure is reported as `ps2ui: ps2ui-layout failed on <html>
(exit N)`. The wrapper exits 1 whatever `N` was. The compiler prints its own
message above that line, and that is the one to read.

### Files written

| path | when |
|---|---|
| `<build>/<screen>.json` | always, one per screen |
| the `out` path, default `build/ui.uib` | always |
| the `preview` path | when `preview` is set |
| the `montage` path | when `montage` is set |
| the `previewDisplay` path | when `previewDisplay` is set |

```console
$ find build | sort
build
build/library.json
build/preview.png
build/saves.json
build/states.png
build/ui.uib
```

## check

Validate the blob the project builds.

### Synopsis

```sh
ps2ui check [project]
```

### Options

None beyond `-h`. New in 0.6.0. Two project keys reach the checker, so one
project means one answer in both halves of the toolchain.

| key | flag on ps2ui-check |
|---|---|
| `vramBudget` | `--vram-budget` |
| `strict` | `--strict` |

The same pair is listed on
[the project file](page:authoring/project-file#keys-that-reach-the-checker).
What the flags govern is on [ps2ui-check](page:cli/ps2ui-check#options).

### Output

The checker's TAP stream, unchanged. Its shape is on
[ps2ui-check](page:cli/ps2ui-check#output).

```console
$ ps2ui check
...
ok 61 - no 1px quads to shimmer on an interlaced CRT
ok 62 - every command can produce a pixel
ok 63 - every texture is drawn or belongs to a font
1..63
# build/ui.uib: 640x448 at 4:3, 2 screen(s), 1062 commands, 11 textures, 6 slots
PASS: 63 checks, 0 error(s), 0 warning(s)
```

### Exit codes

| code | when |
|---|---|
| 0 | the checker passed |
| 1 | the blob is missing, or the checker reported an error |
| 2 | the blob cannot be read, or argparse rejected the command line |

This subcommand never builds. A missing blob is refused by name.

```console
$ ps2ui check
ps2ui: build/ui.uib: no blob to check. Run `ps2ui build` first -- this does not build, so that a check can never report on a blob it just made and nobody has seen.
```

An unreadable blob passes the checker's own code straight through.

```console
$ ps2ui check
ps2ui-check: build/ui.uib: crc mismatch (file 0x4d8c37e4, computed 0x5dc0fb31)
```

### Files written

None.

## fontgen

Generate both metrics files and a manifest from two TTFs.

### Synopsis

```sh
ps2ui fontgen <regular.ttf> <bold.ttf> [-o DIR]
```

### Options

| flag | argument | default | effect |
|---|---|---|---|
| `-o`, `--out-dir` | `DIR` | `fonts` | Where the three files land. Created if absent. |

This subcommand reads no project file. Point the project's `fonts` key at the
manifest it writes, or leave the directory beside `ps2ui.json` and let
[the project file](page:authoring/project-file#fonts) find it.

### Output

One line per file, on stderr.

```console
$ ps2ui fontgen DejaVuSans.ttf DejaVuSans-Bold.ttf -o fonts
ps2ui-fontgen: 115 glyphs, 284 kern pairs -> fonts/default.metrics.json
ps2ui-fontgen: 115 glyphs, 163 kern pairs -> fonts/default-bold.metrics.json
ps2ui-fontgen: manifest -> fonts/fonts.json
```

Both faces carry the family name `default`. The weights are 400 and 700. The
single-face tool and its charset are on
[ps2ui-fontgen](page:cli/ps2ui-fontgen#synopsis).

### Exit codes

| code | when |
|---|---|
| 0 | both faces and the manifest were written |
| 1 | a TTF cannot be read, or the weight is not an integer |
| 2 | Pillow has no Raqm layout engine, or argparse rejected the command line |

The first failing face returns its own code and no manifest is written.

### Files written

| path |
|---|
| `<out-dir>/default.metrics.json` |
| `<out-dir>/default-bold.metrics.json` |
| `<out-dir>/fonts.json` |

## serve

Build the project, then answer a localhost page that draws the baked frame.

### Synopsis

```sh
ps2ui serve [project] [--uib BLOB] [--port PORT] [--screen NAME]
            [--theme N] [--no-watch] [--selftest]
```

### Options

| flag | argument | default | effect |
|---|---|---|---|
| `--uib` | `BLOB` | none | Serves a pre-baked blob. No compiler is needed and nothing is watched. |
| `--port` | `PORT` | 8080, walking up | Binds this port only. A busy explicit port is not retried. |
| `--screen` | `NAME` | screen 0 | The screen the page opens on. |
| `--theme` | `N` | 0 | The theme row the page opens on. |
| `--no-watch` | | off | Builds once and serves, without rebuilding on edits. |
| `--selftest` | | off | Requests one of every route, asserts the frame, and exits. |

Everything else comes from
[the project file](page:authoring/project-file#reference-table), through the
code path `ps2ui build` uses. The controls, the routes and the inspector are
on [the previewer](page:cli/previewer#options).

### Output

The build transcript, then one line naming the URL.

```console
$ ps2ui serve --port 8433
...
ps2ui-layout: 89 paint commands, 9 focusables -> build/serve/library.json
ps2ui-layout: 43 paint commands, 7 focusables -> build/serve/saves.json
...
ps2ui serve: http://127.0.0.1:8433/ -- ctrl-c to stop
```

`--selftest` prints one line per route and a verdict, then exits.

```console
$ ps2ui serve --selftest
...
ok - / 29569 bytes
ok - /frame.png 51449 bytes
ok - /state 93517 bytes
ok - /rev 15 bytes
ok - an unknown route is 404
ok - the frame is byte-identical to --preview
PASS: 6 route(s)
```

### Exit codes

| code | when |
|---|---|
| 0 | the server stopped on ctrl-c, or `--selftest` passed |
| 1 | the project is refused, the first build failed, or Node is absent |
| 2 | argparse rejected the command line |

Refusals here carry the prefix `ps2ui serve: `, not `ps2ui: `.

```console
$ env -i PATH=/usr/bin:/bin HOME=/root PYTHONPATH=/home/user/OPHTML/packages/baker /usr/bin/python3 -m ps2ui_bake.ps2ui serve --selftest
ps2ui serve: watch mode compiles HTML and CSS, which needs the Node half.
  Install it:  npm install -g @ophtml/layout
  Or serve a blob you already have, which needs no Node:
      ps2ui serve --uib build/ui.uib
```

Two failures still escape as tracebacks: a `--uib` path that does not exist,
and an explicit `--port` that is already bound. Both exit 1.

### Files written

| path |
|---|
| `<build>/serve/<screen>.json`, one per screen |
| `<build>/serve/ui.uib` |

No preview PNG is written. The server renders its own frames. The listing
below was taken while the server above was running.

```console
$ find build | sort
build
build/dev
build/dev/library.json
build/dev/preview.png
build/dev/ui.uib
build/library.json
build/preview.png
build/saves.json
build/serve
build/serve/library.json
build/serve/saves.json
build/serve/ui.uib
build/states.png
build/ui.uib
```

## vendor-runtime

Copy the C runtime out of this install and into a project.

### Synopsis

```sh
ps2ui vendor-runtime [dest] [--force] [--starter]
```

### Options

| flag | argument | default | effect |
|---|---|---|---|
| `--force` | | off | Overwrites a file that differs from the shipped runtime. |
| `--starter` | | off | Also writes `main.c` and a `Makefile` that build to an ELF as they stand. These two are never overwritten without `--force` and never stop the command, since editing them is the point. |

This subcommand reads no project file. It writes beside the sources that
compile against it, wherever
[the project file](page:authoring/project-file#what-it-is) happens to live.
The cross toolchain and a worked Makefile are on
[integrating the runtime](page:runtime/integrating#what-it-is).

### Output

One `wrote` line per file, the source they came from, then the toolchain
notes.

```console
$ ps2ui vendor-runtime src
wrote src/ps2ui.c
wrote src/ps2ui.h
runtime source: /home/user/OPHTML/runtime (this checkout)
...
```

A second run reports the pair as unchanged and writes nothing.

```console
$ ps2ui vendor-runtime src
ps2ui.c, ps2ui.h already up to date.
runtime source: /home/user/OPHTML/runtime (this checkout)
```

### Exit codes

| code | when |
|---|---|
| 0 | both files match already, or were written |
| 1 | a file differs and `--force` was not given, or no runtime was found |
| 2 | argparse rejected the command line |

Every file is classified before any file is written. One edited file stops
the whole command, so a fresh header never lands beside a stale source.

```console
$ ps2ui vendor-runtime src
ps2ui: ps2ui.c in src differs from the runtime this toolchain ships, so nothing was written.
  Writing the rest would leave you compiling a mixed pair -- ps2ui.c includes ps2ui.h and is written against its structs, and a version check will not catch it: the format is pledged frozen at v7, so PS2UI_VERSION no longer moves when the runtime does.
  Pass --force to take this toolchain's copy, or move your edited file aside first.
```

### Files written

| path | written |
|---|---|
| `<dest>/ps2ui.c` | always |
| `<dest>/ps2ui.h` | always |
| `<dest>/main.c` | `--starter` |
| `<dest>/Makefile` | `--starter` |

## dev

Watch one screen and rebuild it on every edit.

### Synopsis

```sh
ps2ui dev [project] [--screen NAME] [--once]
```

### Options

| flag | argument | default | effect |
|---|---|---|---|
| `--screen` | `NAME` | the only screen | The screen to watch. Required when the project has more than one. |
| `--once` | | off | Builds once and exits, rather than watching. |

The project keys go to `ps2ui-dev`, which is the compiler and the baker in
one watch loop. The set is the compiler's, plus `--palettize-images`. Read
[ps2ui-dev](page:cli/ps2ui-layout#ps2ui-dev) for the loop itself, and
[the project file](page:authoring/project-file#reference-table) for the keys.
The run below is the same all-keys scratch project.

```console
$ PS2UI_LAYOUT=/bin/echo ps2ui dev --once
ui/library.html ui/library.css -o build/dev --fonts fonts/fonts.json --mode ntsc16x9 --canvas 704x448 --display-aspect 16:9 --strict --min-font-size 11 --focus-wrap --palettize-images --once
```

In 0.6.0, `ps2ui dev` accepted `--strict` and `--min-font-size` and applied
neither. Fixed in 0.7.0: both flags
take effect in `ps2ui-dev` as they do in
`ps2ui-layout`, so `ps2ui dev` and `ps2ui build` warn on the same text and
fail on the same warnings. The detail is under
[strict and the font floor](page:cli/ps2ui-layout#strict-and-the-font-floor).

A scratch copy of `examples/opl-env` sets `strict` and `minFontSize: 11`.
`ps2ui build` on it printed no warning lines and exited 0. `ps2ui dev` on one
of its screens printed none either, and exited 0.

```console
$ ps2ui dev --screen landing --once
...
built in 200ms — 31 commands, 7 focusables, 0 warnings -> build/dev/preview.png
```

### Output

`ps2ui-dev`'s own transcript, unchanged. Its lines are on
[ps2ui-dev](page:cli/ps2ui-layout#ps2ui-dev).

```console
$ ps2ui dev --screen library --once
...
built in 320ms — 89 commands, 9 focusables, 28 warnings -> build/dev/preview.png
```

### Exit codes

| code | when |
|---|---|
| 0 | the build succeeded, or the watch loop was stopped |
| 1 | the project or the screen name is refused, or the build failed |
| 2 | argparse rejected the command line |

Naming no screen in a project with several is an error that lists them.

```console
$ ps2ui dev --once
ps2ui: ps2ui dev watches one screen and this project has 2. Name one: ps2ui dev --screen <name>, where <name> is one of: library, saves
```

### Files written

| path |
|---|
| `<build>/dev/<screen>.json` |
| `<build>/dev/ui.uib` |
| `<build>/dev/preview.png` |

```console
$ find build | sort
build
build/dev
build/dev/library.json
build/dev/preview.png
build/dev/ui.uib
build/library.json
build/preview.png
build/saves.json
build/states.png
build/ui.uib
```

`dev` and `serve` keep their own directories so that neither clobbers the
blob `ps2ui build` wrote.

## How build finds the compiler

The layout compiler is a Node package, so `build` and `dev` reach out of the
Python process to run it. They look in three places, in this order.

| order | where | condition |
|---|---|---|
| 1 | `$PS2UI_LAYOUT` | set; split on spaces and used as the command |
| 2 | `ps2ui-layout` on `PATH` | found by `shutil.which` |
| 3 | `packages/layout/bin/ps2ui-layout.js` beside the installed baker | the file exists and `node` is on `PATH` |

`dev` builds its command from the same list and swaps `ps2ui-layout` for
`ps2ui-dev` in it. The third entry is the checkout case. It exists for people
who have the repository, and is never assumed for anyone else.

When none of the three answers, the command refuses with the install line.

```console
$ env -i PATH=/usr/bin:/bin HOME=/root PYTHONPATH=/home/user/OPHTML/packages/baker /usr/bin/python3 -m ps2ui_bake.ps2ui build
ps2ui: cannot find ps2ui-layout, which compiles the HTML and CSS.
  Install it:      npm install -g @ophtml/layout
  Or point at it:  PS2UI_LAYOUT='node /path/to/ps2ui-layout.js'
  (ps2ui-bake is the Python half and is already here; the compiler is the Node half.)
```

An override that runs and fails is reported as a compiler failure, not as a
missing install.

```console
$ PS2UI_LAYOUT=/bin/false ps2ui build
ps2ui: ps2ui-layout failed on ui/library.html (exit 1)
```

## From a checkout

Pages show the installed spelling. A clone that has not installed the
packages runs the same programs through the commands below. The examples'
`build.sh` scripts and CI use the Python column.

| command | checkout spelling |
|---|---|
| `ps2ui` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui` |
| `ps2ui-bake` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake` |
| `ps2ui-check` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.check` |
| `ps2ui-fontgen` | `PYTHONPATH=packages/baker python3 -m ps2ui_bake.fontgen` |
| `ps2ui-layout` | `node packages/layout/bin/ps2ui-layout.js` |
| `ps2ui-dev` | `node packages/layout/bin/ps2ui-dev.js` |

Run these from the repository root.

```console
$ PYTHONPATH=packages/baker python3 -m ps2ui_bake.ps2ui --version
ps2ui 0.8.0.dev0
$ node packages/layout/bin/ps2ui-layout.js --version
ps2ui-layout 0.8.0-dev.0
```

The two numbers differ in spelling because one is a Python version and the
other is an npm version. `tools/check-versions.py` holds them together.

## Related pages

| page | why |
|---|---|
| [The project file](page:authoring/project-file#reference-table) | every key this command forwards |
| [ps2ui-layout and ps2ui-dev](page:cli/ps2ui-layout#options) | the compiler behind `build` and `dev` |
| [ps2ui-bake](page:cli/ps2ui-bake#options) | the baker behind `build` |
| [ps2ui-check](page:cli/ps2ui-check#options) | the validator behind `check` |
| [ps2ui-fontgen](page:cli/ps2ui-fontgen#options) | the single-face tool behind `fontgen` |
| [Previewer](page:cli/previewer#options) | the page `serve` answers |
| [Integrating the runtime](page:runtime/integrating#what-it-is) | what to do with the files `vendor-runtime` writes |
