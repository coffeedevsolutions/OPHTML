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

| blob | commands | distinct colours | table | blob saved |
|---|---|---|---|---|
| `examples/opl-env` | 1,302 | **9** | 36 B | 3,906 B |
| `examples/channel6` | 913 | **32** | 128 B | 2,739 B |
| `examples/memcard` | 808 | **10** | 40 B | 2,424 B |
| `fixtures/bench-stream` | 74 | 8 | 32 B | 222 B |
| `examples/memcard` testcard | 18 | 7 | 28 B | 54 B |

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

It also makes the blob *smaller*: 3 bytes per command, 3,906 in
opl-env, which is more than the entire arena.

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

**The layout CSS parser has no `var()` support today.** `parseColor`
is called on a resolved value in `css.js`, and nothing resolves custom
properties. That is the largest single implementation cost here and it
should be scoped before anything else, because if `var()` proves
awkward in this parser the whole authoring story needs a different
shape and §3a does not depend on it — indices can be assigned from
literal colours with no CSS change at all.

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
| per theme | 36–128 B | 1,024 B per drawn texture |
| reaches | every command | palettized art only |
| GS cost | none | one palette transfer |
| EE cost | one indirection per command | none |
| blob | **shrinks** 2.4–3.9 KB | grows by each palette |

---

## 8. What would falsify this

- **A shipped UI with hundreds of distinct colours.** The whole design
  rests on the set being small, from five blobs that are all this
  project's own. A photographic or gradient-heavy interface is the
  obvious counterexample and none has been baked.
- **A theme that needs two elements sharing a colour to diverge.** The
  table deduplicates by value, so two things that are both `#12182a`
  today become one entry and can never separate. If that turns out to
  be common, entries must key on *role* rather than value, and the
  count stops being 9.
- **`var()` proving structurally awkward** in the layout parser, which
  would not kill §3a but would change §4 entirely.
- **The EE indirection mattering.** It should not — 14.4% of a field,
  one lookup per command — but it is measured, not assumed, and the
  instrument to check it already exists.

---

## 9. Open questions

1. **Focus states.** The plan lists them beside themes. A focus ring is
   already a separate command list state, so it may need nothing here —
   but if focus is meant to *recolour* rather than to swap commands,
   that is a second index per command and should be designed now rather
   than bolted on.
2. **Does anything want a theme that is not global?** One screen dark,
   another light. The table is per-context today. Per-screen is one
   more indirection and no format change; per-element is a different
   design.
3. **Migration.** `ps2ui_cmd` shrinking by 2 bytes is a v7 format move.
   Whether it rides with anything else in Phase 3 depends on what P3c
   turns into now that its performance argument is gone [F-037].
