# ps2ui Foundation Plan

*rev 1.5 · 2026-08-30 · format v7 shipped · **Phases 0, 1 and 2 locked; Phase 3 open, its speed case measured away, and P3b is the whole of it** · bring-up matrix complete — steps 1–7, 9, 10 pass on SCPH-50000; 8 void pending a CRT (panel deinterlacer, with positive field evidence logged)*

*Progress lives in §6. Every phase gate is a measurement with a
falsifier in [`docs/findings.yaml`](findings.yaml), not a checkbox
someone ticked.*

What has been built, what it proved, where it stopped being one product —
and the plan that replaces score-driven feature selection with a sequenced
foundation: verify the silicon, unify the resource model, prove it with a
real application, then spend the hardware.

This document is the sequencing authority. `BACKLOG.md` remains as a defect
ledger and idea archive; it no longer drives priority (see §4.6).

---

## §1 The product, in one rule

ps2ui compiles HTML and CSS into PlayStation 2 Graphics Synthesizer draw
commands **at build time**. The console never parses, lays out, rasterizes,
or allocates. That single rule settles most design questions, and it is the
right rule for this machine: the GS has no shaders and no scene memory — it
is a rasterizer with 4 MB of embedded DRAM and enormous fill bandwidth — so
a UI that arrives as pre-solved geometry, pre-swizzled textures, and
pre-converted color domains plays directly to what the hardware is good at
and asks nothing of what it lacks.

```
ui/*.html,css ─▶ @ophtml/layout ─▶ ui.json ─▶ ps2ui-bake ─▶ ui.uib ─▶ runtime
                 Node, zero deps            Python+Pillow            C99+gsKit
                 ~2,600 lines               ~2,500 lines             ~1,360 lines
```

The audience has sharpened since the project started. The original target
was an SD2PSX / PSxMemCard virtual-card browser. The anchor use case is now
larger: a full **OPL-class environment** — landing page, combined
multi-source game library, detail sub-pages, filtered and windowed lists,
streamed cover art, layered dialogs (§5). The plan in §6 is built around
making that class of application first-class.

## §2 Foundation inventory — what exists

Twelve sprints, twenty-six shipped backlog items, 44 merged pull
requests, 20 findings under `tools/check-findings.py`.

**Capabilities (all regression-tested on the host):** hand-written flexbox;
nine-patch borders/radii; text with wrap, letter-spacing, ellipsis, and
kerning applied identically by all three pens; images with opt-in
PSMT8+CLUT palettization; `data-slot` dynamic text (UTF-8, ellipsis,
alignment, focus colors, blank-vs-revert); `data-repeat` lists with runtime
windowing; runtime visibility honoured by the command loop *and* slot
rendering; multi-screen blobs with per-screen focus memory; build-time
D-pad graph (`:focus` is paint-only; geometry change is a compile error);
anamorphic widescreen with exact display aspect in the header; CRT linter
(overscan, min font, alpha-aware contrast, charset, interlace shimmer, PAR
distortion); bake refusal over table caps / VRAM budget / scissor depth;
dead-geometry trim; Python previewer replaying the baked command list;
`ps2ui-check` standalone validator; frame fingerprint tool.

**Verification:** 69 layout, 119 baker, 125 runtime checks ×2 (modern gsKit
and the `HAS_FUNCTION=0` fallback), 24 channel6 contract checks,
`ps2ui-check` 49+61 clean. Cross-language pen agreement is tested
glyph-by-glyph (Node↔Python) and against an independent linear scan
(blob↔C). New tests are sabotage-verified. Examples build warning-free and
refresh their own screenshots.

**Format history:** v1 initial → v2 CRC-32 + feature bits + dynamic-text
tables → v3 multi-screen + images (0.2.0) → v4 display aspect (76-byte
header) → v5 kerning (font entry 16→24 bytes, feature bit 1) → v6 texture
kinds (texture entry 16→20, streamed textures, bit 3) → v7 the tint table
(colour bytes become u16 indices, slot entry 32→28, bit 4). Struct-size
changes always bump the version; unknown feature bits reject loudly. Four
of those moves landed after the 0.2.0 metadata both packages still carried,
which is what Phase 4's first item is about; `tools/check-versions.py` now
holds this line to `uib.VERSION`.

Work in flight is not listed here. A sequencing document that names
open pull requests is stale the moment it merges, and `git log` is
already the authority for what is pending.

## §3 What is not proven

**The renderer has never run on a PlayStation 2.** The loader, focus graph,
format handling, command walk, slot pen, and list machinery are covered by
250 host checks against a stub gsKit. The gsKit calls themselves have
produced pixels only under Play!, an HLE emulator that is not a hardware
oracle.

**Play! characterisation (recorded, not diagnosed):** Play! 0.7.2 renders
the clear, unblended sprites, and blended alphas 0x20/0x40/0x60 with
composites matching the blend equation exactly. Alpha **0x7f and 0x80
rasterise wearing the previous primitive's color**. 0x80 is what every
opaque quad carries — hence a captured UI frame 92.8% black with text
intact. **This inference was correct and is now confirmed.** It was not
Play!'s HLE: a SCPH-50000 does the same thing, because nothing in
`runtime/` had ever written the GS `ALPHA` register and gsKit's default
inverts it. With the equation asserted, the same capture returns 52.8%
`#0a0e1a` against an expected 58.6% and RMSE 22.89, down from 72.89.
Bring-up steps 3/4/5 passed under it; step 2 did not. Silicon has now
answered: it was **our GS state**, not Play!'s blend HLE. Stopping the
chase inside Play! was the right call — the emulator could not have
settled it, and the fingerprints kept from that run are what made the
hardware result recognisable the moment it arrived.

That gap is closed. Everything downstream of Phase 0 was provisional
against it and no longer is; step 2 passes on a SCPH-50000.

## §4 The cohesion audit

The critique that prompted this document: *"a lot of features glued
together and less like a cohesive product."* Confirmed. Not bugs — the
shape of a system grown feature-by-feature without a resource model.

**4.1 Fixed maxima instead of a working set.** The context is 3,240 bytes
under the host test stub — and larger on the console, since the stub's
`GSTEXTURE` is a deliberately minimal subset of gsKit's. The exact
number is not the point; where it comes from is. Almost none of it
derives from the blob it loaded:
`gs_tex[32]` 1,536 B, `slot_text[16][96]` 1,536 B, hidden bitmap 32 B,
screen focus memory — five independent ceilings
(`MAX_TEXTURES` 32, `MAX_SLOTS` 16 × `SLOT_BUFSZ` 96, `MAX_HIDEABLE` 256,
`MAX_SCREENS` 8, `MAX_SCISSOR_DEPTH` 8) with three distinct failure
behaviours. A blob knows its own sizes; the context should be sized by the
blob from a caller-provided arena, the constants demoted to validation
limits.

**4.2 Slot storage diverged from its own design.** F2's design note keeps
the no-allocation rule "via caller-provided slot buffers." What shipped
puts the storage inside the context, sized by the ceiling — channel6
already uses 15 of 16. The specified model is correct; Phase 1 restores it.
*[Phase 1: half restored, half re-argued. The ceiling is gone and each
slot is sized from its declared capacity. Borrowing the caller's
string is declined on the evidence — 3.4 KiB saved against a
use-after-free rendered as glyphs.]*

**4.3 No residency model.** `vram.py` budgets at bake; the runtime uploads
once and has no concept of residency. Fine for a fixed overlay,
disqualifying for streamed cover art — and streaming needs a *static
reservation*, not the general unload problem the backlog had gating it.

**4.4 Layering works by accident.** `ps2ui_render` never clears, so two
`screen_set`+`render` pairs in one frame composite (measured: 375 + 255 =
630 prims, focus routing correct). A working dialog technique that is
undocumented, untested, and discovered by experiment. Useful behaviour must
be a contract or the first innocent refactor breaks it.

**4.5 Three pens, held together by tests.** The glyph pen exists in three
languages, agreement enforced by test suites rather than structure. This is
an accepted cost of the replaceable-stage architecture; the rule is
procedural (§8, I2): no pen change lands in fewer than all three plus the
agreement tests.

**4.6 The mechanism: RICE did this.** Independent scoring always pulls the
locally valuable feature and systematically selects against architectural
work (high effort, diffuse reach, low confidence). Twenty-six defensible
items, no resource model. **RICE is retired as the driver.** Sequencing
comes from the phase gates in §6; admission from the pull rule: a feature
enters when a real use case demands it, never because it scores well.

## §5 Use cases, anchored

| UC | Application | Status |
|----|-------------|--------|
| UC-1 | SD2PSX / virtual memory-card browser | built (memcard example) |
| UC-2 | Channel-style game browser over a game frame | built (channel6 example) |
| UC-3 | **OPL-class environment** — landing page; combined HDD/USB/network library; detail sub-pages; Metacritic filters; recently-played / continue-playing; streamed cover art; dialogs; themes | **anchor — drives Phases 1–2** |
| UC-4 | General homebrew overlays and dashboards | served by the same foundation |

**UC-3 demand map:** screens/sub-pages/layering — works, layering must be
formalized (§4.4). Combined library — app-side by design (ps2ui shows
lists; the app owns data and device I/O). Hundreds of games — list
windowing shipped. Filters and dynamic views — shipped mechanics
(`list_set_count` + `slot_set`). Rows×fields at library scale — **blocked
on the 16-slot ceiling → Phase 1 working set**. Streamed cover art —
**blocked, no mechanism → Phase 1 texture slots**. Dialogs/badges —
layering + pull F8. Themes — CLUT swap, Phase 3. Full field rate at
library scale — measure in Phase 2, chains in Phase 3 if the numbers
demand.

## §6 The plan — phases and gates

Sequence replaces scoring. A phase is done when its exit gate is true, not
when its task list is empty. Work inside a phase reorders freely; the
phases do not.

### Phase 0 — Verify the metal

Run `docs/bringup.md` on real hardware and/or PCSX2 with a real BIOS.
**Ten** ordered steps, not nine — step 10 (display aspect) was added
after this section was first written.

**Done, on a SCPH-50000 (NTSC, FMCB, USB):**

- **Step 1 — boot and clear: PASS.** ELF load, dmaKit and gsKit init,
  video mode accepted, framebuffer flip, clean return to the browser.
- **Step 2 — solid quads and the blend unit: PASS, after finding a
  fault.** Alpha ran exactly inverted: nothing in `runtime/` had ever
  written the GS `ALPHA` register and gsKit's default swaps the
  operands, so effective coverage was `128 - As` and every quad the
  format calls opaque composited to background. Fixed in
  `ps2ui_render`, fenced by two runtime checks.
- **The Play! 0x7f/0x80 question: resolved.** Not HLE inaccuracy. Real
  silicon does the same thing, for the reason above.
- **The deliberately clipped probe quad** (deferred from PR #15
  review): landed, and it needed the blend fix first — at alpha `0x80`
  it could not have appeared whether or not the scissor worked.
- **Step 10 — display aspect: characterised.** 4:3 pillarboxed into a
  16:9 panel, which is correct behaviour.

**Left:** steps 3-9 — CLUT upload and CSM1 swizzle, text tinting and
its `HAS_FUNCTION=0` fallback, modulate domain, texel centres via the
test card, scissor nesting, interlace field order, VRAM pressure. The
bench is now cheap to re-enter: the drive works, `probe.elf` runs, and
the loop has been done once end to end.

> **Exit gate:** all ten steps pass on at least one real PS2; hardware
> confidence multipliers flip to verified; the "not hardware-verified"
> caveat leaves the README. **Met, with one recorded asterisk** — steps
> 1–7, 9 and 10 pass on the SCPH-50000; step 8 is void on an LCD bench
> panel whose deinterlacer erases the rule flicker while the 1px-checker
> shimmer proves the fields differ. The step stays open for a CRT and
> does not hold the phase: it verifies the CRT linter's hairline advice,
> not the renderer. **Phase 0 is locked** — six findings, F-001 to
> F-006, and F-011 kept deliberately as `overturned`.

### Phase 1 — One resource model

The §4 rework, shipped as **one deliberate format move (v6)**. Designed
in full in [design-v6-resource-model.md](design-v6-resource-model.md),
written before implementation so the argument can be attacked cheaply;
that document also records what would falsify it.

1. **Blob-declared working set.** The blob states its table sizes;
   `ps2ui_arena_size(blob)` tells the app what to hand `ps2ui_load`; the
   context stops carrying `MAX_*`-sized arrays; the `#define`s become
   validation limits.
2. **Texture slots as a first-class kind: baked, streamed, or absent.** A
   streamed slot is declared in HTML, sized by layout, reserved
   page-aligned in VRAM at bake. At runtime the app hands ps2ui
   already-encoded texels (`ps2ui_tex_set(ctx, "cover", data)`) from HDD /
   USB / Ethernet — upload into a fixed reservation. No allocator, no
   residency tracking, no parsing. Supersedes the old F19→F20 dependency:
   streaming needs a reservation, not an unload. Full unload stays parked
   until a shell-and-module use case pulls it.
3. **Slot text joins the working set.** App-owned storage bound to the rows
   live in a list window — the model F2 specified. The 16-slot ceiling
   stops existing as a concept. **[shipped, one half declined]**
   `PS2UI_MAX_SLOTS`, `PS2UI_MAX_TEXTURES` and `PS2UI_MAX_SCREENS` are
   deleted; a legal count is now bounded by the blob's own size and by
   arena arithmetic that refuses rather than wraps. The UC-3 fixture
   bakes and loads unmodified for the first time: 121 slots, and an
   arena of roughly 8 KiB that `fixtures/opl-scope/README.md` measures
   and now checks against the blob. Borrowing the caller's string rather than copying it
   is declined with the numbers written down — see
   design-v6-resource-model.md, "Slot storage: copied, not borrowed".
4. **Composition becomes a contract.** Document and test that render
   composites over the existing frame; define the overlay idiom, its focus
   routing, and its interaction with visibility. **[shipped]** The
   no-clear guarantee is stated on `ps2ui_render`, in the README with a
   worked frame loop, and in `format-uib.md`; input follows the last
   `screen_set`; 23 runtime checks fence it, including counters in the
   stub for clears and for the residency ageing tick, because the
   primitive sum alone survives either being moved into render. No `ps2ui_overlay_push` — the idiom, as the
   design leaned, with the absence recorded as a decision.

API breaks ride along (e.g. the `visible_get/set` error conflation from the
PR #16 review). One migration note; examples re-baked; v5 and earlier
rejected loudly.

> **Exit gate:** both examples run behaviourally unchanged on the new
> model; the context contains no ceiling-sized arrays; a demo streams a
> cover into a reserved slot on hardware; v6 documented with v5's rigor.

> **Gate met. Phase 1 is locked.** All four items shipped, and the
> hardware clause closed at bench S9 on a SCPH-50000 (HW #260):
> `docs/bench-phase1.md`.

The hardware clause was the only thing between Phase 1 and Phase 2, and
it was not a formality. `ps2ui_tex_set` hands the GS memory the EE
wrote through a write-back cache the GIF cannot see — the fault class
#40 was, and the one emulators model least well.

It also closed the sampling defect [F-033], which had survived months,
four pull requests and every host renderer this project owns. The chain
that killed it: S7a eliminated both original hypotheses; ladder v1 (S8)
found the power-of-two signature but its bias arm **could not fail**; a
`+0.5` fix shipped on that dead arm and was caught by the emulator
gate; ladder v2 (S10) measured the real magnitude at 1/16; and S9
confirmed it on the *shipping* renderer rather than a purpose-built
card [F-019, F-020, F-021].

`+0.5` was the worst possible first guess and not by chance: it is the
exact tipping point at which `floor(u + b + i + 0.5)` stops equalling
`u + i`, so it is the one bias value that changes the result on an
exact interpolator. Every host renderer here is exact. Only the GS is
not [F-011:historical].

### Phase 2 — Prove it with the OPL-class app

Build the UC-3 skeleton as `examples/opl-env`: landing page, library with
windowed list and streamed covers, detail sub-page, one layered dialog, a
filter view — dogfooding every Phase 1 mechanism at realistic scale, with
the existing OPL theme as reference. Every gap found is filed as a
foundation defect, not a feature idea. `position: absolute` (F8) gets
pulled here if the dialog idiom needs it. Measure frame time, prim counts,
VRAM footprint, blob size.

> **Exit gate:** the skeleton runs at full field rate on hardware,
> streaming covers while scrolling a windowed library; measurements
> written down.

Broken out, because three of the gate's four clauses are about the
environment *running* and the first slice only proves it bakes:

1. **The environment exists, bakes and loads.** **[shipped]**
   `examples/opl-env`: six screens, 137 slots, ten streamed texture
   slots, one overlay. 269,824-byte blob, 7,319-byte arena for the
   whole environment, VRAM 336 KiB inside a 736 KiB budget. (Those
   four figures moved at P3b-6 and again when the readout went on
   every screen; `tools/check-example-figures.py` holds the README's
   copy to the blob, and this one is now current with it.) Carries the
   `examples/` contract -- warning-free under `--strict`, screenshots
   refreshed by building, `check-blobs` with no exemptions -- and CI
   runs all three, which the first version did not.
2. **A runtime driver.** **[shipped — #63]** `oplenv.elf`
   (`PS2UI_SAMPLE_OPLENV`): loads the environment, scrolls the library
   on a timer, moves focus with the selection, and writes its own
   measurements to a slot on screen — so a photograph of the screen
   carries the reading, rather than a serial line nobody at a bench can
   read.
3. **The windowed library.** **[shipped — #63]**
   `examples/opl-env/window.h`, pure C89 with no PS2 headers, so the
   windowing logic is host-testable and fenced. Scrolling rebinds slot
   text and streams covers into the fixed reservations under motion —
   the two mechanisms had each been exercised alone and never together.
4. **Measure on hardware.** **[shipped — HW #260 and #261]** Two
   sittings, `docs/bench-phase2.md`. Four findings came out of them:

   | | reading | finding |
   |---|---|---|
   | scroll cost | `up28224`, exact against the reservation model | F-032 |
   | field rate | 16.68 ms, no dropped field past title 250 | F-034 |
   | COP0 rate | settled at 294.912 MHz as a side effect | F-035 |
   | EE headroom | 2.2 ms of a field, 13.5% | F-036 |

   The first sitting also produced the phase's sharpest lesson: its
   16.73 ms reading was the *field period wearing a frame-time label*,
   because the timer spanned `gsKit_sync_flip`. Stable, plausible,
   photographed, and unable to tell a saturated EE from an idle one.
5. **File the gaps.** **[ongoing — the reason the phase exists]** Three
   from the first build: a runtime test harness that segfaulted on any
   blob but one, single-line slots against a two-line dialog body, and
   `--strict` catching a 12px focusable. Eight more since:

   - a frame timer measuring the wait instead of the work (#64)
   - `-fsyntax-only` structurally blind to `-Wunused-function`, so the
     host check could not see a warning class the ELF build treats as
     fatal (#63)
   - a fence that never ran, because `window.h` was not a make
     dependency and three sabotages passed against a stale binary (#63)
   - `EE_HZ / 1000000u` truncating to 294, a +0.310% bias that had been
     misfiled as clock error (#64)
   - `re.search` stopping at the first match, leaving the timing fence
     open to regression-by-addition (#64)
   - a README serving as a finding's instrument, with nothing reading
     the blob header back into it — three figures drifted through two
     pull requests and a phase lock (#65)
   - a runbook telling readers to photograph the one reading its own
     finding says is confounded (#65)
   - `git checkout -- <file>` destroying uncommitted work four times
     during falsification, now fixed by keeping git out of the restore
     path entirely (#64)

> **Gate met.** All five clauses. The skeleton runs at field rate on a
> SCPH-50000 while streaming covers through a scrolling windowed
> library, and the measurements are in `docs/findings.yaml` with
> falsifiers attached. **Phase 2 is locked** (#65).

`position: absolute` (F8) was **not** pulled: the overlay centres with
flex and needed nothing. It stays in the pull lane.

### Phase 3 — Spend the hardware

Optimization against Phase 2's numbers, not vibes. **Phase 2's numbers
are now in, and they reorder this phase.** [F-036]

The EE spends 2.2 ms of a 16.683 ms field — 13.5%, with about 14.4 ms
unused and not one dropped field past title 250. Precompiled chains
optimise EE display-list building. There is no EE display-list problem.
Best case the headline item of this phase saves two milliseconds out of
fourteen already idle, on a loop that is vsync-locked and therefore
cannot go faster.

That does not make chains worthless — they buy headroom for content
Phase 2 never drew, and the argument for them was never only speed. It
makes them **unjustified until something is measured that they would
help**, which is the rule this phase opens with.

What has not been measured is the GS's **share** of the field. Not GS
time outright: `gsKit_queue_exec` blocks on the previous frame's FINISH
before sending the chain, so a GS over budget would surface inside `ee`
and trip `m`, and neither happened [F-034]. Between `ee` at 13.5% and
`m0`, GS time is bounded below a field. What those readings cannot do
is divide it — 10% GS and 90% GS are indistinguishable from them, and
the two lead to opposite plans. Until the share is known, every item
below is a guess about which resource is scarce:

0. **P3a — the GS's share of the field.** **[shipped — #66, answered at HW #262]** Read the clock after
   `gsKit_finish()` rather than after vsync. Smaller than it sounds:
   `gsKit_queue_exec_real` has *already* appended the FINISH token
   (`gsCore.c:582` at 43122eb) and cleared CSR (`:594`) before sending
   the chain, so the instrument is one `gsKit_finish()` and one clock
   read straight after `gsKit_queue_exec`. **Do not call
   `gsKit_set_finish` yourself** — that puts two FINISH tokens per
   frame in the chain.

   **It needs a falsification arm before its number gates anything.**
   `gsKit_finish()` is `while(!(GS_CSR_FINISH));` (`:124-127`) — it
   spins and does *not* clear; gsKit clears at `:594`. Any hand-rolled
   arm/wait that forgets `GS_SETREG_CSR_FINISH(1)` leaves the bit
   latched, and every later wait returns instantly: a GS occupancy of
   0.00 ms, every frame, forever. That reads as *"the GS is idle, so
   chains are pointless"* — which is the conclusion this section
   already leans toward, reached by an instrument that stopped
   measuring after frame one. This project's own defect class, aimed
   at the phase's gating measurement.

   So P3a ships with a fill-heavy arm: a few full-screen alpha-blended
   quads, and the number is **required to move**. If it does not, the
   instrument is latched, not the GS idle.

   Ship a peak-hold `ee` alongside it, so the scroll frame is readable
   rather than smeared into a 1-in-30 mean [F-036] — one sitting, both
   numbers.

   **It gated the rest of the phase, and the gate has now returned an
   answer.** [F-037] Bench S12, HW #262: `gs` 0.93 ms, **5.6% of a
   field**. The arm moved it to 3.22 for eight full-screen blended
   sprites — 1.002 Gpix/s, which is **84.9% of the part's 1.180 Gpix/s
   blended peak** (16 pipelines at 147.456 MHz, halved by the
   read-modify-write) — and moved `ee` by +0.00. A latched bit reads
   0.00 forever; a broken instrument does not land within 15% of a
   spec sheet.

   | | of a field |
   |---|---|
   | EE | 14.4% |
   | GS | 5.6% |
   | **together** | **20.0%**, 13.34 ms unused |
   | worst photographed frame | 27.5% |

   **Confirmed at HW #263 by a five-point sweep** [F-039]: predicted
   from a single delta, measured to one print unit on every point,
   1.002 Gpix/s with r² = 0.999998. A mis-anchored clock cannot draw a
   straight line whose slope is the part's fill rate.

   **So Phase 3 is not about speed.** The branch that said "re-scope
   toward capability" is the one that fired, and the items below are
   re-ordered accordingly. This is the outcome the phase was written to
   make possible: an optimisation phase that measured first and then
   declined to optimise.

Then, in an order P3a decides:

1. **P3b — theming.** **Now the phase's lead item**, having been the
   only one not gated on P3a: it buys capability rather than speed,
   which is the half of the phase that survived the measurement.

   **The plan called this "CLUT-swap theming" and that is the smaller
   half** — see `docs/design-p3b-theming.md`. The mechanism is real and
   measured: gsKit re-sends a palette without its texels, 1,024 bytes
   per drawn texture, lazily [F-041]. But a UI's colour does not live
   in its palettes. In opl-env as it stood when this was written —
   1,302 commands, before P3b-6 turned the rounded boxes into coverage
   pairs and took it to 2,158 — 997 carried the identity tint, and
   every panel, border and background was an untextured quad whose
   colour is a baked `r,g,b,a`. A CLUT swap cannot reach any of it.
   The ratio is the argument and it survived the change; the counts
   are a snapshot and are dated here so they do not read as current.

   What the numbers say instead: a UI's colour is a tiny set repeated
   thousands of times. So a theme is a **tint table** — commands store
   an index, the table is a few hundred bytes, and it reaches every
   command rather than only textured ones. The CLUT swap stays
   alongside it, for palettized art the table cannot reach.

   **The design's own adversarial pass then took two claims off it.**
   The blob does not shrink: `ps2ui_cmd` is 32 bytes with `pad0[6]`,
   and the freed colour bytes land in padding that exists to reach two
   qwords. And entries must key on **role**, not value — `#7c9be0` is
   written by nine separate declarations in opl-env, so deduplicating
   by colour would silently fuse nine theme slots into one. The count
   is 81 rather than 9, which is still 324 bytes, and the two bytes the
   struct frees pay for the focus-recolour index that was an open
   question.

   Design first, as with v6. **The slices, and where they stand:**

   | # | slice | state |
   |---|---|---|
   | P3b-0 | the CLUT-swap mechanism: `ps2ui_clut_set`, measured | **done** (#70, F-041) |
   | P3b-1 | the tint table format (v7) | **done** |
   | P3b-2 | `ps2ui_theme_set`, and a hand-built two-row blob to exercise it | **done** |
   | P3b-3 | `var()` in the CSS parser, and tints keyed on the **name** | **done** |
   | P3b-4 | the baker writes a second row; `PS2UI_FEAT_ROLE_TINTS` is finally set | **done** |
   | P3b-6 | rounded boxes stop premixing their colour, so a theme can reach them | **done** (F-043) |
   | P3b-5 | DX: the palette printed with names, `--strict` on a bare literal in a themed UI, the lints run over every theme | **done** |

   **P3b-5's first item split across two tools, because the format
   made it.** The design asked `ps2ui-check` to print "index, value per
   theme, and the declaration that produced it". It cannot: a tint
   entry is four bytes of colour, and the `var()` name is a build-time
   concept that never reaches the blob, since the runtime selects a
   theme by index and has no use for a name. So `ps2ui-bake --tints`
   prints the names as it writes them and `ps2ui-check --tints` prints
   what a loader actually finds. Read together they answer "why did
   this not change colour"; either alone answers half of it.

   **And linting the themes exposed that slot text was not linted at
   all.** `paint.js` emits no static command for a `data-slot` — its
   glyphs are drawn on the console from the slot table — and `compile`
   only ever handed `commands` to the linter. Same colour, same
   background, same geometry as static text; the only difference was
   the attribute. opl-env is **137 slots**, which is every title, count
   and telemetry line in the environment.

   Fixed by splicing a linter's-eye view of each slot into the command
   list *at the index it would have painted at* — appending would let a
   rect drawn on top of the slot into its contrast chain — with two
   commands per slot, base and focus, because a slot has two colour
   vectors and the focused one is the seam that has been the gap in
   #70, #72 and #74.

   **What that turned up went to the bench and came back settled.**
   opl-env's entire secondary text layer sits below the 14px couch
   floor — row titles at 13, subtitles and counts at 11, detail fields
   at 12, **97 instances across six screens** — and none of it ever
   warned, because all of it is slot text. The floor was not being met;
   it was being missed. `--min-font-size 11` keeps the rule live
   (anything smaller still fails) and records the value where a reader
   will look.

   **S14 then read it off the screen** [F-046]. Every oplenv ELF
   photographed that sitting renders the whole layer, and all of it was
   legible on an SCPH-50000. So the 14px floor is wrong for secondary
   text at this density, and 11 has a photograph behind it rather than
   being the number that makes the build pass. Provisional on one point
   only: the bench panel was within arm's reach, and "from a couch"
   means two or three metres. One photograph from the sofa closes it.

   Worth noting where the blind spot showed: `opl.css`'s comment on
   `.dlg-btn` says *"`--strict` enforces a floor on FOCUSABLE text"*.
   The rule in `lint.js` has always applied to all text. It read as
   focusable-only because every non-focusable small string in the file
   was a slot, and therefore invisible.

   The third item was not in the original plan. It came out of P3b-6:
   `contrast` and `ntsc-red-bleed` read colours, a theme moves colours,
   and the lints only ever saw row 0 — so a UI readable in `:root`
   could be unreadable in `@theme light` with every check in the
   repository passing. The blob would be correct, the screenshots
   correct for the row they render, and the failure discovered on a
   television. opl-env's light theme now passes contrast on all six
   screens, which nothing had checked before.

   **P3b-6 was not in the plan, and P3b-4 is what found it.** The
   design said "every panel, border and background is an untextured
   quad whose colour is a baked `r,g,b,a`". It counted `background:`
   declarations. What the baker actually emitted was a **nine-patch**
   for every box with a `border-radius` — fill and border rasterized
   together into one RGBA texture, drawn with an identity tint. In
   opl-env that is 107 rects against 6 untextured quads, so the first
   working theme recoloured the text and left every panel dark. Colour
   in texels is colour a tint table cannot reach.

   The fix makes a patch a **coverage mask** — PSMT8 on the shared
   coverage CLUT, exactly like a glyph atlas — and moves the colour
   into the vertex tint, one layer for the fill and one for the border
   ring. Both become tint-table entries, which is to say things a theme
   can move.

   | opl-env | before | after |
   |---|---|---|
   | patch textures | 11, keyed on colour too | **4**, keyed on `(radius, borderWidth)` |
   | their VRAM | 88 KiB | **32 KiB** |
   | commands (`n_cmd`) | 1,302 | 2,158 |
   | of those, painting | 1,244 | 2,100 |
   | tint entries | 13 | 28, of which 27 move |

   **The VRAM saving is a property of the stylesheet, not of the
   mechanism**, and opl-env was the wrong example to generalize from.
   Premixed costs one texture per distinct `(radius, bw, fill, border)`
   — call it C. Coverage costs two per distinct `(radius, bw)` — call
   it G. The split wins when C > 2G, and that rule predicts all three
   shipped examples including the one it says loses: opl-env 28 → 21
   textures, memcard 19 → 11 (30% → 21% of budget), channel6 23 → 25
   (47% → 50%) because it draws six rounded geometries and paints each
   about 1.5 times. The justification is that colour becomes reachable
   at all; the VRAM followed in two examples and opposed the third.
   F-043 has all of them.

   The rejected alternative was a per-theme CLUT swap — P3b-0's own
   mechanism, and the obvious reading of "the two compose". It would
   have taken the same blob to **176 KiB** and added 88 KiB per further
   theme, because a CLUT costs a full 8 KiB page whether it colours
   64 KiB of texels or the 81-121 bytes a palettized patch holds.
   F-043 has the arithmetic and the rule it generalizes to.

   **What this costs, stated plainly.** Nine-patch draws roughly double
   (a fill layer of nine cells and a ring of eight; the ring's centre
   cell holds no coverage and is skipped), so opl-env's command count
   rises 66%. And every rounded box's colour now passes through the GS
   modulate domain's 129 levels, where premixed texels were exact.
   Measured over all six default-theme screenshots against `main`:

   | delta | pixels | share |
   |---|---:|---:|
   | 1 | 632,885 | 36.8% |
   | 2 | 35,020 | 2.0% |
   | 3 or more | 35,696 | 2.1% |
   | worst | 40 | 4 px, in `detail` |

   Not visible at 1:1, and the tail is thin and bounded -- but the
   first version of this paragraph said "four corner pixels by up to
   24", which was `library.png` alone read as far as its top bucket
   and no further. It is off by 35,692, and it is precisely the
   sentence a reviewer uses to accept a rendering change WITHOUT
   looking. Measure every image or claim only the one you measured.

   **Sitting A is unaffected** — its ELFs are frozen at `914e20c` — but
   this moves the command count enough that the next EE baseline is a
   new one, not a continuation.

   **A gap P3b-5 closed.** The layout lints ran over the IR's row 0 and
   nothing else, so a theme could ship unreadable text with no check
   saying so. They now run over every row, deduplicated by message
   against row 0 — the geometry lints are byte-identical in every theme
   and would otherwise be reported once per theme.

   ### Bench sequencing: two sittings, not one delayed one

   **The open bench queue is entirely P3a's, and none of it waits on
   P3b.** The EE sweep, F-040's falsifier and the `-fill2` outlier
   measure per-render EE cost, frame 0's field spill, and an
   unexplained `gs^` reading. P3b-4 adds a second tint row — bytes in
   the blob, no change to command count or per-frame work — and P3b-5
   is `ps2ui-check`, previewer and `--strict` output with no runtime
   path at all. Neither moves a number the queue reads.

   **Waiting would make the sweep worse, not better.** Its predictions
   come from F-036 and F-037, measured at v6 with colour inline. Every
   blob change since is drift between the baseline and the thing being
   compared to it: v7 put colour behind an indirection, and P3b-3 took
   opl-env from 12 tints to 13. The N=0 point is already doing double
   duty as the first check that v7's indirection cost nothing — a
   question the whole tint-table design quietly assumes the answer to
   and nobody has measured. Adding two more slices of drift before
   reading it buys nothing and costs the comparison.

   **And P3b earns its own sitting, later, for a different question.**
   The exit gate says a UI recolours every colour it draws from a theme
   chosen at runtime. That is not a host-verifiable claim: the host
   stub counts primitives and the previewer renders from the same
   values the baker wrote, so both would agree with a runtime that
   recoloured nothing on a television. It needs a console and two
   photographs, and it needs a blob with two rows — which is P3b-4.

   | sitting | when | what | outcome |
   |---|---|---|---|
   | **A** | done, S14 on hw #309 | the EE sweep, F-040's falsifier, the `-fill2` outlier | all three answered |
   | **B** | needs a driver theme binding | a theme switch on hardware — P3b's exit gate, and the one claim in the phase a host cannot check | not yet buildable |

   **Sitting A is done and it answered all three.**

   - **The EE sweep** [F-044]. One `ps2ui_render` costs **2.44 ms of
     EE and 0.78 ms of GS**, 3.22 ms in all, about 19% of a field. The
     driver's own per-frame work is 0.08 ms. `m` confirmed it
     independently — clean to N=3, then `m29@270` at N=4 where the
     peak frame needs 18.08 ms of a 16.683 ms field, with 270 = 9 × 30
     against a `SCROLL_EVERY` of 30, so the first miss is a scroll
     frame. The *count* is undivided: no telemetry line carries a frame
     index, so 29 cannot yet be told from near-margin jitter.
   - **F-040 is overturned.** Its own falsifier fired: `m0` at every N
     with the boot phase zeroed, where S13 read `m1@0` at N=4, 8 and
     16. Frame 0 never spilled a field; the clock had started at an
     arbitrary phase into one.
   - **The `-fill2` outlier reproduces** [F-045]. Three windows across
     two sittings at ≈0.075 against 0.21–0.23 everywhere else, so the
     unlucky-window explanation is dead and it is now a real anomaly
     owed a mechanism.

   **F-039 was also reconfirmed independently** — refitting S14's five
   points gives 0.9187 + 0.2869/layer against S13's 0.9205 + 0.2861,
   agreement in the fourth digit, and a fill rate of 0.999 Gpix/s. The
   instrument was sound at S13; the inference drawn beside it was not.

   **Sitting B is unblocked.** `oplenv-theme.elf` cycles the tint rows
   on a 240-frame timer, so a photograph shows a theme chosen at
   *runtime* rather than baked in — which is the whole of the claim a
   host cannot check.

   Self-driven rather than pad-driven, and not for convenience: this
   sample loads no IOP service at all, and adding padman would change
   the boot path the timing arms exist to measure. A timer proves
   runtime selection exactly as well as a button. Behind its own flag,
   so the theme switch is not in the measured path — F-044's lines were
   fitted without it.

   **The next sitting's numbers will not match F-044's, and that is
   P3b-6 rather than a regression.** It took the library screen — the
   one every timing arm renders — from 414 records to 694. So the
   clear-arm prediction is written as a **difference**: photograph
   `oplenv.elf` and `oplenv-clearopaque.elf` in the same sitting and
   subtract, expecting ~0.14 ms. An absolute "0.78 or 0.92" is anchored
   to a blob that no longer exists and would read as *neither* even if
   the mechanism is exactly as described — the cleanest experiment in
   the queue returning a null result for a bookkeeping reason. `p`
   announces it on the first photograph: S14 recorded `p595`, and 595
   is unreachable on a screen that gained 280 records.

   **The readout gained the two fields the last sitting proved it
   needed.** `gs^` now carries `@frame`, which is the instrument F-045
   named as its own next step — its one surviving explanation is that
   the peak-hold is not catching a scroll frame, and that cannot be
   tested without knowing which frame it caught. And line 2 gained
   `n`, the run's frame count, without which `m29@270` divides
   nothing: 29 misses fits *every scroll frame from 270 on* and fits
   *near-margin jitter* equally well, and only `29 ≈ (n − 270)/30 + 1`
   tells them apart.

   Three sittings running, three arguments settled by an instrument
   rather than a theory. That is now the phase's most reliable move.

   **P3b-3 and P3b-5 swapped, and the old P3b-3 is gone.** The plan
   said role-keying meant "the IR carries each colour's declaration
   site". That is sound for the runtime and unusable for an author.
   Measured on `opl.css`: **82 colour declarations, 26 distinct
   literals, 12 baked entries.** Declaration-site keying makes that 82
   table slots addressed by file and line, so a theme file is 82
   anonymous positions — correct, and nobody can write one.

   **The role is the name the author chose.** `var(--focus-ring)` is a
   role; `#7c9be0` written in nine places is nine coincidences. So
   `var()` is not the authoring sugar the plan filed it as, it is the
   mechanism: a restricted form (`:root { --name: #hex }` plus
   `var(--name)` at use sites, no fallbacks, no per-element override)
   is what makes a second row sound.

   **Bare literals stay value-keyed, and that is the author declining
   to theme them.** They collapse across the UI exactly as they do
   today, no theme can move them, and the blob renders correctly under
   every row — it simply does not recolour those pixels. That turns
   `PS2UI_FEAT_ROLE_TINTS` into a sharper claim than the plan had:
   *every tint a theme can move is keyed on an authored name.* And it
   gives `--strict` a real job in P3b-5, which is to say so when a
   multi-theme UI is still painting with literals.

   **P3b-3 measured what role-keying actually separates, and it was not
   what the design predicted.** `opl.css` was converted to `var()` as a
   pure refactor — 82 tokens, 27 names, and not one pixel moved. The
   table went **12 → 13**, and the split was *not* `#0b0f16`, the
   two-role literal the design pointed at. That one was already two
   entries: a background is a QUAD and takes flat shading,
   `(11,15,22,128)`, while the same literal as text is a TEXQUAD and
   takes the modulate domain, `(6,8,11,128)`. **The GS colour-domain
   split had been holding the two roles apart by accident** — value
   keying was right there for a reason that has nothing to do with
   roles, which is this project's own defining failure mode wearing a
   friendly face.

   What role-keying did separate is a role from a **non-role**:
   `#ffffff` as text modulates to `(128,128,128,128)`, exactly the
   identity tint the nine-patch emitter uses on untinted art. Fused,
   a theme touching `--ink-max` would have tinted every nine-patch in
   the environment.

   **P3b-1 shipped the format and one correction to the design.** Every
   colour count in the design doc was one too high: the script behind
   them counted the `(0,0,0,0)` in a scissor command's colour field,
   which is not a colour and which no draw reads. The shipped tables are
   12 entries (opl-env), 33 (channel6) and 9 (memcard).

   **It also ships one refusal rather than one caveat.** Role-keying
   needs the layout package to carry declaration sites, so P3b-1 keys on
   the resolved value — which is *exact* at one theme, because there is
   nothing to diverge into. The combination that would be wrong is
   `n_theme > 1` without role-keying, and `ps2ui_load` returns
   `PS2UI_ERR_TINTS` for it. A blob that cannot be recoloured correctly
   does not open, rather than opening and recolouring nine unrelated
   things together.
2. **P3c — page-aware atlas packing.** Pack to 8 KiB page boundaries
   (64×32 CT32, 128×64 T8) to minimise TBP switches and make streamed
   reservations exact. **Gate did not open** [F-037]: the GS is at
   5.6%, so there is no frame-rate case. It survives only as what it
   always also was — VRAM tidiness and exact streamed reservations —
   and must be argued that way, on the footprint rather than on
   milliseconds. That footprint is **336 KiB**, not the 392 KiB this
   line used to cite: P3b-6 moved it when the rounded boxes stopped
   premixing their colour.

   **The prize is now measured, and it is a third of what the first
   attempt at this paragraph claimed.** That version compared payload
   against the baker's *budget* model — 8 KiB pages — and called the
   difference reclaimable. It is not. `gsKit_vram_alloc` rounds to
   8 KiB only for `GSKIT_ALLOC_SYSBUFFER`, and `ps2ui.c:632` does not
   call it at all: every texture binds through
   `gsKit_TexManager_bind`, sized by `gsKit_texture_size()`, which
   counts **256-byte blocks** after rounding to an alignment group. A
   full page is that function's largest case, not its unit.

   | example | payload | allocator commits | budget charges | reclaimable |
   |---|---:|---:|---:|---:|
   | memcard | 130 KiB | 140 KiB | 160 KiB | **10 KiB** |
   | opl-env | 224 KiB | 257 KiB | 336 KiB | **33 KiB** |
   | channel6 | 190 KiB | 234 KiB | 368 KiB | **44 KiB** |

   The claim that channel6's nine CLUTs cost 63 KiB of page waste was
   the worst of it: `ps2ui.c:594` charges `gsKit_texture_size(16, 16,
   CT32)` = **1024 B** for each, so they cost 9 KiB, not 72 — and it
   charges that per *indexed texture* rather than per distinct CLUT,
   which is a detail neither the page model nor a per-CLUT reading
   gets right.

   **Keeping the budget pessimistic is correct** — refusing a blob that
   would have fitted is the safe direction, and `ps2ui_upload`'s
   preflight exists because `_blockAlloc` hangs rather than fails. What
   does not follow is quoting that pessimism as a saving. The bake now
   prints all three figures, and the pessimism is worth seeing on its
   own account: channel6 books half the budget where the allocator
   takes under a third.

   So P3c's footprint case is **weaker than it looked, and now
   measured**: about 33 KiB on the anchor example, against 336 KiB
   committed. Combined with a frame-rate case that F-042 closed
   outright, that is a fair basis for leaving the item shut — and a far
   better one than a number a packer author would chase and not find.
   `tools/check-vram-model.py` holds the baker's port of
   `gsKit_texture_size` to the vendored original across 45,000 sizes,
   because a second implementation of someone else's arithmetic is
   precisely what this file keeps getting wrong.

   **And the fill argument is now closed rather than merely unopened**
   [F-042]. F-039's calibrated model prices half a field of GS at 25.9
   full-screen blended layers; every content shape F-038 named as a
   threat costs under 11% of a field at the fitted slope, and under
   16% even if textured fill runs at half that rate — the slope was
   fitted on untextured sprites, so the textured shapes are lower
   bounds. Even at half rate, half a field takes 13 layers. There is
   no future content that revives P3c on frame rate. Footprint or
   nothing.
3. **P3d — precompiled GIF/DMA chains.** Bake each screen's static
   geometry as a ready-to-kick chain; runtime patches the dynamic tail.
   Frame ≈ one DMA kick. **Gate did not open, and this was the phase's
   headline item** [F-036, F-037]. It removes EE work; the EE is at
   14.4% of a vsync-locked field, so the best case is two milliseconds
   off fourteen that are already idle. Deferred, not deleted — the
   argument for it is headroom for content nobody has drawn yet, and
   F-038 says what would have to be shown first.

   **P3d's gate has its number now** [F-044]. The GS side of F-038 was
   settled by arithmetic; the EE side had one number and no model, so
   "the EE is at 14.4%" was measured on one content shape and
   extrapolated to none. S14's sweep splits that number: **2.44 ms per
   `ps2ui_render` and 0.08 ms of driver**, from five points at
   r² = 0.99996. The EE cost of a screen is now a thing that can be
   extrapolated rather than a single reading.

   One caveat carried forward: this was measured on the blob at
   `914e20c`, before P3b-6 took opl-env from 1,302 commands to 2,158.
   The per-render figure will rise. The decomposition method is what
   generalises — re-running the same five ELFs against a new blob
   re-prices it in one sitting.

   **And the number it has is still one point.** 2.44 ms is one screen
   at one command count, which is the shape of the problem F-044 was
   built to fix — *"the EE side has one number and no model"* — one
   level up. Dividing it by a command count is a division, not a model.

   **P3d's first slice is therefore the content sweep, not the
   optimization**, which is also what this section's own ordering rule
   demands: a phase opening *"optimization against Phase 2's numbers,
   not vibes"* must not begin with the item those numbers argue
   against. The blob already carries six screens spanning **110 to 694
   commands**, a 6.3× range, so six renders price the gate with no new
   geometry and no new blob.

   **The fit has two regressors, not one.** PLAN.md's own definition of
   P3d is *"bake each screen's **static** geometry as a ready-to-kick
   chain; runtime **patches the dynamic tail**"* — and slot glyphs
   **are** that tail. The pen composes them per frame from the current
   string, so a precompiled chain cannot contain them: they are EE work
   P3d does not remove. Over these six screens glyphs track commands
   only at r = 0.75, so a one-term fit buries glyph cost inside `k` —
   and since the whole claim is that **k bounds what P3d can buy**,
   that bias runs in the direction that wrongly *opens* the gate.

   ```
   ee = base + k_cmd × cmds + k_glyph × glyphs      only k_cmd is the bound
   ```

   Predicted off the blob, at each screen's initial focus. The
   photographs are what count — `c` and `g` are on the readout for
   exactly that reason — but the prediction goes down first, the way
   F-039's and F-044's did:

   | screen | commands | slot glyphs | drawn | `p` |
   |---|---:|---:|---:|---:|
   | confirm | 110 | 153 | 64 | 217 |
   | detail | 196 | 194 | 99 | 293 |
   | landing | 331 | 241 | 206 | 447 |
   | recent | 360 | 351 | 189 | 540 |
   | filters | 467 | 196 | 253 | 449 |
   | library | 694 | 384 | 366 | 750 |

   Written at four-digit `n` and `@`. **The `slot glyphs` column was
   three high on every row until S15**, and `p` with it: the telemetry
   was a declared 55-glyph constant and it is really 52, rising to 54
   once the frame counters reach five digits. `check-sweep-table.py`
   derives it from the format strings now and declares field widths
   instead. See docs/bench-phase2.md.

   `recent` and `filters` are what make the split possible: 30% more
   commands, 45% fewer glyphs.

   Every column is derived by `tools/check-sweep-table.py` against the
   blob and the driver, including the `[c:<screen>] ` build tag #87 put
   on line 1 — the tag is slot text, so its 10-11 glyphs are counted in
   `g`, and both copies of this table were short by exactly that for a
   pull request. `bench-phase2.md` states the one input the derivation
   cannot compute, the 55 glyphs the driver's two telemetry lines
   reconstruct to.

   **Six points are enough, and that is arithmetic rather than hope.**
   r = 0.751 gives a variance inflation of 2.29, which is mild, and the
   commands spread over `sqrt(Σ(c - c̄)²)` = 462. Taking
   `k_cmd ≈ 2.44 ms / 414` as the scale if the walk were the whole
   per-render cost, and σ as the residual standard error of S14's own
   `ee` fit — **0.0276 ms**, derived from its five residuals rather
   than read off its r², which is the step where this first came out
   2.8× too small — the 95% interval on `k_cmd` with 3 degrees of
   freedom is:

   | σ | 95% CI on `k_cmd` |
   |---|---|
   | 0.028 ms (S14's) | ±4.9% |
   | 0.055 ms (twice that) | ±9.8% |

   So `k_cmd` separates to about ±5%, and to ±10% even if these six
   screens are twice as noisy as one screen swept by N. That decides
   the gate several times over, so **the seventh authored screen is not
   needed** — a prediction the sitting can falsify, rather than a worry
   to carry into it. It is falsified by a fitted `k_cmd` whose own
   standard error exceeds a tenth of it, which would mean the residuals
   came back far above S14's.

   **That decomposition is the gate.** A precompiled chain removes the
   per-command term and leaves the fixed one. Mostly `base` and P3d
   buys little at any content scale — the gate then stays shut on a
   measurement rather than on an asymmetry, which is a better place to
   leave it. Mostly `k_cmd` and it scales with content, and the
   intercept says at what size.

   Static by construction: a screen build skips the window scroll and
   the cover uploads, which are library-only, so the points differ in
   content and nothing else.

   **The x-axis is `c`, and `p` is not it.** `p` is `stats.prims` —
   draws submitted, which is painting commands that survived visibility
   *plus one per slot glyph* — while the loop P3d removes trips
   `stats.cmds` times. `p`/`cmds` runs 0.94 to 1.90 across these six
   screens and the two orderings differ, so `p` is not a rescaling of
   commands; a plot against it fits a different line. The screen arm
   therefore prints `c`, `g` and `u` in place of `p` and `up` (which is
   always 0 with no window to scroll), and the sweep reads its x off
   the photograph rather than off this table.

   One correction the write-up owes: **cover streaming is not
   library-only.** `detail.html` carries a `det-art` streamed slot and
   nothing binds it, so detail draws one texquad whose `Mem` is NULL —
   counted in `prims`, then skipped before the bind. Library has nine.
   About 1% of prims, but it lands on both ends of the fit and it
   *removes* work, which flattens the slope toward "P3d buys little" —
   one of the two conclusions on offer. `u` is on the readout so the
   correction is measured rather than argued.

   The readout itself had to move to make room. It is now on **all six
   screens** rather than only on library — slots are per-screen, so a
   readout on library draws nothing while any other screen is up, and
   five of the six points are not library — and it dropped to 11px,
   F-046's floor. At 14px the theme arm's worst case is 43 characters
   in a 38-character slot and 359px in library's 314px of footer, so
   its last field was already being clipped on long runs; a third line
   does not fit either, the lint puts it at y=425, outside title-safe.
   `examples/opl-env/check.py` now measures every arm of the driver's
   own format strings against every screen's slot with the runtime's
   pen, so "it fits" is a check and not a recollection.

   **The EE instrument exists, and this paragraph used to say it did
   not.** It described the arm as missing and proposed building it on
   an alpha test — `ATE` with `ATST = NEVER` before N extra passes, so
   the EE does its work while the GS discards every fragment. That is
   not what was built, and the reason is written at the arm itself:
   `gsKit_set_test` takes a preset, `gsCore.c` is not vendored here,
   and `GS_ATEST_ON` is documented only as *"Turns on Alpha Testing
   (Source)"*. **An instrument built on unverified GS state cannot
   settle a question about whether an instrument is trustworthy**,
   which is the same hazard `ps2ui.c:999-1010` declines to take on.

   What shipped instead is N extra whole-UI passes touching no GS
   state at all. `gs` rises with them, and that costs nothing: `ee` is
   read across the kick window and `gs` after `gsKit_finish` returns,
   so the GS scaling never enters the EE number — it is a free
   cross-check that the passes are doing what the arm claims. S14 ran
   it and F-044 is the result, five points at r² = 0.99996. So the
   prediction this paragraph made about `gs` was wrong too: it does
   not rise "by transfer and setup only", it rises at 0.777 ms per
   render, the full render rate.

   The correction is recorded here because the sequencing authority
   was asserting a missing instrument, a mechanism the code had
   rejected in writing, and a `gs` prediction its own finding
   falsified. `docs/bench-phase2.md` §"The EE arm, and why the obvious
   version of it does not work" has carried the right account since
   S14; this file is the one that drifted.

   **The second slice is what LAYERING costs**, and it is the one
   number F-038 asks for that nothing has measured. That finding's bar
   for reopening either gate names *"a transition compositing two full
   screens"* as the likeliest content to push past half a field — and
   composition is the one Phase 1 contract nobody has timed. §4.4
   measured it in primitives (375 + 255 = 630) and stopped there.

   `COMPOSE=1` renders **library then confirm in one frame**, which is
   the documented overlay idiom exactly, over two screens the blob
   already carries: **804 commands**, above every point in the sweep.
   No new geometry, no new blob, one more photograph on a sitting
   already scheduled.

   **It is read against the sweep, not on its own.** Both screens are
   sweep points, so three photographs settle it between themselves:

   ```
   ee(library+confirm) − ee(library)  ==  ee(confirm) − base    per RENDER
                                      <   ee(confirm) − base    per FRAME
   ```

   **That is the decomposition P3d turns on, one level up from the
   sweep.** The content sweep says what a command costs; this says
   whether `ps2ui_render`'s own fixed cost is paid once per frame or
   once per render. A chain that removes per-render setup pays twice
   on a layered screen and once on a flat one — so if the fixed term
   is large *and* repeats, layering is where P3d earns its keep, and
   if it does not repeat, a modal is nearly free and the gate is
   unmoved by the case F-038 thought most likely to move it.

   Predicted before the sitting, as F-039's and F-044's were:
   additivity holds, because `ps2ui_render` keeps no state between
   calls that a second call could reuse — it re-applies the scissor,
   re-walks from `cmd_first`, and rebinds every texture. Falsified by
   a composed frame coming in materially under the sum, which would
   mean something *is* being reused and the per-render model that
   F-044 fitted is charging for it twice.

   **The identity is in commands *and* glyphs, and the first version
   of this arm broke the glyph half.** It blanked library's readout so
   the scrim would not show two of them — but `oplenv-scr-library`,
   the subtrahend, draws its pair, so the composed frame carried 466
   glyphs against the two sweep points' 521. Under the sweep's own
   two-term model that makes the measured difference short by
   `k_glyph × 55` — **always, and always in the direction of "under"**,
   which is this arm's falsification criterion verbatim. An artifact
   that manufactures the finding is the failure this phase keeps
   catching, and it would have argued for the conclusion F-038
   nominated as most likely to matter.

   Fixed in the instrument rather than corrected in the analysis: the
   driver now writes the same readout into both pairs, so the counts
   add exactly. **And it is checkable on the photographs** — with the
   fix, `g(composed)` must equal `g(library) + g(confirm)`, all three
   read off line 2. A mismatch means an asymmetry like that one is
   back, and the sitting can see it without waiting for the fit.

   **One thing the sweep does not price, and it belongs in the
   decision.** A precompiled chain pays off because the geometry is
   fixed. Nothing in the runtime moves, scales or fades a node today —
   the whole surface is visibility, slot text, streamed textures,
   CLUT/theme, screen, focus and list windowing — so "fixed" is
   currently free. The pull lane's **runtime geometry** item proposes
   changing that, and the animated share of a screen is a direct
   discount on what a chain can buy. If it is ever pulled, its scope
   wants settling before the chain is built rather than after, because
   the chain's design turns on how much of it has to stay patchable.

The ordering is deliberate: the ungated item first, then the two whose
justification does not exist yet. A phase that opens "optimization
against Phase 2's numbers, not vibes" should not begin with the item
those numbers argue against.

**The bar for reopening either gate is written down** [F-038]: content
inside the Phase 2 envelope that pushes `ee` or `gs` past about half a
field. The most likely candidate is not more list rows — text is cheap
and the EE is nowhere near its limit — but anything that fills area: a
background image, larger cover art, or a transition compositing two
full screens. Fill scales with area, and this screen is mostly flat
panels.

> **Exit gate — rewritten, because the old one gated an item this
> phase declined to build.** It read: *"measured frame CPU time
> published before/after; chains are opt-in per blob via a feature bit
> and degrade to the replay path."* That is **P3d's** gate. P3d is
> deferred — F-036 shut it — so the phase was carrying an exit
> condition for work it had decided not to do, which is the
> sequencing authority contradicting its own item list.
>
> **The gate is P3b's, because P3b is the phase:** a UI recolours
> every colour it draws — commands *and* slot text — from a theme
> chosen at runtime; the previewer renders each theme so a reviewer
> can see one without a console; and a blob that cannot be recoloured
> correctly refuses to open rather than switching to a theme that
> moves nine unrelated things together.
>
> **Two conditions carry over from the old gate, and both bind
> harder now.** Any item still claiming a *speed* justification must
> publish measured GS **and** EE time before and after — that
> amendment was made once CPU time turned out to be an eighth of a
> field [F-036], and it stands. And an item that improves neither
> number does not ship on the grounds that it is clever.

### Phase 4 — Make it a product

Distribution, deliberately last.

**Honest versions — [shipped].** Both packages claimed 0.2.0 against
**no git tags at all**, through four format versions of drift (v4-v7),
and the baker additionally carried `__version__ = "0.1.0"` beside the
0.2.0 in its own `pyproject.toml`. They carried a prerelease —
`0.3.0.dev0` and `0.3.0-dev.0`, one version in two spellings — until
`v0.3.0`, which is the first tag this repository has ever had.
`pyproject.toml` derives its version from `__init__.py` rather than
restating it, so there is no second number left to disagree; every CLI
answers `--version` from that one source, since a number no command
will print is a number nobody filing a bug can quote; and
`tools/check-versions.py` reads the package versions, `PS2UI_VERSION`,
`uib.VERSION`, this file's format-history line and the CHANGELOG's
format claims against each other on every push. The CHANGELOG's open
section records v6 and v7, which it had never mentioned.

`docs/releasing.md` carries the order of operations, because the tag
rule is a trap without one — the first person to cut a release would
meet a red CI with no idea what satisfies it, and the cheapest way out
of a rule you do not understand is to delete it. Cutting `0.3.0`
proved that a written order of operations is not the same as a
correct one: releasing.md's step 4 and check-versions.py's rule 5
were mutually unsatisfiable, and neither document said so until the
steps were actually run. It also states what a
prerelease is actually worth, which is less than the first draft of
this claimed: npm resolves the `latest` dist-tag and `npm publish` sets
it whatever the version says, so `@ophtml/layout` pins
`publishConfig.tag` to `next`; and pip's exclusion of prereleases
lapses when no stable version exists, which for a first upload is
exactly the case, so the first PyPI upload has to be a real release.

That leaves the version number itself as a judgement no check makes:
0.3.0 is the tree's own claim about where it is, and nothing verifies
it is the right next number.

**The UC-3 tutorial — [shipped].** `docs/tutorial-uc3.md` builds an
OPL-class game browser from an empty directory with the reader's own
TTF, and `tools/check-tutorial.py` executes it in CI: every command
block in order, in one scratch directory, with the printed numbers
matched against what actually happens.

Writing it is what found the exit gate's real blocker, and the blocker
was not a missing document. **Both packages defaulted their font path
to `../../../fonts`** — the repository root in a checkout, and nothing
at all in an installed package. A stranger with npm, pip and a TTF met
a bare ENOENT on a path pointing outside the package they installed,
and nobody here could see it, because in a checkout the path resolves.
Four more things surfaced the same way: `-o build/ui.json` failed when
`build/` did not exist (every `build.sh` in the repository `mkdir -p`s
first, so the scripts hid it); the layout compiler and the baker took
two different font configurations for one set of fonts, with nothing
checking they agreed; `--font-dir`'s two fixed filenames were
documented nowhere; and a misspelt `data-` attribute was **silent** —
`data-focus` for `focusable` compiled a screen with no navigation at
all, and `data-capacity` for `data-slot-capacity` silently took the
63-byte default.

All five are fixed. None was findable from inside the repository; all
five were findable in ten minutes by running the first command from an
empty directory.

**What the second fix does and does not close.** The layout compiler
reads the same `fonts.json` the baker does, but `--font-dir` survives
alongside it, so a project can still compile with one and bake with the
other. What prevents the damage is that the baker now reads the faces
the IR was **measured** against — the IR has carried them since v1 and
the baker had never looked — and refuses a manifest that names a
different family or weight, since text positioned by one font and drawn
with another is wrong on every screen with nothing to say so. Two
builds of the *same* family whose metrics differ still agree on those
two fields and diverge in the advances; catching that wants a digest of
the tables in the IR, which is format-visible and is not this. The loud
case is prevented, the quiet one is avoidable, and a test asserts the
gap so the claim cannot quietly widen.

**The `ps2ui` wrapper CLI — [shipped].** `build` / `check` / `fontgen`
/ `dev` over a toolchain that had three front doors and three argument
shapes, with `--fonts` meaning the same thing in two of them and absent
from the third. A project is a `ps2ui.json` whose only required keys
are `screens` and `css`; everything else defaults, an unknown key is
refused by name, and every path — including every path the tool
*prints* — is relative to the project rather than the working
directory.

The design was settled by conversion rather than by argument: all four
shipped examples had carried the same `build.sh` with different flags,
and each now describes itself in a project file and produces a
**byte-identical blob**. `variants` was considered and dropped —
channel6's 16:9 build is a second `ps2ui build --mode ntsc16x9 -o …`,
because a second blob is a second build and a nested dialect is one
more thing to learn.

That principle then had to be made true. The first version gave
`ps2ui build` only `--mode` and `-o`, so *"everything a second blob
needs differently is a flag"* could not be applied to the one second
blob in the repository: the 16:9 build overwrote the 4:3 build's
display preview and its intermediate JSON, and because a blob's screen
names ARE the IR file stems, silently renamed its screens. A second
build of one project moves its whole build now — `-o` carries its
suffix down to the intermediates, and `--preview`, `--montage` and
`--preview-display` override the siblings whose names are documented.
All four blobs the examples produce are byte-identical.

**The distribution names — [shipped].** `@ophtml/layout` on npm,
scoped because the `ophtml` organisation is owned and a scope is
unambiguously ours; `ophtml` on PyPI, which has no scopes. Renamed
before tagging, because renaming after a published `0.3.0` leaves a
dead name on two registries permanently, and neither registry reserves
a name without a publish.

`check-versions.py` reads the two names back out of the manifests and
holds them to the ones it states, because the rename is the only
irreversible step in the release and was the only one with no fence:
reverting it across the whole tree left the checker's output
byte-identical at 16/16, printing the new names over manifests that
said the old ones. A consistency rule alone would not have caught that
either — a wholesale rename is self-consistent — so the names are
written down in the checker, and moving them is a deliberate edit
rather than something a `sed` does in silence.

The commands, the Python module and the format keep their names, and
`docs/releasing.md` says why: OPHTML is the product, ps2ui is the
format and the tools that speak it, so `pip install ophtml` giving you
`ps2ui build` is the shape it should have.

Then npm + PyPI, and a format stability pledge **post-v7**.

The pledge moved from post-v6 because v7 broke the format inside
Phase 3 (the tint table), which is the second break since the pledge
was first written down. P3b-3 is the last planned format-visible
change in the phase; the pledge has to start after it or start again.

> **Exit gate:** a stranger with npm, pip, and a TTF reproduces the
> memcard example — and its hardware screenshot — without cloning the repo.

**Both packages are uploaded and the gate is NOT met.** `0.3.0` is on
PyPI and npm as of 2026-09-04, verified from an empty directory: `pip
install ophtml` resolves the release rather than a prerelease, `latest`
points at `0.3.0`, and both registry pages render their READMEs. That
was necessary for the gate and is not sufficient for it, which is the
distinction `docs/releasing.md` step 8 was rewritten to keep visible.

The first real attempt failed at the tutorial's first command. **pip's
macOS Pillow wheel ships no Raqm layout engine**, so `ps2ui fontgen`
refuses to write a metrics file it cannot kern — correctly, since
without Raqm every advance comes out identical and the kern table comes
out empty, and all three pens then agree perfectly on zero kerning.
The toolchain behaved exactly as designed. Its **reachability** is what
failed, and reachability is what the gate is about.

That opened onto four more, none of them new and none of them findable
here:

| | |
|---|---|
| `test_baker.py:49` | discovers a TTF from two Linux paths, while `fonts/fonts.json` already lists four including two macOS ones. Two lists for one job, and the test's is the poorer |
| the skip guards | with no TTF the suite is **22 errors across 7 classes**, not a row of skips. Four `skipIf(TTF is None)` sites exist, only two of them class-level, against seven classes that need one |
| `fonts/fonts.json` | has `/opt/homebrew/share/fonts/` and `/Library/Fonts/`, misses `~/Library/Fonts/` where per-user installs land, and `/usr/local/share/fonts/` which is Intel Homebrew |
| `make -C runtime syntax-check` | **[fixed]** could not pass under clang at all. Misfiled as macOS; it is a compiler problem, reproducible on Linux, and ci.yml now runs a clang arm |

**The shape of all five is one shape: this project is verifiable on
Linux, and the gate is about strangers on arbitrary machines.** Every
runner in `ci.yml` and `hw.yml` is `ubuntu-24.04`, so none of these
could have been seen from inside CI, and four of the five had been
true for as long as the code had existed. This is the same class as
the five defects the tutorial found — *"none was findable from inside
the repository; all five were findable in ten minutes by running the
first command from an empty directory"* — with the platform substituted
for the directory.

**0.4.0's spine is making the gate reachable**, in this order, because
the last item goes red on the first three if they land after it:

1. **One source of truth for test fonts, and guards sized against 22.**
   `test_baker.py` reads `fonts.json` rather than carrying its own
   list, and every class that needs a TTF says so. Measured rather
   than estimated, by pointing the discovery at a path that does not
   exist:

   ```
   FAILED (errors=22, skipped=38)

     7  TestKernTable          2  TestDeadGeometryTrim
     5  TestKerningPen         2  TestCrossLanguagePen
     4  TestSlotSpacing        1  TestTintTable
                               1  TestFontgenRefusesWithoutRaqm
   ```

   That is what a stranger's first `python3 -m unittest discover`
   prints on any machine without DejaVu at one of two Linux paths,
   after they have done everything the tutorial asked. **The number is
   the point**: an earlier draft of this row named one class, and a
   record that says one class produces a remedy sized for one class.
   Note also that `TestFontgenRefusesWithoutRaqm` contributes **one**
   of the 22, not two — its other test mocks `features.check` to
   `False`, so `fontgen` refuses before it ever reaches the TTF.

   The guard on the Raqm test needs **both** a TTF and Raqm, and it
   must be loud: silently skipping the test that proves kerning works
   is how an empty kern table ships while every pen agrees on zero.
2. **`fonts.json` covers macOS properly**, under a stated principle
   rather than by adding paths as they are met. The Intel/ARM prefix
   split is the same one the Raqm remedy has.
3. **The Raqm remedy, written where the failure is met.**
   `fontgen.py`'s refusal says *"install a Pillow wheel built with
   Raqm (pip's manylinux wheels are)"*, which is true and useless on a
   Mac. The remedy is verified end to end — Pillow 12.3.0 with Raqm
   0.10.5 reproduces the tutorial's documented numbers exactly — so it
   can be stated: `brew install libraqm`, then a source build of Pillow
   alone with `PKG_CONFIG_PATH` pointed at `brew --prefix`. **And the
   trap beside it**, because it was paid for: `--no-binary :all:` scopes
   the source build to the whole dependency graph and spends forty
   minutes bootstrapping CMake. `--no-binary pillow` is the flag.
   `brew --prefix` rather than a literal path, because Intel is
   `/usr/local`.
4. **A job that installs from the registries**, matrixed over ubuntu
   and macOS. `tools/check-tutorial.py`'s docstring already states the
   constraint that is easy to get wrong: this must **not** replace the
   shim job. The shim job tests *this tree*; a registry job tests *the
   release*; deleting the shims silently swaps one subject for the
   other. It also cannot gate a PR's own diff — it can only ever
   install the last published version — so it belongs on `schedule:`
   and `release:` rather than per-push, in its own workflow, where a
   registry outage cannot redden ordinary CI.

**What none of that closes.** The gate says the memcard example *and
its hardware screenshot*. Items 1-4 are the software half. No runner
has a PlayStation 2, so a green macOS registry job still leaves the
screenshot half open, and a future green must not be read as the gate
being met.

### What the gates do not hold back

The phases sequence **new capability**. They do not queue defect fixes,
and they never hold a correctness fix behind a hardware session.

A defect is: the toolchain does something other than what it documents,
produces a wrong number, or contradicts the standard it borrows its
syntax from. Those ship when found, in their own change, whatever phase
is open. An authoring correction -- fixing a CSS property that
diverges from CSS -- is a defect fix, not a feature, even though it
breaks existing documents; the breakage is the cost of the fix, not
evidence it is feature work.

Stated because three documents in flight disagreed about which bucket
the `flex-direction` default belonged in, and the sequencing authority
should settle that rather than let the precedent be set by whichever
PR merged first.

### The pull lane

No phase: `position: absolute` (F8), gradients (F15), localization (F17),
non-Latin text (F16), full VRAM unload (old F19), **runtime geometry**
(below). Each enters only when a concrete use pulls it. Nothing enters
because it scores well.

**Runtime geometry — animation and transitions.** Geometry is baked, and
the whole runtime surface is `visible_set`, `slot_set`, `tex_set`,
`clut_set`, `theme_set`, `screen_set`, `focus_set` and `list_*`. Nothing
moves, scales or fades a node, so a cascade, a coverflow, a slide
transition or a focus ring that travels cannot be expressed at all — an
app can only cut between baked states. It is a polish gap rather than a
correctness one: what ps2ui draws is right, it just arrives instantly.

Three tiers, cheapest first, and they are separable:

| tier | mechanism | notes |
|---|---|---|
| offset | `ps2ui_offset_set(ctx, name, dx, dy)` over a subtree | one add per command; an offset table shaped like the visibility bits. Slide-ins, travelling focus rings, parallax |
| scale + opacity | opacity into the tint alpha; scale recomputes quad corners | opacity is nearly free — the tint table has been per-command since P3b. Scale is where I2's rounding rule and P1k's half-texel bias need re-deriving, not reusing |
| timelines | a `@keyframes` subset baked into the blob | an app plays a named transition instead of driving a value per frame. The tier that makes it authored in CSS rather than in C |

**What would pull it**, stated so the admission rule has something to
test: a PSBBN-class animated shell. That is not an anchored use case in
§5 today — UC-3 asks for none of it — so it stays in this lane. `F8` is
upstream of the parts that overlap without nesting, and `lint.js`
already carries forward cover for that.

**It discounts P3d, which is why it is written down now.** A
precompiled chain pays off because the geometry is fixed, so the
animated share of a screen subtracts directly from what the chain buys,
and the chain's design turns on how much has to stay patchable. If this
is ever pulled, its scope wants settling before the chain is built
rather than after. That is a sequencing claim, not a measurement.

## §7 PS2 hardware exploitation map

The GS is a fixed-function rasterizer: no shaders, 4 MB eDRAM on a
2,560-bit bus (~48 GB/s), fill on the order of a gigapixel per second —
absurdly overpowered for a 640×448 UI. The strategy: **trade the console's
abundant fill and the build machine's unlimited compute against the
console's scarce memory and absent programmability.**

| Hardware trait | Exploitation | Status |
|---|---|---|
| No shaders, fixed function | Everything at build time; the console replays | shipped |
| Blend/modulate read 0x80 as 1.0 | All alpha and tints converted once, at bake; the classic overbright bug structurally impossible | shipped · verify P0 |
| PSMT8+CLUT, 4× texel density | Opt-in palettization; all glyph atlases | shipped |
| CSM1 CLUT swizzle | Files linear; runtime permutes on upload | shipped |
| CLUT rewrite ≈ 1 KiB | **Theming by palette swap** — same art, new palette, near-free | Phase 3 |
| 4 MB VRAM, 8 KiB pages | Page-rounded budget + refusal at bake; page-boundary packing and exact streamed reservations next | shipped · P1/P3 |
| GIF/DMA packet feed | **Bake the packets**: static chains + patched dynamic tail; frame ≈ one DMA kick | Phase 3 |
| Inclusive scissor | `overflow: hidden` as baked stack; dead-geometry trim; depth enforced at every stage | shipped |
| Interlaced 640×448 | 1px-shimmer lint; anamorphic aspect in the header; field order is bring-up step 8 | shipped · verify P0 |
| No subpixel positioning | One integral rounding rule across three pens; test card catches half-texel drift | shipped · verify P0 |
| 294 MHz EE has better uses | D-pad press = one lookup; slot pen = advance walk + bsearch kerns; zero allocation after load | shipped |

**Non-goals:** 3D, VU microprograms, audio, video decode. The GIF-chain
path reaches near-zero EE cost without leaving the UI lane.

## §8 Scaling rules

The quality bar features are admitted against — the second half of what
replaces RICE.

- **I1** The console never parses, lays out, rasterizes, or allocates.
- **I2** One rounding rule, three pens: `floor(x + 0.5)` everywhere; no pen
  change lands in fewer than all three implementations plus the agreement
  tests.

  **The mirror inventory**, because I2 names the pens and the same
  hazard is wider than the pens. Any quantity implemented twice in two
  languages is a silent divergence waiting to happen, and this tree
  found two in one day: `vram.py` asserted a page-granular allocator
  the runtime does not use, and `examples/opl-env/check.py` carried a
  private fourth copy of the pen while making a load-bearing claim on
  it. Current state:

  | quantity | implementations | held together by |
  |---|---|---|
  | glyph advance + kern | layout JS, baker, runtime C | agreement tests (F9e) |
  | arena layout | `arena.py`, `arena_compute` | compiled comparison, both sides |
  | CLUT CSM1 order | `clut_csm1_order`, `permute_clut` | `test_runtime.c:256` |
  | clip model | baker, validator | **one module**, asserted identical |
  | VRAM commit | `vram.alloc_size`, `gsKit_texture_size` | `check-vram-model.py`, 45,000 sizes |
  | blob pen | `pen.slot_width`, `slot_measure`, previewer `width_of` | rule tests; **no compiled comparison** |

  The last row is the weak one and is labelled so rather than dressed
  up: `slot_measure` is static and takes a whole context, so there is
  nothing to link against, and its rules are pinned as cases instead.
  **It earned that label immediately.** The first version of
  `pen.slot_width` skipped a codepoint the atlas lacks, and this
  paragraph said the previewer was the one diverging by substituting
  `?`. Both were wrong, in the sequencing authority, in the same
  commit that added the inventory.

  `find_glyph` (`ps2ui.c:1183`) returns `?` for a missing codepoint —
  *"matching the metrics' missing-glyph convention"*, so it was written
  to agree with the previewer. The `if (!g) continue;` further down is
  the fallback's **fallback**, reached only when `?` is absent too. So
  the runtime and the previewer agree, and the new pen was the odd one
  out — short by one `?` advance per missing codepoint, in the
  direction that passes a line the console draws wider. A rule test
  that pins the wrong rule is worse than none, and this one had cited
  the `continue` as its authority.

  **What survives is an authoring hazard, not a measurement one.** The
  charset lint covers `cp > 0x24FF`, so a Latin-1 character outside the
  baked atlas passes it and reaches the console as `?`. Preview, bake
  and runtime all agree about that; the author is simply not told.
  Worth a lint that checks the codepoint against the atlas rather than
  against a range — filed, not fixed here.
- **I3** Format moves are loud: stride changes bump the version, additive
  capabilities take a feature bit, readers reject what they don't know.
- **I4** Previewer parity: no runtime rendering behaviour without its
  previewer mirror.
- **I5** `ps2ui-check` learns every invariant the loader enforces, the
  same release. Scoped to load-time invariants — what a blob owes the
  runtime. Runtime-only surfaces (telemetry counters, focus state) are
  outside it and are covered by the runtime suite instead.
- **I6** Examples are the contract: warning-free builds, self-refreshing
  screenshots, every feature exercised by one. No carve-out for
  features whose only example cost is a screenshot diff — that cost is
  the point, since a feature no example renders is a feature no
  previewer regression can catch.
- **I7** Tests are sabotage-verified: a test earns trust by failing against
  a deliberately broken implementation.
- **I8** Caps and constants are parsed from `ps2ui.h`, never duplicated.

**Definition of done, per feature:** code in every affected stage; tests
including the adversarial case, sabotage-verified; format docs updated in
the same change; validator coverage for new load-time invariants; an
example exercises it with screenshots refreshed and warnings at zero;
CHANGELOG entry; BACKLOG updated as ledger, not scoreboard.

## §9 Risks

| Risk | Standing | Mitigation |
|---|---|---|
| Renderer unproven on silicon | **top risk, now partly realised** | Phase 0 found a real fault at bring-up step 2 before any UI ran, which is what the gate is for |
| ~~Nothing in `runtime/` ever writes the GS `ALPHA`, `TEST` or `PABE` registers~~ | **closed — confirmed cause, fixed, and verified on hardware** | the baker computed alpha in the 0..128 domain assuming `(Cs - Cd) * As >> 7 + Cd`; the runtime inherited gsKit's `GS_BLEND_BACK2FRONT`, which is that equation with the operands swapped, so alpha ran inverted. probe v3 isolated it and a SCPH-50000 confirmed it. `ps2ui_render` now asserts the equation every frame and two runtime checks fail if it stops. **Residual:** the alpha TEST is still inherited — defensible (`ATE` defaults off, a discard was positively ruled out) and reasoned in `ps2ui.c`, but it is the same shape of exposure |
| Emulator not an oracle; PCSX2 needs a BIOS | standing | emulator job kept as characterisation, not verdict; fingerprint tool makes captures comparable |
| Phase 1 is a breaking rework | accepted | that is why it happens before packaging creates external consumers; one v6 move |
| Node + Python dual runtime friction | standing | packaging wraps it, doesn't remove it; accepted cost of replaceable stages |
| Single-track development | standing | §8 discipline makes correctness reviewable after the fact; stacked small PRs; no self-merging |
| I2's three-pen agreement is a convention, not a structure — a hurried contributor can add a pen or edit one and skip the agreement tests | standing | the tests fail loudly when run; the exposure is someone not running them. Only real fix is CI coverage of every pen, which exists today for all three |
| 4 MB VRAM vs art-heavy themes | physics | PSMT8 everywhere, streamed slots, page-exact budgets visible at build time |

## §10 Decision log

| Decision | Rationale | Revisit when |
|---|---|---|
| ~~Stopped diagnosing Play!'s 0x7f/0x80 behaviour~~ **REOPENED, then RESOLVED** | It was not an HLE artifact. A SCPH-50000 does the same thing: blended sprites at As `0x7f` and `0x80` produce nothing, while their unblended references at the same vertex alpha paint correctly. Writing it off as emulator inaccuracy cost a cycle; the fingerprints are what made the hardware result recognisable when it arrived | now — probe v3 |
| Deferred `visible_get/set` conflation fix (PR #16 review) | wants a deliberate API break | Phase 1 API pass |
| Deferred the deliberately clipped probe quad (PR #15 review) | only observable on hardware | Phase 0 probe |
| F19 unload parked; streaming re-derived as static reservation | the F19→F20 dependency was inherited, not derived | a shell-and-module use case |
| ~~No publishing despite 0.2.0 metadata~~ **RESOLVED** | Strangers shouldn't build on an unverified renderer, and the metadata says so: the packages carried a `0.3.0` prerelease against zero tags until `v0.3.0`, the first tag here. Tagged is not uploaded — neither package is on npm or PyPI, and the Phase 4 exit gate is unmet until someone who is not us installs them | — |
| No self-merging of PRs | process error made once (PR #11), fixed forward | — |
| RICE retired as sequencing mechanism | §4.6 | — |

**Immediate action:** Phase 0, the bench session, before further
feature work. Everything downstream of its exit gate is provisional
until it passes. This document is amended by PR like everything else.
