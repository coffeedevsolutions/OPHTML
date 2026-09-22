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

The open 0.8.0.dev0 section of `CHANGELOG.md`, restated by category, one
bullet here for each entry there. The file carries the reasoning and the
measurements; this page carries what changed.

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
- `check-versions.py` asks whether a CHANGELOG section has any content,
  and asked it only of a release tree. A whole cycle could accumulate
  silence and land at the cut as N changes to reconstruct from the log.
  Rule 10c warns on a prerelease too, and can never fail, because the
  honest answer to "should this have an entry?" is sometimes no.

- `registry.yml` had one non-Linux arm and it is now a deprecated
  runner image, so the three jobs pinned to `macos-14` move to
  `macos-15` and gain `macos-15-intel`, while the tutorial job gains
  `windows-2025` beside a new `windows-plain`. Intel is not symmetry:
  both macOS wheels name Intel's Homebrew prefix as their only absolute
  fribidi candidate, so the two arms are the two sides of the
  "probably" the remedy message has carried for a cycle.

### Fixed in the toolchain

- The remedy that ships inside the wheel sent Windows readers to build
  Pillow from source. 0.7.0 removed a false claim from that branch and
  left them on the general one, which wants MSVC and a native
  dependency chain on Windows. The wheel says the gap is fribidi, as it
  is everywhere else, so the message names the three DLLs and the
  `PATH` requirement instead. Read off the binary and not off a Windows
  machine, which the compatibility page now says in as many words. The
  first version of that fix led the reader in a circle -- its win32 arm
  sat inside the source-build hint and then declined the source build,
  so both callers promised a rebuild and neither delivered one. The
  routing is the fix, and a second test fences the shape rather than the
  spelling.

- Nothing read the documentation library backwards, so a citation to a
  deleted file pointed at nothing indefinitely. `check-doc-impact.py`
  reads a facts row's source cell structurally now, resolves a citation
  that names no directory, and runs the graph backwards to report what
  the library still cites that the tree no longer holds. It reaches 58
  documents for `runtime/ps2ui.h` where it reached 45, and 513 more
  citations across the library.
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
- `ps2ui check build/ui.uib` ended in a `UnicodeDecodeError` on a blob it
  could not read as text. It names the file and what it expected now.
- `ps2ui serve --port <busy>` printed a bind traceback, and `--help` did
  not say the port could be taken. Both say it.
- A stylesheet with three mistakes cost three builds, because the CSS
  stage stopped at the first. Every error in a sheet is reported in one
  pass now, one `error:` line each, sorted by line.
- A declaration was reported at the line its rule opens on rather than
  its own, so a long rule pointed every mistake at the same place.
- `:hover` was answered with `unsupported selector syntax near ":"`. A
  pseudo-class the target does not implement is named, with `:focus`
  given as the one that exists.
- `border-radius` costs a flat eight records a box, whatever the radius,
  because a square box is one record and a rounded one is a nine-cell
  patch. The CSS reference says so beside the property and in
  [what a rounded corner costs](page:authoring/css#what-a-rounded-corner-costs).
- The previewer and `build/preview.png` are different sizes, and the
  self-test said "byte-identical" without naming which frame it had
  compared. It names the frame, and both sizes are stated where a reader
  meets them.
- This page restated a shipped release while calling it the open one.
- And then it restated five of the open section's entries and called
  that a mapping. The sentence above the list used to promise only
  that every bullet here had an entry in the file, which is true of
  any five of them. It now promises one bullet for each entry, and
  the list keeps that promise. Writing the entry for that fix moved
  every line under it, and the move turned up a second one: the table
  of earlier releases below cited three releases it does not list, on
  lines that had drifted onto prose. It was never red. A pin proves a
  line has not moved, not that it was the right line. The new promise
  is counted by `ps2ui`'s version checker, because a promise that can
  be false and is never read is the same shape as the one it replaced.
- The audit that catches stale ticks on the backlog had missed rows
  three times. `tools/check-backlog.py` holds every row ID, every
  tick-claim and every open row to each other now, and CI runs it. It
  found a row showing 178 of its 6129 characters on its first run.
  Review found it reading a scaffolded marker as a shipped one, and a
  table split by a blank line as having no rows to check at all. A
  second review found the screen for an unrecognised marker looking
  only at the first one on a line, so a known marker ahead of it hid
  it. Both are fixed and both are fenced.

### Fixed in the documentation checker

Eleven entries: ten about `tools/check-site-pages.py`, which holds every
claim here to the lines it cites, and one about
`tools/check-tutorial.py`. No runtime or format behaviour.

- The tutorial checker printed only the last line of a failing block:
  the wrapper's summary, not the compiler's explanation above it. The
  Windows arm reported `ps2ui build` exiting 1 with its cause already
  discarded. It keeps twenty lines, counts what it drops, and shows what
  a mismatched block printed beside what was claimed. Fenced by
  `--selftest`: a passing tutorial prints no report.

- A comma list was one citation instead of several, so
  `ps2ui.h:653,660,668` pinned the first number and left the rest
  unread. 122 members came into view.
- 424 line numbers named no file, because a citation was only recognised
  when its path began with one of six directories. A file at the
  repository root matched none of them. 27 of the newly readable ones
  were wrong when they were taken.
- The checker counted one line more than every file had, so a citation
  could name the line after the last one and never drift. The count is
  asserted against bytes the tool writes itself.
- A member written as a colon and a number, with no path, named nothing
  any reader could follow. 424 of them now name their path, and writing
  one that does not fails. 57 were wrong.
- An annotation beside a citation is a claim. `ps2ui.py:290-305
  (cmd_check)` says those lines are `cmd_check`, and nothing checked it.
  Two of the four faults found had been green since the day they were
  written.
- A stronger drift test was measured and rejected. It would catch 110 of
  69810 simulated insertions and fire on every in-place edit of the line
  above a citation. The measurement is recorded where the design is.
- Fifty-eight citations named the line before the thing they meant, and
  the ranges prove it: each was the exact length of the construct it
  described, displaced by exactly one. A citation that starts on a blank
  line now fails.
- Three of the seven most-cited rows named the wrong lines, found by
  reading them against the code rather than by any check. Twelve wrong
  members in fifty-nine.
- The annotation rule is widened as far as it goes, and that is not far:
  sixty citations checked before, sixty-eight after, no new faults.
- One screen had a hole. Four members separated by slashes instead of
  commas tripped neither reader, in the row that most needed reading.

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

A v7 blob loads under any other v7 product, which is every release from
0.3.0 on; the drift count above is how far back this section counts, not
how far compatibility reaches. The pledge behind that guarantee is on
[Compatibility](page:reference/compatibility#format-compatibility).

## Earlier releases

| version | date | format | headline |
|---|---|---|---|
| 0.5.0 | 2026-09-06 | v7 | `ps2ui vendor-runtime` ships the C runtime from the installed package; the console half needs no clone. |
| 0.4.0 | 2026-09-06 | v7 | The `.uib` v7 stability pledge, and vendored DejaVu fonts for a checkout with no system font. |
| 0.3.0 | 2026-09-04 | v7 | First tagged release. Breaking authoring and runtime changes; four format moves land, v4 through v7. |

Full history: [CHANGELOG.md](repo:CHANGELOG.md).
