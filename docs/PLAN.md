# ps2ui Foundation Plan

*rev 1.2 · 2026-08-24 · format v5 shipped, v6 planned · status: bring-up matrix complete — steps 1–7, 9, 10 pass on SCPH-50000; 8 void pending a CRT (panel deinterlacer, with positive field evidence logged)*

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

Twelve sprints, twenty-six shipped backlog items, sixteen merged PRs, two
open.

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
> not the renderer.

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

All four items above have shipped. The gate's remaining clause is the
hardware one, and it is the only thing between Phase 1 and Phase 2:
`docs/bench-phase1.md` is the sitting, `fixtures/bench-stream` is the
blob and the covers, and `covers.elf` / `covers-nosync.elf` are the
instruments. Six steps, one photograph each.

Nothing in Phase 1 has been on a console. That is deliberate — the
host suites and the emulator gate carried it — but `ps2ui_tex_set`
hands the GS memory the EE wrote through a write-back cache the GIF
cannot see, which is the fault class #40 was and the one emulators
model least well.

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
   `examples/opl-env`: six screens, 125 slots, ten streamed texture
   slots, one overlay. 246,032-byte blob, 6,951-byte arena for the
   whole environment, VRAM 392 KiB inside a 736 KiB budget. Carries the
   `examples/` contract -- warning-free under `--strict`, screenshots
   refreshed by building, `check-blobs` with no exemptions -- and CI
   runs all three, which the first version did not.
2. **A runtime driver.** An ELF that loads the environment, walks it
   with the pad, and reports frame time and prim counts on screen.
   Nothing loads `opl-env` on a console today, so nothing in clauses
   3 or 4 can be measured.
3. **The windowed library.** The gate names this explicitly and it is
   the least-tested thing in the project: scrolling rebinds slot text
   and streams new covers into the *fixed* reservations as the window
   moves. Slot text and streaming have each been exercised alone and
   never together under motion. The nine `data-repeat` rows are static
   today.
4. **Measure on hardware.** Frame time at field rate, prim counts,
   VRAM, with the numbers written down beside the baked ones. Needs a
   sitting, and needs 2 and 3 first.
5. **File the gaps.** Ongoing, and the reason the phase exists. Three
   from the first build: a runtime test harness that segfaulted on any
   blob but one, single-line slots against a two-line dialog body, and
   `--strict` catching a 12px focusable.

`position: absolute` (F8) was **not** pulled: the overlay centres with
flex and needed nothing. It stays in the pull lane.

### Phase 3 — Spend the hardware

Optimization against Phase 2's numbers, not vibes:

- **Precompiled GIF/DMA chains:** bake each screen's static geometry as a
  ready-to-kick chain; runtime patches the dynamic tail. Frame ≈ one DMA
  kick — the logical conclusion of "everything at build time."
- **CLUT-swap theming:** same PSMT8 art, multiple ~1 KiB palettes; instant
  recolor for themes and focus states.
- **Page-aware atlas packing:** pack to 8 KiB page boundaries (64×32 CT32,
  128×64 T8) to minimize TBP switches and make streamed reservations exact.

> **Exit gate:** measured frame CPU time published before/after; chains
> are opt-in per blob via a feature bit and degrade to the replay path.

### Phase 4 — Make it a product

Distribution, deliberately last. Honest versions first (packages claim
0.2.0 with no tags and three format versions of drift), then npm + PyPI +
a `ps2ui` wrapper CLI (`build` / `dev` / `check` / `fontgen`), a format
stability pledge post-v6, and a docs pass with UC-3 as the flagship
tutorial.

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
