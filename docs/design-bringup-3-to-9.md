# Bench instrument for bring-up steps 3–9

Steps 1, 2 and 10 are done. This is the design for the single ELF and
single probe screen that closes the rest, written before implementation
so the argument can be attacked while it is still cheap.

## What the last three rewrites taught

The step 2 probe was rebuilt three times. Every rewrite came from the
same root cause: **it asked the operator for a measurement.** Name this
colour. Count these bars. Is this the right shade of magenta.

A handheld photograph of a glossy panel cannot answer any of those. A
phone camera renders saturated magenta on an LED panel as violet, its
tone curve lifts a near-black ground into visible maroon, and off-axis
keystone destroys any attempt to measure a width. Measured on real
photographs: references of `#8c0784`, `#c503c1`, `#fd00fd` and
`#ff00ff` all came back within ten units of each other.

The version that worked asks **is there a line here**. Two swatches
share an edge; agreement is one rectangle, disagreement is a seam. That
judgement survives any exposure, white balance, angle or panel.

Three rules follow, and steps 3–9 are designed to them.

### R1 — Binary judgements, never measurements

Every check reduces to *seam or no seam*, *uniform or patterned*,
*present or absent*, *crisp or mush*. Nothing asks for a value.

### R2 — Every check carries a calibration that must fail

A check with no reachable failing state is not a check. This branch has
now found four:

| instrument | passed without the property holding |
|---|---|
| probe v2 calibration column | mismatch chosen where the camera clips; read seamless |
| CI capture aspect guard | root sized 2× the canvas, so untrimmed passed |
| step 7 tell quad | bakes at alpha `0x80`; invisible either way pre-fix |
| README blend claim | cited the two rungs where inverted and correct agree |

So each cell below ships a deliberately wrong twin that **must** show
the fault. If the calibration looks clean, the run is void, not a pass.

### R3 — Sabotage-test the guard, not just the code

Every assertion in `check.py` gets broken on purpose once, and the
failure recorded, before it is trusted.

## Step 7 — scissor nesting

`.tell` already exists: a magenta quad parked outside `.scissor`'s clip
but inside the canvas, so the scissor is the only thing that can hide
it. It proves a negative, which nothing else on the screen does.

**It is currently vacuous in one direction.** Invisible means either
"the scissor works" or "that quad never drew at all" — and the latter
is not hypothetical, since until the blend fix it *could not* have
drawn, at any scissor setting.

**Add `.tell-twin`:** the same 24×24 magenta quad, same `data-keep`,
placed *inside* the clip where it must be visible.

| twin | tell | verdict |
|---|---|---|
| visible | invisible | scissor works |
| visible | visible | scissor not reaching the GS |
| invisible | invisible | **void** — the quad never drew; says nothing about clipping |

## Steps 3, 4, 5 — CLUT, tinting, modulate domain

All three are currently "look at the text and decide if it seems
right", which is R1's failure mode exactly. All three become seams
without touching the runtime, because the baker already computes the
colour each one should produce: put a flat reference swatch of that
colour immediately beside the textured element.

- **Step 5 (modulate domain).** A glyph tinted at `0x80` is identity:
  `Cv = Ct·Cf >> 7`. Beside it, a flat quad of the raw texel colour.
  Seam ⇒ the 0x80-identity domain is wrong — a B1 regression, and the
  previewer normalises by 255 so it structurally cannot show this.
- **Step 4 (tinting).** ~~White texel tinted with a colour, against a
  flat quad of that colour.~~ Dropped: gsKit has no per-texture TFX
  field and hardcodes `TEX0.TFX = 0` (MODULATE) everywhere, so there is
  nothing here that could be off. See `docs/bringup.md` step 4.
- **Step 3 (CSM1 swizzle).** The interesting one, now worked out
  precisely — and it needs a baker change first.

  The CLUT is stored **linearly** in the `.uib`; the *runtime* permutes
  it on upload (`ps2ui_clut_csm1`). So step 3 asks whether that
  permutation agrees with the GS. It swaps bits 3 and 4 of the index,
  so with a correct permutation index `i` renders `linear[i]`, and with
  a wrong one index `i` renders `linear[csm1(i)]`.

  A straight swap is symmetric and therefore hard to see: two regions
  using indices `8` and `16` just exchange colours, which looks like a
  boundary either way. Break the symmetry with an index the swap does
  not touch.

  **Bit 3 probe.** Region A uses index `0` (bit3=bit4=0, unaffected),
  region B uses index `8`. Set `linear[0] = linear[8] = X` and
  `linear[16] = Y`, with `Y` violently unlike `X`.

  | | region A (idx 0) | region B (idx 8) |
  |---|---|---|
  | correct | `linear[0]` = X | `linear[8]` = X |
  | unpermuted | `linear[0]` = X | `linear[16]` = **Y** |

  Uniform is the pass; any visible boundary is the fail.

  **Bit 4 probe.** The permutation works on bits 3 and 4 of the whole
  index, so block 1 (indices 32..63) repeats the structure
  independently. Region C uses index `32`, region D uses index `48`;
  set `linear[32] = linear[48] = X` and `linear[40] = Y`.

  Together they isolate each bit rather than reporting "the text looks
  garbled", and the calibration is a third pair built with the
  permutation deliberately inverted, which must show the boundary.

  **Blocked on a baker change.** `_image_texture` runs
  `img.quantize(colors=256, FASTOCTREE)` on every palettized image, so
  it picks its own palette and authored indices do not survive. The
  tile needs the baker to preserve an already-indexed PNG's palette and
  index data verbatim.

  That is worth having on its own merits — re-quantizing an image that
  is already indexed is lossy for no reason — but it is a change to the
  baker with its own tests and its own review surface, so it belongs in
  its own pull request rather than stacked behind two example cells and
  a layout-package attribute. Resizing has to fall back to quantizing
  (LANCZOS on index values blends indices into nonsense), which the
  feature must say out loud.

## Step 6 — texel centres

`tools/make_testcard.py` already draws a 1:1 checkerboard; a half-texel
error turns it to grey mush. Crisp-or-mush is already binary. It needs
only R2: **a second card deliberately offset by half a texel**, which
must be mush. Without it, "I see mush" and "this panel cannot resolve a
1px checker at this distance" are the same observation.

## Step 8 — interlace and field order

Does a 1px horizontal rule shimmer. A human watching a screen judges
temporal flicker well, which a still photograph cannot capture at all —
so this step stays an operator report by design rather than by
omission. Calibration comes free: the linter already refuses 1px
geometry, so the cell has to opt in deliberately, and a band that does
*not* shimmer next to one that does is the control.

## Step 9 — VRAM pressure

`ps2ui_upload`'s return value, which `PS2UI_SAMPLE_TELEMETRY` already
prints. Not visual, needs no camera. Calibration: a build whose blob
deliberately over-reserves must return non-zero, proving the path
reports failure rather than only ever returning 0.

## Order of work

1. ~~`.tell-twin`~~ — done; closed a vacuity that was live on `main`
2. ~~Steps 4 and 5 vanish rows~~ — done, with the `data-nocontrast`
   exemption they needed
3. ~~Step 3 swizzle tile~~ — done, once the baker preserved authored
   palettes
4. ~~Step 6 calibration card~~ — done, as a resolution wedge: one
   checker could not separate a sampling fault from a panel limit
5. ~~Steps 8 and 9~~ — done. Both were unfalsifiable as written: step
   8 asked for a stable image on a screen with nothing that could
   shimmer, and step 9 expected a 0 that nothing proved could be
   anything else

Items 1 and 2 are one reviewable change: two probe cells, a lint
exemption plumbed through the layout package, and the checks that fence
them. Item 3 opens a second front in the baker. Splitting there keeps
each reviewable; stacking would not.

Each lands with its `check.py` assertions sabotage-tested per R3.
