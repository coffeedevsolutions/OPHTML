# ps2ui backlog — RICE-prioritized

Scored 2026-08-17 against the state of the toolchain at commit `2ae7003`.

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

**Scales.** `Score = (Reach × Impact × Confidence) / Effort`

* **Reach** — 0–10: share of ps2ui adopters who hit this within two
  quarters of adopting (10 = everyone, on every build).
* **Impact** — 0.25 minimal / 0.5 low / 1 medium / 2 high / 3 massive,
  per affected user.
* **Confidence** — 1.0 verified or trivially provable / 0.8 solid
  reasoning, minor unknowns / 0.5 real unknowns (usually: hardware).
* **Effort** — person-weeks for one maintainer who knows the codebase.

RICE's known blind spot is dependency structure, so after the table
there is a sequenced plan: some low-scoring items (PCSX2 harness) are
confidence multipliers for high-scoring ones and get pulled forward.

## Bugs

| ID | Bug | R | I | C | E | Score |
|----|-----|---|---|---|---|-------|
| B1 | **Textured-quad vertex RGB is in the wrong domain for GS modulate.** The GS `MODULATE` function treats `0x80` as identity for RGB exactly as it does for alpha (`Cv = Ct·Cf >> 7`), but the baker emits tint colors with full-range 0–255 RGB. On hardware every tinted glyph and nine-patch will render up-to-2× overbright and clamp: white text survives by luck, mid-tone text (`#8b94a7` metadata, `#c8cfdc` labels) washes out badly. The previewer normalizes by 255, so it *hides* the bug — the exact class of divergence the replay-the-blob design exists to prevent. Fix: emit modulated RGB in the 0x80 domain in `quads.py` (same one-crossing rule as alpha), mirror in `preview._tint`, add a cross-domain test. | 10 | 3 | 0.8 | 0.5 | **48** |
| B2 | **Baseline seam between metrics ascent and FreeType ascent.** Layout positions line boxes from `ascentPx` derived from the metrics JSON (units → px via the shared rounding rule); the atlas places glyph ink relative to Pillow's `font.getmetrics()` ascent at the render size. The two can disagree by ±1px at some sizes, nudging ink off its measured line box. Fix: bake the per-size ascent into the atlas from the *metrics* value and offset bearings accordingly; add a golden test at several sizes. | 8 | 1 | 0.8 | 1 | **6.4** |
| B3 | **GS half-texel / half-pixel sampling conventions unaudited.** Classic PS2 artifact family: sprite UVs off by half a texel, primitive coordinates off by half a pixel against the 2048-centered window, interlaced field offset. gsKit absorbs some of this (`OffsetX/Y`), not all. Everything looks right in the previewer, which proves nothing about texel centers. Needs an on-target test pattern (checkerboard atlas + 1:1 quads) and probably `+0.5` UV nudges in one place. Blocked on F1 for verification. | 10 | 2 | 0.5 | 1 | **10** |
| B8* | **VRAM budget only checked at test time, not bake time.** A UI whose atlases + patches exceed 4 MB (minus framebuffers) currently bakes fine and dies at upload. The baker knows every texture size; it should compute the worst-case VRAM footprint (including gsKit page rounding) and fail the build with a per-texture breakdown. | 6 | 1 | 1.0 | 0.5 | **12** |
| B9 | **`<img>` parses but silently paints nothing.** Until real image support (F3) lands, an `<img>` in the document should at minimum be a loud compile warning — silent drops are how people lose an afternoon. One `if` in `box.js`. | 5 | 0.5 | 1.0 | 0.25 | **10** |
| B7 | **Percentage sizes against an indefinite container silently resolve to auto.** CSS resolves `%` against definite sizes and has defined fallbacks; ps2ui treats null as auto without saying so. Either implement the CSS behavior or make it a documented compile warning. | 3 | 0.5 | 0.8 | 0.5 | **2.4** |
| B4 | **`row-reverse` / `column-reverse` only reverse order, not main-axis start.** With `justify-content: flex-start`, a `-reverse` container should pack from the main-end; ps2ui packs from main-start with reversed items (only coincidentally correct for `center`/`space-between`). | 2 | 0.5 | 1.0 | 0.5 | **2** |
| B5 | **`opacity` is per-box, not group opacity.** A container's opacity doesn't multiply into descendants, diverging from CSS. True group opacity needs offscreen composition the GS makes painful; the honest fix is inherited multiplied opacity (close enough for flat UI) plus a doc note. | 3 | 0.5 | 1.0 | 1 | **1.5** |
| B6 | **`overflow: hidden` + `border-radius` clips square.** The GS scissor is rectangular; rounded clipping would need stencil/alpha tricks. Cheap first step: lint warning when both are set on one box. | 4 | 0.5 | 1.0 | 2 | **1** |

| B10 | ✅ **Baker never checked the runtime's static table caps.** `ps2ui.h` sizes four tables (`MAX_TEXTURES` 32, `MAX_SLOTS` 16, `MAX_SCREENS` 8, `SLOT_BUFSZ` 96) and `ps2ui_load` rejects anything past them, but nothing on the host knew those numbers. An over-sized blob laid out, baked, previewed and passed every host test while being unloadable: the sample ELF's red screen with no diagnostic. Same failure shape as B1, host says fine and console says no. Fixed in `caps.py`, parsed from the header so it cannot drift. | 8 | 3 | 1.0 | 0.25 | **96** |
| B11 | ✅ **`ps2ui_slot_set` split UTF-8 sequences.** Truncation was a byte-wise `strncpy` at the slot capacity, so an accented or CJK title cut mid-character left a partial sequence the pen decoded as U+FFFD and drew as `?`. Fixed by trimming back to the last complete sequence. | 5 | 2 | 1.0 | 0.25 | **40** |
| B13 | ✅ **Charset lint fired on PlayStation face buttons.** The rule warned on every codepoint above U+24FF, which includes ○ (U+25CB) and △ (U+25B3). Every PS2 footer carries those hints, so the lint trained authors to ignore it. Now whitelists punctuation, arrows, math operators, geometric shapes and dingbats, all single glyphs with no line-breaking rules of their own. | 7 | 0.5 | 1.0 | 0.1 | **35** |
| B12 | ✅ **A slot could not be blanked.** `""` reverted to the baked placeholder because the check was `slot_text[i][0] != '\0'`, so an app with no data for a row could not empty it. `NULL` already meant revert, so `""` now means blank. | 4 | 1 | 1.0 | 0.25 | **16** |
| B14 | ✅ **Contrast lint discarded background alpha.** It read the nearest containing rect's raw RGB, so a 60%-opaque scrim scored the same as an opaque fill. A `.uib` is replayed over whatever the host app drew, so this is exactly backwards: the translucent case is the one where contrast is at risk and the one the rule could not see. Now composites the full containing chain in paint order and, when the chain still transmits, evaluates against black and white backdrops and reports the worse. | 6 | 2 | 1.0 | 0.25 | **48** |
| B15 | ✅ **Probe screen overflowed the canvas.** A seventh 178px cell in a wrapping grid sized for six pushed a third row past y=448, putting the FLEX cell and the whole footer off-screen. The linter emitted four overscan warnings that went unread; the example is meant to be warning-free so that a warning means something. Cells are 135px, wrapping 4 + 3. | 3 | 1 | 1.0 | 0.1 | **30** |
| B16 | ✅ **Scissor stack could desynchronise, corrupting the rest of the frame.** `ps2ui_render` refuses a SCISSOR_PUSH past `PS2UI_MAX_SCISSOR_DEPTH` but still popped it, so after one too-deep subtree the stack sat a level shallow and every later clip was wrong — text bleeding out of panels it never belonged to, far from the markup that caused it. Compounding it, `caps.py` never parsed the constant (the regex matched, but `FALLBACK` had no key so `caps.update` dropped it), so no stage knew the limit existed. Refused pushes now refuse their pops, the bake rejects a blob that deep naming the constant to raise, and `ps2ui-check` reports per-screen nesting. | 4 | 2 | 1.0 | 0.25 | **32** |

\* numbered to match the working notes; ordering below is by score.

## Features

| ID | Feature | R | I | C | E | Score |
|----|---------|---|---|---|---|-------|
| F18 | **Hardware bring-up checklist** (`docs/bringup.md`): ordered list of what to verify first on PCSX2/hardware — text tinting (`GSTEXTURE::Function`), B1 color domains, B3 texel centers, CLUT swizzle, alpha blend state, interlace field order — each with its expected-vs-symptom. Converts the "not hardware-verified" caveat into a runnable procedure. | 4 | 1 | 1.0 | 0.25 | **16** |
| F1 | **PCSX2 verification harness in CI.** Boot a minimal ELF that loads the example blob, renders one frame, screenshots via PCSX2's automation, and image-diffs against the previewer PNG within tolerance. The single highest-leverage credibility move: flips C from 0.5→1.0 for B1/B3/F5 and makes every future GS-path change regression-safe. | 10 | 3 | 0.8 | 2 | **12** |
| F10 | **Focus API completion.** `ps2ui_focus_set(ctx, "name")`, optional wrap-around per axis (solved at build time as extra graph edges, zero runtime cost), and an activation callback convention. Every real app needs to restore focus after a screen swap; today only `move` exists. | 6 | 1 | 1.0 | 0.5 | **12** |
| F3 | **Image support.** `<img src>` → Pillow decode at bake time → PSMCT32 (or quantized PSMT8+CLUT for flat art) textures in the .uib, sized by layout like any box. The format already carries arbitrary textures; this is mostly layout-measure + baker plumbing. Unlocks logos, save-icon thumbnails, backgrounds. | 8 | 2 | 1.0 | 2 | **8** |
| F7 | **PAL / video-mode presets.** `--canvas` exists but the CRT linter's safe-area insets and the example are NTSC-tuned. Add `--mode ntsc|pal|480p` presets driving canvas, linter geometry, and a documented runtime note on mode setup. Half of PS2 homebrew's audience is PAL. | 4 | 1 | 1.0 | 0.5 | **8** |
| F11 | **Watch mode.** `ps2ui dev`: watch `ui/*.html,css`, rebuild IR + blob, re-render preview PNG on change (optionally serve in a browser with live reload). The edit loop today is two manual commands; iteration speed is the whole pitch of HTML authoring. | 7 | 1 | 1.0 | 1 | **7** |
| F13 | **Contribution surface.** CONTRIBUTING.md (how to run all three suites, how the seams work), issue templates, and 4–6 curated good-first-issues (named colors, `text-transform`, montage columns flag, B9). Cheap, and the format specs already do the heavy lifting. | 3 | 0.5 | 1.0 | 0.25 | **6** |
| F2 | **Runtime dynamic text.** The flagship gap for the actual SD2PSX use case: a real memory-card browser lists titles read from the card at runtime, but today every string is baked. Design: bake full glyph tables (advance + UV per codepoint) per face/size — the .uib texture format already supports it — reserve `data-slot` text boxes at layout time (fixed rect, alignment, ellipsis policy), and add a small runtime pen (~100 lines: advance loop + ellipsis, no wrapping) writing glyph quads into a per-slot buffer. Keeps the no-allocation rule via caller-provided slot buffers. | 9 | 3 | 0.8 | 4 | **5.4** |
| F14 | **.uib integrity + feature flags.** CRC32 over the payload (validated by loader and Python reader) and a feature-bits field in `flags` so future additions (F2 glyph tables, F5 chains) degrade loudly, not mysteriously. Do it before third parties write .uib files. | 4 | 0.5 | 1.0 | 0.5 | **4** |
| F4 | **Multi-screen documents.** Several HTML files → one .uib with named screens sharing textures/atlases; runtime gets `ps2ui_screen_set`, per-screen focus memory, and an optional baked crossfade. Every non-trivial app has ≥2 screens; today they'd ship N blobs and duplicate atlases. | 8 | 2 | 0.8 | 4 | **3.2** |
| F12 | **Packaging.** Publish `@ps2ui/layout` to npm and `ps2ui-bake` to PyPI, plus one `ps2ui` wrapper CLI (`build`, `dev`, `fontgen`) so the quick start is two installs and one command instead of PYTHONPATH incantations. | 8 | 1 | 0.8 | 2 | **3.2** |
| F9 | **Kerning.** `fontgen` already reserves a kerning field; emit pairs from the TTF, apply in `Font.measure`/wrap and in the baker's pen with the same rounding rule, covered by a cross-language agreement test. Visible on large headings ("PS2", "Library"). | 6 | 0.5 | 1.0 | 1 | **3** |
| F8 | **`position: absolute` overlays.** Badges, dialogs, and focus-follow cursors need out-of-flow boxes. Constrained version: absolute within the nearest padded ancestor, no auto-margins, still zero runtime cost. | 5 | 1 | 0.8 | 2 | **2** |
| F17 | **Localization workflow.** Per-locale build passes (the architecture already prescribes this): string catalog extraction from HTML, per-locale bake with locale-appropriate charsets in the atlas, `ps2ui build --locale`. | 3 | 2 | 0.8 | 3 | **1.6** |
| F15 | **Gradients as baked textures.** `linear-gradient` rasterized to small strip textures at bake time, stretched by the GS. Pure polish; the mockups' thumbnails would benefit. | 3 | 1 | 0.8 | 1.5 | **1.6** |
| F6 | **List templating / scrolling regions.** Data-driven repeats (`data-repeat` on a template child) with a runtime-scrollable window over more items than fit — the full solution to "the card has 40 saves". Depends on F2; large runtime surface (scissor + per-item focus), which is why it scores below its obvious value. Revisit the score once F2 lands. | 6 | 3 | 0.5 | 6 | **1.5** |
| F5 | **Precompiled GIF/DMA chains.** The roadmap's performance endgame: bake per-state GIF packets so a frame is a DMA kick instead of per-quad gsKit calls. Near-zero CPU per frame, but the biggest hardware-knowledge item in the backlog and pointless to attempt before F1 exists to validate it. | 7 | 2 | 0.5 | 6 | **1.2** |
| F16 | **Non-Latin text.** CJK/greedy-break rules, font fallback chains, larger atlases (PSMT8 CLUT pressure). Real for localization, small audience today, large effort. Pair with F17 when demand appears. | 2 | 2 | 0.5 | 4 | **0.5** |
| F22 | ✅ **`ps2ui-check`, a validator for any blob.** `examples/channel6/check.py` asserted the right properties but had one example's focus names and slot capacities hardcoded, so nobody else's build got them. Generalized into `ps2ui_bake.check`: table caps, every index the runtime dereferences unchecked, screens partitioning the command/focus/slot tables, scissor balance per screen, both GS colour domains, codepoint-sorted glyph tables, placeholder coverage, focus reachability, VRAM. Errors mean the console misbehaves with no diagnostic; warnings mean legal but wasteful. TAP output, `--strict`, wired into both workflows. | 8 | 1 | 1.0 | 0.5 | **16** |
| F19 | **`ps2ui_unload()` and VRAM bookkeeping.** The runtime uploads once and never releases, so an app cannot swap one blob for another. Needed before a shell-and-module example is possible: the shell's UI and a module's UI cannot both be resident under a 4 MB budget. Deliberately deferred until the GS path is hardware-verified, since it changes how VRAM is managed and debugging that against an unproven renderer means debugging two things at once. | 5 | 2 | 0.8 | 2 | **4** |
| F20 | **Runtime image slots.** `data-slot` covers text; cover art discovered at runtime (an OPL-style ART folder) still cannot be shown, because textures are baked. Needs F19's VRAM bookkeeping first. | 5 | 2 | 0.7 | 3 | **2.3** |
| F21 | **Runtime visibility toggle.** `display: none` is compile-time only, so an app cannot hide a row it has no data for; today the workaround is blanking every slot in it, which leaves the panel drawn. A per-focus-node or per-element visibility bit the render loop honours. | 4 | 1 | 0.9 | 1 | **3.6** |
| F24 | **Trim geometry that cannot draw.** A `nowrap` run inside `overflow: hidden` bakes every glyph and lets the GS clip, so the channel-6 probe submits 20 quads per frame that are outside their scissor. F22 measures it; the baker could drop them at flatten time once the clip is known. Small, safe, and it shrinks the command list on exactly the data-heavy screens where it matters. | 6 | 0.5 | 0.9 | 0.5 | **5.4** |

## Security & abuse (added 2026-08-17 after CI review)

Context: the repo is public, so GitHub-hosted Actions minutes are free and
un-billable — "bombing the Actions count" is not a cost risk. Fork pushes burn
the fork owner's quota, and first-time-contributor PRs require maintainer
approval before workflows run (keep that default setting on). The real vectors
are queue-congestion noise, CI supply chain, and parsing untrusted inputs.

| ID | Item | R | I | C | E | Score |
|----|------|---|---|---|---|-------|
| S1 | **CI hardening.** Explicit `permissions: contents: read` on every workflow (default token is broader), `concurrency` groups so rapid pushes cancel superseded runs instead of queuing, artifact `retention-days` trimmed from 90, and narrowed `push` triggers (`main` + working branches) so branch pushes and their PRs don't double-run. Never attach a self-hosted runner to this public repo. | 3 | 1 | 1.0 | 0.1 | **30** |
| S4 | **CI supply chain.** Pin third-party actions to commit SHAs (tags are mutable), add Dependabot for actions updates, pin + checksum the Play! AppImage download in `hw.yml` (currently `latest`, a moving target executed in CI), and add SECURITY.md with a reporting contact. SHA pinning needs upstream SHA lookups — done at next maintainer touch. | 3 | 1 | 1.0 | 0.25 | **12** |
| S2 | **Fuzz the .uib loader.** `ps2ui_load` bounds-checks every table, but users will share blobs and themes; a libFuzzer/AFL harness over `ps2ui_load` + a stubbed `ps2ui_render` walk (plus a Python fuzz pass over `read_uib`) turns "carefully reviewed" into "mechanically hammered". Wire into CI as a short smoke pass, longer runs nightly. | 4 | 2 | 0.8 | 1 | **6.4** |
| S3 | **Resource-exhaustion limits in the compilers.** Untrusted HTML/CSS/IR (third-party themes) can request a 30000px canvas, 10k-deep nesting, or atlases that swallow gigabytes at bake time. Add hard caps with clear errors: canvas dimensions, node count, tree depth, per-bake texture bytes (the VRAM budget already bounds the output side). | 3 | 1 | 0.8 | 0.5 | **4.8** |

S1 ships immediately (this commit). If the repo ever goes **private**, minutes
become metered: narrow triggers further, confirm the Actions spending limit is
$0 (the default), and re-read this section.

## Priority order (pure RICE)

| Rank | Item | Score |
|------|------|-------|
| 1 | B1 modulate color domain | 48 |
| 2 | F18 bring-up checklist | 16 |
| 3 | F1 PCSX2 harness · B8 VRAM budget · F10 focus API | 12 |
| 4 | B3 texel conventions · B9 img warning | 10 |
| 5 | F3 images · F7 PAL presets | 8 |
| 6 | F11 watch mode | 7 |
| 7 | B2 baseline seam · F13 contribution surface | ~6 |
| 8 | F2 dynamic text | 5.4 |
| 9 | F14 integrity/flags | 4 |
| 10 | F4 multi-screen · F12 packaging · F9 kerning | ~3 |
| — | everything else | <2.5 |

Security items interleave as: S1 (30) after B1; S4 (12) with rank 3; S2 (6.4)
with rank 7; S3 (4.8) between ranks 9 and 10.

## Sequenced plan (RICE + dependencies)

**Sprint 1 — "trustworthy on hardware" (≈2.5 wk):**
B1 → F18 → F1, plus B9 and B8 as same-day wins. B1 is fixed *before*
the emulator run so the first screenshot diff is meaningful; F1 then
retro-verifies it and B3 (adding the +0.5 UV fix if the pattern test
demands it). Exit criterion: CI contains an image-diff against PCSX2.

**Sprint 2 — "usable for real apps" (≈4 wk):**
F10, F3, F7, F11, B2, F13. After this, a PAL user with logos and a
sane dev loop can build a shippable single-screen UI.

**Sprint 3 — "the flagship gap" (≈5 wk):**
F14 first (format flags before format additions), then F2 dynamic
text, then F4 multi-screen. This is the release that makes the SD2PSX
memory-card browser — the project's stated reason to exist — actually
buildable, and it is the natural `v0.2` + packaging (F12) moment.

**Later, on demand:** F9, F8, F6 (after F2), F5 (after F1 only),
F15/F17/F16, B4–B7 as they annoy someone.
