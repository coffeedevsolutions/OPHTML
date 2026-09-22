# facts: project/changelog

This page emits no new facts. It restates CHANGELOG.md's Unreleased
0.8.0.dev0 section by category and lists the earlier release headings;
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
  same output counted 31 entries under the open section's two headings
  against 31 bullets under the page's three.

| id | fact | source | verified by | status |
|---|---|---|---|---|
| changelog.mapping | Every 0.8.0.dev0 bullet on this page maps to one entry in `CHANGELOG.md`'s open section, and the map is now onto: **thirty-one bullets for thirty-one entries**, one each. The file carries two headings, `### Added` with three entries and `### Fixed` with twenty-eight. The page carries three, because the twenty-eight split by who is affected rather than by kind: eighteen changed the toolchain a project uses, ten changed the checker that reads these pages and no compiler, runtime or format behaviour. **The page restated five of the twenty-four then open until this change** -- its own sentence claimed only that every bullet on it had an entry in the file, which held, so nothing failed while nineteen were missing. Found by F41(a) while re-pointing these citations, widened by F42, filed rather than fixed both times because those changes were about the checker | `CHANGELOG.md:17, 19-66, 69, 71` (`### Added`, its three entries, `### Fixed`, the first of its twenty-eight). **Written as a comma list on purpose.** `FACTS_CITE` pins every member of one and `--fix` moves each. The shape this cell used to use wrote every member after the first as a colon and a number with no path in front of it, which named nothing the checker could read: it pointed at 32 for `### Fixed` while that heading sat at 49, and at 34, 56, 71 and 90 for four bullets that were at 51, 73, 88 and 107. **The numbers in that last sentence are spelled without their colons on purpose**, because F42 made the shape a failure and nothing can tell an example of it from a use of it | re-derived this session: a pass over the open section counts `### Added` at 17 with three entries from 19 and `### Fixed` at 69 with twenty-eight from 71, thirty-one in all; the same pass over the page counts `### Added` at 23 with three, `### Fixed in the toolchain` at 42 with eighteen and `### Fixed in the documentation checker` at 119 with ten, thirty-one in all. **The previous version of this row, including the one F41(a) itself wrote, claimed an `awk` run that put the headings at 17 and 32** -- 32 is the second Added entry, and no run of that command ever said otherwise | verified |
| changelog.earlier-releases | The Earlier releases table's three rows read straight from the CHANGELOG headings and their format paragraphs: `## 0.5.0 — 2026-09-06` (format v7, zero moves since 0.4.0); `## 0.4.0 — 2026-09-06` (format v7, zero moves since 0.3.0, the v7 stability pledge and vendored DejaVu fonts added in that section); `## 0.3.0 — 2026-09-04` (format v7, four moves since 0.2.0: v4 display aspect, v5 kerning, v6 texture kinds, v7 tint table; first tagged release). | `CHANGELOG.md:1214, 1217, 1252` (the 0.5.0 heading, the `vendor-runtime` entry its headline restates, and the format paragraph that section carries); `CHANGELOG.md:1264, 1266, 1279, 1290` (0.4.0, its format paragraph, the stability-pledge entry, the vendored-fonts bullet); `CHANGELOG.md:1354, 1356, 1368` (0.3.0, its format paragraph naming the four moves, the first-tagged sentence). **The previous version of this cell cited 0.7.0, 0.6.0 and 0.5.0 for a table whose three rows are 0.5.0, 0.4.0 and 0.3.0**, and two of its three numbers sat on prose in the middle of a release rather than on a heading. It stayed green throughout: whatever those lines once named, a `--pin` run recorded the text they held by then, and the drift test has faithfully kept them on it since. **A pin proves a line has not moved, not that it was the right line.** | a pass over `^## ` in this session puts the release headings at 1026, 1076 and 1166, and the three format paragraphs at 1064, 1078 and 1168; each cited line was read directly. The table's three headlines were re-read against those sections: `vendor-runtime` ships the runtime from the installed package (1029), the v7 pledge and `fonts/vendor/` (1091, 1102), and the first tagged release with four moves v4 through v7 (1168, 1180) | verified |
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
