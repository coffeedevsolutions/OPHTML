# OPHTML / ps2ui

Write your PlayStation 2 homebrew UI in HTML and CSS. Ship it as draw
commands.

ps2ui is a build-time toolchain: it parses HTML + CSS, solves flexbox
layout, wraps text, solves D-pad navigation and rasterizes chrome — all
on your build machine — and emits a single `.uib` blob that a tiny C99
runtime replays through [gsKit] on the console. The PS2 never parses,
lays out, rasterizes or allocates.

Built for UIs delivered on an SD2PSX / PSxMemCard GEN2 virtual memory
card, useful for any PS2 homebrew that wants a modern authoring workflow
on 2001 silicon.

```
ui/*.html,css ──▶ @ps2ui/layout ──▶ ui.json (IR) ──▶ ps2ui-bake ──▶ ui.uib ──▶ runtime (C99 + gsKit)
                  Node, zero deps                    Python, Pillow only
```

![memcard example preview](examples/memcard/screenshots/preview.png)

That image is not a browser screenshot: it is the Python previewer
replaying the exact baked command list — same quad order, scissor
stack, CLUT lookups and GS alpha domain the console will see. The
previewer can also render [every focus state on one
sheet](examples/memcard/screenshots/states.png) for couch-QA at a
glance.

## Quick start

Requirements: Node ≥ 18, Python 3 with Pillow, a C compiler for the
host tests, DejaVu Sans (or edit `fonts/fonts.json` to point at your
TTF).

```sh
# 1. compile HTML+CSS to the IR
node packages/layout/bin/ps2ui-layout.js \
    examples/memcard/ui/library.html examples/memcard/ui/library.css \
    -o build/ui.json

# 2. bake the IR to a console blob (+ a verification PNG)
PYTHONPATH=packages/baker python3 -m ps2ui_bake build/ui.json \
    -o build/ui.uib --preview build/preview.png --montage build/states.png

# or run both stages + all tests for the example:
./examples/memcard/build.sh
```

On the console side, drop `runtime/ps2ui.c` + `runtime/ps2ui.h` into
your ps2sdk/gsKit project:

```c
ps2ui_ctx ui;
ps2ui_load(&ui, uib_data, uib_len);   /* validates, points into the blob */
ps2ui_upload(&ui, gsGlobal);          /* textures + CSM1-permuted CLUTs  */

/* per frame */
ps2ui_render(&ui, gsGlobal);          /* replays, filtered by focus      */
if (pad_pressed & PAD_RIGHT) ps2ui_move(&ui, PS2UI_RIGHT);
if (pad_pressed & PAD_CROSS) launch(ps2ui_focus_name(&ui));
```

## What subset of CSS?

Flexbox (direction, wrap, grow/shrink/basis, gap, justify/align),
box model (border-box; padding, margin, borders, border-radius via
baked nine-patches), flat colors with real translucency, `font-size` /
`font-weight` / `line-height` / `letter-spacing` / `text-align`,
`white-space: nowrap` + `text-overflow: ellipsis`, `overflow: hidden`
(GS scissor), `display: none`, and `:focus` as a **paint-only** state
(a `:focus` rule that changes geometry is a compile error). Unknown
properties warn; unsupported values error with line numbers.

Interactivity is D-pad-shaped: mark elements `focusable` (and one
`autofocus`); the compiler solves the spatial navigation graph at build
time and the runtime walks it with table lookups.

There is also a CRT linter: overscan-unsafe text, sub-14px fonts, 1px
horizontal lines (interlace flicker), saturated NTSC reds and
low-contrast text are warnings, because your desktop preview will not
show you what a 2001 living-room television does.

## Repository layout

| path | what |
|------|------|
| `packages/layout` | HTML/CSS → `ui.json`. Node, zero dependencies. |
| `packages/baker`  | `ui.json` → `ui.uib` + PNG previews. Python, Pillow only. |
| `runtime`         | `.uib` loader + gsKit replay + D-pad nav. C99, no allocation. |
| `fonts`           | metrics JSON (the layout↔baker seam) + `ps2ui-fontgen`. |
| `docs`            | [architecture](docs/architecture.md) · [IR format](docs/format-ir.md) · [.uib format](docs/format-uib.md) |
| `examples/memcard`| the memory-card library browser from the screenshots. |

Any stage can be replaced by someone who reads the two format specs.

## Tests

```sh
cd packages/layout && node --test 'test/*.test.js'   # parser, cascade, flexbox, focus, lint
cd packages/baker  && python3 -m unittest discover -s tests
cd runtime         && make test test-compat           # real ps2ui.c, -Werror, over a real blob
```

The runtime test compiles the actual `ps2ui.c` against a stub gsKit and
replays a real baked blob, checking struct layouts against the file
format, blob validation, CSM1 permutation, focus-state draw-cost parity
and the D-pad walk. `test-compat` re-runs everything with
`PS2UI_GSKIT_HAS_FUNCTION=0` (older gsKit without `GSTEXTURE::Function`;
text loses tinting).

## Status and caveats

The host toolchain is verified end to end. The gsKit path is written
against the documented API but **not yet hardware-verified** — if you
run it on a console or PCSX2, the first thing to check is text tinting
(`GSTEXTURE::Function`). See [docs/architecture.md](docs/architecture.md)
for the decision log and known next steps (multi-screen documents,
precompiled DMA chains, per-locale builds).

## License

MIT — see [LICENSE](LICENSE).

[gsKit]: https://github.com/ps2dev/gsKit
