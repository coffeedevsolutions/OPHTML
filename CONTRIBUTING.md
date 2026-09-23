# Contributing to ps2ui

## Setup

Node ≥ 18, Python 3.9+ with Pillow and uharfbuzz, a C compiler,
DejaVu Sans (or edit `fonts/fonts.json`):

```sh
python3 -m pip install Pillow uharfbuzz
```

No other dependencies — that's a design rule, not an accident: the
layout package must stay zero-dependency, and the baker takes only
what installs as a self-contained wheel on every platform pip serves.

**That rule used to read "the baker Pillow-only", and F47 amended it
on purpose.** Pillow alone was never self-contained: `ps2ui fontgen`
measured kerning through Pillow's Raqm engine, and Raqm loads fribidi
from the machine at run time, which no Pillow wheel bundles. So a
stock Mac or Windows box refused at the tutorial's first command, and
a contributor on one had to install a system package — on Apple
silicon, rebuild Pillow from source. `uharfbuzz` is HarfBuzz as a wheel
(Apache-2.0), reproduces every table Raqm measured, and needs nothing
from the system. Two self-contained wheels serve the rule's purpose;
one wheel with a system half did not. A third dependency has to clear
the same bar, and says so in the CHANGELOG when it does.

## Run the tests (all three, before every PR)

```sh
cd packages/layout && node --test test/*.test.js
cd packages/baker  && python3 -m unittest discover -s tests
./examples/memcard/build.sh        # end-to-end + C runtime tests
```

`make -C runtime test-compat` used to be a fourth line here. There is no
such target and there has not been since #39 (`499212c`) removed the
mechanism it built: gsKit has **no** `GSTEXTURE::Function` field and
hardcodes `TEX0.TFX = 0` at all 30 of its `TEX0` sites, so the
"old-gsKit fallback" it compiled is a path gsKit has never had
([F-005](docs/findings.md)). The line has outlived the removal by 21
days (`499212c`, 2026-08-23), which makes a failed `make` the first thing a new contributor
sees — and teaches them, correctly, that these instructions are not run.
F28 is the inventory of where else that text is still standing.

The dev loop while working on layout/baker changes:

```sh
node packages/layout/bin/ps2ui-dev.js \
    examples/memcard/ui/library.html examples/memcard/ui/library.css \
    -o build/dev
```

## Before you open a PR: what does this change make wrong?

Run it, and read the list:

```sh
python3 tools/check-doc-impact.py        # against origin/main
```

It names the documents that cite the files you touched, at both levels
— the repository's own (`README.md`, `docs/*.md`, the example READMEs)
and the deep-dive library under `docs/site/`, which every checkout has
since #133.

**It warns and never fails, and that is deliberate.** A change can be
genuinely doc-neutral, and a check that fires on correct work grows a
skip flag that everyone passes within a week. The list is for a person
to read. Acting on it is the rule; the tool only makes the rule cheap.

**One part of this does gate, and it is the part that can.**
`tools/check-site-pages.py` fails when a citation in the library points
at a line whose text has changed, because that is a fact rather than a
judgement — the pinned text either still sits there or it does not.
Move a line and it goes red; `--fix` relocates the citation when the
recorded line is findable, and reports the rest for a hand fix.

**Both halves are gated as of 0.7.0.** It has always covered a page's
`repo:<path>#L<n>` links. It now also covers the `source` cell of every
`_facts` row — `packages/layout/src/css.js:598-655` — which is where
the evidence for every claim lives and which nothing checked before.
That was not a theoretical gap: when the check was added, **266 of the
1087 facts citations had drifted**, one of them broken by a pull
request that inserted a set above `GEOMETRY_PROPS` four commits after a
neighbouring row in the same file had been re-measured by hand. If you
move code, run this; 1087 of those citations now move with you or go
red. Run it before you push:

```sh
python3 tools/check-site-pages.py           # or --fix, then re-read the diff
```

Do not reach for `--pin` to clear it. That rewrites the record to
whatever now sits at those numbers, which turns a citation pointing at
the wrong line into a citation nobody will question again.

Three things it cannot do, so do not read a clean run as a clean bill:

- **File-level, not claim-level.** A comment fix flags the same
  documents as an API removal.
- **It cannot see a document that *should* have cited your file and did
  not.** If you added a public function, no diff reaches the page that
  ought to describe it.
- **A document that names no paths is invisible to it.** Prose about
  behaviour cannot be reached from a diff.
- **A bare filename is not a path**, and this is the one that bites on
  the question the tool is for. A document writing `ps2ui.h` rather
  than `runtime/ps2ui.h` is not reached by a change to that header —
  and 14 documents in this tree do exactly that, `README.md` and
  `CHANGELOG.md` among them. Resolving them is F30's work; knowing it
  is you.

The board is four months of what happens without this: a header comment
that outlived its macro by 20 days, a README naming a Makefile target
#39 deleted, a bench card naming a cause [F-005](docs/findings.md)
proved impossible, and a stylesheet still citing constants #52 removed
— that last one ten lines from prose corrected the day before, in the
same file, missed because the sweep that caught the others keyed on a
different removal's vocabulary.

**Every version bump updates `docs/site/` too.** That is a release
step, not a follow-up: see [docs/releasing.md](docs/releasing.md).

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

Bigger items live in [BACKLOG.md](BACKLOG.md) — a defect ledger and
idea archive, not a queue. What gets done next comes from the phase
gates in [docs/PLAN.md](docs/PLAN.md) §6, and an item is admitted
under the pull rule: a feature enters when a real use case demands
it. Comment on an item before starting so effort isn't duplicated.

## Security

See [SECURITY.md](SECURITY.md). Never attach a self-hosted runner.
