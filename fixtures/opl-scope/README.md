# opl-scope — a measurement fixture

A realistic OPL-class library screen, authored to answer one question
for the Phase 1 resource model (`docs/PLAN.md` §6): **what does a real
environment actually demand of the runtime's static tables?**

It lives in `fixtures/`, not `examples/`, because it is an instrument
rather than a demonstration: it exists to be measured and compared
against later, and it carries none of what `examples/` promises —
warning-free, screenshots refreshed, a shipped contract (invariant I6).

It used to say something stronger here: that a blob *could not be
baked from it without raising a cap*. That was true until PLAN §6.3.
It now bakes with a stock checkout and loads on a stock runtime, which
is the outcome the measurement was taken to justify.

Re-measure, and check the numbers below are still true:

```sh
./fixtures/opl-scope/measure.sh
```

That runs layout on all five screens, bakes them into one blob, and
checks the arena. CI runs it on every push. Nothing is edited to make
it work.

## What it contains

The five screens the anchor use case (UC-3) needs, sharing one
stylesheet and baking into one blob the way a real environment ships:

| screen | what it is |
|---|---|
| `landing` | entry point: source tiles (HDD/USB/NET/…) and a continue-playing rail |
| `library` | nine rows with cover art, title, subtitle, score, source; filter chips |
| `detail` | one title's art, six metadata fields, a blurb, four action buttons |
| `filters` | seven facet rows with a live match preview |
| `recent` | nine session rows with progress |

Nine rows, not twelve. Twelve was the first attempt and the linter
refused it — at 34px per row (title over subtitle drives the height,
not the 16px art) twelve rows push the footer 65px past the canvas.
**Nine rows is what fits NTSC action-safe at this row design**, and
that is the first measurement: a windowed list on this hardware shows
nine items, so the window/scroll behaviour matters more than it would
at twelve.

## The demand

Per screen, from the layout stage:

| screen | slots | focusables |
|---|---:|---:|
| landing | 15 | 7 |
| library | 43 | 17 |
| detail | 15 | 4 |
| filters | 20 | 12 |
| recent | 28 | 9 |
| **environment** | **121** | **49** |

And from the baked blob. **Every figure in this table is read back out
of the blob by `figures.py`, which `measure.sh` runs** — five of them
were wrong before that existed, because `measure.sh` asserted the slot
counts and a ceiling on the arena and nothing else, so P3b-6 moved
records, textures, VRAM, the blob and the arena underneath a table
nobody re-derived:

| | measured | cap when this was written |
|---|---|---|
| **slots** | **121** | **16** |
| screens | 5 | 8 |
| textures | 12 | 32 |
| fonts | 5 | — |
| draw records | 2,048 | — |
| VRAM | 224 KiB of a 736 KiB budget | 4 MB total |
| blob | 238,672 B | — |
| **arena** | **8,165 B** | — |

**The environment needed 7.6× the entire blob-wide slot budget** — and
the library screen alone needed 2.7×. That is what the bake said in
2026-08, quoted here as the measurement that motivated the change:

```
runtime tables: 15/32 textures, 121/16 slots, 5/8 screens
error: slots: 121 exceeds PS2UI_MAX_SLOTS = 16. ps2ui_load() would
return PS2UI_ERR_TOO_MANY.
```

What it says now:

```
ps2ui-bake: 5 screen(s), 2048 records, 12 textures (137 KiB baked), 4 CLUTs
ps2ui-bake: arena 8165 bytes (static uint8_t arena[8165] __attribute__((aligned(16))))
```

8,165 bytes for the largest UI in this repository — against roughly
36 KiB that the fixed-maxima context charged *every* blob, including a
two-slot overlay. The environment that could not be loaded at all is
now the one that fits, and it fits at the EE's 32-bit address width:
`runtime/tests/test_narrow.c` loads this blob there.

### Estimating this failed, which is the point

An earlier revision measured only the library screen and *projected*
the other four. The projection was 33% low, and wrong in a specific
way:

| screen | projected | measured | error |
|---|---:|---:|---:|
| landing | 8 | 15 | +88% |
| library | 43 | 43 | — |
| detail | 14 | 15 | +7% |
| filters | 10 | 20 | +100% |
| recent | 16 | 28 | +75% |
| **total** | **91** | **121** | **+33%** |

The two accurate rows are the one that was measured and the one that
is mostly static text. Every screen built from repeated rows was
underestimated by 75–100%, because `data-repeat` multiplies fields by
rows and eyeballing does not. A resource model sized from estimates
would have been undersized by a third, in the direction that fails on
a television.

### A second ceiling was already in view

`5 of 8 screens`. A shipping OPL environment would want settings,
network configuration, and an about page — exactly 8. The slot cap was
the one that blocked then; `PS2UI_MAX_SCREENS` was the one that would
have blocked the version after.

Both are gone, and so is `PS2UI_MAX_TEXTURES`. Removing one and
leaving the others would have been the same argument answered once:
they were a single check, and none of them bounded anything the blob's
own size did not already bound once the context stopped being sized by
them. What replaced them is not "nothing" — see `arena_compute` in
`runtime/ps2ui.c`, which refuses a carve it cannot do rather than
wrapping it, and `make -C runtime test-narrow`, which proves that at
the EE's width.

The interesting part is what that costs under each model. Slot text
lives in the context as `slot_text[MAX_SLOTS][96]`:

| | `slot_text` cost |
|---|---:|
| **fixed maxima**, raised to fit 121 | **11,616 B — on every blob** |
| arena: this environment | 11,616 B |
| arena: the memcard example (6 slots) | 576 B |
| arena: a two-slot overlay | 192 B |

A two-slot overlay pays **60× what it uses** under fixed maxima. That
is §4.1 of the plan with numbers attached: the ceiling is not merely
too low, it is the wrong shape, and raising it makes the waste worse
rather than better.

Textures and VRAM are comfortable — 33% of budget, with cover art at
16×16 in lists and 120×72 on the detail page. That changes the moment
art is shown at a size a person would call readable, which is what
makes streamed texture slots (Phase 1) the other blocker rather than a
nicety.

## Kept honest

`measure.sh` asserts every screen's slot and focusable count above plus
the environment total, and CI runs it on every push. A fixture whose
only job is to be re-measured at the Phase 1 gate is worthless if it
has quietly stopped compiling, or if the demand moved and nobody
noticed. Verified by sabotage: dropping a row reports
`not ok - library: 39 slots / 16 focusables, README says 43 / 17` and
exits 1.

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

Not changed here, and not deferred either: it is fixed in its own
change, where `flex-direction` becomes required rather than defaulted
in either direction. See `docs/PLAN.md` §6 — the phase gates sequence
new capability and do not queue defect fixes, and a property that
diverges from the standard its syntax is borrowed from is a defect.

**2. The contrast lint composited mutually exclusive focus states.**
Fixed separately: a chip's focused background was being composited
under its unfocused text, inventing a frame the console cannot draw.

## Why author a new UI to find these

Both defects had been in the tree for weeks and neither example
tripped them, because editing a file that already works never
exercises a default you have already worked around. Authoring
something new at realistic scale did it in the first ten minutes.
