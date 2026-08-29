# Bench runbook — Phase 2, the OPL-class environment

Phase 2 asks one question: does a real OPL-class front end — 412
titles, nine covers streamed per scroll step, six screens, 127 slots —
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
| 4. `up` | 0 for the first eight scroll steps, then 28224 | see below |
| 5. `ee` | around 2.2 ms | approaching `f` means the timer is measuring the wait again |
| 6. `p` | rises with title digits | see below |

### `up0` is normal for the first four seconds

`up` reads 0 while the selection walks *inside* the window without
moving it, which is the first eight scroll steps after boot and after
every wrap. `oplenv_window_move` returns 0 on those and nothing is
re-uploaded — that is F-032's second half, not a fault.

Simulated against the shipping loop, `OPLENV_SCROLL_EVERY 30`:

| tick | sel | top | window | `up` |
|---|---|---|---|---|
| 1–8 | 1–8 | 0 | titles 1–9 | **0** |
| 9 | 9 | 1 | titles 2–10 | 28224 — first upload, frame 270, **t = 4.5 s** |
| 412 | wrap | 0 | titles 1–9 | back to **0** for eight more steps |

Telemetry first appears at frame 60, so the earliest readout anyone can
photograph already reads `up0`. The wrap comes round every 411 steps,
about 206 s.

**A reading taken at `up0` is not comparable to the others** — it
differs in upload state as well as in content, which is why F-036
excludes the 2.12 figure from any marginal cost. If you want a
comparable pair, take both after the fourth second.

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

**HW #262 (S12)** — `oplenv.elf` *and* `oplenv-fill.elf` at `5ea02ae`.
The pair, which is the whole point:

| build | `ee` | peak | `gs` |
|---|---|---|---|
| plain | 2.31 → 2.41 | 3.53 → 3.66 | **0.91 → 0.93** |
| fill | 2.28 → 2.41 | 2.29 → 3.66 | **3.20 → 3.22** |

`gs` moved 2.29 ms for 2,293,760 blended pixels — **1.002 Gpix/s**.
The GS is 16 pixel pipelines at 147.456 MHz, so 2.359 Gpix/s unblended
and **1.180 blended**, a blend forcing a framebuffer read-modify-write.
The arm landed at **84.9% of the part's blended peak** — 85% of
theoretical on real silicon with page breaks is where it belongs.

`ee` moved **+0.00** at matched prim counts (2.41 vs 2.41 at p599, 2.37
vs 2.37 at p590), so the arm moved the GS number and nothing else. Not
latched: a latched instrument reads 0.00 forever, and a broken one does
not land within 15% of a spec sheet.

So: **EE 14.4%, GS 5.6%, together 20.0% of a field**, 13.34 ms unused.
F-037, F-038.

4.59 ms (27.5%) is the worst frame *photographed*, but it pairs an EE
peak with a GS **mean**, so it is a lower bound. The two spikes are not
independent: the scroll frame does the bind work on the EE *and* pushes
28,224 bytes through the same chain, making it the worst frame on both
axes at once. A real worst-frame figure needs `gs^` beside `ee^`.

Two things worth noticing in that table. The fill build's `up0` window
reads `ee2.28^2.29` — the peak collapsing onto the mean, because a
window with no scroll frame has no spike to hold. Nobody arranged that;
it is the peak-hold checking its own semantics.

And the fill build reports **`m1`** where the plain build held `m0`.
One field, early, never climbing across a run spanning titles 1 to 130.

**The cause is unknown, and the obvious explanation is wrong.** The
frame period is vsync-locked, so top-to-top quantises to whole fields
and the 18.33 ms trip can only be cleared by two of them — meaning one
frame's work exceeded a **whole 16.683 ms field**, not that it ran a
little long.

Priced against that, "frame 0's cold start" fails. For the fill build's
extra 2.29 ms to be what tipped it, plain frame 0 must have landed in
[14.39, 16.68) ms — 11.05 ms above plain steady state. The blob's
entire texture payload is 233,660 bytes:

| path | cold upload of all of it |
|---|---|
| GIF DMA, 1.2 GB/s | 0.19 ms |
| 300 MB/s | 0.78 ms |
| EE inline, 150 MB/s | 1.56 ms |

Short by a factor of seven at best. And `FirstFrame` argues the wrong
way: `gsKit_queue_exec_real` *skips* its wait on frame 0, making that
frame shorter.

So: one field was lost, nothing identified accounts for 11 ms of it,
and `m` records *how many* but never *when*. A frame index on the first
miss answers "when"; "why" stays open.

---

## P3a — reading the GS's share

Two ELFs from the same run: `oplenv.elf` and `oplenv-fill.elf`. They
are the same driver; the second adds eight full-screen alpha-blended
sprites per frame.

The readout gains a second line:

```
ee2.21^3.94 gs9.12
f16.68 ms p579 up28224 m0
```

| field | is |
|---|---|
| `ee` | mean EE work per frame |
| `^` | **peak** EE frame in the last second — the scroll frame, which the mean smears |
| `gs` | **GIF transfer + GS drawing**, measured after `gsKit_finish()` returns |

`gs` is not drawing alone. `dmaKit_send_chain_ucab` programs the DMA
registers and returns, so the chain is still moving when the clock
starts. For *"does the frame fit in a field"* that is the right
quantity. For deciding what Phase 3 optimises it is not — a large
number could be transfer-bound rather than fill-bound, and those want
opposite work. The fill arm separates them too: its sprites are one
prim each and carry almost no transfer, so a `gs` that climbs under
fill is climbing on rasterisation.

**Photograph both ELFs.** One number is not the reading; the pair is.
The fill build stays legible — the sprites are drawn *before* the UI,
so the telemetry composites on top of them.

| | plain | fill | verdict |
|---|---|---|---|
| `gs` | *g* | noticeably **higher** | the instrument works, and *g* is the GS's real share |
| `gs` | *g* | **the same** | **STOP.** The reading is worthless — see below |
| `gs` | 0.00 | 0.00 | **STOP.** Latched, certainly |

### Why the fill ELF is not optional

`gsKit_finish()` spins on CSR FINISH and does not clear it; gsKit
clears it on the next frame's kick. If that bit is ever left latched,
every wait returns instantly and `gs` reads **0.00 ms on every frame,
forever** — which is indistinguishable from an idle GS.

An idle GS is the answer the plan already expects. So a broken
instrument here does not produce an obviously wrong number; it produces
**the number we were expecting**, and Phase 3 gets planned on it. That
is why the arm exists and why a `gs` reading without its matching fill
photograph does not go in the ledger.

If both ELFs report the same `gs`, the instrument is latched **or** the
fill arm is drawing nothing. Those want opposite fixes and the
photograph cannot tell them apart, which is why
`tools/check-timing-probe.py` refuses a fill arm that does not loop and
draw.

### Optional, and worth it

`PS2UI_OPLENV_FILL_N` is overridable at build time. A sweep — 2, 4, 8,
16 sprites — that moves `gs` roughly proportionally is far stronger
evidence than a single step: it says the number tracks fill, not that
it merely changed once.

Build it with **both** flags: `make -C runtime/sample OPLENV=1 FILL=1
PS2UI_OPLENV_FILL_N=16 …`. `FILL=1` alone is refused by the Makefile,
because without `OPLENV=1` it quietly produces the plain memcard sample
under the fill ELF's name — a file that boots, shows a UI, and is not
the arm you think you are holding.

---

## What Phase 2 did not measure

**The GS's share of the field.** Not GS time outright: `gsKit_queue_exec`
blocks on the previous frame's FINISH before sending the chain, so a GS
over budget would show up inside `ee` and trip `m`. Between `ee` at
13.5% and `m0`, GS time is bounded below a field. What is unmeasured is
how that field divides — 10% GS and 90% GS are indistinguishable from
these readings. One `gsKit_finish()` away; it is P3a.

**Anything but this content shape.** 412 titles of nine visible rows,
one scroll step at a time. A grid view, a larger window, or a cover
size other than 28x28 CT32 are all unmeasured, and F-032's per-row
reservation model is the thing most likely to move under them.
