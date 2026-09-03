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
once per frame however many times the UI is drawn.**

### There is exactly one candidate, and this sitting's own slope excludes it by 2×

In an EE build the only GS work in a frame that is not a
`ps2ui_render` is a single `gsKit_clear` — the fill sprites are
`#ifdef`-ed out, and both telemetry lines go through `ps2ui_slot_set`
and are drawn *inside* the render. That clear is a full-screen 640×448
sprite with ABE on: gsKit does not save or restore `PrimAlphaEnable`
around it, and `ps2ui_render` leaves it ON. F-039's slope prices
exactly that draw.

```
clear 0.2869 + render 0.7770 = 1.064  expected
gs(N=0)                      = 0.922  measured
                               0.142  short
```

| | theoretical | measured | efficiency |
|---|---:|---:|---:|
| 640×448 @ 1.180 Gpix/s (blended) | 0.2430 | 0.2869 (fill slope) | 85% |
| 640×448 @ 2.359 Gpix/s (opaque) | 0.1215 | 0.1450 (residual) | 84% |

The residual lands on the *unblended* rate at the same efficiency the
fill sweep shows blended, and 0.2869 / 0.1450 = **1.98** on a part
whose opaque fill rate is twice its blended one. The intercept also
carries any per-frame queue overhead, so 0.145 is an **upper** bound on
the clear — which widens the shortfall rather than closing it.

**No mechanism is asserted** — F-040 is what that costs. But "no
mechanism proposed" and "the only candidate present is excluded by our
own numbers" are different statements, and the second is a much sharper
place to start. Two readings survive: the clear is not actually
blending despite ABE being set, or `gs = base + (N+1) × R` is wrong in
a way that parks 0.14 ms in the intercept.

**`oplenv-clearopaque` is the discriminator**, and it is free. It turns
ABE off for that one draw, which cannot change a pixel — `ALPHA` is
`(Cs − Cd)·As>>7 + Cd` and the clear's vertex alpha is `0x80` = 128, so
the blend is already the identity `Cv = Cs`. `gs` drops ~0.14 and the
**second** reading is right — the clear was paying the blended rate
and the model misallocates. `gs` does not move and the **first** is:
it already cost the opaque rate with ABE on, and turning ABE off
cannot make it cheaper than that.

**That sentence was inverted here and in `findings.md` until S15**, and
`main.c:2114` had it right the whole time. Read against the documents
as they stood, S15's clearopaque photograph reports "the model is
wrong somewhere"; read against the driver, it reports what it actually
found. A discriminator whose outcomes are mapped to the wrong readings
is worse than no discriminator, because it still returns an answer.

### `m` read the same question independently

At N=4, mean `ee`+`gs` is 16.35 (inside a 16.683 ms field) and peak
`ee^`+`gs^` is 18.08 (outside). The first miss is at frame
**270 = 9 × 30** against a `SCROLL_EVERY` of 30, so it is a scroll
frame — 1-in-30 by luck, which is evidence.

**It does not reach "the mechanism is confirmed", and an earlier draft
of this section said that.** The count is the second read and nothing
divides it: 29 misses fits *every scroll frame from 270 on* and fits
*a scattering of near-margin frames whose first happened to be a scroll
frame* equally well. At 16.35 against 16.683 there is 0.33 ms of
headroom, so jitter puts non-scroll frames over too. The two are told
apart by whether 29 ≈ (frame − 270)/30 + 1, and neither telemetry line
carries a frame index. One `frame` field answers this and F-045's `gs^`
question together.

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

**Built.** `gs^` now prints `@frame`, absolute, so `@ % 30 == 0` reads
directly as "the peak was a scroll frame". Line 2 also gained `n`, the
run's frame count, because `m29@270` divides nothing without it — 29
fits *every scroll frame from 270 on* and fits *near-margin jitter*
equally well, and only `29 ≈ (n − 270)/30 + 1` separates them. Both
land in the next sitting alongside `oplenv-clearopaque` and
`oplenv-theme`.

## P3d's two arms, both waiting on the next sitting

**What to boot.** Two ELFs cover the whole sweep:

```
oplenv-scr-cycle     all six screens, 15 s each, repeating
oplenv-compose       <- after the cycle, it is read against two of its screens
```

`oplenv-scr-cycle` walks confirm → detail → landing → recent → filters
→ library and starts over, so a photograph missed is a photograph
retaken ninety seconds later rather than a reboot. **Line 1 says which
screen is up** — `[c:library]` — so the photographs document themselves.

Wait for `ee` to stop moving before shooting. The readout is a
60-frame mean that resets every window, so a screen change dirties at
most the window in progress: the number is settled about two seconds
in, and the dwell is fifteen.

The six standalone `oplenv-scr-*` ELFs are still built and are the
fallback if a cycling reading is ever in doubt — and
`oplenv-scr-library` is also F-046's subject, since that one wants a
photograph from 2–3 m.

**Every arm now names itself on line 1** — `[c:<screen>]`, `[compose]`,
`[theme]`, `[clearopq]` — except the plain `oplenv`, `fill` and `ee`
builds, which print exactly what they printed for S14.

**The tag is slot text, so it is in `g`, and it is not a constant.**
`[c:<screen>] ` is 11 glyphs for `confirm`, `landing`, `filters` and
`library` and 10 for `detail` and `recent` — the trailing space draws
nothing, since `render_slots` counts only glyphs with `w > 0`. This
paragraph first said "about ten glyphs a frame: a constant across the
sweep, absorbed into `base`", and on that reasoning neither sweep table
was moved; every row of both was 10-11 short in the same pull request
that added the tag. The tables below carry it now, and
`tools/check-sweep-table.py` derives the column from the blob and the
driver rather than leaving it to be re-derived by hand.


Neither is measured yet. Both are written down first, the way F-039's
five points and F-044's two branches were, so the sitting scores a
prediction rather than producing one.

### The content sweep — `oplenv-scr-*`, six ELFs

Six screens the blob already carries, spanning **110 to 694 commands**,
a 6.3× range. `ee = base + k_cmd × cmds + k_glyph × glyphs`, and only
`k_cmd` bounds what a precompiled chain can buy — glyph quads are the
dynamic tail the chain cannot contain, so folding them into one slope
would bias it the way that wrongly opens the gate.

Read `c` and `g` off each photograph rather than off this table; they
are on line 2 for exactly that reason. `p` is **not** the x-axis:
`p`/`cmds` runs 0.94 to 1.90 across these six and the orderings differ.

Every column is derived by `tools/check-sweep-table.py` — `commands`
from the screen's `cmd_count`, `drawn` by resolving focus state at the
screen's initial focus, the static half of `slot glyphs` from the
placeholders, the tag from the driver's `#if` chain, and the telemetry
by walking the two `sprintf` formats literal by literal. The only
hand-supplied numbers left are **what each runtime value prints at**:

```
telemetry field widths, in digits
ee 1  ee_peak 1  gs 1  gs_peak 1  gs_peak_at 4
field 2  cmds 3  glyphs 3  unfilled 1  missed 1  missed_at 1  frame 4
prims 3  uploaded 5  theme 1
```

`cmds` and `glyphs` are fenced against the blob, since those two move
when the blob does. The rest are one glance at a photograph. And `@`
and `n` are not declared per reading at all: `@` is a frame index from
the window just past, so it is within two windows of `n` and its width
follows.

**This paragraph used to declare one scalar and the scalar was wrong.**
It said "the driver's two telemetry lines reconstruct to 55 glyphs",
reconstructed by hand at #83 from the real format strings. They
reconstruct to **52** at four-digit counters, and to **54** once `@`
and `n` reach five — which is not a subtlety anyone had to reason
about, because S15 watched it happen inside a single continuous run as
`n` crossed 10000. Every row of the table below was three high, and so
was the compose arm's predicted glyph identity. A character count
nobody was ever going to redo is the wrong thing to declare; twelve
field widths, two of them fenced, is a better one.

Written at four-digit `n` and `@`, which is where the sitting's first
lap falls:

| screen | commands | slot glyphs | drawn | `p` |
|---|---:|---:|---:|---:|
| confirm | 110 | 153 | 64 | 217 |
| detail | 196 | 194 | 99 | 293 |
| landing | 331 | 241 | 206 | 447 |
| recent | 360 | 351 | 189 | 540 |
| filters | 467 | 196 | 253 | 449 |
| library | 694 | 384 | 366 | 750 |

**Six points are enough** — not a hope, arithmetic. r = 0.751 gives a
variance inflation of 2.29, the commands spread over √Σ(c−c̄)² = 462,
and σ is **0.0276 ms**, the residual standard error of S14's own `ee`
fit computed from its five residuals. That puts `k_cmd` at ±4.9% (95%,
3 dof), ±9.8% at twice the noise. **Falsified** by a fitted `k_cmd`
whose standard error exceeds a tenth of it.

### The composition arm — `oplenv-compose`, one ELF

Library then confirm in one frame: **804 commands**, above every sweep
point. F-038 names *"a transition compositing two full screens"* as the
likeliest content to push past half a field, and composition is the one
Phase 1 contract nobody has timed — §4.4 counted its primitives and
stopped.

Read against the sweep, not alone. Both screens are sweep points, so
three photographs settle it:

```
ee(library+confirm) − ee(library)  ==  ee(confirm) − base    per RENDER
                                   <   ee(confirm) − base    per FRAME
```

**Predicted: additivity holds.** `ps2ui_render` keeps nothing between
calls that a second call could reuse — it re-applies the scissor,
re-walks from `cmd_first`, and rebinds every texture. **Falsified** by
a composed frame coming in materially under the sum, which would mean
something *is* reused and F-044's per-render model charges for it
twice.

**Check the glyph identity first, before trusting the time.** The
composed frame must read `g` equal to `g(library) + g(confirm) - 4`
from the two sweep photographs — **533**, against 384 + 153. The `-4`
is the tags and nothing else: this arm carries `[compose] ` (9 glyphs)
on both of its readout pairs, 18, where the two sweep points carry
`[c:library] ` and `[c:confirm] ` at 11 each, 22. It is derived by
`tools/check-sweep-table.py` rather than left to be rediscovered at a
console with three photographs that refuse to add. It is not a formality: the first version of
this arm blanked library's readout so the scrim would not show two of
them, which left the composed frame drawing 466 glyphs against the
sweep points' 521 — and short by `k_glyph × 55` in exactly the
direction that reads as "something is reused". The driver now mirrors
the same readout into both pairs, so the lower line under the scrim
shows the same numbers as the dialog's. If the two lines ever disagree,
or if `g` does not add, stop and say so rather than fitting it.

Line 2 on this arm prints the frame's totals, not `ui.stats` —
`ps2ui_render` zeroes its stats per pass, so the struct would report
confirm's 110 as if it were the frame's 804. A plausible wrong number
on a photograph is the failure mode this file exists to prevent, so
`check-timing-probe.py` asserts the readout reads the accumulators.

# Bench S15 — the content sweep, F-038, F-040's discriminator, P3b on silicon, and F-046 from the sofa

SCPH-50000, HW #309, into a Hisense 58R6+. Twenty-two photographs
across five arms. Every prediction in the section above was written
before this sitting; where one was wrong, it says so below rather than
being quietly restated.

## Every reading, re-derived

`tools/check-sweep-table.py` derives each row of both tables from the
blob, the driver's `#if` chain, its two `sprintf` formats and the
row's own frame count. Nothing here is transcribed and left.

| arm | screen | `n` | `c` | `g` |
|---|---|---:|---:|---:|
| cycle | detail | 1320 | 196 | 194 |
| cycle | filters | 9393 | 467 | 196 |
| cycle | library | 10399 | 694 | 386 |
| cycle | confirm | 11283 | 110 | 155 |
| cycle | detail | 12121 | 196 | 196 |
| cycle | landing | 13082 | 331 | 243 |
| compose | compose | 542 | 804 | 529 |
| compose | compose | 1289 | 804 | 533 |
| screen | library | 3505 | 694 | 382 |

| arm | `n` | top row | `p` |
|---|---:|---:|---:|
| plain | 1421 | 40 | 749 |
| clearopq | 1242 | 34 | 759 |
| theme | 823 | 20 | 756 |
| theme | 1163 | 31 | 758 |

Read the two `detail` rows against each other, and the two `compose`
rows. Same screen, same commands, `g` two apart both times, and
nothing about the UI changed between them. That is the whole of the
next section.

## The telemetry lines are not a constant [F-047]

The sweep table declared **55 glyphs** for the driver's two telemetry
lines. They measured **52**, and then **54** in the same continuous
run — the six `cycle` rows above are one uninterrupted boot from
n1320 to n13082, and `g` steps up by two as `n` and `@` cross 10000.

```
line 1   11 literals + 12 fixed digits + @        = 23 + digits(@)
line 2    8 literals +  9 fixed digits + n        = 21 + digits(n)
                                                    44 + both
```

52 at four-digit counters, 54 at five, 50 at three — which the compose
arm then reproduced at a different boundary, reading `g529` at `n542`
and `g533` at `n1289` on the same build with nothing else changed.

**Three documents carried the wrong number and one tool read it back.**
Every row of both sweep tables was three high, and so was the compose
arm's predicted glyph identity: 539 where the console read 533. The
prediction was never going to be met, and the arm's own integrity
check — *"if `g` does not add, stop and say so rather than fitting
it"* — would have fired on a correct run.

The fix is not a better constant. `check-sweep-table.py` parses the
format strings now and declares field widths instead, `@` and `n` are
derived from each reading's own frame count, and every photograph
above is re-derived rather than believed.

## The content sweep [F-044]

Six screens, 110 to 694 commands, glyph counts on the measured
52-basis.

```
base    = -0.023 ms       se 0.043
k_cmd   =  1.276 us/cmd   se 0.109    se/|k| = 0.085
k_glyph =  5.010 us/glyph se 0.240    se/|k| = 0.048
R2 = 0.9986    residual sigma = 33 us
```

| screen | `c` | `g` | `ee` | fit | resid |
|---|---:|---:|---:|---:|---:|
| confirm | 110 | 153 | 0.915 | 0.884 | +31 µs |
| detail | 196 | 194 | 1.203 | 1.199 | +4 µs |
| landing | 331 | 241 | 1.573 | 1.607 | −33 µs |
| recent | 360 | 351 | 2.180 | 2.195 | −15 µs |
| filters | 467 | 196 | 1.540 | 1.555 | −15 µs |
| library | 694 | 384 | 2.813 | 2.786 | +27 µs |

`f16.68` and `m0@0` on all fifteen photographs. No missed field on any
screen.

### The falsifier's outcome depends on the intercept, and the sitting cannot hide that

The criterion was **"falsified by a fitted `k_cmd` whose standard error
exceeds a tenth of it."** Fitted freely it is 0.085 and the arm
survives. But the compose arm below measures `base` independently at
**0.088 ms**, S14 measured the same quantity at 0.08, and the sweep's
own intercept — a six-point extrapolation back to zero commands from a
nearest observation 110 away — is the outlier at −0.023.

| intercept | `k_cmd` | se | se/\|k\| | σ | |
|---|---:|---:|---:|---:|---|
| free (−0.023) | 1.276 | 0.109 | 0.085 | 33 µs | survives |
| pinned (0.088) | 1.320 | 0.167 | **0.127** | 52 µs | **falsified** |

By the criterion exactly as written — the ±4.9% arithmetic above is a
free-intercept fit, since the variance inflation only means anything
there — it survives. Recording that without this table would be
recording a result that exists because the fit was allowed to choose an
intercept the hardware says is wrong.

Leave-one-out sharpens the same point. `k_cmd` itself is stable across
all six refits (1.16 to 1.38, every one inside the full fit's ±1σ), so
the estimate is not fragile; the *pass* is. Dropping `detail`, `recent`
or `filters` fires the falsifier.

Adding `drawn` as a third regressor does not rescue the pinned fit: its
coefficient comes out negative and swamped by its own error in every
fit that also contains `cmds` (se/|k| 0.75 pinned, 0.94 free). The
inflated residual is the cost of forcing an intercept the six points do
not want, not a missing term.

### What the prediction got right, and what it assumed

The design arithmetic held. Predicted `se(k_cmd) = σ√VIF / √Σ(c−c̄)² =
0.090 µs`; measured 0.109, and the 21% miss is the 20% by which the
real residual σ exceeds S14's. Six points were enough, in the sense the
prediction meant.

What the ±4.9% figure silently assumed is `k_cmd ≈ 5.9 µs/cmd`, which
is S14 dividing one screen's render by its prims. **The measured value
is 1.28.** A per-prim number taken from a single screen was a blend,
and separating the two is what this arm existed to do:

| model | slope | se/\|k\| | R² |
|---|---|---:|---:|
| cmds only | 2.98 µs/cmd | 0.251 | 0.799 |
| glyphs only | 7.13 µs/glyph | 0.131 | 0.935 |
| both | — | — | 0.999 |

### What `k_cmd` bounds, which is the point

```
k_glyph / k_cmd = 3.93
```

| screen | `ee` | cmds | glyphs | cmd share |
|---|---:|---:|---:|---:|
| confirm | 0.915 | 0.140 | 0.766 | 15.3% |
| detail | 1.203 | 0.250 | 0.972 | 20.8% |
| landing | 1.573 | 0.422 | 1.207 | 26.8% |
| recent | 2.180 | 0.459 | 1.758 | 21.1% |
| filters | 1.540 | 0.596 | 0.982 | 38.7% |
| library | 2.813 | 0.885 | 1.924 | 31.5% |

On the heaviest screen a **perfect** precompiled chain removes at most
0.885 ms of a 2.81 ms frame, and only by eliminating command walking
rather than making it faster. The dynamic tail the chain cannot contain
is the larger half on every screen in the sweep. That is the decision
this arm was built to inform, and it is unaffected by which intercept
you take: `k_cmd` is 1.28 to 1.32 under every reading. What the sitting
did not achieve is the precision it pre-registered.

### `gs` is not command-shaped

The same model on the GS readings gives R² 0.78 with both slopes
swamped (se/|k| 0.84 and 0.91) and a 0.428 ms intercept. Best single
regressor is prims at R² 0.83, still se/|k| = 0.225. Nothing in this
sitting's regressor set explains GS time, which is what you would
expect if it is bound on pixels rather than on draw count. It needs its
own x-axis, not a better fit to this one.

## The composition arm [F-038]

```
photo 1   [compose] ee3.62^3.63 gs1.50^1.62@1241   f16.68 c804 g533 u9 m0@0 n1289
photo 2   [compose] ee3.60^3.62 gs1.50^1.61@517    f16.68 c804 g529 u9 m0@0 n542
```

**Glyph identity first, as the arm requires.** `c804` is 694 + 110
exactly, and `g` derives on both photographs — 533 at four-digit
counters, 529 at three. The two readings differ by 4 and the
digit-width rule predicts 4. Nothing is blanked and nothing is
asymmetric.

The mirrored pair agreed on photo 1 (`n1289` on both lines). On photo 2
the second line's last digit could not be resolved from the
photograph — `n541` or `n542`. Immaterial: both are three digits, so
`g529` is predicted either way, and every other field matched. Worth a
re-read, not a stop.

**Additivity holds.** The composed frame comes in under the naive sum
of the two sweep frames, which is what the falsifier warned about — but
the shortfall is exactly one `base`, which is what additivity itself
predicts, since adding two frames double-counts the driver's per-frame
work:

```
base = ee(lib) + ee(conf) - ee(compose) - k_glyph x dg
photo 1:  2.813 + 0.915 - 3.62 - 4 glyphs  = 0.0880 ms
photo 2:  2.813 + 0.915 - 3.60 - 8 glyphs  = 0.0879 ms
```

Two photographs at different counter widths, different `ee` readings
and different glyph corrections, agreeing to 0.1 µs — against S14's
0.08 ms for the same quantity, measured by a completely different
design. **`ps2ui_render` reuses nothing between calls.** F-044's
per-render model is not charging twice for anything.

Strictly, the difference measures `base_sweep` minus the compose
build's extra per-frame work (one more `ps2ui_screen_set`, two more
`ps2ui_slot_set`), so 0.088 is a floor. That only tightens the
agreement with S14.

**And F-038's worry is not realised.** Two full screens composited —
804 commands, 533 glyphs — cost 3.62 ms EE and 1.50 ms GS. Twenty-two
percent of a field on the EE, nowhere near half.

## The clear is not blending [F-048]

```
oplenv        ee2.77^4.04 gs1.02^1.26@1320   f16.68 p749 up28224 m0@0 n1421
clearopq      ee2.81^4.08 gs1.03^1.27@1140   f16.68 p759 up28224 m0@0 n1242
delta         +0.04 +0.04  +0.01 +0.01                 +10      +0
```

**The +10 is the tag, not the clear.** `[clearopq]` is 10 glyphs and
the control arm carries none, which nothing in the arm's design
accounted for. From the fitted slopes the tag costs 0.050 ms EE and
0.009 ms GS; the raw deltas are 0.04 and 0.01, both inside the
readout's own quantum. After removing it, the ABE change moves `gs` by
**+0.001 ms**, against the −0.14 that "the clear was paying the blended
rate" requires. Fourteen times outside.

The confound biases *away* from the falsifier, so it cannot have
manufactured the null — but it had to be subtracted rather than
ignored, and the arm was specified before #42 named it on the readout.

Everything else is identical: `ee^ − ee` 1.27 on both, `gs^ − gs` 0.24
on both, `up28224` on both, and 1140 = 38 × 30, a scroll frame. The
screen looks the same, which `main.c:2126` names as the first thing to
check.

**Read against the correct mapping, this is the first of the two
readings the discriminator was built to separate.**
The 0.14 was never unexplained; it was unexplained only under the
assumption that an ABE-on draw pays the blended rate, and this
falsifies that assumption directly rather than by residual.

| source | value | method |
|---|---:|---|
| S14 residual | 0.145 | render slope subtracted from `gs(N=0)` |
| compose arm | 0.115 | two sweep frames subtracted from one composed |
| opaque theoretical, 640×448 | 0.1215 | 2.359 Gpix/s |
| blended theoretical | 0.243 | 1.180 Gpix/s |

**A third candidate dies here, and it is the one this project's own
history made most likely.** The v2 alpha probe found that on this
console an ABE-on sprite at alpha `0x7f`–`0x80` painted *nothing*. If
the clear were a no-op for that reason, turning ABE off would make it a
real full-screen opaque fill and `gs` would have **risen** by ~0.145.
It did not move.

What stays open is the mechanism: why an ABE-on draw does not pay the
blend rate. That is now a narrow question about GS state this codebase
has never written — `ALPHA`, `PABE`, `TEST`, inherited from whatever
`gsKit_init_screen` left behind — which is F-001 and F-004's thread
rather than a new one.

## Theming costs nothing [P3b]

P3b on silicon for the first time.

```
t1 light   [theme] ee2.79^4.07 gs1.02^1.27@720    f16.68 p756 up28224 m0@0 n823  t1
t0 dark    [theme] ee2.80^4.07 gs1.03^1.26@1080   f16.68 p758 up28224 m0@0 n1163 t0
```

Both `p` values derive, on a fourth telemetry format and a third tag,
and the two differ by 2 entirely because of counter width.

The clean comparison is theme against theme, everything but the CLUT
row and two telemetry digits held fixed:

```
t0 - t1 = 2 glyphs     predicted +10 us     observed +10 us
```

Against the plain build both themes land 15 µs under the
glyph-corrected prediction, the same bias in both, half a residual σ.
`ps2ui_theme_set` is free by construction rather than by measurement —
`ps2ui.c:780` is a bounds check and a `uint16_t` write, no GSGLOBAL and
no upload, because the row is read by the EE at draw time.

**No first-draw penalty after a switch, and the 241-coprime choice is
what bought the observation.** At `n823` the last completed peak window
is [720, 780). It contains frame **723 = 3 × 241**, a theme switch, and
frame **720**, a scroll frame. The peak landed on 720. So the first
frame drawn under a newly selected theme row costs no more than an
ordinary frame on either clock, which rules out lazy CLUT residency:
every row's CLUTs are already in VRAM after `ps2ui_upload`.

`main.c:2059` argued for 241 over 240 on the grounds that a multiple of
`SCROLL_EVERY` would weld the switch's cost to the scroll's and make it
unmeasurable. It bought exactly the observation it was written for, on
the first sitting.

`t` tracks: 823 / 241 = 3 switches → `t1`, 1163 / 241 = 4 → `t0`, both
consistent with two theme rows and with row 0 being the baked default.
241 frames at 59.94 Hz is 4.02 s, which is what the operator saw.
`up28224` on both, so a switch does not disturb the streamed art.

**One thing the photographs could not settle.** In the plain build the
`ALL` chip reads as a filled rounded rect; in both theme photographs
the chip row reads as five outlined boxes. Angle and glare differ
enough between the shots that this is not callable either way. What the
numbers do say is that it is not a missing primitive: `drawn` is 366 on
both theme readings, identical to the plain build at the same scroll
position, so any difference is colour and lives in the tint table.
**The check that settles it is free and sharp** — theme row 0 is the
baked default, so a `t0` frame must be pixel-identical to plain
`oplenv`. One straight-on photograph of each, same distance and
exposure.

## 11px from nine feet [F-046]

`oplenv-scr-library`, static, read at 9 ft with and without correction.

```
[library] ee2.82^2.83 gs1.01^1.10@3423
f16.68 c694 g382 u9 m0@0 n3505
```

**The reading scores itself.** `g382` derives exactly — static 321 plus
a 9-glyph `[library]` tag plus 52 — and `g382` had appeared in no
document and in no earlier photograph. `n3505` puts the last completed
peak window at [3420, 3480) and `@3423` falls inside it, so a misread
digit in either counter would have shown. `u9` is the nine unbound art
slots, and the screen carries no cover art, which is what the static
arm means.

This is not "the operator says it looks fine". It is a three-digit
value at 11px, read off the panel and checked against an independent
derivation.

### The finding is about angular size, not pixels

The falsifier named 2–3 m. 9 ft is 2.74 m, and the panel is a 58"
16:9, so the vertical scale is fixed regardless of how the 4:3 signal
is fitted horizontally:

```
722 mm of panel height / 448 authored lines = 1.612 mm per line
```

| authored | em | cap height |
|---|---:|---:|
| **11px** `.sub`, `.telem-l` | 22.2′ | **15.6′** |
| 13px row titles | 26.3′ | 18.4′ |
| 14px chips, scores | 28.3′ | 19.8′ |
| 22px `LIBRARY` | 44.4′ | 31.1′ |

A 20/20 Snellen letter subtends 5′ overall with 1′ per stroke feature.
The 11px cap height at 15.6′ is **3.1× a 20/20 letter**, and a 1px stem
subtends **2.0′**, twice the resolution limit. The strokes resolve, not
just the letter mass. Threshold acuity to read this layer here is about
**20/62**, which is why correction made no difference.

**Stated in pixels the finding does not transfer, and that is the
correction this reading forces.** 11px means nothing without a panel
size and a viewing distance. Stated as *"the secondary text layer
clears 15′ of cap height and 2′ of stroke at a seated distance"* it
transfers to any panel, and it survives a future change to the authored
sizes.

The same numbers bound the claim honestly:

| criterion | panel diagonal at 9 ft |
|---|---:|
| 20/20 threshold, readable at all | 18.6″ |
| ~3× threshold, comfortable | **55.9″** |

58" sits just above the comfortable line. A stranger 9 ft from a 43"
set is at about 1.9× threshold — probably still readable, but not the
effortless case measured here. That is guidance rather than a second
falsifier; the 3× figure is a rule of thumb, not a standard.

## What the peak-hold decomposed, unasked

| build | `ee^ − ee` | `gs^ − gs` |
|---|---:|---:|
| `oplenv` (scrolls) | 1.27 | 0.24 |
| `clearopq` (scrolls) | 1.27 | 0.24 |
| **`scr-library` (static)** | **0.01** | **0.09** |

`main.c:2224` asserts that the EE peak's excess over the mean *is*
`oplenv_bind_window`, correcting an earlier comment that contradicted
the model three lines above it. Remove the bind and the peak collapses
onto the mean. The claim is now measured from both sides.

And the GS spread decomposes into **0.09 baseline jitter plus 0.15 for
the texture upload**. F-045's anomaly is that `oplenv-fill2` reads
`gs^ − gs` = 0.075 while N=0 and N=4 bracket it at 0.23 and 0.21 —
which sits on the **no-upload** figure, not the no-scroll one. That
reframes the open question from "why is the spread small at N=2" to
"what hid the upload spike in that window", and gives the re-run
something specific to check: whether its peak frame is a scroll frame
at all.

## What this sitting did not settle

- **F-045 itself.** The control is established and the hypothesis is
  named; `oplenv-fill2` has not been re-shot with the `@`.
- **The `t0` versus plain comparison**, one straight-on photograph
  each, which decides the chip question above.
- **F-044's precision.** The arm's verdict is conditional on the
  intercept and is recorded that way. Pinning it to the
  compose-measured `base` and re-running the sweep with a seventh point
  further from the others would settle it; nothing in this sitting can.
- **F-040's mechanism.** Narrowed, not closed.
