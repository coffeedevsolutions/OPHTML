---
id: cli/ps2ui-layout
title: ps2ui-layout and ps2ui-dev
description: Compile one screen's HTML and CSS into ui.json, or watch the pair and rebake the blob and preview on every save.
section: cli
order: 31
version: 0.7.0
sources: [packages/layout/bin/ps2ui-layout.js, packages/layout/bin/ps2ui-dev.js, packages/layout/src/index.js, packages/layout/src/aspect.js, packages/layout/src/lint.js, packages/layout/package.json, packages/layout/test/cli.test.js, packages/layout/test/fonts.test.js, packages/baker/ps2ui_bake/ps2ui.py, examples/memcard/ps2ui.json, examples/memcard/build.sh, fonts/fonts.json, README.md]
---

# ps2ui-layout and ps2ui-dev

`ps2ui-layout` compiles one HTML file and one CSS file into the [IR](page:reference/ir-format#layout). `ps2ui-dev` runs the same compiler in a loop, bakes the result, and refreshes a preview PNG. Both ship in `@ophtml/layout` and read their version from its `package.json`. `ps2ui build` and `ps2ui dev` wrap them; see [ps2ui](page:cli/ps2ui).

## Synopsis

```
usage: ps2ui-layout <page.html> <page.css> -o <ui.json> [--mode ntsc|ntsc16x9|pal|pal16x9] [--display-aspect W:H] [--canvas WxH] [--font-dir DIR] [--fonts fonts.json] [--focus-wrap] [--strict] [--min-font-size PX] [--version]
```

The usage line above is what `ps2ui-layout --help` prints. Run it on one screen of the memcard example:

```sh
ps2ui-layout examples/memcard/ui/library.html examples/memcard/ui/library.css -o build/library.json
```

One invocation compiles one screen. A project with several screens runs the compiler once per HTML file, then hands every IR file to `ps2ui-bake`.

## Options

Every flag is optional except `-o`. The two positionals are the HTML file and the CSS file, in that order.

| flag | argument | default | effect |
|---|---|---|---|
| `-o` | path to `ui.json` | none, required | Where the IR goes. Missing parent directories are created. |
| `--mode` | `ntsc`, `ntsc16x9`, `pal`, `pal16x9` | `ntsc` geometry | Sets canvas size and display aspect from the mode table below. See [video modes](page:authoring/video-modes#reference-table). |
| `--display-aspect` | `W:H`, for example `16:9` | `4:3` | Sets the panel aspect alone. Overrides the aspect `--mode` set. |
| `--canvas` | `WxH`, for example `640x448` | `640x448` | Sets the framebuffer size alone. Overrides the size `--mode` set. |
| `--font-dir` | directory | `fonts/` three levels above `src/` | Reads `default.metrics.json` and `default-bold.metrics.json` from that directory. |
| `--fonts` | `fonts.json` | none | Reads the `metrics` path of the `regular` and `bold` faces from the manifest `ps2ui-bake` reads. See [text and fonts](page:authoring/text-and-fonts#reference-table). |
| `--focus-wrap` | none | off | Adds wrap-around edges to the focus graph. See [focus and navigation](page:authoring/focus-and-navigation#wrap). |
| `--strict` | none | off | Exits 1 when the compile produced any warning. See [CRT linter](page:authoring/crt-linter#strict). |
| `--min-font-size` | positive integer, px | `14` | Replaces the floor the `min-font-size` lint checks against. See [CRT linter](page:authoring/crt-linter#reference-table). |
| `-h`, `--help` | none | | Prints the usage line and exits 0. |
| `-V`, `--version` | none | | Prints `ps2ui-layout <version>` on stdout and exits 0. |

### Modes

`--mode` looks up one row of this table, from [aspect.js](repo:packages/layout/src/aspect.js#L47). The pixel aspect ratio is the display aspect divided by the canvas aspect. A 16:9 row draws each pixel wider than it is tall.

| mode | canvas | display aspect | par | display size |
|---|---|---|---|---|
| `ntsc` | 640x448 | 4:3 | 0.9333 | 597x448 |
| `ntsc16x9` | 640x448 | 16:9 | 1.2444 | 796x448 |
| `pal` | 640x512 | 4:3 | 1.0667 | 683x512 |
| `pal16x9` | 640x512 | 16:9 | 1.4222 | 910x512 |

The `par` and `display size` columns are the `canvas` block each mode wrote when the memcard library screen was compiled under it:

```sh
for m in ntsc ntsc16x9 pal pal16x9; do
  ps2ui-layout examples/memcard/ui/library.html examples/memcard/ui/library.css -o modes/$m.json --mode $m 2>/dev/null
  python3 -c "import json; print('$m', json.load(open('modes/$m.json'))['canvas'])"
done
```

```
ntsc {'w': 640, 'h': 448, 'displayAspect': [4, 3], 'par': 0.9333, 'display': {'w': 597, 'h': 448}}
ntsc16x9 {'w': 640, 'h': 448, 'displayAspect': [16, 9], 'par': 1.2444, 'display': {'w': 796, 'h': 448}}
pal {'w': 640, 'h': 512, 'displayAspect': [4, 3], 'par': 1.0667, 'display': {'w': 683, 'h': 512}}
pal16x9 {'w': 640, 'h': 512, 'displayAspect': [16, 9], 'par': 1.4222, 'display': {'w': 910, 'h': 512}}
```

### Font resolution

The compiler needs metrics for a regular and a bold face. It resolves them in this order.

| given | reads | on failure |
|---|---|---|
| `--fonts fonts.json` | `regular.metrics` and `bold.metrics`, relative to the manifest | names the missing face, the weight, and the `ps2ui-fontgen` command |
| `--font-dir DIR` | `DIR/default.metrics.json` and `DIR/default-bold.metrics.json` | names the missing file, both filenames, and both flags |
| neither | the same two filenames in `fonts/` three levels above `src/` | as above; the directory exists only in a checkout |

The `ttf` entries in the manifest are ignored here. Only the baker rasterizes. Pass the same manifest to both tools so layout measures with the face the baker draws.

## Output

Every line except `--version` goes to stderr. The IR is the only thing written to disk.

| line | when |
|---|---|
| `warning: <rule>: <message>` | once per compile warning, before the summary |
| `ps2ui-layout: N paint commands, N focusables -> <out>` | after the IR is written |
| `ps2ui-layout: --strict: N warning(s)` | after the summary, only with `--strict` and at least one warning |
| `error: <message>` | a compile failure; nothing is written |
| `ps2ui-layout: --min-font-size takes a positive integer` | the flag's value is not a positive integer |

The memcard library screen compiles with 28 warnings:

```sh
ps2ui-layout examples/memcard/ui/library.html examples/memcard/ui/library.css -o out/nested/library.json
```

```
warning: overscan: text "PS2" at (28,25) leaves the title-safe area; a CRT may crop it
warning: min-font-size: "MEMORY CARD" is 12px; below 14px is unreadable from a couch
warning: overscan: text "MEMORY CARD" at (28,59) leaves the title-safe area; a CRT may crop it
warning: min-font-size: "CARD 1" is 13px; below 14px is unreadable from a couch
...
warning: min-font-size: "△ Options" is 13px; below 14px is unreadable from a couch
ps2ui-layout: 89 paint commands, 9 focusables -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/out/nested/library.json
```

A screen with one 10px text run, compiled with `--strict`, prints the extra last line and exits 1:

```
warning: min-font-size: "Tiny text" is 10px; below 14px is unreadable from a couch
warning: overscan: text "Tiny text" at (0,1) leaves the title-safe area; a CRT may crop it
ps2ui-layout: 2 paint commands, 0 focusables -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/small/small.json
ps2ui-layout: --strict: 2 warning(s)
```

The IR is still written on that path. `--strict` changes the exit status, not the file.

A container with two children and no `flex-direction` is a compile error:

```
error: layout: 1 container(s) lay out two or more children without stating flex-direction:
  <screen> line 1 (2 children)
There is no default. CSS's initial value is row, ps2ui once used column, so either silent answer is wrong for half of all authors — add flex-direction: row or column to each.
```

## Exit codes

| code | condition |
|---|---|
| 0 | the IR was written, with or without warnings |
| 1 | a compile error, or `--strict` with one or more warnings |
| 2 | wrong positional count, no `-o`, unknown `--mode`, malformed `--canvas`, or `--min-font-size` not a positive integer |

Usage errors print the usage line. Each row above was produced in this session; the facts file lists the runs.

A malformed `--display-aspect` such as `16x9` is not caught by the argument parser. Node prints a stack trace from `aspect.js` and exits 1. Write the ratio with a colon.

## Files written

| file | content |
|---|---|
| the `-o` path | the IR, `JSON.stringify(ir, null, 1)`, one-space indent |

Missing parent directories are created first, so `-o build/library.json` works in a tree with no `build/`. The run above wrote 31443 bytes into a two-level missing path.

## Related pages

- [ps2ui](page:cli/ps2ui) for `ps2ui build`, which runs this compiler once per screen from `ps2ui.json`.
- [ui.json](page:reference/ir-format#layout) for what the output contains.
- [Video modes](page:authoring/video-modes#reference-table) for choosing a mode.
- [CRT linter](page:authoring/crt-linter#reference-table) for every warning the compiler can print.

# ps2ui-dev

`ps2ui-dev` compiles one screen, spawns `ps2ui-bake` on the result, and writes a preview PNG. Without `--once` it then watches the HTML, the CSS, and the HTML's directory, and rebuilds on every change.

## Synopsis

```
usage: ps2ui-dev <page.html> <page.css> -o <outdir> [--mode ntsc|pal] [--canvas WxH] [--font-dir DIR] [--fonts fonts.json] [--focus-wrap] [--strict] [--min-font-size PX] [--montage] [--palettize-images] [--once] [--version]
```

That is the `ps2ui-dev --help` output. The usage line is short by two facts: `--mode` accepts all four modes from the table above, and `--display-aspect W:H` is accepted too. Build the memcard library screen once:

```sh
ps2ui-dev examples/memcard/ui/library.html examples/memcard/ui/library.css -o dev --once --fonts fonts/fonts.json
```

The baker is spawned as `python3 -m ps2ui_bake` with `PYTHONPATH` pointing at the sibling `packages/baker` directory. Run it from a checkout, or with `ophtml` installed.

## Options

`-o` names a directory here, not a file.

| flag | argument | default | effect |
|---|---|---|---|
| `-o` | directory | none, required | Created if missing. Every file below lands in it. |
| `--mode` | `ntsc`, `ntsc16x9`, `pal`, `pal16x9` | `ntsc` geometry | As for `ps2ui-layout`. |
| `--display-aspect` | `W:H` | `4:3` | As for `ps2ui-layout`. Not listed in the usage line. |
| `--canvas` | `WxH` | `640x448` | As for `ps2ui-layout`. |
| `--font-dir` | directory | `fonts/` three levels above `src/` | As for `ps2ui-layout`. Not forwarded to the baker. |
| `--fonts` | `fonts.json` | none | Used by the compiler and forwarded to the baker as `--fonts`. |
| `--focus-wrap` | none | off | As for `ps2ui-layout`. |
| `--strict` | none | off | A compile with any warning fails before the bake; `--once` exits 1. See below. |
| `--min-font-size` | positive integer, px | `14` | Replaces the floor the `min-font-size` lint checks against, as for `ps2ui-layout`. |
| `--montage` | none | off | Adds `--montage states.png` to the bake. |
| `--palettize-images` | none | off | Forwarded to the bake as `--palettize-images`. See [ps2ui-bake](page:cli/ps2ui-bake#options). |
| `--once` | none | off | Build one time and exit with the build status. |
| `-h`, `--help` | none | | Prints the usage line and exits 0. |
| `-V`, `--version` | none | | Prints `ps2ui-dev <version>` on stdout and exits 0. |

### Strict and the font floor

In 0.6.0, `ps2ui-dev` accepted both flags and applied neither. Fixed in 0.7.0: both flags reach the linter the way they do in `ps2ui-layout`. The memcard library screen shows the floor moving: both tools double their `min-font-size` warnings at a 40px floor.

```sh
ps2ui-layout examples/memcard/ui/library.html examples/memcard/ui/library.css -o floor/layout14.json 2>&1 | grep -c "min-font-size:"
ps2ui-layout examples/memcard/ui/library.html examples/memcard/ui/library.css -o floor/layout40.json --min-font-size 40 2>&1 | grep -c "min-font-size:"
ps2ui-dev examples/memcard/ui/library.html examples/memcard/ui/library.css -o floor/dev14 --once 2>&1 | grep -c "  warning: min-font-size:"
ps2ui-dev examples/memcard/ui/library.html examples/memcard/ui/library.css -o floor/dev40 --once --min-font-size 40 2>&1 | grep -c "  warning: min-font-size:"
```

```
20
40
20
40
```

`--strict` turns a compile with warnings into a failed build. The warnings print, a strict line follows, the baker is not spawned, and `--once` exits 1. A page with one 8px text run:

```
  warning: min-font-size: "tiny text" is 8px; below 14px is unreadable from a couch
ps2ui-dev: --strict: 1 warning(s)
```

Without `--once` the loop stays up and the next saved change rebuilds. `--min-font-size 0` or a non-number exits 2 with `ps2ui-dev: --min-font-size takes a positive integer`.

## Output

All lines go to stderr. The baker's own transcript is inherited and appears between the compile and the `built` line; [ps2ui-bake](page:cli/ps2ui-bake#output) documents it.

| line | when |
|---|---|
| `layout error: <message>` | the compile threw; no files are written for this build |
| `ps2ui-dev: --strict: N warning(s)` | with `--strict`, after the warning list; the IR file was written, the baker was not spawned |
| `bake failed` | the baker exited non-zero; the IR file was written, the blob and preview were not refreshed |
| `built in <n>ms — N commands, N focusables, N warning(s) -> <outdir>/preview.png` | both stages succeeded |
| `  warning: <rule>: <message>` | once per warning, after the `built` line |
| `watching <dir> — ctrl-c to stop` | once, after the first build, without `--once` |
| `<file> changed` | 120 ms after the last filesystem event, before each rebuild |

The `--once` run above, with the baker's texture and budget lines and the warning list trimmed:

```
warning (layout library): overscan: text "PS2" at (28,25) leaves the title-safe area; a CRT may crop it
...
ps2ui-bake: 1 screen(s), 686 records, 10 textures (112 KiB baked), 1 CLUTs -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/dev/ui.uib
ps2ui-bake: arena 1451 bytes (static uint8_t arena[1451] __attribute__((aligned(16))))
ps2ui-bake: preview -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/dev/preview.png
built in 183ms — 89 commands, 9 focusables, 28 warnings -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/dev/preview.png
  warning: overscan: text "PS2" at (28,25) leaves the title-safe area; a CRT may crop it
  warning: min-font-size: "MEMORY CARD" is 12px; below 14px is unreadable from a couch
...
```

A watch run on the 10px screen, with a line appended to its CSS after the first build:

```
built in 113ms — 2 commands, 0 focusables, 2 warnings -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/watch2-out/preview.png
  warning: min-font-size: "Tiny text" is 10px; below 14px is unreadable from a couch
  warning: overscan: text "Tiny text" at (0,1) leaves the title-safe area; a CRT may crop it
watching /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/watch2 — ctrl-c to stop
small.css changed
built in 84ms — 2 commands, 0 focusables, 1 warning -> /tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/cli/ps2ui-layout/watch2-out/preview.png
  warning: overscan: text "Tiny text" at (0,0) leaves the title-safe area; a CRT may crop it
```

The watch covers the HTML's whole directory, recursively. Keep `-o` outside it. An output directory inside the watched tree retriggers a build on every file it writes.

## Exit codes

| code | condition |
|---|---|
| 0 | `--once` and both stages succeeded |
| 1 | `--once` and the compile or the bake failed |
| 2 | wrong positional count, no `-o`, unknown `--mode`, or malformed `--canvas` |

Without `--once` the process runs until interrupted, and a failed rebuild is reported on stderr and waited out.

## Files written

| file | content |
|---|---|
| `<outdir>/<html stem>.json` | the IR, named after the HTML file so the blob's screen name matches |
| `<outdir>/ui.uib` | the baked blob |
| `<outdir>/preview.png` | the baker's preview render |
| `<outdir>/states.png` | the focus-state montage, only with `--montage` |

The listing after the `--once` run with `--montage`:

```sh
ls dev-montage
```

```
library.json
preview.png
states.png
ui.uib
```

`ps2ui dev` chooses `<build dir>/dev` as the output directory, so a watch loop never overwrites the blob `ps2ui build` wrote.

## Related pages

- [ps2ui](page:cli/ps2ui) for `ps2ui dev`, which fills every flag above from `ps2ui.json`.
- [ps2ui-bake](page:cli/ps2ui-bake#output) for the transcript between the compile and the `built` line.
- [Previewer](page:cli/previewer#the-page) for the browser loop, which serves the same preview with an inspector.
- [Text and fonts](page:authoring/text-and-fonts#reference-table) for the manifest both stages share.
