# facts: project/changelog

This page emits no new facts. It restates CHANGELOG.md's Unreleased
0.8.0.dev0 section by category and lists the earlier release headings;
every row below is a parent fact this page relied on, cited by the
parent page and facts file that verified it, plus two rows verified
directly in this session.

**This file describes a page that is rewritten every cycle, and nothing
mechanical notices when it stops matching.** It carried the 0.6.0
restatement for two releases: `check-site-pages` is green because no
row here is line-pinned (`_citations.tsv` has zero rows for
`project/changelog`), `check-doc-versions` reads banners and its own
docstring says it does not read the sentence around one, and
`check-doc-impact` is file-level, so a document that *should* cite a
changed file and does not is invisible to it -- its own caveat line
says so. Re-read this file whenever the page is re-restated.

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
| changelog.mapping | Every 0.8.0.dev0 bullet on this page maps to an entry in `CHANGELOG.md`'s Unreleased section: the page's one Added bullet to the version-banner fence, and its four Fixed bullets to the font path, the build line, `--starter` and the Installation page, in that order. Five bullets under two headings, which is what the page shows. **The section has grown to nineteen entries and the page still shows five** -- the page's own sentence claims only that every bullet on it has an entry in the file, which holds, but the fourteen added since are not restated. Found by F41(a) while re-pointing these citations and widened by F42; filed rather than fixed here, because it is a content gap and this change is about the checker. | `CHANGELOG.md:17, 19-30, 49` (`### Added`, the version-banner fence, `### Fixed`); `CHANGELOG.md:181-201, 203-216, 218-235, 237-245` (the four Fixed bullets the page restates). **Written as comma lists on purpose.** `FACTS_CITE` pins every member of one and `--fix` moves each. The shape this cell used to use wrote every member after the first as a colon and a number with no path in front of it, which named nothing the checker could read: it pointed at 32 for `### Fixed` while that heading sat at 49, and at 34, 56, 71 and 90 for four bullets that were at 51, 73, 88 and 107. **The numbers in that last sentence are spelled without their colons on purpose**, because F42 made the shape a failure and nothing can tell an example of it from a use of it | re-derived this session: `awk` over the open section puts `### Added` at 17 and `### Fixed` at 49, the two Added bullets at 19 and 32, and seventeen Fixed bullets from 51; the page's own rendered bullets counted five under the same two headings. **The previous version of this row, including the one F41(a) itself wrote, claimed an `awk` run that put the headings at 17 and 32** -- 32 is the second Added bullet, and no run of that command ever said otherwise | verified |
| changelog.earlier-releases | The Earlier releases table's three rows read straight from the CHANGELOG headings and their format paragraphs: `## 0.5.0 — 2026-09-06` (format v7, zero moves since 0.4.0); `## 0.4.0 — 2026-09-06` (format v7, zero moves since 0.3.0, the v7 stability pledge and vendored DejaVu fonts added in that section); `## 0.3.0 — 2026-09-04` (format v7, four moves since 0.2.0: v4 display aspect, v5 kerning, v6 texture kinds, v7 tint table; first tagged release). | CHANGELOG.md:394, CHANGELOG.md:604, CHANGELOG.md:796 (the `## 0.7.0`, `## 0.6.0` and `## 0.5.0` headings) and their Added/format paragraphs | `grep -n '^## ' CHANGELOG.md` and the headings and format paragraphs read directly in this session | verified |
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
