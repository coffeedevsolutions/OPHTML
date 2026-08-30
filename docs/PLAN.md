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
ui/*.html,css ─▶ @ps2ui/layout ─▶ ui.json ─▶ ps2ui-bake ─▶ ui.uib ─▶ runtime
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
header) → v5 kerning (font entry 16→24 bytes, feature bit 1). Struct-size
changes always bump the version; unknown feature bits reject loudly.

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
   bakes and loads unmodified for the first time: 121 slots, 8,285
   bytes of arena. Borrowing the caller's string rather than copying it
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
   `examples/opl-env`: six screens, 127 slots, ten streamed texture
   slots, one overlay. 246,144-byte blob, 7,031-byte arena for the
   whole environment, VRAM 392 KiB inside a 736 KiB budget. Carries the
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
   in its palettes. In opl-env, 997 of 1,302 commands carry the
   identity tint, and every panel, border and background is an
   untextured quad whose colour is a baked `r,g,b,a`. A CLUT swap
   cannot reach any of it.

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
   the attribute. opl-env is **127 slots**, which is every title, count
   and telemetry line in the environment.

   Fixed by splicing a linter's-eye view of each slot into the command
   list *at the index it would have painted at* — appending would let a
   rect drawn on top of the slot into its contrast chain — with two
   commands per slot, base and focus, because a slot has two colour
   vectors and the focused one is the seam that has been the gap in
   #70, #72 and #74.

   **What that turned up is open and is not P3b-5's to settle.**
   opl-env's entire secondary text layer sits below the 14px couch
   floor — row titles at 13, subtitles and counts at 11, detail fields
   at 12, **97 instances across six screens** — and none of it ever
   warned, because all of it is slot text. The floor was not being met;
   it was being missed. `--min-font-size 11` in `build.sh` keeps the
   rule live (anything smaller still fails) and records the admission
   in the one place a reader will look, but it does **not** decide that
   11px is readable from three metres. That is a question about the
   density study this example exists to be — twelve rows of four
   fields, which is what an OPL-class environment demands — and it
   wants a photograph, not an argument.

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

   | sitting | when | what |
   |---|---|---|
   | **A** | now, artifact hw #309 | the EE sweep (5 ELFs), F-040's falsifier (5 ELFs), the `-fill2` outlier |
   | **B** | after P3b-4 | a theme switch on hardware — P3b's exit gate, and the one claim in the phase a host cannot check |

   Sitting A decides whether P3d's gate can reopen, which is a
   phase-level question P3b-4 and P3b-5 do not depend on. Serialising
   them behind each other would hold a measurement for work that cannot
   change it.

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
   and must be argued that way, on the 392 KiB footprint rather than on
   milliseconds.

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

   **P3d's gate is now the only one that can reopen, and its evidence
   is the half nobody has instrumented** [F-042]. The GS side of
   F-038 is settled by arithmetic; the EE side has one number and no
   model, so "the EE is at 14.4%" is measured on one content shape and
   extrapolated to none.

   **The missing instrument is the EE analogue of the fill arm**, and
   the obvious version of it does not work. Rendering the UI N extra
   times inside a 1×1 scissor fails because `ps2ui_render` resets the
   scissor to the full canvas four lines in (`ps2ui.c:1044`), so the
   clip does not survive being entered and every pass fills the
   screen. The **alpha test** does survive: `ps2ui_render` deliberately
   leaves TEST inherited (`ps2ui.c:999-1010`), so `ATE` with
   `ATST = NEVER` before N extra passes gives the EE all of its work
   while the GS discards every fragment — no runtime change, and a
   documented non-assertion becomes the mechanism.

   `gs` will still rise, because it is GIF transfer *plus* drawing and
   each pass pushes the command list again. The check is therefore not
   "`gs` stays flat" but "`gs` rises by transfer and setup only, far
   below the N × 0.2861 ms the fill model predicts" — sharper, because
   the model supplies the number it must come in under. If `gs` rises
   *at* the fill rate, the test is not discarding and the arm is
   measuring nothing: the same trap as P3a's latched CSR, caught the
   same way, by predicting the number before the sitting.

   Until that sweep exists, this item is deferred on an asymmetry
   rather than on a measurement.

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

Distribution, deliberately last. Honest versions first (packages claim
0.2.0 with **no git tags at all** and now **four** format versions of
drift — v5, v6, v7 shipped under one package version), then npm + PyPI +
a `ps2ui` wrapper CLI (`build` / `dev` / `check` / `fontgen`), a format
stability pledge **post-v7**, and a docs pass with UC-3 as the flagship
tutorial.

The pledge moved from post-v6 because v7 broke the format inside
Phase 3 (the tint table), which is the second break since the pledge
was first written down. P3b-3 is the last planned format-visible
change in the phase; the pledge has to start after it or start again.

> **Exit gate:** a stranger with npm, pip, and a TTF reproduces the
> memcard example — and its hardware screenshot — without cloning the repo.

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
non-Latin text (F16), full VRAM unload (old F19). Each enters only when a
concrete use pulls it. Nothing enters because it scores well.

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
| No publishing despite 0.2.0 metadata | strangers shouldn't build on an unverified renderer | Phase 4 entry |
| No self-merging of PRs | process error made once (PR #11), fixed forward | — |
| RICE retired as sequencing mechanism | §4.6 | — |

**Immediate action:** Phase 0, the bench session, before further
feature work. Everything downstream of its exit gate is provisional
until it passes. This document is amended by PR like everything else.
