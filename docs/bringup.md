# Hardware bring-up checklist

The host toolchain is fully tested; the gsKit path is written against
the documented API but has not yet run on real silicon. This is the
ordered procedure for the first run on a console or emulator. Work the
steps in order — each one isolates a single subsystem, and later steps
are meaningless while an earlier one fails.

Reference material: `runtime/sample/` (the standalone ELF used by CI),
`tools/make_testcard.py` (the alignment test card), and the previewer
PNGs from `examples/memcard/build.sh`, which are the ground truth every
step compares against.

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

**Do:** let the sample draw only `OP_QUAD` records (build it with
`-DPS2UI_SAMPLE_SOLID_ONLY` or comment out the TEXQUAD branch).
**Expect:** the panel layout of the memcard example in flat colors,
matching the previewer geometry exactly; translucent panels (the
`#11162400` card-info fill is fully transparent) must not double-darken.
**If wrong:**
- Everything half-transparent → alpha domain regression: quads carry
  GS-domain alpha (0x80 = opaque) and the blend equation must be the
  gsKit default `(Cs - Cd) * As >> 7 + Cd`. Do not "fix" it by scaling
  alpha up — the file domain is correct (see `docs/format-uib.md`).
- Wrong colors entirely → RGBAQ packing order; verify
  `GS_SETREG_RGBAQ(r, g, b, a, q)` argument order against your gsKit.

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
`GSTEXTURE::Function`; the runtime compiled with
`PS2UI_GSKIT_HAS_FUNCTION=0` renders DECAL (untinted). Upgrade gsKit or
accept white text.
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

---

## When all nine pass

Update `docs/architecture.md`'s status section ("not hardware-verified"
→ verified, with the gsKit version and hardware/emulator used), close
backlog items B3 and the verification half of F1, and pin the working
gsKit commit in CI.
