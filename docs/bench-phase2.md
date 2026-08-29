# Bench runbook — Phase 2, the OPL-class environment

Phase 2 asks one question: does a real OPL-class front end — 412
titles, nine covers streamed per scroll step, six screens, 125 slots —
run at field rate on a PlayStation 2, and what does it cost?

Unlike Phase 1 this is not a bring-up. The renderer is known good on
hardware (F-033). What is unknown is the *budget*, and a budget cannot
be read off an emulator, because the thing being measured is a clock.

---

## Before you start

From the latest green `hw` run on `main`, download `ps2ui-sample-elf`
and take `oplenv.elf` from it. Nothing else is needed — the blob is
embedded and there are no cover files to stage. Put it on a USB drive
and launch it from wLaunchELF.

**Check which build you have.** `f` must read **16.68**. A build
reading 16.73 predates the divisor fix and its `ee` field either does
not exist or is measuring the vsync wait. See F-034.

---

## The readout

```
ee2.21 f16.68 ms p579 up28224 m0
```

| field | is | read it for |
|---|---|---|
| `ee` | EE work per frame, stopping at the DMA kick | headroom (F-036) |
| `f`  | wall-clock frame period, top of loop to top of loop | field rate (F-034), clock rate (F-035) |
| `p`  | primitives in the last frame | self-consistency, below |
| `up` | bytes uploaded by the last scroll step | streaming cost (F-032) |
| `m`  | dropped fields, **cumulative since boot** | F-034's falsifier, directly |

`ee` is EE-side only. `gsKit_queue_exec` returns while the GS is still
drawing, so `f - ee` is an upper bound on the headroom available to EE
work and **not** a measure of GS occupancy.

`m` never resets. A drop that happened before you got the camera up is
a drop the photograph still shows. That is the point of it.

---

## What to do

Let it scroll. It advances one row on a timer and wraps at the end of
the list, so the whole run is unattended. Photograph the readout at
the top of the list, somewhere in the tens, and somewhere in the
hundreds. Nothing needs to be timed or triggered.

| step | expect | if not |
|---|---|---|
| 1. it boots to LIBRARY, 412 titles | text crisp, no lost glyph edges | F-033 has regressed; see the texel bias |
| 2. `f` | 16.68, every frame | 16.73 means an old build; anything near 33.4 means dropped fields |
| 3. `m` | 0, and it stays 0 | any non-zero value falsifies F-034 |
| 4. `up` | 0 on the first frame, then 28224 | F-032 predicts 9 x 3,136 exactly |
| 5. `ee` | around 2.2 ms | approaching `f` means the timer is measuring the wait again |
| 6. `p` | rises with title digits | see below |

---

## The prim count checks itself

`p` is worth reading rather than glancing at, because the readout is
drawn by the thing it measures and that makes the count predictable to
the primitive.

Nine rows of `Title of a Game N`. Going from single-digit titles to
double-digit ones adds nine glyph quads, one per row. Going from
double to triple adds nine more. And the readout's *own* text is on
screen, so when `up0` becomes `up28224` that is four more glyphs too.

Measured at HW #261:

| window | `p` | change | accounted for by |
|---|---|---|---|
| 1–9 | 566 | — | — |
| 11–19 | 579 | +13 | +9 title digits, +4 the readout's own `up` field |
| 140–148 | 588 | +9 | +9 title digits; readout length unchanged |

Both exact. If `p` moves by an amount this table cannot explain,
something is drawing that should not be.

---

## Reading history

**HW #260** — `oplenv.elf`, first sitting. `up28224` exact against the
reservation model, no dropped field, 562 to 570 prims. Frame period
read 16.73 ms; the 0.05 ms above a true field turned out to be a
truncated divisor rather than clock error, and the build was replaced.
F-032, F-034, F-035.

**HW #261** — `oplenv.elf` at `4d351ae`. `f` 16.68 on every frame,
`m` 0 held past title 250, `ee` 2.12 → 2.21 → 2.25 ms as the list
deepened. About an eighth of a field on the EE, roughly 14.4 ms
unused. F-036.

---

## What Phase 2 did not measure

**GS occupancy.** Every number here stops at the DMA kick or at vsync,
and neither is the GS finishing its drawing. The EE is at 13.5% and
the GS is at an unknown percentage of the same field. Measuring it
needs a drawing-finished sync, which is a Phase 3 instrument.

**Anything but this content shape.** 412 titles of nine visible rows,
one scroll step at a time. A grid view, a larger window, or a cover
size other than 28x28 CT32 are all unmeasured, and F-032's per-row
reservation model is the thing most likely to move under them.
