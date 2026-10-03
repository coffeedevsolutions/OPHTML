---
id: reference/compatibility
title: Compatibility
description: The versions that ship together, the .uib format pledge across runtimes, registry prerelease rules, and the supported platforms.
section: reference
order: 53
version: 0.10.0
sources: [tools/check-versions.py, tools/check-format-frozen.py, CHANGELOG.md, docs/releasing.md, packages/baker/pyproject.toml, packages/layout/package.json, packages/baker/ps2ui_bake/__init__.py, packages/baker/ps2ui_bake/uib.py, packages/layout/src/index.js, runtime/ps2ui.h, runtime/ps2ui.c, runtime/Makefile, runtime/vendor/README.md, .github/workflows/hw.yml, .github/workflows/registry.yml, examples/memcard/build/library.json]
---

# Compatibility

OPHTML ships two packages and a C runtime as one product, one version
number apart. This page lists every version claim the tree carries,
what a runtime accepts from a blob, how each registry treats a
prerelease, and the platforms the toolchain runs on.

## Versions table

Run `python3 tools/check-versions.py --except-tag` to prove the five
numbers below agree with each other and with the code that writes
them.

```
$ python3 tools/check-versions.py --except-tag
ok - packages/baker derives its version from ps2ui_bake.__version__ and declares it nowhere else
ok - @ophtml/layout 0.11.0-dev.0 and ophtml 0.11.0.dev0 are the same version in the two spellings
ok - PS2UI_VERSION and uib.VERSION are both 7
ok - docs/format-uib.md's header table says version 7
ok - docs/format-uib.md's Versioning list explains v7
ok - CHANGELOG's open section is headed with 0.11.0.dev0
ok - CHANGELOG's open section names format v7
ok - CHANGELOG's 0.10.0 section records the format it shipped (v7)
ok - CHANGELOG counts zero format moves since 0.10.0, and v7 -> v7 is 0
ok - CHANGELOG counts the drift from 0.10.0, the section below it
ok - README's Quick start note names 0.11.0.dev0, 0.11.0-dev.0, format v7 and the drift since 0.10.0
ok - and docs/assets/ophtml-logo-releaseVersion0100-plain-white-darkbg.png is actually there
ok - README's header logo names 0.10.0, which is the last release
ok - @ophtml is scoped and publishes with access: public
ok - @ophtml/layout publishes to the 'next' dist-tag, so a publish of this prerelease would not take `latest`
ok - docs/releasing.md exists and still names __version__ and the tagging step (keywords, not correctness)
ok - layout is named @ophtml/layout
ok - baker is named ophtml
ok - packages/layout/README.md is there
ok - packages/baker/README.md is there and pyproject.toml declares it
ok - CHANGELOG's 0.3.0 section is the one v0.3.0 shipped with its recorded edit
ok - CHANGELOG's 0.4.0 section is the one v0.4.0 shipped
ok - CHANGELOG's 0.5.0 section is the one v0.5.0 shipped
ok - CHANGELOG's 0.6.0 section is the one v0.6.0 shipped
ok - CHANGELOG's 0.7.0 section is the one v0.7.0 shipped
ok - CHANGELOG's 0.8.0 section is the one v0.8.0 shipped
ok - CHANGELOG's 0.9.0 section is the one v0.9.0 shipped
ok - CHANGELOG's 0.10.0 section is the one v0.10.0 shipped
ok - the recorded v0.3.0 edit ('**Tagged is not published.**' -> '**Tagged and published.**') is still the one difference it excuses
# rule 23 compared 8 of 8 released section(s) with their tags
ok - CHANGELOG's Tagged is not published paragraph is gone, matching PUBLISHED = True
ok - the npm package is scoped: @ophtml/layout
ok - README.md names the packages it tells people to install
ok - CHANGELOG.md names the packages it tells people to install
ok - docs/releasing.md names the packages it tells people to install
ok - docs/tutorial-uc3.md names the packages it tells people to install
ok - docs/PLAN.md's format history runs v1 through v7
ok - ci.yml runs this file unflagged exactly once, so the tag rule is evaluated (2 invocation(s) in total)
ok - and it is the last `run:` step in the workflow, so a red tag rule cannot mask the checks before it
ok - the open 0.11.0.dev0 section has 2 entries for the 0 commit(s) since v0.10.0
ok - the Changelog page restates the open 0.11.0.dev0 section one for one: 2 bullet(s) for 2 entries
ok - the changelog.mapping row names the 3 number(s) rule 14 counts
skip - the tag rule, deferred to the full unflagged run at the end of this job (--except-tag)
```

| component | version | reads |
|---|---|---|
| `ophtml` (PyPI) | 0.11.0.dev0 | `ps2ui_bake.__version__` |
| `@ophtml/layout` (npm) | 0.11.0-dev.0 | `packages/layout/package.json` |
| ui.json IR | 1 | `IR_VERSION` in `packages/layout/src/index.js` |
| `.uib` format | 7 | `VERSION` in `packages/baker/ps2ui_bake/uib.py` |
| `PS2UI_VERSION` (runtime macro) | 7 | `runtime/ps2ui.h` |

The table is this tree, a prerelease on neither registry. What
`pip install ophtml` and `npm install -g @ophtml/layout` give you is
the release: its `ps2ui --version` prints `ps2ui 0.10.0`.
Its `ps2ui-layout --version` prints `ps2ui-layout 0.10.0`. Both write
format 7, as this tree does. `PS2UI_VERSION` is the frozen
`.uib` format version, not a mechanism that stops the baker and the
runtime drifting apart by itself. Baker and runtime agree because
`ps2ui vendor-runtime` ships both files from one package in one
commit; see [the cross toolchain](page:runtime/integrating#the-cross-toolchain).

## Format compatibility

Format v7 is the last incompatible `.uib` layout. [The
pledge](page:reference/uib-format#the-pledge) states every future
addition lands in a feature bit, never a struct stride. 0.3.0
introduced v7; 0.4.0, 0.5.0, 0.6.0 and 0.7.0 each
record zero format moves since the release below them, in the
[changelog](page:project/changelog).

```
$ python3 tools/check-format-frozen.py
ok - the format is v7, the version the pledge froze
ok - MAGIC is 0x31424955, unchanged
ok - _CLUT is '<HHI', 8 bytes
ok - _CMD is '<BBHhhHHHHHHHHH6x', 32 bytes
ok - _FOCUS is '<HHHHHHIhhHH', 24 bytes
ok - _FONT is '<HHHHHHIH2xI', 24 bytes
ok - _GLYF is '<IHHHHhhH2x', 20 bytes
ok - _HEADER is '<IHHHHHHIHHIIIIIIIHHIIHHIIHHHH', 84 bytes
ok - _KERN is '<IIh2x', 12 bytes
ok - _SCREEN is '<IIIHHHHH2x', 24 bytes
ok - _SLOT is '<IIhhHHBBHHHHh', 28 bytes
ok - _TEX is '<BBHHHIII', 20 bytes
ok - _TINT is '<BBBB', 4 bytes
ok - FEAT_DYNAMIC_TEXT is still bit 0
ok - FEAT_KERNING is still bit 1
ok - FEAT_SLOT_SPACING is still bit 2
ok - FEAT_STREAMED_TEX is still bit 3
ok - FEAT_ROLE_TINTS is still bit 4
ok - FEAT_KNOWN (0x1f) still admits every frozen bit
ok - all 11 Struct(s) in uib are in the record
```

| runtime version | blob version | result |
|---|---|---|
| any v7 product (0.3.0 through 0.7.0) | any v7 product (0.3.0 through 0.7.0) | loads |
| any v7 product | pre-pledge (0.1.0 or 0.2.0, format v1 through v6) | refused, `PS2UI_ERR_VERSION` |
| pre-pledge (0.1.0 or 0.2.0) | any v7 product | refused, `PS2UI_ERR_VERSION` |

A 0.5.0 runtime loads a 0.7.0 blob and a 0.7.0 runtime loads
a 0.5.0 blob, because both write format v7 and `ps2ui_load` compares
only the header's `version` field against `PS2UI_VERSION`.

## Registries

Under 0.x a prerelease and a release both publish, but the two
registries guard a stranger against installing an unverified
prerelease in different ways.

| registry | package | prerelease mechanism | current state |
|---|---|---|---|
| npm | `@ophtml/layout` | `publishConfig.tag` set to `next` while the version is a prerelease; a plain `npm install` resolves the `latest` dist-tag, so the prerelease stays unreachable by it | `latest` serves the 0.10.0 release; this tree's prerelease carries `tag: "next"`, so a publish of it would not take `latest` |
| PyPI | `ophtml` | pip excludes a prerelease from a plain `pip install` unless no stable version satisfies the request | 0.10.0 is a release, so a plain `pip install ophtml` resolves it |

A release drops `publishConfig.tag`, or sets it to `latest`; pip needs
no equivalent step, because a real release already satisfies a plain
install once one exists. `check-versions.py` holds both directions:
a prerelease refused `latest` and a release refused any other tag.

## Platforms table

| platform | requirement | source |
|---|---|---|
| Node.js | 18 or newer | `packages/layout/package.json` |
| Python | 3.9 or newer | `packages/baker/pyproject.toml` |
| Pillow | 9 or newer | `packages/baker/pyproject.toml` |
| uharfbuzz | 0.51.7 or newer; pip installs it | `packages/baker/pyproject.toml` |
| macOS, Windows | nothing beyond the two wheels, since 0.9.0 | CHANGELOG.md 0.9.0 section |
| host C compiler | `cc` or clang, for `make -C runtime test` | `runtime/Makefile` |
| gsKit (host tests) | vendored headers pinned to commit `43122eb96289167975b56caa45beb71eb8684fa2` | `runtime/vendor/README.md` |
| PS2SDK / ps2dev toolchain | `ghcr.io/ps2dev/ps2dev:latest`, deliberately unpinned | `.github/workflows/hw.yml` |

Install both packages per
[installation](page:getting-started/installation#what-you-need).
**Until 0.9.0, macOS and Windows needed fribidi.** 0.8.0's
`ps2ui-fontgen` measured through Pillow's Raqm engine, which Pillow
compiles in and which loads `fribidi` from the machine at run time, so
a stock Mac or Windows box refused until fribidi was supplied.
`registry.yml` run 35809073289 measured it: a plain install refused on
all three; `brew install fribidi` alone cleared it on Intel but not on
Apple silicon, which needed a Pillow rebuild; and the MSYS2 DLL on
`PATH` cleared it on Windows.

0.9.0 measures through `uharfbuzz`, whose wheels carry HarfBuzz whole,
and reproduces 0.8.0's tables exactly. `ci.yml` runs `ps2ui fontgen`
on stock macOS arm64, macOS x86_64 and Windows runners on every pull
request, with nothing installed but the package. The `.uib` format and the runtime are not involved either
way; this is a property of the authoring host.

### What each platform has actually been run on

| platform | evidence |
|---|---|
| Linux (`ubuntu-24.04`) | every job in `ci.yml` and `hw.yml`, on every push |
| macOS arm64 | `registry.yml`, weekly and on release; `ci.yml`'s `ps2ui fontgen` job on every pull request |
| macOS x86_64 | the same two |
| Windows x86_64 | the same two; the first `registry.yml` run, 35809073289, passed every Windows leg |

Nothing else has been tried. A platform missing from this table is not
known to fail; it is not known at all.

The host test suite compiles against real gsKit declarations instead
of a hand-written stub, on either compiler, so a struct-shape or
prototype mismatch fails the build rather than passing silently. The
console build takes its PS2SDK and gsKit headers from the same
unpinned ps2dev image, kept unpinned on purpose so an upstream change
shows up as a watch rather than staying frozen out of sight.

## Names

`OPHTML` is the product. The format and its tooling keep the name they
always had: `.uib`, `ps2ui.h`, and every `ps2ui`, `ps2ui-bake`,
`ps2ui-check`, `ps2ui-fontgen` and `ps2ui-layout` command. Only the two
registry names moved, to `ophtml` on PyPI and `@ophtml/layout` on npm.
