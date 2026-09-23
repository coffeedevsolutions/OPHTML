---
id: authoring/project-file
title: The project file
description: Every ps2ui.json key with its default and the tool it reaches, how paths resolve, and what the loader refuses.
section: authoring
order: 10
version: 0.8.0
sources: [packages/baker/ps2ui_bake/project.py, packages/baker/ps2ui_bake/ps2ui.py, packages/baker/ps2ui_bake/cli.py, packages/baker/tests/test_baker.py, packages/layout/bin/ps2ui-layout.js, packages/layout/bin/ps2ui-dev.js, packages/layout/src/index.js, examples/memcard/ps2ui.json, examples/opl-env/ps2ui.json, examples/channel6/ps2ui.json, examples/memcard/build.sh, examples/channel6/build.sh, docs/tutorial-uc3.md, CHANGELOG.md, CONTRIBUTING.md, .github/workflows/ci.yml, README.md]
---

# The project file

## What it is

`ps2ui.json` describes one blob. `ps2ui build` reads it, compiles every screen with `ps2ui-layout`, bakes the results with `ps2ui-bake` and writes the previews. `ps2ui check`, `ps2ui dev` and `ps2ui serve` read the same file. Two keys are required, `screens` and `css`. Every other key has a default. A key the loader does not know is an error that names the key.

The file has no variants block. A second blob from the same sources is a second `ps2ui build` with flags, see [-o moves the intermediates](#-o-moves-the-intermediates).

## Minimal example

The smallest project is two keys:

```json
{ "screens": ["ui/a.html"], "css": "ui/app.css" }
```

That file builds `build/ui.uib` with `build/preview.png` beside it. The memcard example adds a montage, [examples/memcard/ps2ui.json](repo:examples/memcard/ps2ui.json#L1):

```json
{
  "screens": ["ui/library.html", "ui/saves.html"],
  "css": "ui/library.css",
  "preview": "build/preview.png",
  "montage": "build/states.png"
}
```

Build it from the directory that holds it:

```sh
ps2ui build
```

Or name the file from anywhere. The last lines of the transcript name every file written:

```sh
ps2ui build memcard/ps2ui.json
```

```text
...
ps2ui-layout: 89 paint commands, 9 focusables -> build/library.json
...
ps2ui-layout: 43 paint commands, 7 focusables -> build/saves.json
...
ps2ui-bake: 2 screen(s), 1062 records, 11 textures (128 KiB baked), 1 CLUTs -> build/ui.uib
ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] __attribute__((aligned(16))))
ps2ui-bake: preview -> build/preview.png
ps2ui-bake: montage -> build/states.png
```

## Reference table

The reaches column names the tool under [ps2ui](page:cli/ps2ui#synopsis) that receives the key. The mapping lives in `compile_screens`, `bake_argv`, `cmd_check` and `cmd_dev` in [ps2ui.py](repo:packages/baker/ps2ui_bake/ps2ui.py#L205). The defaults live in `DEFAULTS` in [project.py](repo:packages/baker/ps2ui_bake/project.py#L39).

| key | type | default | reaches |
|---|---|---|---|
| `screens` | list of string or object | required | layout · bake · dev |
| `css` | string | required unless every screen sets its own | layout · dev |
| `fonts` | string | `fonts/fonts.json` beside the project if present, else the baker default | layout · bake · dev |
| `out` | string | `build/ui.uib` | [bake](page:cli/ps2ui-bake#options) · check · dev |
| `preview` | string or `false` | `build/preview.png` | [bake](page:cli/ps2ui-bake#options) |
| `montage` | string or `false` | none | [bake](page:cli/ps2ui-bake#options) |
| `previewDisplay` | string or `false` | none | [bake](page:cli/ps2ui-bake#options) |
| `mode` | string | none | [layout](page:cli/ps2ui-layout#options) · dev, see [video modes](page:authoring/video-modes#what-it-is) |
| `canvas` | string `WxH` | none | [layout](page:cli/ps2ui-layout#options) · dev |
| `displayAspect` | string `W:H` | none | [layout](page:cli/ps2ui-layout#options) · dev |
| `strict` | boolean | `false` | [layout](page:cli/ps2ui-layout#options) · [check](page:cli/ps2ui-check#options) · dev |
| `minFontSize` | integer px | none | [layout](page:cli/ps2ui-layout#options) · dev |
| `focusWrap` | boolean | `false` | [layout](page:cli/ps2ui-layout#options) · dev, per screen |
| `palettizeImages` | boolean | `false` | [bake](page:cli/ps2ui-bake#options) · dev |
| `vramBudget` | integer bytes | none | [bake](page:cli/ps2ui-bake#options) · [check](page:cli/ps2ui-check#options), see [VRAM budget](page:authoring/vram-budget#what-it-is) |

The test class behind the table ran in this session:

```sh
cd packages/baker/tests && python3 -m unittest test_baker.TestProjectFile -v
```

```text
...
Ran 17 tests in 0.440s

OK
```

An entry in `screens` is a path or an object. The object form takes these keys and no others:

| key | type | default | reaches |
|---|---|---|---|
| `html` | string | required | layout · dev |
| `css` | string | the top-level `css` | layout · dev |
| `focusWrap` | boolean | the top-level `focusWrap` | layout · dev |

The channel6 example uses the object form for one screen, [examples/channel6/ps2ui.json](repo:examples/channel6/ps2ui.json#L4):

```json
  "screens": [
    "ui/games.html",
    { "html": "ui/probe.html", "focusWrap": true }
  ],
```

## Behaviour

### Paths resolve against the project file

Every path in the file joins onto the directory that holds the file. The working directory plays no part. `ps2ui build` changes into that directory for the run, prints every path relative to it, and restores the previous directory before it returns. The build above ran from the repository root against a copy of memcard outside the tree. Its `build/` landed beside the project file:

```sh
ls memcard/build
```

```text
library.json
preview.png
saves.json
states.png
ui.uib
```

A screen's name is the HTML file's stem. The name is the intermediate's file stem and the screen's name inside the blob.

### Fonts

The `fonts` key names a manifest. Without it, `fonts/fonts.json` beside the project is used when that file exists. Without either, no `--fonts` is passed and the baker applies its own default, which is the repository's `fonts/fonts.json` and exists only in a checkout. The tutorial project sets no `fonts` key, [docs/tutorial-uc3.md](repo:docs/tutorial-uc3.md#L146); it relies on `ps2ui fontgen` having written `fonts/fonts.json` beside it. The three shipped examples set no `fonts` key either and build against the checkout default.

### A directory argument

A directory in place of the file means `<dir>/ps2ui.json`. `ps2ui check` accepts the same argument and never builds:

```sh
ps2ui check examples/memcard
```

```text
...
ok 63 - every texture is drawn or belongs to a font
1..63
# build/ui.uib: 640x448 at 4:3, 2 screen(s), 1062 commands, 11 textures, 6 slots
PASS: 63 checks, 0 error(s), 0 warning(s)
```

### The output path moves the intermediates

`ps2ui build -o NEW` writes the blob at NEW and moves the per-screen IR files with it. The IR files land in NEW's directory. Their stems take a suffix derived from the two blob stems, `set_out_override` in [project.py](repo:packages/baker/ps2ui_bake/project.py#L209):

| override | intermediate for screen `games` | rule |
|---|---|---|
| `-o dist/ui.uib` | `dist/games.json` | same stem as `out`, no suffix |
| `-o build/ui-16x9.uib` | `build/games-16x9.json` | NEW's stem extends the `out` stem, the remainder is the suffix |
| `-o build/widescreen.uib` | `build/games-widescreen.json` | no shared stem, the whole NEW stem is the suffix |

The previews keep their configured names. Rename them with `--preview`, `--montage` and `--preview-display`, or pass `none` to skip one. This is the second build line of [examples/channel6/build.sh](repo:examples/channel6/build.sh#L26), run here against a copy of channel6 that had already been built once:

```sh
ps2ui build channel6/ps2ui.json --mode ntsc16x9 -o build/ui-16x9.uib \
    --preview-display build/preview-16x9-display.png --preview none --montage none
```

```text
...
ps2ui-layout: 90 paint commands, 9 focusables -> build/games-16x9.json
...
ps2ui-layout: 99 paint commands, 8 focusables -> build/probe-16x9.json
...
ps2ui-bake: 2 screen(s), 1242 records, 25 textures (180 KiB baked), 9 CLUTs -> build/ui-16x9.uib
ps2ui-bake: arena 10624 bytes (static uint8_t arena[10624] __attribute__((aligned(16))))
ps2ui-bake: display preview 796x448 at 16:9 -> build/preview-16x9-display.png
```

```sh
ls channel6/build
```

```text
games-16x9.json
games.json
preview-16x9-display.png
preview-display.png
preview.png
probe-16x9.json
probe.json
states.png
ui-16x9.uib
ui.uib
```

Nothing the first build wrote was replaced.

### Overrides on ps2ui build

`ps2ui build` takes `--mode`, `-o`, `--preview`, `--montage` and `--preview-display`. Each replaces the key of the same name for that run. The three preview flags accept `none`, which suppresses the file.

### Suppressing a preview in the file

Set `preview`, `montage` or `previewDisplay` to `false` to write no such file. A copy of memcard with `"preview": false` and no `montage` key wrote no PNG at all:

```sh
ls memcard2/build
```

```text
library.json
saves.json
ui.uib
```

### Keys that reach the checker

New in 0.6.0. `ps2ui check` forwards `strict` and `vramBudget` to `ps2ui-check`, so a project means the same thing to the build and to the check, [CHANGELOG.md](repo:CHANGELOG.md#L1387). The forwarded set is not a hand-written list. The test derives it from `DEFAULTS` and the checker's own `--help`, and fails when a key gains a checker flag and is not forwarded:

```sh
cd packages/baker/tests && python3 -m unittest \
    test_baker.TestProjectFile.test_every_project_key_the_checker_accepts_actually_reaches_it -v
```

```text
test_every_project_key_the_checker_accepts_actually_reaches_it (test_baker.TestProjectFile.test_every_project_key_the_checker_accepts_actually_reaches_it)
The mapping, enumerated rather than remembered. ... ok
```

## Limits and errors

Every refusal is one message with no traceback and exit status 1. An unknown key:

```sh
cat ps2ui.json
```

```json
{ "screens": ["ui/a.html"], "css": "ui/app.css", "colour": 1 }
```

```sh
ps2ui build ps2ui.json
```

```text
ps2ui: ps2ui.json: unknown key(s) 'colour'.
  A project takes: canvas, css, displayAspect, focusWrap, fonts, minFontSize, mode, montage, out, palettizeImages, preview, previewDisplay, screens, strict, vramBudget
```

The full list, each message produced in this session by `ps2ui build` over a project written to trigger it:

| message | cause | fix |
|---|---|---|
| `ps2ui: missing.json: no such project file.` followed by the two-key example | the path, or `<dir>/ps2ui.json`, does not exist | create the file or name the right directory |
| `ps2ui: bad-json.json: not valid JSON -- Expecting property name enclosed in double quotes: line 1 column 3 (char 2)` | the file does not parse | fix the JSON at the position named |
| `ps2ui: not-object.json: the top level must be an object` | the top level is a list or a scalar | wrap the keys in `{ }` |
| `ps2ui: no-screens.json: "screens" is required and must not be empty` | no `screens`, or an empty list | list at least one screen |
| `ps2ui: screens-string.json: "screens" must be a list` | `screens` is a string | write `"screens": ["ui/a.html"]` |
| `ps2ui: ps2ui.json: unknown key(s) 'colour'.` followed by the accepted list | a key outside the table above, including a misspelling | use a key from the list |
| `ps2ui: screens[0] is 7; a screen is a path, or an object with "html" and optionally "css" or "focusWrap"` | a screen entry that is neither a string nor an object | write a path or an object |
| `ps2ui: screens[0] has unknown key(s) 'focuswrap'; a screen takes css, focusWrap, html` | an object screen with a key outside the per-screen table | use `html`, `css` or `focusWrap` |
| `ps2ui: screens[0] has no "html"` | an object screen without `html` | add `html` |
| `ps2ui: screens[0] (ui/a.html) has no stylesheet: set "css" at the top level for every screen, or on this one` | no `css` at the top level and none on the screen | set `css` in either place |
| `ps2ui: build/ui.uib: no blob to check. Run `ps2ui build` first -- this does not build, so that a check can never report on a blob it just made and nobody has seen.` | `ps2ui check` on a project whose `out` does not exist | run `ps2ui build` |

One limit:

| limit | detail |
|---|---|
| one blob per file | a second blob is a second `ps2ui build` with `--mode`, `-o` and the preview flags |

## Related pages

- [ps2ui](page:cli/ps2ui#synopsis), the umbrella command and its subcommands
- [ps2ui-layout and ps2ui-dev](page:cli/ps2ui-layout#options), what `mode`, `canvas`, `displayAspect`, `strict`, `minFontSize` and `focusWrap` do
- [ps2ui-bake](page:cli/ps2ui-bake#options), what `out`, `preview`, `montage`, `previewDisplay`, `palettizeImages` and `vramBudget` do
- [ps2ui-check](page:cli/ps2ui-check#options), what `strict` and `vramBudget` do at check time
- [Video modes](page:authoring/video-modes#what-it-is), the values `mode` takes
- [VRAM budget](page:authoring/vram-budget#what-it-is), the number `vramBudget` overrides
