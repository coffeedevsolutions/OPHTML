---
id: authoring/images
title: Images
description: How an img element finds its PNG, takes its size, and bakes into a PSMCT32 or PSMT8 texture.
section: authoring
order: 14
version: 0.6.0
sources: [packages/layout/src/image.js, packages/layout/src/box.js, packages/layout/src/flex.js, packages/layout/src/index.js, packages/layout/test/layout.test.js, packages/baker/ps2ui_bake/quads.py, packages/baker/ps2ui_bake/vram.py, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/gs.py, packages/baker/ps2ui_bake/preview.py, packages/baker/tests/test_baker.py, examples/channel6/ui/games.html, examples/channel6/ui/channel6.css, examples/channel6/ui/assets/make_assets.py, examples/channel6/ps2ui.json, examples/channel6/build.sh]
---

# Images

`<img>` bakes a PNG into the blob as a texture. `ps2ui-layout` reads the file's header for its size and records the resolved path. `ps2ui-bake` decodes the pixels and packs them into `ui.uib`. The console opens no files.

## What it is

One `<img>` becomes one textured quad. The source is a PNG, and nothing else is read at build time.

The baker writes the quad's texture in one of two GS formats. PSMCT32 spends 32 bits per texel and keeps every colour the file had. PSMT8 spends 8 bits per texel and reads its colours from a 256-entry CLUT. The `palettize` attribute asks for PSMT8. Both formats are described in [.uib](page:reference/uib-format#texture-entry).

The channel6 games screen draws six covers, every one of them palettized:

![channel6 games screen, root theme, 4:3, initial state: six palettized covers in a grid beside the details panel](../assets/authoring/images/covers.png)

The markup is [games.html](repo:examples/channel6/ui/games.html#L19). The art comes from [make_assets.py](repo:examples/channel6/ui/assets/make_assets.py), which draws flat shapes with no antialiasing so each cover stays inside 256 colours.

## Minimal example

Keep the art in a folder beside the document that names it.

```html
<div class="tile">
  <img class="cover" src="assets/cover.png" palettize>
</div>
```

```css
.tile { padding: 16px; background: #10182c; }
.cover { width: 96px; }
```

Compile it:

```
$ ps2ui-layout ui.html ui.css --fonts fonts/fonts.json -o ui.json
ps2ui-layout: 2 paint commands, 0 focusables -> ui.json
```

The file is 160x96 and the sheet states one axis. The other follows from the aspect ratio:

```
$ python3 -c "import json;c=[c for c in json.load(open('ui.json'))['commands'] if c['op']=='image'][0];print(c['w'], c['h'])"
96 58
```

## Reference table

| attribute or flag | effect |
|---|---|
| `src="<path>"` | The PNG to bake. A relative path resolves against the directory of the HTML file, not the working directory. An absolute path is used as written. |
| `palettize` | Bakes this image as PSMT8 with its own 256-entry CLUT. Refused on a streamed slot. |
| `data-tex-slot="<name>"` | Reserves a slot the app fills at runtime. Excludes both `src` and `palettize`. Listed in [HTML](page:authoring/html#reference-table). |
| `width`, `height` in CSS | Set the laid-out size. [CSS](page:authoring/css#reference-table) has the accepted units. |
| `--palettize-images` | A [ps2ui-bake](page:cli/ps2ui-bake#options) flag. Bakes every image in the run as PSMT8. |

## Behaviour

### Sizing

An `<img>` is a replaced element. What the sheet states decides which of three cases applies.

| CSS on the element | laid-out size |
|---|---|
| neither `width` nor `height` | the file's own pixels, plus padding and border |
| one of the two | the stated axis, and the other from the intrinsic aspect ratio, rounded half up |
| both | exactly what the sheet states |

Flex never stretches an image. A replaced element under `align-items: stretch` keeps its aspect ratio instead of distorting to fill the line. Give it both axes to fill a row.

### Pre-scaling and sharing

The baker resizes every image to its laid-out size before it packs texels. The texture is the size of the quad, and the GS does no scaling at draw time. Author art at the size it is drawn, and the resample never runs.

The texture cache is keyed by path, width, height and palettize state. Two elements naming one file at one size share a texture. The same file at two sizes is two textures:

```
$ ps2ui-bake ui.json -o ui.uib --fonts fonts/fonts.json
...
  tex[ 0] PSMCT32    64x48   baked       12288 B payload ->   16384 B in pages
  tex[ 1] PSMCT32    32x24   baked        3072 B payload ->    8192 B in pages
...
ps2ui-bake: 1 screen(s), 3 records, 2 textures (15 KiB baked), 0 CLUTs -> ui.uib
```

Three `<img>` elements on one file, two of them at 64x48 and one at 32x24, produced two textures.

### Palettize

`palettize` on one element and `--palettize-images` over the whole run both select PSMT8. They disagree about an already-indexed PNG.

| source PNG | with `palettize` on the element | with `--palettize-images` alone |
|---|---|---|
| any non-indexed mode | quantized to at most 256 colours, then baked PSMT8 | the same |
| indexed, file size equals laid-out size | baked verbatim, keeping its own indices and its own palette | baked verbatim |
| indexed, file size differs from laid-out size | build error, and no blob is written | warning, then requantized |

The attribute is a claim about one asset, so resizing it silently would destroy the thing that was asked for. The flag is a request for VRAM across the run, and its author made no claim about any one file.

A palette shorter than 256 entries is padded with zeros. The runtime permutes all 256 entries when it uploads a CLUT, so a short one would walk off the end of the table. Every palettized image carries a CLUT of its own; palettized images do not share one.

Thirteen cases cover this in `TestImages`:

```
$ cd packages/baker && python3 -m unittest discover -s tests -k TestImages
...
Ran 13 tests in 0.079s

OK
```

### What it costs

PSMT8 costs a quarter of PSMCT32 per texel. The two bakes below run over one IR. It is the channel6 games screen compiled with the `palettize` attribute removed, so the flag is the only difference:

```
$ ps2ui-bake games-plain.json -o off.uib --fonts fonts/fonts.json
...
  tex[ 6] PSMCT32    96x58   baked       22272 B payload ->   32768 B in pages
...
  textures 352256 B of 753664 B budget (46%)
$ ps2ui-bake games-plain.json -o on.uib --fonts fonts/fonts.json --palettize-images
...
  tex[ 6] PSMT8      96x58   baked        5568 B payload ->    8192 B in pages
...
  textures 253952 B of 753664 B budget (33%)
```

One 96x58 cover fell from 22272 B of texels to 5568 B. Each palettized image then adds 1024 B of CLUT payload. The `in pages` column is the budget model, which charges whole 8 KiB pages and is deliberately pessimistic. [VRAM budget](page:authoring/vram-budget#behaviour) has that model and the rest of the breakdown.

### Streamed slots

Art the app supplies at runtime is a streamed slot rather than a baked image. Write `<img data-tex-slot="cover">` with an explicit `width` and `height` in CSS, and no `src`. The blob carries the geometry, the name and a PSMCT32 reservation, and no texels. [Streaming art](page:runtime/streaming-art#what-it-is) has the runtime call and the host-side conversion.

## Limits and errors

Any format other than PNG is refused at compile time, with the resolved path in the message:

```
$ ps2ui-layout jpg.html ui.css --fonts fonts/fonts.json -o jpg.json
error: image: "/tmp/claude-0/-home-user-OPHTML/6b0c72b8-d98f-5f58-b749-f9808bb620d6/scratchpad/authoring/images/mini/assets/cover.jpg" is not a PNG — only PNG is supported at build time; convert other formats before compiling
```

The first seven messages below are compile errors from `ps2ui-layout`. The last three come from `ps2ui-bake`.

| message | cause |
|---|---|
| `image: cannot read "<path>": ENOENT` | The `src` names a file that is not there. |
| `image: "<path>" is not a PNG — only PNG is supported at build time; convert other formats before compiling` | Any other format, JPEG included. |
| `image: "<path>": malformed PNG (IHDR not first chunk)` | The chunk after the 8-byte signature is not `IHDR`. |
| `image: "<path>": zero-sized PNG` | The IHDR width or height is 0. |
| `layout: <img> on line <n> has no src attribute (or data-tex-slot, ...)` | An `<img>` carrying neither. |
| `layout: <img data-tex-slot="<name>"> needs an explicit width and height ...` | A streamed slot with either axis unset. A slot has no file to measure. |
| `layout: <img> on line <n>: palettize is not supported on a streamed slot ...` | `palettize` together with `data-tex-slot`. |
| `image: <path> is an indexed PNG at <w>x<h> but is laid out at <w>x<h>. ...` | `palettize` on an indexed PNG at any other size. |
| `warning: <path> is an indexed PNG at <w>x<h> laid out at <w>x<h>; --palettize-images requantized it, ...` | Warning. The same mismatch under the flag alone. |
| `image: cannot decode <path>: <reason>` | Pillow refused a file that passed the header check at compile time. |

Two silences are worth writing down. An image whose laid-out width or height computes to 0 emits no texture and no draw record, and nothing says so. The compile stage reads the IHDR only. A PNG with a valid header and a corrupt body passes `ps2ui-layout` and fails in `ps2ui-bake`.

## Related pages

| page | why |
|---|---|
| [CSS](page:authoring/css#reference-table) | the units `width` and `height` accept, and the flex rules around them |
| [VRAM budget](page:authoring/vram-budget#behaviour) | what a texture costs and what the bake refuses |
| [.uib](page:reference/uib-format#texture-entry) | how a texture and its CLUT sit in the blob |
| [ps2ui-bake](page:cli/ps2ui-bake#options) | `--palettize-images` and the rest of the transcript |
| [Streaming art](page:runtime/streaming-art#what-it-is) | filling a `data-tex-slot` from the app |
