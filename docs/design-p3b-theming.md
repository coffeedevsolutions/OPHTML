# Design: theming

*Draft · 2026-08-29 · Phase 3 of `docs/PLAN.md` · nothing implemented
beyond §3's mechanism (F-041)*

> **Status.** This is the design pass `design-v6-resource-model.md` set
> the precedent for: written before the format moves, so the argument
> can be attacked while it is still cheap. §3's *mechanism* has shipped
> and is measured (F-041, #70); everything else here is proposed.
>
> It disagrees with `PLAN.md` about what P3b is, and the disagreement
> is the point of the document.
>
> **Rev 2** is the adversarial pass, run against the draft the same day
> on two questions: does this make the developer's experience better,
> and does it optimise for the PS2 at bake time. Four findings are
> folded in below, marked **[rev 2]**. One of them retracts a headline
> claim of the draft outright. As with the v6 document, the losing
> argument is left in place rather than quietly rewritten.

---

## 1. What the plan says, and why it is the smaller half

> **CLUT-swap theming:** same PSMT8 art, multiple ~1 KiB palettes;
> instant recolor for themes and focus states.

The mechanism is real. `gsKit_TexManager_bind` re-sends a palette
without its texels, at 1,024 bytes per *drawn* texture and lazily
[F-041]. That part of the plan survives contact.

What does not survive is the assumption that a UI's colour lives in its
palettes. **It does not.** In `examples/opl-env`, of 1,302 commands:

| textures | count |
|---|---|
| PSMT8 + CLUT (glyph atlases) | 7, across 2 CLUTs |
| PSMCT32 baked | 11 |
| PSMCT32 streamed (covers) | 10 |

and **997 of the 1,302 commands carry `(128,128,128,128)`** — the
identity tint. Those draw art at its own colour. The remaining ~300
carry a real tint, and *every panel, border and background in the
environment is an untextured QUAD whose colour is a baked
`r,g,b,a` in the command itself.*

So a CLUT swap recolours the glyph atlases and the palettized art. It
cannot touch the panels, the borders, the focus ring or the background
— which is where a theme actually lives.

Worse, it multiplies rather than replaces: glyph atlases are white and
modulated, so a red CLUT under a blue baked tint gives a dark mess. To
theme text by palette, the per-command tint would have to be neutral,
which is a different bake and loses per-element colour entirely.

**CLUT swap is a global multiplier on palettized art. It is worth
having. It is not theming.**

---

## 2. The measurement that decides the design

Distinct colours across every command, in every blob this repo ships:

| blob | commands | distinct colours | table | ~~blob saved~~ |
|---|---|---|---|---|
| `examples/opl-env` | 1,302 | **9** | 36 B | ~~3,906 B~~ **0** |
| `examples/channel6` | 913 | **32** | 128 B | ~~2,739 B~~ **0** |
| `examples/memcard` | 808 | **10** | 40 B | ~~2,424 B~~ **0** |
| `fixtures/bench-stream` | 74 | 8 | 32 B | ~~222 B~~ **0** |
| `examples/memcard` testcard | 18 | 7 | 28 B | ~~54 B~~ **0** |

**[rev 2] The blob does not shrink, and the draft was wrong to say so.**
`ps2ui_cmd` is **32 bytes: 26 used and `pad0[6]`**. Replacing `r,g,b,a`
with a `uint16_t` frees two bytes into padding that exists precisely to
reach 32 — two qwords. The next size down is 16, and `u0,v0,u1,v1`
alone spend 8 of those. The "saved" column came from adding up field
widths and forgetting the struct.

Retracted rather than deleted, because it was the second-best argument
for the design and it is worth knowing that it is not available.

Nine colours in a six-screen environment. Thirty-two in the most
colourful thing here.

A UI's colour is a **tiny set, repeated thousands of times**. That is
the fact the design should be built on, and the plan predates anyone
counting.

---

## 3. Two mechanisms, sized by what they carry

### 3a. The tint table — where a theme actually lives

Commands stop storing four colour bytes and store an **index** into a
per-blob tint table. The runtime resolves the index at replay, where it
already writes a vertex colour. A theme is an alternative table.

```
theme "dark"    9 entries x 4 bytes  =  36 bytes
theme "light"   9 entries x 4 bytes  =  36 bytes
```

**Thirty-six bytes per theme**, against 1,024 per drawn texture for a
CLUT swap. It reaches every command rather than only textured ones, it
costs the GS nothing (the vertex colour is written either way), and it
costs the EE one indirection per command on a processor measured at
14.4% of a field [F-036].

~~It also makes the blob *smaller*: 3 bytes per command, 3,906 in
opl-env, which is more than the entire arena.~~

**[rev 2] False — see §2.** The freed bytes land in existing padding
and the blob is byte-for-byte the same size. What they are good for is
different and better: **two spare bytes inside a struct that does not
grow**, which is exactly what open question 1 needs. `pad0[6]` becomes
`pad0[4]` plus a second `uint16_t` for a focus-state tint, and the
focus recolour stops being a future format move at all.

### 3b. The CLUT swap — for art the tint table cannot reach

Palettized art whose colour is in its texels, not in a vertex tint.
`ps2ui_clut_set` already exists and is measured [F-041]. It stays, with
its honest scope: a global multiplier on everything drawn from one
palette, 1,024 bytes per drawn texture, lazy.

The two compose. Neither replaces the other.

---

## 4. Authoring

The natural expression is the one CSS already has, and it is the part
of this design with real unknowns.

```css
:root      { --panel: #12182a; --ink: #dde3f0; }
@theme light { --panel: #ffffff; --ink: #1a2033; }

.row { background: var(--panel); color: var(--ink); }
```

- `:root` custom properties define the default table.
- `@theme <name>` supplies an alternative for the same keys.
- A colour written literally rather than through `var()` still becomes
  a table entry — it simply has the same value in every theme. This
  matters: it means the format is uniform and no command is special.

### [rev 2] Entries key on ROLE, not on value

The draft deduplicated by resolved RGBA, which is where the "9 colours"
figure comes from. **That is a silent trap and it has to go.** Counted
over the real stylesheets:

| stylesheet | colour declarations | distinct values | values shared by >1 declaration |
|---|---|---|---|
| `opl-env/opl.css` | 81 | 25 | **13** |
| `channel6.css` | 74 | 38 | 15 |
| `memcard/library.css` | 36 | 24 | 9 |

In opl-env, **`#7c9be0` is written by nine separate declarations** —
the focus border, a chip outline, a button edge and six more. Under
value-dedup those nine collapse into one theme slot. An author writing
a light theme moves the focus ring and eight unrelated things move with
it, or writes a rule that cannot take effect, **and nothing tells them
either happened**: the blob just has 9 entries and no record of why.

That is the worst kind of developer experience — a correct-looking
input producing a wrong output with no diagnostic — and it was in the
draft as a *falsifier* when it should have been a defect.

Keying on the declaration site instead: **81 entries, 324 bytes** for
the most colourful example here. The table was never the expensive
part, and thanks to §2's retraction the command struct does not grow
either way. Two declarations that happen to share a hex value stay
independent, which is what an author means by writing them twice.

The `uint16_t` index the draft picked for future-proofing turns out to
be the right width for the *present*: role-keying pushes the count from
9 to 81, and 8 bits would already be uncomfortable at channel6's scale
plus themes.

**The layout CSS parser has no `var()` support today.** `parseColor`
is called on a resolved value in `css.js`, and nothing resolves custom
properties. That is the largest single implementation cost here and it
should be scoped before anything else, because if `var()` proves
awkward in this parser the whole authoring story needs a different
shape and §3a does not depend on it — indices can be assigned from
literal colours with no CSS change at all.

### [rev 2] Three things the author has to be able to see

The draft described a format and an API and said nothing about how
anyone would debug a theme. Each of these is cheap and each closes a
failure that would otherwise be discovered on a television.

1. **`ps2ui-check` prints the tint table with its CSS origin** — index,
   value per theme, and the declaration that produced it. Without it
   "why did this not change colour" has no answer short of reading the
   blob by hand.
2. **The previewer renders every theme**, one screenshot set each.
   `ps2ui-bake` already emits screenshots and the drift check already
   diffs them; a theme nobody can look at without a PS2 is a theme
   nobody will get right. This also means the *existing* screenshot
   drift check covers themes for free.
3. **A theme that omits a key fails `--strict`.** Silently inheriting
   the root value is the behaviour that ships a half-converted theme
   and looks fine on the two screens the author happened to open.

**Deliberately not proposed:** a theme that changes anything but
colour. Sizes, fonts and layout are baked geometry; making those
themeable is a different and much larger change, and nothing measured
here argues for it.

---

## 5. Format

```c
typedef struct ps2ui_tint_entry { uint8_t r, g, b, a; } ps2ui_tint_entry;
```

Header gains `n_tint`, `n_theme`, `off_tint`. The table is
`n_theme x n_tint` entries, theme-major. `ps2ui_cmd` loses `r,g,b,a`
and gains `uint16_t tint`.

Sized from the blob, not from a ceiling — P1i removed the last of those
and this must not add one back. 32 colours is the highest count
observed; `uint16_t` is chosen so that a photographic UI with a
thousand does not hit a wall it cannot see coming.

`a` stays in the GS 0–128 domain [F-001], converted at bake exactly as
it is now, so nothing about the alpha contract moves.

---

## 6. Runtime API

```c
int ps2ui_theme_set(ps2ui_ctx *ctx, unsigned theme);
```

No `GSGLOBAL`. Unlike `ps2ui_clut_set`, this touches no texture state
and needs no bind — the next `ps2ui_render` reads the new table when it
replays. That asymmetry is worth stating in the header: one of these
functions schedules a transfer and the other does not.

Returns `PS2UI_ERR_RANGE` past `n_theme`. Callable before `ps2ui_upload`,
because unlike `clut_set` there is nothing for upload to overwrite.

---

## 7. What this costs

| | tint table | CLUT swap |
|---|---|---|
| per theme | 32–324 B *(rev 2: role-keyed)* | 1,024 B per drawn texture |
| reaches | every command | palettized art only |
| GS cost | none | one palette transfer |
| EE cost | one indirection per command | none |
| blob | unchanged *(rev 2: padding absorbs it)* | grows by each palette |

---

## 8. What would falsify this

- **A shipped UI with hundreds of distinct colours.** The whole design
  rests on the set being small, from five blobs that are all this
  project's own. A photographic or gradient-heavy interface is the
  obvious counterexample and none has been baked.
- ~~**A theme that needs two elements sharing a colour to diverge.**~~
  **[rev 2] Resolved, not falsified: it is common.** Thirteen values in
  opl-env are shared by more than one declaration and one of them by
  nine. Entries key on role now, and the count is 81 rather than 9. A
  falsifier that fires the first time anybody checks was a defect
  wearing a falsifier's clothes.
- **`var()` proving structurally awkward** in the layout parser, which
  would not kill §3a but would change §4 entirely.
- **The EE indirection mattering.** **[rev 2] Priced, and it is not a
  cost at all.** 1,302 commands × ~3 cycles is 13.2 µs against an `ee`
  of 2,410 — 0.55% worst case. More to the point it *replaces* a load
  rather than adding one: `cmd->r,g,b,a` was a load too. A 324-byte
  table stays hot while 41 KB of command list streams past it, so the
  indirect form is plausibly the cheaper of the two. It stays on this
  list because it is measurable and the instrument exists, not because
  it is expected.

---

## 9. Open questions

1. ~~**Focus states.**~~ **[rev 2] Closed by §3a's retraction.** A
   second index per command is what a focus recolour needs, and the two
   bytes freed from `r,g,b,a` land in `pad0` and pay for exactly that.
   `pad0[6]` becomes `pad0[4]` plus `uint16_t tint_focus`. No growth,
   no later format move, and it is only visible as an option because
   the blob-shrink claim was checked and failed.
2. **Does anything want a theme that is not global?** One screen dark,
   another light. The table is per-context today. Per-screen is one
   more indirection and no format change; per-element is a different
   design.
3. **Migration.** `ps2ui_cmd` shrinking by 2 bytes is a v7 format move.
   Whether it rides with anything else in Phase 3 depends on what P3c
   turns into now that its performance argument is gone [F-037].
