---
id: project/changelog
title: Changelog
description: The 0.10.0 notes by category, the format status, and a table of every earlier release.
section: project
order: 70
version: 0.10.0
sources: [CHANGELOG.md, tools/check-versions.py, docs/site/_facts/reference/compatibility.md, docs/site/_facts/runtime/moving-and-hiding.md, docs/site/_facts/authoring/vram-budget.md, docs/site/_facts/runtime/integrating.md, docs/site/_facts/cli/ps2ui-fontgen.md, docs/site/_facts/cli/ps2ui-layout.md, docs/site/_facts/project/contributing.md, docs/site/cli/ps2ui-layout.md, docs/site/project/contributing.md, docs/site/runtime/integrating.md, docs/site/authoring/vram-budget.md, docs/site/cli/ps2ui-fontgen.md, docs/site/reference/compatibility.md]
---

# Changelog

The 0.10.0 section of `CHANGELOG.md`, restated by category, one bullet
here for each entry there. The file carries the reasoning and the
measurements; this page carries what changed.

## 0.11.0.dev0

Unreleased; 0.10.0, below, is what installs.

### Fixed

- `ps2ui-layout` refuses a tree nested past the depth cap with its own
  message on every machine. On macOS arm64, 0.10.0 could still die of
  `Maximum call stack size exceeded` before the cap was checked.
- The baker test suite passes on a clean checkout, before the examples
  are built.

## 0.10.0

`ophtml` 0.10.0, `@ophtml/layout` 0.10.0, tagged `v0.10.0`. `pip install
ophtml` and `npm install -g @ophtml/layout` give you this release, and
`ophtml.elf` is on its [GitHub Release](https://github.com/coffeedevsolutions/OPHTML/releases/tag/v0.10.0).

### Added

- The OPHTML console (`console/`): a PS2 program that lists the ISOs on
  USB, an exFAT HDD, MX4SIO or MMCE through any theme that uses its
  names (`game-{i}`, `sel-title`, `status`, ...) and starts the chosen
  one with Neutrino. It boots in the emulator; no console has run it
  yet. See `console/README.md`.
- `ps2ui check` checks a console theme's names (gaps in the rows, rows
  on the wrong screen, slots the console never fills, slots too short
  for what it writes), and `ps2ui serve --console` fills a theme with
  mock games and walks its list the way the console does. See
  [ps2ui-check](page:cli/ps2ui-check#options).
- Hard caps on what a theme may ask the compilers for: canvas
  dimensions, element count, nesting depth and source-image pixels.
  Each is derived from the shipped examples, each fails rather than
  warns, and each is overridable in `ps2ui.json` beside `vramBudget`.
- `ophtml.elf` is attached to each tagged version's GitHub Release, with
  its mock build and checksums, and a new page covers running it with
  Neutrino and your own theme. It has not yet run on a console. See
  [Console launcher](page:runtime/console-launcher).
- `check-versions.py` fails when a released CHANGELOG section differs
  from the same section at its tag, so a merge can no longer add entries
  to a release that already shipped.
- The `.uib` loader is fuzzed, for a minute on every change and half an
  hour nightly, and `ps2ui check` is fuzzed over mutated example blobs.
  Run it with `make -C runtime fuzz`.

### Changed

- `registry.yml` no longer runs 0.8.0's fribidi remedy steps or asserts
  that a plain macOS or Windows install refuses; it requires the
  committed tables from one instead, and fails by name when pip is served
  a release from before 0.9.0. See
  [Compatibility](page:reference/compatibility#what-each-platform-has-actually-been-run-on).

### Fixed

- A `.uib` whose tables were not 4-byte aligned crashed the console in
  `ps2ui_arena_size` or `ps2ui_load`. Both refuse it now, with
  `PS2UI_ERR_ALIGN`, before reading a table. See
  [Errors and constants](page:runtime/errors-and-constants#load-check-order).
- `ps2ui check` printed a Python traceback, not a verdict, for a blob
  with a table past its end, an unknown texture format, or a reference
  past a table.
- A raised `--vram-budget` bought room for a framebuffer, which no
  budget can. A 30000x30000 canvas baked to a blob with exit 0, past a
  message saying a narrower canvas was the only fix.

- A 439 KiB image could cost 432 MB and eleven seconds of bake time, or
  end the bake in a Pillow traceback. The size is read from the header
  now, before any decode.

- Nesting deep enough reported `Maximum call stack size exceeded`,
  which is the interpreter's stack rather than a decision: it gives out
  at 1842 here and at 889 or 7781 with the stack sized down or up. The
  refusal is the compiler's now, at 64, and names the line.

### Format

`.uib` format version 7, unchanged since 0.9.0. `python3
tools/check-versions.py --except-tag` holds the packages, the format
document and this section to each other:

```
ok - @ophtml/layout 0.10.0 and ophtml 0.10.0 are the same version in the two spellings
ok - PS2UI_VERSION and uib.VERSION are both 7
ok - docs/format-uib.md's header table says version 7
ok - docs/format-uib.md's Versioning list explains v7
ok - CHANGELOG's newest section is headed '0.10.0 — 2026-09-26', dated, and is the release the packages carry
ok - CHANGELOG's open section names format v7
ok - CHANGELOG's 0.9.0 section records the format it shipped (v7)
```

A v7 blob loads under every release from 0.3.0 on; see
[Compatibility](page:reference/compatibility#format-compatibility).

## Earlier releases

| version | date | format | headline |
|---|---|---|---|
| 0.9.0 | 2026-09-23 | v7 | `ps2ui fontgen` measures kerning with HarfBuzz through `uharfbuzz`, so a stock macOS or Windows install no longer refuses over a missing fribidi. |
| 0.8.0 | 2026-09-23 | v7 | The first release with Windows and Intel Mac arms in CI, three Windows fixes among what they found, and every version this site prints held to what a command prints. |
| 0.7.0 | 2026-09-17 | v7 | `ps2ui vendor-runtime --starter`, a `:focus` rule that cannot change layout, and eight CSS keywords checked instead of accepted. |
| 0.6.0 | 2026-09-12 | v7 | `ps2ui_offset_set` moves a screen at draw time, and `ps2ui check` is given the settings `ps2ui build` was. |
| 0.5.0 | 2026-09-06 | v7 | `ps2ui vendor-runtime` ships the C runtime from the installed package; the console half needs no clone. |
| 0.4.0 | 2026-09-06 | v7 | The `.uib` v7 stability pledge, and vendored DejaVu fonts for a checkout with no system font. |
| 0.3.0 | 2026-09-04 | v7 | First tagged release. Breaking authoring and runtime changes; four format moves land, v4 through v7. |

Full history: [CHANGELOG.md](repo:CHANGELOG.md).
