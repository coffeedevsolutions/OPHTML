# Hardware bring-up checklist

The host toolchain is fully tested. This is the ordered procedure for
the first run on a console or emulator. Work the steps in order — each
one isolates a single subsystem, and later steps are meaningless while
an earlier one fails.

## Hardware log

What has actually run on silicon, as opposed to what is expected to.
Add a row per console; do not delete rows when a step later regresses.

| console | step | result |
|---|---|---|
| SCPH-50000 (NTSC, FMCB, USB) | 1 minimal | **pass** — blue, then back to the browser on its own |
| SCPH-50000 | 2 probe v1 | **inconclusive** — clear, control and ladder all drew, so packet encoding, ABE and the blend unit are live; the ladder itself could not be read from a photograph (see step 2) |
| SCPH-50000 | 2 probe v2 | **fault found** — columns 1, 2, 3 and 6 painted both halves; columns 4 and 5, alpha `0x7f` and `0x80`, painted the reference and nothing at all in the test half. Reproduced under Play!. See "What v2 found" below |
| SCPH-50000 | 2 probe v3 | **PASS, fix confirmed on hardware.** Upper ladder (gsKit default) seams at columns 1, 3, 4, 5, 6 with 4 and 5 dropping their test halves entirely; only column 2 is clean, `0x40` being the one rung where `128 - As` equals `As`. Lower ladder (fix applied) is solid through columns 1-5 with the calibration seam at 6. Exactly the predicted pattern, including which single column the bug leaves untouched |
| Play! (CI, llvmpipe) | 2 probe v2 | geometry confirmed to the pixel — columns landed at exactly the predicted coordinates, ticks 1-4 legible, both bracket rings present — but Play! applies the **wrong per-sprite alpha** to blended sprites (columns read 0x60/0x40/0x20/0x00 where 0x20/0x40/0x60/0x7f were submitted, while every unblended reference is exact). Its blend is not a verdict on anything |
| SCPH-50000 | 10 aspect | 4:3 pillarboxed into a 16:9 panel, which is correct behaviour and explains why step 1's fill does not reach the panel edges |

Reference material, in the order you will reach for it:

- `examples/channel6/` — the **conformance target**. Its `probe` screen
  puts one labelled cell per feature on a single frame, so most steps
  below reduce to "look at cell X and compare it to the previewer PNG".
  Build it with `./examples/channel6/build.sh`; the per-screen previews
  land in `examples/channel6/build/`.
- `runtime/sample/` — the standalone ELF, which embeds whatever blob you
  point `UIB=` at. By default it walks the focus states on a timer,
  which is what you want when you are the one watching. Build it with
  `make -C runtime/sample STATIC=1` to hold the baked initial focus
  instead: a timed capture then always lands on the frame `--preview`
  rendered, which is the only way an automated diff means anything. CI
  uses `STATIC=1` for exactly that reason.
- `tools/make_testcard.py` — the texel-alignment card, a narrower
  instrument for step 6 alone.
- The previewer PNGs are ground truth throughout. They replay the same
  baked blob the console does.

### Probe cells to bring-up steps

| probe cell | proves | step that fails without it |
|------------|--------|----------------------------|
| `probe-alpha`  | alpha ladder, GS 0-128 domain     | 2 |
| `probe-radius` | nine-patch corners, slice seams   | 6 |
| `probe-type`   | glyph atlas, CLUT, tinting        | 3, 4, 5 |
| `probe-clip`   | ellipsis and scissor clipping     | 7 |
| `probe-image`  | the same PNG as PSMCT32 and PSMT8 + CLUT, side by side | 3, 5 |
| `probe-flex`   | grow/basis and text alignment     | geometry sanity |
| `probe-aspect` | which aspect the panel is applying | 10 |

A cell that matches the previewer PNG clears its steps. A cell that
differs tells you which step to work, which is the whole reason the
screen exists.

**Emulators.** [Play!](https://purei.org/) needs no BIOS (HLE) and is
what CI uses; PCSX2 is more accurate but requires your own BIOS dump,
so it stays a local step. Emulator pass ≠ hardware pass — the GS's
texel addressing and blend quirks are exactly where emulators cut
corners. Treat PCSX2 in software-renderer mode as the most trustworthy
stand-in short of a console.

---

## 1. Boot and clear

**Do:** `make -C runtime/sample MINIMAL=1` and run it. It clears the
screen, holds for 30 seconds, and returns to the browser. Three gsKit
calls: no sprites, no blending, no textures, no blob.

**Expect:** a solid **blue** screen, then the browser again.

Blue confirms, in one frame, that the ELF loads and boots, dmaKit and
gsKit initialise, the video mode is accepted, the framebuffer flips,
and returning from main works — before a single primitive is
submitted. Run this first on any console you have not run on before,
so that if step 2 shows nothing you already know which half is at
fault.

**If wrong:**

- **Orange, not blue** — channel order. The clear is
  `RGBAQ(0x40, 0x80, 0xc0)`: strictly increasing, so correct is
  blue-dominant and byte-swapped is orange-dominant. Fix
  `GS_SETREG_RGBAQ` against your gsKit before going further; every
  colour in every later step is wrong too.
- **Black, then returns to the browser** — the loop ran and the GS
  drew nothing. Boot is fine, the video path is not.
- **Nothing, and never returns** — it hung before drawing. Suspect the
  ELF itself, the load, or gsKit init.



**Do:** run the sample ELF; it clears to the canvas background before
drawing anything.
**Expect:** a stable full-screen dark navy (`#0a0e1a`) frame, no rolling
or tearing.
**If wrong:** video mode init — check `gsKit_init_global` mode
(NTSC/PAL), interlace setting, and that the framebuffer PSM is CT32.
Nothing ps2ui-specific is involved yet.

## 2. Solid quads and the alpha blend unit

**Do:** `make -C runtime/sample PROBE=1` and run it. It draws solid
fills straight through gsKit and never calls `ps2ui_render`, so nothing
this repository's compiler or baker produced is on the path. (A `.uib`
is still *linked* into the ELF, so a baked blob has to exist for the
build to succeed. Nothing draws it.)

It holds its screen for 5400 frames — about 90 seconds on NTSC, 108
on PAL, since the loop counts fields and not wall clock — and then
returns to the browser,
deliberately rather than looping forever. A frozen console and a
working one look identical on a static screen, so the return is the
signal that separates them:

| picture | returns to browser | means |
|---|---|---|
| yes | yes | ran to completion — read the rungs |
| yes | no | hung after drawing |
| no | no | hung before drawing |
| no | yes | ran, and the GS drew nothing |

The last row is the interesting failure and the one an unbounded loop
could not distinguish from the third.

| what | how | expected |
|------|-----|----------|
| ground `#1a0e0a` | `gsKit_clear`, blending **off** | whole frame |
| white corner brackets | sprites, blending **off** | on the true frame edge |
| cyan corner brackets | sprites, blending **off** | on the title-safe box |
| red `#ff0000`, white `#ffffff` | sprites, blending **off** | top left, full strength |
| tick marks | sprites, blending **off** | 1..6 dots over each column |
| six columns | reference half blending **off**, test half blending **on** | middle band |

### Overscan first

Read the brackets before anything else, because they say whether the
rest of the frame is trustworthy.

| brackets visible | means |
|---|---|
| white and cyan | no overscan; the whole framebuffer reaches the panel |
| cyan only | the panel eats the edges, which is normal on a CRT and on a flat panel with overscan left on. Every swatch is inside the cyan box, so **the reading still stands** |
| neither | too much is being cropped to trust anything; fix the display before reading the ladder |

Everything that has to be read lives inside the 10% title-safe box
(x 64..576, y 45..403 of 640x448), and `runtime/sample/main.c` enforces
that with `#error` guards rather than trusting it. The previous layout
ran the ladder from x 20 to 620; Play! in fullscreen zooms 1.38x and
the CI capture cut the frame at x=433, taking column 6 with it. Column
6 is the calibration, so losing it converts a valid run into a void one
— an instrument whose validity depends on the outer tenth of a
television reports a fault in itself as a fault in the hardware.

Those are three different things, not two. `gsKit_clear` builds a
PACKED A+D list; `gsKit_prim_sprite` emits a sprite GIF tag with
SPRITE_REGS. So the probe separates **packet encoding**, then blending
on or off, then the alpha value. An emulator implementing one encoding
and not the other looks exactly like "untextured is broken".

### Reading it: seams, not colours

Each column is one blended swatch sitting directly under an unblended
swatch of the colour `(Cs - Cd) * As >> 7 + Cd` predicts. The runtime
computes that reference itself, in integer arithmetic identical to the
hardware's, and paints it literally. So:

- **no seam** — the GS blended exactly as the baker assumed
- **visible horizontal seam** — it did not, and the darker half says
  which way

| column | ticks | alpha | reference | test | verdict |
|---|---|---|---|---|---|
| 1 | ● | `0x20` | `#370a2b` | `0x20` | must match |
| 2 | ●● | `0x40` | `#55074d` | `0x40` | must match |
| 3 | ●●● | `0x60` | `#72036e` | `0x60` | must match |
| 4 | ●●●● | `0x7f` | `#8f008e` | `0x7f` | must match |
| 5 | ●●●●● | `0x80` | `#900090` | `0x80` | must match |
| 6 | ●●●●●● | `0x80` | `#900090` | `0x20` | **must seam** |

Both ladders carry the same six columns. Read each one the same way.

Column 6 is deliberately mismatched and is the calibration. Without it,
"I see no seam" is unfalsifiable — it could equally mean the observer,
the camera, or the panel cannot resolve a seam at all. **A run where
column 6 also looks seamless is a void result, not a pass.**

This replaced a v1 probe that asked the operator to name a colour and
count bars. On hardware that turned out to be unanswerable from a
photograph: a phone camera renders saturated magenta on an LED panel as
violet, its tone curve lifts the near-black ground to a visible maroon,
and off-axis keystone defeats measuring a width. Five bars read as
three and no re-shoot was going to fix it, because the question
required a measurement. "Is there a line here" survives any camera.

The tick marks fix counting the same way: a column that vanishes into
the ground is identified by the gap in the ticks rather than inferred
from the width of its neighbours. The corner marks answer step 10 early
— four visible corners means the whole framebuffer is reaching the
panel and every coordinate in between can be trusted.

**Expect:** the clear, both controls, four corners, six numbered
columns, seamless in 1-5 and seamed in 6. The ground colour is the
memcard canvas with its channels reversed, so a probe fingerprint can
never be mistaken for a UI capture in the same log.

**If wrong**, what is missing narrows the fault:

- **Nothing but black, or one uniform colour** → ambiguous, and the
  probe cannot settle it. It draws only untextured primitives, which is
  the class under suspicion, so it has no positive control: a blank
  frame equally means the ELF never reached a draw call, or the
  emulator window never got a frame. Read its log first. `framediff
  --stats-only` flags this case rather than letting it read as a
  verdict.
- **Clear and red only, no ladder** → the blend unit is dropping every
  blended primitive.
- **The ladder stops short** → `0x80` is the value a `.uib` calls
  opaque, so if the top rungs are missing, every opaque quad in every
  blob is invisible while text, whose alpha comes from the atlas, still
  draws. Do **not** "fix" that by scaling alpha down: the file domain is
  correct (see `docs/format-uib.md`) and a real GS treats `0x80` as 1.0.
- **Seams in columns 1, 3 and 5 but not 2 and 4** → the ladder is
  running backwards: the alpha applied to each sprite is not the one the
  packet carried. Play! does exactly this (see below), and it is a
  failure v1 could not have detected — a reversed ladder and a correct
  one look identical when nothing says which rung is which. The tick
  marks are what make it visible.
- **Cyan brackets missing** → void run. Read the overscan table first;
  nothing below means anything until the safe box is on screen.
- **Column 6 seamless too** → void run, not a pass. The comparison had
  no resolving power under those conditions; reshoot closer, straighter,
  or with the room darker before believing columns 1-5.
- **Columns seamed, test half brighter** → alpha is being ignored or
  partly ignored; darker means it is being applied twice.
- **All rungs the same colour** → the colour register is not being
  reloaded between primitives, a gsKit queue problem rather than a blend
  one.
- **Wrong colours entirely** → RGBAQ packing order; verify
  `GS_SETREG_RGBAQ(r, g, b, a, q)` against your gsKit.

### What v2 found

Blended sprites at alpha `0x7f` and `0x80` produce nothing. Their
reference halves — the same rectangles, same vertex alpha `0x80`, drawn
with blending **off** — paint correctly, so this is not a discard: an
alpha test rejecting high alpha would have taken the references too.
The only difference between a reference that draws and a test that
vanishes is ABE. The fault is in the blend.

`0x80` is the value every `.uib` calls fully opaque. On this reading
every opaque quad in every blob would be invisible while text, whose
alpha comes from the atlas, still draws.

**Cause, confirmed by measurement.** Nothing in this tree had ever
written the GS blend state:

    $ grep -rn "PrimAlpha\b\|GS_SETREG_ALPHA\|gsKit_set_test\|PABE" runtime/
    (nothing)

`runtime/ps2ui.c` and the sample toggle `PrimAlphaEnable` and stop
there. The `ALPHA` register, the `TEST` register and `PABE` are
whatever `gsKit_init_screen` left behind, while the baker computes
alpha in the 0..128 domain assuming `(Cs - Cd) * As >> 7 + Cd` with `C`
selecting `As`. Nothing asserted that, on either side.

Decoding what each test swatch actually composited to gives the
effective coverage the GS used, and it fits one rule on all six rungs:

| submitted `As` | effective | `128 - As` |
|---|---|---|
| `0x20` | `0x60` | `0x60` |
| `0x40` | `0x40` | `0x40` |
| `0x60` | `0x20` | `0x20` |
| `0x7f` | `0x00` | `0x01` |
| `0x80` | `0x00` | `0x00` |

**Alpha was running exactly inverted.** gsKit's default `ALPHA` is
`GS_BLEND_BACK2FRONT` = `0x01`, which decodes to `A=Cd B=Cs C=As D=Cs`
— the operands swapped — giving `(Cd - Cs) * As >> 7 + Cs` instead of
`(Cs - Cd) * As >> 7 + Cd`. A quad the format calls fully opaque
composited to pure background and vanished; a nearly transparent one
painted at almost full strength.

The fix is one line in `ps2ui_render`, run every frame because the
value is global GS state:

```c
gsKit_set_primalpha(gs, GS_SETREG_ALPHA(0, 1, 0, 1, 0), 0);
```

Note **`gsKit_set_primalpha`**, not `gs->PrimAlpha = ...`. Assigning the
struct field does not emit the register. v3's first draft assigned it,
the lower ladder came back byte-identical to the upper one, and that
silence is what identified the call.

`runtime/tests/test_runtime.c` now fails if the runtime stops asserting
it — verified by deleting the line and watching the checks go red, not
assumed.

CI confirms the fix under Play!. Solving each rendered swatch back to
the coverage that would produce it puts the before and after in one
frame:

| col | submitted `As` | upper ladder (gsKit default) | lower ladder (fixed) |
|---|---|---|---|
| 1 | `0x20` | `0x60` | `0x20` |
| 2 | `0x40` | `0x3f` | `0x40` |
| 3 | `0x60` | `0x20` | `0x60` |
| 4 | `0x7f` | `0x00` | `0x7f` |
| 5 | `0x80` | `0x00` | `0x80` |

`128 - As` on every rung of the upper ladder; the identity on every
rung of the lower one, to within a unit.

**Hardware agrees.** A SCPH-50000 reading probe v3 shows the upper
ladder seamed at 1, 3, 4, 5 and 6 — with 4 and 5 half-height, their
test swatches composited entirely away — and the lower ladder solid
through 1-5 with the calibration seam at 6. Column 2 is the only clean
rung upstairs, which is itself a signature: `0x40` is the single alpha
where `128 - As` equals `As`, so it is the one value the bug cannot
disturb. Bring-up step 2 passes.

### What the fix did to the UI capture

The emulator's UI diff is characterisation, not a verdict, but it moved
a long way:

| | before | after | previewer |
|---|---|---|---|
| mean rgb | `(10.3, 10.6, 11.1)` | `(36.3, 37.5, 49.5)` | `(37.0, 38.3, 50.2)` |
| dominant | 92.8% `#000000` | 52.8% `#0a0e1a` | 58.6% `#0a0e1a` |
| global RMSE | 72.89 | 22.89 | — |

The old "92.8% pure black" reading was long treated as evidence that
untextured geometry never drew. It drew; it composited itself away. The
render loop clears with ABE on at alpha `0x80`, and under gsKit's
default that resolves to the destination — the previous framebuffer —
instead of the clear colour. Text survived because its alpha comes from
the atlas rather than from `0x80`.

RMSE 22.89 against a tolerance of 8 still fails, and should: Play! is
not an oracle and this number is a characterisation to watch, not a
gate. What changed is that it is now measuring the renderer rather than
a broken capture.

### Why this made another instrument un-failable

Bring-up step 7's scissor tell quad bakes to `(255, 0, 255, 128)`. That
alpha is `0x80` — the exact value this bug composited away to nothing.
Under the pre-fix runtime the tell quad would have been invisible on
hardware **whether or not the scissor was applied**, so the step 7
instrument would have passed vacuously.

That is the second instrument in this repository that could not fail,
after the probe's own v2 calibration column. Both were caught by
asking, of every check, what result would prove it wrong. Any
step-7 hardware claim predating this fix is void and needs re-running.

### Reading these photographs

Rectifying a photo against the cyan brackets and sampling framebuffer
coordinates works well in daylight and produced the numbers above. It
failed outright on an evening set: with the room dark the camera blew
the blue channel across the whole picture, cyan stopped being
distinctive, the homography collapsed, and the red control square
mapped to `rgb(41, 75, 143)`.

The **tick-mark count is the check that catches this**. If sampling the
tick row does not return 1, 2, 3, 4, 5, 6 in order, the mapping is
wrong and nothing else measured from that frame means anything. Do not
read the columns until the ticks read straight.

That case is also why the seam design matters: the operator standing in
front of the panel read the frame correctly when the automated pass
could not. "Is there a line here" and "is this block shorter than its
neighbours" survive conditions that defeat any attempt to sample a
colour.

**A trap worth knowing about.** The first capture of the two-ladder
build showed *both* ladders clean, which looked like a pass and was
not. `probe_frame` runs every frame, so the `gsKit_set_primalpha` at
the bottom persists into the next frame and from frame two onward the
"inherited" ladder inherits the fixed state. A capture twenty seconds
in was comparing the fix against itself. The probe now latches gsKit's
default on the first frame and restores it explicitly before the upper
ladder. This is the same hazard as the `PrimAlphaEnable` note above
`gsKit_clear`, and the reason `ps2ui_render` re-asserts the blend per
frame instead of once at init: **GS blend state is global and it
survives your frame.**

| upper ladder | lower ladder | means |
|---|---|---|
| seams at 4 and 5 | clean | the state was the fault — the runtime needs those three lines |
| seams at 4 and 5 | seams at 4 and 5 | the state is not the fault, or gsKit applies it at queue-exec rather than per primitive |
| clean | clean | not reproducible; check the build actually changed |

v3 also drops the source colour from `#ff00ff` to `#900090`. Measuring
the v2 photographs channel by channel showed the panel and camera
together clip hard — references of `#8c0784`, `#c503c1`, `#fd00fd` and
`#ff00ff` all came back within ten units of each other — so the top of
the ladder was unreadable and the v2 calibration column compressed into
a false "seamless". The blend is linear in `Cs`, so a dimmer source
tests the same thing and can be read.

### What CI can and cannot tell you here

CI runs this probe under Play! on llvmpipe and prints the palette, so
the `hw` log gives you an early hint without a console. Treat it as a
hint. Play!'s GS is materially less accurate than PCSX2's, and
untextured primitives and GIF packing are exactly where it diverges, so
a failure there is at least as likely to be an emulator gap as a ps2ui
bug. **This step is not answered until a console or PCSX2 in software
mode has run it.** As of this writing Play! 0.72 renders the clear, the
red control and the `0x20`/`0x40`/`0x60` rungs, and does not render the
top of the ladder; whether real hardware agrees is unknown.

Two notes for when you are looking at an actual CRT. The red control
starts at y=40 and the ladder ends at y=408, both outside the ~10%
title-safe box this project's own linter enforces, so a television may
clip those edges: judge presence, not framing. And saturated `#ff0000`
and `#ff00ff` are precisely what the composite-bleed lint warns about,
so a palette fingerprint of a composite capture will smear across
dozens of neighbouring colours. The fingerprint method is for digital
captures; on composite, use your eyes.

## 3. CLUT upload and the CSM1 swizzle

**Do:** look at the bar across the top of the probe screen's
`IMAGE` cell.

**Expect:** a flat dark-teal bar with **one bright-orange stripe hard
against its right edge** — nothing else.

The two colours are 119 apart in Rec.601 luma and 108 in Rec.709, so
the stripe survives a monochrome capture, a badly tinted CRT, or a
photograph with the saturation crushed. The pair before them looked
emphatic and was 1.2 apart in Rec.709 — #636363 against #747474 in
greyscale — which is the same trap the step 2 ladder fell into.

    correct        [ X X X X X | Y ]
    bit 3 wrong     X Y X X X | Y      stripe appears at 1/6
    bit 4 wrong     X X X Y X | Y      stripe appears at 3/6
    no permutation  X Y X Y X | Y

The stripe's *position* names which bit failed, so the cell does not
only say "wrong". Verified against the real baked CLUT: skipping the
permutation changes exactly regions 1 and 3, which are the two probes.

**The rightmost stripe is the calibration.** Its two indices carry
genuinely different palette entries and both sit below bit 3, so no
permutation — right or wrong — can remove it. If it is missing, this
cell cannot show you a stripe at all: the run is **void, not a pass**,
and nothing above it means anything.

Built by `tools/make_swizzle_tile.py`, which carries the construction
and the reason a straight swap of two indices would have been
invisible: swapping two regions is symmetric, so it looks like a
boundary either way. The tile breaks that symmetry with index 0, which
the permutation does not touch. `check.py` asserts the traps still
differ from the probes, because if `linear[16]` ever equalled
`linear[8]` a bit-3 fault would render identically to a correct upload.

**Do (secondary):** look at any text; legible antialiased glyphs mean
the atlas path agrees too.

**If wrong (glyphs render as banded/garbled noise):** the CSM1
permutation. CLUTs are stored *linearly* in the .uib; the runtime
permutes on upload via `ps2ui_clut_csm1()` (bit-3/bit-4 swap). If your
gsKit or GS path expects a linear CLUT (CSM2, or a gsKit that permutes
internally), you are double-permuting — the involution means applying
it twice is the identity, so symptoms are: correct = permuted once,
garbled in 8-entry bands = zero or two times. Toggle the `permute_clut`
call and compare.

## 4. Text tinting and `GSTEXTURE::Function`

**Do:** look at text colors.
**Expect:** metadata text in muted gray-blue, titles in near-white —
matching the previewer.
**If wrong (all text pure white):** your gsKit predates
`GSTEXTURE::Function`; ps2ui.h autodetects this (via the `GS_TFX_*`
macros) and falls back to DECAL (untinted). The ps2dev container's
bundled gsKit is one of these — CI's ELF renders white text by design.
Upgrade gsKit for tinting, or accept white text.
**If text draws as solid rectangles:** modulate is on but the atlas
CLUT alpha ramp is wrong — recheck step 3.

## 5. The modulate color domain

**Do:** compare mid-tone text (`#8b94a7` tile metadata) against the
previewer PNG side by side.
**Expect:** visually identical brightness.
**If wrong (text washed out / clipped toward white):** a B1 regression —
TEXQUAD vertex colors must be in the 0x80-identity domain
(`Cv = Ct·Cf >> 7`). The runtime test's "texquad colors in the 0x80
modulate domain" check should have caught this before it reached
hardware; if hardware disagrees with a passing test, the blend/TEX0
setup is applying a second scale — check TEXA/TEXFLUSH state and that
`Function` is MODULATE, not HIGHLIGHT.

## 6. Texel and pixel centers (the test card)

**Do:** build and run the alignment card:

    python3 tools/make_testcard.py testcard.uib --preview expected.png

The card carries **three** instruments, and they fail in different ways.

**Expect (1) — the wedge.** Across the canvas centre: a flat grey
patch, 1px, 2px and 4px checkers, then another flat patch. All three
checkers crisp and obviously unlike the grey at either end.

**Expect (2) — the edge rules.** Four 1px colour-coded rules hugging
the canvas edges: **red top, green bottom, blue left, yellow right**.
All four visible.

**If a rule is missing on one side:** a half-pixel *primitive* offset,
or overscan. That is a different fault from the wedge's half-texel *UV*
offset — different code, different fix — which is why the colours name
the side. Compare against gsKit's `OffsetX`/`OffsetY` handling before
touching the linter's safe areas.

**Expect (3) — the corner checkers.** The finest checker repeated at
the four corners of the title-safe box. **Read these only once the
wedge shows 1px crisp.** They have no coarser rung beside them, so on
their own they carry exactly the fault-versus-limit ambiguity the wedge
exists to remove — and they sit where CRT focus and convergence are
worst and overscan crops first, so a mushy corner is more likely to be
the panel than the centre ever was.

**One checker cannot tell a fault from a limit.** A 1px checker
photographed as grey means either the sampling is off by half a texel
or the panel cannot resolve 1px from where the camera is standing, and
those two look identical. That is why there are three:

| 1px | 2px | 4px | reading |
|---|---|---|---|
| crisp | crisp | crisp | **pass** |
| grey | crisp | crisp | real sampling fault |
| grey | grey | crisp | the panel's resolution limit — the 1px result is **void** |
| grey | grey | grey | void; read nothing from this cell |

The flat patch is what a mushed checker looks like, sitting beside them
so the comparison is side by side rather than remembered. Every checker
averages the same 50% grey, which is exactly why a mushed one is
indistinguishable from it — and exactly why it is worth drawing.

**If wrong:** a half-texel UV offset. The baker emits texel-corner UVs
and the GS samples at pixel centres; the `+0.5` convention has to match
on both sides. Under bilinear a mismatch averages neighbouring texels
into grey; under nearest it shifts the checker by one cell, which the
corner copies make visible against the canvas edges.

`make_testcard.py --self-test` fences the construction, and CI runs it.
The property that matters most there is the 1:1 mapping: a wedge quad
drawn at any size other than its UV span makes the GS resample, and a
resampled checker mushes for reasons that have nothing to do with texel
centres — a false fault reported confidently on correct hardware.

## 7. Scissor nesting

**Do:** navigate so an ellipsized title redraws (tiles clip their text
via `overflow: hidden`), and look at the probe screen's CLIP cell.
**Expect:** text clips exactly at the tile's padding edge, identical to
the previewer — **and no magenta anywhere on the probe screen.**

The probe's CLIP cell carries a 24px magenta quad parked at x=603,
outside the cell's clip rect (x=479..594) but inside the 640px canvas.
A correct GS never rasterizes it, so it is invisible and the screen
looks the same with or without it. Magenta on screen means the scissor
rect is not reaching the hardware at all.

That is a positive test for a negative, which nothing else here
provides: every other check on this screen confirms something *is*
drawn, and a scissor that silently does nothing looks identical to a
scissor that works whenever the clipped content would have fitted
anyway. It survives the baker's dead-geometry trim only because it is
marked `data-keep`; `examples/channel6/check.py` asserts it stayed
outside its clip and inside the canvas, since a drift in either
direction turns it back into a quad that proves nothing.
**If wrong:** `GS_SETREG_SCISSOR` is inclusive on both ends — the
runtime passes `x1 - 1` / `y1 - 1`; an off-by-one here shows as a 1px
text bleed. Also confirm scissor state isn't cached across frames by
your app between `ps2ui_render` calls.

## 8. Interlace and flicker

**Do:** run the test card on a real CRT (or an emulator that simulates
interlace) and look at the **interlace pair** below the wedge: a 1px
rule above a 2px rule, same width, same x, same colour.

**Expect:** the **thin one flickers**, the thick one sits still.

| thin | thick | reading |
|---|---|---|
| flickers | steady | interlaced as expected — **pass** |
| steady | steady | **check `gsGlobal->Field` first**, then progressive output or a deinterlacing panel. **Void** either way |
| flickers | flickers | field order, or a half-height framebuffer, in your gsKit init |

**When nothing flickers, look in your own code before your
television.** gsKit defaults `gsGlobal->Field` to `GS_FIELD` (FFMD 0),
where each field reads every other line — which is what makes a 1px
rule live in one field and flicker. Set it to `GS_FRAME` (FFMD 1) and
every field reads every line: both rules sit still, on a perfectly
interlaced output, and this cell reads void forever with no hint why.

ps2ui's own sample never overrides it, so the pair reads as documented
there. But ps2ui is a library inside a host program that owns
`gsKit_init_screen` — which is exactly the OPL-class integration
`docs/PLAN.md` is built around — so the host can change this out from
under the cell.

It matters past step 8. The CRT lint rule and `ps2ui-check`'s hairline
warning — *"no 1px quads to shimmer on an interlaced CRT"* — are
premised on FFMD 0, and **this pair is the only thing in the tree that
tests that premise.** A void reading here means the linter's advice is
unverified, not merely that the step is inconclusive.

A 1px rule on a 480i output lives in one field and so flickers at 30 Hz;
a 2px rule spans both and does not. That is physics, not a fault, and it
is what makes the pair readable.

**This step used to be unfalsifiable.** It said "expect a stable image"
over an example the linter had already stripped of every 1px line — a
screen with nothing that could shimmer, confirmed not to shimmer.
"Nothing moved" was both the pass and the void, and no one could tell
them apart. The thick rule is what separates them now.

**No photograph can capture this.** Step 8 is an operator report by
design rather than by omission; a still frame cannot show a 30 Hz
alternation. Watch it, do not shoot it.

Nothing here is in the baked data; the blob is field-agnostic.

## 9. VRAM pressure

**Do:** run the sample and read `ps2ui_upload`'s return value.
`make -C runtime/sample TELEMETRY=1` prints it.

**Expect:** 0. The baker enforces a budget at bake time
(`--vram-budget`, breakdown printed on every bake), so a failure here
means your app allocates VRAM — framebuffers, other textures — beyond
what the budget assumed.

**Why 0 means something.** A return value nobody has ever seen be
non-zero is not a check: it gives the same answer on a console with 4 MB
free and on one with none. `test_runtime` starves the stub allocator to
the real 4 MB ceiling and asserts the upload reports failure, so the
path is known reachable before anyone reads a 0 off a console. Deleting
the `return -1` in `ps2ui_upload` fails that check.

Both shapes are covered: nothing fitting at all, and — the case a real
console actually meets — running out **partway**, with earlier textures
already allocated and uploaded (measured at 18 of 19).

**What a non-zero leaves behind:** `ctx->uploaded` stays 0 however far
the upload got, so a caller cannot render through a half-built texture
table. Asserted for both shapes.

**Retrying:** call `gsKit_vram_clear()` first. gsKit's `USERBUFFER`
allocator is a bump pointer with no per-allocation free, so the
handles the failed attempt already took are stranded — and
`ps2ui_upload` restarts from texture 0 and re-allocates every one of
them. A second attempt without the clear consumes the footprint twice
and is likelier to fail than the first.

**Fix:** re-bake with `--vram-budget` set to what your app actually
leaves free, and treat the printed per-texture breakdown as the
negotiation table.

## 10. Display aspect

**Do:** look at `probe-aspect`. It draws three boxes, all 34
framebuffer lines tall, each pre-squashed for a different pixel aspect.
Exactly one reads square, and which one it is names what the television
is doing:

| box | width | reads square when |
|-----|-------|-------------------|
| gold  | 34px | pixels are drawn square (PAR 1.0 — a framebuffer capture, no TV) |
| blue  | 36px | the panel is showing 4:3 (PAR 0.9333) |
| green | 27px | the panel is stretching to 16:9 (PAR 1.2444) |

The widths are baked, so this cell reads identically in a `ntsc` and a
`ntsc16x9` build. It measures the display, not the blob.

**Expect:** blue square on a 4:3 set or a 16:9 panel in pillarbox mode;
green square with the panel stretching. Gold square means you are
looking at a screenshot, not a television.

**Then:** compare the rest of the screen against the right reference.
`--preview-display` writes the PNG resampled to the panel's aspect;
that is the one to hold up against a photograph. The 1:1 `--preview` is
a picture of the framebuffer and will disagree with the TV by 7% at 4:3
and 24% at 16:9.

**Fix:** bake with the aspect you are actually displaying at —
`--mode ntsc16x9` for a stretching panel, `--mode ntsc` for 4:3 or
pillarbox.

### Testing both aspects on one panel

Worth doing deliberately, and `./examples/channel6/build.sh` bakes both
blobs for it:

| blob | mode | reference PNG |
|------|------|---------------|
| `build/ui.uib` | `ntsc` (4:3) | `build/preview-display.png` |
| `build/ui-16x9.uib` | `ntsc16x9` | `build/preview-16x9-display.png` |

1. Boot `ui.uib` with the TV in 4:3 / pillarbox. Blue reads square, the
   screen matches `preview-display.png`.
2. Switch the TV to stretch without changing the blob. Green now reads
   square and everything is 33% too wide. This is the failure you are
   learning to recognize.
3. Boot `ui-16x9.uib` with the TV still stretching. Green still reads
   square (it is a display measurement) but the layout matches
   `preview-16x9-display.png` again.

A UI that looks the same in both TV modes means the aspect never
reached the hardware at all.

---

## When all ten pass

Update `docs/architecture.md`'s status section ("not hardware-verified"
→ verified, with the gsKit version and hardware/emulator used), close
backlog items B3 and the verification half of F1, and pin the working
gsKit commit in CI.
