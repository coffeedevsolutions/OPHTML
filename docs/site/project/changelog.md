---
id: project/changelog
title: Changelog
description: The 0.6.0 release notes by category, the format status, and a table of every earlier release.
section: project
order: 70
version: 0.7.0
sources: [CHANGELOG.md, tools/check-versions.py, docs/site/_facts/reference/compatibility.md, docs/site/_facts/runtime/moving-and-hiding.md, docs/site/_facts/authoring/vram-budget.md, docs/site/_facts/runtime/integrating.md, docs/site/_facts/cli/ps2ui-fontgen.md, docs/site/_facts/cli/ps2ui-layout.md, docs/site/_facts/project/contributing.md, docs/site/cli/ps2ui-layout.md, docs/site/project/contributing.md, docs/site/runtime/integrating.md, docs/site/authoring/vram-budget.md, docs/site/cli/ps2ui-fontgen.md, docs/site/reference/compatibility.md]
---

# Changelog

The open 0.6.0 section of `CHANGELOG.md`, restated by category. Every
bullet below has a full entry in the file itself, linked at the bottom
of this page.

## 0.6.0

`ophtml` 0.7.0, `@ophtml/layout` 0.7.0.

### Added

- `ps2ui_offset_set(ctx, dx, dy)` moves every command and scissor rect
  the next `ps2ui_render` submits, without reflowing the layout or
  changing the `.uib` format. Geometry queries stay in UI coordinates.
  See [Moving and hiding](page:runtime/moving-and-hiding#the-offset).

### Fixed

- `ps2ui dev` accepted `--strict` and `--min-font-size` but stored them
  where the compiler never read them, so a project relying on either
  flag built clean under `ps2ui dev` and failed under `ps2ui build`.
  Both now reach the linter the same way `ps2ui build` does. See
  [ps2ui-layout and ps2ui-dev](page:cli/ps2ui-layout#strict-and-the-font-floor).
- README.md and CONTRIBUTING.md told a contributor to run
  `make -C runtime test test-compat`, a target the Makefile does not
  declare. Both documents now name `make test` and
  `make syntax-check CC=clang`, the two runs CI makes. See
  [Contributing](page:project/contributing#tests).
- `ps2ui-fontgen`'s Raqm refusal named a wheel-architecture split
  between platforms that does not exist. Both Pillow 12.3.0 macOS
  wheels carry Raqm compiled in; what varies is whether the machine has
  fribidi, which Pillow loads at run time. The message now reports the
  Pillow version and platform it detected, checks for fribidi
  separately, and leads with `brew install fribidi` before a rebuild.
  See [ps2ui-fontgen](page:cli/ps2ui-fontgen#ps2ui-fontgen).
- `ps2ui vendor-runtime`'s closing message named
  `docs/deploying.md` as the path onto a console, a repository path an
  installed user cannot open. It now states the cross-compile
  constraint and the `ghcr.io/ps2dev/ps2dev` command directly. See
  [Integrating the runtime](page:runtime/integrating#minimal-example).
- `ps2ui check` dropped `vramBudget` and `strict` on the way from the
  project file, so a build that passed at a declared budget could fail
  the check at the computed default. Both settings now reach the
  checker the build was given. See
  [VRAM budget](page:authoring/vram-budget#overriding-the-budget).
- Past a canvas width, three framebuffers cannot fit in 4 MiB and the
  default VRAM budget goes negative; the bake used to blame the
  textures for it. It now names both sides of the comparison and the
  narrower framebuffer count that clears it. See
  [VRAM budget](page:authoring/vram-budget#when-the-default-cannot-exist).

### Format

`.uib` format version 7, unchanged since 0.5.0. `python3
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

A v7 blob loads under a 0.5.0 runtime and a 0.5.0 blob loads under this
one. The pledge behind that guarantee is on
[Compatibility](page:reference/compatibility#format-compatibility).

## Earlier releases

| version | date | format | headline |
|---|---|---|---|
| 0.5.0 | 2026-09-06 | v7 | `ps2ui vendor-runtime` ships the C runtime from the installed package; the console half needs no clone. |
| 0.4.0 | 2026-09-06 | v7 | The `.uib` v7 stability pledge, and vendored DejaVu fonts for a checkout with no system font. |
| 0.3.0 | 2026-09-04 | v7 | First tagged release. Breaking authoring and runtime changes; four format moves land, v4 through v7. |

Full history: [CHANGELOG.md](repo:CHANGELOG.md).
