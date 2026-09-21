# Changelog

## Unreleased — 0.8.0.dev0

`.uib` format **version 7**, unchanged from the release below.
Zero format moves have landed since 0.7.0, which is what a section
opened straight after a release should say: the release under it
shipped the format this tree still writes, so a blob baked here loads
under a 0.7.0 runtime and the other way round.

That count is the one number in this file that starts correct and
decays. It becomes one the moment a format move lands, and
`tools/check-versions.py` derives it from the section below rather than
reading it back, so the check fails the change that moves the format
without moving this line.

### Added

- **A version a document prints is now held to the version something
  prints.** `check-site-pages.py` pins a citation to the line it names,
  which is exact and cannot see a version *flowing* through a file the
  row does not cite: `cli.bake.version` cites `cli.py`, which formats
  `__version__` and never moves, while the number moves in
  `__init__.py`. Ten rows survived the 0.8.0.dev0 bump asserting 0.7.0
  with every citation green, and a reviewer found them by grepping.
  `tools/check-doc-versions.py` records every version banner in
  `docs/site` as meaning the tree or the last release and fails when one
  stops naming what it was pinned to. 28 banners today. It runs in
  `ci.yml` and `docs.yml`, and `docs/releasing.md` step 9 says to run it
  after the four edits: the red list is the work.

- **The CHANGELOG's silence is visible on a prerelease too.**
  `check-versions.py` asks whether a section has any content and fired
  only on a release tree, which is right: `docs/releasing.md` step 9
  opens an empty `## Unreleased` on purpose and failing that step is the
  trap the rule was shaped around. The cost was that nothing asked the
  same question of a prerelease, so the omission accumulated through a
  cycle and landed at the cut as N changes to reconstruct from
  `git log`. The rule's own comment already recorded one occurrence, six
  pull requests between 0.3.0 and the rule listed nowhere; this cycle
  was the second, five changes and zero entries with every check green.

  Rule 10c warns and can never fail, because the honest answer to
  "should this have an entry?" is sometimes no. The threshold is safe
  rather than timid: straight after step 9 the count since the previous
  release is exactly one, the back-to-development commit itself, so it
  cannot fire on the step it was designed around.

### Fixed

- **Fifty-eight citations named the line before the thing they meant,
  and the ranges prove it was drift rather than sloppiness.** 55 of the
  1681 pinned records started on a line with no content: 25 blank, 30
  nothing but punctuation. Every one of the 24 blank-start ranges was
  the exact length of the construct it described and displaced by
  exactly one -- `ps2ui.h:800-806` for a comment and declaration that
  run 801 to 807, seven times over in the list block alone. A range
  that is correctly sized and uniformly displaced was right when it was
  written; the file moved under it. The `.c` side is the same story two
  lines wide, where seven citations each named the brace closing the
  *previous* function.

  A citation that starts on a blank line now fails, with the line the
  content actually begins on in the message, **in both places a
  citation lives**: the guard shipped on facts rows alone at first, and
  a `repo:` link could still pin a record with an empty text cell
  through the other door. **Blank only, not punctuation**: `{` opens a
  JSON file at line 1 and `/**` opens a doc comment, and both are the
  honest first line of what they cite, so the wider rule would have
  been wrong about seven citations to buy the same twenty-four.

  **A mechanical `+1` is not a reading, and two of these needed one.**
  Where the range carries its own length the correction proves itself;
  two single-line members had no length to be right about, and moving
  them to the next line landed them on nothing. `cli.dev.output-lines`
  listed six printed lines and cited six places that were not print
  sites; they are at 127, 163, 167, 170, 194 and 183. `aspect.flags.project`
  cited prose in an unrelated docstring. Both are read now.

  The rule turned out to fence the historical fault and not just the
  shape. Inserting one line above the list block makes it fire on five
  citations at once, because what it guards is exactly the population
  that sits after a blank line and moves.

- **A stronger drift test was measured and rejected, which is the
  entry.** Each record carries the two lines around the one it pins,
  and only relocation reads them; comparing the whole window would
  catch a citation that comes to name a different line while the text
  at that number stays the same. Simulating 1, 2 and 3-line insertions
  at 25 points in every cited file -- 69810 pairs -- the text test
  misses 110 of them, 0.16%, and the window test catches all 110. The
  misses are 57 blank-line pins and 53 punctuation ones, so it is not a
  blank-line problem with a blank-line fix.

  **The same run on the tree that ships misses nothing: 0 of 69714.**
  The corrections above emptied the population, so the window test is
  being offered in exchange for a benefit that no longer exists. And
  the cost was mislabelled the first time: comparing the window fires
  on 1641 of 1641 in-place edits of the line *above* a citation, 100%,
  as it must, since that line is in the comparison. Gating it on a
  pinned text that repeats brings that to 97 of 1641, and those are the
  ones relocation cannot quietly resolve. Nothing to gain against
  either number. The measurement and the verdict live in `drifted_from`
  so the next reader does not have to re-derive them to turn the idea
  down.

- **424 line numbers in the facts library named no file, and one of
  them cited three lines past the end of one.** A run of citations was
  written as `css.js:639-653, :605, :625-630`, where every member after
  the first is a colon and a number. `FACTS_CITE` needs a path, so it
  read the first and walked past the rest: 431 such tokens across 227
  cells, 64 in `authoring/css` alone. Every member now names its path,
  and writing one that does not is a failure with the fix in the
  message.

  **The checker was not taught to read the shape, and the reason is in
  the corpus.** Seven of the 431 are prose. `changelog.mapping`
  explains how it once cited 32 for a heading that sat at 49, and it
  explained that by writing the token. In
  `ps2ui.c:675-733 (`:692` kind)` the same characters are a citation.
  Nothing but intent separates them, so a checker that bound a bare
  member to the last path it saw would have pinned a sentence's example
  and then let `--fix` quietly rewrite the sentence. One spelling and a
  rule against the other is the only reading that cannot guess wrong.

  **57 of the 424 were wrong, and 48 of the 57 are in four rows.** The
  damage is not an even scatter, it is whole lists that went stale
  together, because a list nobody reads is a list nobody re-derives.
  `css.properties` was 178 to 191 lines low on every one of its 32
  numbers -- an ordered snapshot of a `css.js` that had since grown by
  about 180 lines -- while its own verified-by cell said a `grep` had
  returned exactly those cases. It is now 38 numbers derived from
  `applyDeclaration`'s span, carrying the 45 properties the fact names.
  `loop.order` had eight of its nine lifecycle steps landing in
  comments and closing braces.

- **An annotation beside a citation is a claim, and nothing checked
  it.** `ps2ui.py:290-305 (`cmd_check`)` says two things: that those
  lines have not moved, which the pin checks, and that they are
  `cmd_check`, which nothing did. Two of the four faults this found had
  been pinned and green since the day they were written, which is the
  previous entry's finding one layer down: the pin protects a line from
  moving, not a citation from naming the wrong thing.

  **The obvious rule was half wrong about its own findings.** Requiring
  the name inside the cited lines reported eight failures, and four
  were its own fault -- `cmd_check` spans 262-309, so a citation to
  290-305 is inside it, and an annotation names the construct a
  citation sits in rather than repeating itself on every line of it.
  The rule that shipped is *appears at or before*: a construct is
  introduced before its body, so a name that first appears after the
  lines it annotates cannot be describing them. No parser, no
  threshold, three findings and none of them false.

  It is a weaker net on purpose. `flex.js:515 (`whiteSpace`)` pointed
  into `justifyOffsets` while `whiteSpace` sat 390 lines back, it
  passes this rule, and only a hand reading caught it. Two more like it
  turned up in review: `css.white-space` and `text.white-space.values`
  both cited `flex.js:73-80` and `:408`, the margin helpers and a font
  resolve, for a fact about `white-space`, with `flex.js:73` pinned
  green on a closing brace.

  367 of the newly readable members are pinned and have not been read
  by anyone. **The mechanical screens over them were reported clean and
  were not.** They had been run over a global set of `(path, line)`
  pairs, so a member two rows also cited was counted once and dropped
  from the population, which hid `ps2ui.c:1705` starting on a closing
  brace two lines before the function it names. Read off the records
  instead, 25 first lines are blank and 30 are punctuation only, and 20
  of those 30 are one cluster of list-API citations each naming the
  brace that closes the previous function. Those pins hold the text
  `}`, which is not unique in its file, so `--fix` can never move them:
  the drift is invisible and unrepairable at once. All of that is a
  filed row, not a claim of verification.

- **27 line numbers in the facts library were pointing at the wrong
  line, and nothing could see them.** `check-site-pages.py` pins a
  citation to the text at the line it names, but only recognised one
  whose path began with `packages/`, `runtime/`, `tools/`, `examples/`,
  `fonts/` or `docs/`. A file at the repository root matched none of
  them, so `README.md:428`, `CHANGELOG.md:44` and
  `.github/workflows/ci.yml:173` were prose as far as the checker was
  concerned: **51 line numbers over 41 citations in 22 facts files**,
  14 of the numbers to `README.md` and 22 across three workflows,
  unread since each was written. The two units are not
  interchangeable: a citation is one `path:N` match, a line number is
  one member of it, and `README.md:120,129,241` is one of the former
  and three of the latter.

  The prefix list is gone. `os.path.isfile` is the guard now, which is
  the honest one: a token is a citation when it names a file. The
  shape requirement that keeps ordinary prose out has two arms,
  because a repo-root file has no slash and `runtime/Makefile` has no
  extension, and requiring an extension of both silently unpinned 21
  `Makefile` citations the prefix list *had* been checking.

  **Nothing had drifted, which is not the same as nothing being
  wrong.** Every one of the 51 still names its original file at its
  original length, so the checker would have had nothing to report even
  if it had been reading them. What it found on first sight is that
  **27 of the 51, over 23 of the 41 citations, were wrong when they
  were taken**: seven land on a blank line and the rest on unrelated
  text. More than half. `CHANGELOG.md:44` for "the offset needs no
  format change" was the file's own note about when an entry is
  warranted; `:105` for `vramBudget` forwarding was the middle of an
  unrelated entry, cited from two different pages; `ci.yml:378` for the
  `check-blobs.sh` wrapper was the testcard self-test. All 27 are
  re-pointed and pinned.

  **Four more were page-level `repo:` links, pinned and green while
  naming the wrong CI step** — the same shape one layer up, and the
  reason a green pin is worth less than it looks: the pin protects a
  line from moving, not a citation from having been wrong when it was
  taken. **And one row's claim was stale rather than its number.**
  `theme.readme.absent` said README.md's "Supported CSS" list names no
  custom properties, no `var()` and no `@theme`; it names all three,
  and has since 0.7.0.

- **The checker counted one line more than every file had, and its
  range guard called a backwards range an overrun.** `file_lines` split
  on `\n` and kept the empty element a trailing newline leaves behind,
  so the bound every line number is checked against sat one past the
  last line. Two citations lived there: `text.js:183-188` over a
  187-line file and `docs/format-uib.md:466-479` over a 478-line one,
  both green, both pinned to an empty string that can never drift, both
  running to the end of their file and overshooting by one. Correcting
  them is what removed the only witnesses the phantom line had, so the
  count is now asserted directly against bytes the tool writes itself.

  The guard's complaint was wrong twice over. It said "448 lines" of a
  447-line `ci.yml`, and it said *past the end of the file* about
  `156-154`, a range re-pointed at a step that had moved and written
  backwards, which is true of neither number. One condition had folded
  three faults together and the message named only the last. It now
  says which of the three it is.

- **`ps2ui build` before `ps2ui fontgen` named a directory inside the
  npm package as the place your font metrics belong.** With no project
  manifest nothing passed a font flag, so `ps2ui-layout` fell back to a
  default resolved against its own install and printed
  `no font metrics at .../lib/node_modules/fonts/default.metrics.json`
  — a path the reader never chose and could not have created. Found by
  an assessor with no knowledge of this project installing from the
  registries onto a machine with no checkout.

  **Its advice could not work either**, and not only because nothing
  passed the flag: `--font-dir` is two fixed filenames with no `ttf`
  paths, and the baker rasterizes, so a bare directory cannot carry
  what the baker needs. Wiring it through was tried first and failed
  worse — the compile succeeded and the bake then refused on a family
  mismatch. The project resolves fonts once now, before either half
  runs, and names `ps2ui fontgen <regular.ttf> <bold.ttf>`, which
  writes the metrics *and* the manifest both halves read.

  Seeing this needed both halves installed, which is why it survived:
  with only the npm half present the baker's checkout fallback supplies
  `--fonts` and the build succeeds.

- **The build command `vendor-runtime --starter` printed could not be
  followed.** It said to put the blob beside the four files and then
  passed `UIB=build/ui.uib`; the Makefile's rule is `ui_uib.c: $(UIB)`,
  so doing what the sentence said gave
  `No rule to make target 'build/ui.uib'`. Correcting it to
  `UIB=ui.uib` was worse — `UIB ?= build/ui.uib` is where `ps2ui build`
  writes one, so that spelling breaks the in-place layout instead. One
  spelling cannot be right for two layouts, so the message now names
  none: a plain `make` for the default, `UIB=ui.uib` for a blob beside
  the files, and a note that the printed `docker run` mounts only that
  directory. `_gskit_lines()` has been held to the Makefile since the
  starter shipped; this line was the one piece of printed wiring that
  was not, which is how two opposite defects both passed. It has a test
  now, falsified four ways.

- **`--starter` was the answer to the console half and no page a
  stranger reads mentioned it.** Zero occurrences across the
  documentation site, while `runtime/integrating`'s table said the
  command took "one positional and one flag" and `--help` had listed
  two since the flag shipped. Fixed on four artefacts, each found only
  after the previous one: that page, `cli/ps2ui` which it names as
  canonical, `runtime/deploying` whose minimal example opens "Build
  inside a checkout", and `packages/baker/README.md` — the page every
  `pip install ophtml` reader lands on, which still ended its console
  section pointing at `runtime/sample/` on GitHub.

  `runtime/first-boot` says the opposite on purpose: it has no no-clone
  lane, because the channel-6 probe and the test card are the
  instruments each step is read against and nothing in the wheel
  produces either. **And its colour legend is not the starter's** —
  the starter paints navy `#000080` where the sample paints magenta,
  so reading one against the other turns a failed `ps2ui_screen_set`
  into "step 1 passed".

- **The Installation page did not mention that `pip install ophtml`
  fails on a current macOS or Debian box.** PEP 668's
  `externally-managed-environment` is now quoted with `venv` and
  `pipx`, and a *A TTF to start with* section names DejaVu, where each
  platform keeps it, and the two `export` lines the quickstart's first
  command needs and nothing on the site assigned. A `.ttc` collection
  loads but always yields face 0, so it writes a manifest declaring a
  bold face whose glyph and kerning tables are identical to the
  regular one, and nothing downstream says so.

- **The Changelog page restated a shipped release while calling it the
  open one.** Its first sentence has always read "The open <version>
  section of `CHANGELOG.md`, restated by category"; it was restating
  `## 0.6.0 — 2026-09-12`. It got worse while the row was filed: one
  release behind when the defect was written, two once the 0.8.0 notes
  landed, on the document whose whole job is publishing what changed.

  The version fence caught the *semantic* change rather than the text.
  `project/changelog.md:19` was pinned as meaning the last release and
  the rewrite makes the same line mean the tree, so re-pinning was a
  decision rather than a side effect: the split moved 11 release / 17
  tree to 10 / 18, exactly the one banner whose meaning changed.

- **A comma list was one citation instead of several, so
  `runtime/ps2ui.h:653,652,660,668,704,802,806` pinned 653 and left six
  line numbers unread.** 122 members across 69 citations in 13 files
  were invisible to the documentation drift checker, in three spellings:
  a bare comma, a comma with a space, and a range on a tail member,
  where `main.c:2646-2647, 2762-2764` matched only as far as `, 2762`
  and left `-2764` dangling outside the match.

  **It cost corrections rather than silence, which is the worse
  failure.** `--fix` relocated the first number, reported success and
  left the rest behind, so each pass looked finished and the row stayed
  wrong; one row was corrected three times in a single pull request.
  Each number is its own citation now, and relocation rewrites that
  member's token alone so its siblings keep their place and their
  spacing. One of the newly visible spans was already stale:
  `stats.readout.peaks` cited three lines of closing braces for a claim
  about a running max, which is at `main.c:2789-2792`.

- **`ps2ui check build/ui.uib` ended in a `UnicodeDecodeError` and a
  Python stack.** `check` takes a project file; the blob validator is
  the separate `ps2ui-check`, one hyphen away, and `--help` says only
  `usage: ps2ui check [-h] [project]`, so handing it a blob is an
  ordinary mistake. `project.load`'s docstring has always promised
  "Raises ProjectError, never a traceback", and the handler under it
  caught `json.JSONDecodeError` only — but `json.load` decodes before
  it parses, so a binary file never reaches the parser and went past
  the handler untouched.

  A file that is not UTF-8 text is now refused by name. When the first
  four bytes are `UIB1` the message says so and spells out the command
  that does take a blob, which was then run to confirm it works:
  `ps2ui-check build/ui.uib` prints `PASS: 63 checks`. Any other
  binary gets the two-key shape of a `ps2ui.json` and the same pointer.

- **`ps2ui serve --port <busy>` printed a bind traceback, and `--help`
  promised the opposite.** Refusing is the intended behaviour — a
  person who names a port means that port, which is why the default
  wanders and an explicit port does not — but it surfaced as
  `OSError: [Errno 98] Address already in use` out of
  `ThreadingHTTPServer`, which names neither the port nor the fact that
  the refusal was deliberate. It now says which port is busy and that
  a named one is not moved. The behaviour is unchanged: with 8080 held
  and no `--port`, the server still takes 8081.

  **The help text said the wandering was the flag's.** `default 8080,
  moving up when it is busy`, attached to `--port`, described what
  happens when you do not pass it. The sentence is the default's
  property now, and it was fixed in both parsers: `ps2ui.py` restates
  `serve`'s arguments rather than importing them, deliberately, so
  that `ps2ui build` loads no server code — and the copy a reader
  reaches through `ps2ui serve --help` was the one still promising the
  old sentence. A test compares the two help texts.

  **Both of `bind`'s refusals also escaped `serve.run`'s own
  handler**, which wrapped `build_server` alone. Under `ps2ui serve`
  the umbrella caught them and printed `ps2ui: `, against a
  Diagnostics page that has said `ps2ui serve: ports <a>-<b> are all
  busy` since it was written; under `python -m ps2ui_bake.serve`
  nothing caught them at all. Both now print `ps2ui serve: ` and exit
  1.

- **A stylesheet with three mistakes cost three builds.** Each pass
  reported one CSS error and stopped, so clearing a normal sheet was a
  build-fix-build loop: a gradient, a `:hover` and a `display: grid`
  took three runs, each naming one of them. A compile now reports every
  CSS error it finds, one `error: ` line each, sorted by line.

  The same argument the flex-direction refusal already made about its
  own list, applied one stage earlier: reporting the first of N turns a
  migration into a queue of single-line fixes.

  **What is collected and what still stops the parse.** A bad
  declaration is recorded and the compile carries on; a bad SELECTOR
  skips the rule it heads, which could not have applied to anything, so
  the declarations below it are still reached in the same pass. An
  unterminated block or comment still stops on the spot, because after
  one the reader no longer knows where it is in the file and everything
  it would report next is fiction. Only `css: ` messages are collected:
  a crash inside the property code stays a crash rather than becoming a
  confident and wrong statement about somebody's CSS.

- **A declaration was reported at the line its rule opens on.** A
  `background` physically on line 5 said line 1. In a two-line rule
  that is a near miss; in a fifteen-line rule it sends the reader to
  the wrong end of it. Every declaration now carries its own line,
  recorded per character as the rule body is read, which is what makes
  it survive a comment: the reader SKIPS comments, so counting newlines
  in the body would put every declaration under a three-line comment
  three lines too high.

- **`:hover` was answered with `unsupported selector syntax near ":"`.**
  True of the character and silent about the mistake: the reader wrote
  a state this target does not have, and no punctuation fixes that.
  The message names the one pseudo-class that exists, and says why
  there are no others — a pad-driven UI has no pointer. Both selector
  errors also carry a line number now; they were the only messages in
  the compiler without one.

- **`border-radius` costs a flat +8 records a box and nothing said so.**
  A square box is one record; a rounded one is a nine-cell patch. That
  is the number `ps2ui check` budgets against and the one a data-heavy
  screen runs out of, so a reader authoring forty rows should be able
  to find the price before paying it. Measured on a scratch project: a
  screen background, a box and a text child are 3 records square and
  11 rounded, and eight of those boxes are 17 and 81.

  **Two things do not scale with the box count**, and neither was
  written down either. A radius at half the shorter side is a pill,
  the middle row of cells has nowhere to go, and the cost is 5 rather
  than 8. And the corner mask is one texture per distinct *radius*,
  shared across boxes and independent of colour, because the patch key
  is geometry alone: a `(2r+3)` square in PSMT8, 19x19 for `8px`,
  charged 8 KiB of VRAM whatever the radius, that being the smallest
  page allocation.

  The CSS reference carries it beside the property. This is not an
  argument against rounded corners: it is the ordinary thing a console
  UI wants, and the price is knowable.

- **The previewer and `build/preview.png` are different sizes, and the
  self-test's line read as a denial of it.** `ps2ui serve` applies the
  blob's display aspect by default, so a 4:3 blob is 640x448 in the
  file and 597x448 on the page. Both are right and the difference is
  the pixel aspect a television applies — but the self-test forces
  `framebuffer` before comparing, and printed `ok - the frame is
  byte-identical to --preview`, which a reader diffing the browser
  against the file reads as a claim about the picture in front of
  them.

  The line names the frame now: `ok - the framebuffer frame is
  byte-identical to --preview`. The quickstart and the previewer page
  each gain a short paragraph naming both sizes and pointing at video
  modes, where the stretch is explained.

## 0.7.0 — 2026-09-17

`.uib` format **version 7**, unchanged from the release below.
Zero format moves have landed since 0.6.0, which is what a section
opened straight after a release should say: the release under it
shipped the format this tree still writes, so a blob baked here loads
under a 0.6.0 runtime and the other way round.

That count is the one number in this file that starts correct and
decays. It becomes one the moment a format move lands, and
`tools/check-versions.py` derives it from the section below rather than
reading it back, so the check fails the change that moves the format
without moving this line.

### Added

- **`ps2ui vendor-runtime --starter` — the four files that build to a
  console binary, instead of the two that do not.** An install gave a
  stranger `ps2ui.c`, `ps2ui.h`, three Makefile lines of prose and a
  link to `runtime/sample` on GitHub for a worked example — 2810 lines
  of bring-up instrumentation behind eighteen build flags, which is not
  a starting point and is not reachable offline. `--starter` writes a
  `main.c` that brings up gsKit, loads the blob, draws it and reads the
  pad, and a `Makefile` carrying the gsKit resolution, beside the
  runtime pair. `make NOPAD=1` builds with no IOP service at all and
  holds the baked focus: the build to boot first, because it answers
  *does this draw* without a controller in the question (F31).

  The starter's rules are the opposite of the runtime's on purpose.
  A drifted `ps2ui.c` stops the command, because a mixed pair compiles
  and misbehaves. A drifted `main.c` is left exactly where it is and
  reported, because being edited is what it is for.

  The three gsKit lines the bare command prints are now read out of the
  starter Makefile rather than restated, with the count asserted: they
  were prose in one file and build rules in another, and a second copy
  of a fact that moves when the ps2dev image moves is a copy that goes
  stale.

  **Compiled and linked on every push, not booted.** CI builds both
  variants in the ps2dev container from a venv install of a built
  wheel — not from the checkout, which would prove the toolchain can
  compile its own files and nothing about the artifact. The pad path
  has never been exercised by any test here, and `main.c`'s header says
  so rather than letting a green check imply otherwise.

  That header first claimed the file *"cannot stop linking"* in the run
  where the pad build did not link: `EE_LIBS` was copied from a sample
  that names no `libpad` symbol, so `-lpad` never came with it. The job
  caught it and the sentence about the job did not, because the
  sentence was written from what the job was meant to say. The
  incident is recorded in the header it was wrong in.

### Fixed

- **266 of the library's 1087 evidence citations pointed at the wrong
  lines, and nothing could see it.** A page's `repo:<path>#L<n>` link
  has been pinned and gated since #133: move the line and CI goes red.
  The `source` cell of a `_facts` row — `packages/layout/src/css.js:598-655`
  — is where the evidence for every claim lives, and it was checked by
  nothing, so it drifted in silence while the row still read `verified`.

  Found by taking `docs/releasing.md` step 5b, which says to re-measure
  every facts row whose source moved. 251 relocated on a unique match,
  15 needed a person, and one of those was a claim that had actually
  gone wrong: `focus.css.state` said a `:focus` rule on a non-focusable
  element "matches nothing and paints nothing", which this same release
  made untrue by adding the warning. Two more rows were still recording
  defects #134 had fixed, at status `verified`.

  **The check now covers both halves**, pinning and relocating a facts
  citation exactly as it does a page's. One sabotage is the defect that
  motivated it: inserting a line above `GEOMETRY_PROPS` — which is what
  the `:focus` work did — now goes red instead of silently repointing
  the row about the focus guard at a different set.

- **A `:focus` rule could bold a row that had been measured thin, and
  three other text properties it accepted did nothing at all.** The
  geometry guard refuses a `:focus` rule that changes `width`,
  `padding` or `font-size`, because both states share one baked layout.
  Four text properties sat outside it and each failed differently.

  `font-weight` **is now measured for.** It was honoured when drawing
  and ignored when measuring: `emitTextLines` took the weight from the
  focus style while the lines had been placed once, from the base. Bold
  glyphs are wider, so the focused row drew past its box — a 20px
  `Shadow of the Colossus` row boxed at 236px and drew 270px when
  focused, 34px of it outside. The anonymous text box now carries the
  heavier of the two weights, so the box is sized for bold and one
  baked layout holds both states. Bolding the focused row is the
  ordinary thing a console UI does, so the fix is to make it work
  rather than to refuse it.

  **And the cost of that is now said out loud**, because it is bigger
  than "a little slack at the end of the line". On wrapping text the
  unfocused state — the one on screen almost all the time — is wrapped
  at the bold face's break points, so it breaks differently, and at some
  widths it gains a line and the box grows taller in both states; in a
  column, everything below moves. Swept over one string at seven widths,
  the line count moves at 170px and 250px and holds at the other five,
  and the compiler warns at exactly those two, naming both counts.

  `letter-spacing`, `text-align` and `text-overflow` **are now compile
  errors under `:focus`**, with a message of their own rather than the
  geometry one — they ask for nothing impossible, they are simply never
  read on the focus side, so the declaration parsed, applied and
  vanished. No error, no warning, no effect.

- **A `:focus` rule on an element with no `focusable` attribute
  compiled to silence.** It can never apply, and a forgotten attribute
  looked exactly like a typo in the class name. `box.js` carried a
  warning for precisely this and **could not reach it**: it asked
  `focusDeclared && scope === null`, and those cannot both hold,
  because the rule is dropped upstream in `compoundMatches` — so
  nothing matches, so `focusDeclared` is false. The question is now
  asked in the match loop, where the failed rule is still in hand:
  re-testing with the focus requirement relaxed answers "would this
  have matched but for the attribute?". Keyed on the rule, so twenty
  `.panel` elements are one warning, and a rule naming a class the
  element does not carry stays silent.

- **Eight keyword-valued CSS properties accepted any string, and a typo
  bought you a different layout rather than an error.**
  `flex-direction`, `flex-wrap`, `justify-content`, `align-items`,
  `align-self`, `text-align`, `white-space` and `text-overflow` stored
  their value verbatim, and every consumer ends in a `default:` meaning
  "the initial value" — so `flex-direction: rows` laid out as a column
  and `text-align: centre` aligned left, both at exit 0. `display`,
  `overflow` and `border` already refused what they could not honour;
  these did not, and the difference was invisible because falling
  through looked like working.

  **Worse, `flex-direction: rows` also satisfied the required-direction
  check**, which asks whether a declaration exists and not whether its
  value parses — the one fence over this family, defeated by the same
  typo. The value is now validated before the declared flag is set.

  **The accepted sets are what the solver implements, not what CSS
  defines**, because accepting a real value with no branch behind it
  would recreate the bug one value over. So `justify-content:
  space-evenly`, `align-items: baseline`, `text-align: justify` and
  `white-space: pre` (with `pre-wrap`, `pre-line`, `break-spaces`) are
  errors here, each naming the layout it would silently have produced.
  A misspelling reads differently, because a typo and a missing feature
  are not the same problem.

  This can fail a build that used to compile. Every such build was
  already producing a layout its author did not write. All three
  example blobs are byte-identical across the change, and every keyword
  value in every stylesheet in the tree was already valid.

- **README's "Supported CSS" list was wrong in both directions
  (drift row D7, the CSS half).** It omitted `opacity`, `min-*`/`max-*`,
  `align-self`, the `flex` shorthand, `row-gap`/`column-gap` and
  `:root`/`var()`/`@theme`; it said "flat colors" without naming the
  eight that parse, so a sheet written from it could use `orange` and
  fail to compile; and it stated the `:focus` geometry guard flatly
  when four text properties sit outside it — `font-weight`, which
  changes the drawn face while the line was measured at the base
  weight, and `letter-spacing`, `text-align` and `text-overflow`, which
  are accepted and then discarded. That defect is still open; the
  README now states the exception rather than overstating the guard.

- **Every `ps2ui` build under macOS's temporary directory failed, on a
  path arithmetic that only a symlink of unequal depth can break.** The
  project root was `abspath`'d and then `chdir`'d to; `chdir` resolves
  symlinks and `abspath` does not, so every path handed to the layout
  compiler counted its `../` from one spelling of the root and walked
  them from another. macOS hands out `/var/folders/...` and `/var` is a
  symlink to `/private/var`, one component deeper, so the count came up
  short and an absolute `--fonts` manifest arrived as
  `../../../../../../Users/you/repo/fonts/fonts.json` — ENOENT,
  reported as a fonts.json that "cannot be read". The root is now
  resolved, because it is also the working directory.

  **The obvious probe could not have found it.** A symlinked `TMPDIR`
  was tried on Linux and all 285 tests passed, and that was read as
  "the report has some other cause" — but `/tmp/link -> /tmp/real` is
  the same depth from either side, so the miscount is zero by
  construction. The symlink has to *change* the depth. The macOS job
  added in 0.7.0 printed the failure text, three tests rather than the
  six reported, and it reproduced on Linux the same day.

- **The third of CONTRIBUTING's three commands could not finish on any
  Mac.** `runtime/sample/main.c` reads the EE cycle counter with MIPS
  inline asm, guarded on a build flag and not on the target, so the
  host syntax check handed `mfc0 %0, $9` to the host compiler. The
  Makefile's `HOST_NOASM` keeps clang's integrated assembler from
  parsing it — but that is the assembler, not the frontend, which still
  reads the operand: on arm64 a `u32` in an `"=r"` slot is a 32-bit
  value in a 64-bit register, so Apple clang raised
  `-Wasm-operand-widths` and `-Werror` made it fatal. Five sample
  variants compiled and the sixth stopped the build. The asm is now
  guarded on `__mips__` with a host definition beside it, so every
  caller stays compiled and warning-checked and no flag suppresses a
  correct diagnostic; `hw.yml` compiles the instruction for real under
  the EE toolchain.

  Reproduced on Linux by cross-targeting — `clang
  --target=aarch64-linux-gnu` prints the runner's diagnostic word for
  word, and the same command on x86_64 exits 0, which is why the clang
  arm added to `ci.yml` never saw it.

- **`row-reverse` and `column-reverse` packed from the wrong end.**
  `flex-direction: row-reverse` flips the main axis — main-start
  becomes the right edge, so `justify-content: flex-start` packs
  against the right. The solver reversed the item order and left the
  packing end alone, so a reversed container packed from the left with
  its items backwards (B4).

  It read as correct because three of the five justifications are
  symmetric: `center`, `space-between` and `space-around` distribute
  the same from either end, so only `flex-start` and `flex-end` were
  ever wrong. Nothing in the repository used `-reverse` at all — no
  example, no fixture, no test — which is why three pens agreed on it.

  **The solver change is byte-neutral**: all three example blobs are
  identical across it, verified by building the head solver against the
  unmodified stylesheets. `channel6`'s blob does move in this release,
  by the `border-radius` line the B6 warning found — see below.

- **`flex-wrap: wrap-reverse` was accepted and then ignored.** The
  value was stored unvalidated and only ever compared against
  `'wrap'`, so such a container did not wrap and did not stack its
  lines in reverse. It now does both.

- **A percentage with nothing to resolve against is now named.** A
  `%` size needs a definite containing size; a shrink-to-fit row has
  none while its children are being measured, so `width: 50%` there
  resolved to null and every caller downstream read null as `auto`.
  The author wrote a constraint, got a different layout, and got
  nothing connecting the two. The compiler now says so (B7).

  It warns rather than implementing CSS's fallbacks, which are
  per-property and subtle; getting them subtly wrong would replace a
  visible silence with an invisible disagreement.

- **A rounded box that clips is now named.** The GS scissor is a
  rectangle, so `overflow: hidden` clips square however round the box
  is — the corners the author rounded are exactly where children run
  out to the straight edge. Rounded clipping needs stencil or alpha
  work the runtime does not have (B6 stays open); this is the honest
  half, said at compile time.

  It found one in this repository's own conformance card, where
  `.scissor` set both. The decorative radius is gone and
  `examples/channel6/screenshots/probe.png` regenerates with it.

- **`ps2ui dev` accepted `--strict` and `--min-font-size` and read
  neither.** `ps2ui-dev` stored them as `options.strict` and
  `options.minFontSize`; the compiler takes lint overrides from
  `options.lint` alone, so `ps2ui dev` on opl-env (`strict`,
  `minFontSize: 11`) printed 44 warnings at the 14px floor and exited
  0 where `ps2ui build` printed none. The floor now goes where
  `ps2ui-layout` puts it, and `--strict` fails the build before the
  bake, exit 1 under `--once`. Two tests hold it: one spawns the bin on
  a page whose only warning is a font-size one, the other runs
  `ps2ui dev` and `ps2ui build` over opl-env and compares the warning
  counts.

- **CONTRIBUTING's Setup section said nothing to a Mac.** Both macOS
  Pillow wheels compile Raqm in and neither bundles fribidi, which
  Pillow `dlopen`s at run time — so a Mac without it reports no Raqm,
  `ps2ui fontgen` refuses, and the two tests that need the layout
  engine skip. That was written down in `fontgen.py` and in the
  tutorial and nowhere a contributor reads before running the suite.
  Setup now names it, asks for the feature rather than the install, and
  the macOS job runs the same step — which also measures, for the first
  time, whether fribidi alone is enough. `_raqm_remedy()` says
  "probably" because nobody had a Mac to try it on.

## 0.6.0 — 2026-09-12

### Added

- **`ps2ui_offset_set(ctx, dx, dy)` — the runtime can finally change
  *where* something is drawn.** Focus, theme, slot text, textures,
  visibility, screen and the list window all change *what* is drawn;
  nothing changed *where*, so a sliding panel, a carousel, a parallax
  layer and a scrolling region were unreachable, and a UI whose sidebar
  expands had to bake both end states as separate screens with no
  motion between them. Pulled by rebuilding a real shell against the
  published 0.5.0 packages (F27).

  **No format change.** It is a draw-time transform over commands that
  already exist, so it works on every blob this toolchain has ever
  baked and the `.uib` v7 pledge is untouched.

  - The screen edge does not move with it: the canvas rect the scissor
    stack is seeded with is the display, not a UI element, so content
    pushed far enough is clipped rather than drawn off.
  - Geometry queries stay in UI coordinates, so an app's own hit-testing
    keeps working; `ps2ui_offset_get` is there for callers that draw
    their own art beside the UI.
  - Out of int16 returns `PS2UI_ERR_RANGE` rather than truncating — a
    wrapped offset draws a correct-looking frame in the wrong place.
  - `preview.render(..., offset=)` moved with it in the same commit,
    because `ps2ui serve --selftest` asserts the served frame is
    byte-identical to `--preview` and an offset one pen applies and the
    other does not turns that into a comparison of two pictures.

  Two implementations were wrong first and both were caught by fences
  rather than by reading. In C, the offset was applied at the three
  sites that read `c->x` and missed the two that derive a glyph position
  from a slot; it now lands inside `draw_texquad`, at the sink all three
  texture paths pass through. In Python, the texquad clip was measured
  against the quad's blob-space rect while the clip itself had already
  been offset, so every textured quad's source slid by the offset
  *inside* the quad — transparent padding in, background showing through
  where the panel was. Both read correctly at offset `(0, 0)`, which is
  every frame either pen had ever drawn.

### Fixed

- **`ps2ui-fontgen`'s Raqm remedy stated a platform rule, the rule was
  false, and the real cause is a cheaper fix.** It told every macOS
  reader *"pip's macOS wheels are built without it"* and routed them
  through a Pillow source build. Both Pillow 12.3.0 macOS wheels were
  opened and compared: each has Raqm **compiled into `_imagingft`** —
  the linker breadcrumb `src/thirdparty/raqm/raqm.o` is in the binary —
  neither bundles `libraqm` or `fribidi`, and both carry
  `libfribidi.dylib` / `libfribidi.so.0` as `dlopen` candidates.

  **The wheels are identical. What varies is whether the machine has
  fribidi**, which Pillow loads at run time: a Mac with Homebrew
  history usually does, a clean `macos-14` runner does not. That is the
  entire reported "architectural" split, and it is not architectural.

  So the message now reports what it detected — Pillow version,
  platform, machine — asks Pillow about `fribidi` separately, and when
  that is the missing piece leads with `brew install fribidi` and no
  rebuild at all, keeping the source build as the fallback. It states
  no rule about anybody's wheels, on any branch; the previous text also
  handed Windows readers a fact about manylinux wheels as their remedy.

  This blocks a release rather than a doc pass because the text ships
  **inside the wheel**: `_raqm_remedy()` is what a stranger reads when
  `pip install ophtml` then `ps2ui fontgen` refuses. The tutorial's
  section-1 blockquote and `registry.yml`'s macos-plain job are
  corrected with it — the job now reports `raqm` and `fribidi` side by
  side, so if it ever flips, its output says which of the two moved.

- **`vendor-runtime` stopped one step short and cited a file the reader
  cannot open.** It handed over `ps2ui.c` and `ps2ui.h` and then said
  *"docs/deploying.md is the path onto a console"* — a repo path,
  printed by an installed package, to somebody who by definition did not
  clone. That is the defect F26 fixed one layer down, recurring one
  layer up: the tree telling an installed user to go look at the tree.
  The message now names the constraint (the PS2 is a MIPS target and
  never the build host, so a cross-toolchain is required), gives the
  `ghcr.io/ps2dev/ps2dev` one-liner, and links ps2dev and deploying.md
  as absolute URLs.
- **The PyPI page never mentioned the console half, or `vendor-runtime`.**
  It listed four commands as of 0.4.0, said nothing about ps2dev, gsKit
  or cross-compiling, and ended by pointing at `docs/format-uib.md` "at
  the repository root" — the third repo-relative reference on a registry
  page, after the two fixed before 0.3.0. It now carries a *Getting it
  onto a console* section and no repo-relative paths at all.
- **Rule 10 reads the drift anchor and the release tag, not just the
  drift count.** "zero moves ... since 0.4.0" passed on a tree whose
  newest released section was 0.5.0, and `tagged \`v0.5.0\`` could be
  changed to `v9.9.9` with nothing objecting. Three consecutive step-9
  commits moved that version by hand with nothing behind it. Which tag
  the note should name depends on the state, the way rule 5 picks its
  heading shape: a prerelease tree describes the last release, a release
  tree describes the version being cut. Falsified in both, four
  sabotages, all caught (#112, #116, #117).
- The same boundary is now stated where a reader meets it:
  `docs/tutorial-uc3.md` section 8, which is the first step in that
  document not reachable from `pip install ophtml`, and
  `docs/deploying.md` section 2, whose build command assumes a checkout
  and now says what the installed path is instead.

- **`ps2ui check` is given the settings `ps2ui build` was given.** One
  project, two commands that disagreed about the same numbers.
  `vramBudget` reached `ps2ui-bake` and was dropped on the way to the
  checker, so at any budget but the default the build passed at the
  declared figure and the check failed at the computed one —
  `textures 491520 B of 1212416 B budget` against
  `not ok 66 - VRAM 480 KiB within budget -272 KiB`, on one blob.
  `check.py` had accepted `--vram-budget` since it was written; nothing
  passed it. `strict` was the same drop one flag over, found in review:
  the checker takes five options, two have a project key, and this
  forwarded one — so a project declaring `"strict": true`, as the
  tutorial's own does, got strictness in the layout compiler and could
  not get it from the checker.

  Overriding the budget is ordinary rather than exotic, which is why
  this mattered: the default reserves a *third* framebuffer for a Z
  buffer this tree's sample never allocates (`gs->ZBuffering =
  GS_SETTING_OFF`, and gsKit only allocates Z when it is on).
  Reclaiming it is what makes a canvas wide enough for square pixels at
  16:9 fit in VRAM — 796x448 needs three 32-bit buffers that do not fit
  in 4 MB at all, and two leave 1,212,416 B, 61% more texture budget
  than the 640x448 default gives.

  Fenced by a matrix rather than by more hand-written tests: every
  `project.DEFAULTS` key whose kebab-cased flag the checker's own
  parser accepts must appear in the argv the front door builds. It is
  derived from the settings dict, the parser and the builder, so it
  fails when a sixth option is added and not forwarded rather than when
  somebody remembers to test it — which is how `strict` was found. This
  is the fourth hand-maintained settings-to-argv list in the tree and
  three of the four already carried a comment about a bug of this
  shape.
- **A VRAM budget that cannot exist says so, instead of blaming the
  textures.** Above some canvas width three framebuffers do not fit in
  VRAM at all and `default_budget` returns a negative number, after
  which everything downstream read as though the art were at fault: an
  *empty* blob failed, and `textures 0 B of -278528 B budget` named the
  one thing that was not the problem, while the line directly above it
  asserted 4,472,832 B of framebuffers against the 4,194,304 B the same
  module defines as total VRAM without ever saying those two are
  incompatible. A reader had to work backwards through `vram.py` to
  learn that the default was structurally unavailable at their canvas
  rather than that their covers were too big.

  The report now names both sides of that comparison where the numbers
  are, and the way out with the figure it is worth: with ZBuffering off
  the console holds two buffers rather than three, which at 796x448
  leaves 1,212,416 B. The percentage is dropped rather than printed
  against a negative budget, where it read `49152000%`.

  Only for an *inherited* default — somebody who passed
  `--vram-budget` has already made the decision the diagnostic argues
  for. The verdict is deliberately unchanged: an empty blob at an
  impossible canvas is still a failure, because it is one. What was
  missing was the explanation, not a kinder result.

  796x448 is not hypothetical; it is the canvas that gives square
  pixels at 16:9 on a 448-line frame, and reaching it is what turned
  `--vram-budget` from decorative into load-bearing.

  Both surfaces print it, which they did not at first: `check_vram`
  unpacked the report into `_lines` and discarded it, so `ps2ui build`
  explained a negative budget and `ps2ui-check blob.uib` — the bare
  invocation the README, the tutorial and `vendor-runtime`'s own
  closing message all teach — printed `VRAM 24 KiB within budget
  -272 KiB` alone, which does not read as a diagnosis. The diagnostic
  is one function both call, so they agree by construction rather than
  by both remembering, and the failing label now says which kind of
  failure it is for anyone grepping `not ok`.

  And the advice has a ceiling of its own. "with ZBuffering off … which
  leaves N B" did not check its sign, so above a *higher* width — 1153
  columns at 448 lines, where two framebuffers stop fitting — it
  offered a negative number as the budget to declare, which is the
  sentence this diagnostic exists to delete reappearing inside its
  replacement. Past that width no budget helps and the message says so
  instead.

`.uib` format **version 7**, unchanged from the release below.
Zero format moves have landed since 0.5.0, which is what a section
opened straight after a release should say: the release under it
shipped the format this tree still writes, so a blob baked here loads
under a 0.5.0 runtime and the other way round.

That count is the one number in this file that starts correct and
decays. It becomes one the moment a format move lands, and
`tools/check-versions.py` derives it from the section below rather than
reading it back, so the check fails the change that moves the format
without moving this line.

## 0.5.0 — 2026-09-06

### Added
- **`ps2ui vendor-runtime`, and the C runtime inside the wheel.**
  `pip install ophtml` gave you the whole authoring path and then the
  README told you to *"drop `runtime/ps2ui.c` into your ps2sdk/gsKit
  project"* — a repo path, in a package that shipped neither file, so
  the console half needed a clone. It no longer does:
  `ps2ui vendor-runtime src/` writes both files out of the package you
  installed, which means the runtime you compile is the one matching the
  baker that wrote your blob. Existing files are not overwritten without
  `--force`. Phase 4's exit gate says *"without cloning the repo"* and
  had been contradicting the README since it was written (F26).

### Changed
- **Rule 10 counts a version only where it is not extended into a longer
  one.** It used plain substring containment, so `0.4.0` was satisfied by
  `0.4.0.dev0` — during the 0.4.0 cut the stale prerelease note entered
  the release branch green while its prose still said *"those give you
  0.3.0"*, and it was rewritten because a person read it rather than
  because the check objected. The purpose was "the note describes this
  tree"; the coverage was "these characters appear somewhere". The guard
  admits `v0.4.0`, since a `v` is not a digit, and rejects `0.4.0` read
  out of `10.4.0`. Falsified in all four states, because step 9 restores
  the prerelease one minutes after step 8 leaves it. The failure message
  names the baker and npm versions separately now: in a release state
  they are the same string, and it used to print the same line twice
  with nothing to tell them apart (#113).
- **`docs/releasing.md` carries what the 0.4.0 cut cost.** Step 5: the
  literal the checker matches must not wrap across a line break, and rule
  10 asks only for version facts, so prose it does not read can be
  dropped silently — 0.4.0's note lost its stability-pledge clause that
  way. Step 8: npm may answer **202** rather than 200 and take minutes to
  appear, `~/.npm/_logs` is what separates a publish that never ran from
  one still propagating, a warm pip cache serves a stale index and
  reports the *old* version so the resolve wants `--no-cache-dir`, and
  the per-version JSON endpoints 404 for versions that exist (#113).

`.uib` format **version 7**, unchanged from the release below.
Zero format moves have landed since 0.4.0, which is what a section
opened straight after a release should say: the release under it
shipped the format this tree still writes, so a blob baked here loads
under a 0.4.0 runtime and the other way round.

That count is the one number in this file that starts correct and
decays. It becomes one the moment a format move lands, and
`tools/check-versions.py` derives it from the section below rather than
reading it back, so the check fails the change that moves the format
without moving this line.

## 0.4.0 — 2026-09-06

`.uib` format **version 7**, unchanged from the release below.
Zero format moves have landed since 0.3.0, which is what a section
opened straight after a release should say: the release under it
shipped the format this tree still writes, so a blob baked here loads
under a 0.3.0 runtime and the other way round.

That count is the one number in this file that starts correct and
decays. It becomes one the moment a format move lands, and
`tools/check-versions.py` derives it from the section below rather than
reading it back, so the check fails the change that moves the format
without moving this line.

### Added
- **The `.uib` format stability pledge, made at v7.** v7 is the last
  incompatible layout: additions go in feature bits rather than strides,
  so a blob this tree writes will be read by every runtime that comes
  after it. Enforced by `tools/check-format-frozen.py` in CI rather than
  announced — it freezes all eleven structs' formats and sizes, `MAGIC`,
  and the value of each assigned feature bit, and refuses a twelfth that
  is not in the record. The *set* of bits is deliberately left open,
  because that is the growth path the pledge points at. It does not
  forbid a v8; it makes one a decision somebody signed.
  Deferred twice before this, from post-v5 and post-v6, both times
  because a break landed inside the phase meant to end them.
- `fonts/vendor/` carries the default DejaVu faces under their own
  licence, so a checkout builds without a system font. They sit **last**
  in `fonts.json`, so a machine's own DejaVu still wins wherever there
  is one; the vendored pair is a floor, not a preference. Coherence
  rather than convenience: `default.metrics.json` was already committed
  and DejaVu-derived, so the tree shipped the *metrics* for its default
  face without the face, and metrics alone cannot rasterize an atlas.
  Two tests fence it — the vendored face must stay last, and it must
  regenerate the committed metrics byte for byte, so a swapped TTF
  fails rather than drifting advances against glyphs.

### Changed
- `ps2ui-fontgen`'s Raqm refusal prints the remedy for the platform it
  is running on. It used to say "install a Pillow wheel built with
  Raqm (pip's manylinux wheels are)", which is true and useless to the
  reader most likely to see it: pip's macOS wheels are precisely the
  ones that are not. The macOS branch names `brew install libraqm` and
  a source build of Pillow **alone** — `--no-binary pillow`, never
  `--no-binary :all:`, which scopes the build to the whole dependency
  graph and spends tens of minutes bootstrapping CMake. Both branches
  end on the same point: a clean build is not proof, because Pillow
  builds and exits 0 without libraqm and simply omits the feature.
- `fonts/regen.sh` reads `fonts.json` instead of carrying its own copy
  of the candidate list, so the metrics are regenerated from the same
  file the build rasterizes.
- `tools/check-tutorial.py` takes `--from-registry`, which skips the
  shims so the tutorial runs against `pip install ophtml` and
  `npm install -g @ophtml/layout` rather than against the checkout.
  Unknown arguments are now refused rather than ignored: the flag
  selects which of two *subjects* the run is about, and a typo used to
  quietly pick the other one and print the same green line.

**Not listed:** changes to `.github/workflows/`, which are not shipped
to anyone. `registry.yml` is new in this cycle and runs the tutorial
against the registries weekly; it is described in `docs/PLAN.md` under
Phase 4 rather than here. Said out loud because the convention is
otherwise indistinguishable from an omission.

### Fixed
- `load_font_manifest` expands `~`. `os.path.isabs("~/Library/Fonts/
  DejaVuSans.ttf")` is False, so a home-relative candidate was joined
  to the manifest's own directory and could never match — silently,
  since a candidate that does not exist is just the next one tried.
  That is where macOS puts a font a person installs for themselves, so
  the one spelling a Mac reader would reach for was the one spelling
  that could not work.
- `fonts.json` gains `/usr/local/share/fonts` (Intel Homebrew) and
  `~/Library/Fonts` (per-user installs, and where a font cask lands).
- `make -C runtime syntax-check` passes under clang. `-S` makes clang
  parse the sample's MIPS inline asm with its integrated assembler and
  reject `mfc0` on an x86 host; GCC emits the asm text and stops.
  Probed `-fno-integrated-as` rather than `-fsyntax-only`, which would
  have traded a compiler nobody ran for the `-Wunused-function` class
  that only appears during code generation. Every runner here is Linux,
  so this had been broken for the target's whole life and CI could not
  see it.
- The baker suite skips rather than errors on a machine without the
  fonts. It reported 22 errors across seven classes, then 17 failures
  and 2 errors in a second set, on any machine lacking DejaVu at one of
  two hardcoded Linux paths — a stranger's first `unittest discover`,
  after doing everything the tutorial asked. `PS2UI_REQUIRE_FONTS=1`
  turns those skips back into failures where the fonts are installed on
  purpose.

## 0.3.0 — 2026-09-04

`.uib` format **version 7**. v3 through v6 files are rejected; re-bake.
Four format moves have landed since 0.2.0 — v4 display aspect, v5
kerning, v6 texture kinds, v7 the tint table — so a blob baked against
that release will not load.

That count rests on one thing nothing here can check. "0.2.0 shipped
format v3" is read out of the 0.2.0 section below, and there is no
0.2.0 tag and no published artifact to hold it to — so the four moves
and their enumeration are *self-consistent* rather than *measured*.
That is what "0.2.0 named nothing" means, and it is stated rather than
left for a reader to assume the arithmetic was verified end to end.

**This is the first tagged release this repository has ever had.**
There is no 0.2.0 tag and there never was one — 0.2.0 was a number in
two manifests and nothing else — so `v0.3.0` is the first version of
this toolchain anyone can name and get the same bytes back twice.

Both packages carried a prerelease until that tag existed: `0.3.0.dev0`
for `ophtml` on PyPI, `0.3.0-dev.0` for `@ophtml/layout` on npm. What
that bought is written down in [docs/releasing.md](docs/releasing.md),
and it was less than it sounds. npm: a range like `^0.3.0` will not
match a prerelease, but `npm install` resolves the `latest` dist-tag
and `npm publish` sets `latest` whatever the version says, so
`@ophtml/layout` carried `publishConfig.tag = "next"`. This release
drops it, because a release pinned to a side channel is one
`npm install @ophtml/layout` cannot find. pip has no equivalent and
that gap was real: a prerelease is excluded from a specifier unless it
is requested **or no stable version exists**, and for a first upload
none would — so a plain `pip install ophtml` would have resolved
`0.3.0.dev0` and the marker would have bought nothing at all. That is
why the first PyPI upload is a real release rather than a `.dev` build
uploaded to reserve the name.

**Tagged and published.** `v0.3.0` is in git and both packages are on
their registries: `ophtml` on PyPI and `@ophtml/layout` on npm, the
latter on the `latest` dist-tag. Phase 4's exit gate is a separate claim
and is **not** met: it asks that a stranger with npm, pip and a TTF
reproduce the memcard example — and its hardware screenshot — without
cloning this repository, and the first attempt from an install failed.
On macOS, pip's Pillow wheel ships no Raqm layout engine, so
`ps2ui fontgen` correctly refuses to write a metrics file it cannot
kern, and the tutorial stops at its first command. Uploading was
necessary for the gate and is not sufficient for it.

These numbers used to drift because nothing read them: the baker
shipped `__version__ = "0.1.0"` beside `version = "0.2.0"` in its own
`pyproject.toml`, and this section said "format version 5" through two
further format breaks. `pyproject.toml` now derives its version from
`__init__.py` instead of restating it, and `tools/check-versions.py`
reads the package versions, `PS2UI_VERSION`, `uib.VERSION`, the
paragraph above, `docs/format-uib.md`, `docs/PLAN.md`'s format history
and the README's Quick start note against each other on every push.

### Breaking — authoring

- **`flex-direction` is now required on any container laying out two or
  more children.** Omitting it is a compile error listing every
  offending container with its line. Containers with one child or none
  are unaffected.

  **Migrating:** compile once and add `flex-direction: row` or
  `column` to each container the error names. If your document was
  written against a ps2ui release, it relied on the old implicit
  `column`, so `column` restores exactly what you had — adding it to
  both shipped examples left their previews *and* their `.uib` files
  byte-identical.

  Why: the implicit default was `column`, undocumented, where CSS's
  initial value is `row`. Switching to `row` would have silently
  relaid out every existing document; keeping `column` would teach a
  permanent exception to CSS. Requiring the answer is the only version
  with no silent victims.

  No format change. Existing `.uib` blobs are unaffected; only source
  documents need edits.

### Breaking — runtime

- **`ps2ui_load` takes an arena.** The context no longer carries
  fixed-size tables; it points into caller memory sized from the blob
  by `ps2ui_arena_size(data, size)`, which reads the header only and
  returns 0 when the blob is not worth loading at all. The arena must
  be `PS2UI_ARENA_ALIGN`-aligned and must outlive every render, not
  just the load, because nothing is copied — a blob that fails
  validation never touches it.

  **Migrating:** call `ps2ui_arena_size` first and hand `ps2ui_load`
  the buffer. `PS2UI_ERR_ARENA` is the new failure for one that is too
  small.

  Why it matters: the fixed tables charged roughly 36 KiB to every
  blob, a two-slot overlay included. The six-screen UC-3 environment
  asks for 7,319 bytes.

- **Texture entries grew 16 → 20 bytes (`.uib` v6).** The `pad` byte at
  offset 1 became `kind` and a `name_off` was added, which is what
  makes **streamed textures** expressible: an entry carrying geometry
  and a VRAM reservation but no texel data, pointed at the app's own
  buffer on the console by `ps2ui_tex_set`. Cover art off a disc, an
  HDD or a network cannot be baked, because nothing at bake time knows
  what it is.

  A v5 reader would have walked the texture table at the wrong stride,
  so this is a version bump rather than a feature bit alone. Feature
  bit 3 additionally says the blob declares a streamed texture, so a
  reader that cannot fill one refuses the file instead of drawing an
  empty slot.

  **Migrating:** re-bake. Every writer before v6 wrote zero in the byte
  that became `kind`, which is `PS2UI_TEXKIND_BAKED` — the meaning the
  zeros already had.

- **Commands and slots hold tint indices, not colours (`.uib` v7).**
  Where they carried rgba bytes they carry a u16 index into a **tint
  table**: `n_theme × n_tint` entries, theme-major, so one theme's
  colours are contiguous and selecting a theme is a pointer add rather
  than a strided walk. `ps2ui_theme_set` moves which row is live, with
  no `GSGLOBAL` and no upload — it is the cheap half of theming, beside
  `ps2ui_clut_set` for the palettes.

  The command entry did not change size (four colour bytes became two
  indices; the two that freed went into `tint_focus`, inside padding
  that already existed). The slot entry shrank, 32 → 28. Neither the
  stride nor the meaning of a field survives a v6 reader, which is
  exactly the case a version bump exists for.

  **Migrating:** re-bake. A one-theme blob draws what v6 drew.
  `PS2UI_FEAT_ROLE_TINTS` gates more than one row: it says the indices
  are keyed on the authored *declaration* rather than the resolved
  colour, and `ps2ui_load` refuses `n_theme > 1` without it, because
  two declarations that happen to share a colour would otherwise
  collapse into one entry no theme could tell apart.

- **`PS2UI_MAX_TEXTURES`, `PS2UI_MAX_SLOTS` and `PS2UI_MAX_SCREENS` are
  deleted.** A UI is no longer limited to 32 textures, 16 slots or 8
  screens. The v6 arena already sizes the context from the blob, and
  once it did those constants bounded nothing the blob's own size did
  not already bound — every table is checked as
  `off + n * sizeof(entry) <= size` on the way in.

  **Migrating:** nothing to do unless you referenced the constants.
  Code that read them (to size a buffer, or to assert a count) will no
  longer compile, which is the intended outcome — the number it wanted
  is the arena figure `ps2ui-bake` and `ps2ui-check` print.
  `PS2UI_MAX_SCISSOR_DEPTH` stays; it is a real stack in
  `ps2ui_render`, not a validation limit.

  `PS2UI_ERR_TOO_MANY` keeps its number and changes meaning: it now
  says the arena this blob demands does not fit the target's address
  space, not that a count passed a threshold ps2ui.h picked. A blob
  with zero screens returns `PS2UI_ERR_BOUNDS` rather than
  `PS2UI_ERR_TOO_MANY`.

  Why it matters: the UC-3 scoping fixture — a five-screen OPL-class
  environment — measures 121 slots and could not be baked at all
  without hand-editing a vendored header. It now bakes on a stock
  checkout and asks for roughly 8 KiB of arena — the measured figure
  lives in `fixtures/opl-scope/README.md`, where `figures.py` now reads
  it back out of the blob — against roughly 36 KiB that the
  fixed-maxima context charged every blob including a two-slot
  overlay.

### Added
- **Compositing two screens in one frame is a contract**, not an
  accident. `ps2ui_render` never clears — stated as a guarantee on the
  function, in the README with a worked frame loop, and in
  `format-uib.md` — so `screen_set` + `render` twice in a frame draws
  the second over the first. That is the dialog and modal technique,
  with no format flag and no new API: an overlay screen is an ordinary
  screen with a translucent scrim.

  Input follows the **last** `screen_set`, so an overlay drawn last
  owns the D-pad and dismissing it is one call back, restoring the
  focus the user left on the base. Visibility resolves in the current
  screen, so an overlay cannot reach into the base by naming one of
  its nodes.

  Two traps, documented and fenced: `ctx->stats` describes one render
  and is reset at the top of every call, so a composited frame ends
  holding the overlay's counters; and `gsKit_TexManager_nextFrame`
  belongs once per frame after the flip, not between the two renders,
  or an open dialog re-uploads the base's atlases every frame. The
  host stub now counts frame clears and residency ageing ticks, so a
  render that takes over either fails by name rather than silently —
  the primitive count notices neither.

  There is deliberately no `ps2ui_overlay_push`. The one thing it
  would buy is a dialog drawn over a base that still receives input,
  and nothing has asked for that.
- **Kerning** — `ps2ui-fontgen` measures pairs out of the face (with
  ligature substitution disabled, so a ligature's width is never
  mistaken for a kern) and every pen applies them: layout's
  `Font.layout`, the baker's `_flatten_text`, and the runtime's
  `render_slots`. Pairs reach the console pre-resolved to pixels at
  each font's size, in a per-font table sorted for binary search, so a
  frame costs one lookup per glyph and no arithmetic. Feature bit 1;
  the font entry grew 16 → 24 bytes, which is what forces v5.
- **Widescreen** — anamorphic 16:9 authoring, `--mode ntsc16x9`, the
  display aspect recorded in the header, and `ps2ui_pixel_aspect_x1000`
  so a mismatch is detectable rather than merely ugly (`.uib` v4).
- **Lists** — `data-repeat` template expansion at build time plus a
  runtime window over more items than fit: `ps2ui_list_init`,
  `_move`, `_select`, `_set_count`, `_item_at`, `_selected_row`,
  `_apply_visibility`.
- **Runtime visibility** — `ps2ui_visible_set` / `_get` / `_reset`,
  so an app can hide a row it has no data for instead of blanking
  every slot in it and leaving the panel drawn.
- **`ps2ui-check`** — a standalone `.uib` validator (TAP output) that
  reads a blob the way the loader does and reports what would go
  wrong on console: table caps, VRAM budget, scissor balance and
  nesting depth, glyph and kern table sortedness, feature bits that
  do not match the tables they describe.
- `fonts/regen.sh` regenerates the committed metrics in one command.

### Changed
- `arena_compute` accumulates the carve in 64 bits and refuses it
  before narrowing. Counts and slot capacity are all `uint16`, so a
  well-formed header can legally demand 65535 x 65536 bytes of slot
  text; that total wraps a 32-bit `size_t`, which is what the EE has,
  and a wrapped total carves a small arena for a huge blob. The
  ceilings used to make this unreachable as a side effect.
  `make -C runtime test-narrow` compiles the runtime at a 32-bit
  address width and proves both halves: the oversized blob is refused,
  and an ordinary one still loads.
- The bake's table line prints counts instead of fractions
  (`15 slots`, not `15/16 slots`). A fraction of 65535 is a number
  with a decorative second half; the figure that constrains a UI is
  the arena, printed on its own line.
- The baker drops draw records that cannot produce a pixel (geometry
  fully outside its clip), shrinking the command list on exactly the
  data-heavy screens where it matters.
- The contrast lint composites the full containing chain including
  alpha; a translucent scrim no longer lints as an opaque fill.
- Example builds refresh the committed screenshots, so a preview
  cannot drift from the renderer that produced it.

### Fixed
- Slots dropped `letter-spacing`: layout measured and centered the box
  with it while the runtime and previewer drew without it — 44px of
  divergence over 12 glyphs at 4px spacing. The value now travels in
  the slot entry (feature bit 2, stride unchanged) and every pen
  applies it, kern included, ellipsis junction included.
- The scissor stack could desynchronise: a `SCISSOR_PUSH` refused for
  want of stack was still being popped, leaving every *later* clip in
  the frame wrong rather than only the too-deep subtree. The bake now
  refuses a blob that deep as well.
- `render_slots` ignored the visibility bit, so hiding a row removed
  its panel and left its glyphs floating.
- Focus and slot name lookups were blob-global, so hiding a row on one
  screen could blank an identically-named row on another.
- `ps2ui_list_set_count` did not move focus with a shrinking list.

## 0.2.0 — 2026-08-17

The "real apps" release: the toolchain now covers what an actual
SD2PSX memory-card browser needs, with the format hardened for third
parties. `.uib` format version 3 (v1/v2 files are rejected; re-bake).

### Added
- **Dynamic text** — `data-slot` elements whose strings the console
  sets at runtime (`ps2ui_slot_set`), composed per frame from baked,
  codepoint-sorted glyph tables. Same advances and baseline as static
  text; fixed per-slot buffers, zero allocation, UTF-8, ellipsis,
  alignment, focus-aware colors.
- **Multiple screens** — several IR files bake into one blob as named
  screens sharing textures/atlases/fonts; `ps2ui_screen_set` switches
  with per-screen focus memory. The example is now two screens.
- **Images** — `<img src="assets/...png">` baked to PSMCT32 textures,
  pre-scaled at build time; opt-in **palettization** to PSMT8+CLUT
  (`palettize` attribute or `--palettize-images`), 4× less VRAM/texel.
- **Format integrity** — CRC-32 over the whole file (validated by the
  C loader and the Python reader) and feature flags that reject
  unknown capabilities loudly.
- Focus API: `ps2ui_focus_set(name)`, build-time `--focus-wrap`.
- `--mode ntsc|pal` presets; CRT-linter safe areas derive from canvas.
- `ps2ui-dev` watch mode (~200 ms edit-to-preview).
- Bake-time VRAM budget with per-texture page-rounded breakdown.
- Hardware bring-up checklist (docs/bringup.md), CI-built PS2 ELF
  (ps2dev container), texel-alignment test card, frame-diff tool.
- CONTRIBUTING.md, SECURITY.md, issue templates, Dependabot, hardened
  workflows (read-only tokens, concurrency groups).

### Fixed
- **GS modulate color domain**: TEXQUAD tints now bake in the
  0x80-identity domain; previously every tinted glyph/nine-patch would
  render up to 2× overbright on hardware while the previewer hid it.
  The previewer now mirrors the hardware `>>7` multiply.
- **Baseline seam**: glyph ink hangs from the metrics ascent layout
  measured with, not Pillow's per-size ascent (was ±1 px drift).
- **Space width**: an invisible U+00A0 in the fontgen charset shadowed
  the real space, so every space measured at `?` width on both hosts.
  Metrics regenerated; text is now correctly (and visibly) tighter.
- `GSTEXTURE::Function` is autodetected; older gsKit (including the
  ps2dev container's) builds cleanly with untinted text.
- `<img>` elements error/warn instead of silently vanishing.

## 0.1.0 — 2026-08-17

Initial scaffold: layout (HTML/CSS → IR), baker (IR → .uib + PNG
previews), C99 runtime (loader, CSM1 CLUT permutation, focus-filtered
replay, D-pad navigation), memcard example, format documentation.
