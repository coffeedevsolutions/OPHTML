# Bench runbook — Phase 0, steps 3 to 9

One sitting. Read this page and nothing else; it assumes no context
beyond a PS2, a USB stick and a television.

Steps 1, 2 and 10 already passed on a SCPH-50000. This covers the rest.
`docs/bringup.md` is the reference with the reasoning; this is the
order of operations.

---

## Before you start

**Get the ELFs.** From the latest green `hw` run on `main`, download the
`ps2ui-sample-elf` artifact. It contains seven files:

| file | what it is for |
|---|---|
| `minimal.elf` | step 1 — already passed, keep it as a sanity check |
| `probe.elf` | step 2 — already passed, keep it for the same reason |
| `conform.elf` | steps 3, 4, 5, 7 — the conformance grid |
| `testcard.elf` | steps 6 and 8 — the alignment card |
| `probe6.elf` | step 6b — which part of the texture path is at fault |
| `ps2ui_sample.elf` | step 9, and the only one that looks like a real UI |
| `telemetry.elf` | frame timing, not a bring-up step |

**Copy them under fresh names.** Every stale-file incident on this
project came from an old copy sitting on the drive under the name you
were about to run. Copy as `s3.elf`, `s6.elf` and so on if you prefer;
what matters is that the name you boot is a name that did not exist on
that drive before today.

**Check the sizes after copying, not before.** `ls -l` on the drive
itself. A copy that reports success and has not flushed is the single
most common way to spend an hour reading a photograph of the wrong
build.

**One photo per step, straight on.** Every instrument here is built so
a phone at arm's length can read it. Nothing needs a measurement.

**A screen filled edge to edge with one flat colour is never a UI.**
It is the ELF telling you something before it ever draws. **Read these
off the screen, not off a photo** — a phone renders saturated magenta
on a panel as violet and lifts near-black to a visible maroon, which is
exactly the failure the rest of this page is built to avoid:

| fill | means |
|---|---|
| steel blue | `minimal.elf` passed — this one is a **pass** |
| dark red | the blob failed to load |
| olive/dark yellow | the upload ran out of VRAM (that is step 9) |
| magenta, or violet on a photo | the ELF asked for a screen this blob does not have |
| **black, or no picture** | it did not boot. Nothing below applies |

You are not naming a colour here, only noticing that the whole frame is
one flat thing and which of five it is — a judgement that survives any
camera. Magenta means the build is wrong, not the renderer. Report it
and stop; nothing measured after it means anything.

---

## The three words that matter

Each step below ends in one of three states. **Void is not a failure
and it is not a pass** — it means the cell could not tell you anything,
and reading it as either is worse than not running it.

| | |
|---|---|
| **PASS** | the property holds |
| **FAIL** | the property does not hold — record it, keep going |
| **VOID** | the instrument could not answer; the calibration says so |

**Every step below has a void state**, and each one names the
calibration that detects it. If you hit one, note it and move on: a
void reading is a fact about the bench, not about the renderer.

---

## Step 3 — CLUT and the CSM1 swizzle

**Run** `conform.elf`. It opens on the conformance grid; nothing to
navigate. Look at the bar across the top of the **IMAGE** cell.

**Expect:** a flat dark-teal bar with **one bright-orange stripe hard
against its right edge**.

| what you see | verdict |
|---|---|
| one stripe, at the right edge only | **PASS** |
| an extra stripe at 1/6 across | **FAIL** — bit 3 of the palette index |
| an extra stripe at 3/6 across | **FAIL** — bit 4 |
| stripes at 1/6, 3/6 and the right | **FAIL** — the permutation is not being applied at all |
| **no stripe anywhere** | **VOID** — the rightmost stripe is the calibration and no permutation can remove it. If it is gone, this cell cannot show you a stripe and the rest of the row means nothing |

---

## Step 4 and 5 — tinting and the modulate domain

**Run** `conform.elf`, same screen. Look at the **MODULATE** cell:
three rows of `MMMM`.

**Expect:** the top two rows **blank** — the text is painted the exact
colour of the block behind it — and the third row plainly legible.

| what you see | verdict |
|---|---|
| rows 1 and 2 blank, row 3 legible | **PASS** for both steps |
| letters visible in row 1 or 2, **brighter** than their block | **FAIL step 4** — the tint is not being applied; glyphs are rendering at raw atlas white |
| letters visible but merely the **wrong shade** | **FAIL step 5** — the tint is applied in the wrong domain |
| **row 3 not legible either** | **VOID** — this cell draws no readable text at all, so the blank rows above prove nothing |

---

## Step 7 — scissor nesting

**Run** `conform.elf`, same screen. Look at the **CLIP** cell.

**Expect:** exactly **one magenta square**, inside the dark strip.

| what you see | verdict |
|---|---|
| one magenta square | **PASS** — the scissor is suppressing its twin |
| **two** magenta squares | **FAIL** — the scissor rect is not reaching the GS |
| **no** magenta at all | **VOID** — the visible one is the calibration. If it is missing, the quad never drew and this says nothing about clipping |

The previewer renders exactly one. That is the picture to match.

---

## Step 6 — texel centres

**Run** `testcard.elf`.

**Expect:** across the middle, five patches: **flat grey, then 1px, 2px
and 4px checkers, then flat grey again.** All three checkers crisp and
obviously unlike the grey at either end.

| 1px | 2px | 4px | verdict |
|---|---|---|---|
| crisp | crisp | crisp | **PASS** |
| grey | crisp | crisp | **FAIL** — a real half-texel sampling offset |
| grey | grey | crisp | **VOID** — this is the panel's resolution limit, not a fault. Move closer or use a different display |
| grey | grey | grey | **VOID** — read nothing from this card |

### Step 6b — which part of the texture path (run this one too)

**Run** `probe6.elf`. Five columns, no text anywhere. Each column is a
patterned patch with a reference patch directly beneath it. Ignore the
pattern; look only at the horizontal boundary inside each column.

**Expect:** every boundary invisible. A visible one names a fault.

| what you see | verdict |
|---|---|
| all five seamless | **PASS** — none of these reproduces it |
| leftmost seamless, another visible | **FAIL** — note which column, counting from the left |
| **leftmost visible** | **VOID** — the leftmost is the calibration; if it seams the probe is wrong, not the console |

Count columns from the left and write the number down; that number is
the whole result. This is a step where a photo genuinely helps, because
a seam survives a camera. Shoot it straight on.

Also on this card, worth a glance: four **1px colour-coded rules**
hugging the canvas edges — red top, green bottom, blue left, yellow
right. All four should be visible. A missing one names its side and
means a half-pixel *primitive* offset or overscan, which is a different
fault from the checkers above.

The four corner checkers are single 1px checkers with no coarser rung
beside them. **Read them only if the wedge showed 1px crisp** — on
their own they carry the same ambiguity the wedge exists to remove.

---

## Step 8 — interlace

**Run** `testcard.elf`. Below the wedge: a **thin rule above a thick
rule**, same width, same position.

**Watch it. Do not photograph it.** This is a 30 Hz alternation and no
still frame can capture it. It is the one step on this page that is an
operator report by design.

| thin | thick | verdict |
|---|---|---|
| flickers | steady | **PASS** — interlaced as expected |
| steady | steady | **VOID** — see below |
| flickers | flickers | **FAIL** — field order, or a half-height framebuffer |

**If nothing flickers, check your own code before your television.**
gsKit defaults `gsGlobal->Field` to `GS_FIELD`, which is what makes a
1px rule live in a single field. Set to `GS_FRAME` and every field
reads every line: both rules sit still on a perfectly interlaced
output. ps2ui's sample never overrides it, but a host program that owns
`gsKit_init_screen` can.

This is also the only thing in the tree that tests the premise behind
the CRT linter's hairline warning, so a void here means that advice is
unverified — not merely that one step was inconclusive.

---

## Step 9 — VRAM pressure

**Run** `ps2ui_sample.elf`. No wire, no console log: an upload that
fails holds the screen **solid yellow** and never draws anything else.

**Expect:** the memcard UI.

| what you see | verdict |
|---|---|
| the UI | **PASS** — the real blob's textures fit real VRAM |
| **solid yellow**, held | **FAIL** — the upload ran out. Re-bake with `--vram-budget` set to what is actually free on your console |
| black, or nothing | **VOID** — this is a boot failure, not a VRAM result. `minimal.elf` from the top of this page separates the two |

Yellow is known reachable rather than a colour nobody has ever seen:
the host suite starves the allocator and asserts the failure is
reported, in both shapes — nothing fitting at all, and running out
partway through the uploads.

`telemetry.elf` is the same UI with a once-a-second stats line on
`stdout`. Worth running if you have PCSX2's console log or a ps2link
TTY, for the frame timing. It is not what answers this step.

---

## When you are done

Write down, per step, one of **PASS / FAIL / VOID** and the photo.
That is the whole deliverable. A run that produces four passes, two
fails and a void is a good run; a run that produces seven passes and
one of them was really a void is worse than not running at all.

Anything that failed goes back to `docs/bringup.md`, which carries the
reasoning and the fix for each.
