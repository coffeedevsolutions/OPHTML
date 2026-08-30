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
ee2.41^3.66 gs0.93^1.08
f16.68 p599 up28224 m1@0
```

| field | is |
|---|---|
| `ee` | mean EE work per frame, ms |
| `gs` | **GIF transfer + GS drawing**, ms, measured after `gsKit_finish()` returns |
| `^` | **peak** of the preceding number over the last second |
| `m1@0` | one field missed; the frame that overran was **0** |

Both numbers carry a peak because **the two spikes coincide**: the
scroll frame does the bind work on the EE *and* pushes 28,224 bytes
through the same chain, so it is the worst frame on both axes at once.
An `ee` peak paired with a `gs` mean is a lower bound, not a reading.

`m` alone says how many and never when, which is how HW #262's single
miss got an explanation that was wrong by a factor of seven with
nothing able to check it. `@` is the index of the frame **whose work
overran**, for the first miss only; a later one cannot overwrite it.

The counter measures the period *ending* at frame F, which is frame
F−1's work, so the driver records `frame - 1`. A cold-start overrun
therefore prints `@0` — which is what this table says, and would not
have been reachable at all if the raw index were used.

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

### A prediction to falsify, written before the reading

F-037 predicts **`gs^` between 0.95 and 1.15** against a 0.93 mean.
28,224 bytes is 0.024 ms on the DMA path and 0.188 ms EE-inline, and
the HW #262 `up0`-vs-`up28224` mean difference implies about 0.3 ms per
upload frame. That is 2 to 20 print units above the mean — readable.

**A `gs^` sitting on the mean falsifies the upload-cost story**, and
would say the scroll frame's transfer is not where the time goes.

For `m`, the useful reading is `@`. If the miss is at a low frame
index it is a boot transient and the steady state is clean; if it is
mid-run, something in the scroll path occasionally costs a whole field
and that is a defect, not a curiosity. Either way the count alone could
not have told you.

### Optional, and worth it

**The sweep ships as ELFs now** — `oplenv-fill2`, `-fill4`,
`-fill` (8), `-fill16` — so it costs four boots rather than a
toolchain.

One step proves the number is not latched. **Proportionality proves it
is measuring fill**, which is a stronger claim: a latched or
mis-anchored clock can produce a non-zero constant, but it cannot
produce a straight line through four points.

Predicted from HW #262's 0.93 ms baseline and its measured 1.002
Gpix/s, written down before the sitting:

| build | sprites | blended px | predicted `gs` |
|---|---|---|---|
| `oplenv` | 0 | 0 | 0.93 |
| `oplenv-fill2` | 2 | 573,440 | **1.50** |
| `oplenv-fill4` | 4 | 1,146,880 | **2.07** |
| `oplenv-fill` | 8 | 2,293,760 | **3.22** |
| `oplenv-fill16` | 16 | 4,587,520 | **5.51** |

Photograph each. **A reading that lands on the line is the instrument
confirmed against the hardware four times over.** A curve that flattens
at the top would say something else is saturating — bus, not fill —
and is worth having either way.

`FILL=1` alone is refused by the Makefile: without `OPLENV=1` it
quietly produces the plain memcard sample under the fill ELF's name — a
file that boots, shows a UI, and is not the arm you think you are
holding.

---

## Reading history, continued

**HW #263 (S13)** — five ELFs at `085b409`. The sweep, against
predictions written down before the sitting:

| build | N | predicted | measured | error |
|---|---|---|---|---|
| `oplenv` | 0 | 0.93 | **0.92** | −0.01 |
| `-fill2` | 2 | 1.50 | **1.49** | −0.01 |
| `-fill4` | 4 | 2.07 | **2.07** | 0.00 |
| `-fill` | 8 | 3.22 | **3.21** | −0.01 |
| `-fill16` | 16 | 5.51 | **5.50** | −0.01 |

**One print unit, every point.** Least squares through all five:
**1.002 Gpix/s**, r² = **0.999998**, intercept **0.9205 ms**. F-039.

The intercept is the finding: the UI's own GS cost extrapolated to zero
fill, from five points rather than one, agreeing with the directly
measured 0.92 to within half a print unit.

**`gs^` landed at 1.15** against a 0.92 mean — the exact top of the
predicted [0.95, 1.15] band. The scroll frame costs ~0.23 ms more GS
time than the mean.

The gap holds at 0.21–0.23 on four of five builds; **`-fill2` read
0.08** and does not fit. The `up0`-window explanation is ruled out by
the photograph, which reads `up28224` — and with `SCROLL_EVERY` at 30
against a 60-frame peak window, an actively scrolling run has two
scroll frames in every window. Unexplained, for a documented reason.

**`m@` located the dropped field but not its cause.** `m0` at N=0 and
N=2, `m1` at N=4, 8 and 16, every miss at `@0` — frame 0 is the frame
that overran.

The bracket that followed, "frame 0 costs 15.5–16.1 ms", was **wrong**,
and F-040 is provisional because of it. Frame 0's period was the only
one in the run not bounded by two vsyncs: nothing between
`gsKit_init_screen` and `t_prev` waited for one, so the clock started
at an arbitrary phase φ into a field and the sweep bracketed **C + φ**,
not C. An ordinary 3.5 ms frame 0 with φ ≈ 12.3 fits the same five
photographs exactly as well, and it is the reading the code supports —
the VRAM allocation and CLUT work all happen in `ps2ui_upload`, before
the clock starts.

**Fixed in the driver**: `gsKit_vsync_wait()` before `t_prev`, so
frame 0's period is a true multiple of the field. Re-run the same five
ELFs — if the misses vanish, the bracket was measuring boot phase.

### S14 ran them, and the misses vanished [F-040:historical]

| build | N | `gs` | `m` at S13 | `m` at S14 |
|---|---:|---:|---|---|
| `oplenv` | 0 | 0.92 | `m0` | `m0@0` |
| `oplenv-fill2` | 2 | 1.49 | `m0` | `m0@0` |
| `oplenv-fill4` | 4 | 2.07 | **`m1@0`** | `m0@0` |
| `oplenv-fill` | 8 | 3.21 | **`m1@0`** | `m0@0` |
| `oplenv-fill16` | 16 | 5.51 | **`m1@0`** | `m0@0` |

`f16.68` on all five, no stretch. **Frame 0 never spilled a field.**
The bracket measured C + φ, and with φ at zero frame 0 fits inside a
field at every fill level up to sixteen full-screen layers. Of the two
readings that fit the same five photographs, the second was right —
C ≈ 3.5 ms with φ ≈ 12.3 — and it is the one the code supported all
along. The 15.8 ms frame never existed, so **nothing above this line
about frame 0's cost should be read as current.**

Three passes at a mechanism that was not there, each reading as settled
when written. What ended it was not a better explanation but an
instrument change: `m` gained a frame index, and `@0` on every miss is
what made "the clock's own first frame" reachable as a hypothesis. A
finding that cannot say *when* cannot be argued out of a wrong *why*.

**And the readout audited itself a fourth time.** Line 1 gained `^1.15`
(+5 glyphs); line 2 gained `@0` and lost ` ms`, cancelling exactly. `p`
went 590 → **595**. All five photos read p595 on five different
nine-double-digit windows.

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

---

## What the sweep lets you answer without a console

F-039 did not just prove the GS instrument works. It produced a
**calibrated model**, and a calibrated model answers questions that
would otherwise cost a sitting:

```
gs(layers) = 0.9205 ms  +  layers x 0.2861 ms
             ^ the UI's own cost      ^ one full-screen 640x448 blended quad
                                        (286,720 px at 1.002 Gpix/s)
```

Against the five measured points, to the print resolution:

| layers | model | measured |
|---|---|---|
| 0 | 0.92 | 0.92 |
| 2 | 1.49 | 1.49 |
| 4 | 2.07 | 2.07 |
| 8 | 3.21 | 3.21 |
| 16 | 5.50 | 5.50 |

**So half a field on the GS costs 25.9 full-screen blended layers, and
a whole field costs 55.1.**

**THE SLOPE IS UNTEXTURED, AND THREE OF THE FOUR SHAPES BELOW ARE NOT.**
The sweep drew `gsKit_prim_sprite` — flat colour, no texture, alpha
blended (`main.c:1799`). Texel fetch contends for the same path, so the
textured fill rate is materially lower and every textured row here is a
**lower bound**, not a prediction. The intercept is unaffected: 0.9205
ms is the UI's own measured cost and already contains all the textured
work the UI does. Only the slope is untextured.

| shape | layers | at the fitted slope | if textured fill were half as fast |
|---|---|---|---|
| a background image | 1 | 1.21 ms · 7.2% | 1.49 ms · 8.9% |
| a transition compositing two full screens | 2 | 1.49 ms · 8.9% | 2.06 ms · 12.4% |
| both at once | 3 | 1.78 ms · 10.7% | 2.64 ms · 15.8% |
| 9 covers 28x28 -> 128x128 | — | +0.14 ms | +0.28 ms |

The conclusion survives the pessimistic column: **even at half the
fitted rate, half a field still takes 13 full-screen layers**, and
nothing above is close. The 25.9-layer claim itself is *in* domain —
full-screen blended sprites are exactly what was measured.

**F-038's note guessed the wrong processor** [F-042]. It expected the
compositing transition to be "the one most likely to move gs, since
fill scales with area". It costs 0.57 ms. Nothing an OPL-class UI can
plausibly draw gets the GS near its limit, and that half of F-038's
falsifier is now discharged by arithmetic rather than waiting on a
bench.

**The EE half is the open one, and it has no model.** `gs` has five
points, a fitted line and r² = 0.999998. `ee` has one number, 2.4 ms,
and nothing to extrapolate with — so the surviving half of F-038
cannot be answered the same way.

### The EE arm, and why the obvious version of it does not work

The instrument wants to multiply EE work while leaving fill alone. The
first draft of this section said **render the UI N extra times inside a
1x1 scissor**. That cannot work, and the reason is four lines into
`ps2ui_render`:

```c
stack[0].x0 = 0;  stack[0].y0 = 0;
stack[0].x1 = ctx->hdr->canvas_w;
stack[0].y1 = ctx->hdr->canvas_h;
apply_scissor(gs, &stack[0]);        /* ps2ui.c:1044 */
```

A caller-set scissor survives exactly until the renderer is entered.
Every extra pass would fill the whole screen, `ee` and `gs` would rise
together, and the arm's self-falsification clause would fire for a
reason it does not anticipate: the scissor was discarded, not the
design wrong.

**Use the alpha test instead, and it needs no runtime change.**
`ps2ui_render` deliberately does *not* assert the alpha TEST register —
`ps2ui.c:999-1010` spells out why, and names `gsKit_set_test` as the
line that would. So a caller can set `ATE` with `ATST = NEVER` before
the extra passes and it is still in force when the renderer runs: the
GS receives, sets up and discards every fragment, the EE does all of
its work. A documented non-assertion becomes the mechanism.

### And `gs` will not stay flat, which makes the check sharper

`gs` is **GIF transfer + GS drawing** (see the readout table above). N
extra renders push N× the command list through the GIF — roughly 41 KB
per pass — plus per-primitive setup for 1,244 prims × N. None of that
is clipped by an alpha test.

So the expectation is not "flat". It is:

> `gs` rises with N by **transfer and setup only** — far below the
> N × 0.2861 ms the fill model predicts for the same passes drawn for
> real.

### What was built, and why it touches no GS state at all

Neither the scissor nor the alpha test survived contact with the tree.
The scissor is discarded by `ps2ui_render` four lines in. The alpha
test looked sound — `ps2ui_render` does leave TEST inherited, and says
so — but `gsKit_set_test` takes a **preset**, `gsCore.c` is *not*
vendored here, and `GS_ATEST_ON` is documented only as *"Turns on Alpha
Testing (Source)"*. Nothing in this tree says it encodes `ATST = NEVER`.
Building the instrument that settles half of F-038 on top of a GS
register whose semantics this repo cannot pin down is the exact hazard
`ps2ui.c:999-1010` declines to take on, and it would make the
instrument's own trustworthiness the thing in question.

**So the arm touches no GS state: `PS2UI_OPLENV_EE` renders the whole
UI N extra times and nothing else.** `gs` rises too, and that costs
nothing — `ee` is read across the kick window and `gs` after
`gsKit_finish` returns, by separate clocks, so GS scaling never enters
the EE number. It becomes a free cross-check instead.

### The predictions, before the sitting

**`gs` has no free parameter and is the strongest of the three.** The
extra passes are identical draws, so:

| N | gs predicted |
|---|---|
| 0 | 0.92 |
| 1 | 1.84 |
| 2 | 2.76 |
| 3 | 3.68 |
| 4 | 4.60 |

If `gs` does not follow that, **the extra passes are not happening**
and nothing else on the sitting means anything. Check it first.

**`ee` is the measurement, and the sweep exists to split one number
into two.** `ee(N) = base + (N+1) × render`, where `base` is the
driver's own per-frame work (scroll logic, `sprintf`, telemetry) which
does *not* repeat. One point cannot separate them; five can. The two
extreme branches both pass through the measured 2.41 at N=0:

| N | if base ≈ 0 (all of it is render) | if base ≈ 1.0 |
|---|---|---|
| 0 | 2.41 | 2.41 |
| 1 | 4.82 | 3.82 |
| 2 | 7.23 | 5.23 |
| 3 | 9.64 | 6.64 |
| 4 | 12.05 | 8.05 |

**And `m` reads the same question a second way.** EE and GS work are
sequential in a frame, so the field needs `ee + gs`. On the upper
branch N=4 is 12.05 + 4.60 = **16.65 ms against a 16.683 ms field** —
at the edge, and predicted to miss on the scroll frames that carry the
peak. On the lower branch it is 12.65 ms and comfortable. So the miss
counter discriminates between the branches independently of the fitted
line, which is the property F-039's sweep had and the reason it was
worth five ELFs rather than two.

The range stops at N=4 for that reason: past it the loop stops being
vsync-locked and the frame period stops being a clean 16.683.

### `p` does not scale, and that is a third cross-check

`ps2ui_render` opens with `memset(&ctx->stats, 0, ...)` (`ps2ui.c:973`),
so the readout's `p` reports **the last pass only** — one (N+1)th of
what the frame actually drew. The prim count has been this project's
free self-audit four times; a photograph from an EE build will not
reconcile against a plain one unless you multiply.

So it joins the other two rather than being a caveat:

| N | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| `p` printed | 590 | 590 | 590 | 590 | 590 |
| prims actually drawn | 590 | 1,180 | 1,770 | 2,360 | 2,950 |

**`p` staying at 590 while `gs` scales is the pair that says the extra
passes are real and the counter is per-render.** If `p` scales, stats
are accumulating across passes and something else in the readout is
suspect too.

---

# Bench S14 — the EE sweep, and F-040's falsifier

SCPH-50000, HW #309, ten ELFs from `914e20c`. Every prediction in the
section above was written before this sitting.

## The EE sweep [F-044]

| N | `ee` | `ee^` | `gs` | `gs^` | `p` | `m` |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 2.54 | 3.79 | 0.92 | 1.15 | 595 | `m0@0` |
| 1 | 4.96 | 6.22 | 1.70 | 2.00 | 595 | `m0@0` |
| 2 | 7.39 | 8.65 | 2.48 | 2.85 | 595 | `m0@0` |
| 3 | 9.82 | 11.08 | 3.25 | 3.70 | 596 | `m0@0` |
| 4 | 12.32 | 13.58 | 4.03 | 4.50 | 600 | **`m29@270`** |

```
ee = 2.5220 + N x 2.4420    r^2 = 0.9999618
gs = 0.9220 + N x 0.7770    r^2 = 0.9999950
```

**One `ps2ui_render` is 2.44 ms EE + 0.78 ms GS = 3.22 ms**, about 19%
of a field. The driver's own per-frame work — scroll, `sprintf`,
telemetry — is **0.08 ms**. That is the upper branch, decisively: the
prediction put N=4 at 12.05 if the base is negligible and 8.05 if it is
about 1 ms, and the reading is 12.32.

### `gs` was right in shape and wrong in coefficient

| N | predicted | measured | miss |
|---:|---:|---:|---:|
| 0 | 0.92 | 0.92 | +0.00 |
| 1 | 1.84 | 1.70 | −0.14 |
| 2 | 2.76 | 2.48 | −0.28 |
| 3 | 3.68 | 3.25 | −0.43 |
| 4 | 4.60 | 4.03 | **−0.57** |

Perfectly linear, so the extra passes are real and the sitting counts.
But the slope is 0.777, not the 0.9205 predicted on the grounds that
identical draws must cost identically. **0.145 ms of GS time happens
once per frame however many times the UI is drawn.** The mechanism is
not identified and this document does not name one — see F-040 for what
naming a mechanism early costs.

### `m` read the same question independently

At N=4, mean `ee`+`gs` is 16.35 (inside a 16.683 ms field) and peak
`ee^`+`gs^` is 18.08 (outside), so only peak frames overrun. The first
miss is at frame **270 = 9 × 30**, and `SCROLL_EVERY` is 30. The
mechanism is confirmed, not just the count.

### `p` did not scale

595, 595, 595, 596, 600 — against ~2,975 if stats accumulated across
passes. The counter is per-render, confirmed rather than assumed. (The
variation is scroll position; the prediction of a flat 590 was taken
from a different one.)

## The fill sweep — F-040 dies, F-039 is reconfirmed

| build | N | `ee` | `gs` | `gs^` | `gs^ − gs` | F-039 predicts |
|---|---:|---:|---:|---:|---:|---:|
| `oplenv` | 0 | 2.54 | 0.92 | 1.15 | 0.23 | 0.920 |
| `oplenv-fill2` | 2 | 2.51 | 1.49 | 1.56 | **0.07** | 1.493 |
| `oplenv-fill2` (2nd window) | 2 | 2.51 | 1.49 | 1.57 | **0.08** | 1.493 |
| `oplenv-fill4` | 4 | 2.50 | 2.07 | 2.28 | 0.21 | 2.065 |
| `oplenv-fill` | 8 | 2.51 | 3.21 | 3.43 | 0.22 | 3.209 |
| `oplenv-fill16` | 16 | 2.51 | 5.51 | 5.72 | 0.21 | 5.498 |

**F-039 reconfirmed independently.** Refitting these five gives
`gs = 0.9187 + layers × 0.2869`, r² = 0.9999972, against S13's
0.9205 + 0.2861 — agreement in the fourth digit on both coefficients,
from a different sitting on a different revision. The slope is a fill
rate of **0.999 Gpix/s**.

That matters more than a repeat usually does: S13's *other* conclusion
from the same five photographs was overturned here. The instrument was
sound; an inference drawn beside it was not.

**A cross-check nobody asked for.** `ee` reads 2.50–2.54 on every fill
build, identical to the EE sweep's N=0. The fill layers cost **zero EE
time**, which is the instrument validating its own separation: `ee` is
read across the kick window and `gs` after `gsKit_finish` returns, and
the fill arm moves one without touching the other.

## The `-fill2` outlier reproduces [F-045]

Three windows across two sittings, all ≈0.075, against 0.21–0.23 at
every other N. **The unlucky-window explanation is dead** — that is
what photographing N=2 twice bought. It is not monotonic and not fill
scaling: N=0 and N=4 bracket it at 0.23 and 0.21.

No mechanism is proposed. The instrument fix is the one that killed
F-040: **`gs^` needs an `@` the way `m` got one.** Which frame holds the
peak at N=2, and whether the peak-hold is catching the scroll frame at
all, is one sitting away.
