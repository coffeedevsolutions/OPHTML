# Bench runbook — Phase 1, the streaming sitting

One sitting. Read this page and nothing else; it assumes a PS2, a USB
drive and a television, and no memory of Phase 0.

Phase 1 rewrote the resource model: the context is sized from the blob
through an arena you supply, texture slots became a first-class kind
the app fills at runtime, the table ceilings are gone, and compositing
two screens in one frame is a contract. **None of it has been on a
console.** Every claim below was verified on a 64-bit host or under an
emulator, and this page is where that stops being enough.

The reason it stops being enough is specific. `ps2ui_tex_set` hands the
GS a pointer to memory the EE just wrote through a **write-back cache
the GIF cannot see**, then writes it back by hand. Cache and DMA are
the one fault class emulators only partially model — it is what #40
was, and #40 was the root cause of every garbled screen in this
project's history.

---

## Before you start

**Get the files.** From the latest green `hw` run on `main`, download
two artifacts:

| artifact | what you need from it |
|---|---|
| `ps2ui-sample-elf` | `covers.elf`, `covers-nosync.elf` |
| `bench-stream` | `cover0.raw` .. `cover3.raw`, and the three `preview-*.png` |

**Put the covers on the drive**, in a folder named exactly `ps2ui` at
the root:

```
<drive>/ps2ui/cover0.raw
<drive>/ps2ui/cover1.raw
<drive>/ps2ui/cover2.raw
<drive>/ps2ui/cover3.raw
```

Each is exactly **65,536 bytes**. Check that on the drive after
copying, not before — a copy that reports success and has not flushed
is the classic way to spend an hour reading a photograph of the wrong
build.

**To use your own art instead**, run the bake with it. This is the
whole point of the feature, so it is worth doing:

```sh
./fixtures/bench-stream/build.sh ~/Art/one.png ~/Art/two.png \
                                 ~/Art/three.png ~/Art/four.png
```

Anything Pillow opens works. Each image is cover-fitted and
centre-cropped to 128×128 — the reservation is one fixed size the blob
has already told the runtime, so the picture bends, not the geometry.
Fewer than four images is fine; the rest are filled with the synthetic
pattern. The script then rewrites `preview-filled.png` and
`preview-composited.png` from your art, and **those are the references
you compare the television against**, so re-download or re-copy them
after baking.

**Copy the ELFs under fresh names.** Every stale-file incident on this
project came from an old copy sitting on the drive under the name you
were about to boot.

**There is no memory-card step.** The blob is compiled into the ELF;
the covers are not. That split is the feature: the console reads art it
was never baked with.

---

## The three words that matter

| | |
|---|---|
| **PASS** | the property holds |
| **FAIL** | the property does not hold — record it, keep going |
| **VOID** | the instrument could not answer; the calibration says so |

**Void is not a failure and it is not a pass.** Each step below names
the calibration that detects its own void state. If you hit one, note
it and move on.

---

## What a flat screen means

Before anything below, if the television shows one flat colour edge to
edge, that is the ELF talking, not the renderer. **Read it off the
screen, not off a photo** — a phone renders saturated magenta as violet
and lifts near-black to visible maroon.

| fill | means |
|---|---|
| dark red | the blob failed to load — including an arena too small |
| olive / dark yellow | the upload ran out of VRAM |
| magenta (violet on a photo) | the ELF asked for a screen this blob does not have |
| **black, or no picture** | it did not boot. Nothing below applies |

---

## How `covers.elf` behaves

**Five phases on the first lap, four forever after**, five seconds
each. Looping is deliberate: a photograph that misses its moment comes
round again instead of costing a reboot.

`0 EMPTY` is the exception and it happens **once, at the top**. That is
not a quirk, it is the honest shape of the thing: `ps2ui_tex_set` has
no "unset" and should not have one, so once the slots are filled there
is no way back to empty without reloading. **Photograph S1 in the
first five seconds or reboot for it.**

The first version of this ELF got that wrong -- it fired the fill on
frame 0 while its own comment promised a five-second hold -- and step
S1 came back VOID from a console because of it. The schedule and the
on-screen label are both fenced by the host suite now.

**You do not need to time anything.** The screen says which phase it is
in, on the line labelled `state:`. A photo of this ELF labels itself.

Two lines under the covers carry everything you need:

```
src:   mass:/ps2ui  (4 x 65536 B)        <- or SYNTHETIC, with the reason
state: 2 SWAP: slot 0 now shows cover 3
tex_set rc: 0 0 0 0                      <- 0 is PS2UI_OK
```

**Read `src:` first.** If it says `SYNTHETIC`, the drive was not
readable and it names why. Everything below still runs on the generated
pattern, so **the sitting is not wasted**; only step S6 needs the drive.

The ELF now brings the USB stack up itself, so the failure modes have
changed since the first sitting:

| `src:` says | means |
|---|---|
| `mass:/ps2ui (4 x 65536 B)` | the drive was read. S6 is live |
| `no IOP modules embedded` | the build found no mass-storage stack in its SDK. My problem, not yours |
| `<stack> <module>: id N rc M` | a module refused to load, and which one |
| `<stack> loaded, mass: never appeared` | the drivers came up but no device enumerated in two seconds. Try a different stick or port |
| `open coverN: -1` | the device is there but that file is not. Check the folder is named `ps2ui` and sits at the drive root |
| `coverN M B, want 65536` | the file is the wrong size — the art was converted at other than 128×128 |

The first sitting reported `open cover0: -1` from a stick whose files
were verified byte-exact. That was not the drive: wLaunchELF launches
via `LoadExecPS2`, which **resets the IOP**, so the launcher's own USB
drivers were gone before the ELF ran. Nothing survives that reset, so
the ELF carries the modules now.

---

## Step S1 — an unfilled slot draws nothing

**Boot `covers.elf`. Photograph the first five seconds**, while
`state:` reads `0 EMPTY`.

The four cover boxes must be **empty** — the page background, nothing
in them. Compare against `preview-unfilled.png`.

- **PASS** — four empty boxes, the title and captions drawn normally.
- **FAIL, and this is the important one** — anything at all inside a
  box. Garbage, noise, a piece of another texture, a flat block of
  colour. Their VRAM is reserved and committed at upload; if the GS is
  drawing *from* it before anything was sent, `render` is not skipping
  unfilled slots and every one of them is a window onto stale VRAM.
- **VOID** — if `state:` is not `0 EMPTY` in your photo, you missed
  it. This phase does not come round again; reboot and shoot the first
  five seconds.

---

## Step S2 — `ps2ui_tex_set` puts the caller's texels on screen

**Photograph while `state:` reads `1 FILL`.**

Four covers, left to right, matching `preview-filled.png`.

- **PASS** — four covers, each a coarse checker (or your art), each
  with a crisp white border all the way round and a white block in its
  top-left corner.
- **FAIL** — boxes still empty while `tex_set rc:` reads `0 0 0 0`.
  Accepted and not drawn is a renderer fault.
- **FAIL, differently** — `tex_set rc:` shows a non-zero. `-10` is
  `NOT_STREAMED` (wrong name or a baked slot), `-11` is `SIZE` (the
  file is not the reservation), `-8` is `ALIGN`. That is the API
  refusing, not the GS misdrawing, and the number says which.
- **The reading that matters most** — covers present but **wrong**:
  torn, striped, shifted by a few texels, or showing the right shapes
  in wrong colours. That is the cache/DMA fault class. Go to S3 before
  concluding anything.

> **The white border is the instrument.** It is one texel wide on all
> four sides. If any edge is missing or doubled, the texels are
> arriving at an offset — that is a stride or alignment fault, not a
> colour one, and the border is what makes it visible from arm's
> length.

---

## Step S3 — what a live cache fault looks like

**Only if S2 looked wrong.** Skip it otherwise; it takes two minutes
and it is a picture, not a test.

**Boot `covers-nosync.elf` and photograph phase `1 FILL`.**

If instead the covers looked *right* but the **text** looked wrong,
that is a different finding and it has its own instrument -- see
step S7.

This is the same ELF with the cache writeback removed from
`ps2ui_tex_set`. The EE wrote the texels through a write-back cache the
GIF cannot see, so the GS DMAs whatever happened to be in RAM at that
address.

Hold the two photographs side by side:

- **They look the same** → the writeback is not doing its job on this
  console, and S2's failure is the cache fault. This is a real finding;
  record both photos.
- **They look different** → the writeback is working, and whatever S2
  showed has another cause. Record both anyway; a picture of the fault
  is worth having.

This is the same role `conform-noalpha.elf` plays in Phase 0: showing
what a hypothesis predicts, not testing it.

---

## Step S4 — the slot can be repointed mid-run

**Photograph while `state:` reads `2 SWAP`.**

Slot 0 has been pointed at cover 3's texels. The **leftmost** box must
now show what the **rightmost** box shows. Both display cover 3.

- **PASS** — first and last boxes identical, middle two unchanged.
- **FAIL** — the leftmost box still shows cover 0. The texture manager
  is holding it resident from the first `tex_set` and drawing the old
  cover out of VRAM; the invalidate is not landing.
- **VOID** — if your covers all look alike, this step cannot answer.
  That happens if you supplied four near-identical images. Re-bake with
  no arguments to get the synthetic set, which is built in six
  distinguishable hues for exactly this reason.

Phase `3 RESTORE` puts cover 0 back. That is the same assertion in the
other direction and a free second reading.

---

## Step S5 — two screens composite in one frame

**Photograph while `state:` reads `4 COMPOSITE`.** Compare against
`preview-composited.png`.

A translucent panel over the covers, with `OK` and `CANCEL`.

- **PASS** — the covers are **still visible** around and behind the
  scrim, dimmed but there. The panel is drawn over them.
- **FAIL** — the covers are gone and the panel sits on a flat
  background. Something cleared between the two renders, and the whole
  dialog and modal technique goes with it.
- **FAIL, differently** — the panel is drawn but the covers are
  full-brightness with a hard-edged panel and no dimming. The scrim's
  alpha is not compositing.

> **This is the step with a live open question.** The host tests fence
> "nothing on the composite path invalidates residency", but the stub
> deliberately leaves gsKit's eviction heuristic unmodelled. If the
> covers **flicker** or the panel's text drops in and out during this
> phase, the two screens are evicting each other under real VRAM
> pressure — which is precisely what the host could not answer. Note it
> as an observation even if the still photograph passes; watch it for a
> full five-second phase before moving on.

---

## Step S6 — the art path end to end

**Only meaningful if `src:` named the drive.**

Re-bake with your own art, re-copy `ps2ui/`, and boot `covers.elf`
again. Photograph phase `1 FILL`.

- **PASS** — your art, right way up, right colours, filling each box.
- **FAIL: washed out or glowing** — the alpha domain. The GS treats
  `0x80` as fully opaque; art written with `0xFF` asks for about twice
  the coverage it has. `make_cover_raw.py` converts this, so seeing it
  means something bypassed the tool.
- **FAIL: colour channels swapped** — red and blue exchanged means the
  source was BGRA where PSMCT32 wants RGBA.
- **FAIL: squashed or stretched** — the cover-fit did not run; check
  the file is exactly 65,536 bytes.

---

---

## Step S7 — the baseline row (added after the first sitting)

The first sitting found capitals losing their bottom row on the
television: **E renders as F, L as I, 2 as ?**. `MEMORY CARD` reads
`MFMORY CARD`. Lowercase is unaffected, which is why nine bring-up
steps and every host suite missed it, and it is visible in the Phase 0
conformance grid, so it predates all of Phase 1.

Two renderers disagree with the console. The host previewer draws full
glyphs, and so does the Play! emulator **from the same GIF command
stream** — so the atlas, the glyph table, the UVs and the geometry are
all correct. That leaves the display path or real GS behaviour the
emulator does not model.

### S7a — read the dashes, it costs nothing

**On the `covers.elf` screen you are already photographing**, there is
a line reading:

```
S7 - - - - - - - - - -  E L 2
```

Those hyphens are **one pixel tall and sit three rows above the
baseline**. E, L and 2 end *on* the baseline. That single line
separates the two candidates outright:

| what you see | what it means |
|---|---|
| **dashes present**, E broken | only the baseline row is being lost — the display path |
| **dashes gone**, E broken | the last row of *every* glyph is being lost — geometry, and the renderer is at fault |
| dashes present, E fine | nothing is wrong on this screen; photograph a screen where it is |

Read this before booting anything else. It is on a screen you are
already looking at.

> A note on why this replaced a weaker argument. The first write-up
> leant on "lowercase is untouched" as evidence for a baseline-specific
> fault. It is not: in this face every non-descender — capital,
> lowercase and digit — ends on the *same* row, so a uniform last-row
> loss produces exactly the same picture. An `E` loses a full-width
> bar and reads as `F`; an `e` loses the bottom two texels of a curve
> and still reads as `e`. The dashes are the observation that actually
> discriminates.

### S8 — the height ladder

**Run this before S7b.** S7a's first reading killed both hypotheses
S7b was built to separate, so 480p is now the less informative arm.

What S7a actually established, measured against the blob rather than
guessed: the hyphens sit at screen row **233**, one pixel tall; `E`,
`L` and `2` occupy rows **227–237**, and row 237 — which carries their
three bottom bars and is the widest row on the line, 24 inked texels
against 7 for the stem rows — is the only row lost.

Both strokes measure **one texel** out of the atlas: the size-15 face
this line is authored in inks `E` as `[8,2,2,2,2,8,2,2,2,2,8]` and the
hyphen as `[5]`. So thickness is not a variable here at all — two
horizontal strokes of identical thickness differ only in the height of
the quad carrying them, and the one in a 1-row quad renders while the
one at the bottom of an 11-row quad does not.

That is neither "the last row of every quad" (the hyphen's only row
*is* its last) nor a panel eating thin horizontal detail (the hyphen
is a thin isolated horizontal stroke and a display eating those would
eat it first). Whatever is doing this treats a tall quad differently
from a short one.

**Boot `ladder.elf`.** No blob, no ps2ui — it draws directly, so the
question is about the GS and nothing else is in the way.

Twelve rungs down the screen, heights 1 to 12, each labelled by the
row of small ticks on the left — count them. Three blocks across:

| | arm | what it is |
|---|---|---|
| left | **A** | a textured quad with the UVs ps2ui ships today |
| middle | **B** | the same rung built from stacked 1-pixel *untextured* quads |
| right | **C** | arm A with a `+0.5` texel bias on the UVs |

Every block is a dark body with **one bright line along its bottom**.
Every rung's last texel row is the *same* atlas row, so the question
is identical in every column and needs no reinterpretation per height.

**The whole reading is: which blocks have their bright bottom line?**

| what you see | what it means |
|---|---|
| **A has the line at every height** | the fault is not where this card looks; photograph it anyway and tell me |
| **A loses it above some height, B keeps it** | texture sampling. The height it starts at is the signature — say which rung |
| **A and B both lose it above some height** | rasterisation or the display. The renderer is off the hook |
| **C keeps it where A loses it** | the `+0.5` bias is the fix, demonstrated rather than argued |

Photograph the whole screen once, straight on. If the answer is
height-dependent, note the lowest rung where the line goes — that
number is the finding.

#### S8 has been read: SCPH-50000, sitting 3

| height | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** raw integer UVs | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **B** untextured stack | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **C** UVs + 0.5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**What A and B establish.** Raw integer UVs lose the last texel row at
every height that is not a power of two — and the powers of two are
exactly the heights whose reciprocal is exact in binary, which points
at a reciprocal in the GS's per-scanline UV step. B keeps every row
with no texture unit in its path, so neither the rasteriser nor the
display is losing it. **The fault is real and it is in texture
sampling.** An exact interpolator does not have it: the previewer and
Play! both render every row.

**It retrodicts S7a without being fitted to it, and the retrodiction is
differential** — a single already-photographed line separates the two
predictions. Measured from `fixtures/bench-stream/build/bench.uib`,
whose only *drawn* font face is size 15 (texture 5; the size-14 face is
baked but renders nothing):

| glyph | height | power of two? | predicted | observed |
|---|---|---|---|---|
| `E` `L` `2` | 11 | no | loses its row | `SYNTHETIC` → `SYNTHFTIC` |
| `e` `o` `a` | 8 | **yes** | keeps its row | `loaded`, `never appeared` clean |
| `-` | 1 | **yes** | keeps its row | dashes present |

All three appear in one line of the sitting-3 photograph: capitals
broken and lowercase clean, *in the same word*. Lowercase surviving is a
model **prediction** here, not the observational limit it was assumed to
be — and the examples make the contrast, because they use different
faces:

| blob | face drawn | `E` | `e` |
|---|---|---|---|
| `bench.uib` | 15 | 11 — loses | **8 — keeps** |
| `memcard/ui.uib` | 13 | 9 — loses | 7 — loses |
| `channel6/ui.uib` | 14, 16, 20 | 10, 12, 15 — all lose | 8 keeps, 9 and 11 lose |

So `MEMORY CARD` (size 13, lowercase `h=7`) should degrade in lowercase
too, and there "lowercase looks untouched" **is** an observational limit
— a 7-row `e` loses two texels of curve tip where an `E` loses a
full-width bar. Both mechanisms are real; which applies depends on the
face.

**What C establishes: nothing.** The ladder texture is uniform dark on
every row but the last and ignores `x` entirely, so a bias that shifts
sampling down a whole texel is invisible on rows 0–14 and, on the last
row, reads texel 16 and clamps back to 15 — lighting up anyway. Arm C
shows a bright bottom line whether the bias corrects sampling or merely
shifts it. **It cannot fail, so its passing means nothing.**

That surfaced when the `+0.5` bias was built on this reading and the
emulator gate rejected it: `Library` rendered as `Liibrarny`, frame
diff 17.34 against a healthy 4.8. On an exact interpolator the bias
makes every glyph sample one texel across and lose its leftmost column
— which `bringup.md` has argued correctly all along, for renderers that
interpolate exactly. The GS is not one of them, and the correction it
needs is **still open**.

**Two axes, one asked.** Every arm is 128 pixels wide, a power of two,
so the U axis was never swept at a width the fault would bite.

#### Ladder v2 — what the next card had to do, and does (step S10 below)

1. **Per-row and per-column detail in the texture**, so a one-texel
   shift is distinguishable from a lost row rather than hidden by
   uniformity and clamping. This is the defect that made S8's third arm
   worthless.
2. **Sweep bias magnitude**, not just presence: `0`, `1/16`, `1/8`,
   `1/2`. The GS's UV register carries four fractional bits, and any
   bias below half a texel leaves an exact sampler on the same texel —
   so a small enough correction could fix the console without moving
   the emulator at all.
3. **Sweep width as well as height.**

### S10 — ladder v2: how big a bias, and does it shift?

**Boot `ladder2.elf`.** No blob, no ps2ui. Four columns, twelve rows.

Every block is the same draw with the same geometry; **only the UV bias
differs between columns**, left to right:

| column | bias | what it is |
|---|---|---|
| 1 | `0` | what ps2ui ships — **negative control** |
| 2 | `1/16` | the smallest bias the GS's UV register can express |
| 3 | `1/8` | the next one up |
| 4 | `1/2` | **positive control**, known to shift on an exact renderer |

#### Reading one block — three states, and each has a positive signature

The texture's last row is **yellow**, the row above it is **red**, the
body is dark navy, and the body's rightmost column is **cyan**.

| what you see at the bottom of a block | verdict |
|---|---|
| yellow row with **red directly above it** | sampling is **CORRECT** |
| yellow row with **no red** (or two yellows) | sampling is **SHIFTED** |
| **red** row and no yellow | last row is **LOST** |

That third state is what S8 called "the line is missing", and it now
has a colour rather than an absence. The second state is the one S8
could not see at all — its bias arm showed a yellow bottom row whether
the bias fixed the sampling or ruined it, which is why a fix built on
it was rejected by the emulator gate.

**The cyan right edge is the U axis**, which S8 never asked about: its
arms were all 128 wide, a power of two, the one span that cannot
trigger the fault. Here the blocks are 100 wide. Cyan present at the
right edge of the body means horizontal sampling is correct; cyan gone
means it is shifted. Only visible on blocks 3 rows and taller.

#### Before reading anything else, check the two controls

- **Column 1 must show LOST** at heights 3, 5, 6, 7, 9, 10, 11 and 12.
  If it does not, the card is not reproducing the fault and nothing
  else on it can be trusted. Say so and stop.
- **Column 4 must show SHIFTED.** If it does not, this card cannot see
  a shift, which is exactly the defect that made S8's third arm
  worthless. Say so and stop.

Only if both controls read as expected do columns 2 and 3 mean
anything.

#### What each outcome would settle

| reading | what it means |
|---|---|
| column 2 CORRECT at every height | `1/16` fixes the console and is **invisible to the emulator** — any bias below half a texel leaves an exact sampler on the same texel. Best possible answer. |
| column 2 SHIFTED or LOST, column 3 CORRECT | `1/8` is the answer, same argument |
| both LOST, column 4 SHIFTED | the needed bias is between `1/8` and `1/2`, and a bias that fixes the console may not exist below the one that breaks the emulator. That is a real conflict and it needs a different approach, not a bigger number. |
| column 1 CORRECT | the fault did not reproduce — void, see above |

Photograph the whole screen. If the small blocks at the top are hard to
resolve, take a second photo of the top third — the rows are the
question and the top ones are the smallest.

#### S10 has been read: SCPH-50000, sitting 4

| bias | last texel **row** | last texel **column** |
|---|---|---|
| `0` | lost unless the height is a power of two | **always** lost (100 is not one) |
| `1/16` | present at every height | present |
| `1/8` | present at every height | present |
| `1/2` | present at every height | present |

**Both axes fail, independently, each on its own span.** The clinching
observation is column 1 at heights **4 and 8**: those rungs keep their
bottom row, because 4 and 8 are powers of two, and *still* lose their
right column, because 100 is not. Nothing before S10 could see the U
axis at all — every earlier instrument was a power of two wide, which
is the one span that cannot trigger the fault. Glyphs are not: `-` is 5
texels wide and `S` is 9, and both have been losing their last column
since the beginning.

**The GS is not an exact interpolator.** At `1/2` the console does not
shift — the red row is still red rather than becoming a second yellow.
The card's own positive control was built expecting a shift, which was
circular: it assumed the thing under test. The red band is what saved
the reading, and the control is recorded as a design flaw rather than
quietly dropped.

**The fix is `1/16`, not `1/2`.** Both work on the console. Half a
texel is the exact tipping point — the smallest bias that moves a
round-to-nearest sampler off its texel — so on any renderer that
interpolates exactly it shifts every sample by one, and a `1/2` build
scores 17.34 on a frame diff whose healthy band is 4.8. Every bias
below `1/2` is a no-op there. `1/16` fixes the console and leaves the
previewer and the emulator exactly where they were, and it is the
smallest the GS's four fractional UV bits can express.

**What is inferred rather than measured:** V is swept across twelve
heights, U is measured at exactly one width. S9 is the U sweep.

### S9 — the acceptance test: re-run S7a

**Boot `covers.elf` and read the S7 line.** This is the only step that
closes the defect, because everything above tests the *card* rather
than the shipping renderer — and it is also the real U-axis sweep,
across dozens of genuine glyph widths.

```
S7 - - - - - - - - - -  E L 2
```

- **PASS** — `E L 2` read as themselves, bottom bars intact, and the
  title reads `PS2UI PHASE 1 STREAM BENCH` rather than
  `PS2UI PHASF 1 STRFAM BFNCH`. The defect is closed.
- **FAIL** — still `F I ?`. The bias reached the ladder but not the
  runtime, which would mean a call site bypassing `draw_texquad`; the
  host suite fences that, so a FAIL here is a finding about the fence.

Every capital on the screen is a sample. `EMPTY` in the `state:` line
is the easiest one to check at a glance.

### S7b — 480p, only if S8 is inconclusive

**Boot `ps2ui_sample_480p.elf`.** It is the memcard UI, identical in
every respect except that it outputs 480p instead of 480i. Worth
running only if S8 pointed at the display rather than at sampling. Photograph
the `MEMORY CARD` line under the `PS2` title and hold it next to your
480i photo of the same screen.

- **PASS (renderer acquitted)** — `MEMORY CARD` reads correctly at
  480p. The clipping is the interlaced signal and this panel's
  deinterlacer. Worth knowing that step 8's recorded reading cuts
  *against* this: the panel weaves static fields, so it preserved the
  static 1px rules it was shown. Not impossible — the same log has 1px
  checkers shimmering, so the panel is motion-adaptive — but this
  outcome would be the surprising one.
- **FAIL (renderer convicted)** — still `MFMORY CARD` at 480p. The
  fault is in what ps2ui asks the GS for, and the next arm is a
  `+0.5` texel-centre bias, which `bringup.md` already carries as an
  unsettled question.
- **VOID** — no picture at all. Your television does not sync at 480p.
  Power off, boot anything else, and tell me: we need a different
  discriminator.

## When you are done

Send, per step: **one photograph, the step number, and one of PASS /
FAIL / VOID.** Nothing needs measuring and nothing needs describing in
prose — the `state:` line in each photo says which step it is.

If anything went VOID, say which and why; a void reading is a fact
about the bench, not about the renderer, and it usually means the
instrument needs fixing before the question can be asked again.

**The three answers this sitting is worth having**, in order of how
much rests on them:

1. **S2** — does `ps2ui_tex_set` work on real silicon? Everything in
   Phase 1's texture-slot work depends on it and nothing has tested it
   outside a stub.
2. **S5's flicker observation** — do two composited screens stay
   resident under real VRAM pressure? The host is structurally unable
   to answer this.
3. **S1** — is an unfilled slot inert? The failure mode is a window
   onto whatever else is in VRAM, and it would show up on the very
   first frame of a real list before any cover has loaded.
