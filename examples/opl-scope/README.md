# opl-scope — a measurement, not an example

A realistic OPL-class library screen, authored to answer one question
for the Phase 1 resource model (`docs/PLAN.md` §6): **what does a real
environment actually demand of the runtime's static tables?**

It is deliberately not a shipped example. It exists to be measured, and
it exceeds the current caps on purpose.

```sh
node packages/layout/bin/ps2ui-layout.js \
    examples/opl-scope/ui/library.html examples/opl-scope/ui/opl.css \
    -o build/opl.json
PYTHONPATH=packages/baker python3 -m ps2ui_bake build/opl.json \
    -o build/opl.uib --preview build/opl.png
```

## What it contains

One library screen at the scale the anchor use case (UC-3) needs: nine
rows with cover art, title, subtitle, Metacritic score and source tag;
five filter chips; a continue-playing rail; a footer hint bar.

Nine rows, not twelve. Twelve was the first attempt and the linter
refused it — at 34px per row (title over subtitle drives the height,
not the 16px art) twelve rows push the footer 65px past the canvas.
**Nine rows is what fits NTSC action-safe at this row design**, and
that is the first measurement: a windowed list on this hardware shows
nine items, so the window/scroll behaviour matters more than it would
at twelve.

## The demand

Measured from the baked blob, with `PS2UI_MAX_SLOTS` temporarily
raised so the bake could complete:

| | measured | cap today |
|---|---|---|
| **slots** | **43** (9 rows × 4 fields + 3 continue × 2 + count) | **16** |
| textures | 12 (nine-patch corners, three glyph atlases, cover art) | 32 |
| fonts | 4 (size × weight combinations) | — |
| focusables | 17 | 256 hideable |
| draw records | 414 | — |
| VRAM | 152 KiB of a 736 KiB budget (20%) | 4 MB total |
| blob | 116 KiB | — |
| glyph tables | 460 glyphs, 528 kern pairs | — |

Unmodified, the bake refuses, and correctly:

```
runtime tables: 12/32 textures, 43/16 slots, 1/8 screens
error: slots: 43 exceeds PS2UI_MAX_SLOTS = 16. ps2ui_load() would
return PS2UI_ERR_TOO_MANY.
```

**One screen needs 2.7× the entire blob-wide slot budget.** Projecting
the other four UC-3 screens (landing ~8, detail ~14, filters ~10,
recent ~16) puts the environment near **91 slots, 5.7× the cap**.

The interesting part is what that costs under each model. Slot text
lives in the context as `slot_text[MAX_SLOTS][96]`:

- **fixed maxima**, raised to fit 91: **8,736 B**, paid by every blob
  including a two-slot overlay that needs 192 B.
- **blob-sized arena** (Phase 1): this screen asks for 4,128 B and a
  small UI asks for what it uses.

That is §4.1 of the plan with numbers attached: the ceiling is not
merely too low, it is the wrong shape. Raising `PS2UI_MAX_SLOTS` to
256 "fixes" this screen and charges 24 KiB of context to everything
that will never use it.

Textures and VRAM are comfortable — 20% of budget with cover art at
16×16. That changes the moment art is shown at a readable size, which
is what makes streamed texture slots (Phase 1) the other blocker
rather than a nicety.

## Two defects this fixture found

**1. `flex-direction` defaults to `column`, not `row`.**
`INITIAL_STYLE` in `packages/layout/src/css.js` sets `column`; CSS's
initial value is `row`. It is documented nowhere, and it is why this
fixture's first draft stacked every row vertically.

The existing examples hide it because they were written against it:
across `channel6.css` and `library.css` they specify
`flex-direction: row` **20 times** and `column` **4 times**. Authors
are already paying for the divergence in every file; a CSS-correct
default would delete those twenty declarations and need four.

Not changed here. It is a breaking authoring change and belongs with
the other Phase 1 authoring decisions, not as a drive-by.

**2. The contrast lint composited mutually exclusive focus states.**
Fixed separately: a chip's focused background was being composited
under its unfocused text, inventing a frame the console cannot draw.

## Why author a new UI to find these

Both defects had been in the tree for weeks and neither example
tripped them, because editing a file that already works never
exercises a default you have already worked around. Authoring
something new at realistic scale did it in the first ten minutes.
