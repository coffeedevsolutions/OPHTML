# Design: the v6 resource model

*Draft · 2026-08-20 · rev 2 · 2026-08-24 · Phase 1 of `docs/PLAN.md` · §2 and §3 implemented*

> **Status.** §2 (the arena) and §3 (texture slots — the v6 format
> move and the runtime path) have shipped; §3's authoring half, §4 and
> §5 have not. Where implementation contradicted the design, the
> document says so in place and marked **[implemented]** rather than
> being quietly rewritten: the argument that lost is worth as much as
> the one that won, and a design doc that only ever agrees with the
> code is a changelog.
>
> **Rev 2** is the adversarial pass this document asked for, run after
> Phase 0 closed — against the code as #40–#44 left it, which is not
> the code this was drafted against. Three findings are folded in
> below, marked **[rev 2]**: a sixth ceiling the draft did not count
> (`clut_pool`, born after drafting), a collision between §3's fixed
> reservations and the TexManager migration, and a byte-count
> conflation in `ps2ui_tex_set`. One open question (the streamed CLUT
> convention) is settled rather than reopened, because Phase 0 built
> the instrument that guards the answer.

Phase 1 is one deliberate format move rather than a dribble of bumps
(`PLAN.md` §6). This is what it contains and why, written before the
first line of it existed so the argument could be attacked cheaply —
which it then was, twice: once by rev 2's adversarial pass, and again
by the implementation, which found three things neither draft
predicted.

It is designed against measurements, not principles. Everything
numeric here comes from `fixtures/opl-scope/` and the two shipped
examples. Nothing here depends on GS correctness, which is why it can
be designed before Phase 0's bench session — but nothing here should
be *implemented* before it, because a resource model debugged against
an unproven renderer means debugging two things at once.

---

## 1. What is wrong now

`PLAN.md` §4.1 in one sentence: the runtime context is sized by
compile-time ceilings, and almost nothing in it derives from the blob
it loaded.

```c
uint16_t  screen_focus[PS2UI_MAX_SCREENS];        /* 8   */
GSTEXTURE gs_tex[PS2UI_MAX_TEXTURES];             /* 32  */
char      slot_text[PS2UI_MAX_SLOTS][PS2UI_SLOT_BUFSZ];  /* 16 x 96 */
uint8_t   slot_is_set[PS2UI_MAX_SLOTS];
uint32_t  hidden[(PS2UI_MAX_HIDEABLE + 31) / 32]; /* 256 */
```

Five independent ceilings with three different failure behaviours —
two reject at load, one (`MAX_HIDEABLE`) fails soft and silent, and
`MAX_SCISSOR_DEPTH` fails at render. The measured UC-3 environment
needs 121 slots against a cap of 16, so the ceiling has to move
regardless. **Moving it is the wrong fix**, and the numbers say so
loudly.

Sizing every ceiling for UC-3 and charging it to every blob:

| UI | slots | arena | fixed ceilings | overpay |
|---|---:|---:|---:|---:|
| UC-3 environment | 121 | 3,825 B | 13,321 B | 3× |
| channel-6 | 15 | 1,404 B | 13,321 B | 9× |
| memcard | 6 | 1,086 B | 13,321 B | 12× |
| runtime list fixture | 4 | 158 B | 13,321 B | **84×** |

The waste scales with the ceiling and not with use, so raising the cap
to fit the biggest UI makes every smaller one worse. That is the
argument for a different shape rather than a bigger number.

**[rev 2] There is a sixth ceiling, and it is bigger than the other
five together.** The cache-writeback work (#40) and the TexManager
migration (#41) added `clut_pool[PS2UI_MAX_TEXTURES][256*4]` — 32,768
bytes of 16-aligned static in `ps2ui.c` — because gsKit keeps the
`Clut` pointer and re-reads it on any later bind, so permuted palettes
must live as long as the context. Every blob pays for 32 CLUTs; the
memcard blob has **one**, shared by its eight indexed textures. (Rev 2
said "2" here, which was neither the CLUT count nor the indexed-texture
count — corrected against the blob.) The fixed overhead this design
removes is therefore ~36 KiB — the 32 KiB pool plus a 3.3 KiB context.

That is a *different quantity* from the table above, which this
sentence used to read as correcting. The table is a counterfactual:
what the five original ceilings would cost if each were raised to fit
UC-3 and charged to every blob. The ~36 KiB is what the shipped
context actually cost, pool included. Both are true and neither
supersedes the other; the table argues the shape is wrong, and this
paragraph says how much the shape was costing before anyone raised
anything.

**[implemented]** Reconstructed from `2290a27^:runtime/ps2ui.h` and
confirmed at review: `clut_pool[32][1024]` 32,768 + `gs_tex[32]` at EE
pointer width 1,280 + `slot_text[16][96]` 1,536 + the small arrays 64
= **35,648 B**. The UC-3 environment asked for 8,285 bytes when this
was measured, and a two-slot overlay for a few hundred. (Every figure
in this document is that measurement, dated here rather than restated
as current: P3b-6 moved the fixture's records, textures, VRAM, blob and
arena afterwards. `fixtures/opl-scope/README.md` carries the current
numbers and `figures.py` checks them.)
The pool moves into the arena (§2), which also inherits its two hard
properties: the region must be 16-aligned (the #40 DMA-source
invariant — a misaligned source truncates silently) and must outlive
every render, not just the upload, because the TexManager re-binds
evicted textures from it at draw time.

### The blob already knows

Slot text is the largest term, and the format has carried the answer
since v2: **every slot entry declares its own `capacity`**, the byte
budget the baker computed for it. The runtime ignores it for sizing
and allocates `PS2UI_SLOT_BUFSZ` (96) for every slot regardless.

| UI | slots | 96 B each | declared capacities |
|---|---:|---:|---:|
| UC-3 | 121 | 11,616 B | **2,966 B** |
| channel-6 | 15 | 1,440 B | 325 B |
| memcard | 6 | 576 B | 160 B |

Another 3.9× on the dominant term, from information already in the
file. No format change is required to get it — only for the runtime to
read what is there.

---

## 2. The arena

One caller-provided block, sized from the blob.

```c
/* Bytes of scratch this blob needs. Reads the header and table
 * counts only; it does not validate the blob and does not touch the
 * GS. Returns 0 if the header is unreadable, which is also the answer
 * for "do not bother calling load". */
size_t ps2ui_arena_size(const void *data, size_t size);

/* Load, using caller-provided scratch. The arena must be at least
 * ps2ui_arena_size() bytes and PS2UI_ARENA_ALIGN-aligned; the context
 * points into it and does not copy it. Lifetime is the caller's, and
 * it must outlive the context, exactly like `data` already does. */
int ps2ui_load(ps2ui_ctx *ctx, const void *data, size_t size,
               void *arena, size_t arena_size);
```

Typical use, still no allocator on the console:

```c
static uint8_t arena[4096] __attribute__((aligned(16)));

size_t need = ps2ui_arena_size(uib, uib_len);
if (need > sizeof arena) { /* refuse, loudly, with the number */ }
ps2ui_load(&ui, uib, uib_len, arena, sizeof arena);
```

An app that wants a static buffer gets a compile-time number from the
bake (`ps2ui-bake` prints it, `ps2ui-check` reports it); an app with a
heap can `malloc` it. Neither is imposed.

### Layout

Sub-allocated in one pass, in descending alignment so no padding is
needed between regions:

| region | count | from |
|---|---|---|
| permuted CLUTs **[rev 2]** | `n_clut` × 1,024 B, 16-aligned, first | CLUT table |
| `GSTEXTURE[]` | `n_tex` | header |
| slot text | Σ (`capacity` + 1) | slot table |
| slot offsets | `n_slot` × `uint16_t` | header |
| `slot_is_set` bits | `n_slot` | header |
| `hidden` bits | `n_focus` | header |
| `screen_focus[]` | `n_screen` | header |

The context keeps pointers rather than arrays. `slot_text[i]` becomes
`ctx->slot_text + ctx->slot_off[i]`, which is one more indirection on
a path that already does a name lookup.

**[implemented] One CLUT buffer per palette, not per texture.** Rev 2
sized this region per PSMT8 *texture*, which measurement immediately
punished: the memcard blob has **8 indexed textures sharing a single
palette**, so per-texture staging cost 8 KiB for 1 KiB of distinct
data — on what had just become the arena's dominant term. Textures
naming the same CLUT index now share one permuted buffer, which is
sound because the permutation is a pure function of the palette and
the buffer is read-only once uploaded. The memcard arena fell from
9,302 to **2,134** bytes on that one change.

**[implemented] The arena size is target-dependent, and any report of
it has to say so.** The region holding `GSTEXTURE[]` is sized by a
gsKit struct carrying two pointers, so `sizeof(GSTEXTURE)` is 40 bytes
on the EE and 48 on a 64-bit host. The same blob therefore needs a
different arena in the sample ELF than in the host test suite, and a
tool printing one number without naming a target would be wrong about
half the time. `ps2ui-bake` and `ps2ui-check` print the EE number,
because that is where the static buffer lives, and `ps2ui-check` names
both.

Measured, against the ~36 KiB of fixed cost this replaces (a 3,328-byte
context plus the 32 KiB CLUT pool):

Figures as measured at v6, when this was written. P3b-6 moved two of
them -- channel-6 to 10,624 and memcard to 1,662 -- by changing what a
rounded box costs; the ratios are unaffected in kind and the table is
left at its own moment rather than tracking a number it was never
about.

| UI | arena (EE) | + context | was | ratio |
|---|---:|---:|---:|---:|
| channel-6 | 10,544 | 10,736 | 36,096 | 3.4× |
| memcard | 1,982 | 2,174 | 36,096 | 16.6× |
| runtime list fixture | 1,190 | 1,382 | 36,096 | **26×** |
| test card | 122 | 314 | 36,096 | **115×** |

**`PS2UI_SLOT_BUFSZ` disappears as a storage constant.** It survives
only as the baker's default `data-slot-capacity`, which is where the
number always belonged. **[implemented]** Deleting it from `ps2ui.h`
broke three things that had quietly depended on it — `caps.py`'s
enforcement, `ps2ui-check`'s report, and the channel-6 example's own
checker — each of which asserted a capacity ceiling that no longer
exists. All three now report the arena requirement instead of
asserting a limit, because there is no threshold left to fail against
and inventing one would be a made-up number.

### The constants stay, as limits

`PS2UI_MAX_*` are not deleted. They stop being storage and become
**validation limits**: the loader still refuses a blob claiming
100,000 slots, because a bad header should be rejected before anything
sizes an allocation from it. An integrator raising them pays nothing
until a blob actually uses the room, which is the property that does
not exist today.

`caps.py` keeps parsing them from `ps2ui.h`, so the bake still refuses
what the runtime would reject. That machinery does not change.

**[revised — this section was wrong]** Three of them are deleted:
`PS2UI_MAX_TEXTURES`, `PS2UI_MAX_SLOTS`, `PS2UI_MAX_SCREENS`. The
argument above does not survive contact with the implementation.

- *"the loader still refuses a blob claiming 100,000 slots"* — it
  already did, and not because of these. Every table is bounds-checked
  as `off_X + n_X * sizeof(entry) <= size`, so a count is bounded by
  the file that carries it. A blob claiming 100,000 slots would need a
  3.2 MB slot table to be claiming it truthfully, and is rejected as
  truncated otherwise. The ceiling was a second, weaker statement of a
  check that was already there.
- *"a bad header should be rejected before anything sizes an
  allocation from it"* — this half is real, and it is the only half.
  What it needs is not a ceiling but arithmetic that refuses rather
  than wraps: counts are `uint16` and capacity is `uint16`, so a legal
  header can demand 65535 × 65536 bytes of slot text, and that total
  wraps a 32-bit `size_t` — which is what the EE has. A wrapped total
  carves a small arena for a huge blob and every region overlaps.
  `arena_compute` now accumulates in 64 bits and refuses the carve
  before narrowing, returning `PS2UI_ERR_TOO_MANY` — a name that keeps
  its meaning and loses its arbitrary numbers.
- *"an integrator raising them pays nothing"* — an integrator should
  not have to edit a vendored header to ship a five-screen UI. The
  UC-3 scoping fixture measures 121 slots and 5 screens; under the
  ceilings it could not be baked at all. It now bakes on a stock
  checkout and asked for **8,285 bytes** of arena when this was
  written, against roughly 36 KiB that the fixed context charged every
  blob including a two-slot overlay. The ratio is the argument and it
  survived the change.

Removing one and keeping the others was not an option worth taking:
they were a single three-line check and a single idea.

`PS2UI_MAX_SCISSOR_DEPTH` stays, because it is the one that was never
a validation limit — `ps2ui_render` keeps a real stack that deep, and
the bake refuses deeper nesting rather than letting it fail soft on a
television.

The guard is testable at the width that matters. The host suite is
64-bit and the CI image has no 32-bit libc, so `make -C runtime
test-narrow` compiles `ps2ui.c` with `-DPS2UI_ARENA_LIMIT=0xFFFFFFFF`
and feeds it both a blob that must be refused and one that must still
load — the second because a guard that rejects everything passes the
first.

### Slot storage: copied, not borrowed

**[decided]** PLAN §6.3 pairs the ceiling removal with *"app-owned
storage bound to the rows live in a list window — the model F2
specified"*, and §4.2 records that what shipped *"diverged from its own
design"* by putting the storage in the context. Half of that critique
is now answered: the storage is no longer sized by a ceiling, it is
sized per slot from the capacity the blob declares.

The other half — making `ps2ui_slot_set` borrow the caller's string
the way `ps2ui_tex_set` borrows the caller's texels — is **declined**,
and the reason is that the symmetry is superficial.

What borrowing would save, measured on the largest UI in the
repository (the UC-3 environment, 121 slots) at the time this was
written:

| arena region | bytes |
|---|---:|
| permuted CLUTs | 4,096 |
| **slot text** | **2,966** |
| texture handles | 600 |
| slot offsets | 484 |
| everything else | 139 |
| **total** | **8,285** |

So about 3.4 KiB, on a machine with 32 MiB. The longest slot in that
UI declares 80 bytes.

What borrowing would cost is not symmetric with the texture case:

- **A texture is one buffer the app already manages deliberately** —
  it decoded a PNG into it and knows when the row scrolls away.
  Strings are the opposite: they are the transient output of a
  directory read, and "keep this alive and unmoved until the row stops
  being drawn" is a much easier obligation to violate. The failure is
  a use-after-free rendered as glyphs.
- **Truncation would move to render time.** Today `slot_set` copies at
  the declared capacity and trims a partial UTF-8 sequence in place.
  Over a borrowed pointer the pen would have to re-derive both every
  frame, for every slot, instead of once per change.
- **The copy is not what was expensive.** §4.2's complaint was that
  storage was `slot_text[16][96]` — a ceiling charged to every blob.
  That is gone. What remains is 2,966 bytes that exist because 121
  slots declared them.

F2's note said "caller-provided slot buffers" when the alternative was
a fixed array. Against per-slot arena storage the argument is thinner
than the lifetime hazard it introduces, so the pull rule applies to it
the way it applies to any other feature: it enters when a use case
demands it. Phase 2's skeleton is the test — if the OPL environment
finds 3.4 KiB or the copy cost material, this reverses on evidence.

**Related, and not fixed here:** `slot_index_by_name` is a linear
`strcmp` scan. With the ceiling at 16 that was free; at 121 a list
refreshing 28 rows does roughly 1,700 short `strcmp`s per scroll step,
which is well under a millisecond on a 294 MHz EE but is no longer
nothing. Left alone deliberately — Phase 2 measures frame time on a
real library, and that measurement should decide whether this wants
the same sorted-table bsearch the focus lookup uses, rather than a
guess made here.

### What this fixes beyond size

`MAX_HIDEABLE` is the one that fails *silently* today: a blob with more
focusables than 256 loads and renders correctly but cannot hide the
ones past the ceiling, and `ps2ui_visible_set` returns 0 for reasons
the caller cannot distinguish from a typo. Sized from `n_focus`, the
case stops existing rather than being reported better.

---

## 3. Texture slots: baked, streamed, absent

The other blocker. Cover art discovered at runtime — from HDD, USB, or
Ethernet — cannot be baked, and today there is no other way to get a
texel onto the GS.

**This does not need an allocator.** `PLAN.md` §4.3 corrects an
inherited assumption: the old F19 → F20 dependency treated streaming
as a special case of general unload-and-rebudget. It is not. A
streamed slot is a **fixed reservation**, decided at bake time when
the size is already known:

- layout sizes the element as it does any `<img>`
- the baker records the slot's page-rounded VRAM cost in the texture
  table, with **no texel data in the blob**
- at runtime the app hands over already-encoded texels; the runtime
  stages them and the next bind uploads

**[rev 2] "Reservation" means a budget line, not an address.** The
draft said the baker "reserves page-aligned VRAM", which implied an
address decided at bake — and that model died with #41: the runtime
now binds every texture through `gsKit_TexManager_bind`, and
`gsKit_vram_alloc` *resets the TexManager's block list* (gsCore.c:45),
so explicit placement and managed binding cannot coexist in one
context. Streamed slots therefore ride the same path as baked ones:

- the **bake-time** reservation is vram.py's page math counting the
  streamed slot as if its texels existed — the budget check fails the
  build if the working set cannot fit;
- the **load-time** preflight (#41) counts streamed reservations in
  `vram_need`, so residency is stable by the same argument that keeps
  baked textures from eviction thrash;
- `ps2ui_tex_set` validates, points the slot at the caller's texels,
  `SyncDCache`s them, and calls `gsKit_TexManager_invalidate` — the
  next render's bind performs the upload, exactly as it does after a
  VRAM heal today. No new upload path exists to get wrong.

**[implemented] Nothing is copied, and the staging buffer is gone.**
Rev 2 said "copies into the slot's staging buffer", and the
implementation deliberately does not. Measured against the case the
feature exists for — a library scrolling 128×128 covers — staging is
**576 KiB of duplicate texels for nine visible rows** (64 KiB each in
PSMCT32) on a 32 MB machine, duplicating bytes the caller already
holds. It was also inconsistent: ps2ui already points
`GSTEXTURE::Mem` straight into the caller's blob for every baked
texture, so the project had one zero-copy lifetime rule and was about
to grow a second, copying one.

The slot borrows. The caller's buffer must stay alive, unmoved and
16-aligned for as long as the slot can be drawn — the same sentence
that already applied to the blob, and for the same reason: gsKit
re-reads that pointer whenever the texture manager re-binds an evicted
texture, which is **render time, not `tex_set` time**. It also makes a
cover swap O(1) rather than a 64 KiB memcpy per scrolled row, which
the Phase 2 field-rate gate has to pay for either way.

**[rev 2] Two byte counts, not one.** The draft's "len must equal the
reservation" conflated the page-rounded VRAM cost with the caller's
payload. `len` is the *linear texel size* (`w × h × bpp`, plus 1,024
for a PSMT8 palette when the slot carries its own); the reservation is
the page-rounded number vram.py computes. The bake records both; the
mismatch error names which one the caller missed.

```c
/* Point a streamed texture slot at the caller's texels. `len` must
 * equal the entry's reservation exactly; a mismatch is an error
 * rather than a partial upload, because a half-written texture is
 * worse than none. Nothing is copied: `texels` becomes this slot's
 * DMA source and must outlive every draw of it.
 *
 * [implemented] Takes `gs`, which rev 1 did not: invalidating
 * residency needs the GSGLOBAL, and every other GS-touching entry
 * point in this API already takes one. Keeping the shorter signature
 * would have meant storing a GSGLOBAL* in the context — hidden state
 * to avoid an argument. */
int ps2ui_tex_set(ps2ui_ctx *ctx, GSGLOBAL *gs, const char *name,
                  const void *texels, size_t len);
```

Every invariant holds. No allocation (VRAM pre-reserved, texels in the
caller's buffer), no parsing (the app or a decoder produces PSMCT32 or
PSMT8 + CLUT; the runtime moves bytes), and the console still never
lays anything out.

**Format cost:** texture entries gain a kind (baked / streamed) and a
name offset for the lookup. Streamed entries carry a reservation
rather than a `data_off`. Feature bit for the capability.

**Deliberately out of scope:** eviction, LRU, packing several arts
into one reservation, and any notion of residency beyond "this slot is
reserved and currently holds whatever was last written." A library
with 400 covers and 9 visible rows needs 9 reservations, not 400 —
which the windowing model already implies. General unload stays parked
until a shell-and-module use case pulls it (`PLAN.md` pull lane).

**[rev 2] Settled, was open:** a streamed PSMT8 slot's palette is
supplied **linear** and the runtime permutes it, exactly as
`permute_clut` does for baked palettes. Rev 1 could only have picked a
convention; Phase 0 built the instrument that *guards* one — probe6's
column G reads the composed convention on silicon and in CI on every
run — so streamed palettes take the path that instrument watches
rather than adding a second convention beside it. Whether a slot may
alternatively share a baked palette stays open for Phase 2's skeleton
to pull, but the supplied-palette case is decided.

---

## 4. Composition becomes a contract

`ps2ui_render` never clears. Two `screen_set` + `render` pairs in one
frame therefore composite — measured at 375 + 255 = 630 primitives on
the memcard blob, with focus routing landing correctly on the overlay.

That is the dialog and modal technique an OPL-class environment needs,
and it currently works **by accident**: undocumented, untested, and
found by experiment rather than design. The first innocent refactor
that adds a clear to `render` deletes it.

Phase 1 makes it a contract:

- documented in `docs/format-uib.md` and the README, with the
  no-clear guarantee stated as a guarantee
- a runtime test that composites two screens and asserts the primitive
  count is the sum, so the property cannot regress silently
- the focus question answered explicitly: which screen receives D-pad
  input when two are drawn

**[rev 2]** Composition survives the TexManager migration for a
reason worth writing down: both renders bind from the same context,
the preflight already counts the whole blob, and
`gsKit_TexManager_nextFrame` runs once per *frame* (the sample calls
it after `sync_flip`), not once per render — so two composited renders
neither double-age nor evict each other's textures. The contract test
should pin that: composite two screens, assert the primitive count is
the sum *and* the transfer count is what a single residency implies.

**Open:** whether that wants an API (`ps2ui_overlay_push`) or just a
documented idiom over `screen_set`. The idiom works today and costs
nothing; an API would let the runtime keep the input screen and the
drawn screens distinct, which the idiom cannot. Leaning toward
documenting the idiom in v6 and adding the API only when the Phase 2
skeleton shows the idiom is awkward — the pull rule applied to our own
design.

**[implemented]** Idiom, as leaned. No `ps2ui_overlay_push`; the one
thing it would buy that `screen_set` cannot express is a dialog drawn
over a base that still receives the D-pad, and nothing has asked for
that. Written down in `ps2ui.h` so the absence is a decision on the
record rather than a gap.

The contract is stated on `ps2ui_render` in the header, in the README
with a worked frame loop, and in `format-uib.md` (an overlay screen is
an ordinary screen with a scrim; the format needs no flag and has
none). The focus question is answered: **input follows the last
`screen_set`**, so an overlay drawn last owns the D-pad for free and
dismissing it is one call back, restoring the base's remembered focus.

Fenced by 23 checks. Four notes on what making them real took,
because two of the first drafts asserted nothing:

- **The primitive sum does not fence the guarantee.** `composed ==
  solo_a + solo_b` survives a clear being added to `render` — a clear
  costs no primitives — and a clear is precisely the refactor this
  section names as the one that deletes the feature. `gsKit_clear` was
  not in the host stub at all, so a render that called it failed to
  *link*: a fence, but an accidental one saying "undefined reference"
  rather than which guarantee broke. The stub now counts clears and
  the contract asserts zero.
- **"The overlay transfers nothing the base made resident" is false,
  and correctly so.** The overlay's own atlases have not been bound
  that frame, so transferring them is first use, not eviction. The
  property worth pinning is steady state: a composited frame that runs
  again costs no pixels. That is what rev 2's argument actually
  predicts.
- **Scissor state cannot move a prim count in this suite**, so the
  anti-leak check reads the register instead. It is delivered by two
  mechanisms — a balanced blob's last POP re-applies `stack[0]`, and
  `render` restores it explicitly — so deleting either alone leaves it
  green. It fires when both go. That redundancy is *structurally*
  untestable rather than merely untested: the baker refuses to write
  an unbalanced blob and `render` refuses the pops of pushes it
  refused, so no blob the loader accepts can distinguish the two. A
  reason to keep both and disclose it, not to hunt for a fixture.
- **A documented trap is not a fenced one.** The `nextFrame` trap was
  written into three documents and asserted nowhere; moving
  `gsKit_TexManager_nextFrame` into `ps2ui_render` left the suite
  green. Same shape as `gsKit_clear` one step further along — the stub
  had `nextFrame` as a bare no-op, so a render calling it linked fine.
  Counting it is not modelling the eviction heuristic, which stays out
  on purpose; it is the stub's own rule applied again. This one
  matters more than the clear in one respect: a clear is visible the
  instant anyone looks at a composited frame, while a misplaced ageing
  tick shows up only as frame time.

**What the host cannot answer.** The stub leaves gsKit's eviction
heuristic unmodelled on purpose: `ps2ui_upload` preflights the whole
blob, so eviction is unreachable, and modelling the weight function
would certify a guess. The tests therefore fence "nothing on the
composite path invalidates or resets residency" — the half a refactor
can break. Whether the real manager keeps both screens resident under
pressure is a console question, and it joins the streamed-cover demo
at the Phase 1 bench sitting.

**Also now stated, because it is a trap:** `ctx->stats` is reset at the
top of every `ps2ui_render`, so a composited frame ends holding the
*overlay's* counters, not the frame's. A caller summing frame cost has
to read them between renders. Asserted rather than left to be
discovered from a wrong number on a television.

---

## 5. API changes riding along

One breaking release, so the deferred API debts land here rather than
accumulating:

- **`ps2ui_load` signature** — gains the arena. Every caller changes.
- **`ps2ui_visible_get` / `_set`** — the #16 review found both conflate
  distinct failures into `0`: unknown name, name past `MAX_HIDEABLE`,
  and (for `get`) genuinely-hidden. With the ceiling gone one cause
  disappears; the rest want distinct returns.
- **`ps2ui_arena_size`, `ps2ui_tex_set`** — new.

**[implemented]** All three have shipped. `visible_get` returns
`PS2UI_VISIBLE_UNKNOWN` (-1) for a name the current screen does not
have, distinct from `0` for hidden — the typo is the failure a caller
can actually fix. `visible_set` keeps a plain 0/1, because with the
bits sized from `n_focus` its only remaining failure *is* the unknown
name. Two error codes were added that this section did not anticipate,
both for `tex_set`: `PS2UI_ERR_NOT_STREAMED` and `PS2UI_ERR_SIZE`.

---

## 6. Format: what actually moves

| change | why |
|---|---|
| texture entry: kind + name offset + reservation | streamed slots need to be named and sized without data |
| feature bit: streamed textures | a reader that cannot stream must reject a blob that requires it |
| version bump to 6 | the texture entry changes size, so a v5 reader would walk the table at the wrong stride |

**Not changing:** the slot table (capacity is already there), the
command list, the focus graph, the font and kern tables, the header.
The arena is a runtime concern that reads what v5 already records —
worth stating plainly, because "resource model rework" sounds like it
should move more of the format than it does.

---

## 7. Migration

- **Blobs:** v5 and earlier rejected at load with `PS2UI_ERR_VERSION`.
  Re-bake; no authoring changes for anything that does not use
  streamed textures.
- **Apps:** `ps2ui_load` gains two arguments. An app with a fixed UI
  can size the arena as a compile-time constant from the bake output;
  the compile fails until it does, which is the intended outcome.
- **Examples:** both, plus the runtime fixture and the sample ELF.
- **`ps2ui-check`:** reports the arena requirement so an integrator
  sizing a static buffer has the number without running anything.

---

## 8. What would falsify this

Written down so the design can lose rather than be defended:

- **The arena is not worth it if `ps2ui_arena_size` is unusable in
  practice** — an app that cannot know its blob at compile time has to
  size a worst-case buffer anyway, which is the fixed model with extra
  steps. Phase 2's skeleton is the test: if the OPL skeleton ends up
  hardcoding a maximum, the arena bought complexity and nothing else.
- **Streamed textures are not worth it if decode dominates.** Reserving
  VRAM is free; producing PSMT8 texels from a PNG on a 294 MHz EE may
  not be. If decoding a cover costs more than a frame, the design needs
  an async story and this section is wrong about "no allocation" being
  the hard part.
- **[rev 2] Streamed slots are not worth it if residency thrashes.**
  The reservation-as-budget model holds only while everything the
  preflight counts genuinely fits — if Phase 2's skeleton oversubscribes
  VRAM, `_blockAlloc`'s evict-forever loop (the #41 hang class) returns
  wearing a streaming hat, and the answer must stay "refuse at
  preflight", never "evict smarter". If that refusal proves too coarse
  for a real library screen, this section is wrong and the parked
  general-unload work gets pulled early.
- **The composition idiom may not survive contact.** If the Phase 2
  skeleton needs an overlay that keeps its own focus while a background
  screen keeps its own, `screen_set` + `render` cannot express it and
  the API is not optional.

Each is a question Phase 2 answers by building, which is the order the
plan already prescribes: verify the metal, unify the model, **prove it
with a real application**, then spend the hardware.
