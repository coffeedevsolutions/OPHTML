# Design: the v6 resource model

*Draft · 2026-08-20 · Phase 1 of `docs/PLAN.md` · not implemented*

Phase 1 is one deliberate format move rather than a dribble of bumps
(`PLAN.md` §6). This is what it contains and why, written before the
first line of it exists so the argument can be attacked cheaply.

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
- the baker reserves page-aligned VRAM for `w × h` in the chosen format
  and records the reservation in the texture table, with **no texel
  data in the blob**
- at runtime the app hands over already-encoded texels; the runtime
  uploads them into the reservation it already owns

```c
/* Upload texels into a streamed texture slot. `len` must equal the
 * reservation the bake made; a mismatch is an error rather than a
 * partial upload, because a half-written texture is worse than none.
 * No allocation: the VRAM was reserved at load. */
int ps2ui_tex_set(ps2ui_ctx *ctx, const char *name,
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

**Open:** whether the app supplies a CLUT per streamed PSMT8 texture
or shares one baked palette. Sharing is cheaper and is probably right
for cover art, which is why it is worth deciding rather than
defaulting.

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

**Open:** whether that wants an API (`ps2ui_overlay_push`) or just a
documented idiom over `screen_set`. The idiom works today and costs
nothing; an API would let the runtime keep the input screen and the
drawn screens distinct, which the idiom cannot. Leaning toward
documenting the idiom in v6 and adding the API only when the Phase 2
skeleton shows the idiom is awkward — the pull rule applied to our own
design.

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
- **The composition idiom may not survive contact.** If the Phase 2
  skeleton needs an overlay that keeps its own focus while a background
  screen keeps its own, `screen_set` + `render` cannot express it and
  the API is not optional.

Each is a question Phase 2 answers by building, which is the order the
plan already prescribes: verify the metal, unify the model, **prove it
with a real application**, then spend the hardware.
