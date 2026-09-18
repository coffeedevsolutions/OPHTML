---
id: project/changelog
title: Changelog
description: The open 0.8.0.dev0 notes by category, the format status, and a table of every earlier release.
section: project
order: 70
version: 0.7.0
sources: [CHANGELOG.md, tools/check-versions.py, docs/site/_facts/reference/compatibility.md, docs/site/_facts/runtime/moving-and-hiding.md, docs/site/_facts/authoring/vram-budget.md, docs/site/_facts/runtime/integrating.md, docs/site/_facts/cli/ps2ui-fontgen.md, docs/site/_facts/cli/ps2ui-layout.md, docs/site/_facts/project/contributing.md, docs/site/cli/ps2ui-layout.md, docs/site/project/contributing.md, docs/site/runtime/integrating.md, docs/site/authoring/vram-budget.md, docs/site/cli/ps2ui-fontgen.md, docs/site/reference/compatibility.md]
---

# Changelog

The open 0.8.0.dev0 section of `CHANGELOG.md`, restated by category. Every
bullet below has a full entry in the file itself, linked at the bottom
of this page.

## 0.8.0.dev0

`ophtml` 0.8.0.dev0, `@ophtml/layout` 0.8.0-dev.0. A prerelease, on
neither registry; `pip install ophtml` and `npm install -g
@ophtml/layout` give you 0.7.0.

### Added

- `tools/check-doc-versions.py` holds every version this site prints to
  the version something actually prints. A citation pins the line it
  names, so it cannot see a version flowing through a file the row does
  not cite: ten rows survived the 0.8.0.dev0 bump asserting 0.7.0 with
  every citation green. 28 banners are pinned as meaning the tree or the
  last release.

### Fixed

- `ps2ui build` run before `ps2ui fontgen` named a directory inside the
  npm package as the place your font metrics belong. The project
  resolves fonts once now, before either half runs, and names
  `ps2ui fontgen <regular.ttf> <bold.ttf>`, which writes the metrics and
  the manifest both halves read. See
  [Installation](page:getting-started/installation#a-ttf-to-start-with).
- The build command `ps2ui vendor-runtime --starter` printed could not
  be followed: it said to put the blob beside the four files and then
  passed `UIB=build/ui.uib`. One spelling cannot be right for two
  layouts, so the message names none. See
  [Integrating](page:runtime/integrating#starting-from-nothing).
- `--starter` is the console half without a clone and no page here
  mentioned it. Fixed on four artefacts, including the page every
  `pip install ophtml` reader lands on.
- The Installation page did not say that `pip install ophtml` fails on a
  current macOS or Debian box under PEP 668, nor where to get a TTF.

### Format

`.uib` format version 7, unchanged since 0.7.0. `python3
tools/check-versions.py --except-tag` holds the packages, the format
document and this section to each other:

```
ok - @ophtml/layout 0.8.0-dev.0 and ophtml 0.8.0.dev0 are the same version in the two spellings
ok - PS2UI_VERSION and uib.VERSION are both 7
ok - docs/format-uib.md's header table says version 7
ok - docs/format-uib.md's Versioning list explains v7
ok - CHANGELOG's open section is headed with 0.8.0.dev0
ok - CHANGELOG's open section names format v7
ok - CHANGELOG's 0.7.0 section records the format it shipped (v7)
```

A v7 blob loads under a 0.7.0 runtime and a 0.7.0 blob loads under this
one. The pledge behind that guarantee is on
[Compatibility](page:reference/compatibility#format-compatibility).

## Earlier releases

| version | date | format | headline |
|---|---|---|---|
| 0.5.0 | 2026-09-06 | v7 | `ps2ui vendor-runtime` ships the C runtime from the installed package; the console half needs no clone. |
| 0.4.0 | 2026-09-06 | v7 | The `.uib` v7 stability pledge, and vendored DejaVu fonts for a checkout with no system font. |
| 0.3.0 | 2026-09-04 | v7 | First tagged release. Breaking authoring and runtime changes; four format moves land, v4 through v7. |

Full history: [CHANGELOG.md](repo:CHANGELOG.md).
