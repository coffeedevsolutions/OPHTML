# facts: project/changelog

This page emits no new facts. It restates CHANGELOG.md's Unreleased
0.6.0 section by category and lists the earlier release headings; every
row below is a parent fact this page relied on, cited by the parent
page and facts file that verified it, plus two rows verified directly
in this session.

Session commands run from the repository root:

- `python3 tools/check-versions.py --except-tag` printed 27 `ok -`
  lines and 1 `skip -` line, exit 0. The 7 lines pasted on the page
  (rules 2 through 7: the two package versions, `PS2UI_VERSION` against
  `uib.VERSION`, the two `docs/format-uib.md` checks, and the newest
  two CHANGELOG section checks) are copied verbatim from this run.
- `grep -n '^- \*\*\|^### ' CHANGELOG.md` located every bullet and
  heading cited below by symbol, in this session.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| changelog.mapping | Every 0.6.0 bullet on this page maps to a `### ` entry in CHANGELOG.md's Unreleased section: Added -> CHANGELOG.md:54-91 (`ps2ui_offset_set`); Fixed -> CHANGELOG.md:6-16 (`ps2ui dev` flags), :17-25 (README/CONTRIBUTING test-compat), :26-53 (Raqm remedy), :93-102 (vendor-runtime message), :125-156 (`ps2ui check` settings), :157-213 (impossible VRAM budget). The PyPI-page and Rule-10 bullets at CHANGELOG.md:103-123 are release procedure, out of scope per this page's brief and left to `project/internals`. | CHANGELOG.md | `grep -n '^- \*\*\|^### ' CHANGELOG.md` in this session, output pasted above | verified |
| changelog.earlier-releases | The Earlier releases table's three rows read straight from the CHANGELOG headings and their format paragraphs: `## 0.5.0 — 2026-09-06` (format v7, zero moves since 0.4.0); `## 0.4.0 — 2026-09-06` (format v7, zero moves since 0.3.0, the v7 stability pledge and vendored DejaVu fonts added in that section); `## 0.3.0 — 2026-09-04` (format v7, four moves since 0.2.0: v4 display aspect, v5 kerning, v6 texture kinds, v7 tint table; first tagged release). | CHANGELOG.md:215, :265, :355 and their Added/format paragraphs | `grep -n '^## ' CHANGELOG.md` and the headings and format paragraphs read directly in this session | verified |
| compat.versions | `ophtml` is 0.7.0 and `@ophtml/layout` is 0.7.0, the same version in two spellings. Neither package is tagged. | reference/compatibility (parent) | restated without new verification; this session's own `check-versions.py` run reproduces the same line | verified |
| compat.format-matrix | Format v7 is unchanged since 0.5.0: CHANGELOG.md counts zero format moves since that release, and a v7 blob loads under a v7 runtime regardless of the two products' package versions. | reference/compatibility (parent) | restated without new verification; this session's own `check-versions.py` run printed the same "zero format moves since 0.5.0" confirmation the parent cites | verified |
| offset.new | `ps2ui_offset_set` (F27) is the 0.6.0 addition; runtime visibility is older, from 0.3.0. | runtime/moving-and-hiding (parent) | restated without new verification | verified |
| offset.contract | The offset is a draw-time transform over commands that already exist; it changes no file and no format version, and out-of-range calls return `PS2UI_ERR_RANGE` leaving the old offset. | runtime/moving-and-hiding (parent) | restated without new verification | verified |
| offset.no-format-change | The offset works on a blob baked by any 0.x toolchain because no record, header field or version moved for it. | runtime/moving-and-hiding (parent) | restated without new verification | verified |
| cli.dev.inert-flags | `--strict` and `--min-font-size` now reach the linter in `ps2ui-dev`: the bin puts the floor in `options.lint` and `--strict` fails the build before the bake. Fixed on this branch; before it both flags were accepted and inert (D9). | cli/ps2ui-layout (parent, `_facts/cli/ps2ui-layout.md`) | restated without new verification | verified |
| integrate.test-targets | `runtime/Makefile` declares `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. No `test-compat` target exists; CONTRIBUTING.md told a contributor to run the missing target (D1), and now names `make test` and `make syntax-check CC=clang` instead. | project/contributing (parent, `_facts/project/contributing.md`) | restated without new verification | verified |
| fontgen.raqm.remedy | The Raqm refusal reports the detected Pillow version, platform and machine, and asks about `fribidi` separately rather than stating a platform rule. | cli/ps2ui-fontgen (parent) | restated without new verification | verified |
| fontgen.raqm.rebuild-hint | Fribidi missing leads with `brew install fribidi` / `apt install libfribidi0` / `dnf install fribidi`, no rebuild; the Pillow rebuild is the fallback. | cli/ps2ui-fontgen (parent) | restated without new verification | verified |
| integrate.vendor.notes-when-written | The vendor-runtime docker line, the three Makefile lines and the two closing links print only when the run wrote a file, and name the cross-compile constraint rather than a repository path an installed user cannot open. | runtime/integrating (parent) | restated without new verification | verified |
| vram.key.project | New in 0.6.0: the project key `vramBudget` reaches `ps2ui-bake` and `ps2ui-check` alike, so a build and a check on the same project agree on one number. | authoring/vram-budget (parent) | restated without new verification | verified |
| vram.impossible-default | Past a canvas width, three framebuffers cannot fit in 4 MiB and the default budget goes negative; the bake now names both the framebuffer arithmetic and the two-buffer figure that clears it, instead of blaming the textures. | authoring/vram-budget (parent) | restated without new verification | verified |
| vram.impossible-default.check | Under an impossible default, `ps2ui-check` appends a note to the VRAM label and prints the same two explanatory lines as the bake. | authoring/vram-budget (parent) | restated without new verification | verified |

## disputes

None. No parent fact was found wrong.
