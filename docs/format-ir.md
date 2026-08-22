# ui.json — the intermediate representation

The seam between `@ps2ui/layout` (Node) and `ps2ui-bake` (Python). It is
deliberately dumb: absolute integer pixel geometry, flat paint order, no
styles, no tree. A replacement layout engine (or a hand-written
generator) only has to produce this file.

All coordinates are CSS pixels on the fixed canvas, origin top-left.
All colors are `[r, g, b, a]` with every channel **0–255** — the CSS
domain. The GS 0–128 alpha domain is the baker's business, never the
IR's.

```jsonc
{
  "version": 1,
  "canvas": { "w": 640, "h": 448 },
  "fonts": {
    "regular": { "family": "DejaVu Sans", "weight": 400 },
    "bold":    { "family": "DejaVu Sans", "weight": 700 }
  },
  "commands": [ /* paint order, see below */ ],
  "focus": {
    "nodes": [
      {
        "id": 9,                      // opaque box id, unique in file
        "name": "nav-games",          // element id/name, for the runtime API
        "rect": [28, 92, 128, 39],    // x, y, w, h
        "up": null, "down": 11,       // neighbor ids or null
        "left": null, "right": 28
      }
    ],
    "initial": 9                      // id of the autofocus node, or null
  },
  "warnings": [ "min-font-size: ..." ]  // compiler + CRT lint output
}
```

## Commands

Commands appear in paint order (back to front). Every paint command
carries:

* `state` — `"always"` | `"unfocused"` | `"focused"`. The runtime draws
  a command when `state` is `always`, or when it matches whether
  `focusId` is the currently focused node. Both focus states of the
  whole screen live in this single list.
* `focusId` — the focus node this delta belongs to (`null` outside any
  focusable subtree).

### `rect`

```jsonc
{
  "op": "rect", "x": 28, "y": 92, "w": 128, "h": 39,
  "fill": [20, 26, 43, 255],          // or null
  "borderWidth": 2,                    // 0 = no border
  "borderColor": [29, 36, 56, 255],    // null when borderWidth is 0
  "radius": 6,                         // corner radius, px
  "state": "unfocused", "focusId": 9
}
```

The layout stage guarantees `radius <= min(w, h) / 2` and that a
border-color without width (or a fully transparent paint) is normalized
away, so identical unfocused/focused paints always merge to `always`.

### `text`

One command per laid-out line. `x`/`y` is the top-left of the glyph box
(ascent + descent); the baker adds per-glyph bearings.

```jsonc
{
  "op": "text", "x": 44, "y": 117,
  "text": "Games", "size": 15, "weight": 400, "letterSpacing": 0,
  "color": [200, 207, 220, 255],
  "state": "unfocused", "focusId": 9
}
```

An optional `"nocontrast": true` may appear, from `data-nocontrast` on
the element. It applies to **that element's own text only** — it does
not cascade, so putting it on a wrapper does nothing. That is
self-announcing rather than silent: the warning it was meant to
suppress keeps appearing, so the author finds out at once.

It is a **lint-only** flag: the baker ignores it, and it exists so text
whose invisibility is the instrument — bring-up steps 4
and 5 paint glyphs the exact colour of the block behind them — does not
emit a permanent contrast warning on every build. Scoped to that one
rule rather than a blanket opt-out, so it has to be argued for each
time it is used. Absent means false, like `keep` on a rect.

The string is already wrapped, ellipsized and positioned; the baker must
not re-measure it, only advance the pen by the shared rounding rule
`floor(units * size / 1000 + 0.5)` per glyph (see
`docs/architecture.md`, "Font metrics are the seam").

### `image`

```jsonc
{
  "op": "image", "x": 44, "y": 100, "w": 32, "h": 24,
  "src": "/abs/path/to/ui/assets/badge.png",  // build-host path
  "palettize": false,          // true = bake as PSMT8 + 256-color CLUT
  "state": "always", "focusId": 9
}
```

`w`/`h` is the final on-screen size; the baker pre-scales the decoded
pixels to exactly that and the GS never scales at runtime. `src` is a
build-host absolute path (the .uib contains texels, never paths).
`palettize: true` asks the baker to quantize this image to 8-bit
indexed PSMT8 with a per-image CLUT — 4× less VRAM per texel, ≤256
colors; the whole bake can be forced with `ps2ui-bake
--palettize-images`. Images have no focus variants: `state` is always
`"always"`.

An optional `"keep": true` may appear on a rect, from `data-keep` on the
element. It exempts that geometry from the baker's dead-geometry trim,
which otherwise drops any record that provably cannot draw. The one
thing that wants it is deliberate observability: bring-up step 7 needs
a quad that *provably cannot draw*, so that seeing it on a television
means the scissor is not being applied. Trimming it would delete the
test. Absent means false.

### `scissor_push` / `scissor_pop`

```jsonc
{ "op": "scissor_push", "x": 0, "y": 0, "w": 60, "h": 20, "state": "always", "focusId": null }
{ "op": "scissor_pop", "state": "always", "focusId": null }
```

Always balanced, always `state: "always"`. Nested pushes intersect.

## Slots (dynamic text)

`slots` is a top-level array beside `commands`. A slot is a single-line
text region whose *string* arrives at runtime while everything else —
geometry, font, colors, alignment, ellipsis policy — froze at compile
time. Produced by the `data-slot` attribute; the placeholder text is
laid out normally but emitted here instead of as `text` commands.
`letterSpacing` travels with the slot because the pen that draws the
string runs on the console: every input to the pen must reach it, or
the box is measured with a value the glyphs are never drawn with.

```jsonc
{
  "name": "count", "placeholder": "6 titles",
  "x": 520, "textY": 30, "w": 92,          // content box + glyph-box top
  "size": 13, "weight": 400, "lineHeight": 16,
  "align": "left", "letterSpacing": 0, "ellipsis": true, "capacity": 15,
  "focusId": null,
  "colorBase": [139, 148, 167, 255],       // CSS domain, as everywhere in the IR
  "colorFocus": [139, 148, 167, 255]
}
```

## Invariants a consumer may rely on

1. Geometry is integral and identical across focus states (paint-only
   focus deltas are enforced at compile time).
2. Scissor pushes/pops are balanced and properly nested.
3. `focus.nodes` is in document order; neighbor ids always resolve
   within the file.
4. Warnings are advisory; a valid IR may carry any number of them.
