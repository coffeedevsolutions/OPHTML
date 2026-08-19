# Hardware bring-up checklist

The host toolchain is fully tested; the gsKit path is written against
the documented API but has not yet run on real silicon. This is the
ordered procedure for the first run on a console or emulator. Work the
steps in order — each one isolates a single subsystem, and later steps
are meaningless while an earlier one fails.

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

| what | how | expected |
|------|-----|----------|
| ground `#1a0e0a` | `gsKit_clear`, blending **off** | whole frame |
| red `#ff0000` | sprite, blending **off** | top left, full strength |
| magenta ladder | five sprites, blending **on**, alpha `0x20` `0x40` `0x60` `0x7f` `0x80` | bottom row |

Those are three different things, not two. `gsKit_clear` builds a
PACKED A+D list; `gsKit_prim_sprite` emits a sprite GIF tag with
SPRITE_REGS. So the probe separates **packet encoding**, then blending
on or off, then the alpha value. An emulator implementing one encoding
and not the other looks exactly like "untextured is broken".

Every rung of the ladder is the same colour and differs only in alpha,
so a missing rung cannot be blamed on the colour register. Over the
`#1a0e0a` ground, `(Cs - Cd) * As >> 7 + Cd` predicts each one exactly:

| alpha | composites to |
|-------|---------------|
| `0x20` | `#530a47` |
| `0x40` | `#8c0784` |
| `0x60` | `#c503c1` |
| `0x7f` | `#fd00fd` |
| `0x80` | `#ff00ff` |

**Expect:** the clear, the red control, and all five rungs. The ground
colour is the memcard canvas with its channels reversed, so a probe
fingerprint can never be mistaken for a UI capture in the same log.

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
- **Rungs present but the wrong colours** → compare against the table.
  Values above the prediction mean alpha is being ignored; below, that
  it is applied twice.
- **All rungs the same colour** → the colour register is not being
  reloaded between primitives, a gsKit queue problem rather than a blend
  one.
- **Wrong colours entirely** → RGBAQ packing order; verify
  `GS_SETREG_RGBAQ(r, g, b, a, q)` against your gsKit.

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

**Do:** enable TEXQUADs; look at any text.
**Expect:** legible antialiased glyphs.
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
`python3 tools/make_testcard.py testcard.uib --preview expected.png`
(it writes the .uib directly through the baker API — no HTML involved).
It draws a 1px-cell checkerboard texture at 1:1 in five positions and
1px rules hugging the canvas edges.
**Expect:** a crisp black-and-white checker (no gray mush), all four
edge rules visible.
**If checker is blurry/gray:** half-texel offset — sprite UVs need the
classic `+0.5` texel bias on this path; apply it in `ps2ui_render`'s UV
conversion (one place), not per-command in the baker, and re-run.
**If edge rules are missing on one side:** half-pixel primitive offset
or overscan — compare against gsKit's `OffsetX/OffsetY` handling before
touching the linter's safe areas.

## 7. Scissor nesting

**Do:** navigate so an ellipsized title redraws (tiles clip their text
via `overflow: hidden`).
**Expect:** text clips exactly at the tile's padding edge, identical to
the previewer.
**If wrong:** `GS_SETREG_SCISSOR` is inclusive on both ends — the
runtime passes `x1 - 1` / `y1 - 1`; an off-by-one here shows as a 1px
text bleed. Also confirm scissor state isn't cached across frames by
your app between `ps2ui_render` calls.

## 8. Interlace and flicker

**Do:** on a real CRT (or emulator interlace simulation), hold the
default screen still.
**Expect:** stable image; the linter has already flagged any 1px
horizontal lines at compile time, and the example contains none.
**If shimmering anyway:** field order / half-height framebuffer setup in
your gsKit init, not in the baked data — the blob is field-agnostic.

## 9. VRAM pressure

**Do:** check `ps2ui_upload`'s return value in the sample.
**Expect:** 0. The baker already enforces a budget at bake time
(`--vram-budget`, breakdown printed on every bake), so an alloc failure
here means your app allocates VRAM (framebuffers, other textures) beyond
what the budget assumed.
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
