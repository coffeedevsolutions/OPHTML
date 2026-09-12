# ps2ui backlog

A list of known bugs and wanted features. **Not a queue.** What comes
next is decided by `docs/PLAN.md` §6's phase gates and the pull rule --
a feature enters when a real use case demands it -- and the section
"Where the next thing comes from" below says so at length.

Opened 2026-08-17 against the toolchain at commit `2ae7003`.

**THE TWELVE SPRINT BLOCKS BELOW ARE A CLOSED LOG (noted 2026-09-08).**
They are accurate for the period they cover and nothing has renumbered
since: the model ran to Sprint 12 on 2026-08-19 and stopped. Work after
that is recorded in `CHANGELOG.md` and the git history rather than
renumbered. Read these as history — the most recent one is not the
current state of anything.

The first version of this marker said how many commits and releases had
landed since. Both were already wrong by the commit that added them,
which is the failure this whole note is about; the date on the last
block is what a reader actually needs.

**Sprint 1 status (2026-08-17):** ✅ B1 fixed (`a8792c8`) · ✅ B9 + B8
shipped (`92ef617`) · ✅ F18 shipped (`docs/bringup.md`) · 🏗 F1 + B3
scaffolded (`runtime/sample/`, `tools/framediff.py`,
`tools/make_testcard.py`, `.github/workflows/hw.yml`) — the emulator CI
job is experimental until its first proven run; the ELF-compile job is
expected to be authoritative immediately.

**Sprint 2 status (2026-08-17):** ✅ F3 images shipped incl. opt-in
palettization (`palettize` attr / `--palettize-images`: PSMT8+CLUT, 4×
VRAM cut) · ✅ F10 `ps2ui_focus_set` + `--focus-wrap` · ✅ F7 `--mode
ntsc|pal` with canvas-derived safe areas · ✅ F11 `ps2ui-dev` watch mode
· ✅ B2 baseline seam fixed · ✅ F13 CONTRIBUTING + issue templates ·
✅ S1/S4-partial CI hardening. First Actions results: `ci` **green**
from commit `e26f606`; `hw` elf job fixed iteratively (gsKit include
path, implicit-rule includes) — emulator job remains experimental.

**Sprint 3 status (2026-08-17):** ✅ F1/hw milestone: `ci` **and** the
`hw` ELF job green in Actions — a real PS2 ELF builds in CI under the
ps2dev toolchain (the container's older gsKit also proved the
`GSTEXTURE::Function` fallback real; the runtime now autodetects it).
Play! emulator job failed at AppImage download as expected
(`continue-on-error`); needs the real release asset URL. ✅ F14 + F2
shipped as **.uib format v2**: 64-byte header with CRC-32 + feature
flags (unknown bits reject loudly), font tables with codepoint-sorted
glyph records, and dynamic-text slots — `data-slot` in HTML,
`ps2ui_slot_set/get` in the runtime (fixed per-slot buffers, zero
allocation, UTF-8 pen with ellipsis + alignment), previewer slot
rendering with overrides. The example's "6 titles" is now a live slot
and its preview is **pixel-identical** to the static bake — the pen
provably reproduces layout's measurements. ✅ F4 shipped as format v3:
a screen table partitions commands/focus/slots into named ranges with
shared textures and fonts; `ps2ui_screen_set` switches with per-screen
focus memory; the example is now two screens (library + saves, the
saves rows all dynamic slots). Bonus find: an invisible U+00A0 in the
fontgen charset had shadowed the real space — every space measured at
'?' width on both hosts; fixed with chr(32) + regression test, metrics
regenerated. F12 packaging prep: CHANGELOG, package metadata, version
0.2.0.

**Sprint 4 status (2026-08-17):** surfaced by building the channel-6
hardware mockup, all four fixed on `runtime-caps-and-slot-fixes`.
✅ B10 the baker now reads the runtime's static caps out of `ps2ui.h`
and fails the bake when a blob would hit `PS2UI_ERR_TOO_MANY`; the
17-slot blob that reached the console as a red screen is now a build
error naming the constant to raise. ✅ B11 `ps2ui_slot_set` backs off
to the last complete UTF-8 sequence instead of splitting a character.
✅ B12 `""` blanks a slot, `NULL` still reverts to the placeholder.
✅ B13 the charset lint no longer fires on face buttons and arrows;
those glyphs joined the default font charset. ✅ F23 the channel-6
example landed with its `probe` screen promoted to the repository's
conformance target: `docs/bringup.md` maps each probe cell to the step
that fails when the cell looks wrong, so bring-up is a comparison
against a previewer PNG rather than a judgement call.

**Sprint 5 status (2026-08-17):** ✅ F25 widescreen. The framebuffer and
the panel are now separate concepts: `--mode ntsc|ntsc16x9|pal|pal16x9`
and `--display-aspect W:H` set the aspect, the IR and the `.uib` header
(format v4) carry it, and `--preview-display` writes the PNG resampled
to what the television draws. A new `aspect-distortion` lint warns when
rounded corners or images will visibly stretch, and `probe-aspect` puts
three boxes on the conformance screen, pre-squashed for 1:1, 4:3 and
16:9, so whichever reads square names the aspect the panel is applying.
`examples/channel6/build.sh` bakes the same UI at both aspects, which
makes the two-way panel test in bring-up step 10 two files rather than
a procedure. Finding along the way: 640x448 is not square-pixel even at
4:3 (PAR 0.9333), so every 1:1 preview this project has ever produced
was 7% wrong, and 24% wrong at 16:9.

Two defects fell out of testing it. ✅ **B14** the contrast lint
composited text against the nearest containing rect's raw RGB and
discarded that rect's alpha, so a translucent scrim linted identically
to an opaque background — structurally blind to the one class of
problem an overlay has. It now composites the whole containing chain in
paint order, and where light still gets through it brackets the unknown
host frame between black and white and reports the worse end. That
immediately caught the channel-6 `CH 6` badge at 2.93:1 over a bright
frame. ✅ **B15** the probe screen overflowed a 448-line frame when the
aspect cell made a seventh grid cell; the footer and the FLEX cell were
off-screen and four overscan warnings had been saying so.

**Sprint 6 status (2026-08-17):** post-consolidation cleanup, both items
picked because neither needs hardware. ✅ **F22** `ps2ui-check`
generalizes `examples/channel6/check.py` into a validator any project
can point at any blob: table caps, every index the runtime dereferences
unchecked, screens partitioning the command/focus/slot tables, scissor
balance, both GS colour domains, glyph-table sort order, placeholder
coverage, focus reachability, VRAM. Errors mean the console misbehaves
with no diagnostic; warnings mean legal but wasteful. It found real dead
geometry on its first run, now filed as F24. ✅ **S4-partial** the Play!
download no longer hardcodes an asset name that 404s, and no longer
saves and executes the error page when it does.

**Sprint 7 status (2026-08-17):** the emulator job runs. Six layers had
to come off before it did: the download pointed at GitHub releases that
`jpd002/Play-` does not publish (Play! ships from purei.org), curl had
no `--fail` so a 404 body was saved and executed, `libOpenGL.so.0` was
missing, ALSA had no device, `--disc ""` was the wrong boot flag, and
the capture was of the whole desktop rather than the frame. ✅
**S4-partial** is now genuinely partial rather than nominal: the asset
is discovered, not guessed, and every step fails loudly.

**Provenance for everything below**, since the point of writing it down
is that CI logs expire: Play! **0.72**, asset
`Play!-8de4a71f-x86_64.AppImage` (the suffix is Play!'s own build
commit), fetched from purei.org's stable tree, running on llvmpipe
under xvfb in [run
32065976980](https://github.com/coffeedevsolutions/OPHTML/actions/runs/32065976980).
The job resolves the newest stable version at run time and prints the
downloaded file's sha256, so a later run may report a different oracle
for the same finding — S4 wants that pinned. Every claim here is read
off the palette fingerprint `framediff.py --stats` prints for both
frames.

**First results from something that is not our own previewer.** The
captured frame's palette matches the stylesheet's text colours to
within one unit (`#8b94a7` → `#8c94a8`, `#e8ecf4` exact), so the glyph
atlas, CLUT upload, CSM1 swizzle, modulate function and 0x80-identity
domain are all correct — bring-up steps 3, 4 and 5, and independent
confirmation of the **B1** fix.

Solid fills are a different story: the frame is 92.8% black. The step 2
probe (`make PROBE=1`, no `.uib` involved) shows the clear and an
unblended sprite drawing, blended sprites at alpha 0x20/0x40/0x60
drawing with composites matching `(Cs - Cd) * As >> 7 + Cd` exactly,
and blended sprites at 0x7f/0x80 rasterising with the *previous*
primitive's colour — a colour latch, not a discarded primitive, which
on a black clear looks the same and is not the same thing to debug.
0x80 is what every opaque quad in a `.uib` carries.
This is characterised, not diagnosed: Play! is HLE, and whether a real
GS behaves the same way is the open question. Not worth more rounds
against the wrong oracle — PCSX2 in software mode or the console
decides it.

**Sprint 8 status (2026-08-17):** ✅ **F6** lists, both halves, and
neither needed a format change.

*Templating.* `data-repeat="N"` on an element stamps N copies before
styles are computed, with `{i}` (0-based) and `{n}` (1-based)
substituted in any attribute and in text. Because expansion happens on
the element tree, a repeated row is indistinguishable downstream from
one typed out, and a test asserts the two compile to identical command
lists. Nothing is renamed implicitly: forgetting `{i}` on a `data-slot`
lands on the existing duplicate-name error, which names the slot, and
copies with no index at all are a warning. Nested repeats are refused
rather than guessed at, since only one index is in scope. Counts are
literal and bounded 1..256, because every copy costs commands and a
focusable one costs a focus node.

*Windowing.* `ps2ui_list` is the arithmetic between a fixed number of
baked rows and a variable number of items: minimum-distance scrolling
so the screen does not jump when the user asked one row to move,
clamping at both ends rather than wrapping, `item_at()` returning -1 for
rows past the end so they get blanked instead of showing last frame's
text, and a count that can shrink under a selection sitting past the new
end. Those are the cases an app reimplementing this gets wrong, which is
the whole argument for it living in the runtime. ps2ui owns the indices
and the focus; the app owns the data.

A list is a view over rows that are already baked, so this costs a UI
that never uses one exactly nothing, and no `.uib` version moved.

**Sprint 9 status (2026-08-17):** ✅ **F24** the baker drops draw
records that cannot produce a pixel. A `nowrap` run inside
`overflow: hidden` bakes every glyph and lets the GS clip, so the tail
of a long string was quads the console submitted every frame and could
never see — twenty of them in the channel-6 probe, which is where
ps2ui-check found them on its first run.

A per-screen post-pass replays the scissor stack the way `ps2ui_render`
does and drops QUAD/TEXQUAD records outside the current clip, keeping
every scissor record because balance is a contract and an empty clip
still has to be popped. The safety argument is that removing a command
that could never draw cannot change the image, and that is asserted
rather than argued: all three example previews are byte-identical
across the change, and a unit test renders a blob with and without a
dead record and compares pixels. channel-6 went 851 → 831 commands and
`ps2ui-check` now reports zero warnings on every example.

The loop closed nicely: the validator found it, the baker fixed it, and
the validator confirms it.

**Sprint 10 status (2026-08-17):** ✅ **F21** runtime visibility, which
closes a gap F6 opened. Blanking a row past the end of the data leaves
its panel and border drawn, so a short list still looked full of empty
rows.

`ps2ui_visible_set(ctx, name, 0)` stops painting a focusable subtree.
The unit is a focus node because that is the only grouping the command
list already carries, and in practice it is the unit you want. Two
details make it more than a paint flag: `ps2ui_move` walks *past* hidden
nodes rather than landing on something invisible, which is the half an
app cannot get by blanking slot text; and `ps2ui_focus_set` still
reaches one, because naming a node explicitly is deliberate.

State is a 256-bit mask in the context, zeroed at load, so a UI that
never calls the API behaves identically and pays 32 bytes. It is not a
load-time cap: a blob with more focusables loads and renders fine, it
just cannot hide the ones past the ceiling, and the setter returns 0
rather than pretending. No format change.

`ps2ui_list_apply_visibility` wires the two features together.

**Sprint 11 status (2026-08-19):** review follow-up. Four reviews on
the F6/F24/F21 stack found two defects that made shipped documentation
false — `render_slots` never saw the visibility check, so hiding a row
took its panel and left its glyphs; and the `data-repeat` no-index
warning fired on the exact pattern the README recommends, because the
serialiser skipped descendant attributes. Both fixed, along with
`ps2ui_list_set_count` gaining a `ctx` so focus follows a shrinking
list, name lookups scoped to the current screen (they were blob-global,
so hiding a row could blank another screen's), and one shared scissor
model in `clip.py` instead of two copies that already differed.

The defect behind the first one is worth naming: the test that should
have caught it drove a list prefix against a blob whose rows had other
names, so every call returned 0 and the assertions passed vacuously.
There is now a real `data-repeat` fixture built by the runtime
Makefile.

✅ **B16** the scissor stack could desynchronise. `ps2ui_render` refuses
a SCISSOR_PUSH past `PS2UI_MAX_SCISSOR_DEPTH` but was still popping it,
leaving the stack a level shallow and every *subsequent* clip in the
frame wrong, not just the ones inside the too-deep subtree. Refused
pushes now refuse their pops too, so the failure is confined to drawing
under a larger clip. And it is caught earlier: `caps.py` never actually
parsed `PS2UI_MAX_SCISSOR_DEPTH` — the regex matched but `FALLBACK` had
no key, so `caps.update` dropped it and no stage knew the limit existed
— so the bake now refuses a blob that deep and `ps2ui-check` reports
per-screen nesting.

Counts move often enough that quoting them per sprint just makes the
file wrong; `README.md` carries the commands that print them.

**Sprint 12 status (2026-08-19):** ✅ **F9** kerning, applied by all
three pens. The backlog claimed `fontgen` "already reserves a kerning
field"; it did not — only layout's `text.js` ever read
`metrics.kerning`, and nothing had written it. So the work started one
step earlier than the row assumed.

Pairs are measured rather than parsed: Pillow exposes no kern/GPOS
reader, and asking the shaper that will rasterize the glyphs what
`getlength("AV")` is against `"A"` + `"V"` records whatever it actually
does. That only holds with substitutions off — DejaVu shapes `ff` as a
ligature 15 units narrower than f + f, and the pen draws two glyphs, so
the ligature's width would have become a kern that does not exist.

The interesting constraint is that three pens must agree to the pixel,
and the third one runs on the console. Kerns therefore reach the blob
pre-resolved to pixels at each font's size — the EE is not going to
divide by 1000 per glyph pair — which makes the table per-size and
drops most pairs at UI sizes. That is the correct outcome rather than
a limitation: kerning is a sub-em correction and is invisible in 13px
text either way. Two consequences fell out of writing it down: the
ellipsis kerns against whatever glyph the cut leaves last, so its cost
cannot be subtracted from the budget up front, and a space kerns
against its neighbours, so a wrapped line's accumulated width has to
account for both boundary kerns or it disagrees with `measure()` of the
same text.

`.uib` v5: the font entry grew 16 → 24 bytes, so a v4 reader would have
walked the table at the wrong stride rather than ignoring something it
did not understand. Feature bit 1 is the first use of the machinery
F14 built, and `ps2ui-check` errors when the bit and the tables
disagree.

The agreement is now tested rather than asserted. `rounding.py` had
claimed "test_metrics_agree proves it" about a test that did not
exist; `TestCrossLanguagePen` runs both pens over a corpus at seven
sizes and three letter-spacings and compares every glyph position, and
the runtime suite checks the C pen against a linear scan of the same
tables it binary-searches. Both were verified by sabotage.

Two adjacent gaps closed on the way. The runtime's list fixture is
built by the Makefile so that it tracks the compiler it tests, but the
rule depended only on its HTML and CSS, so the format change left a
stale blob — and the test binary answered that by segfaulting, because
`CHECK` records a failure and keeps going straight into `ps2ui_upload`
on a zeroed context. And the committed example screenshots were copied
by hand, so a preview could drift from the renderer that produced it;
both example builds now refresh them.

**RICE SCORES WERE REMOVED ON 2026-09-07, AND THE SCALES WITH THEM.**
`docs/PLAN.md` §4.6 retired RICE as the driver; the ranked table that
used to sit below was deleted when it went stale; the R/I/C/E columns
outlived both, in the rows, labelled as a historical record rather than
a mechanism. That distinction did not survive contact with readers.

It misled twice. Once when the stale ranked table read as the answer to
"what is next" while every item it named had shipped. And once when
somebody adding an item re-scored an existing row to justify sequencing
by the result -- destroying the one thing a filing-time estimate is
for, in the very file whose sequencing section exists to explain why
that mechanism was retired.

A number that nothing consumes, printed beside every row, will be read
as a ranking however it is captioned. So the columns are gone rather
than re-explained. What replaces them is what was already true: the
gates in `docs/PLAN.md` §6, and the pull rule.

## Bugs

| ID | Bug |
|----|-----|
| B1 | ✅ **Textured-quad vertex RGB is in the wrong domain for GS modulate.** The GS `MODULATE` function treats `0x80` as identity for RGB exactly as it does for alpha (`Cv = Ct·Cf >> 7`), but the baker emits tint colors with full-range 0–255 RGB. On hardware every tinted glyph and nine-patch will render up-to-2× overbright and clamp: white text survives by luck, mid-tone text (`#8b94a7` metadata, `#c8cfdc` labels) washes out badly. The previewer normalizes by 255, so it *hides* the bug — the exact class of divergence the replay-the-blob design exists to prevent. Fix: emit modulated RGB in the 0x80 domain in `quads.py` (same one-crossing rule as alpha), mirror in `preview._tint`, add a cross-domain test. |
| B2 | ✅ **Baseline seam between metrics ascent and FreeType ascent.** Layout positioned line boxes from `ascentPx` derived from the metrics JSON while the atlas placed ink relative to Pillow's `font.getmetrics()` ascent at the render size; the two disagree by ±1px at some sizes, nudging ink off its measured line box. Both halves the row asked for are in the tree: `atlas.py:75` derives `metrics_ascent_px` through the shared rounding rule and `:130-132` hangs ink from it rather than from Pillow's, with the code citing this row by name; `test_baker.py:397` `test_ink_hangs_from_metrics_baseline` is the golden test at five sizes, asserting the ink bottom lands on the metrics baseline within a pixel of AA slop and that a descender still reaches past it. **The third shipped-but-unticked row found on 2026-09-12, and the one that says the most.** B8 was unmatchable and F24 was simply missed; B2 was *audited and recorded as unsettled*, which is worse, because a reader consulting the board learned something false from a row someone had looked at. The Sprint 2 status line has said `✅ B2 baseline seam fixed` since 2026-08-17. It was found by running the status-line-versus-row check F29 proposes — on its first run, against a row nobody suspected. |
| B3 | ✅ **GS half-texel / half-pixel sampling conventions unaudited.** Classic PS2 artifact family: sprite UVs off by half a texel, primitive coordinates off by half a pixel against the 2048-centered window, interlaced field offset. gsKit absorbs some of this (`OffsetX/Y`), not all. Everything looks right in the previewer, which proves nothing about texel centers. Needs an on-target test pattern (checkerboard atlas + 1:1 quads) and probably `+0.5` UV nudges in one place. Blocked on F1 for verification. |
| B8 | ✅ **VRAM budget only checked at test time, not bake time.** A UI whose atlases + patches exceeded 4 MB (minus framebuffers) baked fine and died at upload. `vram.report` now computes the worst-case footprint with gsKit page rounding and `cli.py:266` fails the build on it, printing the per-texture breakdown the row asked for; `--vram-budget` overrides, and #119 made a budget that cannot exist say so rather than blaming the textures. **THIS ROW WAS `B8*` FOR A MONTH, AND THE ASTERISK IS WHY NOBODY FIXED IT.** No legend in this file ever defined that marker — every other shipped row uses ✅ — while the Sprint 1 status line above already said *"✅ B9 + B8"*, so the board stated three different things about one row. It was not overlooked, it was **unmatchable**: a sweep keyed on `| B8 |`, or on `^\| (F\|B\|S)[0-9]+ \| `, skips `| B8* |` entirely. That is why the 2026-09-07 audit missed it and why a sweep on 2026-09-12 missed it again. Ticked once the marker was removed. |
| B9 | ✅ **`<img>` parses but silently paints nothing.** Until real image support (F3) lands, an `<img>` in the document should at minimum be a loud compile warning — silent drops are how people lose an afternoon. One `if` in `box.js`. |
| B7 | **Percentage sizes against an indefinite container silently resolve to auto.** CSS resolves `%` against definite sizes and has defined fallbacks; ps2ui treats null as auto without saying so. Either implement the CSS behavior or make it a documented compile warning. |
| B4 | **`row-reverse` / `column-reverse` only reverse order, not main-axis start.** With `justify-content: flex-start`, a `-reverse` container should pack from the main-end; ps2ui packs from main-start with reversed items (only coincidentally correct for `center`/`space-between`). |
| B5 | **`opacity` is per-box, not group opacity.** A container's opacity doesn't multiply into descendants, diverging from CSS. True group opacity needs offscreen composition the GS makes painful; the honest fix is inherited multiplied opacity (close enough for flat UI) plus a doc note. |
| B6 | **`overflow: hidden` + `border-radius` clips square.** The GS scissor is rectangular; rounded clipping would need stencil/alpha tricks. Cheap first step: lint warning when both are set on one box. |
| B10 | ✅ **Baker never checked the runtime's static table caps.** `ps2ui.h` sizes four tables (`MAX_TEXTURES` 32, `MAX_SLOTS` 16, `MAX_SCREENS` 8, `SLOT_BUFSZ` 96) and `ps2ui_load` rejects anything past them, but nothing on the host knew those numbers. An over-sized blob laid out, baked, previewed and passed every host test while being unloadable: the sample ELF's red screen with no diagnostic. Same failure shape as B1, host says fine and console says no. Fixed in `caps.py`, parsed from the header so it cannot drift. *(Superseded by PLAN §6.3: three of the four caps were deleted rather than checked harder, once the v6 arena made them bound nothing the blob's own size did not. `caps.py` still parses `PS2UI_MAX_SCISSOR_DEPTH`, which is real storage.)* |
| B11 | ✅ **`ps2ui_slot_set` split UTF-8 sequences.** Truncation was a byte-wise `strncpy` at the slot capacity, so an accented or CJK title cut mid-character left a partial sequence the pen decoded as U+FFFD and drew as `?`. Fixed by trimming back to the last complete sequence. |
| B13 | ✅ **Charset lint fired on PlayStation face buttons.** The rule warned on every codepoint above U+24FF, which includes ○ (U+25CB) and △ (U+25B3). Every PS2 footer carries those hints, so the lint trained authors to ignore it. Now whitelists punctuation, arrows, math operators, geometric shapes and dingbats, all single glyphs with no line-breaking rules of their own. |
| B12 | ✅ **A slot could not be blanked.** `""` reverted to the baked placeholder because the check was `slot_text[i][0] != '\0'`, so an app with no data for a row could not empty it. `NULL` already meant revert, so `""` now means blank. |
| B14 | ✅ **Contrast lint discarded background alpha.** It read the nearest containing rect's raw RGB, so a 60%-opaque scrim scored the same as an opaque fill. A `.uib` is replayed over whatever the host app drew, so this is exactly backwards: the translucent case is the one where contrast is at risk and the one the rule could not see. Now composites the full containing chain in paint order and, when the chain still transmits, evaluates against black and white backdrops and reports the worse. |
| B15 | ✅ **Probe screen overflowed the canvas.** A seventh 178px cell in a wrapping grid sized for six pushed a third row past y=448, putting the FLEX cell and the whole footer off-screen. The linter emitted four overscan warnings that went unread; the example is meant to be warning-free so that a warning means something. Cells are 135px, wrapping 4 + 3. |
| B16 | ✅ **Scissor stack could desynchronise, corrupting the rest of the frame.** `ps2ui_render` refuses a SCISSOR_PUSH past `PS2UI_MAX_SCISSOR_DEPTH` but still popped it, so after one too-deep subtree the stack sat a level shallow and every later clip was wrong — text bleeding out of panels it never belonged to, far from the markup that caused it. Compounding it, `caps.py` never parsed the constant (the regex matched, but `FALLBACK` had no key so `caps.update` dropped it), so no stage knew the limit existed. Refused pushes now refuse their pops, the bake rejects a blob that deep naming the constant to raise, and `ps2ui-check` reports per-screen nesting. |

\* numbered to match the working notes. The order rows appear in carries no meaning.

## Features

| ID | Feature |
|----|---------|
| F18 | ✅ **Hardware bring-up checklist** (`docs/bringup.md`): ordered list of what to verify first on PCSX2/hardware — text tinting (`GSTEXTURE::Function`), B1 color domains, B3 texel centers, CLUT swizzle, alpha blend state, interlace field order — each with its expected-vs-symptom. Converts the "not hardware-verified" caveat into a runnable procedure. |
| F1 | ✅ **PCSX2 verification harness in CI.** Boot a minimal ELF that loads the example blob, renders one frame, screenshots via PCSX2's automation, and image-diffs against the previewer PNG within tolerance. The single highest-leverage credibility move: flips C from 0.5→1.0 for B1/B3/F5 and makes every future GS-path change regression-safe. |
| F10 | ✅ **Focus API completion.** `ps2ui_focus_set(ctx, "name")`, optional wrap-around per axis (solved at build time as extra graph edges, zero runtime cost), and an activation callback convention. Every real app needs to restore focus after a screen swap; today only `move` exists. |
| F3 | ✅ **Image support.** `<img src>` → Pillow decode at bake time → PSMCT32 (or quantized PSMT8+CLUT for flat art) textures in the .uib, sized by layout like any box. The format already carries arbitrary textures; this is mostly layout-measure + baker plumbing. Unlocks logos, save-icon thumbnails, backgrounds. |
| F7 | ✅ **PAL / video-mode presets.** `--canvas` exists but the CRT linter's safe-area insets and the example are NTSC-tuned. Add `--mode ntsc\|pal\|480p` presets driving canvas, linter geometry, and a documented runtime note on mode setup. Half of PS2 homebrew's audience is PAL. |
| F11 | ✅ **Watch mode.** `ps2ui dev`: watch `ui/*.html,css`, rebuild IR + blob, re-render preview PNG on change (optionally serve in a browser with live reload). The edit loop today is two manual commands; iteration speed is the whole pitch of HTML authoring. *(✅ `ps2ui dev` shipped in Sprint 2; the parenthetical did not, and it was the half that mattered — `dev` re-renders a PNG and leaves you refreshing an image viewer, with no way to move focus, switch screen or see a second theme. Closed by `ps2ui serve`: a localhost page rendering `preview.render()` server-side, with arrow-key navigation along the baked focus graph, screen and theme switching, four aspect modes, editable slot text, warnings and click-to-inspect over the command list. `dev` stays: it is headless and writes PNGs, which is what keeps it usable in CI. What `serve` does not cover — runtime visibility, and the F-048 class of divergence only hardware finds — is stated in the README rather than left to be discovered.)* |
| F13 | ✅ **Contribution surface.** CONTRIBUTING.md (how to run all three suites, how the seams work), issue templates, and 4–6 curated good-first-issues (named colors, `text-transform`, montage columns flag, B9). Cheap, and the format specs already do the heavy lifting. |
| F2 | ✅ **Runtime dynamic text.** The flagship gap for the actual SD2PSX use case: a real memory-card browser lists titles read from the card at runtime, but today every string is baked. Design: bake full glyph tables (advance + UV per codepoint) per face/size — the .uib texture format already supports it — reserve `data-slot` text boxes at layout time (fixed rect, alignment, ellipsis policy), and add a small runtime pen (~100 lines: advance loop + ellipsis, no wrapping) writing glyph quads into a per-slot buffer. Keeps the no-allocation rule via caller-provided slot buffers. |
| F14 | ✅ **.uib integrity + feature flags.** CRC32 over the payload (validated by loader and Python reader) and a feature-bits field in `flags` so future additions (F2 glyph tables, F5 chains) degrade loudly, not mysteriously. Do it before third parties write .uib files. |
| F4 | ✅ **Multi-screen documents.** Several HTML files → one .uib with named screens sharing textures/atlases; runtime gets `ps2ui_screen_set`, per-screen focus memory, and an optional baked crossfade. Every non-trivial app has ≥2 screens; today they'd ship N blobs and duplicate atlases. |
| F12 | ✅ **Packaging.** Publish `@ophtml/layout` to npm and `ophtml` to PyPI, plus one `ps2ui` wrapper CLI (`build`, `dev`, `fontgen`) so the quick start is two installs and one command instead of PYTHONPATH incantations. |
| F9 | ✅ **Kerning.** `fontgen` already reserves a kerning field; emit pairs from the TTF, apply in `Font.measure`/wrap and in the baker's pen with the same rounding rule, covered by a cross-language agreement test. Visible on large headings ("PS2", "Library"). |
| F8 | **`position: absolute` overlays.** Badges, dialogs, and focus-follow cursors need out-of-flow boxes. Constrained version: absolute within the nearest padded ancestor, no auto-margins, still zero runtime cost. **Pulled 2026-09-07** by the OPLattice recreation, which wanted a title over key art and a badge on a cover and could express neither; see the dated section below. What that section adds is that this is a COMPILER change touching no format field: `paint.js` already walks in document order back-to-front with no z-index and records already carry `x, y, w, h`, so an overlapping display list is expressible in a v7 blob today and nothing can produce one. **Whether it DRAWS that way is the host's decision, not the runtime's** — `ps2ui.c` never sets, requires or checks `ZBuffering`; the sample host disables it, and `vram.py`'s budget model already treats hosts differing on exactly that as load-bearing. So F8's design pass has a question to answer on purpose: does layering require Z off, and if it does, does that belong in `ps2ui.h`'s contract rather than in a sample? `lint.js:97` was written as forward cover for exactly this. It does break two load-bearing lint assumptions — the contrast check composites against *the nearest containing rect*, undefined under overlap, and `box.js` refuses nested focusables outright. |
| F17 | **Localization workflow.** Per-locale build passes (the architecture already prescribes this): string catalog extraction from HTML, per-locale bake with locale-appropriate charsets in the atlas, `ps2ui build --locale`. |
| F15 | **Gradients as baked textures.** `linear-gradient` rasterized to small strip textures at bake time, stretched by the GS. Pure polish; the mockups' thumbnails would benefit. |
| F6 | ✅ **List templating / scrolling regions.** Data-driven repeats (`data-repeat` on a template child) with a runtime-scrollable window over more items than fit — the full solution to "the card has 40 saves". Depends on F2; large runtime surface (scissor + per-item focus), which is why it scores below its obvious value. Revisit the score once F2 lands. |
| F5 | **Precompiled GIF/DMA chains.** The roadmap's performance endgame: bake per-state GIF packets so a frame is a DMA kick instead of per-quad gsKit calls. Near-zero CPU per frame, but the biggest hardware-knowledge item in the backlog and pointless to attempt before F1 exists to validate it. |
| F16 | **Non-Latin text.** CJK/greedy-break rules, font fallback chains, larger atlases (PSMT8 CLUT pressure). Real for localization, small audience today, large effort. Pair with F17 when demand appears. |
| F22 | ✅ **`ps2ui-check`, a validator for any blob.** `examples/channel6/check.py` asserted the right properties but had one example's focus names and slot capacities hardcoded, so nobody else's build got them. Generalized into `ps2ui_bake.check`: table caps, every index the runtime dereferences unchecked, screens partitioning the command/focus/slot tables, scissor balance per screen, both GS colour domains, codepoint-sorted glyph tables, placeholder coverage, focus reachability, VRAM. Errors mean the console misbehaves with no diagnostic; warnings mean legal but wasteful. TAP output, `--strict`, wired into both workflows. |
| F19 | **`ps2ui_unload()` and VRAM bookkeeping.** The runtime uploads once and never releases, so an app cannot swap one blob for another. Needed before a shell-and-module example is possible: the shell's UI and a module's UI cannot both be resident under a 4 MB budget. Deliberately deferred until the GS path is hardware-verified, since it changes how VRAM is managed and debugging that against an unproven renderer means debugging two things at once. |
| F20 | ✅ **Runtime image slots.** `data-slot` covers text; cover art discovered at runtime (an OPL-style ART folder) still cannot be shown, because textures are baked. Needs F19's VRAM bookkeeping first. |
| F21 | ✅ **Runtime visibility toggle.** `display: none` is compile-time only, so an app cannot hide a row it has no data for; today the workaround is blanking every slot in it, which leaves the panel drawn. A per-focus-node or per-element visibility bit the render loop honours. |
| F24 | ✅ **Trim geometry that cannot draw.** A `nowrap` run inside `overflow: hidden` baked every glyph and let the GS clip, so the channel-6 probe submitted 20 quads per frame that were outside their scissor. F22 measured it; the baker now drops them at flatten time, once the clip is known: `clip.py:41` `dead_indices` finds them, `quads.py:486` `_trim_dead_geometry` removes them, `quads.py:576` calls it per screen, and `cli.py:249` reports the count. Fenced at `test_baker.py:2636,2641`, including the case where nothing should be dropped. Shipped and left unticked; found the same day as B8. |
| F26 | ✅ **The runtime did not reach anyone who had not cloned.** `pip install ophtml` gave a stranger the whole authoring path, and then `README.md` told them to *"drop `runtime/ps2ui.c` and `runtime/ps2ui.h` into your ps2sdk/gsKit project"* — repo paths, in a package that shipped neither file: the wheel carried `ps2ui_bake` alone and the npm tarball `src/ bin/ README.md`. So the console half, which is the point of the project, required a clone, and **Phase 4's exit gate says "without cloning the repo"** — the two had contradicted each other since the gate was written, unseen because `registry.yml` exercised the authoring half weekly and went green over a gate whose other half nobody had attempted. Fixed in `packages/baker/setup.py`, which stages `ps2ui.c` and `ps2ui.h` into the package at build time from their one canonical home, and `ps2ui vendor-runtime <dir>`, which writes them into a project from the install — so the runtime compiled matches the baker that wrote the blob. Nothing is committed, so there is no second copy to go stale. `package-data` could not simply point at `../../runtime`: measured, it is silently omitted with rc=0 and no warning, which is why `tools/check-runtime-shipped.py` asserts the built wheel *and* the sdist rather than the declaration. **Numbered F26 because F25 was already taken** by the Sprint 5 status line above (widescreen), and two ticked F25s made `grep` ambiguous. **F23 is the same trap and was not written down until now:** `✅ F23 the channel-6 example landed…` sits in a status line with no F23 row anywhere, so the next person reaching for a free ID can recreate the collision this note exists to explain. **F23 and F25 are consumed. Do not reuse either.** Both live in status lines rather than tables, which is why F29's uniqueness check has to read the whole file rather than the three ID tables. |
| F27 | ✅ **A positional API: `ps2ui_offset_set(ctx, dx, dy)`.** The runtime could change *what* is drawn — focus, theme, slot text, textures, visibility, screen, list window — and never *where*. The public surface in `runtime/ps2ui.h` had no translate, offset, scroll or pan, so a panel that slides, a carousel, a parallax layer and a scrolling region were all unreachable, and a UI whose sidebar expands had to bake both end states as separate screens with no motion between them. **No format change**, as predicted: a draw-time transform over commands that already exist, so it works on every blob this toolchain has ever baked and the v7 pledge is untouched. **The row's own plan was wrong about where the offset goes, and the fence is what said so.** It named three `c->x` sites plus the scissor computation; applying it exactly there left the two glyph sites that derive a position from a slot behind, and the runtime check for "every primitive moved by exactly the offset" failed on the first run. It lands inside `draw_texquad` instead — the sink all three texture paths pass through — and in `clip_rect` on the Python side, the same shape for the same reason. `preview.py` moved in the same commit, and its own first version was wrong too: the texquad clip was measured against the quad's blob-space rect while the clip had already been offset, sliding every texture's source *inside* its quad. Both defects read correctly at offset `(0, 0)`, which is every frame either pen had drawn before this. Nine runtime checks and five Python ones, six sabotages, two of which reported HOLE first — one because the scene carried no text and one because the assertion was reading Pillow's boundary clipping rather than this module's. **Pulled 2026-09-07.** |
| F28 | **Eight places still state a mechanism that was removed on purpose — six to correct, two to leave — and no rule can see any of them.** `README.md:672` and `CONTRIBUTING.md:16` instruct a contributor to run `make -C runtime test-compat`; `README.md:675` describes what it does (*"repeats everything with `PS2UI_GSKIT_HAS_FUNCTION=0` for older gsKit (text loses tinting)"*); `docs/PLAN.md:75` states the runtime suite is *"run twice (modern gsKit and the `HAS_FUNCTION=0` fallback)"* as a phase's verification. **None of it exists** — neither the Makefile target nor the macro is in the tree, so the README's own verification block ends in `make: *** No rule to make target 'test-compat'`. **Not drift: a correct removal whose documentation was never followed through.** #39 (`499212c`) took the mechanism out deliberately and enumerated `test-compat` in its commit message, because [F-005](docs/findings.md) settled that gsKit has **no** `GSTEXTURE::Function` field and hardcodes `TEX0.TFX = 0` at all 30 of its `TEX0` sites. The fallback these documents describe is a path gsKit has never had. **THE INVENTORY IS THIS ITEM'S ONLY DELIVERABLE, AND THE FIRST DRAFT OF IT WAS INCOMPLETE — for the reason the item is about.** It was built by grepping `test-compat\|HAS_FUNCTION`, the vocabulary of the *mechanism*, which cannot match prose naming the *field*. Two sites name the field and were missed, and the worse of the two is the worst site overall: `examples/channel6/README.md:245`, the bench card an operator is told to *"put next to your capture"*, whose TYPE row reads *"flat white = no `GSTEXTURE::Function` (step 4)"*. That is a cause F-005 proves impossible, printed as a diagnosis to a person at a console, so the third cause that must therefore exist goes unlooked-for. `examples/channel6/ui/channel6.css:466` is the same fault in a source comment. **Two sites are historical record and stay as written**, but the row names them so nobody edits shipped history to satisfy this item: `CHANGELOG.md:600` (0.2.0 — a changelog records what shipped) and `BACKLOG.md:41` (the Sprint 3 status line, which says the container's older gsKit *"proved the `GSTEXTURE::Function` fallback real"* — worth an explicit correction beside it rather than a rewrite, because what it reports as proved was disproved six days later). `docs/PLAN.md:232` needs a second look rather than a search-and-replace: it lists the fallback under *"Left: steps 3-9"*, and `docs/bringup.md` §4 opens *"SETTLED BY SOURCE. No bench slot, no ELF, nothing to look at"* — stale twice over. **WHAT CANNOT BE FENCED, AND WHAT CAN.** `tools/check-findings.py` rules 6 and 8 exist for prose repeating a dead belief and cannot reach any of this: both key on **citations** (rule 8's docstring: *"it cannot see prose that states one while citing nothing"*) and both are scoped to **overturned** findings, while F-005 is live and correct. A keyword sweep is the obvious wrong answer — rule 6's own note records that matching claim text against prose was tried and dropped as too fragile — and the missed bench card is a second proof of it. But the neighbouring class IS already fenced: `.github/workflows/hw.yml:188-231` compiles a probe that fires if F-005's **falsifier** ever appears, and `docs/findings.yaml` carries a `falsifier` field for every finding. So the generalisable rule is *"every confirmed finding whose falsifier is mechanically testable has that test wired up, and a falsifier that fires makes every document citing the finding fail through rule 6"* — which converts an unfenceable prose problem into a partly-fenced source problem using machinery the checker already has. It also explains why THIS one still slipped: F-005's probe exists and is green, the library never changed, and what rotted was text about a **removal**, which no falsifier describes. Fencing that residue is the open question. **Found 2026-09-09** by running the README's verification block during F27, the first time in this session anything ran it end to end; inventory completed in review of #123, which found the sixth site; the count and the two historical records were settled by re-deriving the list over `test-compat\|HAS_FUNCTION\|GSTEXTURE::Function` and classifying every hit, rather than by adding one to a number. The four remaining hits are correct narrative saying the belief was false (`docs/bringup.md:670,682`, `docs/findings.yaml:117`, `runtime/stub/gskit_stub.h:8`) and are listed so the next pass does not re-litigate them. |
| F29 | **The audit that exists to catch stale ticks has now missed rows three times, and none of the three was a judgement call.** The 2026-09-07 pass ticked 17 rows and left B8, F24 and B2; a sweep on 2026-09-12 missed B8 again. B8 was **unmatchable** — its row read `| B8* |`, a marker no legend defines, which no ID-keyed pattern matches; F24 was **well-formed and missed anyway**, findable only by reading `quads.py`; B2 was **audited and recorded as unsettled**, which is worse than either, because a reader learned something false from a row somebody had checked. F28 records the same shape one layer out and `docs/method.md` a third time. **WHAT A FENCE CAN ASSERT, all of it structure and none of it prose.** *(1)* Every row ID in the three `| ID |` tables matches `(F|B|S|P)[0-9]+` exactly, no trailing punctuation and no undefined marker. *(2)* Every ID **claimed** anywhere in this file resolves to exactly one row or is declared consumed. Scoped to tables it misses both real collisions, because `✅ F23` and `✅ F25` live in status lines and have no rows at all — but "mentioned anywhere" is too wide. **ONE CORPUS RULE SERVES BOTH CHECKS: a table row contributes only its ID cell, and every tick-claim is read from the status lines.** A bare prose mention is a reference, not a claim. Without it check 2 fires on `S10` at `:481` — a **bench step**, not a board row; `docs/bringup.md:971` and `docs/findings.md:154` use the same `S` prefix for a namespace this file never declares — and on this row itself, which quotes `✅ B9 + B8` and mentions `S10` in one long line. With it, both checks are clean on this head and, run against `098b134`, return exactly the right things: check 2 gives B8 and B10-B16, check 3 gives B2, F24 and S4. *(3)* No status line claims an ID shipped while its row is open. **Which check catches which row is not what this row first said.** Run against the board as it stood at `098b134`, check 3 returns B2 and F24 — and **not B8**, because `| B8* |` never parsed as a row at all, so the ID falls to check 2 as an unresolved claim. The marker defect is check 2's business and the stale tick is check 3's; the two are not interchangeable, and check 2 also returns B10-B16 there, the rows the split table swallowed. **THE SPEC HAS TO NAME THREE TRAPS OR THE IMPLEMENTER WILL HIT THEM, and the first was hit while writing this row.** (a) **Match the ID as a token, through markup.** A pattern anchored on `✅ <ID>` misses `✅ **<ID>**`, which on the board this was run against (`098b134`) is **10 of the 29 ticks that name an ID** — a third of them, invisible. (30 raw `✅` marks sit on its status lines; one names prose rather than an ID, which markup blindness cannot affect either way. The denominator is worth pinning because this row states it as a measurement.) The first hand-run of check 3 used exactly that pattern, reported the board clean, and was believed; it found B2 only because line 33 happens to be unbolded. **A check that found a real defect for an accidental reason is still a check that passes for the wrong reason.** (b) **`<ID>-partial` is a distinct token and does not assert `<ID>`.** The board has a genuine third state and already spells it that way twice; a check requiring exact tokens never fires on it, so no prose carve-out is needed and none should be added — that would be claim-matching, which rule 6's note warns off. One status line broke the convention by writing `✅ **S4**` for partial work and is corrected in this commit. (c) **Only the three `| ID |` tables are the board.** This file also holds a three-column table whose first cells read `F27 positional API ✅` and `F8 layering`; checks 1 and 2 flag both unless scoped. (d) **Check 3 reads status lines, not table rows, and the case it exists for is what forces that.** `✅ B9 + B8` does not put the ID next to the tick, so any implementation that catches B8 must match **non-adjacently within the line** — and non-adjacent matching over table rows then fires on every ticked row that names an open ID anywhere in its prose, which these rows do routinely: F20's row is ticked and cites F19, which is open. Run that way over the whole file it returns F19, F5, F8, S4 and this row's own quoted examples. So the scoping is structural rather than an accommodation for one quotation — it is the same corpus rule check 2 needs, for the same reason, and nobody should later "improve" either check by widening it back over table rows. Check 2 still needs the whole file, because the collisions it looks for live in status lines. The two checks read different corpora and the spec has to say so. **A fourth thing was found by building it:** a blank line inside the Bugs table split it in two, so B10-B16 followed no header row and rendered as literal text rather than as table rows on every view of this file since `0b985d2`. Nobody reading the board noticed for a month; a parser noticed immediately, which is the argument for check 1 having a shape at all. **WHAT IT CANNOT DO:** a row whose work shipped and whose ID and marker are both well-formed. F24 was exactly that, and only reading the code found it. The fence bounds the problem rather than solving it, and the residue is the one F28 leaves open. **Filed 2026-09-12**; the trigger was a stranger-path report checking the board against the code rather than against itself, and the spec above is what survived a reviewer building all three checks and finding two of them red on correct board state. |

## Security & abuse (added 2026-08-17 after CI review)

Context: the repo is public, so GitHub-hosted Actions minutes are free and
un-billable — "bombing the Actions count" is not a cost risk. Fork pushes burn
the fork owner's quota, and first-time-contributor PRs require maintainer
approval before workflows run (keep that default setting on). The real vectors
are queue-congestion noise, CI supply chain, and parsing untrusted inputs.

| ID | Item |
|----|------|
| S1 | ✅ **CI hardening.** Explicit `permissions: contents: read` on every workflow (default token is broader), `concurrency` groups so rapid pushes cancel superseded runs instead of queuing, artifact `retention-days` trimmed from 90, and narrowed `push` triggers (`main` + working branches) so branch pushes and their PRs don't double-run. Never attach a self-hosted runner to this public repo. |
| S4 | **CI supply chain.** Pin third-party actions to commit SHAs (tags are mutable), add Dependabot for actions updates, pin + checksum the Play! AppImage download in `hw.yml` (currently `latest`, a moving target executed in CI), and add SECURITY.md with a reporting contact. SHA pinning needs upstream SHA lookups — done at next maintainer touch. |
| S2 | **Fuzz the .uib loader.** `ps2ui_load` bounds-checks every table, but users will share blobs and themes; a libFuzzer/AFL harness over `ps2ui_load` + a stubbed `ps2ui_render` walk (plus a Python fuzz pass over `read_uib`) turns "carefully reviewed" into "mechanically hammered". Wire into CI as a short smoke pass, longer runs nightly. |
| S3 | **Resource-exhaustion limits in the compilers.** Untrusted HTML/CSS/IR (third-party themes) can request a 30000px canvas, 10k-deep nesting, or atlases that swallow gigabytes at bake time. Add hard caps with clear errors: canvas dimensions, node count, tree depth, per-bake texture bytes (the VRAM budget already bounds the output side). |

S1 ships immediately (this commit). If the repo ever goes **private**, minutes
become metered: narrow triggers further, confirm the Actions spending limit is
$0 (the default), and re-read this section.

## Sequencing — read docs/PLAN.md §6, not this file

**A ranked table used to sit here and it should not have.**
`docs/PLAN.md` §4.6 retired RICE as the driver in so many words —
*"RICE is retired as the driver. Sequencing comes from the phase gates
in §6; admission from the pull rule: a feature enters when a real use
case demands it, never because it scores well."* The table outlived
that decision by long enough to go completely stale, and because it was
still printed under the heading "Priority order" it read as the answer
to "what is next".

Every item it named had shipped. It ranked **F12 packaging** second
while `0.4.0` sat on PyPI and npm, and **B1 modulate colour domain**
first while the CHANGELOG recorded the fix. The three sprint plans
under it sequenced work finished a year ago. Removed rather than
updated: maintaining a mechanism the plan has retired is how it got
here.

**The R/I/C/E columns are gone too, as of 2026-09-07.** They were kept
as a record of what was believed when an item was filed. In practice a
number beside every row reads as a ranking whatever the caption says,
and it misled a reader into re-scoring a row to justify an order --
which is the one thing a filing-time record must not allow. Removing
them costs the history of an estimate nobody consulted; keeping them
cost the same confusion twice.

### Where the next thing comes from

1. **`docs/PLAN.md` §6, the phase gates.** Phase 4 is the current and
   last one. Its remaining clause needs a PlayStation 2, not a commit.
2. **The pull rule.** A feature enters when a real use case demands it.
3. **The open rows below**, when one of them is in the way of that.

## How the ticks below were established (2026-09-07, amended 2026-09-12)

**THE 2026-09-07 PASS BELOW MISSED THREE ROWS, AND THE AMENDMENT IS
WORTH MORE THAN THE PASS.** B8, F24 and B2 had shipped and stayed
unticked; a fresh sweep on 2026-09-12 missed B8 a second time. None of
the three was a judgement call, and they failed in three different
ways:

- **B8 was unmatchable.** Its row read `| B8* |`. No legend in this
  file has ever defined that marker, and no ID-keyed pattern matches
  it — not `| B8 |`, not `^\| (F\|B\|S)[0-9]+ \| `. Meanwhile the
  Sprint 1 status line said `✅ B9 + B8`, so the board asserted three
  different things about one row and a reader could confirm whichever
  they looked at first. The marker is now gone and the row is ticked.
- **F24 was well-formed and still missed**, which is the harder case:
  its ID and marker were fine and only reading `quads.py` and
  `clip.py` showed the work was done. No syntax check would have
  caught it.
- **B2 was audited and recorded as UNSETTLED**, which is worse than
  either, because a reader consulting the board learned something
  false from a row somebody had already looked at. It is fixed in
  `atlas.py:75,130-132` and fenced at `test_baker.py:397`, both citing
  the row by name, and the Sprint 2 status line has said `✅ B2` since
  2026-08-17. Found by checking status lines against row markers — the
  cheapest thing F29 proposes, run once by hand.

**AND THAT HAND-RUN WAS ITSELF A CHECK THAT PASSED FOR THE WRONG
REASON**, which is worth more than the row it found. Its pattern
anchored on `✅ <ID>` and could not see `✅ **<ID>**` — 10 of the 29
ticks naming an ID on the board it ran against, a third of them — nor
`✅ B9 + B8`, where B8 is not adjacent to its tick. It reported clean
and was believed; a reviewer implementing check 3 from F29's wording
immediately found two hits it had missed. B2 came back only because
line 33 happens not to be bolded. So the argument for building the
fence stands and the evidence for it was luck, and F29's spec now
names token-matching-through-markup as trap (a).

Both were found by a report that checked the board against the *code*
rather than against itself. F29 files what a fence can and cannot
assert here; the short version is that table syntax is checkable and
"has this shipped" is not.

Not from memory. Each ✅ rests on one of: an entry in `CHANGELOG.md`
naming the change, a symbol that exists in `runtime/ps2ui.h`, or a live
artifact in the tree. Seventeen rows were ticked in this pass — they
had shipped, in some cases years of commits ago, and nothing had
recorded it.

**THE FIRST PASS OF THIS AUDIT WAS ITSELF WRONG, TWICE, AND THE REASON
IS THE USEFUL PART.** It searched using the vocabulary of the PROBLEM
rather than the vocabulary of the FIX:

- **B3** was reported unsettled because `grep` for "half-texel" and
  `0.5` found nothing. The fix is `runtime/ps2ui.c:860`,
  `#define PS2UI_TEXEL_BIAS (1.0f / 16.0f)` — S10 measured both axes
  and the bias landed as one *sixteenth*. The row's own title still
  says "half-texel", so searching it was searching for the bug.
- **F3** was reported open because the CHANGELOG's `<img>` line reads
  "error/warn instead of silently vanishing" — which is B9's earlier
  fix. Image support is `cli.py:152`, `--palettize-images`, with a
  per-image `palettize` attribute.

Both are ticked. Two other methods were tried and were worse: keyword
`grep` returned three false positives in one run (F15 matched `rgba`,
F17 matched PLAN.md prose *describing* the item, S2 matched a
filename), and `git log --grep` matched this audit's own commit for
every ID it names. **What worked was reading the implementation area
for the fix's vocabulary.**

**One row is still unsettled and is marked so rather than guessed:**

- **B2** (baseline seam between metrics ascent and FreeType ascent).
  `fontgen.py`'s docstring calls the metrics file "the seam", but about
  *advances*, which is a different claim from the ascent one. Wants
  somebody who knows the text path.

**Absence of evidence was not recorded as "open" without checking.**
Every unticked row below other than B2 was confirmed at the
implementation level — the symbol, the CSS property, or the harness is
absent. B4 is the strongest of them: `flex.js:451` reads
`isReverse(s) ? [...line.items].reverse() : line.items`, which reverses
the order and nothing else, which is exactly what the row says the bug
is.

## Two gaps a real UI found (2026-09-07)

Both rows above — F8 and the new F27 — came out of building a working
recreation of the OPLattice shell in this toolchain: four screens at
`--canvas 704x448 --display-aspect 16:9`, real cover art, real metadata
from 46 discs, built with the published `0.5.0` packages rather than
from this checkout. Neither gap was visible from reading the code. Both
appeared within an hour of trying to reproduce a shell that already
exists.

**THE FINDING THAT MATTERS IS WHAT THEY DO *NOT* COST.** The `.uib`
format is pledged frozen at v7 and `tools/check-format-frozen.py`
enforces it, so the first question about any new capability is whether
it forces a v8. Neither of these does:

| | change lands in | format |
|---|---|---|
| F27 positional API ✅ | `runtime/ps2ui.c` + `preview.py` | untouched, as predicted |
| F8 layering | `packages/layout/src` | untouched |

F8 is a compiler change because the format never prevented overlap:
records carry `x, y, w, h`, `paint.js` emits them in document order,
and the runtime draws back-to-front with `gs->ZBuffering =
GS_SETTING_OFF`. A v7 blob can already *describe* a badge sitting on a
cover. Nothing in the toolchain can produce one, because `position` is
refused at the CSS stage — honestly, with a warning, which is how this
was confirmed rather than assumed:

    warning: css: line 2: property "position" not supported on this
    target; ignored

F27 is a runtime change for the same reason in the other direction:
the geometry is fixed in the blob, and the draw loop is the only place
it becomes a coordinate.

### What the absence actually cost, measured

The recreation's sidebar expands from a 31px icon rail to a 238px
panel. In the original that is a translation — the content slides right
and back. Three things were tried:

1. **A column in the flex row.** Wrong: the content reflows narrower
   instead of moving, so every card is laid out twice at two widths.
2. **A second screen composited over the first**, which is the
   documented overlay technique (`ps2ui_render` never clears, so a
   second `ps2ui_screen_set` + render draws on top). This is *correct*
   for a static overlay and the blob carries it properly — a
   `466x448` quad at `(238,0)` with `rgba=(24, 22, 16, 58)`, alpha 58
   of the GS domain's 128, exactly the authored 0.45. But it covers;
   it does not move.
3. **Baking both end states** as separate screens. Reachable today,
   and the reason F27 is a 1-effort row rather than a blocker: it
   costs a duplicate of every screen the sidebar can appear over, and
   there is no motion between the two.

The overlay in (2) also found a previewer boundary worth recording:
`preview.render()` takes a background *colour*, not a frame, so it
cannot show a two-screen composite at all. Rendering the overlay on a
transparent background returns alpha 255 everywhere, because the scrim
is baked into the quad rather than left as frame alpha. The composite
exists only on hardware or in a host that renders twice.

### And what layering cost

Two adaptations in the recreation are pure absence-of-F8:

- The hero band's title sits *below* the key art instead of on it.
  The original overlays "CONTINUE PLAYING / Cars (US) / 2 launches"
  on the image; flex has no z-stacking, so there is no way to express
  it.
- Nothing can be badged. The original puts a favourite star beside a
  title and a score in the corner of a cover; both are overlays.

Neither is cosmetic once a second UI wants them. A launcher badges
covers — "installed", "new", a progress ring — and that is the pull
rule's test: a feature enters when a real use case demands it, and one
just did.

### Admission, and what order to do them in

**Both enter under the pull rule, not on a number.** `docs/PLAN.md`
§4.6 retired RICE as the driver — *"admission from the pull rule: a
feature enters when a real use case demands it, never because it scores
well"*. F8 was on the board unscored-against for months; what is new
here is the evidence, not an estimate. The scores that used to sit in
these rows were removed in the same change, for the reason given at the
top of this file.

The use case is the demand: a shell that exists, rebuilt in this
toolchain, wanting a title over an image and a panel that moves. Two
things it could not express.

Order, when they are done: F27 first. It is self-contained, touches no
layout, and falsifies cleanly — the same blob, an offset applied, the
frame shifts by exactly N pixels with the scissor moving with it. F8
second, with its own design pass on what focus means when two
focusables overlap, a question `box.js` currently answers by refusing
the case and `lint.js` already has the code for.

Neither is in the way of Phase 4's remaining clause, which needs a
PlayStation 2 rather than a commit.

