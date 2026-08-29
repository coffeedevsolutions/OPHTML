# How this project tests itself, and the ways it has failed to

Every claim in this document is drawn from this repository's own
history: sixty-one pull requests, four bench sittings on a SCPH-50000,
and a rendering path that has been wrong in public more than once.

It exists because one failure shape accounts for most of the time this
project has lost, and it is not a bug shape. It is a **test** shape:

> A check whose passing state is reachable without the property holding.

Thirty-odd instances are catalogued below. Six shapes were written first; the seventh was found by a reviewer, in the tool built to enforce the other six. They were written by people
being careful — most were caught by review or by the author before
shipping, several by a gate, two by a console. What follows is the
taxonomy, because the instances are varied and the shapes are few.

---

## The seven shapes

### 1. The guard that skips

A precondition quietly disables the check, and the suite reports
coverage it never had.

The sharpest case: `test_arena_matches_the_runtime`
was the **only** test holding the baker's hand-modelled `GSTEXTURE`
against the runtime's real `sizeof`. It guarded on `os.path.exists` for
a built object — and CI ran the baker tests *before* the runtime build,
so it skipped on every run. Proven sole-of-its-class by adding a `u32`
to the vendored struct: only that test failed, 2134 against 2286.

The fix is instructive. It was **not** fixed by reordering the workflow:

> the next person to tidy the workflow reorders it back and gets no
> signal

It was fixed twice instead — the test builds the object itself, and
`PS2UI_REQUIRE_CROSSCHECK=1` turns a skip into a failure in CI.

**And then the lesson was applied to one test and not generalised**,
which is how the same defect ran for months two hundred lines further
down the same file. Four `TestS7Discriminator` tests skipped with
*"bench fixture not built; ci.yml builds it"* — true of the workflow,
false of the moment: `ci.yml` built that fixture ninety-six lines after
the step that ran them. They had never executed in CI, and a skip
reports as `OK`, so nothing said so. Found in review of the v7 format
change, in a diff that did not touch them.

`unavailable()` is now a helper the whole file shares rather than a
closure inside the one test that needed it first, and the variable
means the broader thing: under it, **every** fixture the suite reaches
for must exist. The workflow was reordered as well — the reorder is the
fix, the failure is the tripwire, and shipping only the first is what
invites being reordered back.

**The general form, and the first draft of it was wrong in a way worth
keeping.** It read: *a skip message may cite a workflow step as the
reason the skip is safe only if that step has already run.* Review
applied it to the one skip this file deliberately keeps —
`TestCheck.test_the_shipped_examples_pass`, which cites a step at
`ci.yml:191` and runs at `:75`, **116 lines too late** — and the rule
condemns it. It should not: that step really does assert the same
property over the same bytes, by name, and gates.

So ordering is the incidental part. For the S7 four the coverage was
not late, it was **zero**: nothing else ran those assertions in any
position, and had the fixture build happened to sit at line 40 all
along, an ordering rule would have blessed them while they still had no
second reader.

> A skip message may cite a workflow step as the reason it is safe only
> if that step **actually asserts the same property**. If nothing else
> does, the skip *is* the coverage — and a skip is reported as `OK`.
> Ordering matters only when what is cited is the step that builds the
> fixture the test needs.

That condemns the four, exempts the fifth for the reason that actually
holds, and does not depend on line numbers that move.

**The audit it prompted found a worse one**, two hundred lines up from
the four: `test_capacity_survives_the_bake` skipped with *"bake refused
a capacity it should accept"* — a skip guarding not a missing fixture
but the test's own subject. No reordering could have made that one run,
because the condition it skipped on **was** the failure it existed to
detect. A skip on a missing fixture is a coverage gap; a skip on your
own assertion is a test that reports `OK` for the bug.

Others: a `argc == 3` guard that silently skipped eighteen checks when
a fourth fixture was added, leaving the suite green *and smaller*; and
`opl-env` registered in `check-blobs.sh`'s `ALL` list while `ci.yml`
passed an explicit three-blob list, so the registration did nothing.

> **A tripwire that skips is worse than none, because it reports
> coverage it never had.**

Rule adopted: a guard on inputs must say *"I have what I need"*, never
*"the caller passed exactly what I expected"*.

### 2. The check sourced from what it checks

Both sides of the comparison come from the thing under test, so it
agrees with itself.

`arena_size` was first fenced by asserting that `load(need)` passes and
`load(need - 1)` fails — with **both sides sourced from `arena_size`**.
It stays green with the size over-reported by any amount. Replaced with
an independent carve of the same header.

The subtlest instance is recent. Ladder v2's U-axis fence checked that
the cyan column differed from the body — sampling the pattern *at the
same constant the pattern paints with*. Move the constant outside the
sampled rectangle and the card goes U-blind with 311 checks green. Fixed
by asserting the property (`L2_COL_LAST == L2_W - 1`) rather than
relying on two expressions happening to agree.

And the one that nearly cost a fourth sitting: ladder v2's **positive
control was circular**. Arm `1/2` was required to read SHIFTED, on the
reasoning that half a texel shifts an exact sampler — but whether the
GS is an exact sampler was [F-019], the thing under test. The reading
survived only because the card had a second, non-circular way to see a
shift.

### 3. The instrument blind to its own hypothesis

The fault the instrument exists to catch renders as a clean pass.

probe6 v2's checker had a **16-texel period, and 16 divides 64**. A
stride fault shifts every row by a multiple of the period, so the one
fault class the column existed to catch rendered perfectly clean. It
was voided at a bench, twice, before being rebuilt aperiodic with a
column immune by construction.

Ladder v1's arm C is the same shape and cost more. Its texture ignored
`x` and was uniform on every row but the last, so a bias that merely
*shifted* sampling by a whole texel was invisible on the body — and on
the last row it read texel 16, **clamped back to 15, and lit up
anyway**. Arm C showed a bright line whether the bias corrected
sampling or ruined it. A fix was built on that reading and shipped to
CI, where the emulator gate rejected it at 17.34 against a healthy 4.79.

> **An instrument blind to its own hypothesis is worse than no
> instrument**, because no instrument does not produce a reading anyone
> acts on.

### 4. The fixture where two quantities coincide

The test cannot distinguish the thing it measures from something else,
because at the chosen size they are equal.

A VRAM check used a 64×64 texture — where the payload size and the
page-rounded size are **the same number**, so it could not tell which
one the code reported. Changed to 100×70.

A flat-fill check compared texels against `cov[0]` — which is the
white border, not the fill. It passed on a blank cover. Fixed to count
distinct texels; falsifying *that* fix then found the corner block
supplying horizontal variation, so the axis scan had to start clear of
it.

The README once claimed the blend was correct, citing the two alpha
values where the correct and the inverted equation **agree**.

And the reason three probe rewrites were needed at all: the step-2
probe asked the operator for a *measurement*. Photographed reference
colours `#8c0784`, `#c503c1`, `#fd00fd` and `#ff00ff` all came back
within ten units of each other.

> **Operators can compare, not measure.** Binary judgements only —
> seam or no seam, present or absent — plus tick marks, so a vanished
> column is found by counting a gap rather than by inferring one.

### 5. The check that never executed

It compiled away, errored out, or was never wired in — and reported
success.

A compile probe printed **"GSTEXTURE::Function absent, as expected"**
while dying in `tamtypes.h` on `#error Either _EE or _IOP must be
defined!`. It would have printed the same against a gsKit that *had*
the field. It was caught by its author, in the run that supported the
conclusion he wanted.

A table pin looped `k3 < 8` over an array of nine — so a ninth row with
a deliberately impossible expectation passed green. That is an
un-failable check *inside the check whose entire job is to be a
tripwire*, and it failed on exactly the maintenance action the table
invites.

Others: `$(wildcard irx_*.c)` evaluated at make-parse time, before the
generator that writes those files ran, silently dropping the IOP
modules — *a generated file list cannot be discovered by the same make
pass that generates it*. A composition fence whose stub was missing
`gsKit_clear` entirely, so the "fence" failed with *undefined
reference*. A reviewer-suggested `#if PS2UI_ARENA_LIMIT > SIZE_MAX`
that cannot work, because the preprocessor may not evaluate a cast.

And a shim that made the host compile something the target forbids:
ps2sdk's newlib `#error`s on `fio`/`fileXio`, so `covers.elf` had
**never compiled for a console** while host `syntax-check` sat green.

> **A shim for an API the target forbids is worse than no shim at
> all.** The shims make the host *compile*, not *conform*; the
> container is the arbiter.

### 6. Written down instead of tested

The belief that documenting a property is the same as asserting it.

One PR shipped four drafts that asserted nothing. The fourth was found
in review — a documented trap about `gsKit_TexManager_nextFrame` had
been **written down three times and asserted nowhere**, because the stub
implementing it was a bare no-op. The author's own account:

> the fourth was the one I never tested because I'd written it down and
> that felt like the same thing

Hand-quoted glyph metrics were wrong in **four consecutive pull
requests** — "capitals are 11 texels tall" (they are 9 and 10), "`S` is
9 wide" (8 in the face that draws the static text). The conclusions
survived every time, which is precisely why it recurred: nothing
depended on the number, so nothing checked it. The fix was not to be
more careful. It was to make `ps2ui-check` print the count on every run
— see [F-022].

And the worst of them, confessed in its own commit message:

```c
memcmp(a, b, n) != 0 || 1
```

An un-failable check with a `|| 1` on it, written to make it pass after
a fixture size had been chosen where both sides were identical.

### 7. The rule whose coverage is narrower than its purpose

It runs. It passes. It asserts over a smaller domain than its
description implies — and the gap is invisible because nothing skips
and nothing errors.

This shape was added because a review found it in the tool built to
catch the other six, in the commit that introduced it.

`check-findings.py` rule 6 refuses any document that cites an
overturned finding without marking it historical. Exact, enforced,
falsified before shipping. But its coverage is a function of how many
citations exist, and when it shipped the count was:

```
docs/method.md         3
docs/bench-runbook.md  0
docs/bench-phase1.md   0
docs/bringup.md        0
docs/PLAN.md           0
README.md              0
```

**So it guarded its own README and nothing else.** The two documents
named in the pull request as the *motivation* for the rule — one still
stating a disproved cache fault as fact ten lines below the section
disproving it, the other still calling a settled question unsettled —
carried no citations, so the rule could not see either. The rot that
justified the mechanism was in the tree, and invisible to the
mechanism.

Nothing was skipped and nothing failed to execute. The rule did exactly
what it said, over a domain far smaller than the sentence describing it
suggested.

The repair had two halves, and only the second is durable:

- backfill the citations, so the known-bad passages come under the rule
- **rule 8**: an overturned finding must be cited `:historical` by at
  least one document, so a belief cannot be retired in the ledger while
  the prose that taught it sits unreferenced

The first fixes today's gap. The second makes tomorrow's impossible,
because retiring a belief now fails CI until someone goes and corrects
the text.

> **Ask of any check: not "does it fail when broken", but "over what
> domain does it hold?"** The first question has an easy answer and the
> second is where the coverage hides.

---

## What actually catches these

Sorted by cost, cheapest first. The ordering is the point.

| detector | caught | cost |
|---|---|---|
| **Falsifying the check** — break it deliberately, confirm it fails | the arena cross-check, the `k3 < 8` pin, every fence since | minutes |
| **Review** | most of the instances above | hours |
| **A blocking gate** | the `+0.5` fix, the YAML step that caught its own formatting | one CI round |
| **A bench sitting** | probe6 voided twice; S1 returned VOID | a day, and a person |

> The only reliable detector is the cheapest one: **deliberately break
> the check and confirm it fails.** Everything below it in that table is
> luck or expense.

And one reading of that detector's output is worth naming, because it
looks like good news and is not:

> **A 100% pass rate on deliberate breakage is itself a finding.** If
> every sabotage passes, the likeliest explanation is not that the code
> is unbreakable — it is that the sabotages did not run.

That inference is what caught the stale-binary case above: three
sabotages, three passes, and the checks were fine. It generalises well
past make dependencies, to any apparatus that sits between the change
and the assertion.

This is now the standing rule. Every fence added to this repository is
falsified before it ships, and the sabotages are recorded in the commit
message — not because the record is interesting, but because writing
them down is what forces them to be run.

---

## Three rules that came from the hardware, not the tests

**VOID is a third outcome.** A reading that the instrument was not
capable of giving is not a failure and it is certainly not a pass.

> seven passes with one void among them is worse than no run at all

Implemented as a distinct exit code, and as a named branch in every
bench runbook step.

**Read the library first.** Four bench-blocking questions in a row —
`GSTEXTURE::Function`, `TEX0.TFX`, `TEX0.TCC`, `TEX0.TBW` — were all
answerable from gsKit's source, and were instead attacked with A/B ELFs
on a console. Each cost a sitting.

A related miss, from the disproved cache-writeback theory:

> the line was in my own grep output, one line above the hits I quoted;
> I searched for the narrow symbol and stopped reading

**A green gate means no gross regression, never a certified path.** The
emulator diff's tolerance is 6.5; a build with a known-wrong CLUT
convention scores 4.83, comfortably inside it. The gate's own documented
triage advice cites a "resampling floor" of 6.40 which sits *above* the
healthy capture at 4.79 — so following it would argue for loosening the
gate. Both facts are recorded next to the threshold, because a
calibrated number without its blind spots written down is a number
people will over-trust.

---

## The one that is not a testing lesson

[F-011:historical] — the argument that a `+0.5` UV bias must be wrong — was
correct arithmetic resting on a false premise, and it survived for
months through a design document, a probe design, and four pull
requests.

It survived because **every renderer this project owns is exact**. The
previewer indexes texels directly. Play! interpolates in float. At
power-of-two spans the argument is not merely plausible, it is exactly
right. Nothing off-console could have caught it, and nothing off-console
did.

The lesson is not "test more". It is:

> **When every instrument you own shares an assumption, that assumption
> is invisible to all of them at once.**

The counter-measure that worked was writing down what would falsify the
claim, and then building the one instrument that could. It took two
attempts, because the first one could not fail.

## Restoring after a deliberate breakage

`git checkout -- <file>` does not restore the file. It restores HEAD.
Every uncommitted change in that file is destroyed, silently, with a
zero exit status.

Deliberate breakage is the only reliable detector this document has to
offer, so it gets run constantly, usually against a file that is being
actively edited -- which is the exact condition under which that
command is destructive. It has now destroyed work four times here:
`runtime/ps2ui.c`, the opl-env driver, `docs/bench-runbook.md`, and the
`ticks_to_us` change. Three were caught immediately. One was committed
and pushed in a failing state before anyone noticed.

The counter-measure is not vigilance, because vigilance is what failed
four times. It is to keep git out of the restore path entirely:

- `tools/falsify.sh` snapshots the real bytes and puts the real bytes
  back. Use it rather than hand-rolling a sabotage loop.
- Commit before falsifying anyway. A snapshot protects against the
  restore; a commit protects against everything else.

This belongs in a document about checks that pass for the wrong reason
because it is the same failure in the tooling around the check: a
restore that reports success while having thrown the work away.
