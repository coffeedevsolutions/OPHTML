# Contributing to ps2ui

## Setup

Node ≥ 18, Python 3.9+ with Pillow, a C compiler, DejaVu Sans (or edit
`fonts/fonts.json`). No other dependencies — that's a design rule, not
an accident: the layout package must stay zero-dependency, the baker
Pillow-only.

## Run the tests (all three, before every PR)

```sh
cd packages/layout && node --test test/*.test.js
cd packages/baker  && python3 -m unittest discover -s tests
./examples/memcard/build.sh        # end-to-end + C runtime tests
make -C runtime test-compat        # old-gsKit build
```

The dev loop while working on layout/baker changes:

```sh
node packages/layout/bin/ps2ui-dev.js \
    examples/memcard/ui/library.html examples/memcard/ui/library.css \
    -o build/dev
```

## How the codebase is shaped

Three stages, two documented seams — read these first:

- [docs/architecture.md](docs/architecture.md) — the decision log
- [docs/format-ir.md](docs/format-ir.md) — layout → baker (`ui.json`)
- [docs/format-uib.md](docs/format-uib.md) — baker → runtime (`.uib`)

Rules that PRs must not break:

1. **Everything moves to build time.** The runtime never parses, lays
   out, rasterizes, or allocates.
2. **Domain conversions cross once.** CSS alpha→GS 0–128, modulate RGB
   →0x80 identity, CLUT linear→CSM1: each has one owner; tests exist on
   both sides of every seam.
3. **The two hosts must agree bit-for-bit** on glyph math: the shared
   rounding rule is `floor(x + 0.5)`, never `round()`.
4. **The previewer replays the blob**, not the IR — if you add a
   command type, the previewer and the C runtime learn it in the same
   PR, and `docs/format-uib.md` bumps its version story.
5. `:focus` is paint-only; geometry deltas are compile errors.

## Good first issues

- Named CSS colors beyond the current small set (`values.js`).
- `text-transform: uppercase` (layout-only; the baker already handles
  any codepoint the metrics know).
- `--columns` flag for the previewer montage (`preview.py`).
- Lint rule: warn when `overflow: hidden` meets `border-radius`
  (clips square — backlog B6's cheap half).
- PAL example: a 640×512 variant of the memcard screen.

Bigger items live in [docs/BACKLOG.md](docs/BACKLOG.md), RICE-scored —
comment on an item before starting so effort isn't duplicated.

## Security

See [SECURITY.md](SECURITY.md). Never attach a self-hosted runner.
