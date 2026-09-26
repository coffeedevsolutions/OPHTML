---
id: reference/ir-format
title: ui.json
description: The intermediate representation as the compiler emits it: every top-level key, every record field, the invariants and the version check.
section: reference
order: 50
version: 0.10.0
sources: [packages/layout/src/index.js, packages/layout/src/paint.js, packages/layout/src/focus.js, packages/layout/src/aspect.js, packages/layout/src/box.js, packages/layout/src/css.js, packages/layout/src/values.js, packages/layout/src/text.js, packages/layout/test/layout.test.js, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/quads.py, docs/format-ir.md]
---

# ui.json

## Layout

`ui.json` is the seam between the two build stages. [ps2ui-layout](page:cli/ps2ui-layout) writes it from one HTML file and one CSS file. [ps2ui-bake](page:cli/ps2ui-bake) reads it and produces the blob.

One `ui.json` describes one screen. Every geometry decision is already made. The baker never reads HTML, CSS or fonts to place anything.

The file is UTF-8 JSON with one object at the root. Key order is emission order and carries no meaning.

Compile the memcard library screen:

```sh
ps2ui-layout examples/memcard/ui/library.html examples/memcard/ui/library.css \
  --fonts fonts/fonts.json -o library.json
```

That run printed `ps2ui-layout: 89 paint commands, 9 focusables`. Abridged, with all but two commands, all but one node, and all but one warning elided:

```json
{
  "version": 1,
  "canvas": {
    "w": 640,
    "h": 448,
    "displayAspect": [4,3],
    "par": 0.9333,
    "display": { "w": 597, "h": 448 }
  },
  "fonts": {
    "regular": { "family": "DejaVu Sans", "weight": 400 },
    "bold": { "family": "DejaVu Sans", "weight": 700 }
  },
  "themes": ["root"],
  "commands": [
    {
      "op": "rect",
      "x": 0, "y": 0, "w": 640, "h": 448,
      "fill": [10,14,26,255],
      "fillVar": null,
      "fillThemes": [[10,14,26,255]],
      "borderWidth": 0,
      "borderColor": null,
      "borderColorVar": null,
      "borderColorThemes": null,
      "radius": 0,
      "state": "always",
      "focusId": null
    },
    {
      "op": "text",
      "x": 28, "y": 25,
      "text": "PS2",
      "size": 26,
      "weight": 700,
      "letterSpacing": 3,
      "color": [242,245,250,255],
      "colorVar": null,
      "colorThemes": [[242,245,250,255]],
      "state": "always",
      "focusId": null
    },
    ...
  ],
  "focus": {
    "nodes": [
      {
        "id": 9,
        "name": "nav-games",
        "rect": [28,92,128,39],
        "up": null, "down": 11, "left": null, "right": 28
      },
      ...
    ],
    "initial": 9
  },
  "slots": [
    {
      "name": "count",
      "placeholder": "6 titles",
      "x": 567, "textY": 31, "w": 45,
      "size": 13, "weight": 400, "lineHeight": 16,
      "align": "left", "letterSpacing": 0, "ellipsis": false,
      "capacity": 15,
      "focusId": null,
      "colorBase": [139,148,167,255],
      "colorFocus": [139,148,167,255],
      "colorBaseVar": null,
      "colorFocusVar": null,
      "colorBaseThemes": [[139,148,167,255]],
      "colorFocusThemes": [[139,148,167,255]]
    }
  ],
  "warnings": [
    "overscan: text \"PS2\" at (28,25) leaves the title-safe area; a CRT may crop it",
    ...
  ]
}
```

Every key is always present. An empty screen still carries `commands: []`, `slots: []`, `warnings: []` and `focus: {"nodes": [], "initial": null}`.

| field | type | meaning |
|---|---|---|
| `version` | integer | IR format version. Always `1`. |
| `canvas` | object | Canvas size and how it reaches a display. |
| `fonts` | object | The two font faces the text commands were measured with. |
| `themes` | array of string | Theme names, index-ordered, `root` first. |
| `commands` | array of object | The display list, in paint order. |
| `focus` | object | The focus graph and the starting node. |
| `slots` | array of object | The dynamic-text descriptors. |
| `warnings` | array of string | Compiler and linter messages. |

## Records

### canvas

`par` is the pixel aspect ratio. `display` is the size the canvas fills on a correctly configured display.

| field | type | meaning |
|---|---|---|
| `w` | integer | Canvas width in pixels. |
| `h` | integer | Canvas height in pixels. |
| `displayAspect` | `[num, den]` | The authored display aspect as an exact ratio. |
| `par` | number | `(num / den) / (w / h)`, rounded to four decimals. |
| `display.w` | integer | `round(h * num / den)`. |
| `display.h` | integer | Equal to `h`. |

With no `--mode`, `--canvas` or `--display-aspect`, the canvas is 640 by 448 at 4:3. The memcard compile above used none of them and printed:

```json
{"w":640,"h":448,"displayAspect":[4,3],"par":0.9333,"display":{"w":597,"h":448}}
```

The baker reads `canvas` and `canvas.displayAspect`. It ignores `par` and `display`, which exist so a consumer does not recompute them.

### fonts

| field | type | meaning |
|---|---|---|
| `regular.family` | string | Family name from the loaded metrics. |
| `regular.weight` | integer | Numeric weight of the regular face. |
| `bold.family` | string | Family name of the bold face. |
| `bold.weight` | integer | Numeric weight of the bold face. |

The memcard compile printed `{"regular":{"family":"DejaVu Sans","weight":400},"bold":{"family":"DejaVu Sans","weight":700}}`. Nothing downstream reads this block. It records which metrics produced the geometry.

### themes

| field | type | meaning |
|---|---|---|
| `themes` | array of string | One name per theme row, index-ordered. |
| `themes[0]` | string | Always `root`. |

A sheet with no `@theme` rule emits `["root"]`. The opl-env sheet declares one theme, and compiling its landing screen printed `["root","light"]`:

```sh
ps2ui-layout examples/opl-env/ui/landing.html examples/opl-env/ui/opl.css \
  --fonts fonts/fonts.json -o landing.json
```

`themes.length` is the width of every `*Themes` vector on every command and every slot. Names are build-time only. The blob stores a row count, and the runtime selects a row by index. See [theming](page:authoring/theming#behaviour).

### Fields on every command

| field | type | meaning |
|---|---|---|
| `op` | string | One of `rect`, `text`, `image`, `scissor_push`, `scissor_pop`. |
| `state` | string | One of `always`, `unfocused`, `focused`. |
| `focusId` | integer or null | The focus node this command belongs to. |

A box whose base paint and `:focus` paint differ emits two commands with identical geometry, one `unfocused` and one `focused`. Identical paints merge into a single `always` command. Count the states in the memcard screen:

```sh
node -e 'const c=require("./library.json").commands, n={};
for (const x of c) n[x.state]=(n[x.state]||0)+1; console.log(JSON.stringify(n))'
```

```
{"always":53,"unfocused":18,"focused":18}
```

### rect

| field | type | meaning |
|---|---|---|
| `x` `y` `w` `h` | integer | Border box, canvas coordinates. |
| `fill` | `[r,g,b,a]` or null | Fill colour in theme row 0. Null when nothing is painted. |
| `fillVar` | string or null | Custom property the fill was resolved from. |
| `fillThemes` | array of `[r,g,b,a]` | One fill per theme row. |
| `borderWidth` | integer | Border width in pixels. `0` when no border is painted. |
| `borderColor` | `[r,g,b,a]` or null | Border colour in theme row 0. |
| `borderColorVar` | string or null | Custom property the border colour came from. |
| `borderColorThemes` | array or null | One border colour per theme row. Null with no border. |
| `radius` | integer | Corner radius, clamped to `floor(min(w, h) / 2)`. |
| `keep` | `true` | Present only for an element with `data-keep`. |

A fill with alpha 0 becomes `fill: null`. A border with zero width or a transparent colour becomes `borderWidth: 0` and `borderColor: null`. A rect with neither a fill nor a border is not emitted at all. That decision reads theme row 0 only.

The opl-env landing page background resolves its fill from a custom property, so it carries a name and a two-row vector:

```json
{
  "op": "rect",
  "x": 0, "y": 0, "w": 640, "h": 448,
  "fill": [11,15,22,255],
  "fillVar": "--bg-page",
  "fillThemes": [[11,15,22,255],[244,246,250,255]],
  "borderWidth": 0,
  "borderColor": null,
  "borderColorVar": null,
  "borderColorThemes": null,
  "radius": 0,
  "state": "always",
  "focusId": null
}
```

### text

One command per laid-out line. An empty line emits nothing.

| field | type | meaning |
|---|---|---|
| `x` | integer | Pen start, canvas coordinates. |
| `y` | integer | Glyph box top: the line top plus `floor(leading / 2)`. |
| `text` | string | The line as laid out. |
| `size` | integer | Font size in pixels. |
| `weight` | integer | Numeric weight, picking the regular or bold face. |
| `letterSpacing` | integer | Extra advance per glyph, in pixels. |
| `color` | `[r,g,b,a]` | Colour in theme row 0. |
| `colorVar` | string or null | Custom property the colour came from. |
| `colorThemes` | array of `[r,g,b,a]` | One colour per theme row. |
| `nocontrast` | `true` | Present only for an element with `data-nocontrast`. |

`nocontrast` suppresses the contrast lint. The baker never reads it.

### image

An image has two forms. A baked image names a file on the build host. A streamed image names a texture the program fills at runtime. Both forms carry the same geometry, and `state` is always `always`.

| field | type | meaning |
|---|---|---|
| `x` `y` `w` `h` | integer | Content box, canvas coordinates. |
| `src` | string | Absolute build-host path to the PNG. Baked form. |
| `palettize` | boolean | Whether the baker converts to a paletted texture. Baked form. |
| `streamed` | `true` | Marks the streamed form. |
| `name` | string | Texture name the runtime addresses. Streamed form. |

Baked, from the opl-env landing compile:

```json
{
  "op": "image",
  "x": 258, "y": 121, "w": 28, "h": 28,
  "src": "/home/user/OPHTML/examples/channel6/ui/assets/cover-aurora.png",
  "palettize": true,
  "state": "always",
  "focusId": 34
}
```

Streamed, from the opl-env library compile:

```json
{
  "op": "image",
  "x": 44, "y": 63, "w": 28, "h": 28,
  "streamed": true,
  "name": "row-0-art",
  "state": "always",
  "focusId": 20
}
```

### The scissor ops

A push and pop pair brackets the children of every non-text box with `overflow: hidden`.

| field | type | meaning |
|---|---|---|
| `x` `y` `w` `h` | integer | Clip rectangle. `scissor_push` only. |
| `state` | string | Always `always`. |
| `focusId` | null | Always null. |

`scissor_pop` carries no geometry:

```json
{ "op": "scissor_push", "x": 188, "y": 150, "w": 112, "h": 18, "state": "always", "focusId": null }
{ "op": "scissor_pop", "state": "always", "focusId": null }
```

### focus node

`focus` is `{nodes, initial}`. Each node describes one focusable box and its four neighbours. See [focus and navigation](page:authoring/focus-and-navigation#behaviour).

| field | type | meaning |
|---|---|---|
| `id` | integer | Node id. Referenced by command `focusId` and by neighbours. |
| `name` | string | The element `id`, else its `name`, else `box<id>`. |
| `rect` | `[x, y, w, h]` | Border box of the focusable. |
| `up` `down` `left` `right` | integer or null | Neighbour node id, or null for a dead end. |
| `initial` | integer or null | The `autofocus` node, else the first node, else null. |

The memcard library screen has nine nodes, the first of which is:

```json
{ "id": 9, "name": "nav-games", "rect": [28,92,128,39], "up": null, "down": 11, "left": null, "right": 28 }
```

A screen with no focusable box emits `{"nodes": [], "initial": null}`.

### slot

A `data-slot` element emits a descriptor instead of text commands. The console draws its glyphs from the slot table.

| field | type | meaning |
|---|---|---|
| `name` | string | Slot name. Unique within the file. |
| `placeholder` | string | The authored text, laid out once at compile time. |
| `x` | integer | Left edge of the parent content box. |
| `textY` | integer | Glyph box top. |
| `w` | integer | Width of the parent content box. |
| `size` | integer | Font size in pixels. |
| `weight` | integer | Numeric weight. |
| `lineHeight` | integer | Line box height in pixels. |
| `align` | string | Text alignment inside `w`. |
| `letterSpacing` | integer | Extra advance per glyph. |
| `ellipsis` | boolean | Whether overflow is truncated with an ellipsis. |
| `capacity` | integer | Bytes reserved for the string. Defaults to 63. |
| `focusId` | integer or null | The focus node the slot sits inside. |
| `colorBase` | `[r,g,b,a]` | Unfocused colour, theme row 0. |
| `colorFocus` | `[r,g,b,a]` | Focused colour, theme row 0. |
| `colorBaseVar` | string or null | Custom property behind `colorBase`. |
| `colorFocusVar` | string or null | Custom property behind `colorFocus`. |
| `colorBaseThemes` | array of `[r,g,b,a]` | Unfocused colour per theme row. |
| `colorFocusThemes` | array of `[r,g,b,a]` | Focused colour per theme row. |

Every input to the pen travels with the slot, spacing and alignment included. A slot placeholder that wraps to more than one line is a compile error.

The opl-env landing screen resolves its subtitle from a custom property:

```json
{
  "name": "hero-sub",
  "placeholder": "412 titles across 3 sources",
  "x": 34, "textY": 57, "w": 572,
  "size": 14, "weight": 400, "lineHeight": 18,
  "align": "left", "letterSpacing": 0, "ellipsis": false,
  "capacity": 48,
  "focusId": null,
  "colorBase": [139,148,167,255],
  "colorFocus": [139,148,167,255],
  "colorBaseVar": "--ink-muted",
  "colorFocusVar": "--ink-muted",
  "colorBaseThemes": [[139,148,167,255],[90,100,120,255]],
  "colorFocusThemes": [[139,148,167,255],[90,100,120,255]]
}
```

### warnings

| field | type | meaning |
|---|---|---|
| `warnings[n]` | string | One diagnostic line. |

Order is fixed: repeat, CSS, box and focus warnings first, then lint lines as `<rule>: <message>`, then per-theme lint lines as `@theme <name>: <rule>: <message>`. Geometry lints are deduplicated across theme rows. The colour lints `contrast` and `ntsc-red-bleed` are not, because two rows can fail for different reasons.

The memcard compile shown under [Layout](#layout) emitted 28 lines, beginning:

```
overscan: text "PS2" at (28,25) leaves the title-safe area; a CRT may crop it
min-font-size: "MEMORY CARD" is 12px; below 14px is unreadable from a couch
```

`ps2ui-bake` reprints each one prefixed with `warning (layout <screen>):`.

## Invariants

A file that breaks any of these is a compiler defect, not authored input.

1. Every `x`, `y`, `w` and `h` on every command is an integer. Text advances are summed as integers, never as floats.
2. Every colour is `[r, g, b, a]` with integer channels from 0 to 255. CSS `opacity` is folded into the alpha channel of every theme row before emission.
3. Every `*Themes` vector is exactly `themes.length` long.
4. Element 0 of every `fillThemes`, `borderColorThemes`, `colorThemes`, `colorBaseThemes` and `colorFocusThemes` vector equals the scalar colour beside it.
5. `radius` never exceeds `floor(min(w, h) / 2)`.
6. Every neighbour id and every command `focusId` names a node in the same file.
7. Nodes appear in document order, so their ids ascend.
8. An `unfocused` command and its `focused` partner share geometry exactly. A `:focus` rule that changes a geometry property is a compile error, so both states share one layout.
9. `scissor_push` and `scissor_pop` are balanced, and depth returns to zero at the end of the display list.
10. Slot names are unique within a file. A duplicate is the compile error `layout: duplicate data-slot name "<n>"`.

`node --test packages/layout/test/layout.test.js` holds these, and passes 71 tests.

## Versioning

`version` is the integer `1`. The layout package writes `IR_VERSION` once and never compares it, so `ps2ui-layout` accepts nothing and rejects nothing on this field.

`ps2ui-bake` checks it before reading anything else. Set `version` to `2` in a copy and bake it:

```sh
ps2ui-bake library-v2.json -o v2.uib --fonts fonts/fonts.json
```

```
error: library-v2.json: IR version 2, expected 1
```

The command exits 1 and writes no blob.

`ui.json` is not a distribution format and carries no stability pledge. Regenerate it from source whenever either package changes. The pledge lives on the blob instead, whose layout is fixed at version 7. See [the .uib format](page:reference/uib-format#versioning).

One `ui.json` is one screen. Pass several to [ps2ui-bake](page:cli/ps2ui-bake#synopsis) and each becomes a named screen in one blob. The screen name is the file stem, and duplicate stems are a bake error.
