# facts: project/changelog

This page emits no new facts. It restates CHANGELOG.md's newest
section, 0.11.0.dev0, and the 0.10.0 release section by category and lists the earlier release headings;
every row below is a parent fact this page relied on, cited by the
parent page and facts file that verified it, plus two rows verified
directly in this session.

**This file describes a page that is rewritten every cycle, and nothing
mechanical notices when it stops matching.** It carried the 0.6.0
restatement for two releases, and then restated five of the open
section's entries for two more. Three checks were green through all of
it. `_citations.tsv` holds fourteen rows for this facts file and zero
for the page, so `check-site-pages` pins what the rows below cite and
nothing at all about what the page chooses to restate. Fourteen pinned
rows is also the smaller half of the lesson: two of them spent this
cycle sitting on prose in the middle of a release, green, because
**a pin proves a line has not moved, not that it was the right line.**
`check-doc-versions` reads banners and its own docstring says it does
not read the sentence around one. `check-doc-impact` is file-level, so
a document that *should* cite a changed file and does not is invisible
to it -- its own caveat line says so. Re-read this file whenever the
page is re-restated, and count the bullets against the section.

Session commands run from the repository root:

- `python3 tools/check-versions.py --except-tag` exited 0 with one
  `skip -` line, and each of the 7 lines below was matched against
  that run's output. **THE COUNT OF `ok -` LINES USED TO BE HERE AND IS
  GONE ON PURPOSE.** It said 27, which three added rules had made
  false; it was corrected to 30 in this change, and the rule that
  change itself added made it 31 before the commit landed. The
  sentence recording that the number went stale because rules were
  added went stale because a rule was added, in the same commit.
  `BACKLOG.md`'s closed-log marker settled this shape already -- its
  first version counted commits and releases since, both wrong by the
  commit that added them, and the fix was to keep the date and drop
  the count. A total that every new rule invalidates is evidence the
  run happened and nothing more, and the exit status says that
  without rotting. The 7 lines pasted on the page
  (rules 2 through 7: the two package versions, `PS2UI_VERSION` against
  `uib.VERSION`, the two `docs/format-uib.md` checks, and the newest
  two CHANGELOG section checks) are copied verbatim from this run.
- `grep -n '^- \*\*\|^### ' CHANGELOG.md` located every bullet and
  heading cited below by symbol, in this session, and a pass over the
  same output counted 2 entries under the open section's one heading
  against 2 bullets under the page's one, and 12 under 0.10.0's three
  against 12 on the page.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| changelog.mapping | The open 0.11.0.dev0 section maps **two bullets for two entries**, the depth cap that now runs before `data-repeat` expansion and the image-cap test's corpus walk: `### Fixed` at 17 with two in `CHANGELOG.md`, and `### Fixed` at 21 with two on the page, and rule 14 holds the page's `## 0.11.0.dev0` to that count as entries land. **Rule 15 reads this cell**, which is what makes the arithmetic a claim something checks rather than prose that goes stale at the next entry: two versions of this row were corrected by hand twice in one session before that rule existed, each time after the cell beside them had just been corrected. The 0.10.0 notes below it map twelve bullets to the twelve entries of `CHANGELOG.md`'s 0.10.0 section: `### Added` with six (the console, its theme check and preview, the caps, the launcher's download and page, the released-section check, the loader fuzzing), `### Changed` with one (the registry.yml cleanup) and `### Fixed` with five (the two faults the fuzzing found and the three the caps closed) | `CHANGELOG.md:17, 19, 40` (the open section's `### Fixed` and its two entries); `CHANGELOG.md:65, 67, 89, 111, 159, 175, 185` (0.10.0's `### Added` and its six); `CHANGELOG.md:197, 199` (its `### Changed` and the registry.yml entry); `CHANGELOG.md:214, 216, 229, 240, 250, 259` (its `### Fixed` and its five). The counts in this row are held to rule 15 of `check-versions.py`, which derives them from the same pass rule 14 counts with | `python3 tools/check-versions.py --except-tag` printed "the Changelog page restates the open 0.11.0.dev0 section one for one: 2 bullet(s) for 2 entries" and "the changelog.mapping row names the 3 number(s) rule 14 counts"; the 0.10.0 mapping was counted at the 0.10.0 cut, when rule 14 printed 12 for 12 | verified |
| changelog.earlier-releases | The Earlier releases table's seven rows read straight from the CHANGELOG headings and the entries their headlines restate, every one of them format v7: `## 0.9.0 — 2026-09-23` (F47: `ps2ui fontgen` kerns through `uharfbuzz`, not Pillow's Raqm); `## 0.8.0 — 2026-09-23` (the Windows and Intel Mac CI arms, and the version banners held to what commands print); `## 0.7.0 — 2026-09-17` (`vendor-runtime --starter`, the `:focus` rules, the eight checked keywords); `## 0.6.0 — 2026-09-12` (`ps2ui_offset_set`, and `ps2ui check` given `ps2ui build`'s settings); `## 0.5.0 — 2026-09-06`; `## 0.4.0 — 2026-09-06` (the v7 stability pledge and vendored DejaVu fonts); `## 0.3.0 — 2026-09-04` (four moves since 0.2.0, v4 through v7; first tagged release). **0.6.0 and 0.7.0 were missing from this table** from their own releases until the 0.9.0 cut added them with 0.8.0 | `CHANGELOG.md:272, 288` (0.9.0 and F47's entry); `CHANGELOG.md:337, 353, 383` (0.8.0, the version-banner entry, the platforms entry); `CHANGELOG.md:1297, 1313, 1373, 1418` (0.7.0 and its three restated entries); `CHANGELOG.md:1568, 1572, 1670` (0.6.0 and its two); `CHANGELOG.md:1760, 1810, 1900` (the three older headings) | read against `grep -n '^## ' CHANGELOG.md` and each cited entry at the 0.9.0 cut, and the 0.9.0 row at the 0.10.0 cut | verified |
| compat.versions | This tree's `ophtml` is 0.11.0.dev0 and `@ophtml/layout` is 0.11.0-dev.0, the same version in two spellings; the release both registries serve is 0.10.0, tagged `v0.10.0`. | reference/compatibility (parent) | after step 9 `check-versions.py --except-tag` printed "@ophtml/layout 0.11.0-dev.0 and ophtml 0.11.0.dev0 are the same version in the two spellings" | verified |
| compat.format-matrix | Format v7 is unchanged since 0.10.0: CHANGELOG.md counts zero format moves since that release, and a v7 blob loads under a v7 runtime regardless of the two products' package versions. | reference/compatibility (parent) | after step 9 `check-versions.py` printed "CHANGELOG counts zero format moves since 0.10.0, and v7 -> v7 is 0" | verified |
| offset.new | `ps2ui_offset_set` (F27) is the 0.6.0 addition; runtime visibility is older, from 0.3.0. | runtime/moving-and-hiding (parent) | restated without new verification | verified |
| offset.contract | The offset is a draw-time transform over commands that already exist; it changes no file and no format version, and out-of-range calls return `PS2UI_ERR_RANGE` leaving the old offset. | runtime/moving-and-hiding (parent) | restated without new verification | verified |
| offset.no-format-change | The offset works on a blob baked by any 0.x toolchain because no record, header field or version moved for it. | runtime/moving-and-hiding (parent) | restated without new verification | verified |
| cli.dev.inert-flags | `--strict` and `--min-font-size` now reach the linter in `ps2ui-dev`: the bin puts the floor in `options.lint` and `--strict` fails the build before the bake. Fixed on this branch; before it both flags were accepted and inert (D9). | cli/ps2ui-layout (parent, `_facts/cli/ps2ui-layout.md`) | restated without new verification | verified |
| integrate.test-targets | `runtime/Makefile` declares `test`, `test-narrow`, `syntax-check`, `timing-check`, `clean`. No `test-compat` target exists; CONTRIBUTING.md told a contributor to run the missing target (D1), and now names `make test` and `make syntax-check CC=clang` instead. | project/contributing (parent, `_facts/project/contributing.md`) | restated without new verification | verified |
| integrate.vendor.notes-when-written | The vendor-runtime docker line, the three Makefile lines and the two closing links print only when the run wrote a file, and name the cross-compile constraint rather than a repository path an installed user cannot open. | runtime/integrating (parent) | restated without new verification | verified |
| vram.key.project | New in 0.6.0: the project key `vramBudget` reaches `ps2ui-bake` and `ps2ui-check` alike, so a build and a check on the same project agree on one number. | authoring/vram-budget (parent) | restated without new verification | verified |
| vram.impossible-default | Past a canvas width, three framebuffers cannot fit in 4 MiB and the default budget goes negative; the bake now names both the framebuffer arithmetic and the two-buffer figure that clears it, instead of blaming the textures. | authoring/vram-budget (parent) | restated without new verification | verified |
| vram.impossible-default.check | Under an impossible default, `ps2ui-check` appends a note to the VRAM label and prints the same two explanatory lines as the bake. | authoring/vram-budget (parent) | restated without new verification | verified |

## disputes

None. No parent fact was found wrong.
