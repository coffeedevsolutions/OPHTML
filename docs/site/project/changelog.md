---
id: project/changelog
title: Changelog
description: The 0.9.0 notes by category, the format status, and a table of every earlier release.
section: project
order: 70
version: 0.9.0
sources: [CHANGELOG.md, tools/check-versions.py, docs/site/_facts/reference/compatibility.md, docs/site/_facts/runtime/moving-and-hiding.md, docs/site/_facts/authoring/vram-budget.md, docs/site/_facts/runtime/integrating.md, docs/site/_facts/cli/ps2ui-fontgen.md, docs/site/_facts/cli/ps2ui-layout.md, docs/site/_facts/project/contributing.md, docs/site/cli/ps2ui-layout.md, docs/site/project/contributing.md, docs/site/runtime/integrating.md, docs/site/authoring/vram-budget.md, docs/site/cli/ps2ui-fontgen.md, docs/site/reference/compatibility.md]
---

# Changelog

The 0.9.0 section of `CHANGELOG.md`, restated by category, one bullet
here for each entry there. The file carries the reasoning and the
measurements; this page carries what changed.

## 0.10.0.dev0

Unreleased; 0.9.0, below, is what installs.

## 0.9.0

`ophtml` 0.9.0, `@ophtml/layout` 0.9.0, tagged `v0.9.0`. `pip install
ophtml` and `npm install -g @ophtml/layout` give you this release.

### Changed

- `ps2ui fontgen` measures kerning with HarfBuzz through the new
  `uharfbuzz` dependency instead of Pillow's Raqm engine, so a stock
  macOS or Windows install no longer refuses over a missing fribidi.
  The metrics it writes are byte-identical. See
  [ps2ui-fontgen](page:cli/ps2ui-fontgen#exit-codes).

### Format

`.uib` format version 7, unchanged since 0.8.0. `python3
tools/check-versions.py --except-tag` holds the packages, the format
document and this section to each other:

```
ok - @ophtml/layout 0.9.0 and ophtml 0.9.0 are the same version in the two spellings
ok - PS2UI_VERSION and uib.VERSION are both 7
ok - docs/format-uib.md's header table says version 7
ok - docs/format-uib.md's Versioning list explains v7
ok - CHANGELOG's newest section is headed '0.9.0 — 2026-09-23', dated, and is the release the packages carry
ok - CHANGELOG's open section names format v7
ok - CHANGELOG's 0.8.0 section records the format it shipped (v7)
```

A v7 blob loads under every release from 0.3.0 on; see
[Compatibility](page:reference/compatibility#format-compatibility).

## Earlier releases

| version | date | format | headline |
|---|---|---|---|
| 0.8.0 | 2026-09-23 | v7 | The first release with Windows and Intel Mac arms in CI, three Windows fixes among what they found, and every version this site prints held to what a command prints. |
| 0.7.0 | 2026-09-17 | v7 | `ps2ui vendor-runtime --starter`, a `:focus` rule that cannot change layout, and eight CSS keywords checked instead of accepted. |
| 0.6.0 | 2026-09-12 | v7 | `ps2ui_offset_set` moves a screen at draw time, and `ps2ui check` is given the settings `ps2ui build` was. |
| 0.5.0 | 2026-09-06 | v7 | `ps2ui vendor-runtime` ships the C runtime from the installed package; the console half needs no clone. |
| 0.4.0 | 2026-09-06 | v7 | The `.uib` v7 stability pledge, and vendored DejaVu fonts for a checkout with no system font. |
| 0.3.0 | 2026-09-04 | v7 | First tagged release. Breaking authoring and runtime changes; four format moves land, v4 through v7. |

Full history: [CHANGELOG.md](repo:CHANGELOG.md).
